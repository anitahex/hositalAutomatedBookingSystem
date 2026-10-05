"""What the doctor's patient overview shows under "Documents and results", patient by patient.

WHY. The blocks look the same on every server: the page and its rules are code. What can
differ is the data. A document appears only when it has results out of range, or (for a
prescription, scan or other text report) a summary stored for it. A document uploaded
before documents were summarised, or whose original file was lost, has neither, and so
does not appear. This lists every document of every patient and says whether it appears —
and if not, why — by the same rules the screen uses (overview_documents.document_blocks).

Read-only. On the server:
    docker compose exec backend python scripts/check_document_display.py
    docker compose exec backend python scripts/check_document_display.py --email someone@example.com
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.connection import connect_db  # noqa: E402
from app.services.overview_documents import document_blocks  # noqa: E402

NOT_PROCESSED = {"processing": "still being processed", "pending": "still being processed",
                 "failed": "could not be processed"}


def _patients(email: str | None) -> list[tuple[str, str | None]]:
    """(patient_id, email) for every patient with at least one document."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT dc.user_id::text, u.email
                FROM document_catalog dc
                LEFT JOIN users u ON u.user_id::text = dc.user_id::text
                WHERE %(email)s::text IS NULL OR lower(u.email) = lower(%(email)s::text)
                ORDER BY u.email NULLS LAST
                """,
                {"email": email},
            )
            rows = cur.fetchall()
        conn.commit()
    return rows


def _documents(patient_id: str) -> list[tuple]:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT document_id::text, original_filename, document_type, clinical_date, ingestion_status
                FROM document_catalog
                WHERE user_id = %s
                ORDER BY clinical_date DESC NULLS LAST, created_at DESC
                """,
                (patient_id,),
            )
            rows = cur.fetchall()
        conn.commit()
    return rows


def _how_shown(block: dict) -> str:
    what = (f"{len(block['findings'])} result(s) out of range or back to normal" if block["findings"]
            else f"summary, {len(block['summary'])} sentence(s)")
    review = block.get("review") or {}
    if review.get("status") == "verified":
        who = ", ".join(person.get("name") or "a clinician" for person in review.get("verified_by") or [])
        what += f" · verified by {who}"
    elif review.get("status") == "flagged":
        what += " · reported inaccurate"
    else:
        what += " · not verified yet"
    if block.get("copies", 1) > 1:
        what += f" · uploaded {block['copies']} times"
    return what


def document_display(patient_id: str) -> list[dict]:
    """Every document of one patient: {"document_id", "filename", "document_type",
    "clinical_date", "shown", "detail"}, newest first."""
    explain: list[dict] = []
    blocks = {block["document_id"]: block for block in document_blocks(None, patient_id, None, explain=explain)}
    reasons = {entry["document_id"]: entry["reason"] for entry in explain}
    rows = []
    for document_id, filename, document_type, clinical_date, status in _documents(patient_id):
        if status != "complete":
            shown, detail = False, NOT_PROCESSED.get(status, f"not processed ({status})")
        elif document_id in blocks:
            shown, detail = True, _how_shown(blocks[document_id])
        else:
            shown, detail = False, reasons.get(document_id, "not shown")
        rows.append({"document_id": document_id, "filename": filename or document_id,
                     "document_type": document_type or "other",
                     "clinical_date": clinical_date.isoformat() if clinical_date else "no date",
                     "shown": shown, "detail": detail})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", help="only this patient")
    args = parser.parse_args(argv)

    patients = _patients(args.email)
    if not patients:
        print("No patient with documents" + (f" for {args.email}." if args.email else "."))
        return 0
    nothing_shown = []
    for patient_id, email in patients:
        rows = document_display(patient_id)
        shown = sum(row["shown"] for row in rows)
        print(f"\n{email or patient_id} - {shown} of {len(rows)} document(s) shown")
        for row in rows:
            mark = "SHOWN " if row["shown"] else "hidden"
            print(f"  {mark}  {row['document_type']:14} {row['clinical_date']:10}  {row['filename']}")
            print(f"          {row['detail']}")
        if not shown:
            nothing_shown.append(email or patient_id)
    print(f"\n{len(patients)} patient(s) checked; {len(nothing_shown)} with nothing under Documents and results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
