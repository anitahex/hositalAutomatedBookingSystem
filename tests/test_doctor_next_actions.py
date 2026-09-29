"""Document work in "Your next actions": reported documents, new abnormal results, documents
to verify — for this doctor's own patients, against a real database.

What was wrong: "Your next actions" listed note work only. A document a colleague reported
inaccurate, a result that turned abnormal for today's patient, and a new report nobody had
checked were nowhere on the screen a doctor sees first.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.doctor_next_actions import document_actions
from app.services.document_reviews import record_review


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM document_reviews LIMIT 0")
                cur.execute("SELECT 1 FROM appointment_bookings LIMIT 0")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


@pytest.fixture
def clinic():
    """Dr. Me sees patient P tomorrow and patient F in ten days; patient Q is someone else's."""
    _skip_if_no_database()
    tag = uuid.uuid4().hex[:8]
    ids = {
        "me": str(uuid.uuid4()), "colleague": str(uuid.uuid4()), "other": str(uuid.uuid4()),
        "p": f"next-p-{tag}", "q": f"next-q-{tag}", "f": f"next-f-{tag}",
        "old_labs": f"next-old-{tag}", "new_labs": f"next-new-{tag}", "verified": f"next-ver-{tag}",
        "reported": f"next-rep-{tag}", "q_reported": f"next-qrep-{tag}", "f_doc": f"next-fdoc-{tag}",
        "slots": [],
    }
    now = datetime.now()
    with connect_db() as conn:
        with conn.cursor() as cur:
            for key, name, department in (("me", "Dr. Me", "Orthopedics"), ("colleague", "Dr. Colleague", "Cardiology"),
                                          ("other", "Dr. Other", "Neurology")):
                cur.execute("INSERT INTO doctors (doctor_id, name, department, experience_years, is_active) "
                            "VALUES (%s, %s, %s, 5, TRUE)", (ids[key], name, department))
            for patient, doctor, start in (("p", "me", now + timedelta(days=1)),
                                           ("f", "me", now + timedelta(days=10)),
                                           ("q", "other", now + timedelta(days=1))):
                slot = str(uuid.uuid4())
                ids["slots"].append(slot)
                cur.execute("INSERT INTO appointment_slots (slot_id, doctor_id, start_time, end_time, is_booked) "
                            "VALUES (%s, %s, %s, %s, TRUE)", (slot, ids[doctor], start, start + timedelta(minutes=30)))
                cur.execute("INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status) "
                            "VALUES (%s, %s, %s, %s, %s, 'booked')",
                            (slot, ids[doctor], ids[patient], start, start + timedelta(minutes=30)))
            documents = [
                ("old_labs", "p", "may.pdf", "blood_report", date(2026, 5, 1)),
                ("new_labs", "p", "sep.pdf", "blood_report", date(2026, 9, 20)),
                ("verified", "p", "xray.png", "xray_report", date(2026, 9, 10)),
                ("reported", "p", "rx.png", "prescription", date(2026, 9, 5)),
                ("q_reported", "q", "q.pdf", "blood_report", date(2026, 9, 1)),
                ("f_doc", "f", "f.pdf", "blood_report", date(2026, 9, 1)),
            ]
            for key, patient, filename, document_type, clinical_date in documents:
                cur.execute(
                    """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                                     blob_summary_path, original_filename, ingestion_status)
                       VALUES (%s, %s, 's', %s, %s, 'x', %s, 'complete')""",
                    (ids[key], ids[patient], document_type, clinical_date, filename))
            for key, value, flag, clinical_date in (("old_labs", 5.4, "normal", date(2026, 5, 1)),
                                                    ("new_labs", 8.1, "high", date(2026, 9, 20))):
                cur.execute(
                    """INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name,
                                                      value_text, value_num, unit, abnormal, clinical_date)
                       VALUES (%s, %s, 'HbA1c', 'HbA1c', %s, %s, '%%', %s, %s)""",
                    (ids[key], ids["p"], f"{value} %", value, flag, clinical_date))
        conn.commit()
    record_review(ids["colleague"], ids["p"], ids["verified"], "verify")
    record_review(ids["colleague"], ids["p"], ids["reported"], "flag", reason="Dose misread on the photo")
    record_review(ids["colleague"], ids["q"], ids["q_reported"], "flag", reason="Wrong patient name")
    try:
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                docs = [ids[k] for k in ("old_labs", "new_labs", "verified", "reported", "q_reported", "f_doc")]
                cur.execute("DELETE FROM document_reviews WHERE document_id = ANY(%s)", (docs,))
                cur.execute("DELETE FROM consult_audit_log WHERE metadata->>'document_id' = ANY(%s)", (docs,))
                cur.execute("DELETE FROM document_findings WHERE document_id = ANY(%s)", (docs,))
                cur.execute("DELETE FROM document_catalog WHERE document_id = ANY(%s)", (docs,))
                cur.execute("DELETE FROM appointment_bookings WHERE slot_id = ANY(%s::uuid[])", (ids["slots"],))
                cur.execute("DELETE FROM appointment_slots WHERE slot_id = ANY(%s::uuid[])", (ids["slots"],))
                cur.execute("DELETE FROM doctors WHERE doctor_id = ANY(%s::uuid[])",
                            ([ids["me"], ids["colleague"], ids["other"]],))
            conn.commit()


def _documents(items):
    return [item["document"]["document_id"] for item in items]


def test_a_colleagues_report_on_my_patient_is_listed_with_the_reason(clinic):
    actions = document_actions(clinic["me"], "Orthopedics")
    assert _documents(actions["reported"]) == [clinic["reported"]]
    item = actions["reported"][0]
    assert item["patient_id"] == clinic["p"]
    assert item["review"]["flagged_by"][0]["reason"] == "Dose misread on the photo"


def test_someone_elses_patient_is_not_my_work(clinic):
    actions = document_actions(clinic["me"], "Orthopedics")
    assert clinic["q_reported"] not in _documents(actions["reported"])


def test_a_result_newly_out_of_range_for_tomorrows_patient_is_listed(clinic):
    [item] = document_actions(clinic["me"], "Orthopedics")["new_abnormal"]
    assert item["document"]["document_id"] == clinic["new_labs"]
    assert [(f["name"], f["change"]["kind"]) for f in item["findings"]] == [("HbA1c", "new")]
    assert item["booking_id"]


def test_recent_unverified_documents_are_listed_but_not_verified_or_reported_ones(clinic):
    listed = _documents(document_actions(clinic["me"], "Orthopedics")["to_verify"])
    assert clinic["new_labs"] in listed
    assert clinic["verified"] not in listed and clinic["reported"] not in listed


def test_a_patient_seen_in_ten_days_is_not_yet_on_the_list(clinic):
    listed = _documents(document_actions(clinic["me"], "Orthopedics")["to_verify"])
    assert clinic["f_doc"] not in listed


def test_verifying_a_document_takes_it_off_the_list(clinic):
    record_review(clinic["me"], clinic["p"], clinic["new_labs"], "verify")
    listed = _documents(document_actions(clinic["me"], "Orthopedics")["to_verify"])
    assert clinic["new_labs"] not in listed


def test_clearing_the_report_takes_it_off_the_reported_list(clinic):
    record_review(clinic["colleague"], clinic["p"], clinic["reported"], "clear_flag")
    assert document_actions(clinic["me"], "Orthopedics")["reported"] == []
