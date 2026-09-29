"""What a patient sees of their own records: the documents they uploaded, which doctors have
checked each against the original, and the food handouts their doctors gave them.

VERIFICATION, AS THE PATIENT SEES IT. From document_reviews, the same shared record the
doctors use, with two differences:
  - every verifying doctor is named, with their department and date. The doctors' own view
    hides a doctor in a restricted specialty from colleagues outside it; that protects the
    patient's privacy from other staff, and the patient already knows their own doctors.
  - a report of inaccuracy is shown as "being checked by your care team", without the
    reason: it is a note between clinicians about the document, not a finding about the
    patient, and its wording was written for doctors.

The same report uploaded more than once (a browser saves the second copy as "report (1).pdf")
is one entry, with the number of uploads and every verification across its copies.

AUTHORIZATION. Only the patient's own rows, by the user id in their token; a file is served
only when its catalog row belongs to them. The same attachment-only, allowlisted-type rules
as the doctors' download.
"""
from __future__ import annotations

import logging

from app.db.connection import connect_db

logger = logging.getLogger(__name__)

MAX_DOCUMENTS = 60

STATUS_VERIFIED = "verified"
STATUS_UNDER_REVIEW = "under_review"
STATUS_NOT_REVIEWED = "not_reviewed"
STATUS_PROCESSING = "processing"
STATUS_FAILED = "failed"


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def documents_for_patient(patient_id: str) -> list[dict]:
    """The patient's documents, newest first, one entry per report."""
    from app.services.document_catalog import _content_type_for
    from app.services.document_reviews import _current_positions
    from app.services.overview_documents import _copy_key

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT document_id, session_id, original_filename, document_type, clinical_date,
                          created_at, ingestion_status
                   FROM document_catalog
                   WHERE user_id = %s
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (patient_id, MAX_DOCUMENTS),
            )
            rows = cur.fetchall()
            complete = [str(row[0]) for row in rows if row[6] == "complete"]
            positions = _current_positions(cur, complete) if complete else []
        conn.commit()

    by_document: dict[str, list[tuple]] = {}
    for document_id, doctor_id, name, department, action, _reason, created_at in positions:
        by_document.setdefault(str(document_id), []).append((str(doctor_id), name, department, action, created_at))

    entries: dict[tuple, dict] = {}
    order: list[tuple] = []
    for document_id, session_id, filename, document_type, clinical_date, created_at, status in rows:
        document_id = str(document_id)
        key = _copy_key(filename, document_type, clinical_date) if status == "complete" else ("upload", document_id)
        entry = entries.get(key)
        if entry is None:
            entry = {
                "document_id": document_id,
                "document_ids": [],
                "session_id": str(session_id) if session_id else None,
                "original_filename": filename or "document",
                "document_type": document_type or "other",
                "clinical_date": _iso(clinical_date),
                "uploaded_at": _iso(created_at),
                "content_type": _content_type_for(filename),
                "copies": 0,
                "ingestion_status": status,
                "verified_by": [],
                "_flagged": False,
                # A doctor who verified two copies is named once. By id, not name: two
                # doctors can share a name. The id itself is not sent to the patient.
                "_verifiers": set(),
            }
            entries[key] = entry
            order.append(key)
        entry["document_ids"].append(document_id)
        entry["copies"] += 1
        # Named as the patient first saved it ("labs.pdf", not "labs (4).pdf"); the newest
        # copy is still the one opened.
        if filename and len(filename) < len(entry["original_filename"]):
            entry["original_filename"] = filename
        for doctor_id, name, department, action, reviewed_at in by_document.get(document_id, []):
            if action == "flagged_inaccurate":
                entry["_flagged"] = True
            elif doctor_id not in entry["_verifiers"]:
                entry["_verifiers"].add(doctor_id)
                entry["verified_by"].append({"name": name, "department": department, "at": _iso(reviewed_at)})

    result = []
    for key in order:
        entry = entries[key]
        flagged = entry.pop("_flagged")
        entry.pop("_verifiers")
        if entry["ingestion_status"] == "failed":
            entry["status"] = STATUS_FAILED
        elif entry["ingestion_status"] != "complete":
            entry["status"] = STATUS_PROCESSING
        elif flagged:
            entry["status"] = STATUS_UNDER_REVIEW
            entry["verified_by"] = []
        elif entry["verified_by"]:
            entry["status"] = STATUS_VERIFIED
        else:
            entry["status"] = STATUS_NOT_REVIEWED
        entry["verified_by"].sort(key=lambda v: str(v["at"] or ""))
        result.append(entry)
    return result


async def read_own_document_file(patient_id: str, document_id: str) -> tuple[bytes, str, str]:
    """The patient's own uploaded file. (data, filename, content_type).

    PermissionError when the document is not theirs (or does not exist — the same answer);
    ValueError while it is still processing; FileNotFoundError when the stored file is gone.
    """
    from app.services.blob_storage import vault_blob_path
    from app.services.document_catalog import _content_type_for
    from app.services.document_storage import read_document_bytes

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT user_id, session_id, original_filename, ingestion_status
                   FROM document_catalog WHERE document_id = %s""",
                (str(document_id),),
            )
            row = cur.fetchone()
        conn.commit()
    if not row or str(row[0]) != str(patient_id):
        raise PermissionError("Document not found.")
    user_id, session_id, filename, status = row
    if status != "complete":
        raise ValueError("This document is still being processed.")
    data = await read_document_bytes(vault_blob_path(str(user_id), str(session_id), str(document_id), filename))
    return data, filename, _content_type_for(filename)
