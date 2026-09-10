"""Regression coverage for FULL_SYSTEM_AUDIT.md P1 #8: start_consult()'s
"does an active consult already exist for this booking" check was a plain unlocked
SELECT, so two concurrent POST /consult/start calls (double-click, two tabs) could
both pass the check before either committed its INSERT, creating two simultaneous
consultations for one booking. Fixed by locking the appointment_bookings row FOR
UPDATE (serializing concurrent calls for the same booking) plus a partial unique
index on consultations(booking_id) as a DB-level backstop.

Races two real threads (each with its own pooled connection via connect_db()) against
the exact same booking_id — not a mock, an actual concurrency race against Postgres.
Skips (not fails) if no database is reachable, matching this repo's convention.
"""
import threading
from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.consults import start_consult


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _make_doctor(cur, name):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, 'Testing', 1, TRUE) RETURNING doctor_id""",
        (name,),
    )
    return str(cur.fetchone()[0])


def _make_booking(cur, doctor_id, patient_id="patient-race"):
    start_time = datetime.now() + timedelta(hours=1)
    end_time = start_time + timedelta(minutes=30)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
           VALUES (%s, %s, %s, TRUE) RETURNING slot_id""",
        (doctor_id, start_time, end_time),
    )
    slot_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, 'booked') RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start_time, end_time),
    )
    return str(cur.fetchone()[0])


def _cleanup(doctor_id):
    if not doctor_id:
        return
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        conn.commit()


def test_concurrent_start_consult_for_same_booking_only_one_succeeds():
    _skip_if_no_database()
    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Consult Race")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        results = {}
        errors = {}
        start_barrier = threading.Barrier(2)

        def _attempt(label):
            start_barrier.wait()
            try:
                results[label] = start_consult(doctor_id=doctor_id, booking_id=booking_id)
            except Exception as exc:
                errors[label] = exc

        threads = [
            threading.Thread(target=_attempt, args=("a",)),
            threading.Thread(target=_attempt, args=("b",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        successes = list(results.values())
        assert len(successes) == 1, f"expected exactly one successful start_consult, got {len(successes)} (results={results}, errors={errors})"
        assert len(errors) == 1
        assert isinstance(list(errors.values())[0], PermissionError)

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM consultations WHERE booking_id::text = %s", (booking_id,))
                count = cur.fetchone()[0]
        assert count == 1, f"expected exactly one consultation row for the booking, found {count}"
    finally:
        _cleanup(doctor_id)


def test_sequential_start_consult_rejects_second_call_while_first_is_not_started():
    """A second start_consult call must be rejected even while the first consult is
    still 'not_started' (never even reached consent/recording) — not just once it's
    actively recording. Confirmed against real behavior: before this fix, both calls
    silently succeeded and created two rows, since only _ACTIVE_CONSULT_STATUSES
    (recording/transcribing/transcript_ready) blocked a second call."""
    _skip_if_no_database()
    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Consult Sequential")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        first = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        assert first is not None
        assert first["status"] == "not_started"

        with pytest.raises(PermissionError):
            start_consult(doctor_id=doctor_id, booking_id=booking_id)

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM consultations WHERE booking_id::text = %s", (booking_id,))
                count = cur.fetchone()[0]
        assert count == 1
    finally:
        _cleanup(doctor_id)
