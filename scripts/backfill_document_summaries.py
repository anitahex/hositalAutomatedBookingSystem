"""Backfills page text and clinician summaries for documents ingested before they existed.

WHY THIS IS NEEDED. Two capabilities were added to the ingestion path after documents had
already been stored:

  - per-page source text (document_pages), without which a summary cannot be verified
    against anything, so none is generated at all;
  - vision transcription for IMAGE documents, which have no text layer and so produced no
    page text even after the first change.

Both apply only at upload time, as does a third: the per-measurement table
(document_findings) behind the viewer's abnormal-results list, the overview's abnormal
results and the nutritionist. A document stored before these existed has none of the
three. This makes them retroactive: page text, then measurements (re-read from the
extraction already in storage, classified with the report's own printed flags), then the
summary. The measurements need no model call.

WHAT IT WILL NOT DO. It never regenerates a summary that already exists. Re-running is
therefore safe and cheap: a second run over a fully backfilled catalog makes no model
calls at all. Pass --force to rebuild summaries that are already present.

Every summary it writes goes through the same verification as a live upload
(document_grounding.summarise_document): sentences whose quote or numbers cannot be found
in the source are dropped before anything is stored. A document whose summary fails
verification entirely is recorded as 'failed' rather than left looking ungenerated —
those are different facts and the UI says something different for each.

Run:  python scripts/backfill_document_summaries.py [--force] [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.connection import connect_db  # noqa: E402
from app.services.blob_storage import vault_blob_path  # noqa: E402
from app.services.document_catalog import (  # noqa: E402
    PAGE_SOURCE_PDF_TEXT, PAGE_SOURCE_VISION, get_document_pages, save_document_pages,
)
from app.services.document_pipeline import extract_pdf_pages  # noqa: E402
from app.services.document_storage import read_document_bytes, read_document_json  # noqa: E402
from app.services.document_grounding import summarise_document  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("backfill")


def _candidates(force: bool, limit: int | None) -> list[tuple]:
    """Complete documents missing a stored summary or their measurements (or all of them,
    with --force)."""
    having = "" if force else (
        "AND (NOT EXISTS (SELECT 1 FROM document_summaries s WHERE s.document_id = dc.document_id)"
        " OR NOT EXISTS (SELECT 1 FROM document_findings f WHERE f.document_id = dc.document_id))"
    )
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT dc.document_id, dc.user_id, dc.session_id, dc.original_filename,
                       dc.blob_summary_path, dc.clinical_date,
                       EXISTS (SELECT 1 FROM document_summaries s WHERE s.document_id = dc.document_id)
                FROM document_catalog dc
                WHERE dc.ingestion_status = 'complete' {having}
                ORDER BY dc.created_at
                {'LIMIT %s' if limit else ''}
                """,
                (limit,) if limit else (),
            )
            rows = cur.fetchall()
        conn.commit()
    return rows


async def _ensure_pages(document_id: str, user_id: str, session_id: str, filename: str) -> list[dict]:
    """Stored page text, extracting it from the original file if it was never captured."""
    pages = get_document_pages(document_id)
    if pages:
        return pages

    data = await read_document_bytes(vault_blob_path(user_id, session_id, document_id, filename))

    if filename.lower().endswith(".pdf"):
        pages = extract_pdf_pages(data)
        if pages:
            save_document_pages(document_id, pages, PAGE_SOURCE_PDF_TEXT)
        elif data:
            # A PDF with no text layer is a scan in a PDF wrapper. Falls through to the
            # same treatment as an image rather than being written off as empty.
            logger.info("  %s: no text layer, treating as a scan", filename)
    else:
        # Image: transcribe. The guarantee this buys is weaker than a text layer and is
        # recorded as such — see PAGE_SOURCE_VISION.
        from app.inference.azure_client import gpt4o_transcribe_document_image

        mime = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
        text = await gpt4o_transcribe_document_image(mime_type=mime, file_bytes=data)
        if text:
            save_document_pages(document_id, [{"page_no": 1, "text": text}], PAGE_SOURCE_VISION)

    return get_document_pages(document_id)


async def _ensure_findings(document_id: str, user_id: str, summary_path: str | None,
                           clinical_date, pages: list[dict]) -> int | None:
    """This document's measurements, rebuilt from the extraction already in storage when
    none were ever saved. Returns how many were stored, or None when it already had them.
    No model call: the extraction is re-read, not redone."""
    from app.services.document_findings import apply_report_flags, flatten_findings, save_findings

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM document_findings WHERE document_id = %s LIMIT 1", (document_id,))
            present = cur.fetchone() is not None
        conn.commit()
    if present or not summary_path:
        return None
    extraction = await read_document_json(summary_path)
    rows = apply_report_flags(flatten_findings(extraction.get("findings") or {}), pages)
    return save_findings(document_id, user_id, rows, clinical_date)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="rebuild summaries that already exist")
    parser.add_argument("--limit", type=int, default=None, help="process at most N documents")
    parser.add_argument("--dry-run", action="store_true", help="report what would be done, change nothing")
    args = parser.parse_args()

    rows = _candidates(args.force, args.limit)
    print(f"{len(rows)} document(s) to process\n")
    if args.dry_run:
        for document_id, _, _, filename, _, _, has_summary in rows:
            print(f"  would process {filename} ({document_id})"
                  f"{'' if has_summary else ' — no summary'}")
        return 0

    done = skipped = failed = 0
    for document_id, user_id, session_id, filename, summary_path, clinical_date, has_summary in rows:
        print(f"  {filename}")
        try:
            pages = await _ensure_pages(document_id, user_id, session_id, filename)
            try:
                stored = await _ensure_findings(document_id, user_id, summary_path, clinical_date, pages)
                if stored is not None:
                    print(f"    measurements: {stored} stored")
            except FileNotFoundError:
                print("    stored extraction is no longer in storage — no measurements")
            if not pages:
                # No source text means nothing can be verified, and an unverifiable
                # summary is exactly what this design refuses to produce.
                print("    no source text could be obtained — skipped")
                skipped += 1
                continue
            if has_summary and not args.force:
                done += 1
                continue
            result = await summarise_document(document_id, pages)
            print(f"    {result.status}: {len(result.sentences)} kept, {len(result.rejected)} dropped"
                  f" (source: {pages[0].get('source')})")
            done += 1
        except FileNotFoundError:
            print("    original file is no longer in storage — skipped")
            skipped += 1
        except Exception as exc:
            print(f"    FAILED: {type(exc).__name__}: {exc}")
            failed += 1

    print(f"\nsummarised {done}, skipped {skipped}, failed {failed}")
    return 1 if failed else 0


async def _run() -> int:
    try:
        return await main()
    finally:
        # The Azure client holds an aiohttp session; closed here so the run ends cleanly
        # instead of printing "Unclosed client session" at exit.
        from app.services.blob_storage import close_blob_clients

        await close_blob_clients()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
