"""The cross-doctor timeline against a real database.

This is the feature that widened disclosure, so these are the tests that matter most:

  - a treating doctor sees encounters from OTHER doctors and departments
  - an unsigned draft is never shown to anyone but its author — in fact never at all
  - a sensitive specialty's note CONTENT is withheld, while the encounter still appears
  - the timeline never crosses patients
  - filters and the cursor do what they claim

Conventions follow test_doctor_workspace_integration.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.patient_timeline import get_patient_timeline, get_timeline_filters


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _doctor(cur, name, department):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, %s, 1, TRUE) RETURNING doctor_id""",
        (name, department),
    )
    return str(cur.fetchone()[0])


def _patient(cur, email):
    cur.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id", (email,)
    )
    user_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
           VALUES (%s, %s, 30, '9999999999', 'Test', %s, 'O+')""",
        (user_id, f"Patient {email}", email),
    )
    return user_id


def _encounter(cur, doctor_id, patient_id, *, days_ago, status="completed", note=None,
               note_status="signed", booking_note=None):
    """A booking, its consultation, and optionally a SOAP note in a given status."""
    start = datetime.now() - timedelta(days=days_ago)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
           VALUES (%s, %s, %s, TRUE, %s) RETURNING slot_id""",
        (doctor_id, start, start + timedelta(minutes=30), patient_id),
    )
    slot_id = cur.fetchone()[0]
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status, booking_note)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start, start + timedelta(minutes=30), status, booking_note),
    )
    booking_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO consultations (booking_id, doctor_id, patient_id, status)
           VALUES (%s, %s, %s, 'transcript_ready') RETURNING id""",
        (booking_id, doctor_id, patient_id),
    )
    consult_id = str(cur.fetchone()[0])
    if note:
        cur.execute(
            """INSERT INTO soap_notes (consultation_id, doctor_id, patient_id, assessment, plan,
                                       status, generated_at, signed_at)
               VALUES (%s, %s, %s, %s, 'Plan text', %s, NOW(),
                       CASE WHEN %s = 'signed' THEN NOW() ELSE NULL END)""",
            (consult_id, doctor_id, patient_id, note, note_status, note_status),
        )
    return booking_id


@pytest.fixture
def world():
    """One patient seen by three doctors: their own, a cardiologist, and a psychiatrist."""
    _skip_if_no_database()
    ids = {}
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                ids["patient"] = _patient(cur, f"tl-{uuid.uuid4().hex[:8]}@example.com")
                ids["mine"] = _doctor(cur, "Dr. Mine", "Nephrology")
                ids["cardio"] = _doctor(cur, "Dr. Cardio", "Cardiology")
                ids["psych"] = _doctor(cur, "Dr. Psych", "Psychiatry")

                ids["b_mine"] = _encounter(cur, ids["mine"], ids["patient"], days_ago=1,
                                           note="Stable renal function.")
                ids["b_cardio"] = _encounter(cur, ids["cardio"], ids["patient"], days_ago=5,
                                             note="Atrial fibrillation, rate controlled.")
                ids["b_psych"] = _encounter(cur, ids["psych"], ids["patient"], days_ago=10,
                                            note="Generalised anxiety disorder.",
                                            booking_note="Patient reports panic episodes.")
                ids["b_draft"] = _encounter(cur, ids["cardio"], ids["patient"], days_ago=20,
                                            note="Unsigned draft content.", note_status="draft")
            conn.commit()
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                for key in ("mine", "cardio", "psych"):
                    if ids.get(key):
                        cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (ids[key],))
                if ids.get("patient"):
                    cur.execute("DELETE FROM users WHERE user_id = %s", (ids["patient"],))
            conn.commit()


def _by_department(timeline):
    return {e["department"]: e for e in timeline["encounters"]}


# ---- the widening ----

def test_a_treating_doctor_sees_other_doctors_encounters(world):
    """The whole point of the feature. Before this, a doctor saw only their own."""
    timeline = get_patient_timeline(world["mine"], world["patient"], "Nephrology")
    departments = {e["department"] for e in timeline["encounters"]}

    assert {"Nephrology", "Cardiology", "Psychiatry"} <= departments


def test_another_doctors_signed_note_is_readable(world):
    # Keyed by booking, not department: the fixture deliberately gives Cardiology two
    # encounters — one signed, one an unsigned draft — so a department lookup would
    # collapse them and test whichever came last.
    timeline = get_patient_timeline(world["mine"], world["patient"], "Nephrology")
    cardiology = {e["booking_id"]: e for e in timeline["encounters"]}[world["b_cardio"]]

    assert cardiology["note"]["summary"] == "Atrial fibrillation, rate controlled."
    assert cardiology["is_own"] is False


def test_own_encounters_are_marked_as_such(world):
    timeline = get_patient_timeline(world["mine"], world["patient"], "Nephrology")
    assert _by_department(timeline)["Nephrology"]["is_own"] is True


def test_newest_first(world):
    timeline = get_patient_timeline(world["mine"], world["patient"], "Nephrology")
    times = [e["start_time"] for e in timeline["encounters"]]
    assert times == sorted(times, reverse=True)


# ---- what stays withheld ----

def test_an_unsigned_draft_is_never_shown(world):
    """A draft is model output no clinician has taken responsibility for. Showing it in a
    history timeline would launder it into the record by presentation alone."""
    timeline = get_patient_timeline(world["mine"], world["patient"], "Nephrology")
    drafted = next(e for e in timeline["encounters"] if e["booking_id"] == world["b_draft"])

    assert drafted["note"] is None
    assert "Unsigned draft content" not in str(timeline)


def test_a_sensitive_specialtys_note_content_is_withheld(world):
    """The agreed default. A cardiologist sees that a psychiatry visit happened and does
    not see what was written."""
    timeline = get_patient_timeline(world["cardio"], world["patient"], "Cardiology")
    psychiatry = _by_department(timeline)["Psychiatry"]

    assert psychiatry["restricted"] is True
    assert psychiatry["note"]["restricted"] is True
    assert "Generalised anxiety disorder" not in str(timeline)


def test_the_sensitive_encounter_itself_is_still_visible(world):
    """Hiding the visit would misrepresent the record and let a doctor believe there is no
    history when there is. Only the content is held back."""
    timeline = get_patient_timeline(world["cardio"], world["patient"], "Cardiology")
    psychiatry = _by_department(timeline)["Psychiatry"]

    assert psychiatry["department"] == "Psychiatry"
    assert psychiatry["start_time"]
    assert psychiatry["status"] == "completed"


def test_the_booking_note_of_a_sensitive_encounter_is_withheld_too(world):
    """A booking note is the pre-visit clinical summary — exactly as sensitive as the note.
    Withholding one and not the other would leak the same information by another route."""
    timeline = get_patient_timeline(world["cardio"], world["patient"], "Cardiology")

    assert _by_department(timeline)["Psychiatry"]["reason"] is None
    assert "panic episodes" not in str(timeline)


def test_a_psychiatrist_reads_psychiatry_notes_normally(world):
    """The restriction is about disclosure ACROSS specialties, not about making these
    notes unreadable to the people who wrote them."""
    timeline = get_patient_timeline(world["psych"], world["patient"], "Psychiatry")
    psychiatry = _by_department(timeline)["Psychiatry"]

    assert psychiatry["restricted"] is False
    assert psychiatry["note"]["summary"] == "Generalised anxiety disorder."
    assert psychiatry["reason"] == "Patient reports panic episodes."


def test_a_restricted_note_is_distinguishable_from_no_note(world):
    """"Nothing was written" and "something exists and is withheld" must never look the
    same — a doctor acting on the first when the second is true is the whole hazard."""
    timeline = get_patient_timeline(world["cardio"], world["patient"], "Cardiology")
    by_booking = {e["booking_id"]: e for e in timeline["encounters"]}

    assert by_booking[world["b_psych"]]["note"]["restricted"] is True
    assert by_booking[world["b_draft"]]["note"] is None


# ---- scoping ----

def test_the_timeline_never_crosses_patients(world):
    other = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                other = _patient(cur, f"other-{uuid.uuid4().hex[:8]}@example.com")
                _encounter(cur, world["mine"], other, days_ago=2, note="Someone else's note.")
            conn.commit()

        timeline = get_patient_timeline(world["mine"], world["patient"], "Nephrology")
        assert "Someone else" not in str(timeline)
    finally:
        if other:
            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM users WHERE user_id = %s", (other,))
                conn.commit()


# ---- filters and paging ----

def test_filtering_by_department(world):
    timeline = get_patient_timeline(
        world["mine"], world["patient"], "Nephrology", department="Cardiology"
    )
    assert {e["department"] for e in timeline["encounters"]} == {"Cardiology"}


def test_filtering_by_doctor(world):
    timeline = get_patient_timeline(
        world["mine"], world["patient"], "Nephrology", other_doctor_id=world["psych"]
    )
    assert [e["booking_id"] for e in timeline["encounters"]] == [world["b_psych"]]


def test_a_date_range_includes_the_whole_end_day(world):
    """"to 20 Sep" means everything that happened on the 20th, not everything before
    midnight that morning."""
    today = datetime.now().date().isoformat()
    timeline = get_patient_timeline(
        world["mine"], world["patient"], "Nephrology",
        date_from=(datetime.now() - timedelta(days=2)).date().isoformat(),
        date_to=today,
    )
    assert [e["booking_id"] for e in timeline["encounters"]] == [world["b_mine"]]


def test_the_cursor_pages_without_repeating_or_skipping(world):
    first = get_patient_timeline(world["mine"], world["patient"], "Nephrology", limit=2)
    assert len(first["encounters"]) == 2
    assert first["has_more"] is True

    second = get_patient_timeline(
        world["mine"], world["patient"], "Nephrology", limit=2, cursor=first["next_cursor"]
    )
    seen = [e["booking_id"] for e in first["encounters"] + second["encounters"]]
    assert len(seen) == len(set(seen)), "a page boundary repeated an encounter"
    assert len(seen) == 4


def test_the_filter_options_are_only_what_this_patient_actually_has(world):
    """Offering every department in the hospital, most returning nothing, makes the
    control useless."""
    filters = get_timeline_filters(world["patient"])

    assert set(filters["departments"]) == {"Nephrology", "Cardiology", "Psychiatry"}
    assert len(filters["doctors"]) == 3
