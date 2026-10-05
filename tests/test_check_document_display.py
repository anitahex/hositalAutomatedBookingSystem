"""scripts/check_document_display.py: on a server, which documents the patient overview shows
under "Documents and results", and why the others are not shown — by the screen's own rules.

The fixture is test_overview_documents.py's `record`: a May lab report whose readings were all
superseded, a September lab report with current readings, and an MRI with a summary.
"""
from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

from app.services import overview_documents as od

from tests.test_overview_documents import record  # noqa: F401  (the shared fixture)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_document_display.py"


def _script():
    spec = importlib.util.spec_from_file_location("check_document_display", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _add(record, key, filename, document_type, clinical_date, status="complete", created="NOW()"):
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                                  blob_summary_path, original_filename, ingestion_status, created_at)
                    VALUES (%s, %s, 's', %s, %s, 'x', %s, %s, {created})""",
                (record[key], record["patient"], document_type, clinical_date, filename, status))
        conn.commit()


def _by_id(rows):
    return {row["document_id"]: row for row in rows}


def test_the_screen_and_the_check_agree(record):
    explain = []
    blocks = od.document_blocks(None, record["patient"], None, explain=explain)
    rows = _by_id(_script().document_display(record["patient"]))
    assert {r["document_id"] for r in rows.values() if r["shown"]} == {b["document_id"] for b in blocks}
    # Every complete document is either shown or explained.
    assert {e["document_id"] for e in explain} | {b["document_id"] for b in blocks} == set(rows)


def test_each_shown_document_says_how(record):
    rows = _by_id(_script().document_display(record["patient"]))
    assert rows[record["sep"]]["detail"].startswith("3 result(s) out of range or back to normal")
    assert rows[record["mri"]]["detail"] == "summary, 2 sentence(s) · not verified yet"


def test_a_verified_document_names_who_verified_it(record):
    from app.services.document_reviews import record_review

    record_review(record["doctor"], record["patient"], record["sep"], "verify")
    rows = _by_id(_script().document_display(record["patient"]))
    assert rows[record["sep"]]["detail"].endswith("· verified by Dr. Glance Test")


def test_a_second_upload_of_a_scan_is_named_a_copy(record):
    from app.db.connection import connect_db

    _add(record, "sep_copy", "mri (1).png", "mri_report", date(2026, 4, 23), created="NOW() - interval '1 day'")
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_summaries (document_id, sentences, register, verification, rejected_count, generated_at)
                   VALUES (%s, '[{"text": "Disc bulge at L4-L5."}]'::jsonb, 'clinician', 'passed', 0, NOW())""",
                (record["sep_copy"],))
        conn.commit()
    rows = _by_id(_script().document_display(record["patient"]))
    assert rows[record["sep_copy"]]["detail"] == od.HIDDEN_COPY
    assert rows[record["mri"]]["shown"] and rows[record["mri"]]["detail"].endswith("· uploaded 2 times")


def test_a_lab_report_with_nothing_current_says_why(record):
    rows = _by_id(_script().document_display(record["patient"]))
    assert rows[record["may"]]["shown"] is False
    assert rows[record["may"]]["detail"] == od.HIDDEN_NO_CURRENT_VALUES


def test_a_document_without_a_summary_says_why(record):
    _add(record, "sep_copy", "xray.png", "xray_report", date(2026, 1, 5))
    rows = _by_id(_script().document_display(record["patient"]))
    assert rows[record["sep_copy"]]["detail"] == od.HIDDEN_NO_SUMMARY


def test_an_older_upload_of_a_shown_lab_report_is_named_a_copy(record):
    """Its readings are held by the copy that is shown — it is not a report with nothing to say."""
    _add(record, "sep_copy", "sep-labs (1).pdf", "blood_report", date(2026, 9, 20), created="NOW() - interval '1 day'")
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name, value_text,
                                                  value_num, unit, abnormal, clinical_date, created_at)
                   VALUES (%s, %s, 'Vitamin D', 'Vitamin D', '13.8 ng/mL', 13.8, 'ng/mL', 'low', %s, NOW() - interval '1 day')""",
                (record["sep_copy"], record["patient"], date(2026, 9, 20)))
        conn.commit()
    rows = _by_id(_script().document_display(record["patient"]))
    assert rows[record["sep_copy"]]["detail"] == od.HIDDEN_COPY


def test_at_most_six_documents_are_shown_and_the_rest_say_so(record):
    import uuid

    from app.db.connection import connect_db

    extra = [f"cap-{uuid.uuid4().hex[:8]}" for _ in range(8)]
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                for index, document_id in enumerate(extra):
                    cur.execute(
                        """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                                         blob_summary_path, original_filename, ingestion_status)
                           VALUES (%s, %s, 's', 'xray_report', %s, 'x', %s, 'complete')""",
                        (document_id, record["patient"], date(2025, 1, index + 1), f"xray-{index}.png"))
                    cur.execute(
                        """INSERT INTO document_summaries (document_id, sentences, register, verification, rejected_count, generated_at)
                           VALUES (%s, '[{"text": "No fracture."}]'::jsonb, 'clinician', 'passed', 0, NOW())""",
                        (document_id,))
            conn.commit()
        explain = []
        blocks = od.document_blocks(None, record["patient"], None, explain=explain)
        assert len(blocks) == od.MAX_DOCUMENT_BLOCKS
        over = [e for e in explain if e["reason"] == od.HIDDEN_OVER_LIMIT]
        # Sep labs + MRI + 8 x-rays = 10 that could show: the newest 6 do, 4 say why not.
        assert len(over) == 4
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_summaries WHERE document_id = ANY(%s)", (extra,))
                cur.execute("DELETE FROM document_catalog WHERE document_id = ANY(%s)", (extra,))
            conn.commit()


def test_a_document_still_processing_says_so(record):
    _add(record, "sep_copy", "new.pdf", "blood_report", None, status="processing")
    rows = _by_id(_script().document_display(record["patient"]))
    assert rows[record["sep_copy"]]["shown"] is False
    assert rows[record["sep_copy"]]["detail"] == "still being processed"


def test_the_script_prints_one_patient(record, capsys):
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE user_id::text = %s", (record["patient"],))
            has_user = cur.fetchone() is not None
        conn.commit()
    module = _script()
    # The fixture patient has no users row (no email): select it by id through the helper.
    module._patients = lambda email: [(record["patient"], None)]
    assert module.main([]) == 0
    out = capsys.readouterr().out
    assert f"{record['patient']} - 2 of 3 document(s) shown" in out
    assert "SHOWN " in out and "hidden" in out and not has_user
