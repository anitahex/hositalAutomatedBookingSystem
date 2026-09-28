"""Share-a-signed-note-with-the-patient (C8) — route wiring and patient-exposure tests.

Sharing is deliberately a separate doctor action from signing, and is one-way. The
properties that matter here are: only a SIGNED note can ever be shared, the patient
endpoints expose a shared note and nothing more, and the patient-visible projection
never carries clinician-only signals (citations, confidence flags, transcript source).

test_soap_note_sharing_integration.py exercises the actual UPDATE and the patient-scoped
SELECT against a real database.
"""

from fastapi import HTTPException
import pytest

from app.api.routes import appointments as appointments_route
from app.api.routes import consult as consult_route
from app.services import soap_notes


def _doctor(doctor_id="doctor-1"):
    return {"doctor_id": doctor_id, "account_id": "account-1", "name": "Dr. Test"}


# ---- share route wiring ----

def test_share_route_returns_the_note_on_success(monkeypatch):
    monkeypatch.setattr(
        consult_route, "share_soap_note",
        lambda consultation_id, doctor_id: {"id": "note-1", "shared_with_patient_at": "2026-09-22T10:00:00"},
    )

    result = consult_route.share_soap_note_route("consult-1", doctor=_doctor())

    assert result["shared_with_patient_at"] == "2026-09-22T10:00:00"


def test_share_route_scopes_to_the_authenticated_doctor(monkeypatch):
    seen = {}

    def fake_share(consultation_id, doctor_id):
        seen.update(consultation_id=consultation_id, doctor_id=doctor_id)
        return {"id": "note-1"}

    monkeypatch.setattr(consult_route, "share_soap_note", fake_share)

    consult_route.share_soap_note_route("consult-1", doctor=_doctor("doctor-authenticated"))

    assert seen == {"consultation_id": "consult-1", "doctor_id": "doctor-authenticated"}


def test_share_route_maps_unsigned_note_to_conflict(monkeypatch):
    """An unsigned draft is AI output no clinician has accepted responsibility for.
    Refusing it is the single most important rule in this feature."""
    def fake_share(consultation_id, doctor_id):
        raise PermissionError("Only a signed clinical note can be shared with the patient.")

    monkeypatch.setattr(consult_route, "share_soap_note", fake_share)

    with pytest.raises(HTTPException) as exc:
        consult_route.share_soap_note_route("consult-1", doctor=_doctor())
    assert exc.value.status_code == 409


def test_share_route_maps_missing_consult_to_not_found(monkeypatch):
    def fake_share(consultation_id, doctor_id):
        raise ValueError("Consult not found.")

    monkeypatch.setattr(consult_route, "share_soap_note", fake_share)

    with pytest.raises(HTTPException) as exc:
        consult_route.share_soap_note_route("consult-1", doctor=_doctor())
    assert exc.value.status_code == 404


def test_share_route_maps_missing_note_to_not_found(monkeypatch):
    def fake_share(consultation_id, doctor_id):
        raise ValueError("No clinical note exists yet for this consult.")

    monkeypatch.setattr(consult_route, "share_soap_note", fake_share)

    with pytest.raises(HTTPException) as exc:
        consult_route.share_soap_note_route("consult-1", doctor=_doctor())
    assert exc.value.status_code == 404


def test_there_is_no_unshare_route():
    """Sharing is one-way by product decision. This pins that down so an unshare path
    cannot appear without someone deliberately revisiting the decision."""
    paths = {route.path for route in consult_route.router.routes}
    assert "/{consultation_id}/soap/share" in paths
    assert not any("unshare" in path for path in paths)


# ---- patient exposure ----

def test_patient_visible_fields_exclude_clinician_only_signals():
    """field_citations and confidence_flags are documentation-quality signals written
    for a clinician. A patient reading 'Needs review' on their own assessment would
    reasonably hear 'my diagnosis is uncertain'."""
    forbidden = {
        "field_citations", "confidence_flags", "source_transcript_type",
        "transcript_fallback_error", "addenda", "status",
    }
    assert forbidden.isdisjoint(soap_notes._PATIENT_VISIBLE_NOTE_FIELDS)


def test_shared_note_lookup_short_circuits_on_an_empty_booking_list():
    """No bookings means no query at all — the patient appointments endpoints call this
    unconditionally, including for a brand-new account with nothing booked."""
    assert soap_notes.list_shared_notes_for_patient("patient-1", []) == {}


def test_visit_summary_is_attached_to_the_matching_booking(monkeypatch):
    monkeypatch.setattr(
        appointments_route, "list_shared_notes_for_patient",
        lambda patient_id, booking_ids: {"b1": {"subjective": "S", "doctor_name": "Dr. Patel"}},
    )

    bookings = [{"booking_id": "b1"}, {"booking_id": "b2"}]
    result = appointments_route._with_visit_summaries(bookings, "patient-1")

    assert result[0]["visit_summary"] == {"subjective": "S", "doctor_name": "Dr. Patel"}
    assert result[1]["visit_summary"] is None


def test_visit_summary_lookup_is_scoped_to_the_authenticated_patient(monkeypatch):
    seen = {}

    def fake_lookup(patient_id, booking_ids):
        seen.update(patient_id=patient_id, booking_ids=booking_ids)
        return {}

    monkeypatch.setattr(appointments_route, "list_shared_notes_for_patient", fake_lookup)

    appointments_route._with_visit_summaries([{"booking_id": "b1"}], "patient-authenticated")

    assert seen["patient_id"] == "patient-authenticated"
    assert seen["booking_ids"] == ["b1"]


def test_visit_summary_enrichment_is_one_batched_call_not_one_per_booking(monkeypatch):
    """Guards the N+1 the plan explicitly set out to avoid."""
    calls = []

    monkeypatch.setattr(
        appointments_route, "list_shared_notes_for_patient",
        lambda patient_id, booking_ids: calls.append(booking_ids) or {},
    )

    bookings = [{"booking_id": f"b{i}"} for i in range(25)]
    appointments_route._with_visit_summaries(bookings, "patient-1")

    assert len(calls) == 1
    assert len(calls[0]) == 25
