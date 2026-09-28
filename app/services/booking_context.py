"""The pre-visit record: what happened in the conversation that produced an appointment.

WHY THIS EXISTS. A doctor opening an appointment could see the booking and the note, but
nothing about why the patient came. That information was not merely unexposed — it was
never stored. The assistant's recommended department, the patient's actual choice and the
documents uploaded while booking lived only in LangGraph state and were discarded when the
turn ended. Every booking made before this module shipped is unreconstructable.

IMMUTABILITY IS STRUCTURAL, NOT A CONVENTION.

  - The snapshot is written inside the booking's OWN transaction. If the booking commits,
    its context committed with it; if the booking rolls back, so does this. There is no
    window in which an appointment exists without its context, and no retry path that
    could attach a later conversation to an earlier booking.
  - booking_context_snapshots.booking_id is UNIQUE, so a second write for the same booking
    is refused by the database rather than by this code remembering to check.
  - There is NO update function in this module, deliberately. Nothing in the codebase can
    modify a snapshot after the fact.
  - The transcript is pinned to a TIME WINDOW, not to a session. chat_messages is
    append-only, so messages added after the booking fall outside the window and cannot
    change what the doctor sees. Pinning "the session" would have meant the record grew
    every time the patient said anything else. See _pin_transcript for why a window and
    not a first/last message id — the short version is that a turn's two messages share a
    created_at, so "the last message" is not a well-defined row.

WHAT IS DELIBERATELY NOT CAPTURED HERE. The AI summary of the conversation is left
`pending` by this module. That is safe precisely because the transcript is pinned: the
summary is *derivable* from an input that can no longer change, so generating it later
produces exactly what generating it now would. The raw, non-derivable facts — which
conversation, which documents, which department was suggested versus chosen — are what
must be captured at booking time, and they are.

Authorization: this module writes. Reads go through get_snapshot_for_doctor, which applies
the same treating-relationship rule as document_catalog (appointments.doctor_treats_patient)
and is audited, because a booking transcript is clinical content.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass

from app.db.connection import connect_db
from app.db.schema_once import once_per_process

logger = logging.getLogger(__name__)

# A conversation can be long; the pinned range is bounded so one appointment cannot turn
# into an unbounded read. The count recorded on the snapshot is the TRUE total, so the UI
# can say "showing 200 of 340" rather than silently presenting a truncated record as whole.
MAX_PINNED_MESSAGES = 200


@dataclass(frozen=True)
class SnapshotContext:
    """The parts of the booking context that come from agent state rather than from SQL.

    Frozen, and built by a pure function, so the extraction rules can be tested without a
    database or a model.
    """

    chat_session_id: str | None = None
    suggested_department: str | None = None
    chosen_department: str | None = None
    department_match_source: str | None = None
    department_match_reason: str | None = None


def _clean(value) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _uuid_or_none(value) -> str | None:
    """chat_session_id is a UUID column but arrives as free-form state. A malformed id must
    leave the field NULL, never abort a booking — losing the transcript link is bad, losing
    the appointment is worse."""
    text = _clean(value)
    if not text:
        return None
    try:
        return str(uuid.UUID(text))
    except (ValueError, AttributeError, TypeError):
        logger.warning("booking_context: ignoring non-UUID chat_session_id %r", text)
        return None


def context_from_state(state: dict | None, chosen_department: str | None = None) -> SnapshotContext:
    """Reads the booking context out of agent state.

    suggested_department and chosen_department are kept as separate, independently
    nullable fields on purpose. "The assistant had no opinion", "the assistant agreed" and
    "the assistant was overruled" are three different clinical stories, and collapsing any
    two of them — by defaulting one field from the other — would make the disagreement the
    doctor most needs to see indistinguishable from agreement.
    """
    state = state or {}
    return SnapshotContext(
        chat_session_id=_uuid_or_none(
            state.get("chat_session_id") or state.get("session_id")
        ),
        suggested_department=_clean(state.get("suggested_department")),
        chosen_department=_clean(chosen_department),
        department_match_source=_clean(state.get("department_match_source")),
        department_match_reason=_clean(state.get("department_match_reason")),
    )


@once_per_process
def ensure_booking_context_schema(conn) -> None:
    """Mirrors alembic 0023, per this repo's convention of keeping the migration and a
    runtime ensure_* in step (see ensure_soap_schema, ensure_consult_schema)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS booking_context_snapshots (
                snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                booking_id UUID NOT NULL UNIQUE
                    REFERENCES appointment_bookings(booking_id) ON DELETE CASCADE,
                patient_id TEXT,
                chat_session_id UUID,
                transcript_from_at TIMESTAMP,
                transcript_to_at TIMESTAMP,
                transcript_message_count INTEGER NOT NULL DEFAULT 0,
                ai_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
                ai_summary_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (ai_summary_status IN ('pending', 'complete', 'failed', 'skipped')),
                suggested_department TEXT,
                chosen_department TEXT,
                department_match_source TEXT,
                department_match_reason TEXT,
                document_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_booking_snapshots_patient
                ON booking_context_snapshots(patient_id, created_at DESC);
            """
        )


def _pin_transcript(cur, patient_id: str | None, chat_session_id: str | None):
    """The inclusive time window this conversation occupied, plus the true message count.

    Returns (from_at, to_at, count).

    A WINDOW rather than a first/last message id, because chat_messages.created_at
    defaults to now() and one turn writes the patient message and the assistant reply in
    the same transaction — so both rows carry an identical created_at. On live data a
    26-message session had only 13 distinct timestamps. "The last message" is therefore
    not a well-defined row, and picking one by id would pick arbitrarily between the two
    halves of the final turn; a boundary has no such ambiguity and includes both.

    Scoped by patient_id as well as session so a guessed or collided session id cannot
    pull another patient's conversation into an appointment record.
    """
    if not chat_session_id or not patient_id:
        return None, None, 0

    cur.execute(
        """
        SELECT MIN(created_at), MAX(created_at), COUNT(*)
        FROM chat_messages
        WHERE patient_id = %s AND chat_session_id = %s
        """,
        (patient_id, chat_session_id),
    )
    row = cur.fetchone()
    if not row or not row[2]:
        return None, None, 0
    return row[0], row[1], int(row[2])


def _documents_for_session(cur, patient_id: str | None, chat_session_id: str | None) -> list[str]:
    """Documents uploaded during this booking conversation.

    Resolved from document_catalog rather than from agent state: the catalog is the
    authoritative record of what was actually stored, and state has been observed to drop
    keys it was never declared to carry. document_catalog.session_id IS the chat session
    id — chat.py keeps session_id and chat_session_id in step — which is what makes this
    a lookup rather than new plumbing.

    The result is frozen onto the snapshot. Documents uploaded in a LATER conversation are
    correctly absent: they were not part of what the patient brought to this appointment.
    """
    if not chat_session_id or not patient_id:
        return []

    cur.execute(
        """
        SELECT document_id
        FROM document_catalog
        WHERE user_id = %s AND session_id = %s
        ORDER BY created_at ASC
        """,
        (patient_id, str(chat_session_id)),
    )
    return [str(row[0]) for row in cur.fetchall()]


def write_snapshot(cur, *, booking_id, patient_id, context: SnapshotContext) -> None:
    """Writes the pre-visit context using the CALLER'S cursor.

    Taking a cursor rather than opening a connection is load-bearing twice over:

      1. It puts the snapshot in the booking's transaction, so the two commit or roll back
         together and an appointment can never exist without its context.
      2. connect_db() keys checked-out connections by thread id, so opening one here —
         inside book_selected_slot's open connection, on the same thread — would hand back
         the SAME physical connection and commit the booking's transaction early. That
         failure is documented at connect_db's docstring and has happened before.

    ON CONFLICT DO NOTHING, not DO UPDATE: a second write for one booking is a bug, and
    the correct response is to keep the original record rather than overwrite a snapshot
    that a doctor may already have read.
    """
    from_at, to_at, count = _pin_transcript(cur, patient_id, context.chat_session_id)
    document_ids = _documents_for_session(cur, patient_id, context.chat_session_id)

    cur.execute(
        """
        INSERT INTO booking_context_snapshots (
            booking_id, patient_id, chat_session_id,
            transcript_from_at, transcript_to_at, transcript_message_count,
            ai_summary_status,
            suggested_department, chosen_department,
            department_match_source, department_match_reason,
            document_ids
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (booking_id) DO NOTHING
        """,
        (
            str(booking_id),
            patient_id,
            context.chat_session_id,
            from_at,
            to_at,
            count,
            # 'skipped' when there is no conversation to summarise (the REST booking
            # route). Distinguishing that from 'pending' stops a background summariser
            # retrying forever over a transcript that does not exist.
            "pending" if count else "skipped",
            context.suggested_department,
            context.chosen_department,
            context.department_match_source,
            context.department_match_reason,
            json.dumps(document_ids),
        ),
    )


def capture_snapshot_safely(cur, *, booking_id, patient_id, context: SnapshotContext) -> bool:
    """write_snapshot, but a failure here must never cost the patient their appointment.

    Returns True if the context was recorded. On failure it logs and returns False, and
    the booking proceeds: an appointment with no pre-visit context is a degraded record,
    while a lost appointment is a patient who does not get seen.

    NOTE the caller must run this on a cursor it can afford to have poisoned — in Postgres
    a failed statement aborts the whole transaction, so this is called from a SAVEPOINT in
    book_selected_slot rather than inline.
    """
    try:
        write_snapshot(cur, booking_id=booking_id, patient_id=patient_id, context=context)
        return True
    except Exception as exc:
        logger.error(
            "booking_context: could not record context for booking=%s: %s", booking_id, exc
        )
        return False


# ---- Read side ----

def get_snapshot(booking_id: str) -> dict | None:
    """The raw snapshot. No authorization — callers that serve a doctor must use
    get_snapshot_for_doctor instead."""
    with connect_db() as conn:
        ensure_booking_context_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT booking_id, patient_id, chat_session_id,
                       transcript_from_at, transcript_to_at, transcript_message_count,
                       ai_summary, ai_summary_status,
                       suggested_department, chosen_department,
                       department_match_source, department_match_reason,
                       document_ids, created_at
                FROM booking_context_snapshots
                WHERE booking_id = %s
                """,
                (str(booking_id),),
            )
            row = cur.fetchone()
        conn.commit()

    if not row:
        return None

    return {
        "booking_id": str(row[0]),
        "patient_id": row[1],
        "chat_session_id": str(row[2]) if row[2] else None,
        "transcript_from_at": row[3].isoformat() if row[3] else None,
        "transcript_to_at": row[4].isoformat() if row[4] else None,
        "transcript_message_count": int(row[5] or 0),
        "ai_summary": row[6] or {},
        "ai_summary_status": row[7],
        # Both reported exactly as stored. The UI decides what to make of a disagreement;
        # this layer does not editorialise by omitting either side.
        "suggested_department": row[8],
        "chosen_department": row[9],
        "department_match_source": row[10],
        "department_match_reason": row[11],
        "document_ids": row[12] or [],
        "created_at": row[13].isoformat() if row[13] else None,
    }


def get_snapshot_for_doctor(doctor_id: str, booking_id: str) -> dict | None:
    """The pre-visit context for a doctor, authorized and audited.

    Authorization is the booking's OWN doctor_id, not the treating relationship used for
    documents. They differ: doctor_treats_patient is true for any doctor who has ever
    booked this patient, and the context of one colleague's appointment is not part of
    that. A doctor reads the context of appointments that are theirs.

    Raises PermissionError for both "not yours" and "does not exist", deliberately
    indistinguishable — the same non-disclosure rule as consults.get_consult_owned, so
    this cannot be used to probe which bookings exist.
    """
    # booking_id arrives from the URL path, so it is attacker-controlled. Both columns are
    # UUID, and handing Postgres a non-UUID raises InvalidTextRepresentation — which would
    # surface as a 500 and, worse, tell the caller their input reached the database. A
    # malformed id is simply not found, like any other id that does not exist.
    safe_booking_id = _uuid_or_none(booking_id)
    safe_doctor_id = _uuid_or_none(doctor_id)
    if not safe_booking_id or not safe_doctor_id:
        raise PermissionError("Appointment not found.")

    with connect_db() as conn:
        ensure_booking_context_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT patient_id FROM appointment_bookings WHERE booking_id = %s AND doctor_id = %s",
                (safe_booking_id, safe_doctor_id),
            )
            owned = cur.fetchone()
        conn.commit()

    if not owned:
        raise PermissionError("Appointment not found.")

    snapshot = get_snapshot(booking_id)
    if snapshot is None:
        # A booking made before this shipped. Says so honestly rather than returning an
        # empty context that reads as "the patient said nothing".
        return None

    _audit_snapshot_view(doctor_id, booking_id)
    return snapshot


def _audit_snapshot_view(doctor_id: str, booking_id: str) -> None:
    """A booking transcript is clinical content, so reading it is recorded — the same rule
    document_catalog applies to document content. Written to consult_audit_log with a NULL
    consultation_id, reusing this codebase's single clinical audit trail rather than
    starting a parallel one."""
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata)
                       VALUES (NULL, %s, %s, %s::jsonb)""",
                    (
                        str(doctor_id),
                        "booking_context_viewed",
                        json.dumps({"booking_id": str(booking_id)}),
                    ),
                )
            conn.commit()
    except Exception as exc:
        # Never fail the read because the audit write failed; log loudly instead.
        logger.error(
            "booking_context: could not audit context view doctor=%s booking=%s: %s",
            doctor_id, booking_id, exc,
        )
