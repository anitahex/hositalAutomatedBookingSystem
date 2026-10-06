"""A consult whose note is signed is part of the patient's record.

  - discarding it is refused, and nothing is deleted
  - a consult with only a draft can still be discarded, as before
  - a discarded consult's note cannot then be signed
  - migration 0035 puts back the consults discarded after signing (only those, and not one
    whose booking has had another consult since), and audits each

The migration is run inside a transaction that is rolled back, so it leaves nothing behind —
including on any real row of the database the tests run against.
"""
from __future__ import annotations

import importlib.util
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.db.connection import connect_db
from app.services.consults import ConsultSigned, discard_consult
from app.services.soap_notes import sign_soap_note

MIGRATION = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0035_restore_signed_consults.py"


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _doctor(cur):
    cur.execute("""INSERT INTO doctors (name, department, experience_years, is_active)
                   VALUES ('Dr. Signed Consult', 'Testing', 1, TRUE) RETURNING doctor_id""")
    return str(cur.fetchone()[0])


def _booking(cur, doctor_id):
    when = datetime.now() - timedelta(days=1)
    cur.execute("""INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
                   VALUES (%s, %s, %s, TRUE) RETURNING slot_id""", (doctor_id, when, when + timedelta(minutes=30)))
    slot = cur.fetchone()[0]
    cur.execute("""INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
                   VALUES (%s, %s, 'patient-signed', %s, %s, 'completed') RETURNING booking_id""",
                (slot, doctor_id, when, when + timedelta(minutes=30)))
    return str(cur.fetchone()[0])


def _consult(cur, doctor_id, booking_id, *, status="transcript_ready", note=None, signed_at=None):
    """A consult with one transcript segment and, optionally, a note ('draft' or 'signed')."""
    cur.execute("""INSERT INTO consultations (booking_id, doctor_id, patient_id, status, transcript_source)
                   VALUES (%s, %s, 'patient-signed', %s, 'batch') RETURNING id""", (booking_id, doctor_id, status))
    consult = str(cur.fetchone()[0])
    cur.execute("""INSERT INTO transcript_segments (consultation_id, speaker, start_ms, end_ms, text, is_final)
                   VALUES (%s, 'doctor', 0, 1000, 'hello', TRUE)""", (consult,))
    if note:
        cur.execute("""INSERT INTO soap_notes (consultation_id, doctor_id, patient_id, subjective, objective,
                                               assessment, plan, status, generated_at, signed_at)
                       VALUES (%s, %s, 'patient-signed', 'S', 'O', 'A', 'P', %s, NOW(), %s)""",
                    (consult, doctor_id, note, (signed_at or datetime.now()) if note == "signed" else None))
    return consult


@pytest.fixture
def doctor():
    _skip_if_no_database()
    with connect_db() as conn:
        with conn.cursor() as cur:
            doctor_id = _doctor(cur)
        conn.commit()
    try:
        yield doctor_id
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
            conn.commit()


def _make(doctor_id, **kwargs):
    with connect_db() as conn:
        with conn.cursor() as cur:
            consult = _consult(cur, doctor_id, _booking(cur, doctor_id), **kwargs)
        conn.commit()
    return consult


def _status_and_segments(consult):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM consultations WHERE id = %s", (consult,))
            status = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM transcript_segments WHERE consultation_id = %s", (consult,))
            segments = cur.fetchone()[0]
            cur.execute("SELECT status FROM soap_notes WHERE consultation_id = %s", (consult,))
            note = cur.fetchone()
        conn.commit()
    return status, segments, note[0] if note else None


# ---- from now on ----

def test_a_consult_with_a_signed_note_cannot_be_discarded(doctor):
    consult = _make(doctor, note="signed")
    with pytest.raises(ConsultSigned):
        discard_consult(consult, doctor)
    # Nothing was deleted or changed.
    assert _status_and_segments(consult) == ("transcript_ready", 1, "signed")


def test_a_consult_with_only_a_draft_can_still_be_discarded(doctor):
    consult = _make(doctor, note="draft")
    assert discard_consult(consult, doctor)["row"]["status"] == "discarded"
    assert _status_and_segments(consult) == ("discarded", 0, "draft")


def test_a_discarded_consults_note_cannot_then_be_signed(doctor):
    consult = _make(doctor, note="draft")
    discard_consult(consult, doctor)
    with pytest.raises(PermissionError):
        sign_soap_note(consult, doctor)
    assert _status_and_segments(consult)[2] == "draft"


# ---- migration 0035: the ones discarded before ----

def _run_migration_and_read(setup):
    """Runs 0035's upgrade on a connection, after `setup(cursor)` inserted rows on the same
    connection; reads the result; rolls everything back."""
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine

    spec = importlib.util.spec_from_file_location("migration_0035", MIGRATION)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                cursor = conn.connection.dbapi_connection.cursor()
                ids = setup(cursor)
                with Operations.context(MigrationContext.configure(conn)):
                    migration.upgrade()
                cursor.execute("SELECT id::text, status FROM consultations WHERE id::text = ANY(%s)",
                               (list(ids.values()),))
                statuses = dict(cursor.fetchall())
                cursor.execute("""SELECT consultation_id::text FROM consult_audit_log
                                  WHERE action_type = 'consult_restored_signed' AND consultation_id::text = ANY(%s)""",
                               (list(ids.values()),))
                audited = {row[0] for row in cursor.fetchall()}
                return {name: (statuses[consult], consult in audited) for name, consult in ids.items()}
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def test_the_migration_restores_only_consults_discarded_after_signing():
    _skip_if_no_database()

    def setup(cur):
        doctor = _doctor(cur)
        signed = _consult(cur, doctor, _booking(cur, doctor), status="discarded", note="signed")
        draft = _consult(cur, doctor, _booking(cur, doctor), status="discarded", note="draft")
        bare = _consult(cur, doctor, _booking(cur, doctor), status="discarded")
        # Signed, discarded — and the booking has had a new consult started since.
        restarted_booking = _booking(cur, doctor)
        superseded = _consult(cur, doctor, restarted_booking, status="discarded", note="signed")
        _consult(cur, doctor, restarted_booking, status="not_started")
        # Production's case: one booking with TWO consults, each signed and then discarded.
        # A booking may hold one live consult, so only the later-signed comes back; restoring
        # both broke the unique index and stopped the backend from starting.
        twice = _booking(cur, doctor)
        earlier = _consult(cur, doctor, twice, status="discarded", note="signed",
                           signed_at=datetime.now() - timedelta(hours=3))
        later = _consult(cur, doctor, twice, status="discarded", note="signed",
                         signed_at=datetime.now() - timedelta(hours=1))
        return {"signed": signed, "draft": draft, "bare": bare, "superseded": superseded,
                "twice_earlier": earlier, "twice_later": later}

    result = _run_migration_and_read(setup)
    assert result == {
        "signed": ("transcript_ready", True),
        "draft": ("discarded", False),
        "bare": ("discarded", False),
        "superseded": ("discarded", False),
        "twice_earlier": ("discarded", False),
        "twice_later": ("transcript_ready", True),
    }
