"""Regenerates stored clinician summaries written by an older summary prompt.

WHY. The v1 prompt capped a summary at "1 to 3 sentences", so a report with more abnormal
findings than that lost some of them from the summary. v2 writes one verified sentence per
abnormal or critical finding. Stored summaries keep their old text until regenerated.

WHAT IT DOES. For every processed document whose summary was written by another prompt
version (or that has none), calls document_grounding.summarise_document — the one path by
which a summary reaches the database, which verifies every sentence against the stored
page text before storing it. One model call per document.

Run:  python scripts/resummarise_documents.py            (dry run: lists what would run)
      python scripts/resummarise_documents.py --apply    (makes the model calls)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.connection import connect_db  # noqa: E402
from app.services.document_catalog import get_document_pages  # noqa: E402
from app.services.document_grounding import SUMMARY_PROMPT_VERSION, summarise_document  # noqa: E402


def _stale_documents(patient_id: str | None, document_id: str | None = None) -> list[tuple[str, str | None, str | None]]:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT dc.document_id, dc.original_filename, ds.prompt_version
                   FROM document_catalog dc
                   LEFT JOIN document_summaries ds ON ds.document_id = dc.document_id
                   WHERE dc.ingestion_status = 'complete'
                     AND EXISTS (SELECT 1 FROM document_pages p WHERE p.document_id = dc.document_id)
                     AND ds.prompt_version IS DISTINCT FROM %(version)s
                     AND (%(p)s::text IS NULL OR dc.user_id = %(p)s)
                     AND (%(d)s::text IS NULL OR dc.document_id = %(d)s)
                   ORDER BY dc.created_at""",
                {"version": SUMMARY_PROMPT_VERSION, "p": patient_id, "d": document_id},
            )
            return cur.fetchall()


async def _run(documents) -> None:
    for document_id, filename, _version in documents:
        result = await summarise_document(document_id, get_document_pages(document_id))
        print(f"{document_id} {filename}: {len(result.sentences)} kept, "
              f"{len(result.rejected)} dropped, {result.status}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="make the model calls (default: dry run)")
    parser.add_argument("--patient", help="limit to one patient id")
    parser.add_argument("--document", help="limit to one document id")
    args = parser.parse_args()

    documents = _stale_documents(args.patient, args.document)
    for document_id, filename, version in documents:
        print(f"{document_id} {filename}: {version or 'no summary'} -> {SUMMARY_PROMPT_VERSION}")
    print(f"{len(documents)} document(s), one model call each.")
    if not args.apply:
        print("Dry run — nothing regenerated. Re-run with --apply.")
        return 0
    asyncio.run(_run(documents))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
