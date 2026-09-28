"""Integration coverage for the doctor AI-review queue against a real database.

list_reviews_for_doctor() filters by doctor_id in raw SQL. A route-level unit test can
prove the right doctor_id is passed through (test_doctor_reviews.py does), but only a
real query can prove doctor A's queue actually excludes doctor B's consults and notes.
That, plus the three pending item types and the counts, is what this file checks
(mirrors test_doctor_appointments_integration.py's rationale).

Skips (not fails) if no database is reachable.
"""

from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.soap_notes import list_reviews_for_doctor


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
        "INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id",
        (email,),
    )
    user_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
           VALUES (%s, %s, 30, '9999999999', 'Test address', %s, 'O+')""",
        (user_id, f"Patient {email}", email),
    )
    return user_id


def _make_booking(cur, doctor_id, patient_id, start_offset_hours=-2):
    """Past-dated by default: a consult can only reach transcript_ready after the visit.
    Mirrors test_doctor_appointments_integration's is_booked discipline so
    ensure_booking_schema's idempotent backfill can't duplicate this booking."""
    start_time = datetime.now() + timedelta(hours=start_offset_hours)
    end_time = start_time + timedelta(minutes=30)
    is_booked = start_offset_hours > 0
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
           VALUES (%s, %s, %s, %s, %s) RETURNING slot_id""",
        (doctor_id, start_time, end_time, is_booked, patient_id if is_booked else None),
    )
    slot_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, 'completed') RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start_time, end_time),
    )
    return str(cur.fetchone()[0])


def _make_consult(cur, booking_id, doctor_id, patient_id, *, status="transcript_ready",
                  transcript_source="batch"):
    cur.execute(
        """INSERT INTO consultations (booking_id, doctor_id, patient_id, status,
                                      transcript_source, ended_at)
           VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING id""",
        (booking_id, doctor_id, patient_id, status, transcript_source),
    )
    return str(cur.fetchone()[0])


def _make_note(cur, consultation_id, doctor_id, patient_id, *, status="draft",
               confidence_flags="{}", edited=False, signed=False):
    cur.execute(
        """INSERT INTO soap_notes (consultation_id, doctor_id, patient_id,
                                   subjective, objective, assessment, plan,
                                   confidence_flags, status, generated_at,
                                   edited_at, signed_at, signed_by)
           VALUES (%s, %s, %s, 'S', 'O', 'A', 'P', %s::jsonb, %s, NOW(),
                   CASE WHEN %s THEN NOW() END,
                   CASE WHEN %s THEN NOW() END,
                   %s)
           RETURNING id""",
        (
            consultation_id, doctor_id, patient_id, confidence_flags, status,
            edited, signed, doctor_id if signed else None,
        ),
    )
    return str(cur.fetchone()[0])


def _ensure_review_schema(conn):
    """The consult/SOAP tables live only in Alembic + the runtime ensure_* helpers —
    they are NOT in app/db/schema.sql — so a database bootstrapped from schema.sql alone
    would not have them. Create them the same way the application does."""
    from app.services.appointments import ensure_booking_schema
    from app.services.consults import ensure_consult_schema
    from app.services.soap_notes import ensure_soap_schema

    ensure_booking_schema(conn)
    ensure_consult_schema(conn)
    ensure_soap_schema(conn)


def _cleanup(doctor_ids, user_ids):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for doctor_id in doctor_ids:
                if doctor_id:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
            for user_id in user_ids:
                if user_id:
                    cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()


def test_doctor_cannot_see_another_doctors_reviews():
    """The property this file exists for: the doctor_id filter lives in the SQL, so
    doctor A's queue must not contain doctor B's consult even though both are pending."""
    _skip_if_no_database()

    doctor_a = doctor_b = patient_a = patient_b = None
    try:
        with connect_db() as conn:
            _ensure_review_schema(conn)
            with conn.cursor() as cur:
                doctor_a = _make_doctor(cur, "Dr. A Reviews")
                doctor_b = _make_doctor(cur, "Dr. B Reviews")
                patient_a = _make_patient(cur, "review-patient-a@example.com")
                patient_b = _make_patient(cur, "review-patient-b@example.com")

                booking_a = _make_booking(cur, doctor_a, patient_a)
                booking_b = _make_booking(cur, doctor_b, patient_b)
                consult_a = _make_consult(cur, booking_a, doctor_a, patient_a)
                consult_b = _make_consult(cur, booking_b, doctor_b, patient_b)
                _make_note(cur, consult_a, doctor_a, patient_a)
                _make_note(cur, consult_b, doctor_b, patient_b)
            conn.commit()

        a_result = list_reviews_for_doctor(doctor_a)
        a_consult_ids = {r["consultation_id"] for r in a_result["reviews"]}
        assert consult_a in a_consult_ids
        assert consult_b not in a_consult_ids

        b_result = list_reviews_for_doctor(doctor_b)
        b_consult_ids = {r["consultation_id"] for r in b_result["reviews"]}
        assert consult_b in b_consult_ids
        assert consult_a not in b_consult_ids

        # Counts must be scoped too — a leaked count is still a leak.
        assert a_result["counts"]["pending"] == 1
        assert b_result["counts"]["pending"] == 1
    finally:
        _cleanup((doctor_a, doctor_b), (patient_a, patient_b))


def test_pending_queue_surfaces_all_three_item_types():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_review_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Item Types")
                patient_id = _make_patient(cur, "review-item-types@example.com")

                # 1. transcript_ready with no note at all
                b1 = _make_booking(cur, doctor_id, patient_id, start_offset_hours=-5)
                c1 = _make_consult(cur, b1, doctor_id, patient_id)

                # 2. a draft note
                b2 = _make_booking(cur, doctor_id, patient_id, start_offset_hours=-4)
                c2 = _make_consult(cur, b2, doctor_id, patient_id)
                _make_note(cur, c2, doctor_id, patient_id, status="draft")

                # 3. a stale note — blocked from signing until regenerated
                b3 = _make_booking(cur, doctor_id, patient_id, start_offset_hours=-3)
                c3 = _make_consult(cur, b3, doctor_id, patient_id)
                _make_note(cur, c3, doctor_id, patient_id, status="stale")
            conn.commit()

        result = list_reviews_for_doctor(doctor_id)
        by_consult = {r["consultation_id"]: r for r in result["reviews"]}

        assert by_consult[c1]["item_type"] == "not_generated"
        assert by_consult[c2]["item_type"] == "draft"
        assert by_consult[c3]["item_type"] == "stale"

        assert result["counts"]["pending"] == 3
        assert result["counts"]["not_generated"] == 1
        assert result["counts"]["draft"] == 1
        assert result["counts"]["stale"] == 1

        # Stale is pinned first because it *blocks* signing, not because it is oldest —
        # c3 is the most recent of the three by appointment time.
        assert result["reviews"][0]["consultation_id"] == c3
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_signed_notes_leave_pending_and_appear_in_completed():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_review_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Signed")
                patient_id = _make_patient(cur, "review-signed@example.com")
                booking_id = _make_booking(cur, doctor_id, patient_id)
                consult_id = _make_consult(cur, booking_id, doctor_id, patient_id)
                _make_note(cur, consult_id, doctor_id, patient_id, status="signed", signed=True)
            conn.commit()

        pending = list_reviews_for_doctor(doctor_id, scope="pending")
        assert consult_id not in {r["consultation_id"] for r in pending["reviews"]}
        assert pending["counts"]["pending"] == 0

        completed = list_reviews_for_doctor(doctor_id, scope="completed")
        rows = {r["consultation_id"]: r for r in completed["reviews"]}
        assert consult_id in rows
        assert rows[consult_id]["item_type"] == "signed"
        assert rows[consult_id]["signed_at"] is not None

        # The counts are always the PENDING counts, whichever scope was asked for —
        # they drive the dashboard's "what still needs me" cards.
        assert completed["counts"]["pending"] == 0
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_discarded_consult_does_not_appear_as_outstanding_work():
    """discard_consult() deletes the transcript and flips the consult to 'discarded' but
    leaves any existing soap_notes row behind — without the c.status filter that orphan
    would surface forever as phantom work the doctor can never clear."""
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_review_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Discarded")
                patient_id = _make_patient(cur, "review-discarded@example.com")
                booking_id = _make_booking(cur, doctor_id, patient_id)
                consult_id = _make_consult(cur, booking_id, doctor_id, patient_id, status="discarded")
                _make_note(cur, consult_id, doctor_id, patient_id, status="draft")
            conn.commit()

        result = list_reviews_for_doctor(doctor_id)
        assert consult_id not in {r["consultation_id"] for r in result["reviews"]}
        assert result["counts"]["pending"] == 0
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_in_progress_consult_is_not_yet_a_review():
    """A consult still recording has nothing to document yet — it must not appear."""
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_review_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Recording")
                patient_id = _make_patient(cur, "review-recording@example.com")
                booking_id = _make_booking(cur, doctor_id, patient_id)
                consult_id = _make_consult(cur, booking_id, doctor_id, patient_id, status="recording")
            conn.commit()

        result = list_reviews_for_doctor(doctor_id)
        assert consult_id not in {r["consultation_id"] for r in result["reviews"]}
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_triage_flags_come_through_from_real_rows():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_review_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Flags")
                patient_id = _make_patient(cur, "review-flags@example.com")
                booking_id = _make_booking(cur, doctor_id, patient_id)
                consult_id = _make_consult(
                    cur, booking_id, doctor_id, patient_id, transcript_source="live_fallback"
                )
                _make_note(
                    cur, consult_id, doctor_id, patient_id, status="draft",
                    confidence_flags='{"subjective": true, "plan": true, "objective": false}',
                    edited=True,
                )
            conn.commit()

        result = list_reviews_for_doctor(doctor_id)
        row = next(r for r in result["reviews"] if r["consultation_id"] == consult_id)

        assert row["low_quality_transcript"] is True
        assert row["low_confidence_fields"] == 2
        assert row["is_edited"] is True
        assert result["counts"]["low_quality_transcript"] == 1
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_limit_is_clamped_to_the_documented_maximum():
    """An unbounded client-supplied limit must never reach the database."""
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_review_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Limit")
                patient_id = _make_patient(cur, "review-limit@example.com")
                booking_id = _make_booking(cur, doctor_id, patient_id)
                _make_consult(cur, booking_id, doctor_id, patient_id)
            conn.commit()

        # Both extremes must return without error rather than being passed through.
        assert len(list_reviews_for_doctor(doctor_id, limit=10_000_000)["reviews"]) == 1
        assert len(list_reviews_for_doctor(doctor_id, limit=0)["reviews"]) == 1
    finally:
        _cleanup((doctor_id,), (patient_id,))
