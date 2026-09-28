"""Backend-agnostic read access to stored patient documents.

Mirrors audio_storage.py's two-backend design exactly, because the problem is the same
one: clinical files that must be readable whether this deployment keeps them in Azure
Blob Storage or on the server's own filesystem.

Backend is selected via DOCUMENT_STORAGE_BACKEND, read once at import time like every
other env-driven constant in this codebase.

  - "azure" (DEFAULT): reads through blob_storage.py. This is the default deliberately,
    NOT to match audio_storage's "local" default: the patient document upload path in
    chat.py writes to Azure today, so every document that currently exists lives there.
    Defaulting this module to "local" would leave every one of them unreadable.
  - "local": reads from LOCAL_DOCUMENT_DIR on disk.

THE PATH LAYOUT IS IDENTICAL IN BOTH BACKENDS. The relative path persisted in
document_catalog.blob_summary_path (and the vault path built the same way) is used
verbatim — as a blob name against Azure, or as a path under LOCAL_DOCUMENT_DIR on disk:

    summaries/{user_id}/{document_id}.json
    vault/{user_id}/{session_id}/{document_id}/{filename}

That symmetry is the point: switching backends is one environment variable, and moving a
deployment between them is a plain directory copy rather than a rewrite of every stored
path in the database.

SCOPE — reads only. chat.py still writes uploads directly to Azure Blob Storage; it has
not been routed through this module. Until it is, setting DOCUMENT_STORAGE_BACKEND=local
gives you a backend that can read local files but nothing that writes them. See the
follow-up noted where this module is used.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DOCUMENT_STORAGE_BACKEND = os.getenv("DOCUMENT_STORAGE_BACKEND", "azure").strip().lower()

# Repo-root/var/patient_documents by default — a sibling of app/, never under
# app/api/static (the only directory StaticFiles serves publicly), so a stored clinical
# document can never become reachable over HTTP just by guessing its filename.
_DEFAULT_LOCAL_DIR = Path(__file__).resolve().parent.parent.parent / "var" / "patient_documents"
LOCAL_DOCUMENT_DIR = Path(os.getenv("DOCUMENT_STORAGE_LOCAL_DIR", str(_DEFAULT_LOCAL_DIR)))

# Owner read/write/execute only — this directory holds raw, unencrypted patient
# documents. Same rationale and the same Windows caveat as audio_storage's
# _PRIVATE_DIR_MODE: enforcement is real only on the Linux containers this deploys to.
_PRIVATE_DIR_MODE = 0o700


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=_PRIVATE_DIR_MODE)
    try:
        os.chmod(path, _PRIVATE_DIR_MODE)
    except OSError as exc:
        logger.warning("document_storage: could not chmod %s to 0700: %s", path, exc)


def resolve_local_path(relative_path: str) -> Path:
    """Maps a stored relative path to a real path under LOCAL_DOCUMENT_DIR, refusing
    anything that would escape it.

    The stored path originates from blob_storage.sanitize_filename, so it is not
    attacker-controlled in the normal flow — but it is read back out of the database and
    joined onto a filesystem root, which is exactly the shape of a path-traversal bug.
    The guard is therefore unconditional rather than trusting that provenance: an
    absolute path, a drive letter, or any number of '..' segments all resolve outside the
    root and are rejected before any file is opened.
    """
    if not relative_path or not relative_path.strip():
        raise ValueError("A document path is required.")

    root = LOCAL_DOCUMENT_DIR.resolve()
    candidate = (root / relative_path).resolve()

    if candidate != root and root not in candidate.parents:
        # Deliberately does not echo the offending path back to the caller — it would
        # end up in an API error body and a log line, disclosing server filesystem
        # layout. The document_id the caller asked for is logged by the caller instead.
        raise PermissionError("Resolved document path escapes the document storage root.")

    return candidate


async def read_document_bytes(relative_path: str) -> bytes:
    """Raises FileNotFoundError if the document is not present in the active backend,
    matching blob_storage.download_blob's contract so callers handle one error shape."""
    if DOCUMENT_STORAGE_BACKEND == "local":
        path = resolve_local_path(relative_path)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Document not found: {relative_path}") from exc

    from app.services.blob_storage import download_blob

    return await download_blob(relative_path)


async def read_document_json(relative_path: str) -> dict[str, Any]:
    """Raises FileNotFoundError if absent, RuntimeError if the stored bytes are not valid
    JSON — a corrupt summary must fail loudly rather than surface to a clinician as an
    empty or half-populated document.

    RuntimeError (not ValueError) deliberately: it matches blob_storage's own failure
    type for a download that came back unusable, and it keeps a storage-layer fault
    distinguishable from the caller's ValueError for "no such document", which routes
    map to entirely different status codes.
    """
    if DOCUMENT_STORAGE_BACKEND == "local":
        raw = await read_document_bytes(relative_path)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Stored document summary is not valid JSON: {relative_path}") from exc

    from app.services.blob_storage import download_blob_json

    return await download_blob_json(relative_path)


def ensure_local_root() -> Path:
    """Creates the local document root with restrictive permissions. Safe to call
    regardless of the active backend; only meaningful for the local one."""
    _ensure_private_dir(LOCAL_DOCUMENT_DIR)
    return LOCAL_DOCUMENT_DIR
