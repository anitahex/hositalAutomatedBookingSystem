"""Document upload / consent-gating coverage (Part: full-stack-through-the-service-layer).

Same convention as test_consult_routes.py and test_doctor_appointments.py: call the
route functions directly (no TestClient), monkeypatch the service layer (blob storage,
the GPT-4o relevance guardrail) so no real Azure/OpenAI network calls happen, and assert
on the route's orchestration.

/chat/upload and /chat/confirm-processing (app/api/routes/chat.py) take a raw
`Request`/`BackgroundTasks` rather than a typed Pydantic body for the upload route, so
this file uses small duck-typed fakes (FakeUploadFile / FakeRequest) standing in for
Starlette's UploadFile/Request — upload_document() only ever calls `.filename`,
`.content_type` and `await .read()` on the file, and `await request.form()` on the
request, so real Starlette objects are unnecessary.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.routes import chat as chat_route
from app.services.document_pipeline import ALLOWED_UPLOAD_MIME_TYPES


# ── Fakes standing in for Starlette's UploadFile / Request ──────────────────────

class FakeUploadFile:
    def __init__(self, filename: str, content_type: str, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self._data = data

    async def read(self) -> bytes:
        return self._data


class FakeRequest:
    def __init__(self, form_data: dict):
        self._form_data = form_data

    async def form(self) -> dict:
        return self._form_data


def _user(patient_id="patient-1"):
    return {"patient_id": patient_id, "name": "Test Patient"}


# ── Valid upload succeeds ────────────────────────────────────────────────────

def test_valid_pdf_upload_succeeds_and_returns_expected_shape(monkeypatch):
    seen_upload_blob = {}
    seen_save_pending = {}

    async def fake_relevance_check(*, mime_type, file_bytes, extracted_text):
        return True

    async def fake_upload_blob(blob_path, data, content_type="application/octet-stream"):
        seen_upload_blob["blob_path"] = blob_path
        seen_upload_blob["content_type"] = content_type

    def fake_save_pending_upload(*, document_token, user_id, session_id, document_id, blob_path, original_filename):
        seen_save_pending.update(
            document_token=document_token, user_id=user_id, session_id=session_id,
            document_id=document_id, blob_path=blob_path, original_filename=original_filename,
        )

    monkeypatch.setattr("app.inference.azure_client.gpt4o_relevance_check", fake_relevance_check)
    monkeypatch.setattr(chat_route, "upload_blob", fake_upload_blob)
    monkeypatch.setattr(chat_route, "save_pending_upload", fake_save_pending_upload)

    request = FakeRequest({
        "file": FakeUploadFile("report.pdf", "application/pdf", b"%PDF-1.4 fake medical report content"),
        "session_id": "session-1",
    })

    result = asyncio.run(chat_route.upload_document(request, user=_user("patient-1")))

    assert result["requires_consent"] is True
    assert isinstance(result["document_token"], str) and result["document_token"]
    assert "message" in result

    assert seen_save_pending["user_id"] == "patient-1"
    assert seen_save_pending["session_id"] == "session-1"
    assert seen_save_pending["original_filename"] == "report.pdf"
    assert seen_save_pending["document_token"] == result["document_token"]
    # staging path is built from the (mocked-out) document_id, not user-controlled input
    assert seen_upload_blob["blob_path"].startswith("staging/patient-1/")
    assert seen_upload_blob["content_type"] == "application/pdf"


def test_valid_jpeg_upload_succeeds(monkeypatch):
    monkeypatch.setattr(
        "app.inference.azure_client.gpt4o_relevance_check",
        _async_true,
    )
    monkeypatch.setattr(chat_route, "upload_blob", _async_noop)
    monkeypatch.setattr(chat_route, "save_pending_upload", lambda **kwargs: None)

    request = FakeRequest({
        "file": FakeUploadFile("xray.jpg", "image/jpeg", b"\xff\xd8\xff\xe0fakejpegbytes"),
        "session_id": "session-1",
    })

    result = asyncio.run(chat_route.upload_document(request, user=_user()))
    assert result["requires_consent"] is True
    assert result["document_token"]


def test_valid_png_upload_succeeds(monkeypatch):
    monkeypatch.setattr(
        "app.inference.azure_client.gpt4o_relevance_check",
        _async_true,
    )
    monkeypatch.setattr(chat_route, "upload_blob", _async_noop)
    monkeypatch.setattr(chat_route, "save_pending_upload", lambda **kwargs: None)

    request = FakeRequest({
        "file": FakeUploadFile("scan.png", "image/png", b"\x89PNGfakepngbytes"),
        "session_id": "session-1",
    })

    result = asyncio.run(chat_route.upload_document(request, user=_user()))
    assert result["requires_consent"] is True
    assert result["document_token"]


async def _async_true(*, mime_type, file_bytes, extracted_text):
    return True


async def _async_noop(blob_path, data, content_type="application/octet-stream"):
    return None


# ── Oversized file is rejected ───────────────────────────────────────────────

def test_oversized_file_is_rejected_with_400():
    """15 MB is the exact cap enforced in upload_document() (`len(file_bytes) > 15 * 1024 * 1024`)."""
    oversized = b"0" * (15 * 1024 * 1024 + 1)
    request = FakeRequest({
        "file": FakeUploadFile("big.pdf", "application/pdf", oversized),
        "session_id": "session-1",
    })

    with pytest.raises(HTTPException) as exc:
        asyncio.run(chat_route.upload_document(request, user=_user()))

    assert exc.value.status_code == 400
    assert "too large" in exc.value.detail.lower()


def test_file_at_exactly_the_cap_is_not_rejected_for_size(monkeypatch):
    """Boundary check: exactly 15 MB must NOT trip the oversized branch (`>`, not `>=`)."""
    monkeypatch.setattr("app.inference.azure_client.gpt4o_relevance_check", _async_true)
    monkeypatch.setattr(chat_route, "upload_blob", _async_noop)
    monkeypatch.setattr(chat_route, "save_pending_upload", lambda **kwargs: None)

    exactly_cap = b"0" * (15 * 1024 * 1024)
    request = FakeRequest({
        "file": FakeUploadFile("report.pdf", "application/pdf", exactly_cap),
        "session_id": "session-1",
    })

    result = asyncio.run(chat_route.upload_document(request, user=_user()))
    assert result["requires_consent"] is True


# ── Wrong MIME type is rejected ──────────────────────────────────────────────

def test_wrong_mime_type_is_rejected_with_400():
    assert "text/plain" not in ALLOWED_UPLOAD_MIME_TYPES  # pin the assumption we're testing
    request = FakeRequest({
        "file": FakeUploadFile("notes.txt", "text/plain", b"just some text"),
        "session_id": "session-1",
    })

    with pytest.raises(HTTPException) as exc:
        asyncio.run(chat_route.upload_document(request, user=_user()))

    assert exc.value.status_code == 400
    assert "PDF and JPEG/PNG" in exc.value.detail


def test_missing_file_is_rejected_with_400():
    request = FakeRequest({"session_id": "session-1"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(chat_route.upload_document(request, user=_user()))
    assert exc.value.status_code == 400


def test_gpt4o_relevance_check_rejecting_the_document_returns_400(monkeypatch):
    async def fake_relevance_check(*, mime_type, file_bytes, extracted_text):
        return False

    monkeypatch.setattr("app.inference.azure_client.gpt4o_relevance_check", fake_relevance_check)

    request = FakeRequest({
        "file": FakeUploadFile("vacation.jpg", "image/jpeg", b"\xff\xd8\xff\xe0notmedical"),
        "session_id": "session-1",
    })

    with pytest.raises(HTTPException) as exc:
        asyncio.run(chat_route.upload_document(request, user=_user()))

    assert exc.value.status_code == 400
    assert "medical" in exc.value.detail.lower()


# ── /chat/confirm-processing: consent flow moves staged upload to committed storage ──

def _pending_record(**overrides):
    record = {
        "user_id": "patient-1",
        "session_id": "session-1",
        "document_id": "doc-1",
        "blob_path": "staging/patient-1/doc-1/report.pdf",
        "original_filename": "report.pdf",
    }
    record.update(overrides)
    return record


def test_confirm_processing_with_consent_moves_blob_and_queues_ingestion(monkeypatch):
    seen_move = {}

    monkeypatch.setattr(chat_route, "consume_pending_upload", lambda token: _pending_record())

    async def fake_move_blob(source_path, dest_path):
        seen_move["source_path"] = source_path
        seen_move["dest_path"] = dest_path

    monkeypatch.setattr(chat_route, "move_blob", fake_move_blob)

    background_tasks = BackgroundTasks()
    request = chat_route.ConfirmProcessingRequest(document_token="tok-1", consent_granted=True)

    result = asyncio.run(chat_route.confirm_processing(request, background_tasks, user=_user()))

    assert result["status"] == "processing"
    assert result["document_id"] == "doc-1"

    # The route's orchestration, not real blob I/O: it must move the staged blob to a
    # vault path built from the *server-side* record, not any client-supplied path.
    assert seen_move["source_path"] == "staging/patient-1/doc-1/report.pdf"
    assert seen_move["dest_path"].startswith("vault/patient-1/session-1/doc-1/")

    # A background ingestion task must be queued for the moved document.
    assert len(background_tasks.tasks) == 1
    task = background_tasks.tasks[0]
    assert task.func is chat_route._run_ingestion_pipeline
    assert task.kwargs["document_id"] == "doc-1"
    assert task.kwargs["vault_path"] == seen_move["dest_path"]


def test_confirm_processing_without_consent_deletes_staged_blob_and_skips_ingestion(monkeypatch):
    seen_delete = {}

    monkeypatch.setattr(chat_route, "consume_pending_upload", lambda token: _pending_record())

    async def fake_delete_blob(blob_path):
        seen_delete["blob_path"] = blob_path

    monkeypatch.setattr(chat_route, "delete_blob", fake_delete_blob)

    def fail_if_moved(*args, **kwargs):
        raise AssertionError("move_blob must not be called when consent is declined.")

    monkeypatch.setattr(chat_route, "move_blob", fail_if_moved)

    background_tasks = BackgroundTasks()
    request = chat_route.ConfirmProcessingRequest(document_token="tok-1", consent_granted=False)

    result = asyncio.run(chat_route.confirm_processing(request, background_tasks, user=_user()))

    assert result["status"] == "cancelled"
    assert seen_delete["blob_path"] == "staging/patient-1/doc-1/report.pdf"
    assert len(background_tasks.tasks) == 0


def test_confirm_processing_rejects_missing_or_expired_or_reused_token(monkeypatch):
    monkeypatch.setattr(chat_route, "consume_pending_upload", lambda token: None)

    background_tasks = BackgroundTasks()
    request = chat_route.ConfirmProcessingRequest(document_token="bogus-token", consent_granted=True)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(chat_route.confirm_processing(request, background_tasks, user=_user()))

    assert exc.value.status_code == 410


# ── Characterization: an uploaded-but-never-confirmed document has no cleanup path ──
#
# app/db/schema_document_catalog.sql documents the intended TTL in a COMMENT
# ("DELETE FROM pending_uploads WHERE created_at < NOW() - INTERVAL '30 minutes'")
# but nothing in the codebase ever executes that query or an equivalent one: unlike
# consult audio (app/services/consults.py: run_retention_sweep(),
# sweep_stale_recording_consults(), both wired into a periodic loop in app/api/main.py
# _consult_retention_sweep_loop), there is no scheduled task, cron, or route that sweeps
# expired/unconsumed pending_uploads rows or their orphaned staging/ blobs.
# consume_pending_upload() only *reads* rows (WHERE consumed = FALSE AND created_at >
# NOW() - INTERVAL '30 minutes') so an expired token is simply never returned again —
# the row (and its staged blob) is left behind forever. This test pins that gap down so
# it fails loudly (rather than the report silently going stale) the day someone adds a
# real sweep.

def test_no_automatic_cleanup_exists_for_expired_or_orphaned_pending_uploads():
    import app.api.main as main_module
    import app.services.document_catalog as document_catalog_module

    # No sweep/cleanup function for pending_uploads exists anywhere in the service layer.
    assert not hasattr(document_catalog_module, "sweep_pending_uploads")
    assert not hasattr(document_catalog_module, "cleanup_expired_uploads")
    assert not any(
        "pending_upload" in name.lower() and ("sweep" in name.lower() or "cleanup" in name.lower() or "expire" in name.lower())
        for name in dir(document_catalog_module)
    )

    # main.py's startup wires exactly one periodic sweep loop (consult retention /
    # stale-recording), and it has nothing to do with pending_uploads.
    assert hasattr(main_module, "_consult_retention_sweep_loop")
    assert not hasattr(main_module, "_pending_upload_sweep_loop")
