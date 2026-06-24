"""
Azure Blob Storage service — raw file vault + extracted summary storage.

Blob layout:
  Staged (pre-consent):  {container}/staging/{user_id}/{document_id}/{filename}
  Vault (confirmed):     {container}/vault/{user_id}/{session_id}/{document_id}/{filename}
  Summary JSON:          {container}/summaries/{user_id}/{document_id}.json
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "hospital-documents")

try:
    from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
    from azure.storage.blob import ContentSettings
    from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
    _HAS_AZURE_BLOB = True
except ImportError:
    AsyncBlobServiceClient = None  # type: ignore[assignment, misc]
    ContentSettings = None  # type: ignore[assignment, misc]
    ResourceExistsError = Exception  # type: ignore[assignment, misc]
    ResourceNotFoundError = OSError  # type: ignore[assignment, misc]
    _HAS_AZURE_BLOB = False


def _get_blob_service_client() -> "AsyncBlobServiceClient":
    if not _HAS_AZURE_BLOB:
        raise RuntimeError(
            "azure-storage-blob is not installed. Run: pip install azure-storage-blob"
        )
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise RuntimeError(
            "Azure Blob Storage is not configured. Set AZURE_STORAGE_CONNECTION_STRING in .env."
        )
    return AsyncBlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)


# ---- Path builders ----

def sanitize_filename(filename: str) -> str:
    """Strip path separators and unsafe chars; keep extension."""
    name = os.path.basename(filename or "upload")
    name = re.sub(r"[^\w.\-]", "_", name)
    return name[:200] or "upload"


def staging_blob_path(user_id: str, document_id: str, filename: str) -> str:
    return f"staging/{user_id}/{document_id}/{sanitize_filename(filename)}"


def vault_blob_path(user_id: str, session_id: str, document_id: str, filename: str) -> str:
    return f"vault/{user_id}/{session_id}/{document_id}/{sanitize_filename(filename)}"


def summary_blob_path(user_id: str, document_id: str) -> str:
    return f"summaries/{user_id}/{document_id}.json"


# ---- Blob operations ----

async def _ensure_container(container_client) -> None:
    """Create the container if it does not already exist."""
    try:
        await container_client.create_container()
        logger.info("blob_storage: container '%s' created", AZURE_CONTAINER_NAME)
    except ResourceExistsError:
        pass  # Already exists — normal path after first upload


async def upload_blob(
    blob_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    """Upload raw bytes to the configured container, creating it if needed."""
    async with _get_blob_service_client() as svc:
        container = svc.get_container_client(AZURE_CONTAINER_NAME)
        await _ensure_container(container)
        blob = container.get_blob_client(blob_name)
        logger.info("blob_storage: uploading %d bytes → %s", len(data), blob_name)
        await blob.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        logger.info("blob_storage: upload complete — %s", blob_name)


async def upload_json_blob(blob_name: str, payload: dict[str, Any]) -> None:
    """Serialize a dict as UTF-8 JSON and upload."""
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    await upload_blob(blob_name, data, content_type="application/json")


async def download_blob_json(blob_name: str) -> dict[str, Any]:
    """
    Download and parse a JSON blob.
    Raises FileNotFoundError if the blob does not exist.
    Raises RuntimeError on other download failures.
    """
    async with _get_blob_service_client() as svc:
        container = svc.get_container_client(AZURE_CONTAINER_NAME)
        blob = container.get_blob_client(blob_name)
        try:
            logger.info("blob_storage: downloading JSON ← %s", blob_name)
            stream = await blob.download_blob()
            raw = await stream.readall()
            return json.loads(raw.decode("utf-8"))
        except ResourceNotFoundError as exc:
            raise FileNotFoundError(f"Blob not found: {blob_name}") from exc
        except Exception as exc:
            logger.error("blob_storage: download failed for %s: %s", blob_name, exc)
            raise RuntimeError(f"Failed to download blob {blob_name}: {exc}") from exc


async def move_blob(source_path: str, dest_path: str) -> None:
    """
    Copy a blob to dest_path then delete the source.
    Azure Blob Storage has no native atomic move; this is a copy-then-delete.
    """
    async with _get_blob_service_client() as svc:
        container = svc.get_container_client(AZURE_CONTAINER_NAME)
        src_blob = container.get_blob_client(source_path)
        dst_blob = container.get_blob_client(dest_path)

        logger.info("blob_storage: copying %s → %s", source_path, dest_path)
        await dst_blob.start_copy_from_url(src_blob.url)
        logger.info("blob_storage: deleting source %s", source_path)
        await src_blob.delete_blob()
        logger.info("blob_storage: move complete")


async def delete_blob(blob_name: str) -> None:
    """Delete a blob; silently ignores 404 (already deleted)."""
    async with _get_blob_service_client() as svc:
        container = svc.get_container_client(AZURE_CONTAINER_NAME)
        blob = container.get_blob_client(blob_name)
        try:
            await blob.delete_blob()
            logger.info("blob_storage: deleted %s", blob_name)
        except ResourceNotFoundError:
            logger.debug("blob_storage: blob not found (already deleted?) — %s", blob_name)
        except Exception as exc:
            logger.warning("blob_storage: could not delete %s: %s", blob_name, exc)
