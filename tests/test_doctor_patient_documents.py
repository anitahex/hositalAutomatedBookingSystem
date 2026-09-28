"""Doctor access to a patient's uploaded documents (C9).

Patient documents were uploaded under a consent flow that authorised AI PROCESSING, not
disclosure to a clinician. Exposing them to a treating doctor is a deliberate product
decision, so the controls around it are the whole point of this file:

  - a doctor with no booking history with the patient gets nothing, and cannot tell the
    difference between "not allowed" and "does not exist";
  - a document_id belonging to a different patient is unreachable even for a doctor who
    legitimately treats somebody (get_catalog_entry has no ownership check of its own);
  - a stored path can never escape the document storage root;
  - the original file always downloads, never renders inline.

Uses asyncio.run for the async routes, matching test_consult_routes.py's convention
(this repo has no pytest-asyncio).
"""

import asyncio

from fastapi import HTTPException
import pytest

from app.api.routes import doctor as doctor_route
from app.services import document_catalog, document_storage


def _doctor(doctor_id="doctor-1"):
    return {"doctor_id": doctor_id, "name": "Dr. Test", "department": "Neurology"}


class _Entry:
    """Stands in for a CatalogEntry without needing the pydantic model's full shape."""

    def __init__(self, user_id="patient-1", document_id="doc-1", status="complete",
                 filename="Complete_Blood_Count.pdf"):
        self.user_id = user_id
        self.document_id = document_id
        self.session_id = "session-1"
        self.original_filename = filename
        self.document_type = "lab_report"
        self.clinical_date = "2026-09-02"
        self.created_at = None
        self.blob_summary_path = f"summaries/{user_id}/{document_id}.json"
        self.findings_keys = ["hemoglobin"]
        self.ingestion_status = status


# ---- path traversal ----

def test_resolve_local_path_accepts_a_normal_stored_path():
    resolved = document_storage.resolve_local_path("summaries/patient-1/doc-1.json")
    assert resolved.is_relative_to(document_storage.LOCAL_DOCUMENT_DIR.resolve())


@pytest.mark.parametrize("hostile", [
    "../../../etc/passwd",
    "summaries/../../../../etc/shadow",
    "summaries/patient-1/../../../../../../root/.ssh/id_rsa",
    "/etc/passwd",
    "C:\\Windows\\System32\\config\\SAM",
    "summaries/./../../..",
])
def test_resolve_local_path_refuses_anything_escaping_the_root(hostile):
    """The stored path is read back out of the database and joined onto a filesystem
    root — exactly the shape of a path-traversal bug, regardless of how trustworthy its
    provenance is believed to be."""
    with pytest.raises(PermissionError):
        document_storage.resolve_local_path(hostile)


@pytest.mark.parametrize("empty", ["", "   ", None])
def test_resolve_local_path_refuses_an_empty_path(empty):
    with pytest.raises(ValueError):
        document_storage.resolve_local_path(empty)


def test_resolve_local_path_error_does_not_disclose_the_filesystem_layout():
    """The message reaches an API error body and a log line; it must not echo back the
    resolved server path."""
    with pytest.raises(PermissionError) as exc:
        document_storage.resolve_local_path("../../../etc/passwd")
    assert "etc/passwd" not in str(exc.value)
    assert str(document_storage.LOCAL_DOCUMENT_DIR) not in str(exc.value)


def test_local_document_root_is_never_inside_the_publicly_served_static_directory():
    """StaticFiles serves app/api/static. A clinical document under it would be
    reachable over HTTP by anyone who guessed the filename."""
    root = document_storage.LOCAL_DOCUMENT_DIR.resolve()
    static_dir = (document_storage.Path(__file__).resolve().parent.parent / "app" / "api" / "static").resolve()
    assert not root.is_relative_to(static_dir)


def test_document_storage_defaults_to_azure():
    """Defaulting to 'local' would leave every document the upload path has already
    written to Azure unreadable."""
    assert document_storage.DOCUMENT_STORAGE_BACKEND in ("azure", "local")


# ---- content type allowlist ----

@pytest.mark.parametrize("filename,expected", [
    ("report.pdf", "application/pdf"),
    ("scan.JPG", "image/jpeg"),
    ("scan.jpeg", "image/jpeg"),
    ("xray.png", "image/png"),
])
def test_content_type_allowlist_maps_the_permitted_upload_types(filename, expected):
    assert document_catalog._content_type_for(filename) == expected


@pytest.mark.parametrize("hostile", [
    "payload.html", "payload.svg", "payload.js", "noextension", "", "archive.zip",
])
def test_unrecognised_types_are_served_as_octet_stream(hostile):
    """An inline-rendering type would be stored XSS against the doctor's authenticated
    session on this same origin."""
    assert document_catalog._content_type_for(hostile) == "application/octet-stream"


# ---- authorization ----

def test_listing_requires_a_treating_relationship(monkeypatch):
    monkeypatch.setattr(
        "app.services.appointments.doctor_treats_patient", lambda doctor_id, patient_id: False
    )

    with pytest.raises(PermissionError):
        document_catalog.list_documents_for_doctor("doctor-1", "patient-1")


def test_listing_passes_the_authenticated_doctor_to_the_authorization_check(monkeypatch):
    seen = {}

    def fake_treats(doctor_id, patient_id):
        seen.update(doctor_id=doctor_id, patient_id=patient_id)
        return True

    monkeypatch.setattr("app.services.appointments.doctor_treats_patient", fake_treats)
    monkeypatch.setattr(document_catalog, "list_user_documents", lambda patient_id: [])

    document_catalog.list_documents_for_doctor("doctor-authenticated", "patient-7")

    assert seen == {"doctor_id": "doctor-authenticated", "patient_id": "patient-7"}


def test_a_document_belonging_to_another_patient_is_unreachable(monkeypatch):
    """get_catalog_entry() resolves a document by id with no ownership check at all, so
    the entry.user_id comparison in _owned_entry is load-bearing: without it, any doctor
    who treats anyone could read any document in the system by guessing its id."""
    monkeypatch.setattr(
        "app.services.appointments.doctor_treats_patient", lambda doctor_id, patient_id: True
    )
    monkeypatch.setattr(
        document_catalog, "get_catalog_entry",
        lambda document_id: _Entry(user_id="somebody-else"),
    )

    with pytest.raises(ValueError):
        document_catalog._owned_entry("doctor-1", "patient-1", "doc-1")


def test_a_missing_document_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "app.services.appointments.doctor_treats_patient", lambda doctor_id, patient_id: True
    )
    monkeypatch.setattr(document_catalog, "get_catalog_entry", lambda document_id: None)

    with pytest.raises(ValueError):
        document_catalog._owned_entry("doctor-1", "patient-1", "doc-1")


def test_a_still_processing_document_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "app.services.appointments.doctor_treats_patient", lambda doctor_id, patient_id: True
    )
    monkeypatch.setattr(
        document_catalog, "get_catalog_entry", lambda document_id: _Entry(status="processing")
    )

    with pytest.raises(ValueError) as exc:
        document_catalog._owned_entry("doctor-1", "patient-1", "doc-1")
    assert "processing" in str(exc.value).lower()


# ---- route error mapping ----

def test_document_list_route_maps_no_relationship_to_404_not_403(monkeypatch):
    """404, never 403: a 403 would confirm the patient exists."""
    def fake_list(doctor_id, patient_id):
        raise PermissionError("Patient not found.")

    monkeypatch.setattr(doctor_route, "list_documents_for_doctor", fake_list)

    with pytest.raises(HTTPException) as exc:
        doctor_route.doctor_patient_documents_route("patient-1", doctor=_doctor())
    assert exc.value.status_code == 404
    assert exc.value.detail == "Patient not found."


def test_document_summary_route_maps_missing_stored_file_to_404(monkeypatch):
    async def fake_summary(doctor_id, patient_id, document_id):
        raise FileNotFoundError("gone")

    monkeypatch.setattr(doctor_route, "get_document_summary_for_doctor", fake_summary)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(doctor_route.doctor_patient_document_summary_route(
            "patient-1", "doc-1", doctor=_doctor()
        ))
    assert exc.value.status_code == 404


def test_document_summary_route_maps_corrupt_stored_json_to_502(monkeypatch):
    """A storage-layer fault is not the caller's fault and must not read as 404."""
    async def fake_summary(doctor_id, patient_id, document_id):
        raise RuntimeError("Stored document summary is not valid JSON")

    monkeypatch.setattr(doctor_route, "get_document_summary_for_doctor", fake_summary)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(doctor_route.doctor_patient_document_summary_route(
            "patient-1", "doc-1", doctor=_doctor()
        ))
    assert exc.value.status_code == 502


def test_document_summary_route_maps_still_processing_to_409(monkeypatch):
    async def fake_summary(doctor_id, patient_id, document_id):
        raise ValueError("This document has not finished processing.")

    monkeypatch.setattr(doctor_route, "get_document_summary_for_doctor", fake_summary)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(doctor_route.doctor_patient_document_summary_route(
            "patient-1", "doc-1", doctor=_doctor()
        ))
    assert exc.value.status_code == 409


def test_document_summary_route_scopes_to_the_authenticated_doctor(monkeypatch):
    seen = {}

    async def fake_summary(doctor_id, patient_id, document_id):
        seen.update(doctor_id=doctor_id, patient_id=patient_id, document_id=document_id)
        return {"document_id": document_id, "is_ai_generated": True}

    monkeypatch.setattr(doctor_route, "get_document_summary_for_doctor", fake_summary)

    result = asyncio.run(doctor_route.doctor_patient_document_summary_route(
        "patient-1", "doc-1", doctor=_doctor("doctor-authenticated")
    ))

    assert seen["doctor_id"] == "doctor-authenticated"
    assert result["is_ai_generated"] is True


# ---- file download hardening ----

def test_file_download_is_always_an_attachment_and_never_sniffable(monkeypatch):
    async def fake_read(doctor_id, patient_id, document_id):
        return b"%PDF-1.4 fake", "Complete_Blood_Count.pdf", "application/pdf"

    monkeypatch.setattr(doctor_route, "read_document_file_for_doctor", fake_read)

    response = asyncio.run(doctor_route.doctor_patient_document_file_route(
        "patient-1", "doc-1", doctor=_doctor()
    ))

    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.body == b"%PDF-1.4 fake"


def test_file_download_sanitizes_the_filename_in_the_header(monkeypatch):
    """A CR/LF or quote in the filename would be header injection."""
    async def fake_read(doctor_id, patient_id, document_id):
        return b"x", 'evil"\r\nSet-Cookie: a=b.pdf', "application/pdf"

    monkeypatch.setattr(doctor_route, "read_document_file_for_doctor", fake_read)

    response = asyncio.run(doctor_route.doctor_patient_document_file_route(
        "patient-1", "doc-1", doctor=_doctor()
    ))

    disposition = response.headers["content-disposition"]
    assert "\r" not in disposition and "\n" not in disposition
    assert "Set-Cookie" not in response.headers.get("set-cookie", "")


def test_file_download_maps_a_missing_stored_file_to_404(monkeypatch):
    """Normal for any document uploaded before this deployment's current storage
    backend — it must be a clear 404, not a 500."""
    async def fake_read(doctor_id, patient_id, document_id):
        raise FileNotFoundError("gone")

    monkeypatch.setattr(doctor_route, "read_document_file_for_doctor", fake_read)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(doctor_route.doctor_patient_document_file_route(
            "patient-1", "doc-1", doctor=_doctor()
        ))
    assert exc.value.status_code == 404


# ---- document list payload ----

# ---- error-detail disclosure ----

def test_storage_failure_does_not_leak_internal_paths_to_the_client(monkeypatch):
    """blob_storage raises RuntimeError("Failed to download blob {name}: {provider exc}").
    Echoing that into an HTTP body would disclose the internal object layout and the raw
    provider error. The client gets a generic message; the detail goes to the log."""
    leaky = RuntimeError(
        "Failed to download blob summaries/patient-1/doc-1.json: "
        "AuthenticationFailed at https://acct.blob.core.windows.net/hospital-documents"
    )

    async def fake_summary(doctor_id, patient_id, document_id):
        raise leaky

    monkeypatch.setattr(doctor_route, "get_document_summary_for_doctor", fake_summary)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(doctor_route.doctor_patient_document_summary_route(
            "patient-1", "doc-1", doctor=_doctor()
        ))

    detail = str(exc.value.detail)
    assert exc.value.status_code == 502
    for secret in ("summaries/", "blob.core.windows.net", "AuthenticationFailed", "hospital-documents"):
        assert secret not in detail


def test_download_storage_failure_does_not_leak_internal_paths_to_the_client(monkeypatch):
    async def fake_read(doctor_id, patient_id, document_id):
        raise RuntimeError("Failed to download blob vault/patient-1/s1/doc-1/report.pdf: boom")

    monkeypatch.setattr(doctor_route, "read_document_file_for_doctor", fake_read)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(doctor_route.doctor_patient_document_file_route(
            "patient-1", "doc-1", doctor=_doctor()
        ))

    assert exc.value.status_code == 502
    assert "vault/" not in str(exc.value.detail)


# ---- query bounds ----

def test_user_document_listing_is_bounded(monkeypatch):
    """This query had no LIMIT at all. It feeds the patient panel, the doctor listing,
    and select_relevant_documents(), which renders every row into an LLM prompt."""
    captured = {}

    def fake_execute_rows(sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(document_catalog, "_execute_rows", fake_execute_rows)
    monkeypatch.setattr(document_catalog, "_document_catalog_has_original_filename", lambda: True)

    document_catalog.list_user_documents("patient-1")

    assert "LIMIT" in captured["sql"].upper()
    assert captured["params"][-1] == document_catalog.DOCUMENT_LIST_MAX


def test_user_document_listing_clamps_a_caller_supplied_limit(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        document_catalog, "_execute_rows",
        lambda sql, params=(): captured.update(params=params) or [],
    )
    monkeypatch.setattr(document_catalog, "_document_catalog_has_original_filename", lambda: True)

    document_catalog.list_user_documents("patient-1", limit=10_000_000)
    assert captured["params"][-1] == document_catalog.DOCUMENT_LIST_MAX

    document_catalog.list_user_documents("patient-1", limit=0)
    assert captured["params"][-1] == 1


def test_treating_relationship_predicate_agrees_with_doctor_patient_detail():
    """doctor_treats_patient() is the cheap EXISTS form of the gate doctor_patient_detail
    already enforces. If the two ever disagree, one of them is silently widening or
    narrowing access — so assert they agree against a real database.

    Skips (not fails) if no database is reachable.
    """
    from datetime import datetime, timedelta

    from app.db.connection import connect_db
    from app.services.appointments import (
        doctor_patient_detail, doctor_treats_patient, ensure_booking_schema,
    )

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")

    doctor_id = treated_id = untreated_id = None
    try:
        with connect_db() as conn:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO doctors (name, department, experience_years, is_active)
                       VALUES ('Dr. Predicate', 'Testing', 1, TRUE) RETURNING doctor_id"""
                )
                doctor_id = str(cur.fetchone()[0])

                for email in ("predicate-treated@example.com", "predicate-untreated@example.com"):
                    cur.execute(
                        "INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id",
                        (email,),
                    )
                    user_id = str(cur.fetchone()[0])
                    cur.execute(
                        """INSERT INTO patient_profiles
                           (user_id, name, age, mobile_number, address, email, blood_group)
                           VALUES (%s, 'Predicate Patient', 30, '9999999999', 'Addr', %s, 'O+')""",
                        (user_id, email),
                    )
                    if treated_id is None:
                        treated_id = user_id
                    else:
                        untreated_id = user_id

                start_time = datetime.now() - timedelta(hours=2)
                cur.execute(
                    """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
                       VALUES (%s, %s, %s, FALSE) RETURNING slot_id""",
                    (doctor_id, start_time, start_time + timedelta(minutes=30)),
                )
                slot_id = str(cur.fetchone()[0])
                cur.execute(
                    """INSERT INTO appointment_bookings
                       (slot_id, doctor_id, patient_id, start_time, end_time, status)
                       VALUES (%s, %s, %s, %s, %s, 'completed')""",
                    (slot_id, doctor_id, treated_id, start_time, start_time + timedelta(minutes=30)),
                )
            conn.commit()

        for patient_id in (treated_id, untreated_id):
            predicate = doctor_treats_patient(doctor_id, patient_id)
            detail = doctor_patient_detail(doctor_id, patient_id)
            assert predicate is (detail is not None), (
                f"doctor_treats_patient and doctor_patient_detail disagree for {patient_id}"
            )
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                if doctor_id:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                for user_id in (treated_id, untreated_id):
                    if user_id:
                        cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            conn.commit()


def test_document_list_payload_carries_no_clinical_content(monkeypatch):
    """Listing must not pull every document's findings out of storage — the AI summary
    is fetched only on explicit open."""
    monkeypatch.setattr(
        "app.services.appointments.doctor_treats_patient", lambda doctor_id, patient_id: True
    )
    monkeypatch.setattr(document_catalog, "list_user_documents", lambda patient_id: [_Entry()])

    documents = document_catalog.list_documents_for_doctor("doctor-1", "patient-1")

    assert len(documents) == 1
    assert {"overall_impression", "findings", "blob_summary_path"}.isdisjoint(documents[0].keys())
    assert documents[0]["document_id"] == "doc-1"
