import asyncio
import re
import uuid
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime

from app.db.connection import connect_db


_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_active_usage_records: ContextVar[list[dict] | None] = ContextVar(
    "active_llm_usage_records",
    default=None,
)


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class TokenLogRecord:
    session_id: str
    patient_id: str
    node_name: str
    model_name: str
    input_tokens: int
    output_tokens: int
    status: str
    latency_ms: int


def new_chat_session_id() -> str:
    return str(uuid.uuid4())


def ensure_chat_session_id(state: dict) -> str:
    session_id = state.get("chat_session_id")
    if not session_id:
        session_id = new_chat_session_id()
        state["chat_session_id"] = session_id
    return session_id


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_TOKEN_PATTERN.findall(text))


def usage_from_response(response, prompt: str, completion: str) -> TokenUsage:
    usage = getattr(response, "usage", None)
    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
        completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")
    else:
        prompt_tokens = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None)
        completion_tokens = (
            getattr(usage, "completion_tokens", None)
            or getattr(usage, "output_tokens", None)
        )
        total_tokens = getattr(usage, "total_tokens", None)

    prompt_tokens = int(prompt_tokens) if prompt_tokens is not None else estimate_tokens(prompt)
    completion_tokens = (
        int(completion_tokens)
        if completion_tokens is not None
        else estimate_tokens(completion)
    )
    total_tokens = (
        int(total_tokens)
        if total_tokens is not None
        else prompt_tokens + completion_tokens
    )

    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


@contextmanager
def collect_llm_usage():
    records: list[dict] = []
    token = _active_usage_records.set(records)
    try:
        yield records
    finally:
        _active_usage_records.reset(token)


def record_llm_usage(
    *,
    model: str,
    call_type: str,
    prompt: str,
    completion: str,
    response=None,
    node_name: str | None = None,
    session_id: str | None = None,
    patient_id: str | None = None,
    status: str = "SUCCESS",
    latency_ms: int = 0,
):
    records = _active_usage_records.get()
    usage = usage_from_response(response, prompt, completion)
    if records is not None:
        records.append(
            {
                "model": model,
                "call_type": call_type,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "created_at": datetime.utcnow(),
                "node_name": node_name or call_type,
                "session_id": session_id,
                "patient_id": patient_id,
                "status": status,
                "latency_ms": latency_ms,
            }
        )

    if session_id and patient_id:
        persist_token_log(
            TokenLogRecord(
                session_id=str(session_id),
                patient_id=str(patient_id),
                node_name=str(node_name or call_type),
                model_name=str(model),
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                status=str(status),
                latency_ms=int(latency_ms),
            )
        )


def summarize_usage(records: list[dict]) -> dict:
    return {
        "input_tokens": sum(record["prompt_tokens"] for record in records),
        "output_tokens": sum(record["completion_tokens"] for record in records),
        "total_tokens": sum(record["total_tokens"] for record in records),
        "llm_calls": len(records),
    }


def ensure_llm_usage_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS chat_sessions (
                chat_session_id UUID PRIMARY KEY,
                patient_id TEXT NOT NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                llm_calls INTEGER NOT NULL DEFAULT 0,
                chat_summary TEXT NOT NULL DEFAULT '',
                started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            ALTER TABLE chat_sessions
                ADD COLUMN IF NOT EXISTS chat_summary TEXT NOT NULL DEFAULT '';

            CREATE TABLE IF NOT EXISTS llm_token_usage (
                usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                chat_session_id UUID NOT NULL REFERENCES chat_sessions(chat_session_id) ON DELETE CASCADE,
                patient_id TEXT NOT NULL,
                model TEXT NOT NULL,
                call_type TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_llm_token_usage_session_created
                ON llm_token_usage(chat_session_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_patient_updated
                ON chat_sessions(patient_id, updated_at);

            CREATE TABLE IF NOT EXISTS token_logs (
                session_id VARCHAR NOT NULL,
                patient_id VARCHAR NOT NULL,
                node_name VARCHAR NOT NULL,
                model_name VARCHAR NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                status VARCHAR NOT NULL CHECK (status IN ('SUCCESS', 'ERROR')),
                latency_ms INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_token_logs_session
                ON token_logs(session_id);
            CREATE INDEX IF NOT EXISTS idx_token_logs_patient
                ON token_logs(patient_id);
            """
        )


def _persist_token_log_sync(record: TokenLogRecord):
    with connect_db() as conn:
        ensure_llm_usage_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO token_logs (
                    session_id,
                    patient_id,
                    node_name,
                    model_name,
                    input_tokens,
                    output_tokens,
                    status,
                    latency_ms
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    record.session_id,
                    record.patient_id,
                    record.node_name,
                    record.model_name,
                    record.input_tokens,
                    record.output_tokens,
                    record.status,
                    record.latency_ms,
                ),
            )
        conn.commit()


async def persist_token_log_async(record: TokenLogRecord):
    await asyncio.to_thread(_persist_token_log_sync, record)


def persist_token_log(record: TokenLogRecord):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        threading.Thread(
            target=lambda: asyncio.run(persist_token_log_async(record)),
            daemon=True,
        ).start()
        return

    loop.create_task(persist_token_log_async(record))


def persist_chat_session_memory(
    *,
    patient_id: str,
    chat_session_id: str,
    chat_summary: str,
):
    with connect_db() as conn:
        ensure_llm_usage_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_sessions (
                    chat_session_id,
                    patient_id,
                    chat_summary
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (chat_session_id)
                DO UPDATE SET
                    patient_id = EXCLUDED.patient_id,
                    chat_summary = EXCLUDED.chat_summary,
                    updated_at = NOW();
                """,
                (
                    chat_session_id,
                    patient_id,
                    chat_summary or "",
                ),
            )
        conn.commit()


def load_chat_session_memory(
    *,
    patient_id: str,
    chat_session_id: str,
) -> str:
    with connect_db() as conn:
        ensure_llm_usage_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chat_summary
                FROM chat_sessions
                WHERE chat_session_id = %s
                    AND patient_id = %s
                LIMIT 1;
                """,
                (chat_session_id, patient_id),
            )
            row = cur.fetchone()

    if not row:
        return ""

    if isinstance(row, dict):
        return str(row.get("chat_summary") or "")
    return str(row[0] or "")


def persist_llm_usage_records(
    *,
    patient_id: str,
    chat_session_id: str,
    records: list[dict],
):
    if not records:
        return summarize_usage(records)

    summary = summarize_usage(records)
    with connect_db() as conn:
        ensure_llm_usage_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_sessions (
                    chat_session_id,
                    patient_id,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    llm_calls
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (chat_session_id)
                DO UPDATE SET
                    input_tokens = chat_sessions.input_tokens + EXCLUDED.input_tokens,
                    output_tokens = chat_sessions.output_tokens + EXCLUDED.output_tokens,
                    total_tokens = chat_sessions.total_tokens + EXCLUDED.total_tokens,
                    llm_calls = chat_sessions.llm_calls + EXCLUDED.llm_calls,
                    updated_at = NOW();
                """,
                (
                    chat_session_id,
                    patient_id,
                    summary["input_tokens"],
                    summary["output_tokens"],
                    summary["total_tokens"],
                    summary["llm_calls"],
                ),
            )
            cur.executemany(
                """
                INSERT INTO llm_token_usage (
                    chat_session_id,
                    patient_id,
                    model,
                    call_type,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                [
                    (
                        chat_session_id,
                        patient_id,
                        record["model"],
                        record["call_type"],
                        record["prompt_tokens"],
                        record["completion_tokens"],
                        record["total_tokens"],
                        record["created_at"],
                    )
                    for record in records
                ],
            )
        conn.commit()

    return summary
