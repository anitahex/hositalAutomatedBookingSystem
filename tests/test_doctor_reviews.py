"""Doctor AI-review queue — route wiring and pure-projection tests.

Mirrors test_doctor_appointments.py's convention: the route functions are called
directly (no TestClient) with the service monkeypatched, proving the service always
receives the *authenticated* doctor's own doctor_id and never anything a client could
supply, plus the input-validation branch.

test_doctor_reviews_integration.py covers the actual SQL — cross-doctor isolation, the
three pending item types, and the counts — against a real database.
"""

from datetime import datetime

from fastapi import HTTPException
import pytest

from app.api.routes import doctor as doctor_route
from app.services import soap_notes


def _doctor(doctor_id="doctor-1"):
    return {"doctor_id": doctor_id, "name": "Dr. Test", "department": "Neurology"}


# ---- route wiring ----

def test_reviews_route_rejects_invalid_scope():
    with pytest.raises(HTTPException) as exc:
        doctor_route.doctor_reviews_route(scope="everything", limit=100, doctor=_doctor())
    assert exc.value.status_code == 400


def test_reviews_route_defaults_to_pending(monkeypatch):
    seen = {}

    def fake_list(doctor_id, scope, limit):
        seen.update(doctor_id=doctor_id, scope=scope, limit=limit)
        return {"reviews": [], "counts": {}}

    monkeypatch.setattr(doctor_route, "list_reviews_for_doctor", fake_list)

    doctor_route.doctor_reviews_route(scope="pending", limit=100, doctor=_doctor("doctor-1"))

    assert seen["scope"] == "pending"


def test_reviews_route_scopes_to_authenticated_doctor_only(monkeypatch):
    """The route signature has no client-controllable doctor_id at all — this pins that
    down so a future edit cannot accidentally introduce one."""
    seen = {}

    def fake_list(doctor_id, scope, limit):
        seen.update(doctor_id=doctor_id, scope=scope, limit=limit)
        return {"reviews": [{"consultation_id": "c1"}], "counts": {"pending": 1}}

    monkeypatch.setattr(doctor_route, "list_reviews_for_doctor", fake_list)

    result = doctor_route.doctor_reviews_route(
        scope="completed", limit=25, doctor=_doctor("doctor-authenticated")
    )

    assert seen["doctor_id"] == "doctor-authenticated"
    assert seen["scope"] == "completed"
    assert seen["limit"] == 25
    assert result == {"reviews": [{"consultation_id": "c1"}], "counts": {"pending": 1}}


def test_reviews_route_normalizes_scope_case_and_whitespace(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        doctor_route, "list_reviews_for_doctor",
        lambda doctor_id, scope, limit: seen.update(scope=scope) or {"reviews": [], "counts": {}},
    )

    doctor_route.doctor_reviews_route(scope="  COMPLETED  ", limit=100, doctor=_doctor())

    assert seen["scope"] == "completed"


# ---- service-level input validation (runs before any database access) ----

def test_service_rejects_unknown_scope_before_touching_the_database():
    with pytest.raises(ValueError):
        soap_notes.list_reviews_for_doctor("doctor-1", scope="all")


# ---- low-confidence counting ----

def test_low_confidence_count_counts_only_true_flags():
    flags = {"subjective": True, "objective": False, "assessment": True, "plan": False}
    assert soap_notes._low_confidence_count(flags) == 2


def test_low_confidence_count_ignores_unknown_field_names():
    """Only the four real SOAP fields count — a stray key must not inflate the badge."""
    flags = {"subjective": True, "not_a_soap_field": True}
    assert soap_notes._low_confidence_count(flags) == 1


def test_low_confidence_count_tolerates_malformed_values():
    """This feeds a dashboard count; one malformed row must never break the whole queue."""
    assert soap_notes._low_confidence_count(None) == 0
    assert soap_notes._low_confidence_count("not-a-dict") == 0
    assert soap_notes._low_confidence_count({}) == 0
    # Truthy-but-not-True must not count: the writer stores real booleans.
    assert soap_notes._low_confidence_count({"subjective": "yes"}) == 0


# ---- row projection ----

def _row(note_id="note-1", note_status="draft", transcript_source="batch",
         edited_at=None, signed_at=None, shared_with_patient_at=None, confidence_flags=None):
    return (
        "consult-1", "booking-1", "patient-1", "Maria Chen", "Neurology",
        datetime(2026, 9, 16, 10, 30), datetime(2026, 9, 16, 11, 0), transcript_source,
        note_id, note_status, datetime(2026, 9, 16, 11, 5), edited_at, signed_at,
        shared_with_patient_at, confidence_flags if confidence_flags is not None else {},
    )


def test_row_projection_marks_a_missing_note_as_not_generated():
    """A transcribed consult with no note is outstanding work nothing else surfaces."""
    result = soap_notes._review_row_to_dict(_row(note_id=None, note_status=None))
    assert result["item_type"] == "not_generated"
    assert result["note_id"] is None
    assert result["is_stale"] is False


def test_row_projection_flags_stale_notes():
    result = soap_notes._review_row_to_dict(_row(note_status="stale"))
    assert result["item_type"] == "stale"
    assert result["is_stale"] is True


def test_row_projection_reports_signed_notes_as_signed():
    result = soap_notes._review_row_to_dict(
        _row(note_status="signed", signed_at=datetime(2026, 9, 16, 12, 0))
    )
    assert result["item_type"] == "signed"
    assert result["signed_at"] == "2026-09-16T12:00:00"


def test_row_projection_distinguishes_untouched_ai_output_from_doctor_edits():
    """AI GENERATED vs DOCTOR MODIFIED — the distinction the whole queue exists to make."""
    untouched = soap_notes._review_row_to_dict(_row(edited_at=None))
    edited = soap_notes._review_row_to_dict(_row(edited_at=datetime(2026, 9, 16, 11, 30)))
    assert untouched["is_edited"] is False
    assert edited["is_edited"] is True


def test_row_projection_flags_live_fallback_transcripts():
    """A live_fallback transcript was never proofread by the batch pass, so the doctor
    must be told before they open it, not after."""
    assert soap_notes._review_row_to_dict(_row(transcript_source="live_fallback"))["low_quality_transcript"] is True
    assert soap_notes._review_row_to_dict(_row(transcript_source="batch"))["low_quality_transcript"] is False


def test_row_projection_surfaces_low_confidence_field_count():
    result = soap_notes._review_row_to_dict(
        _row(confidence_flags={"subjective": True, "plan": True, "objective": False})
    )
    assert result["low_confidence_fields"] == 2


def test_row_projection_serializes_timestamps_as_iso_strings():
    result = soap_notes._review_row_to_dict(_row())
    assert result["appointment_start"] == "2026-09-16T10:30:00"
    assert result["consult_ended_at"] == "2026-09-16T11:00:00"


def test_row_projection_does_not_leak_note_content():
    """The queue is an index, not a record viewer: no SOAP text, no citations, no
    transcript. Minimising what a single request returns is deliberate — see the plan's
    security note on this being the first bulk cross-consult doctor endpoint."""
    result = soap_notes._review_row_to_dict(_row())
    leaked = {"subjective", "objective", "assessment", "plan", "field_citations", "segments"}
    assert leaked.isdisjoint(result.keys())
