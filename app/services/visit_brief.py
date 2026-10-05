"""The visit brief: what a doctor needs for ONE appointment.

WHY IT EXISTS. The patient page used to carry two summaries of the same patient, stacked:
a "patient brief" (this doctor's own signed assessments plus every document's unverified
impression, read one blob at a time) and the "at a glance" overview (cross-department,
verified, cached). They answered the same question twice, one of them worse.

The two now answer different questions:

  - AT A GLANCE (patient_overview) — "who is this patient?" Patient-level, cross-
    department, every doctor's notes and every document. Lives on the patient page.
  - THIS — "what do I need for THIS visit?" Appointment-level, from this doctor's point
    of view. Lives on the appointment and on the Today card. Three sections:

      1. Why they're here — the booking itself: the booking note, the department chosen
         versus the one the assistant suggested, what they brought. Everything here came
         from the patient, and is labelled so.
      2. Documents for this appointment — the documents that belong to THIS booking, by the
         timeline's own rule (patient_timeline._ENCOUNTER_DOCUMENTS), each with what it
         recorded and who verified it. It used to list every document the patient had
         uploaded for any doctor in the last year, which put a colleague's appointment's
         reports on this one.
      3. Your previous visits — this doctor's own earlier appointments with the patient:
         their signed assessment and plan, what was approved, the documents brought.

    Other doctors' notes and prescriptions are not here. They are on the patient page,
    which is one click away and built for the whole record.

HOW IT IS BUILT. Selection, not generation: nothing here calls a model and nothing reads
blob storage. Every line is a row from the record with its source. The visits come from
get_patient_timeline filtered to this doctor, so a visit reads the same in the brief and in
the history.

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

AUDIT. Every read is recorded (visit_brief_viewed), with counts, never content.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from app.db.connection import connect_db
from app.services.patient_timeline import _clip, get_patient_timeline

logger = logging.getLogger(__name__)

# Bounds, so a long record cannot turn a pre-visit glance into a history dump. The full
# history is the timeline's job.
MAX_PREVIOUS_VISITS = 10
# Encounters read from the timeline: this one, earlier ones, cancelled ones and any later
# the same day all count against it, so it is well above MAX_PREVIOUS_VISITS.
_VISITS_READ = 40
_PLAN_CHARS = 600
CANCELLED = "cancelled"

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

            since = last_note[1] if last_note and last_note[1] else None
            last_plan = _last_plan(cur, last_note)
            # Whether the patient has ANY processed document — the older rule for offering
            # food guidance, kept for a page that predates nutrition_focus.
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM document_catalog WHERE user_id = %s AND ingestion_status = 'complete')",
                (patient_id,),
            )
            has_documents = bool(cur.fetchone()[0])
        conn.commit()

    # After the block: the timeline opens its own connections, and a connect_db() nested on
    # one thread hands back the SAME connection (app/db/connection.py).
    documents, previous = _this_and_previous_visits(
        doctor_id, patient_id, str(safe_booking), start_time, viewer_department)

    brief = {
        "booking_id": str(safe_booking),
        "patient_id": patient_id,
        "patient_name": patient_name,
        "department": department,
        "appointment_start": start_time.isoformat() if start_time else None,
        "appointment_status": status,
        "why": _why(booking_id, booking_note),
        "this_visit": {"documents": documents},
        "previous_visits": previous,
        "since": {
            # A first visit WITH THIS DOCTOR: no earlier appointment with them that took
            # place (cancelled ones did not), whether or not a note was signed for it.
            "first_visit": not previous,
            # This doctor's last signed note before this appointment, when there is one.
            "boundary": since.isoformat() if since else None,
        },
        "last_plan": last_plan,
        "has_documents": has_documents,
    }
    _audit_brief_view(doctor_id, brief)
    return brief


def _instant(value) -> datetime | None:
    """A timeline timestamp (ISO text) or a database one, comparable with each other."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def _collapse_copies(documents: list[dict]) -> list[dict]:
    """One row per distinct document: the same report uploaded twice for one appointment is
    one row, "uploaded 2 times". Its review is already merged across copies by the timeline."""
    from app.services.document_catalog import _content_type_for

    seen: dict = {}
    for doc in documents:
        key = (doc.get("original_filename"), doc.get("clinical_date"))
        if key in seen:
            seen[key]["copies"] += 1
            continue
        seen[key] = {
            **doc,
            "document_type": doc.get("document_type") or "other",
            # The viewer labels the file from this; the same field the documents list sends.
            "content_type": _content_type_for(doc.get("original_filename")),
            "copies": 1,
        }
    return list(seen.values())


def _this_and_previous_visits(doctor_id, patient_id, booking_id, start_time, viewer_department):
    """(documents of THIS booking, this doctor's earlier visits newest first).

    Both come from the timeline filtered to this doctor, so which documents belong to a
    visit, and what each recorded, are decided in one place. A visit after this one — or
    later the same day — is not "previous": a past appointment's brief reads as it did then.
    """
    timeline = get_patient_timeline(
        doctor_id, patient_id, viewer_department,
        other_doctor_id=doctor_id,
        date_to=start_time.date().isoformat() if start_time else None,
        limit=_VISITS_READ,
    )
    starts = _instant(start_time)
    documents: list[dict] = []
    previous: list[dict] = []
    for encounter in timeline["encounters"]:
        if encounter["booking_id"] == booking_id:
            documents = _collapse_copies(encounter.get("documents") or [])
            continue
        began = _instant(encounter.get("start_time"))
        if encounter.get("status") == CANCELLED or not began or not starts or began >= starts:
            continue
        if len(previous) < MAX_PREVIOUS_VISITS:
            previous.append(encounter)
    return documents, _previous_visits(previous)


def _previous_visits(encounters: list[dict]) -> list[dict]:
    """The brief's shape for each earlier visit: the timeline's encounter, with the whole
    signed plan and every item approved at that visit (the timeline carries only the first
    two sentences of the plan and the prescription)."""
    if not encounters:
        return []
    booking_ids = [encounter["booking_id"] for encounter in encounters]
    with connect_db() as conn:
        with conn.cursor() as cur:
            # The same consult the timeline reads for a visit: its latest, not discarded.
            cur.execute(
                """
                SELECT b.booking_id::text, lc.id, sn.plan
                FROM appointment_bookings b
                LEFT JOIN LATERAL (
                    SELECT c.id FROM consultations c
                    WHERE c.booking_id = b.booking_id AND c.status <> 'discarded'
                    ORDER BY c.created_at DESC
                    LIMIT 1
                ) lc ON TRUE
                LEFT JOIN soap_notes sn ON sn.consultation_id = lc.id AND sn.status = 'signed'
                WHERE b.booking_id = ANY(%s::uuid[])
                """,
                (booking_ids,),
            )
            consults = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
            consult_ids = [consult for consult, _plan in consults.values() if consult]
            approved: dict = {}
            if consult_ids:
                cur.execute(
                    """SELECT consultation_id, kind, content FROM consult_clinical_items
                       WHERE consultation_id = ANY(%s::uuid[]) AND status = 'approved' AND content <> ''
                       ORDER BY consultation_id, kind""",
                    (consult_ids,),
                )
                for consult, kind, content in cur.fetchall():
                    approved.setdefault(str(consult), []).append({"kind": kind, "content": content})
        conn.commit()

    visits = []
    for encounter in encounters:
        consult, plan = consults.get(encounter["booking_id"], (None, None))
        note = encounter.get("note")
        restricted = bool(encounter.get("restricted"))
        if note and not note.get("restricted"):
            note = {**note, "plan": _clip(plan, _PLAN_CHARS) if plan else note.get("plan")}
        visits.append({
            "booking_id": encounter["booking_id"],
            "start_time": encounter.get("start_time"),
            "status": encounter.get("status"),
            "restricted": restricted,
            # None: nothing was signed for this visit — said, not hidden.
            "note": note,
            "approved_items": [] if restricted or not consult else approved.get(str(consult), []),
            "documents": _collapse_copies(encounter.get("documents") or []),
        })
    return visits


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
    metadata = {
        "booking_id": brief["booking_id"],
        "patient_id": brief["patient_id"],
        "documents": len(brief["this_visit"]["documents"]),
        "previous_visits": len(brief["previous_visits"]),
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
