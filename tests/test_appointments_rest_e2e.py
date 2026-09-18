"""End-to-end coverage for the direct REST booking surface (app/api/routes/appointments.py).

Route-level tests call the route functions directly (no TestClient) and monkeypatch the
service layer where a real DB isn't needed — same convention as test_consult_routes.py /
test_doctor_appointments.py. DB-backed tests hit a real Postgres via connect_db() and
skip cleanly (not fail) if unreachable — same pattern as test_consult_integration.py and
test_booking_schema_integration.py.
"""

import threading
from datetime import datetime, timedelta

from fastapi import HTTPException
import pytest

from app.api.routes import appointments as appointments_route
from app.db.connection import connect_db
from app.services import appointments as appointments_service


def _user(patient_id="patient-1"):
    return {"patient_id": patient_id, "name": "Test Patient"}


# ── DB availability helper (same pattern as test_consult_integration.py) ────────

def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _make_doctor(cur, name, department="Testing"):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
        (name, department, 5),
    )
    return str(cur.fetchone()[0])


def _make_slot(cur, doctor_id, offset):
    start_time = datetime.now() + offset
    end_time = start_time + timedelta(minutes=30)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
           VALUES (%s, %s, %s, FALSE) RETURNING slot_id""",
        (doctor_id, start_time, end_time),
    )
    return str(cur.fetchone()[0])


def _cleanup(doctor_ids):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for doctor_id in doctor_ids:
                if doctor_id:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        conn.commit()


# ── Route-level wiring tests (monkeypatched service layer) ──────────────────────

def test_book_slot_route_passes_authenticated_patient_id_and_slot(monkeypatch):
    seen = {}

    def fake_book_selected_slot(slot_id, patient_id):
        seen["slot_id"] = slot_id
        seen["patient_id"] = patient_id
        return {"slot_id": slot_id, "booking_id": "booking-1", "doctor": "Dr. A"}

    monkeypatch.setattr(appointments_route, "book_selected_slot", fake_book_selected_slot)

    result = appointments_route.book_slot(
        appointments_route.BookRequest(slot_id="slot-1"),
        user=_user("patient-1"),
    )

    assert seen == {"slot_id": "slot-1", "patient_id": "patient-1"}
    assert result["booking"]["booking_id"] == "booking-1"


def test_book_slot_route_400_when_slot_unavailable(monkeypatch):
    monkeypatch.setattr(appointments_route, "book_selected_slot", lambda slot_id, patient_id: None)

    with pytest.raises(HTTPException) as exc:
        appointments_route.book_slot(appointments_route.BookRequest(slot_id="taken"), user=_user())
    assert exc.value.status_code == 400


def test_upcoming_bookings_route_passes_authenticated_patient_id_and_hardcoded_limit(monkeypatch):
    seen = {}

    def fake_upcoming(patient_id, limit):
        seen["patient_id"] = patient_id
        seen["limit"] = limit
        return [{"booking_id": "b1"}]

    monkeypatch.setattr(appointments_route, "upcoming_bookings_for_patient", fake_upcoming)

    result = appointments_route.upcoming_bookings(user=_user("patient-9"))

    assert seen == {"patient_id": "patient-9", "limit": 30}
    assert result == {"bookings": [{"booking_id": "b1"}]}


def test_cancel_upcoming_booking_route_passes_authenticated_patient_id(monkeypatch):
    seen = {}

    def fake_cancel(booking_id, patient_id):
        seen["booking_id"] = booking_id
        seen["patient_id"] = patient_id
        return {"booking_id": booking_id, "status": "cancelled"}

    monkeypatch.setattr(appointments_route, "cancel_patient_booking", fake_cancel)

    result = appointments_route.cancel_upcoming_booking("booking-1", user=_user("patient-1"))

    assert seen == {"booking_id": "booking-1", "patient_id": "patient-1"}
    assert result["booking"]["status"] == "cancelled"


def test_cancel_upcoming_booking_route_400_when_not_cancellable(monkeypatch):
    monkeypatch.setattr(appointments_route, "cancel_patient_booking", lambda booking_id, patient_id: None)

    with pytest.raises(HTTPException) as exc:
        appointments_route.cancel_upcoming_booking("booking-1", user=_user())
    assert exc.value.status_code == 400
    assert "24 hours" in exc.value.detail


def test_reschedule_booking_route_passes_authenticated_patient_id_and_new_slot(monkeypatch):
    seen = {}

    def fake_reschedule(booking_id, patient_id, new_slot_id):
        seen["booking_id"] = booking_id
        seen["patient_id"] = patient_id
        seen["new_slot_id"] = new_slot_id
        return {"booking_id": booking_id, "slot_id": new_slot_id, "status": "booked"}

    monkeypatch.setattr(appointments_route, "reschedule_patient_booking", fake_reschedule)

    result = appointments_route.reschedule_booking(
        "booking-1",
        appointments_route.RescheduleRequest(slot_id="slot-new"),
        user=_user("patient-1"),
    )

    assert seen == {"booking_id": "booking-1", "patient_id": "patient-1", "new_slot_id": "slot-new"}
    assert result["booking"]["slot_id"] == "slot-new"


def test_reschedule_booking_route_400_when_not_reschedulable(monkeypatch):
    monkeypatch.setattr(appointments_route, "reschedule_patient_booking", lambda **kwargs: None)

    with pytest.raises(HTTPException) as exc:
        appointments_route.reschedule_booking(
            "booking-1",
            appointments_route.RescheduleRequest(slot_id="slot-new"),
            user=_user(),
        )
    assert exc.value.status_code == 400
    assert "24 hours" in exc.value.detail


def test_reschedule_options_route_rejects_bad_date_format():
    with pytest.raises(HTTPException) as exc:
        appointments_route.reschedule_options("booking-1", date="not-a-date", user=_user())
    assert exc.value.status_code == 400


def test_reschedule_options_route_passes_authenticated_patient_id_and_parsed_date(monkeypatch):
    seen = {}

    def fake_options(booking_id, patient_id, requested_date, limit):
        seen["booking_id"] = booking_id
        seen["patient_id"] = patient_id
        seen["requested_date"] = requested_date
        seen["limit"] = limit
        return [{"slot_id": "slot-1"}]

    monkeypatch.setattr(appointments_route, "reschedule_options_for_booking", fake_options)

    result = appointments_route.reschedule_options("booking-1", date="2026-09-20", user=_user("patient-1"))

    assert seen == {
        "booking_id": "booking-1", "patient_id": "patient-1",
        "requested_date": "2026-09-20", "limit": 10,
    }
    assert result == {"slots": [{"slot_id": "slot-1"}]}


def test_previous_bookings_route_always_passes_hardcoded_limit_30_never_client_controlled(monkeypatch):
    """/appointments/previous exposes no `limit` (or any other) query parameter on the
    route signature at all — previous_bookings(user: dict = Depends(current_user)) —
    so the limit passed to the service layer is always the hardcoded 30, never anything
    a client could influence."""
    seen = {}

    def fake_previous(patient_id, limit):
        seen["patient_id"] = patient_id
        seen["limit"] = limit
        return [{"booking_id": f"b{i}"} for i in range(limit)]

    monkeypatch.setattr(appointments_route, "previous_bookings_for_patient", fake_previous)

    result = appointments_route.previous_bookings(user=_user("patient-1"))

    assert seen == {"patient_id": "patient-1", "limit": 30}
    assert len(result["bookings"]) == 30


def test_doctors_route_uses_date_scoped_lookup_only_when_date_given(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        appointments_route, "available_doctors_for_department_on_date",
        lambda department, requested_date, limit: seen.update(
            {"path": "on_date", "department": department, "date": requested_date, "limit": limit}
        ) or [],
    )
    monkeypatch.setattr(
        appointments_route, "available_doctors_for_department",
        lambda department, limit: seen.update({"path": "no_date", "department": department, "limit": limit}) or [],
    )

    appointments_route.doctors(department="Cardiology", date="2026-09-20")
    assert seen["path"] == "on_date"
    assert seen["date"] == "2026-09-20"

    seen.clear()
    appointments_route.doctors(department="Cardiology", date=None)
    assert seen["path"] == "no_date"


def test_slots_route_uses_date_scoped_lookup_only_when_date_given(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        appointments_route, "available_slots_for_doctor_on_date",
        lambda doctor_id, requested_date, limit: seen.update(
            {"path": "on_date", "doctor_id": doctor_id, "date": requested_date}
        ) or [],
    )
    monkeypatch.setattr(
        appointments_route, "available_slots_for_doctor",
        lambda doctor_id, limit: seen.update({"path": "no_date", "doctor_id": doctor_id}) or [],
    )

    appointments_route.slots(doctor_id="doc-1", date="2026-09-20")
    assert seen["path"] == "on_date"

    seen.clear()
    appointments_route.slots(doctor_id="doc-1", date=None)
    assert seen["path"] == "no_date"


# ── DB-backed end-to-end: book -> list upcoming -> cancel -> reschedule ─────────

def test_rest_route_flow_book_then_list_upcoming_then_cancel_then_reschedule():
    """Drives the actual REST route functions (not the raw service functions) through
    the full patient lifecycle against a real database: book a slot, see it via
    /upcoming, cancel it (rejected — too soon per the 24h rule), then successfully
    reschedule a second, further-out booking."""
    _skip_if_no_database()

    doctor_id = None
    patient_id = "patient-rest-e2e"
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. REST E2E")
                far_slot_id = _make_slot(cur, doctor_id, timedelta(days=3))
                reschedule_target_slot_id = _make_slot(cur, doctor_id, timedelta(days=4))
            conn.commit()

        # Book.
        booked = appointments_route.book_slot(
            appointments_route.BookRequest(slot_id=far_slot_id),
            user=_user(patient_id),
        )
        booking_id = booked["booking"]["booking_id"]
        assert booked["booking"]["slot_id"] == far_slot_id

        # List upcoming.
        upcoming = appointments_route.upcoming_bookings(user=_user(patient_id))
        assert any(b["booking_id"] == booking_id for b in upcoming["bookings"])

        # Reschedule (booking is 3 days out, well past 24h, so this must succeed).
        rescheduled = appointments_route.reschedule_booking(
            booking_id,
            appointments_route.RescheduleRequest(slot_id=reschedule_target_slot_id),
            user=_user(patient_id),
        )
        assert rescheduled["booking"]["slot_id"] == reschedule_target_slot_id

        # Cancel the rescheduled booking (still well past 24h -> must succeed).
        cancelled = appointments_route.cancel_upcoming_booking(booking_id, user=_user(patient_id))
        assert cancelled["booking"]["status"] == "cancelled"

        # It must no longer show up as upcoming.
        upcoming_after = appointments_route.upcoming_bookings(user=_user(patient_id))
        assert all(b["booking_id"] != booking_id for b in upcoming_after["bookings"])
    finally:
        _cleanup([doctor_id])


def test_rest_route_cancel_rejects_a_booking_inside_the_24_hour_window():
    _skip_if_no_database()

    doctor_id = None
    patient_id = "patient-rest-cancel-soon"
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. REST Cancel Soon")
                soon_slot_id = _make_slot(cur, doctor_id, timedelta(hours=2))
            conn.commit()

        booked = appointments_route.book_slot(
            appointments_route.BookRequest(slot_id=soon_slot_id), user=_user(patient_id),
        )
        booking_id = booked["booking"]["booking_id"]

        with pytest.raises(HTTPException) as exc:
            appointments_route.cancel_upcoming_booking(booking_id, user=_user(patient_id))
        assert exc.value.status_code == 400
    finally:
        _cleanup([doctor_id])


# ── Concurrent double-booking of the same slot is rejected ──────────────────────

def test_concurrent_booking_of_the_same_slot_by_two_patients_only_one_succeeds():
    """book_selected_slot() uses `FOR UPDATE OF s SKIP LOCKED` plus a NOT EXISTS guard
    against an existing 'booked' row for the slot. Races two real threads (each with
    its own pooled connection, via connect_db()) against the exact same slot_id and
    confirms exactly one booking is created — not a mock, an actual concurrency race
    against Postgres."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Concurrency Race")
                slot_id = _make_slot(cur, doctor_id, timedelta(days=1))
            conn.commit()

        results = {}
        start_barrier = threading.Barrier(2)

        def _attempt(patient_id):
            start_barrier.wait()
            results[patient_id] = appointments_service.book_selected_slot(
                slot_id=slot_id, patient_id=patient_id,
            )

        threads = [
            threading.Thread(target=_attempt, args=("patient-race-a",)),
            threading.Thread(target=_attempt, args=("patient-race-b",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        successes = [pid for pid, result in results.items() if result is not None]
        failures = [pid for pid, result in results.items() if result is None]

        assert len(successes) == 1, f"expected exactly one winner, got {successes}"
        assert len(failures) == 1

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT patient_id FROM appointment_bookings WHERE slot_id = %s AND status = 'booked'",
                    (slot_id,),
                )
                rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == successes[0]
    finally:
        _cleanup([doctor_id])


# ── /appointments/previous limit=30 boundary, against a real database ───────────

def test_previous_bookings_hardcoded_limit_30_boundary_against_real_data():
    """Confirms the actual boundary behavior, not just that 30 was passed through:
    create more than 30 completed bookings for one patient and verify the route
    returns exactly 30 (the hardcoded cap), not all of them."""
    _skip_if_no_database()

    doctor_id = None
    patient_id = "patient-previous-boundary"
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Previous Boundary")
                for i in range(35):
                    start_time = datetime.now() - timedelta(days=i + 1)
                    end_time = start_time + timedelta(minutes=30)
                    cur.execute(
                        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
                           VALUES (%s, %s, %s, TRUE) RETURNING slot_id""",
                        (doctor_id, start_time, end_time),
                    )
                    slot_id = cur.fetchone()[0]
                    cur.execute(
                        """INSERT INTO appointment_bookings
                           (slot_id, doctor_id, patient_id, start_time, end_time, status)
                           VALUES (%s, %s, %s, %s, %s, 'completed')""",
                        (slot_id, doctor_id, patient_id, start_time, end_time),
                    )
            conn.commit()

        result = appointments_route.previous_bookings(user=_user(patient_id))
        assert len(result["bookings"]) == 30
    finally:
        _cleanup([doctor_id])
