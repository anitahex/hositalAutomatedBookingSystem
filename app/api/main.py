from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, appointments, auth, chat, consult, doctor, whatsapp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
    force=True,
)

logger = logging.getLogger(__name__)

_SCHEMA_SQL = Path(__file__).resolve().parent.parent / "db" / "schema_document_catalog.sql"


def _ensure_catalog_tables() -> None:
    if not _SCHEMA_SQL.exists():
        logger.warning("startup: schema_document_catalog.sql not found at %s", _SCHEMA_SQL)
        return
    sql = _SCHEMA_SQL.read_text()
    try:
        from app.db.connection import connect_db
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
        logger.info("startup: document catalog tables ensured")
    except Exception as exc:
        logger.error("startup: could not create document catalog tables: %s", exc)


def _bootstrap_admin_account() -> None:
    from app.services.admin_auth import bootstrap_admin_from_env

    try:
        if bootstrap_admin_from_env():
            logger.info("startup: configured admin account synchronized")
    except Exception as exc:
        logger.error("startup: configured admin account could not be synchronized: %s", exc)
        raise


def _cleanup_stale_consult_audio_temp_files() -> None:
    """Crash-orphaned consult-audio-*.pcm temp files (a WS session that ended without
    reaching finalize_recording, e.g. a process crash) are never referenced by any
    consultations row, so they're always safe to delete once they're old enough that no
    session could still be legitimately writing to them."""
    from app.services.audio_storage import cleanup_stale_temp_files

    try:
        deleted = cleanup_stale_temp_files()
        if deleted:
            logger.info("startup: cleaned up %d stale consult audio temp file(s)", deleted)
    except Exception as exc:
        logger.error("startup: could not clean up stale consult audio temp files: %s", exc)


CONSULT_RETENTION_SWEEP_INTERVAL_SECONDS = int(os.getenv("CONSULT_RETENTION_SWEEP_INTERVAL_SECONDS", "3600"))


async def _consult_retention_sweep_loop() -> None:
    """No scheduler/cron mechanism existed anywhere in this codebase before this feature
    (checked: no APScheduler/Celery, no recurring asyncio loop in lifespan) — this is new
    infrastructure, kept intentionally simple (a plain asyncio loop) rather than adding a
    new dependency for a single periodic job."""
    from app.services.consults import (
        retry_stuck_transcriptions, run_retention_sweep, sweep_stale_recording_consults,
    )

    while True:
        try:
            await asyncio.sleep(CONSULT_RETENTION_SWEEP_INTERVAL_SECONDS)
            deleted = await run_retention_sweep()
            if deleted:
                logger.info("consult retention sweep: deleted audio for %d consultation(s)", deleted)

            # Safety net: force-end any consult stuck in 'recording' far longer than any
            # real visit would take, regardless of why (crashed handler, a connection
            # that neither side ever cleanly closed, etc.) — see sweep_stale_recording_consults's
            # own docstring for why this doesn't just rely on Deepgram/websockets ping-pong.
            stale = sweep_stale_recording_consults()
            if stale:
                logger.warning("consult stale-recording sweep: force-ended %d stuck consultation(s)", stale)

            # Safety net for the symmetric case: a consult stuck in 'ended'/'transcribing'
            # because batch re-transcription never got a chance to reach its own
            # terminal-state guarantee (e.g. a process crash between end_consult() and
            # its scheduled task actually running) — see retry_stuck_transcriptions.
            retried = await retry_stuck_transcriptions()
            if retried:
                logger.warning("consult stuck-transcription retry: re-attempted %d consultation(s)", retried)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("consult retention sweep failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_catalog_tables()
    _bootstrap_admin_account()
    _cleanup_stale_consult_audio_temp_files()
    sweep_task = asyncio.create_task(_consult_retention_sweep_loop())
    try:
        yield
    finally:
        sweep_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sweep_task
        from app.db.connection import close_db_pool
        close_db_pool()


# Interactive API docs (/docs, /redoc) expose the full request/response schema,
# including admin-only models — disabled by default (FULL_SYSTEM_AUDIT.md P1 #15).
# Set ENABLE_API_DOCS=true for local development only.
_ENABLE_API_DOCS = os.getenv("ENABLE_API_DOCS", "false").strip().lower() in {"1", "true", "yes"}

app = FastAPI(
    title="Smart Hospital Portal",
    lifespan=lifespan,
    docs_url="/docs" if _ENABLE_API_DOCS else None,
    redoc_url="/redoc" if _ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if _ENABLE_API_DOCS else None,
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(whatsapp.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(doctor.router, prefix="/doctor", tags=["doctor"])
app.include_router(consult.router, prefix="/doctor/consult", tags=["consult"])


@app.get("/health")
def health_check():
    return {"status": "ok"}


_STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/")
def serve_index():
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/doctor/set-password")
def serve_doctor_set_password():
    return FileResponse(_STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


# ---- WebSocket connection manager ----
# Keyed by session_id; supports multiple concurrent connections per session
# (e.g. multiple browser tabs). Ingestion background workers import and use
# this manager to broadcast document status events.

class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(session_id, []).append(websocket)
        logger.info("ws: session_id=%s connected (%d sockets)", session_id, len(self._connections[session_id]))

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        sockets = self._connections.get(session_id, [])
        if websocket in sockets:
            sockets.remove(websocket)
        if not sockets:
            self._connections.pop(session_id, None)
        logger.info("ws: session_id=%s disconnected", session_id)

    async def broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        """
        Send a JSON message to all sockets for a session.
        Removes stale connections silently.
        """
        sockets = list(self._connections.get(session_id, []))
        if not sockets:
            logger.debug("ws: no live sockets for session_id=%s — message not delivered", session_id)
            return
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.warning("ws: send failed for session_id=%s: %s", session_id, exc)
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)


connection_manager = ConnectionManager()


@app.websocket("/ws/status/{session_id}")
async def document_status_ws(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket endpoint for document ingestion status notifications.

    Clients connect here after calling /chat/confirm-processing. The
    background ingestion worker broadcasts 'complete' or 'error' events.

    If the client connects AFTER ingestion already finished, it can poll
    GET /chat/document-status/{document_id} to get the persisted status
    from the Postgres catalog rather than relying solely on this live event.

    Event shapes:
      {"status": "complete", "document_id": "...", "message": "..."}
      {"status": "error",    "error": "..."}
    """
    await connection_manager.connect(session_id, websocket)
    logger.info("ws: /ws/status/%s opened", session_id)
    try:
        while True:
            # Keep connection alive; server pushes; client sends nothing.
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("ws: /ws/status/%s closed by client", session_id)
    finally:
        connection_manager.disconnect(session_id, websocket)
