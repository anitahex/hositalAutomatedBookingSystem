from __future__ import annotations

import asyncio
import os
import sqlite3
import time
import tempfile
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from pathlib import Path
from typing import Any, Iterator, Sequence

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    PendingWrite,
    RunnableConfig,
    get_checkpoint_id,
    get_checkpoint_metadata,
)


DEFAULT_CHECKPOINT_PATH = Path(
    os.getenv("CHECKPOINT_DB_PATH") or (Path(tempfile.gettempdir()) / "hospital_ai_langgraph_checkpoints.sqlite")
)


class SQLiteCheckpointer(BaseCheckpointSaver[str], AbstractContextManager, AbstractAsyncContextManager):
    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        super().__init__()
        self.path = Path(path or DEFAULT_CHECKPOINT_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    parent_checkpoint_id TEXT,
                    checkpoint_type TEXT NOT NULL,
                    checkpoint_blob BLOB NOT NULL,
                    metadata_type TEXT NOT NULL,
                    metadata_blob BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoint_writes (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    task_path TEXT NOT NULL,
                    write_idx INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    value_blob BLOB NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx)
                )
                """
            )
            conn.commit()

    def _serialize(self, value: Any) -> tuple[str, bytes]:
        return self.serde.dumps_typed(value)

    def _deserialize(self, payload_type: str, payload_blob: bytes) -> Any:
        return self.serde.loads_typed((payload_type, payload_blob))

    def _row_to_tuple(self, config: RunnableConfig, row: sqlite3.Row) -> CheckpointTuple:
        checkpoint = self._deserialize(row["checkpoint_type"], row["checkpoint_blob"])
        metadata = self._deserialize(row["metadata_type"], row["metadata_blob"])
        thread_id = row["thread_id"]
        checkpoint_ns = row["checkpoint_ns"]
        checkpoint_id = row["checkpoint_id"]
        parent_checkpoint_id = row["parent_checkpoint_id"]
        with self._connect() as conn:
            write_rows = conn.execute(
                """
                SELECT task_id, channel, value_type, value_blob
                FROM checkpoint_writes
                WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                ORDER BY write_idx ASC
                """,
                (thread_id, checkpoint_ns, checkpoint_id),
            ).fetchall()
        pending_writes: list[PendingWrite] = [
            (str(item["task_id"]), str(item["channel"]), self._deserialize(item["value_type"], item["value_blob"]))
            for item in write_rows
        ]
        parent_config = (
            {"configurable": {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns, "checkpoint_id": parent_checkpoint_id}}
            if parent_checkpoint_id
            else None
        )
        return CheckpointTuple(
            config={"configurable": {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns, "checkpoint_id": checkpoint_id}},
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=parent_config,
            pending_writes=pending_writes,
        )

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)
        with self._connect() as conn:
            if checkpoint_id:
                row = conn.execute(
                    """
                    SELECT * FROM checkpoints
                    WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                    """,
                    (thread_id, checkpoint_ns, checkpoint_id),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM checkpoints
                    WHERE thread_id = ? AND checkpoint_ns = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (thread_id, checkpoint_ns),
                ).fetchone()
        if not row:
            return None
        return self._row_to_tuple(config, row)

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"] if config else None
        checkpoint_ns = config["configurable"].get("checkpoint_ns") if config else None
        before_checkpoint_id = get_checkpoint_id(before) if before else None
        query = "SELECT * FROM checkpoints"
        clauses: list[str] = []
        params: list[Any] = []
        if thread_id is not None:
            clauses.append("thread_id = ?")
            params.append(thread_id)
        if checkpoint_ns is not None:
            clauses.append("checkpoint_ns = ?")
            params.append(checkpoint_ns)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        for row in rows:
            if before_checkpoint_id and row["checkpoint_id"] >= before_checkpoint_id:
                continue
            checkpoint_tuple = self._row_to_tuple(config or {"configurable": {"thread_id": row["thread_id"], "checkpoint_ns": row["checkpoint_ns"], "checkpoint_id": row["checkpoint_id"]}}, row)
            if filter and not all(checkpoint_tuple.metadata.get(key) == value for key, value in filter.items()):
                continue
            if limit is not None:
                if limit <= 0:
                    break
                limit -= 1
            yield checkpoint_tuple

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")
        checkpoint_id = checkpoint["id"]
        checkpoint_type, checkpoint_blob = self._serialize(checkpoint)
        metadata_type, metadata_blob = self._serialize(get_checkpoint_metadata(config, metadata))
        created_at = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO checkpoints (
                    thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id,
                    checkpoint_type, checkpoint_blob, metadata_type, metadata_blob, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    checkpoint_ns,
                    checkpoint_id,
                    parent_checkpoint_id,
                    checkpoint_type,
                    checkpoint_blob,
                    metadata_type,
                    metadata_blob,
                    created_at,
                ),
            )
            conn.commit()
        return {"configurable": {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns, "checkpoint_id": checkpoint_id}}

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id", "")
        with self._connect() as conn:
            for index, (channel, value) in enumerate(writes):
                value_type, value_blob = self._serialize(value)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO checkpoint_writes (
                        thread_id, checkpoint_ns, checkpoint_id, task_id, task_path,
                        write_idx, channel, value_type, value_blob
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        thread_id,
                        checkpoint_ns,
                        checkpoint_id,
                        task_id,
                        task_path,
                        index,
                        channel,
                        value_type,
                        value_blob,
                    ),
                )
            conn.commit()

    def delete_thread(self, thread_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = ?", (thread_id,))
            conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
            conn.commit()

    def delete_for_runs(self, run_ids: Sequence[str]) -> None:
        if not run_ids:
            return
        placeholders = ",".join("?" for _ in run_ids)
        with self._connect() as conn:
            conn.execute(f"DELETE FROM checkpoint_writes WHERE checkpoint_id IN ({placeholders})", tuple(run_ids))
            conn.execute(f"DELETE FROM checkpoints WHERE checkpoint_id IN ({placeholders})", tuple(run_ids))
            conn.commit()

    def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        with self._connect() as conn:
            checkpoint_rows = conn.execute(
                "SELECT * FROM checkpoints WHERE thread_id = ?",
                (source_thread_id,),
            ).fetchall()
            write_rows = conn.execute(
                "SELECT * FROM checkpoint_writes WHERE thread_id = ?",
                (source_thread_id,),
            ).fetchall()
            for row in checkpoint_rows:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO checkpoints (
                        thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id,
                        checkpoint_type, checkpoint_blob, metadata_type, metadata_blob, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        target_thread_id,
                        row["checkpoint_ns"],
                        row["checkpoint_id"],
                        row["parent_checkpoint_id"],
                        row["checkpoint_type"],
                        row["checkpoint_blob"],
                        row["metadata_type"],
                        row["metadata_blob"],
                        row["created_at"],
                    ),
                )
            for row in write_rows:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO checkpoint_writes (
                        thread_id, checkpoint_ns, checkpoint_id, task_id, task_path,
                        write_idx, channel, value_type, value_blob
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        target_thread_id,
                        row["checkpoint_ns"],
                        row["checkpoint_id"],
                        row["task_id"],
                        row["task_path"],
                        row["write_idx"],
                        row["channel"],
                        row["value_type"],
                        row["value_blob"],
                    ),
                )
            conn.commit()

    def prune(self, thread_ids: Sequence[str], *, strategy: str = "keep_latest") -> None:
        if not thread_ids:
            return
        placeholders = ",".join("?" for _ in thread_ids)
        with self._connect() as conn:
            if strategy == "delete":
                conn.execute(f"DELETE FROM checkpoint_writes WHERE thread_id IN ({placeholders})", tuple(thread_ids))
                conn.execute(f"DELETE FROM checkpoints WHERE thread_id IN ({placeholders})", tuple(thread_ids))
            else:
                rows = conn.execute(
                    f"""
                    SELECT thread_id, checkpoint_ns, MAX(created_at) AS max_created
                    FROM checkpoints
                    WHERE thread_id IN ({placeholders})
                    GROUP BY thread_id, checkpoint_ns
                    """,
                    tuple(thread_ids),
                ).fetchall()
                keep_keys = {(row["thread_id"], row["checkpoint_ns"], row["max_created"]) for row in rows}
                for row in conn.execute(f"SELECT * FROM checkpoints WHERE thread_id IN ({placeholders})", tuple(thread_ids)).fetchall():
                    if (row["thread_id"], row["checkpoint_ns"], row["created_at"]) not in keep_keys:
                        conn.execute(
                            "DELETE FROM checkpoint_writes WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?",
                            (row["thread_id"], row["checkpoint_ns"], row["checkpoint_id"]),
                        )
                        conn.execute(
                            "DELETE FROM checkpoints WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?",
                            (row["thread_id"], row["checkpoint_ns"], row["checkpoint_id"]),
                        )
            conn.commit()

    async def aget(self, config: RunnableConfig) -> Checkpoint | None:
        return await asyncio.to_thread(super().aget, config)

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return await asyncio.to_thread(self.get_tuple, config)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ):
        def _collect():
            return list(self.list(config, filter=filter, before=before, limit=limit))

        for item in await asyncio.to_thread(_collect):
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        await asyncio.to_thread(self.delete_thread, thread_id)

    async def adelete_for_runs(self, run_ids: Sequence[str]) -> None:
        await asyncio.to_thread(self.delete_for_runs, run_ids)

    async def acopy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        await asyncio.to_thread(self.copy_thread, source_thread_id, target_thread_id)

    async def aprune(self, thread_ids: Sequence[str], *, strategy: str = "keep_latest") -> None:
        await asyncio.to_thread(self.prune, thread_ids, strategy=strategy)
