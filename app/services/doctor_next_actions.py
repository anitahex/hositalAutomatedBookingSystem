"""Document work for "Your next actions": what a doctor can act on as soon as they log in.

The queue under "Your next actions" was note work only: drafts to sign, blocked drafts,
transcripts with no note. Three kinds of document work were nowhere on the screen:

  - REPORTED INACCURATE: a colleague reported a document for one of this doctor's patients
    inaccurate. Its values are being read by everyone treating the patient, so this is the
    one to look at first.
  - NEW ABNORMAL RESULTS: a patient this doctor sees in the next few days has a result that
    is newly out of range, worse, or changed direction since the previous reading.
  - DOCUMENTS TO VERIFY: a patient this doctor sees soon has a recent document that no
    doctor has checked against the original.

Same rules as the rest of the workspace: every "what changed" comes from stored readings
(overview_documents.describe_change), never a model; review status comes from
document_reviews as this doctor may see it; and scope is this doctor's own appointments.
"""
from __future__ import annotations

import logging

from app.db.connection import connect_db

logger = logging.getLogger(__name__)

# The patients this doctor sees soon: today and the next few days.
UPCOMING_DAYS = 7
# A "recent" document: older ones have been in the record through earlier visits.
RECENT_DOCUMENT_DAYS = 90
MAX_PER_KIND = 5
# The changes that need a doctor's attention. "Improving" and "back in range" are good news,
# shown on the patient's page; they are not work.
ATTENTION_CHANGES = {"new", "worse", "flipped"}


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _upcoming_patients(cur, doctor_id: str) -> list[dict]:
    """This doctor's patients with a booked appointment from today on, soonest first."""
    cur.execute(
        """
        SELECT DISTINCT ON (b.patient_id)
               b.patient_id, b.booking_id, b.start_time, pp.name
        FROM appointment_bookings b
        LEFT JOIN patient_profiles pp ON pp.user_id::text = b.patient_id
        WHERE b.doctor_id = %s AND b.status = 'booked'
          AND b.start_time >= date_trunc('day', NOW())
          AND b.start_time < NOW() + make_interval(days => %s)
        ORDER BY b.patient_id, b.start_time
        """,
        (doctor_id, UPCOMING_DAYS),
    )
    rows = [
        {"patient_id": patient_id, "booking_id": str(booking_id), "appointment_start": _iso(start),
         "patient_name": name}
        for patient_id, booking_id, start, name in cur.fetchall()
    ]
    return sorted(rows, key=lambda row: str(row["appointment_start"] or ""))


def _document_item(kind: str, patient: dict, document: dict, **extra) -> dict:
    return {
        "kind": kind,
        "patient_id": patient["patient_id"],
        "patient_name": patient.get("patient_name"),
        "booking_id": patient.get("booking_id"),
        "appointment_start": patient.get("appointment_start"),
        "document": document,
        **extra,
    }


def document_actions(doctor_id: str, viewer_department: str | None) -> dict:
    """{"reported": [...], "new_abnormal": [...], "to_verify": [...]}, each bounded."""
    from app.services.document_catalog import _content_type_for
    from app.services.document_reviews import STATUS_FLAGGED, STATUS_UNVERIFIED, review_states
    from app.services.overview_documents import document_blocks

    with connect_db() as conn:
        with conn.cursor() as cur:
            upcoming = _upcoming_patients(cur, doctor_id)

            # Documents a colleague reported, for any patient this doctor has an appointment
            # with — the same treating relationship that lets them open the document.
            cur.execute(
                """
                SELECT DISTINCT r.document_id, dc.user_id, dc.original_filename, dc.document_type,
                       dc.clinical_date, pp.name
                FROM document_reviews r
                JOIN document_catalog dc ON dc.document_id = r.document_id
                LEFT JOIN patient_profiles pp ON pp.user_id::text = dc.user_id
                WHERE r.action = 'flagged_inaccurate'
                  AND EXISTS (SELECT 1 FROM appointment_bookings b
                              WHERE b.patient_id = dc.user_id AND b.doctor_id = %s)
                """,
                (doctor_id,),
            )
            reported_rows = cur.fetchall()

            patient_ids = [p["patient_id"] for p in upcoming]
            recent_rows = []
            if patient_ids:
                cur.execute(
                    """
                    SELECT dc.document_id, dc.user_id, dc.original_filename, dc.document_type,
                           dc.clinical_date, dc.created_at
                    FROM document_catalog dc
                    WHERE dc.user_id = ANY(%s) AND dc.ingestion_status = 'complete'
                      AND dc.created_at > NOW() - make_interval(days => %s)
                    ORDER BY dc.created_at DESC
                    """,
                    (patient_ids, RECENT_DOCUMENT_DAYS),
                )
                recent_rows = cur.fetchall()
        conn.commit()

    def describe(document_id, filename, document_type, clinical_date):
        return {
            "document_id": str(document_id),
            "original_filename": filename or str(document_id),
            "document_type": document_type or "other",
            "clinical_date": _iso(clinical_date),
            "content_type": _content_type_for(filename),
        }

    by_patient = {p["patient_id"]: p for p in upcoming}

    # 1. Reported inaccurate — only while the report still stands on the current summary.
    reported_states = review_states([row[0] for row in reported_rows], doctor_id, viewer_department)
    reported = []
    for document_id, patient_id, filename, document_type, clinical_date, name in reported_rows:
        state = reported_states.get(str(document_id)) or {}
        if state.get("status") != STATUS_FLAGGED:
            continue
        patient = by_patient.get(patient_id) or {"patient_id": patient_id, "patient_name": name}
        reported.append(_document_item(
            "reported_document", patient, describe(document_id, filename, document_type, clinical_date),
            review=state,
        ))

    # 2. New abnormal results, for the patients seen soon.
    new_abnormal = []
    for patient in upcoming:
        try:
            blocks = document_blocks(doctor_id, patient["patient_id"], viewer_department)
        except Exception as exc:  # one patient's record must not blank the whole list
            logger.warning("next actions: results for %s could not be read: %s", patient["patient_id"], exc)
            continue
        for block in blocks:
            findings = [
                finding for finding in block.get("findings") or []
                if (finding.get("change") or {}).get("kind") in ATTENTION_CHANGES
            ]
            if not findings:
                continue
            new_abnormal.append(_document_item(
                "new_abnormal", patient,
                describe(block["document_id"], block["original_filename"], block["document_type"],
                         block["clinical_date"]),
                findings=findings, review=block.get("review"),
            ))

    # 3. Recent documents nobody has verified, for the patients seen soon. One entry per
    #    report: the same file uploaded twice is one thing to check.
    recent_states = review_states([row[0] for row in recent_rows], doctor_id, viewer_department)
    to_verify, seen = [], set()
    for document_id, patient_id, filename, document_type, clinical_date, _created in recent_rows:
        key = (patient_id, filename, _iso(clinical_date))
        if key in seen:
            continue
        seen.add(key)
        state = recent_states.get(str(document_id)) or {}
        if state.get("status") != STATUS_UNVERIFIED:
            continue
        to_verify.append(_document_item(
            "verify_document", by_patient[patient_id],
            describe(document_id, filename, document_type, clinical_date), review=state,
        ))

    # Soonest appointment first within each kind.
    def soonest(item):
        return str(item.get("appointment_start") or "9999")

    return {
        "reported": sorted(reported, key=soonest)[:MAX_PER_KIND],
        "new_abnormal": sorted(new_abnormal, key=soonest)[:MAX_PER_KIND],
        "to_verify": sorted(to_verify, key=soonest)[:MAX_PER_KIND],
    }
