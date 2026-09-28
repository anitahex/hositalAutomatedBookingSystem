"""The report's own flags, stored and re-derived, against a real database.

The pure reading of a line is covered in test_document_report_flags.py. These cover what
only SQL can prove: the new columns round-trip, rows stored before this change are
repaired from their document's page text, the repair is idempotent, and it never touches
another patient's rows.
"""
from __future__ import annotations

import uuid

import pytest

from app.db.connection import connect_db
from app.services.document_findings import (
    apply_report_flags,
    findings_for_document,
    flatten_findings,
    rederive_stored_findings,
    save_findings,
)

PAGE = """CLINICAL BIOCHEMISTRY
Total Leucocyte Count 7,850 cells/µL 4,000 - 10,000
Red Cell Distribution Width (RDW-CV) 14.8 H % 11.6 - 14.0
Potassium (K+) 6.9 HH mmol/L 3.5 - 5.1
Total Cholesterol / HDL Ratio 5.37 H Ratio < 5.0
HbA1c (Glycated Haemoglobin) 5.4 %"""

FINDINGS = {
    "Biochemistry": {
        "Total Leucocyte Count": "7,850 cells/µL",
        "Red Cell Distribution Width (RDW-CV)": "14.8 %",
        "Potassium (K+)": "6.9 mmol/L",
        "Total Cholesterol / HDL Ratio": "5.37",
        "HbA1c (Glycated Haemoglobin)": "5.4 %",
    }
}


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT report_flag FROM document_findings LIMIT 0")
    except Exception as exc:
        pytest.skip(f"Requires Postgres with migration 0026 applied: {exc}")


@pytest.fixture
def document():
    _skip_if_no_database()
    patient_id = f"reflag-{uuid.uuid4().hex[:10]}"
    document_id = f"reflag-doc-{uuid.uuid4().hex[:10]}"
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO document_pages (document_id, page_no, text, source) VALUES (%s, 1, %s, 'pdf_text')",
                (document_id, PAGE),
            )
        conn.commit()
    try:
        yield {"patient": patient_id, "document": document_id}
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_findings WHERE patient_id = %s", (patient_id,))
                cur.execute("DELETE FROM document_pages WHERE document_id = %s", (document_id,))
            conn.commit()


def _by_name(document_id: str) -> dict[str, dict]:
    return {row["printed_name"]: row for row in findings_for_document(document_id)}


def test_the_reports_verdict_round_trips(document):
    rows = apply_report_flags(flatten_findings(FINDINGS), [{"page_no": 1, "text": PAGE}])
    save_findings(document["document"], document["patient"], rows, "2026-09-20")

    stored = _by_name(document["document"])
    rdw = stored["Red Cell Distribution Width (RDW-CV)"]
    assert (rdw["abnormal"], rdw["report_flag"], rdw["report_ref_text"], rdw["flag_source"]) == (
        "high", "H", "11.6 - 14.0", "report_flag",
    )
    assert (rdw["ref_low"], rdw["ref_high"], rdw["ref_source"], rdw["page_no"]) == (11.6, 14.0, "report", 1)
    assert stored["Potassium (K+)"]["critical"] is True
    assert stored["HbA1c (Glycated Haemoglobin)"]["ref_source"] == "standard"


def test_critical_results_are_listed_first(document):
    rows = apply_report_flags(flatten_findings(FINDINGS), [{"page_no": 1, "text": PAGE}])
    save_findings(document["document"], document["patient"], rows, "2026-09-20")
    ordered = findings_for_document(document["document"])
    assert ordered[0]["printed_name"] == "Potassium (K+)"
    flagged_first = [row["abnormal"] in ("low", "high") for row in ordered]
    assert flagged_first == sorted(flagged_first, reverse=True)


def test_rows_stored_before_the_change_are_repaired_and_the_repair_is_idempotent(document):
    """Stored the old way: standard range only, "7,850" read as 7.85, no report flags."""
    old_rows = flatten_findings(FINDINGS)
    for row in old_rows:
        for key in ("report_flag", "report_ref_text", "ref_source", "flag_source", "critical",
                    "ref_low", "ref_high"):
            row.pop(key, None)
    wbc = next(row for row in old_rows if row["name"] == "Total Leucocyte Count")
    wbc["value_num"] = 7.85
    save_findings(document["document"], document["patient"], old_rows, "2026-09-20")
    assert _by_name(document["document"])["Red Cell Distribution Width (RDW-CV)"]["abnormal"] == "unknown"

    dry = rederive_stored_findings(dry_run=True, patient_id=document["patient"])
    assert dry["changed"] >= 4 and dry["dry_run"] is True
    assert _by_name(document["document"])["Red Cell Distribution Width (RDW-CV)"]["abnormal"] == "unknown", \
        "a dry run wrote"

    applied = rederive_stored_findings(patient_id=document["patient"])
    assert applied["changed"] == dry["changed"]
    stored = _by_name(document["document"])
    assert stored["Red Cell Distribution Width (RDW-CV)"]["abnormal"] == "high"
    assert stored["Total Leucocyte Count"]["value_num"] == 7850.0
    assert stored["Total Leucocyte Count"]["abnormal"] == "normal"
    assert stored["Potassium (K+)"]["critical"] is True
    assert stored["Total Cholesterol / HDL Ratio"]["canonical_name"] == "Total Cholesterol HDL Ratio"

    assert rederive_stored_findings(patient_id=document["patient"])["changed"] == 0


def test_the_repair_leaves_other_patients_alone(document):
    save_findings(document["document"], document["patient"], flatten_findings(FINDINGS), "2026-09-20")
    result = rederive_stored_findings(dry_run=True, patient_id=document["patient"])
    assert result["checked"] == len(flatten_findings(FINDINGS))
    assert result["documents"] == 1
