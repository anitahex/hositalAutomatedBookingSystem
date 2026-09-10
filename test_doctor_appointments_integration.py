"""Integration regression coverage for the Part 1 doctor-scoped appointment/patient
queries against a real database.

These functions filter by doctor_id in raw SQL — a mocked-cursor unit test can prove the
route passes the right doctor_id through, but only a real query can prove doctor A's
result set actually excludes doctor B's bookings and patients. That's the property this
file exists to check (mirrors test_admin_doctor_management_integration.py's rationale).

Skips (not fails) if no database is reachable.
"""

from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.appointments import doctor_appointments, doctor_patient_detail, doctor_patients


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
           VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
        (name, "Testing", 1),
    )
    return str(cur.fetchone()[0])


def _make_patient(cur, email):
    cur.execute(
        """INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id""",
        (email,),
    )
    user_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
           VALUES (%s, %s, 30, '9999999999', 'Test address', %s, 'O+')""",
        (user_id, f"Patient {email}", email),
    )
    return user_id


def _make_slot_and_booking(cur, doctor_id, patient_id, start_offset_hours):
    # Naive timestamps in this codebase are local wall-clock time (matched against
    # Postgres NOW()), not UTC — see admin_management.py's locked_until comparison.
    start_time = datetime.now() + timedelta(hours=start_offset_hours)
    end_time = start_time + timedelta(minutes=30)
    status = "booked" if start_offset_hours > 0 else "completed"
    # is_booked must match real lifecycle state: ensure_booking_schema()'s idempotent
    # backfill re-inserts a 'booked' row for any slot left is_booked=TRUE with no
    # matching 'booked' appointment_bookings row (the partial unique index only
    # covers status='booked'). A completed/past visit's slot is always flipped back
    # to is_booked=FALSE by that same schema helper in normal app usage — mimic that
    # here, or the backfill silently duplicates this test's booking.
    is_booked = start_offset_hours > 0
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
           VALUES (%s, %s, %s, %s, %s) RETURNING slot_id""",
        (doctor_id, start_time, end_time, is_booked, patient_id if is_booked else None),
    )
    slot_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start_time, end_time, status),
    )
    return str(cur.fetchone()[0])


def test_doctor_cannot_see_another_doctors_appointments_or_patients():
    _skip_if_no_database()

    doctor_a_id = doctor_b_id = patient_a_user_id = patient_b_user_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_a_id = _make_doctor(cur, "Dr. A Regression")
                doctor_b_id = _make_doctor(cur, "Dr. B Regression")
                patient_a_user_id = _make_patient(cur, "patient-a-regression@example.com")
                patient_b_user_id = _make_patient(cur, "patient-b-regression@example.com")

                # Doctor A has one upcoming booking with patient A.
                _make_slot_and_booking(cur, doctor_a_id, patient_a_user_id, start_offset_hours=1)
                # Doctor B has one upcoming booking with patient B — must never leak into A's results.
                _make_slot_and_booking(cur, doctor_b_id, patient_b_user_id, start_offset_hours=1)
            conn.commit()

        # ── Appointments: A sees only A's booking ────────────────────────────
        a_upcoming = doctor_appointments(doctor_a_id, "upcoming")
        assert len(a_upcoming) == 1
        assert a_upcoming[0]["patient_name"] == "Patient patient-a-regression@example.com"

        b_upcoming = doctor_appointments(doctor_b_id, "upcoming")
        assert len(b_upcoming) == 1
        assert b_upcoming[0]["patient_name"] == "Patient patient-b-regression@example.com"

        # ── Patients: A's patient list never includes B's patient ───────────
        a_patients = doctor_patients(doctor_a_id)
        a_patient_ids = {p["patient_id"] for p in a_patients}
        assert patient_a_user_id in a_patient_ids
        assert patient_b_user_id not in a_patient_ids

        # ── Patient detail: A can see A's own patient ────────────────────────
        detail = doctor_patient_detail(doctor_a_id, patient_a_user_id)
        assert detail is not None
        assert len(detail["visits"]) == 1

        # ── Patient detail: A CANNOT see B's patient, even with a valid, real patient_id ──
        cross_doctor_detail = doctor_patient_detail(doctor_a_id, patient_b_user_id)
        assert cross_doctor_detail is None

        # ── Patient detail: B cannot see A's patient either (symmetry) ───────
        assert doctor_patient_detail(doctor_b_id, patient_a_user_id) is None
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                for doctor_id in (doctor_a_id, doctor_b_id):
                    if doctor_id:
                        cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                for user_id in (patient_a_user_id, patient_b_user_id):
                    if user_id:
                        cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            conn.commit()


def test_doctor_appointments_response_includes_booking_id():
    """Part 3's 'Start Consult' button needs booking_id on each appointment row —
    pin this down now so a later refactor of the SELECT can't silently drop it."""
    _skip_if_no_database()

    doctor_id = patient_user_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Booking Id Regression")
                patient_user_id = _make_patient(cur, "patient-booking-id-regression@example.com")
                booking_id = _make_slot_and_booking(cur, doctor_id, patient_user_id, start_offset_hours=1)
            conn.commit()

        upcoming = doctor_appointments(doctor_id, "upcoming")
        assert len(upcoming) == 1
        assert "booking_id" in upcoming[0]
        assert upcoming[0]["booking_id"] == booking_id
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                if doctor_id:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                if patient_user_id:
                    cur.execute("DELETE FROM users WHERE user_id = %s", (patient_user_id,))
            conn.commit()


def test_shared_patient_detail_shows_only_this_doctors_own_visits():
    """A patient who has been treated by two different doctors is a real, legitimate case
    (unlike the 'stranger patient' case above, which is a security violation). Doctor A's
    patient-detail view for that shared patient must show only Doctor A's own visit(s) —
    never Doctor C's — even though the patient itself is valid for both."""
    _skip_if_no_database()

    doctor_a_id = doctor_c_id = patient_user_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_a_id = _make_doctor(cur, "Dr. A Shared Patient")
                doctor_c_id = _make_doctor(cur, "Dr. C Shared Patient")
                patient_user_id = _make_patient(cur, "shared-patient-regression@example.com")

                # Same patient, one completed visit with each doctor.
                booking_with_a = _make_slot_and_booking(cur, doctor_a_id, patient_user_id, start_offset_hours=-2)
                booking_with_c = _make_slot_and_booking(cur, doctor_c_id, patient_user_id, start_offset_hours=-1)
            conn.commit()

        detail_for_a = doctor_patient_detail(doctor_a_id, patient_user_id)
        assert detail_for_a is not None
        visit_ids_for_a = {v["booking_id"] for v in detail_for_a["visits"]}
        assert visit_ids_for_a == {booking_with_a}
        assert booking_with_c not in visit_ids_for_a

        detail_for_c = doctor_patient_detail(doctor_c_id, patient_user_id)
        assert detail_for_c is not None
        visit_ids_for_c = {v["booking_id"] for v in detail_for_c["visits"]}
        assert visit_ids_for_c == {booking_with_c}
        assert booking_with_a not in visit_ids_for_c

        # The patients list (not just detail) must also scope each doctor to their own visit count.
        a_patients = {p["patient_id"]: p for p in doctor_patients(doctor_a_id)}
        assert a_patients[patient_user_id]["visit_count"] == 1
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                for doctor_id in (doctor_a_id, doctor_c_id):
                    if doctor_id:
                        cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                if patient_user_id:
                    cur.execute("DELETE FROM users WHERE user_id = %s", (patient_user_id,))
            conn.commit()


def test_brand_new_doctor_with_zero_bookings_sees_empty_state_not_an_error():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Zero Bookings")
            conn.commit()

        assert doctor_appointments(doctor_id, "upcoming") == []
        assert doctor_appointments(doctor_id, "past") == []
        assert doctor_patients(doctor_id) == []
    finally:
        if doctor_id:
            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                conn.commit()
