"""The visit brief: what a doctor needs for ONE appointment.

WHY IT EXISTS. The patient page used to carry two summaries of the same patient, stacked:
a "patient brief" (this doctor's own signed assessments plus every document's unverified
impression, read one blob at a time) and the "at a glance" overview (cross-department,
verified, cached). They answered the same question twice, one of them worse.

The two now answer different questions:

  - AT A GLANCE (patient_overview) — "who is this patient?" Patient-level, cross-
    department, the same for every doctor in a department. Lives on the patient page.
  - THIS — "what do I need for THIS visit?" Appointment-level, from this doctor's point
    of view. Lives on the appointment and on the Today card. Three sections:

      1. Why they're here — the booking itself: the booking note, the department chosen
         versus the one the assistant suggested, what they brought. Everything here came
         from the patient, and is labelled so.
      2. Since you last saw them — everything that arrived after THIS doctor's last signed
         note for the patient: new documents, results that are now abnormal, colleagues'
         signed notes, prescriptions colleagues approved. On a first visit, the recent
         record instead, and it says which it is.
      3. Your last plan — the Plan of that last signed note, and what was approved with it.

HOW IT IS BUILT. Selection, not generation: nothing here calls a model and nothing reads
blob storage. Every line is a row from the record with its source. One connection, a
handful of bounded queries.

WHAT IT MUST NEVER CONTAIN, carried over from the brief it replaces:

  - Unsigned drafts. A draft is AI output nobody has taken responsibility for; a brief is
    read as settled fact. Only status = 'signed' notes are read, in the SQL.
  - A sensitive specialty's note content, for a doctor outside it. The encounter is shown
    — hiding it would mislead — and the content withheld, exactly as the timeline does
    (patient_timeline.may_read_note).

AUTHORIZATION. The booking's own doctor only — the same rule as the booking context
(booking_context.get_snapshot_for_doctor), not the wider treating relationship. A doctor
prepares for their own appointments. "Not yours" and "does not exist" are the same
PermissionError, so this cannot be used to probe which bookings exist.

AUDIT. Every read is recorded (visit_brief_viewed). The brief carries the booking
conversation's context and may carry colleagues' notes; both are reads the existing
routes already audit individually.
"""
from __future__ import annotations

import json
import logging

from app.db.connection import connect_db
from app.services.patient_timeline import _note_summary, may_read_note

logger = logging.getLogger(__name__)

# Bounds, so a long record cannot turn a pre-visit glance into a history dump. The full
# history is the timeline's job.
MAX_BRIEF_DOCUMENTS = 6
MAX_BRIEF_NOTES = 6
MAX_BRIEF_PRESCRIPTIONS = 5
MAX_BRIEF_ABNORMAL = 8
# How far back "the recent record" reaches on a first visit, when there is no "last saw".
FIRST_VISIT_LOOKBACK_DAYS = 365

LABEL_PATIENT_REPORTS = "Patient reports"


def _uuid_or_none(value):
    from app.services.booking_context import _uuid_or_none as parse

    return parse(value)


def get_visit_brief(doctor_id: str, booking_id: str, viewer_department: str | None) -> dict:
    """The brief for one of this doctor's appointments.

    Raises PermissionError when the booking is not this doctor's, or does not exist.
    """
    safe_booking = _uuid_or_none(booking_id)
    safe_doctor = _uuid_or_none(doctor_id)
    if not safe_booking or not safe_doctor:
        raise PermissionError("Appointment not found.")

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.patient_id, b.start_time, b.status, b.booking_note, d.department,
                       pp.name
                FROM appointment_bookings b
                JOIN doctors d ON d.doctor_id = b.doctor_id
                LEFT JOIN patient_profiles pp ON pp.user_id::text = b.patient_id
                WHERE b.booking_id = %s AND b.doctor_id = %s
                """,
                (safe_booking, safe_doctor),
            )
            booking = cur.fetchone()
            if not booking:
                raise PermissionError("Appointment not found.")
            patient_id, start_time, status, booking_note, department, patient_name = booking

            # The boundary: this doctor's last SIGNED note for this patient, from an EARLIER
            # appointment. Earlier than this one, so the brief of a past appointment still
            # reads as it did before that visit, not relative to today.
            cur.execute(
                """
                SELECT sn.consultation_id, sn.signed_at, sn.plan, sn.assessment
                FROM soap_notes sn
                JOIN consultations c ON c.id = sn.consultation_id
                JOIN appointment_bookings b ON b.booking_id = c.booking_id
                WHERE sn.doctor_id = %s AND sn.patient_id = %s AND sn.status = 'signed'
                  AND b.booking_id <> %s AND b.start_time < %s
                ORDER BY sn.signed_at DESC NULLS LAST
                LIMIT 1
                """,
                (safe_doctor, patient_id, safe_booking, start_time),
            )
            last_note = cur.fetchone()

            if last_note and last_note[1]:
                since, first_visit = last_note[1], False
                since_param = {"since": since, "lookback": None}
            else:
                since, first_visit = None, True
                since_param = {"since": None, "lookback": FIRST_VISIT_LOOKBACK_DAYS}
            # One predicate for "after the boundary", used by every section below: after
            # the last signed note, or within the look-back window on a first visit.
            after = """(
                (%(since)s::timestamp IS NOT NULL AND {col} > %(since)s::timestamp)
                OR (%(since)s::timestamp IS NULL
                    AND {col} > NOW() - make_interval(days => %(lookback)s))
            )"""
            params = {"patient": patient_id, "me": safe_doctor, **since_param}

            documents = _documents(cur, params, after)
            abnormal = _abnormal(cur, params, after)
            other_notes = _colleague_notes(cur, params, after, viewer_department)
            prescriptions = _colleague_prescriptions(cur, params, after, viewer_department)
            last_plan = _last_plan(cur, last_note)
            # Whether the patient has ANY processed document, not only new ones — it decides
            # whether the brief offers the AI nutritionist.
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM document_catalog WHERE user_id = %s AND ingestion_status = 'complete')",
                (patient_id,),
            )
            has_documents = bool(cur.fetchone()[0])
        conn.commit()

    # Who has verified or reported each document — shared across the patient's doctors
    # (document_reviews). A result read from a document someone reported inaccurate is
    # marked, so it is not taken at face value in the brief.
    from app.services.document_reviews import STATUS_FLAGGED, review_states

    states = review_states(
        [doc["document_id"] for doc in documents] + [row["document_id"] for row in abnormal],
        doctor_id, viewer_department,
    )
    for doc in documents:
        doc["review"] = states.get(doc["document_id"])
    for row in abnormal:
        row["source_reported_inaccurate"] = (states.get(row["document_id"]) or {}).get("status") == STATUS_FLAGGED

    brief = {
        "booking_id": str(safe_booking),
        "patient_id": patient_id,
        "patient_name": patient_name,
        "department": department,
        "appointment_start": start_time.isoformat() if start_time else None,
        "appointment_status": status,
        "why": _why(booking_id, booking_note),
        "since": {
            "first_visit": first_visit,
            "boundary": since.isoformat() if since else None,
            "lookback_days": FIRST_VISIT_LOOKBACK_DAYS if first_visit else None,
            "documents": documents,
            "abnormal": abnormal,
            "colleague_notes": other_notes,
            "colleague_prescriptions": prescriptions,
        },
        "last_plan": last_plan,
        "has_documents": has_documents,
    }
    _audit_brief_view(doctor_id, brief)
    return brief


def _why(booking_id, booking_note) -> dict:
    """Section 1. From the booking itself and the snapshot taken when it was made."""
    from app.services.booking_context import get_snapshot

    snapshot = get_snapshot(booking_id)
    why = {
        # Free text the patient wrote while booking: shown, labelled, never promoted.
        "booking_note": (booking_note or None),
        "label": LABEL_PATIENT_REPORTS,
        "recorded": snapshot is not None,
    }
    if snapshot:
        why.update({
            "chosen_department": snapshot.get("chosen_department"),
            "suggested_department": snapshot.get("suggested_department"),
            "department_match_reason": snapshot.get("department_match_reason"),
            "messages": snapshot.get("transcript_message_count") or 0,
            "documents_brought": len(snapshot.get("document_ids") or []),
        })
    return why


def _documents(cur, params, after) -> list[dict]:
    """New documents, one row per distinct document. The same report uploaded three times
    is one document here — it was three identical lines in the brief this replaces."""
    from app.services.document_catalog import _content_type_for

    cur.execute(
        f"""
        SELECT dc.document_id, dc.original_filename, dc.document_type, dc.clinical_date,
               dc.created_at, ds.verification
        FROM document_catalog dc
        LEFT JOIN document_summaries ds ON ds.document_id = dc.document_id
        WHERE dc.user_id = %(patient)s AND dc.ingestion_status = 'complete'
          AND {after.format(col="dc.created_at::timestamp")}
        ORDER BY dc.created_at DESC
        """,
        params,
    )
    seen: dict = {}
    for document_id, filename, document_type, clinical_date, created_at, verification in cur.fetchall():
        key = (filename, clinical_date)
        if key in seen:
            seen[key]["copies"] += 1
            continue
        seen[key] = {
            "document_id": document_id,
            "original_filename": filename,
            "document_type": document_type or "other",
            "clinical_date": clinical_date.isoformat() if clinical_date else None,
            "uploaded_at": created_at.isoformat() if created_at else None,
            "summary_verification": verification,
            # The viewer labels the file from this; the same field the documents list sends.
            "content_type": _content_type_for(filename),
            "copies": 1,
        }
        if len(seen) >= MAX_BRIEF_DOCUMENTS:
            break
    return list(seen.values())


def _abnormal(cur, params, after) -> list[dict]:
    """Results that are abnormal NOW (the latest reading of each measurement) and arrived
    after the boundary. Same "latest reading" rule as the overview, with the same
    tie-break, so the two never disagree about whether a result is abnormal."""
    cur.execute(
        f"""
        SELECT canonical_name, value_num, unit, abnormal, clinical_date, document_id
        FROM (
            SELECT DISTINCT ON (df.canonical_name)
                   df.canonical_name, df.value_num, df.unit, df.abnormal, df.clinical_date,
                   df.document_id, dc.created_at
            FROM document_findings df
            JOIN document_catalog dc ON dc.document_id = df.document_id
            WHERE df.patient_id = %(patient)s AND df.canonical_name IS NOT NULL
            ORDER BY df.canonical_name, df.clinical_date DESC NULLS LAST,
                     (df.abnormal = 'unknown'), df.created_at DESC
        ) latest
        WHERE abnormal IN ('low', 'high')
          AND {after.format(col="latest.created_at::timestamp")}
        ORDER BY clinical_date DESC NULLS LAST, canonical_name
        LIMIT {MAX_BRIEF_ABNORMAL}
        """,
        params,
    )
    return [
        {
            "name": name,
            "value": float(value) if value is not None else None,
            "unit": unit,
            "flag": flag,
            "clinical_date": clinical_date.isoformat() if clinical_date else None,
            "document_id": document_id,
        }
        for name, value, unit, flag, clinical_date, document_id in cur.fetchall()
    ]


def _colleague_notes(cur, params, after, viewer_department) -> list[dict]:
    """Colleagues' SIGNED notes since. A restricted specialty's encounter is listed with its
    content withheld — the same rule the timeline applies."""
    cur.execute(
        f"""
        SELECT sn.consultation_id, sn.signed_at, sn.assessment, sn.plan, d.name, d.department
        FROM soap_notes sn
        JOIN doctors d ON d.doctor_id = sn.doctor_id
        WHERE sn.patient_id = %(patient)s AND sn.doctor_id <> %(me)s AND sn.status = 'signed'
          AND {after.format(col="sn.signed_at")}
        ORDER BY sn.signed_at DESC
        LIMIT {MAX_BRIEF_NOTES}
        """,
        params,
    )
    notes = []
    for consultation_id, signed_at, assessment, plan, doctor_name, note_department in cur.fetchall():
        readable = may_read_note(viewer_department, note_department)
        notes.append({
            "consultation_id": str(consultation_id),
            "signed_at": signed_at.isoformat() if signed_at else None,
            "doctor_name": doctor_name,
            "department": note_department,
            "restricted": not readable,
            "summary": _note_summary((assessment, plan)) if readable else None,
        })
    return notes


def _colleague_prescriptions(cur, params, after, viewer_department) -> list[dict]:
    """Prescriptions colleagues approved since — the medication a patient may now be on
    that this doctor did not prescribe. Withheld under the same restriction as notes."""
    cur.execute(
        f"""
        SELECT ci.content, ci.approved_at, d.name, d.department
        FROM consult_clinical_items ci
        JOIN doctors d ON d.doctor_id = ci.doctor_id
        WHERE ci.patient_id = %(patient)s AND ci.doctor_id <> %(me)s
          AND ci.kind = 'prescription' AND ci.status = 'approved'
          AND {after.format(col="COALESCE(ci.approved_at, ci.updated_at)")}
        ORDER BY COALESCE(ci.approved_at, ci.updated_at) DESC
        LIMIT {MAX_BRIEF_PRESCRIPTIONS}
        """,
        params,
    )
    return [
        {
            "content": content if may_read_note(viewer_department, item_department) else None,
            "restricted": not may_read_note(viewer_department, item_department),
            "approved_at": approved_at.isoformat() if approved_at else None,
            "doctor_name": doctor_name,
            "department": item_department,
        }
        for content, approved_at, doctor_name, item_department in cur.fetchall()
    ]


def _last_plan(cur, last_note) -> dict | None:
    """Section 3: the Plan of this doctor's last signed note, and what was approved with it."""
    if not last_note:
        return None
    consultation_id, signed_at, plan, _assessment = last_note
    cur.execute(
        """SELECT kind, content FROM consult_clinical_items
           WHERE consultation_id = %s AND status = 'approved' AND content <> ''
           ORDER BY kind""",
        (consultation_id,),
    )
    return {
        "consultation_id": str(consultation_id),
        "signed_at": signed_at.isoformat() if signed_at else None,
        "plan": plan or "",
        "approved_items": [{"kind": kind, "content": content} for kind, content in cur.fetchall()],
    }


def _audit_brief_view(doctor_id: str, brief: dict) -> None:
    """Every read, with counts of what was shown — never the content itself. Never fails
    the read: a broken audit write must not stop a doctor preparing for a visit, but it is
    logged loudly."""
    since = brief["since"]
    metadata = {
        "booking_id": brief["booking_id"],
        "patient_id": brief["patient_id"],
        "colleague_notes": len(since["colleague_notes"]),
        "restricted_notes": sum(1 for note in since["colleague_notes"] if note["restricted"]),
        "documents": len(since["documents"]),
    }
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata)
                       VALUES (NULL, %s, 'visit_brief_viewed', %s::jsonb)""",
                    (str(doctor_id), json.dumps(metadata)),
                )
            conn.commit()
    except Exception as exc:
        logger.error("visit_brief: could not audit view by doctor=%s: %s", doctor_id, exc)
