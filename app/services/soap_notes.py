"""SOAP clinical note storage (Phase 3).

Schema was introduced in full during Part 1 (speaker label correction), which only
needed status-check/mark-stale functions — the correction endpoints must know whether a
note exists and reject/invalidate accordingly, and there is nowhere else this table
could sensibly live. Part 2 adds the operations that actually populate and transition
it: generate_soap_note, get_soap_note, update_soap_note, sign_soap_note, add_addendum.
The share_note/patient-visibility operation is Part 4's concern, deliberately kept out
of this file's Part 2 additions since sharing is an explicit, separate doctor action
from signing.

Status values: 'draft' (freshly generated or doctor-edited, still changeable),
'stale' (a draft that existed when a transcript speaker-label correction was made — see
consults.py's swap_all_speakers/correct_segment_speaker — flagged rather than silently
left intact, since it may cite/reflect now-corrected-away speaker attributions),
'signed' (immutable; only addenda may be appended after this).
"""
from __future__ import annotations

import json

from app.db.connection import connect_db

_SOAP_FIELDS = ("subjective", "objective", "assessment", "plan")

_SOAP_NOTE_COLUMNS = (
    "id, subjective, objective, assessment, plan, field_citations, confidence_flags, "
    "status, generated_at, edited_at, signed_at, signed_by, shared_with_patient_at, shared_by, "
    "source_transcript_type"
)


def ensure_soap_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS soap_notes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                consultation_id UUID NOT NULL UNIQUE REFERENCES consultations(id) ON DELETE CASCADE,
                doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                patient_id TEXT,
                subjective TEXT,
                objective TEXT,
                assessment TEXT,
                plan TEXT,
                field_citations JSONB NOT NULL DEFAULT '{}'::jsonb,
                confidence_flags JSONB NOT NULL DEFAULT '{}'::jsonb,
                status TEXT NOT NULL DEFAULT 'draft',
                generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                edited_at TIMESTAMP,
                signed_at TIMESTAMP,
                signed_by UUID,
                shared_with_patient_at TIMESTAMP,
                shared_by UUID,
                source_transcript_type TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            ALTER TABLE soap_notes ADD COLUMN IF NOT EXISTS source_transcript_type TEXT;
            CREATE INDEX IF NOT EXISTS idx_soap_notes_doctor ON soap_notes(doctor_id);
            CREATE INDEX IF NOT EXISTS idx_soap_notes_patient_shared
                ON soap_notes(patient_id)
                WHERE shared_with_patient_at IS NOT NULL;

            CREATE TABLE IF NOT EXISTS soap_note_addenda (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                soap_note_id UUID NOT NULL REFERENCES soap_notes(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                added_by UUID NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_soap_note_addenda_note
                ON soap_note_addenda(soap_note_id, created_at);
            """
        )


def get_note_status_for_consultation(consultation_id: str) -> str | None:
    """Returns the current soap_notes.status for this consultation, or None if no note
    has ever been generated for it yet."""
    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM soap_notes WHERE consultation_id = %s",
                (consultation_id,),
            )
            row = cur.fetchone()
    return row[0] if row else None


def mark_note_stale_if_draft_exists(consultation_id: str) -> bool:
    """If a 'draft' note exists for this consultation, marks it 'stale' rather than
    silently leaving it intact after a speaker-label correction — the doctor must
    explicitly regenerate rather than risk signing a note that cites now-corrected-away
    speaker attributions. Returns True if a draft was actually marked, False if there was
    nothing to mark (no note yet, or it was already 'stale'). Callers are responsible for
    rejecting corrections outright when the note is already 'signed' — this function
    never touches a signed note (the WHERE clause only ever matches 'draft')."""
    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE soap_notes SET status = 'stale', updated_at = NOW() "
                "WHERE consultation_id = %s AND status = 'draft'",
                (consultation_id,),
            )
            marked = cur.rowcount > 0
        conn.commit()
    return marked


def _audit(cur, action: str, consultation_id: str | None, doctor_id: str | None, **metadata) -> None:
    """Mirrors consults.py's _audit exactly, writing to the same consult_audit_log
    table — every function below only calls this after get_consult_owned() has already
    run in the same call, which itself calls ensure_consult_schema(), so the table is
    guaranteed to exist by the time this runs without needing its own import of
    ensure_consult_schema (which would create a circular import at module load time)."""
    cur.execute(
        "INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata) VALUES (%s, %s, %s, %s::jsonb)",
        (consultation_id, doctor_id, action, json.dumps(metadata)),
    )


def _row_to_note(row, consultation_id: str, addenda: list[dict]) -> dict:
    (
        note_id, subjective, objective, assessment, plan, field_citations, confidence_flags,
        status, generated_at, edited_at, signed_at, signed_by, shared_with_patient_at, shared_by,
        source_transcript_type,
    ) = row
    return {
        "id": str(note_id),
        "consultation_id": consultation_id,
        "subjective": subjective,
        "objective": objective,
        "assessment": assessment,
        "plan": plan,
        "field_citations": field_citations,
        "confidence_flags": confidence_flags,
        "status": status,
        "generated_at": generated_at.isoformat() if generated_at else None,
        "edited_at": edited_at.isoformat() if edited_at else None,
        "signed_at": signed_at.isoformat() if signed_at else None,
        "signed_by": str(signed_by) if signed_by else None,
        "shared_with_patient_at": shared_with_patient_at.isoformat() if shared_with_patient_at else None,
        "shared_by": str(shared_by) if shared_by else None,
        # 'batch' (normal, high-accuracy pass) or 'live_fallback' (the batch
        # re-transcription pass failed and this note was generated from the raw
        # streaming-only transcript instead — see consults.py's
        # run_batch_retranscription/get_transcript docstrings). None for a note
        # generated before this field existed. The doctor reviewing this note should
        # see this context, since a live_fallback transcript is lower-confidence and
        # was never proofread by the batch pass.
        "source_transcript_type": source_transcript_type,
        "addenda": addenda,
    }


def _fetch_addenda(cur, note_id) -> list[dict]:
    cur.execute(
        "SELECT id, content, added_by, created_at FROM soap_note_addenda "
        "WHERE soap_note_id = %s ORDER BY created_at ASC",
        (note_id,),
    )
    return [
        {
            "id": str(addendum_id),
            "content": content,
            "added_by": str(added_by),
            "created_at": created_at.isoformat() if created_at else None,
        }
        for addendum_id, content, added_by, created_at in cur.fetchall()
    ]


def get_soap_note(consultation_id: str, doctor_id: str) -> dict | None:
    """Returns None if the consult doesn't exist/isn't owned by this doctor, OR if no
    note has been generated yet — callers distinguish those via a prior ownership check
    if they need to, but for a plain GET both are simply "nothing to show"."""
    from app.services.consults import get_consult_owned

    consult = get_consult_owned(consultation_id, doctor_id)
    if not consult:
        return None

    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_SOAP_NOTE_COLUMNS} FROM soap_notes WHERE consultation_id = %s",
                (consultation_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            addenda = _fetch_addenda(cur, row[0])
    return _row_to_note(row, consultation_id, addenda)


async def generate_soap_note(consultation_id: str, doctor_id: str) -> dict:
    """Runs the consult_documentation_graph subgraph over the corrected final
    transcript and creates/replaces the draft note. A 'stale' note (marked so by a
    speaker-label correction made after a draft existed — see consults.py's
    swap_all_speakers/correct_segment_speaker) is treated identically to 'draft':
    silently replaced, no confirmation step required here. This is a deliberate service-
    layer decision, not implied by the original spec (which only enumerates draft/signed)
    — a doctor who has started reviewing a draft and triggers a correction that makes it
    stale, then re-generates, should not be blocked by the API; any "are you sure, you'll
    lose your in-progress edits" warning belongs in the UI (Part 3), shown *before* this
    endpoint is even called, not enforced here. Only 'signed' is protected at this layer.
    """
    from app.services.consults import get_consult_owned, get_transcript
    from app.agents.consult_documentation_graph import agenerate_soap_note

    consult = get_consult_owned(consultation_id, doctor_id)
    if not consult:
        raise ValueError("Consult not found.")

    if get_note_status_for_consultation(consultation_id) == "signed":
        raise PermissionError(
            "This clinical note has already been signed. Add an addendum instead of regenerating."
        )

    if consult["status"] != "transcript_ready":
        raise ValueError("Transcript is not ready yet for this consult.")

    transcript = get_transcript(consultation_id, doctor_id)
    segments = (transcript or {}).get("segments") or []
    if not segments:
        raise ValueError("There is no transcript to generate a note from.")

    extracted = await agenerate_soap_note(consultation_id, str(consult.get("patient_id") or ""), segments)

    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO soap_notes (
                    consultation_id, doctor_id, patient_id, subjective, objective, assessment, plan,
                    field_citations, confidence_flags, status, generated_at, edited_at,
                    signed_at, signed_by, source_transcript_type, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, 'draft', NOW(), NULL, NULL, NULL, %s, NOW())
                ON CONFLICT (consultation_id) DO UPDATE SET
                    subjective = EXCLUDED.subjective,
                    objective = EXCLUDED.objective,
                    assessment = EXCLUDED.assessment,
                    plan = EXCLUDED.plan,
                    field_citations = EXCLUDED.field_citations,
                    confidence_flags = EXCLUDED.confidence_flags,
                    status = 'draft',
                    generated_at = NOW(),
                    edited_at = NULL,
                    signed_at = NULL,
                    signed_by = NULL,
                    source_transcript_type = EXCLUDED.source_transcript_type,
                    updated_at = NOW()
                WHERE soap_notes.status != 'signed'
                RETURNING id
                """,
                (
                    consultation_id, doctor_id, consult.get("patient_id"),
                    extracted["subjective"], extracted["objective"], extracted["assessment"], extracted["plan"],
                    json.dumps(extracted["field_citations"]), json.dumps(extracted["confidence_flags"]),
                    consult.get("transcript_source"),
                ),
            )
            row = cur.fetchone()
            if row is None:
                # ON CONFLICT ... DO UPDATE ... WHERE was false: a sign happened between
                # our check above and this INSERT. Treat identically to the up-front check.
                raise PermissionError(
                    "This clinical note has already been signed. Add an addendum instead of regenerating."
                )
            _audit(cur, "consult_soap_note_generated", consultation_id, doctor_id, note_id=str(row[0]))
        conn.commit()

    return get_soap_note(consultation_id, doctor_id)


def update_soap_note(consultation_id: str, doctor_id: str, fields: dict) -> dict:
    """Doctor edits to the note's text fields, permitted only while the note is
    'draft' or 'stale' — rejected at this layer (not just the UI) once 'signed'. PATCH
    deliberately does NOT clear a 'stale' status back to 'draft', even if the doctor
    manually edits every field: regeneration (generate_soap_note) is the ONLY way to
    clear staleness, since sign_soap_note rejects 'stale' outright. So a doctor can still
    use PATCH to adjust a stale note's text if they want to, but must regenerate before
    they can sign it — the UI should make this explicit rather than let a doctor edit a
    stale note expecting that alone to unblock signing."""
    from app.services.consults import get_consult_owned

    consult = get_consult_owned(consultation_id, doctor_id)
    if not consult:
        raise ValueError("Consult not found.")

    updates = {key: value for key, value in fields.items() if key in _SOAP_FIELDS and value is not None}
    if not updates:
        raise ValueError("No valid fields to update.")

    set_clause = ", ".join(f"{field} = %s" for field in updates)
    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE soap_notes SET {set_clause}, edited_at = NOW(), updated_at = NOW()
                WHERE consultation_id = %s AND status != 'signed'
                RETURNING id
                """,
                (*updates.values(), consultation_id),
            )
            row = cur.fetchone()
            if row is None:
                # Deliberately re-uses the already-open cursor/connection rather than
                # calling get_note_status_for_consultation() here — that helper opens
                # its OWN connect_db() block, and nesting one inside this still-open one
                # is unsafe: psycopg2's ThreadedConnectionPool keys connections by
                # thread id, so a nested call returns the SAME physical connection and
                # its exit prematurely commits and returns it to the pool while this
                # outer block still thinks it owns an open transaction. (Confirmed the
                # hard way: this exact nesting once left a connection stuck 'idle in
                # transaction', which then deadlocked every later
                # CREATE INDEX IF NOT EXISTS in ensure_soap_schema.)
                cur.execute("SELECT status FROM soap_notes WHERE consultation_id = %s", (consultation_id,))
                existing = cur.fetchone()
                if existing is None:
                    raise ValueError("No clinical note exists yet for this consult.")
                raise PermissionError("This clinical note has already been signed and can no longer be edited.")
            _audit(cur, "consult_soap_note_edited", consultation_id, doctor_id, fields=list(updates.keys()))
        conn.commit()

    return get_soap_note(consultation_id, doctor_id)


def sign_soap_note(consultation_id: str, doctor_id: str) -> dict:
    """Signing requires status = 'draft' specifically — a 'stale' note is rejected too,
    not just an already-'signed' one, since staleness means the note may cite
    speaker-attributions that were corrected away after generation; the doctor must
    resolve that (regenerate, or edit the affected fields) before it can be signed."""
    from app.services.consults import get_consult_owned

    consult = get_consult_owned(consultation_id, doctor_id)
    if not consult:
        raise ValueError("Consult not found.")

    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE soap_notes SET status = 'signed', signed_at = NOW(), signed_by = %s, updated_at = NOW()
                WHERE consultation_id = %s AND status = 'draft'
                RETURNING id
                """,
                (doctor_id, consultation_id),
            )
            row = cur.fetchone()
            if row is None:
                # Same nested-connection hazard as update_soap_note above — query
                # status via this already-open cursor, never a fresh connect_db() call.
                cur.execute("SELECT status FROM soap_notes WHERE consultation_id = %s", (consultation_id,))
                existing = cur.fetchone()
                if existing is None:
                    raise ValueError("No clinical note exists yet for this consult.")
                status = existing[0]
                if status == "signed":
                    raise PermissionError("This clinical note has already been signed.")
                raise PermissionError(
                    "This clinical note is stale (transcript labels changed since it was generated). "
                    "Regenerate or edit it before signing."
                )
            _audit(cur, "consult_soap_note_signed", consultation_id, doctor_id, note_id=str(row[0]))
        conn.commit()

    return get_soap_note(consultation_id, doctor_id)


def add_addendum(consultation_id: str, doctor_id: str, content: str) -> dict:
    """Addenda are the ONLY way to add information to a note once signed — the signed
    fields themselves are never touched again by this function or any other."""
    from app.services.consults import get_consult_owned

    consult = get_consult_owned(consultation_id, doctor_id)
    if not consult:
        raise ValueError("Consult not found.")

    content = (content or "").strip()
    if not content:
        raise ValueError("Addendum content cannot be empty.")

    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, status FROM soap_notes WHERE consultation_id = %s",
                (consultation_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("No clinical note exists yet for this consult.")
            note_id, status = row
            if status != "signed":
                raise PermissionError("Addenda can only be added to a signed clinical note.")

            cur.execute(
                "INSERT INTO soap_note_addenda (soap_note_id, content, added_by) VALUES (%s, %s, %s)",
                (note_id, content, doctor_id),
            )
            _audit(cur, "consult_soap_note_addendum_added", consultation_id, doctor_id, note_id=str(note_id))
        conn.commit()

    return get_soap_note(consultation_id, doctor_id)
