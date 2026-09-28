"""Per-section "I have checked this" marks on a draft SOAP note (plan §4.6).

WHAT THIS IS NOT. A verification mark is a workflow aid — it tracks how far a doctor has
got through reviewing a draft, so the note screen can show "2 of 4 sections verified" and
the doctor can put the note down and come back to it. It is NOT a second signature, it
carries no clinical authority of its own, and it does not gate signing:

  - Signing remains governed entirely by soap_notes.sign_soap_note. A 'stale' (blocked)
    note stays unsignable no matter what is recorded here, because that check lives in
    that function's WHERE clause and nothing in this module touches it.
  - Unresolved confidence flags WARN at the confirmation step, they do not block
    (docs/ai-redesign/plan.md D4): confidence_flags is the model's self-assessment, and a
    doctor who has read the transcript overrules it. Making the model's uncertainty
    veto a clinician would invert the "AI drafts, you decide" principle.

Marks are only meaningful while the note is still a draft, so they are rejected once the
note is signed: at that point the doctor's signature is the record of review, and a
"verified" mark added afterwards would imply a review step that never happened.

Stored in its own table rather than as columns on soap_notes: this is per-section,
per-doctor data about the REVIEW process, and it must never sit alongside — or risk being
written into — the signed clinical content.
"""
from __future__ import annotations

import json

from app.db.connection import connect_db
from app.services.doctor_workspace import SOAP_SECTIONS
from app.db.schema_once import once_per_process


@once_per_process
def ensure_section_verification_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS soap_note_section_verifications (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                soap_note_id UUID NOT NULL REFERENCES soap_notes(id) ON DELETE CASCADE,
                section TEXT NOT NULL CHECK (section IN ('subjective', 'objective', 'assessment', 'plan')),
                verified_by UUID NOT NULL,
                verified_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (soap_note_id, section)
            );
            CREATE INDEX IF NOT EXISTS idx_soap_section_verifications_note
                ON soap_note_section_verifications(soap_note_id);
            """
        )


def validate_section(section: str) -> str:
    normalized = (section or "").strip().lower()
    if normalized not in SOAP_SECTIONS:
        raise ValueError(f"section must be one of {SOAP_SECTIONS}.")
    return normalized


def _audit(cur, action: str, consultation_id: str, doctor_id: str, **metadata) -> None:
    """Writes to the same consult_audit_log every other clinical action in this codebase
    uses. Callers reach this only after get_consult_owned() has run, which itself calls
    ensure_consult_schema(), so the table is guaranteed to exist."""
    cur.execute(
        "INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata) "
        "VALUES (%s, %s, %s, %s::jsonb)",
        (consultation_id, doctor_id, action, json.dumps(metadata)),
    )


def list_verified_sections(consultation_id: str, doctor_id: str) -> list[str]:
    """The sections this consult's note has been marked verified on. Returns [] for a
    consult with no note yet, rather than raising — the note screen renders an empty
    progress bar in that case."""
    from app.services.consults import get_consult_owned

    if not get_consult_owned(consultation_id, doctor_id):
        raise ValueError("Consult not found.")

    with connect_db() as conn:
        ensure_section_verification_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.section
                FROM soap_note_section_verifications v
                JOIN soap_notes sn ON sn.id = v.soap_note_id
                WHERE sn.consultation_id = %s
                ORDER BY v.section
                """,
                (consultation_id,),
            )
            return [row[0] for row in cur.fetchall()]


def set_section_verified(
    consultation_id: str, doctor_id: str, section: str, verified: bool = True,
) -> dict:
    """Marks one section verified, or clears that mark.

    Idempotent in both directions: marking an already-marked section succeeds without
    moving its timestamp or writing a second audit row, and clearing an unmarked one is a
    no-op. Rejected once the note is signed (see this module's header).

    Returns {"verified_sections": [...]} — the caller pairs it with
    doctor_workspace.verification_progress() to render the bar.
    """
    from app.services.consults import get_consult_owned

    section = validate_section(section)
    if not get_consult_owned(consultation_id, doctor_id):
        raise ValueError("Consult not found.")

    with connect_db() as conn:
        ensure_section_verification_schema(conn)
        with conn.cursor() as cur:
            # Note id AND status read through this same cursor — never a nested
            # connect_db(), for the pool-reentrancy reason documented at length in
            # soap_notes.update_soap_note (a nested call returns the SAME physical
            # connection and commits it early, stranding this transaction).
            cur.execute(
                "SELECT id, status FROM soap_notes WHERE consultation_id = %s",
                (consultation_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("No clinical note exists yet for this consult.")
            note_id, status = row
            if status == "signed":
                raise PermissionError(
                    "This note is signed. Its signature is the record of review — sections "
                    "can no longer be marked."
                )

            if verified:
                cur.execute(
                    """
                    INSERT INTO soap_note_section_verifications (soap_note_id, section, verified_by)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (soap_note_id, section) DO NOTHING
                    RETURNING id
                    """,
                    (note_id, section, doctor_id),
                )
                changed = cur.fetchone() is not None
            else:
                cur.execute(
                    "DELETE FROM soap_note_section_verifications "
                    "WHERE soap_note_id = %s AND section = %s",
                    (note_id, section),
                )
                changed = cur.rowcount > 0

            # Only audit a real transition — a repeated call changed nothing, and an audit
            # row claiming otherwise would misrepresent the review history.
            if changed:
                _audit(
                    cur,
                    "consult_soap_section_verified" if verified else "consult_soap_section_unverified",
                    consultation_id, doctor_id, section=section, note_id=str(note_id),
                )

            cur.execute(
                "SELECT section FROM soap_note_section_verifications "
                "WHERE soap_note_id = %s ORDER BY section",
                (note_id,),
            )
            sections = [r[0] for r in cur.fetchall()]
        conn.commit()

    return {"verified_sections": sections}


def clear_verifications_for_note(cur, note_id) -> None:
    """Drops every mark on a note, for a caller that already holds an open cursor.

    Called when a note is REGENERATED: the text the doctor verified no longer exists, so
    carrying the marks forward would show "3 of 4 verified" against sections nobody has
    read. Takes a cursor rather than opening its own connection, for the same
    pool-reentrancy reason as above.
    """
    cur.execute("DELETE FROM soap_note_section_verifications WHERE soap_note_id = %s", (note_id,))
