"""The visit brief against a real database.

The fixture is built so each rule the brief states has a case that would expose it:

  - the boundary is this doctor's last SIGNED note — a later unsigned draft must not move it
  - "since" means after that boundary: older documents, notes and results stay out
  - the same report uploaded twice is one document, with a copies count
  - a colleague's draft never appears; a sensitive specialty's note and prescription are
    listed with their content withheld
  - "your last plan" is that signed note's Plan and the items approved with it
  - a past appointment's brief is measured from before THAT appointment, not from today
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


def _booking(cur, doctor_id, patient_id, when, note=None):
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
         "booked" if when > NOW else "completed", note),
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


def _document(cur, patient_id, filename, uploaded, clinical):
    document_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO document_catalog (document_id, user_id, session_id, original_filename,
                                         blob_summary_path, document_type, clinical_date,
                                         ingestion_status, created_at)
           VALUES (%s, %s, %s, %s, 'summaries/x.json', 'blood_report', %s, 'complete', %s)""",
        (document_id, patient_id, str(uuid.uuid4()), filename, clinical, uploaded),
    )
    return document_id


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

                # MY last signed note, 30 days ago — this is the boundary.
                my_consult, ids["my_past_booking"] = _note(
                    cur, me, patient, NOW - timedelta(days=30),
                    assessment="Knee osteoarthritis", plan="Physiotherapy; review in two weeks",
                )
                ids["boundary"] = NOW - timedelta(days=30)
                _approved_item(cur, my_consult, me, patient, "Tab Paracetamol 500 mg SOS", NOW - timedelta(days=30))
                # A LATER draft of mine — unsigned, so it must not move the boundary.
                _note(cur, me, patient, NOW - timedelta(days=10), status="draft", plan="DRAFT PLAN")

                # Colleagues, after the boundary.
                _note(cur, colleague, patient, NOW - timedelta(days=5), assessment="Atrial fibrillation, rate controlled")
                psych_consult, _ = _note(cur, psych, patient, NOW - timedelta(days=3), assessment="SECRET PSYCH ASSESSMENT")
                _note(cur, colleague, patient, NOW - timedelta(days=2), status="draft", assessment="COLLEAGUE DRAFT")
                # ...and one BEFORE the boundary, which is not news.
                _note(cur, colleague, patient, NOW - timedelta(days=60), assessment="OLD NEWS")

                cardio_consult, _ = _note(cur, colleague, patient, NOW - timedelta(days=4), assessment="Follow-up")
                _approved_item(cur, cardio_consult, colleague, patient, "Tab Bisoprolol 2.5 mg OD", NOW - timedelta(days=4))
                _approved_item(cur, psych_consult, psych, patient, "SECRET PSYCH PRESCRIPTION", NOW - timedelta(days=3))

                # Documents: one report uploaded twice after the boundary; one from before.
                recent = _document(cur, patient, "lab-sept.pdf", NOW - timedelta(days=2), date.today() - timedelta(days=3))
                _document(cur, patient, "lab-sept.pdf", NOW - timedelta(days=1), date.today() - timedelta(days=3))
                old = _document(cur, patient, "lab-july.pdf", NOW - timedelta(days=35), date.today() - timedelta(days=36))
                _finding(cur, recent, patient, "Vitamin D", 13.8, "ng/mL", "low", date.today() - timedelta(days=3))
                _finding(cur, old, patient, "HbA1c", 7.9, "%", "high", date.today() - timedelta(days=36))

                # The appointment being prepared for: tomorrow, with the patient's own words.
                ids["booking"] = _booking(cur, me, patient, NOW + timedelta(days=1),
                                          note="Knee pain worse for a week")
                # A stranger's first appointment with this patient. Their only earlier note
                # is an unsigned DRAFT: it must neither end their first visit nor surface as
                # "your last plan".
                _note(cur, stranger, patient, NOW - timedelta(days=20), status="draft",
                      plan="STRANGER DRAFT PLAN")
                ids["stranger_booking"] = _booking(cur, stranger, patient, NOW + timedelta(days=2))

                # An inconsistent row — a colleague's draft that nonetheless carries a
                # signed_at — so the brief's own "signed only" filter is what excludes it,
                # not merely the missing timestamp.
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


# ---- the boundary ----

def test_the_boundary_is_my_last_signed_note_not_a_later_draft(world):
    brief = _brief(world)
    assert brief["since"]["first_visit"] is False
    boundary = datetime.fromisoformat(brief["since"]["boundary"])
    assert abs((boundary - world["boundary"]).total_seconds()) < 5


def test_my_last_plan_is_the_signed_one_with_what_was_approved(world):
    plan = _brief(world)["last_plan"]
    assert plan["plan"] == "Physiotherapy; review in two weeks"
    assert plan["approved_items"] == [{"kind": "prescription", "content": "Tab Paracetamol 500 mg SOS"}]
    assert "DRAFT PLAN" not in json.dumps(plan)


# ---- since you last saw them ----

def test_colleague_notes_since_are_listed_and_older_ones_are_not(world):
    notes = _brief(world)["since"]["colleague_notes"]
    summaries = json.dumps(notes)
    assert "Atrial fibrillation" in summaries
    assert "OLD NEWS" not in summaries


def test_no_draft_ever_appears(world):
    """A draft is AI output nobody has taken responsibility for; a brief reads as fact.
    Including one whose row is inconsistent and carries a signed_at anyway."""
    text = json.dumps(_brief(world))
    assert "COLLEAGUE DRAFT" not in text and "DRAFT PLAN" not in text
    assert "INCONSISTENT DRAFT" not in text


def test_a_sensitive_specialty_is_listed_with_its_content_withheld(world):
    brief = _brief(world)
    text = json.dumps(brief)
    assert "SECRET PSYCH ASSESSMENT" not in text
    assert "SECRET PSYCH PRESCRIPTION" not in text
    psych = [n for n in brief["since"]["colleague_notes"] if n["department"] == "Psychiatry"]
    assert len(psych) == 1 and psych[0]["restricted"] is True and psych[0]["summary"] is None


def test_the_specialty_itself_reads_its_own_notes(world):
    text = json.dumps(_brief(world, department="Psychiatry"))
    assert "SECRET PSYCH ASSESSMENT" in text


def test_colleague_prescriptions_since_are_listed(world):
    items = _brief(world)["since"]["colleague_prescriptions"]
    contents = [i["content"] for i in items]
    assert "Tab Bisoprolol 2.5 mg OD" in contents
    assert any(i["restricted"] and i["content"] is None for i in items)


def test_the_same_report_uploaded_twice_is_one_document(world):
    documents = _brief(world)["since"]["documents"]
    assert [d["original_filename"] for d in documents] == ["lab-sept.pdf"]
    assert documents[0]["copies"] == 2


def test_only_results_that_arrived_since_are_new(world):
    names = [a["name"] for a in _brief(world)["since"]["abnormal"]]
    assert "Vitamin D" in names
    assert "HbA1c" not in names


# ---- why they're here ----

def test_the_patients_own_words_are_labelled(world):
    why = _brief(world)["why"]
    assert why["booking_note"] == "Knee pain worse for a week"
    assert why["label"] == "Patient reports"


# ---- first visits and past visits ----

def test_a_first_visit_says_so_and_shows_the_recent_record(world):
    brief = _brief(world, department="Neurology", booking="stranger_booking", doctor="stranger")
    assert brief["since"]["first_visit"] is True
    assert brief["since"]["boundary"] is None
    # Their earlier DRAFT is not a plan they committed to.
    assert brief["last_plan"] is None
    assert "STRANGER DRAFT PLAN" not in json.dumps(brief)
    assert brief["since"]["documents"], "a first visit should still see the recent record"


def test_a_past_appointments_brief_is_measured_from_before_it(world):
    """My appointment 30 days ago: at that visit, nothing of mine had been signed before
    it — so it is a first visit, not 'since' a note that did not exist yet."""
    brief = _brief(world, booking="my_past_booking")
    assert brief["since"]["first_visit"] is True


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
    assert metadata["restricted_notes"] == 1
    assert "Atrial" not in json.dumps(metadata)
