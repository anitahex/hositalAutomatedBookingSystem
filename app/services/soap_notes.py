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
from app.db.schema_once import once_per_process

_SOAP_FIELDS = ("subjective", "objective", "assessment", "plan")

_SOAP_NOTE_COLUMNS = (
    "id, subjective, objective, assessment, plan, field_citations, confidence_flags, "
    "status, generated_at, edited_at, signed_at, signed_by, shared_with_patient_at, shared_by, "
    "source_transcript_type, ai_model, ai_prompt_version"
)

# Review-queue scopes. 'pending' is the doctor's outstanding documentation work;
# 'completed' is the history of what they have already verified.
REVIEW_SCOPES = ("pending", "completed")

# Mirrors the limit discipline the doctor_* queries in appointments.py already use
# (doctor_appointments limit=100, doctor_patients limit=200) — a doctor's review queue
# is bounded per-doctor work, never an unbounded scan.
REVIEW_DEFAULT_LIMIT = 100
REVIEW_MAX_LIMIT = 200


@once_per_process
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
            -- AI provenance. Additive and nullable: a note generated before these existed
            -- simply reports no provenance rather than a wrong one. Mirrored by Alembic
            -- revision 0021, matching this file's existing dual-source convention.
            ALTER TABLE soap_notes ADD COLUMN IF NOT EXISTS ai_model TEXT;
            ALTER TABLE soap_notes ADD COLUMN IF NOT EXISTS ai_prompt_version TEXT;
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
                "WHERE consultation_id = %s AND status = 'draft' "
                "RETURNING id, doctor_id",
                (consultation_id,),
            )
            row = cur.fetchone()
            marked = row is not None
            if marked:
                # Recorded as a real event, not left to be inferred from status='stale'.
                # "AI held this note back" is something the doctor is told happened on
                # their activity feed, and a feed entry must be evidenced by an audit row
                # rather than reconstructed from current state — current state cannot say
                # WHEN it happened. doctor_id comes from the note row itself because the
                # caller (a transcript speaker-label correction) does not pass one.
                _audit(
                    cur, "consult_soap_note_held_back", consultation_id, str(row[1]),
                    note_id=str(row[0]), reason="transcript_labels_corrected",
                )
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
        source_transcript_type, ai_model, ai_prompt_version,
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
        # Which model and which prompt+style produced this draft. NULL for any note
        # generated before these columns existed — the UI must handle that rather than
        # claiming a model it cannot actually evidence.
        "ai_model": ai_model,
        "ai_prompt_version": ai_prompt_version,
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


def _low_confidence_count(confidence_flags) -> int:
    """confidence_flags maps each SOAP field to True when it is NOT confident (see
    consult_documentation_graph.soap_extractor_node, which stores `not field.confident`).
    A non-dict value is treated as "no flags" rather than raising — this feeds a
    dashboard count, and a malformed row must never break the whole queue."""
    if not isinstance(confidence_flags, dict):
        return 0
    return sum(1 for field in _SOAP_FIELDS if confidence_flags.get(field) is True)


def _review_row_to_dict(row) -> dict:
    (
        consultation_id, booking_id, patient_id, patient_name, department, appointment_start,
        consult_ended_at, transcript_source, note_id, note_status, generated_at, edited_at,
        signed_at, shared_with_patient_at, confidence_flags,
    ) = row

    # 'not_generated' is a real item of outstanding work, not an absence of one: the
    # consult was recorded and transcribed but no note was ever produced for it. Nothing
    # else in the application surfaces that state, so it belongs in this queue alongside
    # the drafts (see the plan's C4).
    if note_id is None:
        item_type = "not_generated"
    elif note_status == "signed":
        item_type = "signed"
    else:
        item_type = note_status  # 'draft' or 'stale'

    return {
        "consultation_id": str(consultation_id),
        "booking_id": str(booking_id),
        "patient_id": patient_id,
        "patient_name": patient_name,
        "department": department,
        "appointment_start": appointment_start.isoformat() if appointment_start else None,
        "consult_ended_at": consult_ended_at.isoformat() if consult_ended_at else None,
        "item_type": item_type,
        "note_id": str(note_id) if note_id else None,
        "note_status": note_status,
        "generated_at": generated_at.isoformat() if generated_at else None,
        "edited_at": edited_at.isoformat() if edited_at else None,
        "signed_at": signed_at.isoformat() if signed_at else None,
        "shared_with_patient_at": shared_with_patient_at.isoformat() if shared_with_patient_at else None,
        # Doctor-facing triage signals, all already persisted — see the plan's C1/C2/C3.
        "is_stale": note_status == "stale",
        "is_edited": edited_at is not None,
        "low_quality_transcript": transcript_source == "live_fallback",
        "low_confidence_fields": _low_confidence_count(confidence_flags),
    }


_REVIEW_SELECT = """
    SELECT
        c.id,
        c.booking_id,
        c.patient_id,
        COALESCE(pp.name, 'Unknown patient') AS patient_name,
        d.department,
        b.start_time,
        c.ended_at,
        c.transcript_source,
        sn.id AS note_id,
        sn.status AS note_status,
        sn.generated_at,
        sn.edited_at,
        sn.signed_at,
        sn.shared_with_patient_at,
        sn.confidence_flags
    FROM consultations c
    JOIN appointment_bookings b ON b.booking_id = c.booking_id
    JOIN doctors d ON d.doctor_id = c.doctor_id
    LEFT JOIN soap_notes sn ON sn.consultation_id = c.id
    LEFT JOIN patient_profiles pp ON pp.user_id::text = c.patient_id
"""

# A consult must have reached 'transcript_ready' for a note to be generatable at all
# (generate_soap_note enforces exactly that), and this clause additionally excludes a
# 'discarded' consult — discard_consult deletes the transcript but leaves any existing
# soap_notes row behind, which would otherwise surface here as phantom outstanding work.
_REVIEW_PENDING_WHERE = """
    WHERE c.doctor_id = %s
        AND c.status = 'transcript_ready'
        AND (sn.id IS NULL OR sn.status IN ('draft', 'stale'))
"""

# Deliberately NOT filtered on c.status: a signed note is a permanent clinical record and
# must stay in the doctor's history regardless of anything that happened to the consult
# row afterwards.
_REVIEW_COMPLETED_WHERE = """
    WHERE c.doctor_id = %s
        AND sn.status = 'signed'
"""


def list_reviews_for_doctor(doctor_id: str, scope: str = "pending", limit: int = REVIEW_DEFAULT_LIMIT) -> dict:
    """The doctor's own AI-note review queue: every consult of theirs that still needs
    documentation work ('pending'), or every note they have already signed ('completed').

    Scoped by doctor_id inside the SQL itself, exactly as every other doctor_* query in
    this codebase is — never post-filtered in Python, so a doctor can no more reach
    another doctor's review here than they can reach their appointments.

    Returns {"reviews": [...], "counts": {...}}. The counts are deliberately computed by
    their own aggregate query rather than from the returned rows: the row list is capped
    at `limit`, so counting it would silently under-report the moment a doctor has more
    outstanding work than one page. Both statements run on one connection and are indexed
    by idx_consultations_doctor / idx_soap_notes_doctor — there is no per-row query here.
    """
    if scope not in REVIEW_SCOPES:
        raise ValueError(f"scope must be one of {REVIEW_SCOPES}.")
    limit = max(1, min(int(limit), REVIEW_MAX_LIMIT))

    from app.services.appointments import ensure_booking_schema
    from app.services.consults import ensure_consult_schema

    if scope == "completed":
        where = _REVIEW_COMPLETED_WHERE
        # Most recently verified first — this is a history view, not a work queue.
        order = "ORDER BY sn.signed_at DESC"
    else:
        where = _REVIEW_PENDING_WHERE
        # Stale notes first because they are *blocked*, not merely old: sign_soap_note
        # rejects a stale note outright, so it needs the doctor before anything else in
        # the list. Everything after that is plain appointment order — oldest unreviewed
        # visit first. This is workflow freshness, NOT a clinical-urgency ranking (no
        # severity is persisted anywhere in this schema to rank by).
        order = "ORDER BY COALESCE(sn.status = 'stale', FALSE) DESC, b.start_time ASC"

    with connect_db() as conn:
        ensure_booking_schema(conn)
        ensure_consult_schema(conn)
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(f"{_REVIEW_SELECT}{where}{order}\nLIMIT %s", (doctor_id, limit))
            rows = cur.fetchall()

            cur.execute(
                f"""
                SELECT
                    COUNT(*) AS pending,
                    COUNT(*) FILTER (WHERE sn.id IS NULL) AS not_generated,
                    COUNT(*) FILTER (WHERE sn.status = 'draft') AS draft,
                    COUNT(*) FILTER (WHERE sn.status = 'stale') AS stale,
                    COUNT(*) FILTER (WHERE c.transcript_source = 'live_fallback') AS low_quality_transcript
                FROM consultations c
                JOIN appointment_bookings b ON b.booking_id = c.booking_id
                LEFT JOIN soap_notes sn ON sn.consultation_id = c.id
                {_REVIEW_PENDING_WHERE}
                """,
                (doctor_id,),
            )
            pending, not_generated, draft, stale, low_quality = cur.fetchone()

    return {
        "reviews": [_review_row_to_dict(row) for row in rows],
        # Always the *pending* counts, whichever scope was requested — these drive the
        # dashboard's "what still needs me" stat cards, which must not change meaning
        # just because the doctor happens to be looking at their history tab.
        "counts": {
            "pending": int(pending),
            "not_generated": int(not_generated),
            "draft": int(draft),
            "stale": int(stale),
            "low_quality_transcript": int(low_quality),
        },
    }


async def generate_soap_note(
    consultation_id: str, doctor_id: str, style: str = "concise",
) -> dict:
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
    from app.services.soap_sections import (
        clear_verifications_for_note, ensure_section_verification_schema,
    )

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

    extracted = await agenerate_soap_note(
        consultation_id, str(consult.get("patient_id") or ""), segments, style,
    )

    with connect_db() as conn:
        ensure_soap_schema(conn)
        # Needed because this function clears the note's section-verification marks below;
        # the table must exist even on a database whose first ever note is this one.
        ensure_section_verification_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO soap_notes (
                    consultation_id, doctor_id, patient_id, subjective, objective, assessment, plan,
                    field_citations, confidence_flags, status, generated_at, edited_at,
                    signed_at, signed_by, source_transcript_type, ai_model, ai_prompt_version, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, 'draft', NOW(), NULL, NULL, NULL, %s, %s, %s, NOW())
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
                    ai_model = EXCLUDED.ai_model,
                    ai_prompt_version = EXCLUDED.ai_prompt_version,
                    updated_at = NOW()
                WHERE soap_notes.status != 'signed'
                RETURNING id
                """,
                (
                    consultation_id, doctor_id, consult.get("patient_id"),
                    extracted["subjective"], extracted["objective"], extracted["assessment"], extracted["plan"],
                    json.dumps(extracted["field_citations"]), json.dumps(extracted["confidence_flags"]),
                    consult.get("transcript_source"),
                    # .get(), not [...]: provenance is metadata about the generation, and
                    # a generator that did not report it must still produce a usable note
                    # with NULL provenance rather than failing the whole request.
                    extracted.get("ai_model"), extracted.get("ai_prompt_version"),
                ),
            )
            row = cur.fetchone()
            if row is None:
                # ON CONFLICT ... DO UPDATE ... WHERE was false: a sign happened between
                # our check above and this INSERT. Treat identically to the up-front check.
                raise PermissionError(
                    "This clinical note has already been signed. Add an addendum instead of regenerating."
                )
            # Regenerating replaces every field, so any "I have checked this section" marks
            # refer to text that no longer exists. Carrying them forward would show the
            # doctor "3 of 4 verified" against sections nobody has read. Cleared through
            # this same cursor and committed with the rest of the regeneration, so the note
            # and its review progress can never disagree.
            clear_verifications_for_note(cur, row[0])
            _audit(
                cur, "consult_soap_note_generated", consultation_id, doctor_id,
                note_id=str(row[0]), style=style,
                ai_model=extracted.get("ai_model"), ai_prompt_version=extracted.get("ai_prompt_version"),
            )
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


def share_soap_note(consultation_id: str, doctor_id: str) -> dict:
    """Makes a SIGNED note visible to the patient. Deliberately a separate, explicit
    doctor action from signing (this module's header has said so since the schema was
    introduced): signing is the clinical act, sharing is a disclosure decision, and a
    doctor may legitimately sign a note they do not want the patient reading unprompted.

    One-way by design, mirroring sign_soap_note's irreversibility — there is no unshare
    operation anywhere in this module, because withdrawing access cannot un-read a note
    the patient has already opened. Idempotent: re-sharing an already-shared note returns
    it unchanged rather than erroring (same rationale as end_consult) and writes no
    second audit row, since nothing changed.

    Only ever exposes a signed note. An unsigned draft is AI output that no clinician has
    accepted responsibility for, and must never reach a patient.
    """
    from app.services.consults import get_consult_owned

    consult = get_consult_owned(consultation_id, doctor_id)
    if not consult:
        raise ValueError("Consult not found.")

    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE soap_notes
                SET shared_with_patient_at = NOW(), shared_by = %s, updated_at = NOW()
                WHERE consultation_id = %s AND status = 'signed' AND shared_with_patient_at IS NULL
                RETURNING id
                """,
                (doctor_id, consultation_id),
            )
            row = cur.fetchone()
            if row is None:
                # Same nested-connection hazard as update_soap_note/sign_soap_note —
                # query status via this already-open cursor, never a fresh connect_db().
                cur.execute(
                    "SELECT status, shared_with_patient_at FROM soap_notes WHERE consultation_id = %s",
                    (consultation_id,),
                )
                existing = cur.fetchone()
                if existing is None:
                    raise ValueError("No clinical note exists yet for this consult.")
                status, already_shared_at = existing
                if status != "signed":
                    raise PermissionError(
                        "Only a signed clinical note can be shared with the patient. Sign it first."
                    )
                if already_shared_at is None:
                    # Signed and unshared, yet the UPDATE matched nothing: the row changed
                    # underneath this transaction. Never report success we didn't achieve.
                    raise PermissionError("This clinical note could not be shared. Please retry.")
                # Already shared — idempotent no-op, no second audit row.
                conn.commit()
                return get_soap_note(consultation_id, doctor_id)
            _audit(cur, "consult_soap_note_shared", consultation_id, doctor_id, note_id=str(row[0]))
        conn.commit()

    return get_soap_note(consultation_id, doctor_id)


# What a PATIENT is allowed to see of a clinical note. Deliberately excludes
# field_citations and confidence_flags (documentation-quality signals written for a
# clinician — a patient reading "Needs review" on their assessment would reasonably hear
# "my diagnosis is uncertain"), source_transcript_type, and anything about the
# transcript or the model. See the plan's "must not be exposed to patients".
_PATIENT_VISIBLE_NOTE_FIELDS = (
    "subjective", "objective", "assessment", "plan", "signed_at", "shared_with_patient_at",
)


def list_shared_notes_for_patient(patient_id: str, booking_ids: list[str]) -> dict[str, dict]:
    """Signed-and-shared notes for this patient, keyed by booking_id.

    Follows the exact pattern consults.list_latest_consult_status_by_booking already
    established for the doctor's appointment list: one batched query keyed by booking_id,
    enriching a list the caller already has, rather than a per-row round trip or a LEFT
    JOIN bolted onto appointments.py (whose queries deliberately know nothing about the
    consult/SOAP tables — those live only in Alembic and the runtime ensure_* helpers, so
    a join from there would hard-fail on a database bootstrapped from schema.sql alone).

    Scoped by patient_id AND shared_with_patient_at IS NOT NULL AND status = 'signed' in
    the SQL itself — a patient can reach no note that is unsigned, unshared, or somebody
    else's, regardless of what booking_ids they manage to supply.
    """
    if not booking_ids:
        return {}

    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.booking_id, sn.subjective, sn.objective, sn.assessment, sn.plan,
                       sn.signed_at, sn.shared_with_patient_at, d.name
                FROM soap_notes sn
                JOIN consultations c ON c.id = sn.consultation_id
                JOIN doctors d ON d.doctor_id = sn.doctor_id
                WHERE sn.patient_id = %s
                    AND c.booking_id::text = ANY(%s)
                    AND sn.status = 'signed'
                    AND sn.shared_with_patient_at IS NOT NULL
                """,
                (patient_id, booking_ids),
            )
            rows = cur.fetchall()

    return {
        str(booking_id): {
            "subjective": subjective,
            "objective": objective,
            "assessment": assessment,
            "plan": plan,
            "signed_at": signed_at.isoformat() if signed_at else None,
            "shared_at": shared_at.isoformat() if shared_at else None,
            "doctor_name": doctor_name,
        }
        for booking_id, subjective, objective, assessment, plan, signed_at, shared_at, doctor_name in rows
    }


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
