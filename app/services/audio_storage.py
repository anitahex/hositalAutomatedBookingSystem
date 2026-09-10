"""Backend-agnostic storage for consult audio recordings.

Two backends, selected via AUDIO_STORAGE_BACKEND (default "local", read once at import
time like every other env-driven constant in this codebase):
  - "local": writes to a persistent directory outside app/api/static — StaticFiles only
    serves that one directory, so anything outside it is never publicly reachable.
  - "azure": uploads to Azure Blob Storage via blob_storage.py. That code is kept
    exactly as it was (not discarded) so this backend can be flipped on later without
    rewriting anything, once a subscription is available.

Recording flow: the consult WebSocket route writes incoming audio chunks incrementally
to a local temp file as they arrive (never buffered fully in memory), then calls
finalize_recording() once at session end to hand the completed file to whichever
backend is active. This means the "local" backend has no extra upload step at all —
finalizing a local recording is just moving the temp file into permanent storage.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)

AUDIO_STORAGE_BACKEND = os.getenv("AUDIO_STORAGE_BACKEND", "local").strip().lower()

# Repo-root/var/consult_audio by default — sibling to app/, never under app/api/static
# (the only directory StaticFiles serves publicly).
_DEFAULT_LOCAL_DIR = Path(__file__).resolve().parent.parent.parent / "var" / "consult_audio"
LOCAL_AUDIO_DIR = Path(os.getenv("AUDIO_STORAGE_LOCAL_DIR", str(_DEFAULT_LOCAL_DIR)))

CONSULT_AUDIO_TEMP_MAX_AGE_HOURS = float(os.getenv("CONSULT_AUDIO_TEMP_MAX_AGE_HOURS", "6"))

# Owner read/write/execute only — this directory holds raw, unencrypted patient audio.
# Enforced both via mkdir's mode= AND an explicit chmod: on POSIX, mkdir's mode is still
# subject to the process umask, so a belt-and-suspenders chmod guarantees the final bits
# regardless of umask. On Windows this mode is a no-op (Windows has no POSIX permission
# bits) — real enforcement only happens on the Linux containers this actually deploys to
# (confirmed via Dockerfile/docker-compose.yml), which is fine since dev-machine access
# control isn't the threat model here.
_PRIVATE_DIR_MODE = 0o700


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=_PRIVATE_DIR_MODE)
    try:
        os.chmod(path, _PRIVATE_DIR_MODE)
    except OSError as exc:
        logger.warning("audio_storage: could not chmod %s to 0700: %s", path, exc)


def open_recording_tempfile() -> tuple[BinaryIO, str]:
    """Opens a local temp file for incremental writes during an active recording
    session, regardless of which backend is active — even the azure backend stages the
    recording on local disk first, then uploads the completed file once at the end.
    Returns (file_handle, temp_path); write chunks to file_handle as they arrive and
    pass temp_path to finalize_recording() once, at session end."""
    _ensure_private_dir(LOCAL_AUDIO_DIR)
    fd, temp_path = tempfile.mkstemp(prefix="consult-audio-", suffix=".pcm", dir=str(LOCAL_AUDIO_DIR))
    os.chmod(temp_path, 0o600)
    handle = os.fdopen(fd, "wb")
    return handle, temp_path


def cleanup_stale_temp_files(max_age_hours: float | None = None) -> int:
    """Deletes crash-orphaned consult-audio-*.pcm temp files older than max_age_hours.
    A temp file this old was never finalized (the process ended before finalize_recording
    ran) and is safe to discard — no consultations row ever got an audio_blob_path
    pointing at it, since that's only set after finalize_recording succeeds. Runs
    regardless of which backend is active, since temp files always land here first."""
    max_age = CONSULT_AUDIO_TEMP_MAX_AGE_HOURS if max_age_hours is None else max_age_hours
    if not LOCAL_AUDIO_DIR.exists():
        return 0

    cutoff = time.time() - (max_age * 3600)
    deleted = 0
    for entry in LOCAL_AUDIO_DIR.glob("consult-audio-*.pcm"):
        try:
            if entry.is_file() and entry.stat().st_mtime < cutoff:
                entry.unlink()
                deleted += 1
        except OSError as exc:
            logger.warning("audio_storage: could not remove stale temp file %s: %s", entry, exc)

    if deleted:
        logger.info("audio_storage: cleaned up %d stale crash-orphaned temp recording(s)", deleted)
    return deleted


def _discard_temp_file(temp_path: str) -> None:
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except OSError as exc:
            logger.warning("audio_storage: could not remove temp file %s: %s", temp_path, exc)


async def finalize_recording(temp_path: str, *, doctor_id: str, consultation_id: str) -> str | None:
    """Hands a completed local recording off to the active backend. Returns the storage
    reference to persist as consultations.audio_blob_path, or None if there was nothing
    to store (e.g. a zero-byte file — the session ended before any audio arrived)."""
    if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
        _discard_temp_file(temp_path)
        return None

    if AUDIO_STORAGE_BACKEND == "azure":
        from app.services.blob_storage import consult_audio_blob_path, upload_blob

        blob_path = consult_audio_blob_path(doctor_id, consultation_id)
        try:
            with open(temp_path, "rb") as f:
                data = f.read()
            await upload_blob(blob_path, data, content_type="application/octet-stream")
            return blob_path
        finally:
            _discard_temp_file(temp_path)

    # local backend: "uploading" is just moving the temp file into permanent storage.
    dest_dir = LOCAL_AUDIO_DIR / doctor_id
    _ensure_private_dir(dest_dir)
    dest_path = dest_dir / f"{consultation_id}.pcm"
    shutil.move(temp_path, dest_path)
    os.chmod(dest_path, 0o600)
    return str(dest_path)


async def download_audio(storage_ref: str) -> bytes:
    if AUDIO_STORAGE_BACKEND == "azure":
        from app.services.blob_storage import download_blob
        return await download_blob(storage_ref)

    with open(storage_ref, "rb") as f:
        return f.read()


async def delete_audio(storage_ref: str) -> None:
    """Deletes a stored recording; silently ignores an already-missing file/blob,
    matching blob_storage.delete_blob's idempotent behavior."""
    if AUDIO_STORAGE_BACKEND == "azure":
        from app.services.blob_storage import delete_blob
        await delete_blob(storage_ref)
        return

    try:
        os.remove(storage_ref)
        logger.info("audio_storage: deleted local recording %s", storage_ref)
    except FileNotFoundError:
        logger.debug("audio_storage: local recording not found (already deleted?) — %s", storage_ref)
