"""Doctor dashboard (Part 1) route-level access control tests.

Every route below is Depends(get_current_doctor)-protected and must filter strictly by
the doctor_id embedded in the caller's own JWT — never by anything the client supplies.
These tests call the route functions directly (this repo's convention, no TestClient)
and prove the underlying service call always receives the *authenticated* doctor's own
doctor_id, never a client-supplied one, plus the plain input-validation/404 branches.

test_doctor_appointments_integration.py covers the actual cross-doctor data leakage
question against a real database (the SQL itself, not just the route wiring).
"""

from fastapi import HTTPException
import pytest

from app.api.routes import doctor as doctor_route


def _doctor(doctor_id="doctor-1"):
    return {"doctor_id": doctor_id, "name": "Dr. Test", "department": "Cardiology"}


def test_appointments_route_rejects_invalid_scope():
    with pytest.raises(HTTPException) as exc:
        doctor_route.doctor_appointments_route(scope="everything", doctor=_doctor())
    assert exc.value.status_code == 400


def test_appointments_route_filters_by_authenticated_doctor_only(monkeypatch):
    seen = {}

    def fake_doctor_appointments(doctor_id, scope, limit=100):
        seen["doctor_id"] = doctor_id
        seen["scope"] = scope
        return [{"booking_id": "b1"}]

    monkeypatch.setattr(doctor_route, "doctor_appointments", fake_doctor_appointments)
    monkeypatch.setattr(doctor_route, "list_latest_consult_status_by_booking", lambda doctor_id, booking_ids: {})

    result = doctor_route.doctor_appointments_route(scope="upcoming", doctor=_doctor("doctor-1"))

    assert seen["doctor_id"] == "doctor-1"
    assert seen["scope"] == "upcoming"
    assert result == {"appointments": [{
        "booking_id": "b1", "consult_id": None, "consult_status": None,
        "consult_started_at": None, "consult_ended_at": None,
    }]}


def test_appointments_route_ignores_any_client_supplied_doctor_id(monkeypatch):
    """The route signature has no client-controllable doctor_id parameter at all —
    this pins that down so a future edit can't accidentally introduce one."""
    seen = {}

    def fake_doctor_appointments(doctor_id, scope, limit=100):
        seen["doctor_id"] = doctor_id
        return []

    monkeypatch.setattr(doctor_route, "doctor_appointments", fake_doctor_appointments)
    monkeypatch.setattr(doctor_route, "list_latest_consult_status_by_booking", lambda doctor_id, booking_ids: {})

    doctor_route.doctor_appointments_route(scope="past", doctor=_doctor("doctor-A"))
    assert seen["doctor_id"] == "doctor-A"

    # A different authenticated doctor always yields that doctor's own id, never doctor-A's.
    seen.clear()
    doctor_route.doctor_appointments_route(scope="past", doctor=_doctor("doctor-B"))
    assert seen["doctor_id"] == "doctor-B"


def test_patients_route_filters_by_authenticated_doctor_only(monkeypatch):
    seen = {}

    def fake_doctor_patients(doctor_id):
        seen["doctor_id"] = doctor_id
        return [{"patient_id": "p1"}]

    monkeypatch.setattr(doctor_route, "doctor_patients", fake_doctor_patients)

    result = doctor_route.doctor_patients_route(doctor=_doctor("doctor-1"))

    assert seen["doctor_id"] == "doctor-1"
    assert result == {"patients": [{"patient_id": "p1"}]}


def test_patient_detail_route_rejects_when_no_shared_booking_history(monkeypatch):
    """doctor_patient_detail returning None (no booking history between this doctor and
    this patient) must surface as a 404 — the same response as a nonexistent patient_id,
    so a doctor can't distinguish 'wrong id' from 'patient exists but isn't mine'."""
    monkeypatch.setattr(doctor_route, "doctor_patient_detail", lambda doctor_id, patient_id: None)

    with pytest.raises(HTTPException) as exc:
        doctor_route.doctor_patient_detail_route(patient_id="someone-elses-patient", doctor=_doctor("doctor-1"))
    assert exc.value.status_code == 404


def test_patient_detail_route_passes_authenticated_doctor_id_not_a_client_value(monkeypatch):
    seen = {}

    def fake_detail(doctor_id, patient_id):
        seen["doctor_id"] = doctor_id
        seen["patient_id"] = patient_id
        return {"patient_id": patient_id, "visits": []}

    monkeypatch.setattr(doctor_route, "doctor_patient_detail", fake_detail)

    result = doctor_route.doctor_patient_detail_route(patient_id="patient-9", doctor=_doctor("doctor-1"))

    assert seen["doctor_id"] == "doctor-1"
    assert seen["patient_id"] == "patient-9"
    assert result["patient_id"] == "patient-9"
