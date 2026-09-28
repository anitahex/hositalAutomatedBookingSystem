"""Integration coverage for sharing a signed note with the patient, against a real database.

Two properties can only be proven by a real query:
  1. Only a SIGNED note can ever become patient-visible — the guard lives in the UPDATE's
     WHERE clause, not in Python.
  2. list_shared_notes_for_patient scopes by patient_id in SQL, so one patient can never
     reach another's shared note.

Skips (not fails) if no database is reachable.
"""

from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.soap_notes import (
    get_soap_note, list_shared_notes_for_patient, share_soap_note,
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
    from app.services.consults import ensure_consult_schema
    from app.services.soap_notes import ensure_soap_schema

    ensure_booking_schema(conn)
    ensure_consult_schema(conn)
    ensure_soap_schema(conn)


def _make_doctor(cur, name):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, 'Testing', 1, TRUE) RETURNING doctor_id""",
        (name,),
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


def _make_consult_with_note(cur, doctor_id, patient_id, *, note_status):
    start_time = datetime.now() - timedelta(hours=2)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
           VALUES (%s, %s, %s, FALSE) RETURNING slot_id""",
        (doctor_id, start_time, start_time + timedelta(minutes=30)),
    )
    slot_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, 'completed') RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start_time, start_time + timedelta(minutes=30)),
    )
    booking_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO consultations (booking_id, doctor_id, patient_id, status, transcript_source, ended_at)
           VALUES (%s, %s, %s, 'transcript_ready', 'batch', NOW()) RETURNING id""",
        (booking_id, doctor_id, patient_id),
    )
    consultation_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO soap_notes (consultation_id, doctor_id, patient_id,
                                   subjective, objective, assessment, plan,
                                   field_citations, confidence_flags, status,
                                   generated_at, signed_at, signed_by)
           VALUES (%s, %s, %s, 'Headaches improving', 'BP 128/82', 'Migraine', 'Continue',
                   '{"subjective": ["seg-1"]}'::jsonb, '{"plan": true}'::jsonb, %s, NOW(),
                   CASE WHEN %s THEN NOW() END, %s)""",
        (
            consultation_id, doctor_id, patient_id, note_status,
            note_status == "signed", doctor_id if note_status == "signed" else None,
        ),
    )
    return booking_id, consultation_id


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


@pytest.mark.parametrize("unsignable_status", ["draft", "stale"])
def test_an_unsigned_note_can_never_be_shared(unsignable_status):
    """The single most important rule here: an unsigned note is AI output no clinician
    has accepted responsibility for, and must never reach a patient."""
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, f"Dr. Unsigned {unsignable_status}")
                patient_id = _make_patient(cur, f"share-{unsignable_status}@example.com")
                booking_id, consultation_id = _make_consult_with_note(
                    cur, doctor_id, patient_id, note_status=unsignable_status
                )
            conn.commit()

        with pytest.raises(PermissionError):
            share_soap_note(consultation_id, doctor_id)

        # And nothing became patient-visible as a side effect of the attempt.
        assert list_shared_notes_for_patient(patient_id, [booking_id]) == {}
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_sharing_a_signed_note_makes_it_visible_to_that_patient_only():
    _skip_if_no_database()

    doctor_id = patient_a = patient_b = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Share")
                patient_a = _make_patient(cur, "share-patient-a@example.com")
                patient_b = _make_patient(cur, "share-patient-b@example.com")
                booking_a, consult_a = _make_consult_with_note(
                    cur, doctor_id, patient_a, note_status="signed"
                )
            conn.commit()

        # Signed but not yet shared — invisible.
        assert list_shared_notes_for_patient(patient_a, [booking_a]) == {}

        share_soap_note(consult_a, doctor_id)

        visible = list_shared_notes_for_patient(patient_a, [booking_a])
        assert booking_a in visible
        assert visible[booking_a]["subjective"] == "Headaches improving"
        assert visible[booking_a]["doctor_name"] == "Dr. Share"

        # Patient B cannot reach it even while supplying a real booking_id.
        assert list_shared_notes_for_patient(patient_b, [booking_a]) == {}
    finally:
        _cleanup((doctor_id,), (patient_a, patient_b))


def test_patient_projection_never_carries_clinician_only_signals():
    """field_citations and confidence_flags exist on the row and are deliberately not
    selected — a patient seeing 'Needs review' on their assessment would reasonably hear
    'my diagnosis is uncertain'."""
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Projection")
                patient_id = _make_patient(cur, "share-projection@example.com")
                booking_id, consultation_id = _make_consult_with_note(
                    cur, doctor_id, patient_id, note_status="signed"
                )
            conn.commit()

        share_soap_note(consultation_id, doctor_id)
        summary = list_shared_notes_for_patient(patient_id, [booking_id])[booking_id]

        forbidden = {
            "field_citations", "confidence_flags", "source_transcript_type",
            "status", "addenda", "signed_by", "shared_by",
        }
        assert forbidden.isdisjoint(summary.keys())
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_sharing_twice_is_idempotent_and_does_not_move_the_timestamp():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Idempotent")
                patient_id = _make_patient(cur, "share-idempotent@example.com")
                _, consultation_id = _make_consult_with_note(
                    cur, doctor_id, patient_id, note_status="signed"
                )
            conn.commit()

        first = share_soap_note(consultation_id, doctor_id)
        second = share_soap_note(consultation_id, doctor_id)

        assert first["shared_with_patient_at"] is not None
        assert second["shared_with_patient_at"] == first["shared_with_patient_at"]

        # Exactly one audit row — an idempotent no-op must not manufacture a second
        # disclosure event in the audit trail.
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT COUNT(*) FROM consult_audit_log
                       WHERE consultation_id = %s AND action_type = 'consult_soap_note_shared'""",
                    (consultation_id,),
                )
                assert cur.fetchone()[0] == 1
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_sharing_does_not_alter_the_clinical_content():
    """Sharing is a disclosure decision, not an edit. A signed note is immutable."""
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Immutable")
                patient_id = _make_patient(cur, "share-immutable@example.com")
                _, consultation_id = _make_consult_with_note(
                    cur, doctor_id, patient_id, note_status="signed"
                )
            conn.commit()

        before = get_soap_note(consultation_id, doctor_id)
        share_soap_note(consultation_id, doctor_id)
        after = get_soap_note(consultation_id, doctor_id)

        for field in ("subjective", "objective", "assessment", "plan", "status", "signed_at"):
            assert before[field] == after[field]
    finally:
        _cleanup((doctor_id,), (patient_id,))
