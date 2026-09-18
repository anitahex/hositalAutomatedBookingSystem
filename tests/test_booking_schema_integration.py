"""Regression coverage for ensure_booking_schema()'s idempotent backfill logic against a
real database.

Found while adding Part 1 doctor-dashboard tests: a slot left is_booked=TRUE whose booking
is already 'completed' (or 'cancelled') — a state the app's own request-handling code
never produces in normal operation, but that a direct SQL edit or app/db/ingest_relational.py's
CSV bulk-upsert (which writes appointment_slots.is_booked directly and never touches
appointment_bookings at all) can produce — used to make the backfill INSERT create a
second, duplicate booking for that slot. The partial unique index backing ON CONFLICT DO
NOTHING only covers status='booked' rows, so it silently let a non-'booked' duplicate through.

Skips (not fails) if no database is reachable.
"""

from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.appointments import ensure_booking_schema


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def test_backfill_does_not_duplicate_a_completed_booking_left_with_is_booked_true():
    _skip_if_no_database()

    doctor_id = slot_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO doctors (name, department, experience_years, is_active)
                       VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
                    ("Dr. Backfill Regression", "Testing", 1),
                )
                doctor_id = str(cur.fetchone()[0])

                start_time = datetime.now() - timedelta(hours=2)
                end_time = start_time + timedelta(minutes=30)

                # Deliberately inconsistent state: is_booked=TRUE on a slot whose
                # booking is already 'completed' — the app's own code never leaves
                # this behind (completing a booking always resets is_booked to
                # FALSE in the same transaction), but a direct SQL edit or a stale
                # ingest_relational.py CSV re-import can.
                cur.execute(
                    """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
                       VALUES (%s, %s, %s, TRUE) RETURNING slot_id""",
                    (doctor_id, start_time, end_time),
                )
                slot_id = str(cur.fetchone()[0])
                cur.execute(
                    """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
                       VALUES (%s, %s, NULL, %s, %s, 'completed')""",
                    (slot_id, doctor_id, start_time, end_time),
                )
            conn.commit()

        with connect_db() as conn:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT booking_id, status FROM appointment_bookings WHERE slot_id = %s",
                    (slot_id,),
                )
                rows = cur.fetchall()

        assert len(rows) == 1, f"expected exactly one booking for this slot, found {len(rows)}: {rows}"
        assert rows[0][1] == "completed"
    finally:
        if doctor_id:
            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                conn.commit()
