"""Integration coverage for doctor-authored clinical items against a real database.

Three things only real SQL can prove: the ownership filter actually excludes another
doctor's consult, the approve transition is genuinely one-way at the database level (the
guard is in the UPDATE's WHERE clause), and each action writes its audit row.

Skips (not fails) if no database is reachable.
"""

from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.clinical_items import (
    approve_clinical_item, get_clinical_item, save_clinical_item,
)


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _ensure_schema(conn):
    from app.services.appointments import ensure_booking_schema
    from app.services.clinical_items import ensure_clinical_items_schema
    from app.services.consults import ensure_consult_schema

    ensure_booking_schema(conn)
    ensure_consult_schema(conn)
    ensure_clinical_items_schema(conn)


def _make_consult(cur, doctor_name, email):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, 'Testing', 1, TRUE) RETURNING doctor_id""",
        (doctor_name,),
    )
    doctor_id = str(cur.fetchone()[0])
    cur.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id", (email,)
    )
    user_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
           VALUES (%s, 'Item Patient', 30, '9999999999', 'Addr', %s, 'O+')""",
        (user_id, email),
    )
    start = datetime.now() - timedelta(hours=2)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
           VALUES (%s, %s, %s, FALSE) RETURNING slot_id""",
        (doctor_id, start, start + timedelta(minutes=30)),
    )
    slot_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, 'completed') RETURNING booking_id""",
        (slot_id, doctor_id, user_id, start, start + timedelta(minutes=30)),
    )
    booking_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO consultations (booking_id, doctor_id, patient_id, status, transcript_source, ended_at)
           VALUES (%s, %s, %s, 'transcript_ready', 'batch', NOW()) RETURNING id""",
        (booking_id, doctor_id, user_id),
    )
    return doctor_id, user_id, str(cur.fetchone()[0])


def _cleanup(doctor_ids, user_ids):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for d in doctor_ids:
                if d:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (d,))
            for u in user_ids:
                if u:
                    cur.execute("DELETE FROM users WHERE user_id = %s", (u,))
        conn.commit()


def test_another_doctor_cannot_read_or_write_this_consults_items():
    _skip_if_no_database()

    doctor_a = doctor_b = user_a = user_b = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_a, user_a, consult_a = _make_consult(cur, "Dr. Items A", "items-a@example.com")
                doctor_b, user_b, _ = _make_consult(cur, "Dr. Items B", "items-b@example.com")
            conn.commit()

        save_clinical_item(consult_a, doctor_a, "prescription", "Sumatriptan 50mg PRN")

        # Doctor B holds a real consult of their own, so this is a genuine cross-tenant
        # attempt with a valid session — not merely an unauthenticated call.
        with pytest.raises(ValueError):
            get_clinical_item(consult_a, doctor_b, "prescription")
        with pytest.raises(ValueError):
            save_clinical_item(consult_a, doctor_b, "prescription", "malicious edit")
        with pytest.raises(ValueError):
            approve_clinical_item(consult_a, doctor_b, "prescription")

        # A's record is untouched by any of that.
        assert get_clinical_item(consult_a, doctor_a, "prescription")["content"] == "Sumatriptan 50mg PRN"
    finally:
        _cleanup((doctor_a, doctor_b), (user_a, user_b))


def test_approval_is_one_way_and_locks_the_record():
    _skip_if_no_database()

    doctor_id = user_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id, user_id, consult_id = _make_consult(cur, "Dr. Approve", "items-approve@example.com")
            conn.commit()

        save_clinical_item(consult_id, doctor_id, "care_plan", "Headache diary for four weeks.")
        approved = approve_clinical_item(consult_id, doctor_id, "care_plan")

        assert approved["status"] == "approved"
        assert approved["approved_at"] is not None
        assert approved["approved_by"] == doctor_id

        # Immutable afterwards, and not re-approvable.
        with pytest.raises(PermissionError):
            save_clinical_item(consult_id, doctor_id, "care_plan", "sneaky edit")
        with pytest.raises(PermissionError):
            approve_clinical_item(consult_id, doctor_id, "care_plan")

        assert get_clinical_item(consult_id, doctor_id, "care_plan")["content"] == "Headache diary for four weeks."
    finally:
        _cleanup((doctor_id,), (user_id,))


def test_an_empty_record_cannot_be_approved():
    """Approving nothing would create a signed-off clinical record with no content."""
    _skip_if_no_database()

    doctor_id = user_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id, user_id, consult_id = _make_consult(cur, "Dr. Empty", "items-empty@example.com")
            conn.commit()

        with pytest.raises(ValueError):
            approve_clinical_item(consult_id, doctor_id, "referral")

        save_clinical_item(consult_id, doctor_id, "referral", "   ")
        with pytest.raises(ValueError):
            approve_clinical_item(consult_id, doctor_id, "referral")
    finally:
        _cleanup((doctor_id,), (user_id,))


def test_the_three_kinds_are_independent_of_one_another():
    _skip_if_no_database()

    doctor_id = user_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id, user_id, consult_id = _make_consult(cur, "Dr. Kinds", "items-kinds@example.com")
            conn.commit()

        save_clinical_item(consult_id, doctor_id, "prescription", "Rx content")
        save_clinical_item(consult_id, doctor_id, "referral", "Referral content")
        approve_clinical_item(consult_id, doctor_id, "prescription")

        # Approving one must not lock or alter the others.
        assert get_clinical_item(consult_id, doctor_id, "prescription")["status"] == "approved"
        assert get_clinical_item(consult_id, doctor_id, "referral")["status"] == "draft"
        assert get_clinical_item(consult_id, doctor_id, "care_plan")["content"] == ""

        save_clinical_item(consult_id, doctor_id, "referral", "still editable")
        assert get_clinical_item(consult_id, doctor_id, "referral")["content"] == "still editable"
    finally:
        _cleanup((doctor_id,), (user_id,))


def test_every_action_writes_an_audit_row():
    _skip_if_no_database()

    doctor_id = user_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id, user_id, consult_id = _make_consult(cur, "Dr. Audit", "items-audit@example.com")
            conn.commit()

        save_clinical_item(consult_id, doctor_id, "prescription", "Rx")
        approve_clinical_item(consult_id, doctor_id, "prescription")

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT action_type, COUNT(*) FROM consult_audit_log
                       WHERE consultation_id = %s AND action_type LIKE 'consult_clinical_item%%'
                       GROUP BY action_type""",
                    (consult_id,),
                )
                counts = dict(cur.fetchall())

        assert counts.get("consult_clinical_item_saved", 0) >= 1
        assert counts.get("consult_clinical_item_approved", 0) == 1
    finally:
        _cleanup((doctor_id,), (user_id,))


def test_content_length_is_bounded():
    _skip_if_no_database()

    doctor_id = user_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id, user_id, consult_id = _make_consult(cur, "Dr. Long", "items-long@example.com")
            conn.commit()

        with pytest.raises(ValueError):
            save_clinical_item(consult_id, doctor_id, "prescription", "x" * 50_000)
    finally:
        _cleanup((doctor_id,), (user_id,))
