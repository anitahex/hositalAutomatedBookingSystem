"""Review phase 2 against a real database: the activity log links to its consults, and a
patient's visits say what actually happened.

  - Each feed event carries what the UI needs to open its appointment. The docstring had
    promised a link "through to the consult" while the UI received only consultation_id
    and did nothing with it.
  - An event whose consult was later discarded is NOT openable — no screen shows a
    discarded consult, so a link would land on nothing — and the discard itself now
    appears in the feed instead of being dropped by the allowlist.
  - Visit cards on a patient's page printed "No clinical note yet" for every visit. They
    now carry the latest non-discarded consult and its note — and a booking with two
    consults (one discarded, one restarted) is still ONE visit.

Follows test_doctor_workspace_integration.py's fixture conventions.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.appointments import doctor_patient_detail
from app.services.doctor_ai_activity import get_activity_log


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _booking(cur, doctor_id, patient_id, hours_ago):
    start = datetime.now() - timedelta(hours=hours_ago)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
           VALUES (%s, %s, %s, TRUE, %s) RETURNING slot_id""",
        (doctor_id, start, start + timedelta(minutes=30), patient_id),
    )
    slot_id = cur.fetchone()[0]
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, 'completed') RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start, start + timedelta(minutes=30)),
    )
    return str(cur.fetchone()[0])


def _consult(cur, booking_id, doctor_id, patient_id, status, minutes_ago):
    cur.execute(
        """INSERT INTO consultations (booking_id, doctor_id, patient_id, status, transcript_source,
                                      ended_at, created_at)
           VALUES (%s, %s, %s, %s, 'batch', NOW(), NOW() - make_interval(mins => %s)) RETURNING id""",
        (booking_id, doctor_id, patient_id, status, minutes_ago),
    )
    return str(cur.fetchone()[0])


def _note(cur, consultation_id, doctor_id, patient_id, status):
    cur.execute(
        """INSERT INTO soap_notes (consultation_id, doctor_id, patient_id, subjective, objective,
                                   assessment, plan, status, generated_at)
           VALUES (%s, %s, %s, 'S', 'O', 'A', 'P', %s, NOW())""",
        (consultation_id, doctor_id, patient_id, status),
    )


def _audit(cur, consultation_id, doctor_id, action):
    cur.execute(
        """INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata)
           VALUES (%s, %s, %s, '{"style": "concise"}'::jsonb)""",
        (consultation_id, doctor_id, action),
    )


@pytest.fixture
def world():
    _skip_if_no_database()
    ids = {}
    try:
        with connect_db() as conn:
            from app.services.appointments import ensure_booking_schema
            from app.services.consults import ensure_consult_schema
            from app.services.soap_notes import ensure_soap_schema
            ensure_booking_schema(conn)
            ensure_consult_schema(conn)
            ensure_soap_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO doctors (name, department, experience_years, is_active)
                       VALUES ('Dr. Phase Two', 'Orthopedics', 1, TRUE) RETURNING doctor_id"""
                )
                ids["doctor"] = doctor = str(cur.fetchone()[0])
                email = f"p2-{uuid.uuid4().hex[:10]}@example.com"
                cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id", (email,))
                ids["patient"] = patient = str(cur.fetchone()[0])
                cur.execute(
                    """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
                       VALUES (%s, 'Phase Two Patient', 30, '9999999999', 'Test', %s, 'O+')""",
                    (patient, email),
                )

                # Visit 1: a signed note.
                ids["signed_booking"] = b1 = _booking(cur, doctor, patient, 48)
                ids["signed_consult"] = c1 = _consult(cur, b1, doctor, patient, "transcript_ready", 60)
                _note(cur, c1, doctor, patient, "signed")
                _audit(cur, c1, doctor, "consult_soap_note_generated")

                # Visit 2: discarded, then restarted — two consults on ONE booking.
                ids["restarted_booking"] = b2 = _booking(cur, doctor, patient, 24)
                ids["discarded_consult"] = c2a = _consult(cur, b2, doctor, patient, "discarded", 50)
                _note(cur, c2a, doctor, patient, "draft")
                _audit(cur, c2a, doctor, "consult_soap_note_generated")
                _audit(cur, c2a, doctor, "consult_discarded")
                ids["restarted_consult"] = c2b = _consult(cur, b2, doctor, patient, "transcript_ready", 10)
                _note(cur, c2b, doctor, patient, "draft")

                # Visit 3: nothing recorded.
                ids["empty_booking"] = _booking(cur, doctor, patient, 2)

                # Visit 4: its only consult was discarded, leaving a draft note behind.
                ids["discarded_only_booking"] = b4 = _booking(cur, doctor, patient, 12)
                c4 = _consult(cur, b4, doctor, patient, "discarded", 30)
                _note(cur, c4, doctor, patient, "draft")
            conn.commit()
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                if ids.get("doctor"):
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (ids["doctor"],))
                if ids.get("patient"):
                    cur.execute("DELETE FROM users WHERE user_id = %s", (ids["patient"],))
            conn.commit()


# ---- the activity log ----

def test_a_feed_event_carries_what_opening_its_appointment_needs(world):
    events = get_activity_log(world["doctor"])["events"]
    signed = next(e for e in events if e["consultation_id"] == world["signed_consult"])

    assert signed["openable"] is True
    assert signed["booking_id"] == world["signed_booking"]
    assert signed["patient_id"] == world["patient"]
    assert signed["patient_name"] == "Phase Two Patient"
    assert signed["appointment_start"] and signed["department"] == "Orthopedics"


def test_an_event_for_a_discarded_consult_is_not_openable(world):
    """No screen shows a discarded consult; a link would land on nothing."""
    events = get_activity_log(world["doctor"])["events"]
    for event in events:
        if event["consultation_id"] == world["discarded_consult"]:
            assert event["openable"] is False
            assert event["consult_status"] == "discarded"


def test_discarding_a_consult_appears_in_the_feed(world):
    """It was recorded in the audit log and dropped by the feed's allowlist, so the feed
    showed a drafted note with no hint of what became of it."""
    actions = [e["action"] for e in get_activity_log(world["doctor"])["events"]]
    assert "consult_discarded" in actions


def test_the_feed_still_never_leaks_unlisted_metadata(world):
    """The added consult fields must not become a way round the metadata allowlist."""
    for event in get_activity_log(world["doctor"])["events"]:
        assert set(event["detail"]) <= {"style", "reason", "section", "fields", "document_id"}


# ---- visit cards ----

def _visits(world):
    detail = doctor_patient_detail(world["doctor"], world["patient"])
    return {visit["booking_id"]: visit for visit in detail["visits"]}, detail["visits"]


def test_a_visit_reports_its_real_note_state(world):
    by_booking, _ = _visits(world)
    assert by_booking[world["signed_booking"]]["note_status"] == "signed"
    assert by_booking[world["signed_booking"]]["consult_id"] == world["signed_consult"]
    assert by_booking[world["empty_booking"]]["consult_id"] is None
    assert by_booking[world["empty_booking"]]["note_status"] is None


def test_a_restarted_visit_is_one_visit_showing_the_live_consult(world):
    """Two consults on one booking. A plain join listed the visit twice; the discarded
    consult's leftover draft must not be what the card reports."""
    by_booking, visits = _visits(world)
    assert [v["booking_id"] for v in visits].count(world["restarted_booking"]) == 1
    assert by_booking[world["restarted_booking"]]["consult_id"] == world["restarted_consult"]


def test_a_visit_whose_only_consult_was_discarded_reports_nothing_recorded(world):
    """Its leftover draft must not be reported as 'awaiting your review' — there is nowhere
    to review it, because every screen hides discarded consults."""
    by_booking, _ = _visits(world)
    visit = by_booking[world["discarded_only_booking"]]
    assert visit["consult_id"] is None
    assert visit["note_status"] is None

