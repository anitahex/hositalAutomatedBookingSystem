"""The visit brief against a real database.

The fixture is built so each rule the brief states has a case that would expose it:

  - only the documents brought to THIS booking are listed — through the booking snapshot or
    document_catalog.booking_id — never a colleague's appointment's report, nor one tied
    to no appointment
  - the same report brought twice is one document, with a copies count, and carries what it
    recorded
  - "your previous visits" are this doctor's own, before this appointment, newest first; a
    cancelled one and a later one are not; each carries its signed assessment, its whole
    plan, everything approved, and the documents brought
  - no colleague's note, prescription or psychiatry content appears anywhere
  - an unsigned draft never appears, including one whose row carries a signed_at anyway
  - a past appointment's brief is read as of before THAT appointment
  - only the booking's own doctor may read it, and every read is audited without content

Follows test_doctor_workspace_integration.py's fixture conventions.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.visit_brief import get_visit_brief


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


NOW = datetime.now()


def _doctor(cur, name, department):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, %s, 1, TRUE) RETURNING doctor_id""",
        (name, department),
    )
    return str(cur.fetchone()[0])


def _booking(cur, doctor_id, patient_id, when, note=None, status=None):
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
           VALUES (%s, %s, %s, TRUE, %s) RETURNING slot_id""",
        (doctor_id, when, when + timedelta(minutes=30), patient_id),
    )
    slot_id = cur.fetchone()[0]
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time,
                                             status, booking_note)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, when, when + timedelta(minutes=30),
         status or ("booked" if when > NOW else "completed"), note),
    )
    return str(cur.fetchone()[0])


def _note(cur, doctor_id, patient_id, when, *, status="signed", assessment="A", plan="P"):
    """A consult on its own booking, with a note signed (or not) at `when`."""
    booking = _booking(cur, doctor_id, patient_id, when - timedelta(hours=1))
    cur.execute(
        """INSERT INTO consultations (booking_id, doctor_id, patient_id, status, transcript_source, ended_at)
           VALUES (%s, %s, %s, 'transcript_ready', 'batch', %s) RETURNING id""",
        (booking, doctor_id, patient_id, when),
    )
    consult = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO soap_notes (consultation_id, doctor_id, patient_id, subjective, objective,
                                   assessment, plan, status, generated_at, signed_at)
           VALUES (%s, %s, %s, 'S', 'O', %s, %s, %s, %s, %s)""",
        (consult, doctor_id, patient_id, assessment, plan, status, when,
         when if status == "signed" else None),
    )
    return consult, booking


def _approved_item(cur, consult, doctor_id, patient_id, content, when, kind="prescription"):
    cur.execute(
        """INSERT INTO consult_clinical_items (consultation_id, doctor_id, patient_id, kind, content,
                                               status, approved_at, approved_by)
           VALUES (%s, %s, %s, %s, %s, 'approved', %s, %s)""",
        (consult, doctor_id, patient_id, kind, content, when, doctor_id),
    )


def _document(cur, patient_id, filename, uploaded, clinical, booking=None):
    """A processed document; `booking` ties it to an appointment through
    document_catalog.booking_id (the other way is the booking snapshot, _brought)."""
    document_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO document_catalog (document_id, user_id, session_id, original_filename,
                                         blob_summary_path, document_type, clinical_date,
                                         ingestion_status, created_at, booking_id)
           VALUES (%s, %s, %s, %s, 'summaries/x.json', 'blood_report', %s, 'complete', %s, %s)""",
        (document_id, patient_id, str(uuid.uuid4()), filename, clinical, uploaded, booking),
    )
    return document_id


def _brought(cur, booking, patient_id, document_ids):
    """The booking snapshot: the documents uploaded in the chat that made the booking."""
    cur.execute(
        """INSERT INTO booking_context_snapshots (booking_id, patient_id, document_ids)
           VALUES (%s, %s, %s::jsonb)""",
        (booking, patient_id, json.dumps(document_ids)),
    )


def _finding(cur, document_id, patient_id, name, value, unit, flag, clinical):
    cur.execute(
        """INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name,
                                          value_text, value_num, unit, abnormal, clinical_date)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (document_id, patient_id, name, name, str(value), value, unit, flag, clinical),
    )


@pytest.fixture
def world():
    _skip_if_no_database()
    ids = {"doctors": []}
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                me = _doctor(cur, "Dr. Me", "Orthopedics")
                colleague = _doctor(cur, "Dr. Colleague", "Cardiology")
                psych = _doctor(cur, "Dr. Psych", "Psychiatry")
                stranger = _doctor(cur, "Dr. Stranger", "Neurology")
                ids["doctors"] += [me, colleague, psych, stranger]
                ids.update(me=me, colleague=colleague, psych=psych, stranger=stranger)

                email = f"brief-{uuid.uuid4().hex[:10]}@example.com"
                cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id", (email,))
                patient = ids["patient"] = str(cur.fetchone()[0])
                cur.execute(
                    """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
                       VALUES (%s, 'Brief Patient', 40, '9999999999', 'Test', %s, 'O+')""",
                    (patient, email),
                )

                # MY visit 30 days ago, signed, with a prescription and a test approved and a
                # report brought to it (tied by document_catalog.booking_id).
                my_consult, ids["my_past_booking"] = _note(
                    cur, me, patient, NOW - timedelta(days=30),
                    assessment="Knee osteoarthritis",
                    plan="Physiotherapy three times a week. Review in two weeks. Avoid squatting. "
                         "Ice after exercise.",
                )
                ids["boundary"] = NOW - timedelta(days=30)
                _approved_item(cur, my_consult, me, patient, "Tab Paracetamol 500 mg SOS", NOW - timedelta(days=30))
                _approved_item(cur, my_consult, me, patient, "Physiotherapy department", NOW - timedelta(days=30),
                               kind="referral")
                xray = _document(cur, patient, "xray-knee.pdf", NOW - timedelta(days=31),
                                 date.today() - timedelta(days=31), booking=ids["my_past_booking"])
                _finding(cur, xray, patient, "Joint space", 2.1, "mm", "low", date.today() - timedelta(days=31))
                # A LATER visit of mine with only an unsigned draft: a visit, but no note.
                _, ids["my_draft_booking"] = _note(cur, me, patient, NOW - timedelta(days=10),
                                                   status="draft", plan="DRAFT PLAN")
                # A cancelled appointment of mine: never a "previous visit".
                ids["my_cancelled"] = _booking(cur, me, patient, NOW - timedelta(days=5), status="cancelled")

                # Colleagues: notes, prescriptions, and a report brought to THEIR appointment.
                _note(cur, colleague, patient, NOW - timedelta(days=5), assessment="Atrial fibrillation, rate controlled")
                psych_consult, _ = _note(cur, psych, patient, NOW - timedelta(days=3), assessment="SECRET PSYCH ASSESSMENT")
                _note(cur, colleague, patient, NOW - timedelta(days=2), status="draft", assessment="COLLEAGUE DRAFT")
                cardio_consult, cardio_booking = _note(cur, colleague, patient, NOW - timedelta(days=4), assessment="Follow-up")
                _approved_item(cur, cardio_consult, colleague, patient, "Tab Bisoprolol 2.5 mg OD", NOW - timedelta(days=4))
                _approved_item(cur, psych_consult, psych, patient, "SECRET PSYCH PRESCRIPTION", NOW - timedelta(days=3))
                echo = _document(cur, patient, "colleague-echo.pdf", NOW - timedelta(days=4), date.today() - timedelta(days=4))
                _brought(cur, cardio_booking, patient, [echo])
                # A report the patient uploaded with no appointment at all.
                _document(cur, patient, "loose-upload.pdf", NOW - timedelta(days=1), date.today() - timedelta(days=1))

                # The appointment being prepared for: tomorrow, with the patient's own words,
                # and one report brought twice through the booking chat.
                tomorrow_9am = (NOW + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                ids["booking"] = _booking(cur, me, patient, tomorrow_9am, note="Knee pain worse for a week")
                # Later the SAME day: within the day the history is read up to, so only the
                # brief's own "before this appointment" rule keeps it out.
                ids["my_same_day_later"] = _booking(cur, me, patient, tomorrow_9am + timedelta(hours=8))
                lab = _document(cur, patient, "lab-sept.pdf", NOW - timedelta(days=2), date.today() - timedelta(days=3))
                lab_copy = _document(cur, patient, "lab-sept.pdf", NOW - timedelta(days=1), date.today() - timedelta(days=3))
                _finding(cur, lab, patient, "Vitamin D", 13.8, "ng/mL", "low", date.today() - timedelta(days=3))
                _brought(cur, ids["booking"], patient, [lab, lab_copy])
                # A visit of mine AFTER this appointment: not "previous".
                ids["my_later"] = _booking(cur, me, patient, NOW + timedelta(days=9))

                # A stranger's first appointment with this patient. Their only earlier note
                # is an unsigned DRAFT.
                _note(cur, stranger, patient, NOW - timedelta(days=20), status="draft",
                      plan="STRANGER DRAFT PLAN")
                ids["stranger_booking"] = _booking(cur, stranger, patient, NOW + timedelta(days=2))
                # A doctor with no earlier appointment at all: the first-visit case.
                ids["newcomer"] = _doctor(cur, "Dr. Newcomer", "Dermatology")
                ids["doctors"].append(ids["newcomer"])
                ids["newcomer_booking"] = _booking(cur, ids["newcomer"], patient, NOW + timedelta(days=4))

                # A colleague's draft that nonetheless carries a signed_at.
                inconsistent, _ = _note(cur, colleague, patient, NOW - timedelta(days=1),
                                        status="draft", assessment="INCONSISTENT DRAFT")
                cur.execute("UPDATE soap_notes SET signed_at = NOW() - interval '1 day' WHERE consultation_id = %s",
                            (inconsistent,))
            conn.commit()
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                if ids.get("patient"):
                    # No foreign key cascades these: without the explicit delete every run
                    # left the patient's measurements behind, attached to no document.
                    cur.execute("DELETE FROM document_findings WHERE patient_id = %s", (ids["patient"],))
                    cur.execute("DELETE FROM document_catalog WHERE user_id = %s", (ids["patient"],))
                for doctor_id in ids["doctors"]:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                if ids.get("patient"):
                    cur.execute("DELETE FROM users WHERE user_id = %s", (ids["patient"],))
            conn.commit()


def _brief(world, department="Orthopedics", booking="booking", doctor="me"):
    return get_visit_brief(world[doctor], world[booking], department)


# ---- documents for this appointment ----

def test_only_the_documents_brought_to_this_booking_are_listed(world):
    names = [d["original_filename"] for d in _brief(world)["this_visit"]["documents"]]
    assert names == ["lab-sept.pdf"]


def test_a_colleagues_report_and_a_loose_upload_are_not_listed(world):
    text = json.dumps(_brief(world))
    assert "colleague-echo.pdf" not in text
    assert "loose-upload.pdf" not in text


def test_the_same_report_brought_twice_is_one_document_with_what_it_recorded(world):
    [document] = _brief(world)["this_visit"]["documents"]
    assert document["copies"] == 2
    assert [(f["name"], f["flag"]) for f in document["findings"]] == [("Vitamin D", "low")]
    assert document["review"]["status"] == "unverified"
    assert document["content_type"] == "application/pdf"


def test_a_document_tied_by_the_catalog_counts_for_its_booking(world):
    """The other way a document belongs to a visit: document_catalog.booking_id."""
    [visit] = [v for v in _brief(world)["previous_visits"] if v["booking_id"] == world["my_past_booking"]]
    assert [d["original_filename"] for d in visit["documents"]] == ["xray-knee.pdf"]
    assert visit["documents"][0]["findings"][0]["name"] == "Joint space"


# ---- your previous visits ----

def test_previous_visits_are_mine_before_this_one_newest_first(world):
    visits = _brief(world)["previous_visits"]
    assert [v["booking_id"] for v in visits] == [world["my_draft_booking"], world["my_past_booking"]]


def test_a_cancelled_or_later_visit_is_not_a_previous_one(world):
    booked = {v["booking_id"] for v in _brief(world)["previous_visits"]}
    assert world["my_cancelled"] not in booked
    assert world["my_later"] not in booked
    assert world["my_same_day_later"] not in booked


def test_a_previous_visit_carries_its_whole_plan_and_everything_approved(world):
    [visit] = [v for v in _brief(world)["previous_visits"] if v["booking_id"] == world["my_past_booking"]]
    assert visit["note"]["assessment"] == "Knee osteoarthritis"
    # The whole plan, not the timeline's first two sentences.
    assert visit["note"]["plan"].endswith("Ice after exercise.")
    assert sorted((i["kind"], i["content"]) for i in visit["approved_items"]) == [
        ("prescription", "Tab Paracetamol 500 mg SOS"), ("referral", "Physiotherapy department")]


def test_a_visit_with_only_a_draft_has_no_note(world):
    [visit] = [v for v in _brief(world)["previous_visits"] if v["booking_id"] == world["my_draft_booking"]]
    assert visit["note"] is None


def test_no_draft_ever_appears(world):
    """A draft is AI output nobody has taken responsibility for; a brief reads as fact.
    Including one whose row is inconsistent and carries a signed_at anyway."""
    text = json.dumps(_brief(world))
    assert "COLLEAGUE DRAFT" not in text and "DRAFT PLAN" not in text
    assert "INCONSISTENT DRAFT" not in text


def test_no_colleagues_note_or_prescription_appears(world):
    """Other doctors' history is the patient page's; the brief is this doctor's visit."""
    for department in ("Orthopedics", "Psychiatry"):
        text = json.dumps(_brief(world, department=department))
        for colleague in ("Atrial fibrillation", "Bisoprolol", "SECRET PSYCH ASSESSMENT",
                          "SECRET PSYCH PRESCRIPTION", "Dr. Colleague", "Dr. Psych"):
            assert colleague not in text, (department, colleague)


def test_my_last_plan_is_the_signed_one_with_what_was_approved(world):
    plan = _brief(world)["last_plan"]
    assert plan["plan"].startswith("Physiotherapy three times a week")
    assert {"kind": "prescription", "content": "Tab Paracetamol 500 mg SOS"} in plan["approved_items"]
    assert "DRAFT PLAN" not in json.dumps(plan)


def test_the_boundary_is_my_last_signed_note_not_a_later_draft(world):
    brief = _brief(world)
    assert brief["since"]["first_visit"] is False
    boundary = datetime.fromisoformat(brief["since"]["boundary"])
    assert abs((boundary - world["boundary"]).total_seconds()) < 5


# ---- why they're here ----

def test_the_patients_own_words_are_labelled(world):
    why = _brief(world)["why"]
    assert why["booking_note"] == "Knee pain worse for a week"
    assert why["label"] == "Patient reports"


# ---- first visits and past visits ----

def test_a_first_visit_says_so_and_lists_no_previous_visits(world):
    brief = _brief(world, department="Dermatology", booking="newcomer_booking", doctor="newcomer")
    assert brief["since"]["first_visit"] is True
    assert brief["previous_visits"] == []
    assert brief["last_plan"] is None
    assert brief["this_visit"]["documents"] == []


def test_an_earlier_visit_with_only_a_draft_is_still_a_visit_but_no_plan(world):
    """The stranger saw the patient once and signed nothing: not a first visit, and their
    draft is not a plan they committed to."""
    brief = _brief(world, department="Neurology", booking="stranger_booking", doctor="stranger")
    assert brief["since"]["first_visit"] is False
    assert [v["note"] for v in brief["previous_visits"]] == [None]
    assert brief["last_plan"] is None
    assert "STRANGER DRAFT PLAN" not in json.dumps(brief)


def test_a_past_appointments_brief_is_read_from_before_it(world):
    """My appointment 30 days ago: nothing of mine came before it, and the visits after it
    — including tomorrow's — are not its "previous visits"."""
    brief = _brief(world, booking="my_past_booking")
    assert brief["since"]["first_visit"] is True
    assert brief["previous_visits"] == []
    assert [d["original_filename"] for d in brief["this_visit"]["documents"]] == ["xray-knee.pdf"]


# ---- authorization and audit ----

def test_only_the_bookings_own_doctor_may_read_it(world):
    with pytest.raises(PermissionError):
        get_visit_brief(world["colleague"], world["booking"], "Cardiology")


@pytest.mark.parametrize("bad", ["not-a-uuid", "", str(uuid.uuid4())])
def test_a_bad_or_unknown_booking_is_simply_not_found(world, bad):
    with pytest.raises(PermissionError):
        get_visit_brief(world["me"], bad, "Orthopedics")


def test_every_read_is_audited_with_counts_not_content(world):
    _brief(world)
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT metadata FROM consult_audit_log
                   WHERE doctor_id = %s AND action_type = 'visit_brief_viewed'
                   ORDER BY created_at DESC LIMIT 1""",
                (world["me"],),
            )
            row = cur.fetchone()
        conn.commit()
    assert row is not None
    metadata = row[0]
    assert metadata["booking_id"] == world["booking"]
    assert metadata["documents"] == 1 and metadata["previous_visits"] == 2
    assert "lab-sept" not in json.dumps(metadata) and "Knee" not in json.dumps(metadata)
