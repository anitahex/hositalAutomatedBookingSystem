"""What is captured about a document at ingestion time.

Two things this protects, both of which were being silently lost:

  1. referring_doctor / referring_department / body_region. The extractor has always
     returned them; chat.py dropped all three when assembling the summary payload, so a
     report that plainly said "Referred by Dr Panday, Psychiatry" could not be traced to
     that referral once ingestion finished.
  2. Per-page text. _extract_pdf_text flattened pages into one string and persisted
     nothing, so a summary could only ever be verified against its source at the instant
     it was generated. A grounded summary that cites "page 2" needs page 2 to still exist.
"""
from __future__ import annotations

import uuid

import pytest

from app.db.connection import connect_db
from app.services.document_catalog import (
    PAGE_SOURCE_PDF_TEXT,
    PAGE_SOURCE_VISION,
    get_document_pages,
    save_document_pages,
    update_catalog_after_extraction,
)
from app.services.document_pipeline import PDF_TEXT_PAGE_LIMIT, _extract_pdf_text, extract_pdf_pages

fitz = pytest.importorskip("fitz", reason="PyMuPDF is needed to build a PDF fixture")


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _pdf(lines: list[str]) -> bytes:
    doc = fitz.open()
    for index, line in enumerate(lines, start=1):
        page = doc.new_page()
        page.insert_text((72, 720), f"Page {index}: {line}")
    return doc.tobytes()


@pytest.fixture
def catalog_row():
    _skip_if_no_database()
    document_id = str(uuid.uuid4())
    user_id = f"test-{uuid.uuid4().hex[:8]}"
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_catalog
                       (document_id, user_id, session_id, blob_summary_path,
                        original_filename, ingestion_status)
                   VALUES (%s, %s, %s, 'x', 'report.pdf', 'processing')""",
                (document_id, user_id, str(uuid.uuid4())),
            )
        conn.commit()
    try:
        yield document_id
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_catalog WHERE document_id = %s", (document_id,))
            conn.commit()


# ---- per-page text ----

def test_pages_are_numbered_from_one_and_in_order():
    pages = extract_pdf_pages(_pdf(["Vitamin D 18 ng/mL LOW", "Thyroid normal", "Signed"]))
    assert [page["page_no"] for page in pages] == [1, 2, 3]
    assert "Vitamin D" in pages[0]["text"]
    assert "Thyroid" in pages[1]["text"]


def test_the_flattened_extractor_still_returns_what_it_always_did():
    """_extract_pdf_text has other callers and its contract must not drift — it is now a
    join over extract_pdf_pages precisely so the two cannot disagree."""
    pdf = _pdf(["Alpha", "Beta"])
    assert _extract_pdf_text(pdf) == "\n\n".join(p["text"] for p in extract_pdf_pages(pdf))
    assert "Alpha" in _extract_pdf_text(pdf)
    assert "Beta" in _extract_pdf_text(pdf)


def test_the_page_cap_is_a_named_constant_and_is_enforced():
    """A discharge summary longer than the cap has no text beyond it, so nothing there can
    be summarised or cited. That is a real limit and it should be visible, not an unnamed
    [:12] repeated across three reader branches."""
    pages = extract_pdf_pages(_pdf([f"line {n}" for n in range(PDF_TEXT_PAGE_LIMIT + 5)]))
    assert len(pages) == PDF_TEXT_PAGE_LIMIT


def test_a_pdf_with_no_text_layer_yields_no_pages_rather_than_blank_ones():
    """A row saying text='' is indistinguishable from a genuinely blank page. Absence is
    the honest representation of "this needs a vision transcription"."""
    doc = fitz.open()
    doc.new_page()
    assert extract_pdf_pages(doc.tobytes()) == []


def test_stored_pages_round_trip_with_their_source(catalog_row):
    save_document_pages(catalog_row, extract_pdf_pages(_pdf(["Cortisol high"])), PAGE_SOURCE_PDF_TEXT)
    stored = get_document_pages(catalog_row)

    assert len(stored) == 1
    assert stored[0]["page_no"] == 1
    assert "Cortisol" in stored[0]["text"]
    assert stored[0]["source"] == PAGE_SOURCE_PDF_TEXT


def test_the_source_distinguishes_a_text_layer_from_a_transcription(catalog_row):
    """A quote verified against a vision transcription proves the summary invented nothing
    beyond what was transcribed — it cannot prove the transcription was right. Callers
    must be able to tell which guarantee they have."""
    save_document_pages(catalog_row, [{"page_no": 1, "text": "scanned text"}], PAGE_SOURCE_VISION)
    assert get_document_pages(catalog_row)[0]["source"] == PAGE_SOURCE_VISION


def test_re_extraction_overwrites_rather_than_duplicating(catalog_row):
    save_document_pages(catalog_row, [{"page_no": 1, "text": "first pass"}], PAGE_SOURCE_PDF_TEXT)
    save_document_pages(catalog_row, [{"page_no": 1, "text": "second pass"}], PAGE_SOURCE_PDF_TEXT)

    stored = get_document_pages(catalog_row)
    assert len(stored) == 1
    assert stored[0]["text"] == "second pass"


def test_an_unknown_page_source_is_rejected(catalog_row):
    with pytest.raises(ValueError):
        save_document_pages(catalog_row, [{"page_no": 1, "text": "x"}], "guessed")


# ---- the referral fields ----

def test_the_referral_and_body_region_are_persisted(catalog_row):
    """The incident behind this: a blood report referred by Dr Panday, Psychiatry, whose
    referral was dropped during ingestion and could not be recovered afterwards."""
    update_catalog_after_extraction(
        document_id=catalog_row, document_type="blood_report",
        clinical_date="2026-09-20", findings_keys=["Cortisol"],
        referring_doctor="Dr. Sunita Panday", referring_department="Psychiatry",
        body_region=None,
    )

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT referring_doctor, referring_department FROM document_catalog
                   WHERE document_id = %s""",
                (catalog_row,),
            )
            assert cur.fetchone() == ("Dr. Sunita Panday", "Psychiatry")
        conn.commit()


def test_a_later_pass_that_reads_no_referral_does_not_erase_one_already_captured(catalog_row):
    """COALESCE, not assignment. These fields only ever gain information — a re-extraction
    that happens to miss the referral line must not delete what an earlier pass saw."""
    update_catalog_after_extraction(
        document_id=catalog_row, document_type="blood_report", clinical_date=None,
        findings_keys=[], referring_department="Psychiatry",
    )
    update_catalog_after_extraction(
        document_id=catalog_row, document_type="blood_report", clinical_date=None,
        findings_keys=[],
    )

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT referring_department FROM document_catalog WHERE document_id = %s",
                (catalog_row,),
            )
            assert cur.fetchone()[0] == "Psychiatry"
        conn.commit()


def test_existing_callers_that_pass_no_referral_still_work(catalog_row):
    """The new parameters are keyword-optional; every pre-existing call site must be
    unaffected."""
    update_catalog_after_extraction(
        document_id=catalog_row, document_type="prescription",
        clinical_date=None, findings_keys=["Amlodipine"],
    )

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT document_type, ingestion_status FROM document_catalog WHERE document_id = %s",
                (catalog_row,),
            )
            assert cur.fetchone() == ("prescription", "complete")
        conn.commit()
