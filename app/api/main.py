from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, appointments, auth, chat


app = FastAPI(title="Smart Hospital Portal")
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
