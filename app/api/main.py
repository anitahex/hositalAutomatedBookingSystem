from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, appointments, auth, chat

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
        conn = connect_db()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
            logger.info("startup: document catalog tables ensured")
        finally:
            conn.close()
    except Exception as exc:
        logger.error("startup: could not create document catalog tables: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_catalog_tables()
    yield


app = FastAPI(title="Smart Hospital Portal", lifespan=lifespan)
STATIC_DIR = Path(__file__).resolve().parent / "static"

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def portal_ui():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health_check():
    return {"status": "ok"}


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
