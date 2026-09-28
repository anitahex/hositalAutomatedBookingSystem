"""Doctor-authored clinical actions attached to a consultation: prescription, care plan,
and referral.

WHAT THIS IS NOT. Nothing in this module is generated, suggested, completed or checked by
a model. There is no formulary, no dose validation, no allergy cross-check and no
drug-interaction checking anywhere in this application, and none is implied by storing a
prescription here. This is a record of what a clinician decided and typed, nothing more —
it is not clinical decision support, and it is not a transmissible or dispensable
prescription. The implementation plan classified the demo's AI-suggested versions of these
tabs as DO NOT USE for exactly that reason; this is the doctor-authored form instead.

Lifecycle mirrors soap_notes deliberately, so there is one approval concept in this
codebase rather than two: 'draft' is editable, 'approved' is immutable. Unlike a SOAP
note there is no AI to regenerate from, so an approved item has no addendum mechanism —
the doctor writes a new item on a later consultation instead.
"""
from __future__ import annotations

import json

from app.db.connection import connect_db
from app.db.schema_once import once_per_process

ITEM_KINDS = ("prescription", "care_plan", "referral")

_ITEM_COLUMNS = "id, kind, content, status, created_at, updated_at, approved_at, approved_by"

# Same cap and rationale as appointments._sanitize_booking_note: this is free text that
# ends up rendered in a clinician's browser and stored indefinitely, so it is bounded at
# the service layer rather than trusting the client to limit it.
CONTENT_MAX_LENGTH = 5000


@once_per_process
def ensure_clinical_items_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS consult_clinical_items (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                consultation_id UUID NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
                doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                patient_id TEXT,
                kind TEXT NOT NULL CHECK (kind IN ('prescription', 'care_plan', 'referral')),
                content TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                approved_at TIMESTAMP,
                approved_by UUID,
                UNIQUE (consultation_id, kind)
            );
            CREATE INDEX IF NOT EXISTS idx_consult_clinical_items_consultation
                ON consult_clinical_items(consultation_id);
            CREATE INDEX IF NOT EXISTS idx_consult_clinical_items_doctor
                ON consult_clinical_items(doctor_id);
            """
        )


def _audit(cur, action: str, consultation_id: str, doctor_id: str, **metadata) -> None:
    """Writes to the same consult_audit_log every other clinical action in this codebase
    uses. Callers reach this only after get_consult_owned() has run, which itself calls
    ensure_consult_schema(), so the table is guaranteed to exist."""
    cur.execute(
        "INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata) "
        "VALUES (%s, %s, %s, %s::jsonb)",
        (consultation_id, doctor_id, action, json.dumps(metadata)),
    )


def _row_to_item(row, consultation_id: str, kind: str) -> dict:
    if row is None:
        # An item that has never been written is reported as an empty draft rather than
        # absent, so the UI has one shape to render instead of two.
        return {
            "consultation_id": consultation_id, "kind": kind, "content": "",
            "status": "draft", "approved_at": None, "approved_by": None,
            "created_at": None, "updated_at": None,
        }
    item_id, row_kind, content, status, created_at, updated_at, approved_at, approved_by = row
    return {
        "id": str(item_id),
        "consultation_id": consultation_id,
        "kind": row_kind,
        "content": content,
        "status": status,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "approved_at": approved_at.isoformat() if approved_at else None,
        "approved_by": str(approved_by) if approved_by else None,
    }


def _validate(kind: str) -> None:
    if kind not in ITEM_KINDS:
        raise ValueError(f"kind must be one of {ITEM_KINDS}.")


def get_clinical_item(consultation_id: str, doctor_id: str, kind: str) -> dict:
    from app.services.consults import get_consult_owned

    _validate(kind)
    if not get_consult_owned(consultation_id, doctor_id):
        raise ValueError("Consult not found.")

    with connect_db() as conn:
        ensure_clinical_items_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_ITEM_COLUMNS} FROM consult_clinical_items "
                "WHERE consultation_id = %s AND kind = %s",
                (consultation_id, kind),
            )
            row = cur.fetchone()
    return _row_to_item(row, consultation_id, kind)


def save_clinical_item(consultation_id: str, doctor_id: str, kind: str, content: str) -> dict:
    """Upserts the draft. Rejected once approved — an approved item is immutable, exactly
    as a signed SOAP note is."""
    from app.services.consults import get_consult_owned

    _validate(kind)
    consult = get_consult_owned(consultation_id, doctor_id)
    if not consult:
        raise ValueError("Consult not found.")

    content = (content or "").strip()
    if len(content) > CONTENT_MAX_LENGTH:
        raise ValueError(f"Content is too long (max {CONTENT_MAX_LENGTH} characters).")

    with connect_db() as conn:
        ensure_clinical_items_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO consult_clinical_items
                    (consultation_id, doctor_id, patient_id, kind, content, status, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'draft', NOW())
                ON CONFLICT (consultation_id, kind) DO UPDATE SET
                    content = EXCLUDED.content,
                    updated_at = NOW()
                WHERE consult_clinical_items.status != 'approved'
                RETURNING id
                """,
                (consultation_id, doctor_id, consult.get("patient_id"), kind, content),
            )
            if cur.fetchone() is None:
                raise PermissionError(
                    "This record has already been approved and can no longer be edited."
                )
            _audit(cur, "consult_clinical_item_saved", consultation_id, doctor_id, kind=kind)
        conn.commit()

    return get_clinical_item(consultation_id, doctor_id, kind)


def approve_clinical_item(consultation_id: str, doctor_id: str, kind: str) -> dict:
    """Locks the record. Irreversible, matching sign_soap_note — approving is a clinical
    act, and a reversible one would make the record's meaning ambiguous."""
    from app.services.consults import get_consult_owned

    _validate(kind)
    if not get_consult_owned(consultation_id, doctor_id):
        raise ValueError("Consult not found.")

    with connect_db() as conn:
        ensure_clinical_items_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE consult_clinical_items
                SET status = 'approved', approved_at = NOW(), approved_by = %s, updated_at = NOW()
                WHERE consultation_id = %s AND kind = %s AND status = 'draft'
                    AND length(trim(content)) > 0
                RETURNING id
                """,
                (doctor_id, consultation_id, kind),
            )
            if cur.fetchone() is None:
                # Query state through this same cursor — never a nested connect_db(), for
                # the pool-reentrancy reason documented in soap_notes.update_soap_note.
                cur.execute(
                    "SELECT status, length(trim(content)) FROM consult_clinical_items "
                    "WHERE consultation_id = %s AND kind = %s",
                    (consultation_id, kind),
                )
                existing = cur.fetchone()
                if existing is None or existing[1] == 0:
                    raise ValueError("There is nothing to approve — write the record first.")
                if existing[0] == "approved":
                    raise PermissionError("This record has already been approved.")
                raise PermissionError("This record could not be approved. Please retry.")
            _audit(cur, "consult_clinical_item_approved", consultation_id, doctor_id, kind=kind)
        conn.commit()

    return get_clinical_item(consultation_id, doctor_id, kind)
