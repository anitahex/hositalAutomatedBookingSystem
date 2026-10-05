"""The patient overview across every doctor and document, and the history beneath it.

What a doctor opening a patient must get, and the guardrails around it:
  - each doctor's latest signed assessment and plan, newest first, with who and when;
  - what each report found; a report another doctor objected to stays, with who and why;
  - what does not fit the summary is COUNTED, never silently dropped;
  - a sensitive specialty stays out of the summary for other departments, and its visit's
    documents carry no content in the history;
  - history keeps what each document itself recorded, even a value a later report replaced;
  - "New since your last visit" is the viewing doctor's own, never another's.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date, datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services import patient_overview as po
from app.services.overview_documents import apply_review_labels
from app.services.patient_timeline import get_patient_timeline


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM document_reviews LIMIT 0")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _doctor(cur, name, department):
    cur.execute("INSERT INTO doctors (name, department, experience_years, is_active) VALUES (%s, %s, 1, TRUE) "
                "RETURNING doctor_id", (name, department))
    return str(cur.fetchone()[0])


def _visit(cur, doctor_id, patient_id, *, days_ago, assessment=None, plan=None):
    """A completed visit; with an assessment, a note signed that day."""
    start = datetime.now() - timedelta(days=days_ago)
    cur.execute("""INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
                   VALUES (%s, %s, %s, TRUE, %s) RETURNING slot_id""",
                (doctor_id, start, start + timedelta(minutes=30), patient_id))
    slot_id = cur.fetchone()[0]
    cur.execute("""INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
                   VALUES (%s, %s, %s, %s, %s, 'completed') RETURNING booking_id""",
                (slot_id, doctor_id, patient_id, start, start + timedelta(minutes=30)))
    booking_id = str(cur.fetchone()[0])
    cur.execute("""INSERT INTO consultations (booking_id, doctor_id, patient_id, status)
                   VALUES (%s, %s, %s, 'transcript_ready') RETURNING id""", (booking_id, doctor_id, patient_id))
    consult_id = str(cur.fetchone()[0])
    if assessment:
        cur.execute("""INSERT INTO soap_notes (consultation_id, doctor_id, patient_id, assessment, plan, status,
                                               generated_at, signed_at)
                       VALUES (%s, %s, %s, %s, %s, 'signed', %s, %s)""",
                    (consult_id, doctor_id, patient_id, assessment, plan or "", start, start + timedelta(minutes=20)))
    return booking_id


def _document(cur, ids, key, document_type, clinical_date, *, uploaded_days_ago, filename=None, booking=None,
              summary=None, findings=()):
    document_id = f"hist-{key}-{uuid.uuid4().hex[:8]}"
    ids[key] = document_id
    ids["docs"].append(document_id)
    cur.execute(
        """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                         blob_summary_path, original_filename, ingestion_status, created_at, booking_id)
           VALUES (%s, %s, 's', %s, %s, 'x', %s, 'complete', NOW() - make_interval(days => %s), %s)""",
        (document_id, ids["patient"], document_type, clinical_date, filename or f"{key}.pdf", uploaded_days_ago, booking))
    if summary:
        cur.execute("""INSERT INTO document_summaries (document_id, sentences, register, verification, rejected_count,
                                                       generated_at)
                       VALUES (%s, %s::jsonb, 'clinician', 'passed', 0, NOW())""",
                    (document_id, json.dumps([{"text": s} for s in summary])))
    for name, value, unit, flag in findings:
        cur.execute("""INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name, value_text,
                                                      value_num, unit, abnormal, clinical_date)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (document_id, ids["patient"], name, name, f"{value} {unit}", value, unit, flag, clinical_date))


@pytest.fixture
def record():
    _skip_if_no_database()
    ids = {"docs": []}
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                email = f"hist-{uuid.uuid4().hex[:10]}@example.com"
                cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id", (email,))
                ids["patient"] = str(cur.fetchone()[0])
                cur.execute("""INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
                               VALUES (%s, 'History Patient', 40, '9999999999', 'Test', %s, 'O+')""",
                            (ids["patient"], email))
                for key, name, department in (("ortho", "Dr. Ortho", "Orthopedics"), ("cardio", "Dr. Cardio", "Cardiology"),
                                              ("psych", "Dr. Psych", "Psychiatry"), ("neuro", "Dr. Neuro", "Neurology"),
                                              ("endo", "Dr. Endo", "Endocrinology"), ("viewer", "Dr. Viewer", "Orthopedics"),
                                              ("stranger", "Dr. Stranger", "Orthopedics")):
                    ids[key] = _doctor(cur, name, department)
                p = ids["patient"]
                # Recent enough to be in the summary on date alone: only "each doctor's
                # latest" keeps it out.
                _visit(cur, ids["ortho"], p, days_ago=4, assessment="Old knee strain.", plan="Rest.")
                ids["b_ortho"] = _visit(cur, ids["ortho"], p, days_ago=3, assessment="Lumbar spondylosis.",
                                        plan="- Physiotherapy daily.\n- MRI if no relief in 4 weeks.")
                _visit(cur, ids["cardio"], p, days_ago=10, assessment="Atrial fibrillation, rate controlled.")
                ids["b_psych"] = _visit(cur, ids["psych"], p, days_ago=5, assessment="Generalised anxiety disorder.")
                _visit(cur, ids["viewer"], p, days_ago=15, assessment="Viewer's own assessment.")
                _visit(cur, ids["neuro"], p, days_ago=20, assessment="Migraine without aura.")
                _visit(cur, ids["endo"], p, days_ago=30, assessment="Type 2 diabetes.")

                _document(cur, ids, "may", "blood_report", date(2026, 5, 1), uploaded_days_ago=50,
                          findings=[("Vitamin D", 18.2, "ng/mL", "low")])
                _document(cur, ids, "sep", "blood_report", date(2026, 9, 20), uploaded_days_ago=1, booking=ids["b_ortho"],
                          findings=[("Vitamin D", 13.8, "ng/mL", "low"), ("HbA1c", 8.1, "%", "high")])
                _document(cur, ids, "mri", "mri_report", date(2022, 4, 23), uploaded_days_ago=1,
                          summary=["L4 butterfly vertebra.", "L4-5 disc bulge."])
                _document(cur, ids, "rx", "prescription", date(2022, 5, 21), uploaded_days_ago=55,
                          summary=["Tab Gabantin NT 400/10 BD for 15 days."])
                _document(cur, ids, "psychdoc", "other", date(2026, 9, 1), uploaded_days_ago=5, booking=ids["b_psych"],
                          findings=[("Cortisol", 30.1, "ug/dL", "high")])
            conn.commit()
        from app.services.document_reviews import record_review

        record_review(ids["cardio"], ids["patient"], ids["rx"], "flag", reason="Dose misread")
        record_review(ids["ortho"], ids["patient"], ids["sep"], "verify")
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                docs = ids.get("docs") or []
                for table in ("document_reviews", "document_summaries", "document_findings"):
                    cur.execute(f"DELETE FROM {table} WHERE document_id = ANY(%s)", (docs,))
                cur.execute("DELETE FROM consult_audit_log WHERE metadata->>'patient_id' = %s", (ids.get("patient"),))
                cur.execute("DELETE FROM document_catalog WHERE document_id = ANY(%s)", (docs,))
                cur.execute("DELETE FROM patient_overviews WHERE patient_id = %s", (ids.get("patient"),))
                for key in ("ortho", "cardio", "psych", "neuro", "endo", "viewer", "stranger"):
                    if ids.get(key):
                        cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (ids[key],))
                if ids.get("patient"):
                    cur.execute("DELETE FROM users WHERE user_id = %s", (ids["patient"],))
            conn.commit()


def _facts(record, doctor="viewer", department="Orthopedics"):
    return po.gather_facts(record[doctor], record["patient"], department)


def _kind(facts, kind):
    return [fact for fact in facts if fact["kind"] == kind]


# ---- the summary ----

def test_each_doctors_latest_conclusion_newest_first_with_who_and_when(record):
    conclusions = _kind(_facts(record), "conclusion")
    assert [c["meta"]["by"] for c in conclusions] == ["Dr. Ortho", "Dr. Cardio", "Dr. Viewer", "Dr. Neuro"]
    first = conclusions[0]
    assert first["text"] == "Lumbar spondylosis. Plan: Physiotherapy daily."
    assert first["meta"]["department"] == "Orthopedics" and first["source_type"] == "note" and first["at"]


def test_what_does_not_fit_is_counted_not_dropped(record):
    """Dr. Endo's note and Dr. Ortho's older one do not fit four lines; the card says so."""
    [omitted] = _kind(_facts(record), "omitted")
    assert omitted["meta"] == {"notes": 2, "reports": 0}
    assert omitted["text"] == "2 older signed notes — in the history below"
    # And the history has every visit: seven, plus the two documents no visit holds.
    timeline = get_patient_timeline(record["viewer"], record["patient"], "Orthopedics", limit=5)
    assert timeline["total"] == 7 + 3


def test_a_sensitive_specialty_stays_out_of_other_departments_summaries(record):
    assert "anxiety" not in str(_facts(record))
    psychiatry = _kind(_facts(record, "psych", "Psychiatry"), "conclusion")
    assert "Generalised anxiety disorder." in [c["text"] for c in psychiatry]


def test_each_report_is_one_finding_newest_first(record):
    findings = _kind(_facts(record), "finding")
    texts = [f["text"] for f in findings]
    # September's labs (May's values were all superseded), then the MRI and the prescription.
    assert texts[0].startswith("Blood report: ")
    assert "Vitamin D 13.8 ng/mL low" in texts[0] and "HbA1c 8.1 % high" in texts[0]
    assert "18.2" not in " ".join(texts)
    assert any(t == "MRI report: L4 butterfly vertebra. L4-5 disc bulge." for t in texts)
    assert findings[0]["meta"]["doc_type"] == "blood_report"


def test_a_report_another_doctor_objected_to_stays_with_who_and_why(record):
    facts = apply_review_labels({"facts": _facts(record), "lines": [], "mode": "phrased"},
                                record["viewer"], "Orthopedics")["facts"]
    rx = next(f for f in _kind(facts, "finding") if f["text"].startswith("Prescription"))
    assert rx["label"] == "From a document · reported inaccurate by Dr. Cardio: “Dose misread”"
    labs = next(f for f in _kind(facts, "finding") if f["text"].startswith("Blood report"))
    assert labs["label"] == "From a document · verified by Dr. Ortho"


def test_new_since_the_viewers_own_last_visit(record):
    overview = {"facts": _facts(record)}
    mine = {f["text"]: f["is_new"] for f in po.mark_new_since(overview, record["viewer"], record["patient"])["facts"]}
    # The viewer last saw the patient 15 days ago.
    assert mine["Lumbar spondylosis. Plan: Physiotherapy daily."] is True
    assert mine["Migraine without aura."] is False
    labs = next(text for text in mine if text.startswith("Blood report"))
    assert mine[labs] is True                    # uploaded yesterday
    mri = next(text for text in mine if text.startswith("MRI report"))
    assert mine[mri] is True                     # dated 2022, but uploaded yesterday: new to this doctor
    rx = next(text for text in mine if text.startswith("Prescription"))
    assert mine[rx] is False                     # uploaded 55 days ago
    # Another doctor's "since" is their own: Dr. Cardio saw the patient 10 days ago.
    cardio = {f["text"]: f["is_new"] for f in po.mark_new_since(overview, record["cardio"], record["patient"])["facts"]}
    assert cardio["Viewer's own assessment."] is False and cardio["Lumbar spondylosis. Plan: Physiotherapy daily."] is True
    # A doctor who never saw the patient is shown nothing as "new".
    stranger = po.mark_new_since(overview, record["stranger"], record["patient"])
    assert stranger["new_since"] is None and not any(f["is_new"] for f in stranger["facts"])


def test_the_card_rebuilds_when_a_document_is_summarised_again(record):
    async def no_model(**_):
        raise RuntimeError("no model in tests")

    import app.inference.azure_client as client

    original = client.gpt4o_overview_phrasing
    client.gpt4o_overview_phrasing = no_model
    try:
        first = asyncio.run(po.get_overview(record["viewer"], record["patient"], "Orthopedics"))
        assert asyncio.run(po.get_overview(record["viewer"], record["patient"], "Orthopedics"))["cached"] is True
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE document_summaries SET generated_at = NOW() + interval '1 minute' "
                            "WHERE document_id = %s", (record["mri"],))
            conn.commit()
        again = asyncio.run(po.get_overview(record["viewer"], record["patient"], "Orthopedics"))
        assert first["cached"] is False and again["cached"] is False
    finally:
        client.gpt4o_overview_phrasing = original


def test_the_model_is_never_handed_the_omitted_count_or_single_results(record):
    """It may only reword the summary's facts; the count of what is in the history and the
    per-measurement results are the page's, in code's words."""
    seen = {}

    async def recording_model(*, facts):
        seen["kinds"] = sorted({fact["kind"] for fact in facts})
        raise RuntimeError("no model in tests")

    import app.inference.azure_client as client

    original = client.gpt4o_overview_phrasing
    client.gpt4o_overview_phrasing = recording_model
    try:
        card = asyncio.run(po.get_overview(record["viewer"], record["patient"], "Orthopedics"))
    finally:
        client.gpt4o_overview_phrasing = original
    assert seen["kinds"] == ["conclusion", "finding", "visit"]
    # Still recorded with the card (audited), and shown by the page.
    assert {"omitted", "conclusion", "finding"} <= {fact["kind"] for fact in card["facts"]}


# ---- the history ----

def _items(record, doctor="viewer", department="Orthopedics"):
    return get_patient_timeline(record[doctor], record["patient"], department, limit=20)["items"]


def test_a_visit_carries_its_signed_assessment_plan_and_signer(record):
    visit = next(i for i in _items(record) if i.get("booking_id") == record["b_ortho"])
    assert visit["note"]["assessment"] == "Lumbar spondylosis."
    assert visit["note"]["plan"] == "Physiotherapy daily. MRI if no relief in 4 weeks."
    assert visit["note"]["signed_by"] == "Dr. Ortho"
    assert visit["is_new"] is True


def test_a_document_keeps_what_it_recorded_even_when_superseded(record):
    """May's Vitamin D was replaced by September's — on May's own entry it stays."""
    may = next(i for i in _items(record) if i.get("document_id") == record["may"])
    assert [(f["name"], f["value"], f["flag"]) for f in may["findings"]] == [("Vitamin D", 18.2, "low")]
    assert may["review"]["status"] == "unverified" and may["is_new"] is False


def test_a_document_brought_to_a_visit_says_what_it_found_and_who_checked_it(record):
    visit = next(i for i in _items(record) if i.get("booking_id") == record["b_ortho"])
    [labs] = visit["documents"]
    assert {f["name"] for f in labs["findings"]} == {"Vitamin D", "HbA1c"}
    assert [p["name"] for p in labs["review"]["verified_by"]] == ["Dr. Ortho"]


def test_an_objection_shows_with_its_reason_in_the_history(record):
    rx = next(i for i in _items(record) if i.get("document_id") == record["rx"])
    assert rx["review"]["status"] == "flagged"
    assert rx["review"]["flagged_by"][0]["reason"] == "Dose misread"
    assert rx["summary"] == ["Tab Gabantin NT 400/10 BD for 15 days."]


def test_a_restricted_visits_documents_carry_no_content(record):
    visit = next(i for i in _items(record) if i.get("booking_id") == record["b_psych"])
    assert visit["restricted"] is True
    [doc] = visit["documents"]
    assert "findings" not in doc and "review" not in doc and "Cortisol" not in str(visit)
    # The psychiatrist reads it in full.
    own = next(i for i in _items(record, "psych", "Psychiatry") if i.get("booking_id") == record["b_psych"])
    assert own["documents"][0]["findings"][0]["name"] == "Cortisol"


def test_history_pages_newest_first_without_losing_anything(record):
    first = get_patient_timeline(record["viewer"], record["patient"], "Orthopedics", limit=4)
    rest = get_patient_timeline(record["viewer"], record["patient"], "Orthopedics", limit=20,
                                cursor=first["next_cursor"])
    items = first["items"] + rest["items"]
    assert len(items) == first["total"] == 10
    assert rest["total"] is None  # counted once, on the first page
    times = [i.get("start_time") or i.get("at") for i in items]
    assert times == sorted(times, reverse=True)
