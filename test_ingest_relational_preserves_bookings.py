"""Regression coverage for app/db/ingest_relational.py's appointment_slots upsert.

docker-entrypoint.sh now runs ingest_relational_data() on every container boot instead of
once behind a flag file. Before this fix, its ON CONFLICT (slot_id) DO UPDATE clause wrote
is_booked/booked_by_patient_id straight from the static seed CSV (always is_booked=False),
clobbering a slot's real, live booking state on every restart — even though
app/services/appointments.py treats appointment_bookings as the actual source of truth for
availability. See test_booking_schema_integration.py's docstring for the same hazard from
the read side (ensure_booking_schema's backfill).

Skips (not fails) if no database is reachable.
"""

from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.db.ingest_relational import ingest_relational_data
from app.services.appointments import ensure_booking_schema


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def test_ingest_does_not_clobber_a_live_booked_slot(tmp_path, monkeypatch):
    _skip_if_no_database()

    doctor_id = slot_id = None
    try:
        with connect_db() as conn:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO doctors (name, department, experience_years, is_active)
                       VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
                    ("Dr. Ingest Regression", "Testing", 1),
                )
                doctor_id = str(cur.fetchone()[0])

                start_time = datetime.now() + timedelta(days=1)
                end_time = start_time + timedelta(minutes=30)
                patient_id = "test-patient-ingest-regression"

                # A real, live booking: is_booked=TRUE on the slot and a matching
                # 'booked' row in appointment_bookings — exactly what a patient
                # booking through the app produces.
                cur.execute(
                    """INSERT INTO appointment_slots
                           (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
                       VALUES (%s, %s, %s, TRUE, %s) RETURNING slot_id""",
                    (doctor_id, start_time, end_time, patient_id),
                )
                slot_id = str(cur.fetchone()[0])
                cur.execute(
                    """INSERT INTO appointment_bookings
                           (slot_id, doctor_id, patient_id, start_time, end_time, status)
                       VALUES (%s, %s, %s, %s, %s, 'booked')""",
                    (slot_id, doctor_id, patient_id, start_time, end_time),
                )
            conn.commit()

        # Mirrors the static seed CSVs shipped in the repo: same slot_id, but with
        # is_booked=False/no patient — this is what every redeploy re-ingests.
        (tmp_path / "doctors_roster.csv").write_text(
            "name,department,experience_years,doctor_id\n"
            f"Dr. Ingest Regression,Testing,1,{doctor_id}\n"
        )
        (tmp_path / "appointment_slots.csv").write_text(
            "slot_id,doctor_id,start_time,end_time,is_booked,booked_by_patient_id\n"
            f"{slot_id},{doctor_id},{start_time:%Y-%m-%d %H:%M:%S},"
            f"{end_time:%Y-%m-%d %H:%M:%S},False,\n"
        )
        monkeypatch.chdir(tmp_path)

        ingest_relational_data()

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT is_booked, booked_by_patient_id FROM appointment_slots WHERE slot_id = %s",
                    (slot_id,),
                )
                is_booked, booked_by = cur.fetchone()

        assert is_booked is True, "re-ingesting the seed CSV must not un-book a live booking"
        assert booked_by == patient_id, "re-ingesting the seed CSV must not clear booked_by_patient_id"
    finally:
        if doctor_id:
            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                conn.commit()
