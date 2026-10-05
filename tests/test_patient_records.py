"""A patient's own records: their documents with the doctors who verified each, their own
files, the food handouts their doctors gave them — and the nutritionist reading the booking
chat, not only the booking note.

What was wrong:
  - a patient saw a list of processed documents only: nothing processing or failed, no way
    to open their own file, and no sign that any doctor had checked a document;
  - a food handout was printed once and kept nowhere the patient could find it again;
  - the nutritionist read symptoms from the booking note alone, which is empty whenever the
    patient did not send their summary — so symptoms they described in the chat were missed.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date, datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services import nutrition_plan as np_
from app.services import patient_records as pr
from app.services.document_reviews import record_review


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            # As the app does at startup: the handout table may not exist on a fresh database.
            np_.ensure_handout_schema(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM document_reviews LIMIT 0")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


@pytest.fixture
def records():
    _skip_if_no_database()
    tag = uuid.uuid4().hex[:8]
    ids = {"patient": f"rec-p-{tag}", "other": f"rec-o-{tag}",
           "ortho": str(uuid.uuid4()), "psych": str(uuid.uuid4()), "docs": []}
    with connect_db() as conn:
        with conn.cursor() as cur:
            for key, name, department in (("ortho", "Dr. Rec Ortho", "Orthopedics"),
                                          ("psych", "Dr. Rec Psych", "Psychiatry")):
                cur.execute("INSERT INTO doctors (doctor_id, name, department, experience_years, is_active) "
                            "VALUES (%s, %s, %s, 5, TRUE)", (ids[key], name, department))
        conn.commit()

    def add(key, filename, status="complete", owner="patient", document_type="blood_report",
            clinical_date=date(2026, 9, 20), age_minutes=0):
        document_id = f"rec-{key}-{tag}"
        ids[key] = document_id
        ids["docs"].append(document_id)
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                                     blob_summary_path, original_filename, ingestion_status, created_at)
                       VALUES (%s, %s, %s, %s, %s, 'x', %s, %s, NOW() - make_interval(mins => %s))""",
                    (document_id, ids[owner], str(uuid.uuid4()), document_type, clinical_date, filename, status, age_minutes))
            conn.commit()
        return document_id

    ids["add"] = add
    try:
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_reviews WHERE document_id = ANY(%s)", (ids["docs"],))
                cur.execute("DELETE FROM consult_audit_log WHERE metadata->>'patient_id' = ANY(%s)",
                            ([ids["patient"], ids["other"]],))
                cur.execute("DELETE FROM document_catalog WHERE document_id = ANY(%s)", (ids["docs"],))
                cur.execute("DELETE FROM nutrition_handouts WHERE patient_id = ANY(%s)", ([ids["patient"], ids["other"]],))
                cur.execute("DELETE FROM doctors WHERE doctor_id = ANY(%s::uuid[])", ([ids["ortho"], ids["psych"]],))
            conn.commit()


def _by_name(documents):
    return {d["original_filename"]: d for d in documents}


# ---- documents and who verified them ----

def test_a_document_verified_by_two_doctors_names_both(records):
    lab = records["add"]("lab", "labs.pdf")
    record_review(records["ortho"], records["patient"], lab, "verify")
    record_review(records["psych"], records["patient"], lab, "verify")
    [doc] = pr.documents_for_patient(records["patient"])
    assert doc["status"] == pr.STATUS_VERIFIED
    assert [v["name"] for v in doc["verified_by"]] == ["Dr. Rec Ortho", "Dr. Rec Psych"]
    # The patient's own doctors, named — the psychiatry masking protects the patient from
    # OTHER staff, not the patient from knowing their own doctor.
    assert doc["verified_by"][1]["department"] == "Psychiatry"


def test_an_unreviewed_document_says_so(records):
    records["add"]("lab", "labs.pdf")
    [doc] = pr.documents_for_patient(records["patient"])
    assert doc["status"] == pr.STATUS_NOT_REVIEWED and doc["verified_by"] == []


def test_a_report_of_inaccuracy_shows_as_being_checked_without_the_reason(records):
    lab = records["add"]("lab", "labs.pdf")
    record_review(records["ortho"], records["patient"], lab, "verify")
    record_review(records["psych"], records["patient"], lab, "flag", reason="Vitamin D misread")
    [doc] = pr.documents_for_patient(records["patient"])
    assert doc["status"] == pr.STATUS_UNDER_REVIEW
    assert doc["verified_by"] == []
    assert "misread" not in str(doc)


def test_documents_still_processing_or_failed_are_listed_too(records):
    records["add"]("proc", "new-scan.png", status="processing", document_type=None)
    records["add"]("fail", "blurry.jpg", status="failed", document_type=None)
    docs = _by_name(pr.documents_for_patient(records["patient"]))
    assert docs["new-scan.png"]["status"] == pr.STATUS_PROCESSING
    assert docs["blurry.jpg"]["status"] == pr.STATUS_FAILED


def test_copies_are_one_entry_with_every_verification(records):
    """The same report uploaded twice ("labs (1).pdf") is one entry; a doctor verified the
    copy they happened to open."""
    records["add"]("lab", "labs.pdf", age_minutes=10)
    copy = records["add"]("copy", "labs (1).pdf")
    record_review(records["ortho"], records["patient"], copy, "verify")
    [doc] = pr.documents_for_patient(records["patient"])
    assert doc["copies"] == 2 and doc["status"] == pr.STATUS_VERIFIED
    assert sorted(doc["document_ids"]) == sorted([records["lab"], copy])
    # Named as first saved; the newest copy is the one opened.
    assert doc["original_filename"] == "labs.pdf" and doc["document_id"] == copy


def test_a_doctor_who_verified_both_copies_is_named_once(records):
    lab = records["add"]("lab", "labs.pdf", age_minutes=10)
    copy = records["add"]("copy", "labs (1).pdf")
    record_review(records["ortho"], records["patient"], lab, "verify")
    record_review(records["ortho"], records["patient"], copy, "verify")
    [doc] = pr.documents_for_patient(records["patient"])
    assert [v["name"] for v in doc["verified_by"]] == ["Dr. Rec Ortho"]
    assert "_verifiers" not in doc and records["ortho"] not in str(doc)


def test_two_doctors_who_share_a_name_are_both_listed(records):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE doctors SET name = 'Dr. Rec Ortho' WHERE doctor_id = %s", (records["psych"],))
        conn.commit()
    lab = records["add"]("lab", "labs.pdf")
    record_review(records["ortho"], records["patient"], lab, "verify")
    record_review(records["psych"], records["patient"], lab, "verify")
    [doc] = pr.documents_for_patient(records["patient"])
    assert [(v["name"], v["department"]) for v in doc["verified_by"]] == [
        ("Dr. Rec Ortho", "Orthopedics"), ("Dr. Rec Ortho", "Psychiatry")]


def test_another_patients_documents_are_not_listed(records):
    records["add"]("mine", "mine.pdf")
    records["add"]("theirs", "theirs.pdf", owner="other")
    assert [d["original_filename"] for d in pr.documents_for_patient(records["patient"])] == ["mine.pdf"]


def test_a_patient_can_only_open_their_own_file(records):
    theirs = records["add"]("theirs", "theirs.pdf", owner="other")
    with pytest.raises(PermissionError):
        asyncio.run(pr.read_own_document_file(records["patient"], theirs))
    with pytest.raises(PermissionError):
        asyncio.run(pr.read_own_document_file(records["patient"], "no-such-document"))


def test_a_file_still_processing_is_not_served(records):
    processing = records["add"]("proc", "new.pdf", status="processing")
    with pytest.raises(ValueError):
        asyncio.run(pr.read_own_document_file(records["patient"], processing))


# ---- food handouts in the patient's account ----

PLAN = np_.organize({"items": [
    {"kind": "finding", "term": "Vitamin D", "direction": "low", "veg_foods": ["paneer", "oats", "almonds"],
     "non_veg_foods": ["salmon", "eggs"], "limit": ["fried foods"], "note": "Sit in the morning sun.",
     "because": [{"canonical_name": "Vitamin D", "printed_name": "Vitamin D", "value_text": "13.8 ng/mL",
                  "flag": "low", "clinical_date": "2026-09-20", "page_no": 2, "document_id": "d1",
                  "document_type": "blood_report"}]},
]})


def test_a_handout_carries_no_values_or_document_names():
    handout = np_.build_handout(PLAN, "veg")
    text = str(handout)
    assert "13.8" not in text and "blood_report" not in text and "d1" not in text
    assert handout["themes"][0]["foods"] == ["Paneer", "Oats", "Almonds"]
    assert handout["diet"] == "veg" and handout["note"] == np_.HANDOUT_NOTE


def test_a_handout_follows_the_diet_the_doctor_chose():
    assert np_.build_handout(PLAN, "non_veg")["themes"][0]["foods"] == ["Salmon", "Eggs"]
    assert np_.build_handout(PLAN, "anything")["diet"] == "veg"


def test_a_saved_handout_is_in_the_patients_account_with_the_doctor(records):
    content = np_.build_handout(PLAN, "veg")
    np_.save_handout(records["ortho"], records["patient"], None, "d1", content)
    [handout] = np_.handouts_for_patient(records["patient"])
    assert handout["doctor_name"] == "Dr. Rec Ortho" and handout["department"] == "Orthopedics"
    assert handout["content"] == content
    assert np_.handouts_for_patient(records["other"]) == []


def test_making_a_handout_is_audited(records):
    np_.save_handout(records["ortho"], records["patient"], None, None, np_.build_handout(PLAN, "veg"))
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT action_type, metadata FROM consult_audit_log WHERE metadata->>'patient_id' = %s",
                        (records["patient"],))
            [(action, metadata)] = cur.fetchall()
        conn.commit()
    assert action == "nutrition_handout_created"
    assert metadata["themes"] == ["Vitamins & blood"] and metadata["handout_id"]


# ---- sharing a handout: once, and the doctor can see it was shared ----

def _handout_rows(patient_id):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM nutrition_handouts WHERE patient_id = %s", (patient_id,))
            handouts = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM consult_audit_log WHERE action_type = 'nutrition_handout_created' "
                        "AND metadata->>'patient_id' = %s", (patient_id,))
            audits = cur.fetchone()[0]
        conn.commit()
    return handouts, audits


def test_sharing_the_same_handout_again_stores_nothing_new(records):
    """Seen on the server: Share pressed five or six times, five or six identical copies in
    the patient's account, and nothing told the doctor."""
    content = np_.build_handout(PLAN, "veg")
    first = np_.save_handout(records["ortho"], records["patient"], None, None, content)
    again = np_.save_handout(records["ortho"], records["patient"], None, None, content)
    assert first["created"] is True and again["created"] is False
    assert again["id"] == first["id"] and again["shared_at"] == first["shared_at"]
    assert _handout_rows(records["patient"]) == (1, 1)
    assert len(np_.handouts_for_patient(records["patient"])) == 1


def test_a_different_diet_is_a_new_handout(records):
    np_.save_handout(records["ortho"], records["patient"], None, None, np_.build_handout(PLAN, "veg"))
    second = np_.save_handout(records["ortho"], records["patient"], None, None, np_.build_handout(PLAN, "non_veg"))
    assert second["created"] is True
    assert [h["diet"] for h in np_.handouts_for_patient(records["patient"])] == ["non_veg", "veg"]


def test_a_second_press_waits_for_the_first_and_stores_nothing(records):
    """Two presses at once: the first has stored its copy but not committed yet. Without the
    lock the second cannot see that copy and stores another. Deterministic, not a timing race."""
    import threading
    import time

    content = np_.build_handout(PLAN, "veg")
    result = {}
    with connect_db() as first_press:
        with first_press.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                        (np_.share_lock_key(records["patient"], records["ortho"]),))
            cur.execute("INSERT INTO nutrition_handouts (patient_id, doctor_id, diet, content) "
                        "VALUES (%s, %s, 'veg', %s::jsonb)", (records["patient"], records["ortho"], json.dumps(content)))
            second = threading.Thread(target=lambda: result.update(
                np_.save_handout(records["ortho"], records["patient"], None, None, content)), daemon=True)
            second.start()
            # Wait for Postgres to report the second press queued behind the first — not a
            # fixed sleep: opening its connection alone can take seconds on some hosts.
            waiting = False
            deadline = time.monotonic() + 20
            while second.is_alive() and time.monotonic() < deadline:
                cur.execute("SELECT COUNT(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted")
                if cur.fetchone()[0]:
                    waiting = True
                    break
                time.sleep(0.05)
            assert waiting and second.is_alive(), "the second press did not wait for the one in flight"
        first_press.commit()
    second.join(timeout=15)
    assert result["created"] is False
    assert _handout_rows(records["patient"])[0] == 1


def test_copies_shared_before_the_fix_are_shown_once(records):
    """The server's existing duplicates: shown as one handout, dated by the latest copy."""
    content = np_.build_handout(PLAN, "veg")
    with connect_db() as conn:
        with conn.cursor() as cur:
            for minutes in (30, 20, 10):
                cur.execute(
                    """INSERT INTO nutrition_handouts (patient_id, doctor_id, diet, content, created_at)
                       VALUES (%s, %s, 'veg', %s::jsonb, NOW() - make_interval(mins => %s))""",
                    (records["patient"], records["ortho"], json.dumps(content), minutes))
        conn.commit()
    [handout] = np_.handouts_for_patient(records["patient"])
    [shared] = np_.shared_handouts(records["patient"], records["ortho"])
    assert handout["id"] == shared["id"]
    # And sharing it once more still adds nothing.
    assert np_.save_handout(records["ortho"], records["patient"], None, None, content)["created"] is False


def test_the_doctor_sees_what_is_already_in_the_patients_account(records):
    np_.save_handout(records["ortho"], records["patient"], None, None, np_.build_handout(PLAN, "non_veg"))
    [mine] = np_.shared_handouts(records["patient"], records["ortho"])
    assert mine["by_me"] is True and mine["diet"] == "non_veg" and mine["themes"] == ["Vitamins & blood"]
    [theirs] = np_.shared_handouts(records["patient"], records["psych"])
    assert theirs["by_me"] is False and theirs["doctor_name"] == "Dr. Rec Ortho"
    assert np_.shared_handouts(records["other"], records["ortho"]) == []


def test_two_doctors_sharing_the_same_foods_are_two_handouts(records):
    content = np_.build_handout(PLAN, "veg")
    np_.save_handout(records["ortho"], records["patient"], None, None, content)
    assert np_.save_handout(records["psych"], records["patient"], None, None, content)["created"] is True
    assert {h["doctor_name"] for h in np_.handouts_for_patient(records["patient"])} == {"Dr. Rec Ortho", "Dr. Rec Psych"}


# ---- the nutritionist reads the booking chat ----

@pytest.fixture
def booked_chat():
    """A booking whose chat has the patient describing constipation, the assistant saying
    "bloating", and a later message outside the booking's window."""
    _skip_if_no_database()
    tag = uuid.uuid4().hex[:8]
    ids = {"patient": f"chat-p-{tag}", "doctor": str(uuid.uuid4()), "slot": str(uuid.uuid4()),
           "session": str(uuid.uuid4())}
    start = datetime.now() + timedelta(days=1)
    t0 = datetime.now() - timedelta(hours=1)
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO doctors (doctor_id, name, department, experience_years, is_active) "
                        "VALUES (%s, 'Dr. Chat', 'Gastroenterology', 5, TRUE)", (ids["doctor"],))
            cur.execute("INSERT INTO appointment_slots (slot_id, doctor_id, start_time, end_time, is_booked) "
                        "VALUES (%s, %s, %s, %s, TRUE)", (ids["slot"], ids["doctor"], start, start + timedelta(minutes=30)))
            cur.execute("INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status) "
                        "VALUES (%s, %s, %s, %s, %s, 'booked') RETURNING booking_id",
                        (ids["slot"], ids["doctor"], ids["patient"], start, start + timedelta(minutes=30)))
            ids["booking"] = str(cur.fetchone()[0])
            for offset, role, text in ((0, "patient", "I have constipation for a week"),
                                       (1, "assistant", "Any bloating or pain?"),
                                       (2, "patient", "No, just hard stools"),
                                       (120, "patient", "Also I feel tired now")):  # after the window
                cur.execute("INSERT INTO chat_messages (patient_id, chat_session_id, role, text, created_at) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (ids["patient"], ids["session"], role, text, t0 + timedelta(minutes=offset)))
            cur.execute(
                """INSERT INTO booking_context_snapshots (booking_id, patient_id, chat_session_id,
                                                          transcript_from_at, transcript_to_at, transcript_message_count)
                   VALUES (%s, %s, %s, %s, %s, 3)""",
                (ids["booking"], ids["patient"], ids["session"], t0, t0 + timedelta(minutes=2)))
        conn.commit()
    try:
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM booking_context_snapshots WHERE booking_id = %s", (ids["booking"],))
                cur.execute("DELETE FROM chat_messages WHERE patient_id = %s", (ids["patient"],))
                cur.execute("DELETE FROM consult_audit_log WHERE metadata->>'patient_id' = %s", (ids["patient"],))
                cur.execute("DELETE FROM appointment_bookings WHERE booking_id = %s", (ids["booking"],))
                cur.execute("DELETE FROM appointment_slots WHERE slot_id = %s", (ids["slot"],))
                cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (ids["doctor"],))
            conn.commit()


def test_only_the_patients_own_words_inside_the_booking_window_are_read(booked_chat):
    from app.services.nutrition import _booking_chat_patient_text, symptoms_in

    text = _booking_chat_patient_text(booked_chat["patient"], booked_chat["booking"])
    assert "constipation" in text and "hard stools" in text
    assert "bloating" not in text          # the assistant's words
    assert "tired" not in text             # after the booking
    assert symptoms_in(text) == ["constipation"]


def test_symptoms_from_the_chat_reach_the_guidance_and_say_where_they_came_from(booked_chat, monkeypatch):
    from app.services import nutrition

    seen = {}

    async def fake_build(results, symptoms, symptom_sources=None):
        seen.update(symptoms=symptoms, sources=symptom_sources)
        return {"items": [], "cautions": [], "unavailable": []}

    monkeypatch.setattr(nutrition, "build_guidance", fake_build)
    asyncio.run(nutrition.guidance_for_appointment(booked_chat["doctor"], booked_chat["booking"]))
    assert seen["symptoms"] == ["constipation"]
    assert seen["sources"] == {"constipation": "booking chat"}


def test_the_heading_names_a_symptom_the_patient_described_in_the_chat(booked_chat):
    """Most symptoms now arrive in the booking chat, not the note: the heading must name them."""
    from app.services import nutrition

    assert nutrition.nutrition_focus_for_appointment(booked_chat["doctor"], booked_chat["booking"]) == ["Constipation"]


def test_a_booking_with_no_recorded_chat_still_reads_the_note(booked_chat, monkeypatch):
    from app.services import nutrition

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM booking_context_snapshots WHERE booking_id = %s", (booked_chat["booking"],))
            cur.execute("UPDATE appointment_bookings SET booking_note = 'Patient reports acidity' WHERE booking_id = %s",
                        (booked_chat["booking"],))
        conn.commit()
    seen = {}

    async def fake_build(results, symptoms, symptom_sources=None):
        seen.update(symptoms=symptoms, sources=symptom_sources)
        return {"items": [], "cautions": [], "unavailable": []}

    monkeypatch.setattr(nutrition, "build_guidance", fake_build)
    asyncio.run(nutrition.guidance_for_appointment(booked_chat["doctor"], booked_chat["booking"]))
    assert seen["sources"] == {"acidity or heartburn": "booking note"}


def test_a_symptom_shows_where_it_was_found_on_the_page():
    plan = np_.organize({"items": [{"kind": "symptom", "term": "constipation", "direction": "present",
                                    "veg_foods": ["papaya"], "non_veg_foods": ["papaya"], "limit": [], "note": "",
                                    "because": [{"symptom": "constipation", "source": "booking chat"}]}]})
    assert plan["themes"][0]["symptom_sources"] == {"constipation": "booking chat"}
