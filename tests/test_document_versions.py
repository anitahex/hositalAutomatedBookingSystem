"""Nothing a doctor verified is lost when a document is processed again.

Before: re-summarising a document rewrote document_summaries in place and re-extracting or
re-deriving its measurements rewrote document_findings in place. The text a doctor had
verified was gone, and the verification silently stopped applying with no trace of it.
Now the replaced row is kept, whole, in the same transaction (app/services/document_versions),
and a verification of an earlier version is reported as such rather than vanishing.
"""
from __future__ import annotations

import time
import uuid
from datetime import date

import pytest

from app.db.connection import connect_db
from app.services import document_versions as dv
from app.services.document_findings import rederive_stored_findings, save_findings
from app.services.document_grounding import GroundingResult, VerifiedSentence, store_summary
from app.services.document_reviews import record_review, review_states


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            dv.ensure_document_versions_schema(conn)
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


@pytest.fixture
def document():
    _skip_if_no_database()
    tag = uuid.uuid4().hex[:8]
    ids = {"patient": f"ver-p-{tag}", "document": f"ver-d-{tag}", "doctor": str(uuid.uuid4())}
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO doctors (doctor_id, name, department, experience_years, is_active) "
                        "VALUES (%s, 'Dr. Version', 'Orthopedics', 5, TRUE)", (ids["doctor"],))
            cur.execute(
                """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                                 blob_summary_path, original_filename, ingestion_status)
                   VALUES (%s, %s, 's', 'blood_report', %s, 'x', 'labs.pdf', 'complete')""",
                (ids["document"], ids["patient"], date(2026, 9, 20)))
        conn.commit()
    try:
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                for table in ("document_summary_versions", "document_findings_versions", "document_reviews",
                              "document_summaries"):
                    cur.execute(f"DELETE FROM {table} WHERE document_id = %s", (ids["document"],))
                cur.execute("DELETE FROM document_findings WHERE document_id = %s", (ids["document"],))
                cur.execute("DELETE FROM consult_audit_log WHERE metadata->>'document_id' = %s", (ids["document"],))
                cur.execute("DELETE FROM document_catalog WHERE document_id = %s", (ids["document"],))
                cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (ids["doctor"],))
            conn.commit()


def _summary(*texts):
    return GroundingResult(sentences=[VerifiedSentence(text=t, quote=t, page_no=1) for t in texts],
                           rejected=[], status="passed")


def _rows(table, document_id):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT previous, replaced_by FROM {table} WHERE document_id = %s ORDER BY id", (document_id,))
            rows = cur.fetchall()
        conn.commit()
    return rows


# ---- summaries ----

def test_the_first_summary_keeps_nothing_and_a_new_one_keeps_the_old(document):
    store_summary(document["document"], _summary("Vitamin D is low at 13.8 ng/mL."))
    assert _rows("document_summary_versions", document["document"]) == []
    store_summary(document["document"], _summary("Vitamin D 13.8 ng/mL, low."))
    [(previous, replaced_by)] = _rows("document_summary_versions", document["document"])
    assert previous["sentences"][0]["text"] == "Vitamin D is low at 13.8 ng/mL."
    assert replaced_by == dv.REPLACED_BY_RESUMMARY
    [version] = dv.summary_versions(document["document"])
    assert version["sentences"][0]["text"] == "Vitamin D is low at 13.8 ng/mL."


def test_a_verification_of_an_earlier_version_is_kept_not_lost(document):
    store_summary(document["document"], _summary("Vitamin D is low at 13.8 ng/mL."))
    record_review(document["doctor"], document["patient"], document["document"], "verify")
    time.sleep(0.01)  # a new generated_at, as a real re-run has
    store_summary(document["document"], _summary("Vitamin D 13.8 ng/mL, low."))
    [state] = review_states([document["document"]], str(uuid.uuid4()), None).values()
    # It does not vouch for text it was not made against …
    assert state["status"] == "unverified" and state["verified_by"] == []
    # … but it happened, and the history says so.
    [earlier] = state["earlier"]
    assert earlier["name"] == "Dr. Version" and earlier["action"] == "verified"


def test_verifying_the_new_version_replaces_the_earlier_line(document):
    store_summary(document["document"], _summary("First reading."))
    record_review(document["doctor"], document["patient"], document["document"], "verify")
    time.sleep(0.01)
    store_summary(document["document"], _summary("Second reading."))
    record_review(document["doctor"], document["patient"], document["document"], "verify")
    [state] = review_states([document["document"]], document["doctor"], None).values()
    assert state["status"] == "verified" and state["earlier"] == []


# ---- measurements ----

ROW = {"name": "Vitamin D", "canonical_name": "Vitamin D", "value_text": "13.8 ng/mL", "value_num": 13.8,
       "unit": "ng/mL", "abnormal": "low", "page_no": 1}


def test_a_changed_measurement_is_kept_as_it_was(document):
    save_findings(document["document"], document["patient"], [ROW], date(2026, 9, 20))
    assert _rows("document_findings_versions", document["document"]) == []
    save_findings(document["document"], document["patient"], [{**ROW, "value_text": "31.8 ng/mL", "value_num": 31.8,
                                                               "abnormal": "normal"}], date(2026, 9, 20))
    [(previous, replaced_by)] = _rows("document_findings_versions", document["document"])
    assert previous["value_text"] == "13.8 ng/mL" and previous["abnormal"] == "low"
    assert replaced_by == dv.REPLACED_BY_EXTRACTION


def test_an_identical_re_extraction_keeps_no_copy(document):
    save_findings(document["document"], document["patient"], [ROW], date(2026, 9, 20))
    save_findings(document["document"], document["patient"], [ROW], "2026-09-20")
    assert _rows("document_findings_versions", document["document"]) == []


def test_re_deriving_a_measurement_keeps_the_old_row(document):
    """rederive_stored_findings (scripts/reflag_findings.py) rewrites rows in place."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            # As an old rule stored it: the right value, but no canonical name and no flag.
            cur.execute(
                """INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name, value_text,
                                                  value_num, unit, abnormal, clinical_date)
                   VALUES (%s, %s, 'Vitamin D', NULL, '13.8 ng/mL', 13.8, 'ng/mL', 'unknown', %s)""",
                (document["document"], document["patient"], date(2026, 9, 20)))
        conn.commit()
    result = rederive_stored_findings(patient_id=document["patient"])
    assert result["changed"] == 1
    [(previous, replaced_by)] = _rows("document_findings_versions", document["document"])
    assert previous["canonical_name"] is None and previous["abnormal"] == "unknown"
    assert replaced_by == dv.REPLACED_BY_REFLAG


def test_a_dry_run_keeps_nothing_and_changes_nothing(document):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name, value_text,
                                                  value_num, unit, abnormal, clinical_date)
                   VALUES (%s, %s, 'Vitamin D', NULL, '13.8 ng/mL', 13.8, 'ng/mL', 'unknown', %s)""",
                (document["document"], document["patient"], date(2026, 9, 20)))
        conn.commit()
    rederive_stored_findings(dry_run=True, patient_id=document["patient"])
    assert _rows("document_findings_versions", document["document"]) == []
