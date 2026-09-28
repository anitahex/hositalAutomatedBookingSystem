"""Doctor AI workspace: previous-login window, doctor-scoped audit index, section verification.

Three additions, all purely additive (no column drops, no type changes, no backfill), so
this is safe to apply ahead of the code that reads it and safe under a rolling deploy.

1. doctor_accounts.previous_login_at — the login BEFORE the current one.

   doctor_accounts.last_login_at already exists, but complete_mfa_challenge() overwrites it
   as part of authenticating, so by the time the doctor's overview renders it already reads
   "now". It therefore cannot answer "what did AI do since your last session?". This column
   holds the value last_login_at had immediately before the current login, which is exactly
   that window's lower bound. NULL for an account that has never logged in twice; the
   activity summary falls back to a 24h window in that case rather than inventing one.

2. idx_consult_audit_doctor — consult_audit_log(doctor_id, created_at DESC).

   consult_audit_log has existed since 0007 with only idx_consult_audit_consultation on
   (consultation_id, created_at DESC). The new doctor-facing AI activity feed reads that
   table by doctor_id over a time window, which without this index is a full scan of a
   table that grows with every clinical action in the system.

3. soap_note_section_verifications — per-section "I have checked this" marks.

   Deliberately a separate table rather than four columns on soap_notes: this is
   per-section, per-doctor, append-only, audit-shaped data about the REVIEW process, and
   it must never sit alongside — or risk being written into — the signed clinical content.
   ON DELETE CASCADE from soap_notes so a deleted note leaves no orphaned review state.

   Note this table records only that a doctor marked a section checked. It is a workflow
   aid; it is NOT a second signature and it does not gate signing (see
   docs/ai-redesign/plan.md D4 — flags warn, they do not block; a 'stale' note stays
   unsignable via soap_notes.status regardless of anything recorded here).

Mirrors the runtime ensure_*_schema() helpers, per this repo's convention of keeping both
in step (see 0007 and 0021, which did the same).

Reversible: downgrade drops the index, the table and the column. Dropping them discards
the review-progress marks and the previous-login bound recorded while this revision was
applied; no clinical content is affected, because none is stored here.

revision: 0022_doctor_workspace_ai
"""
from alembic import op

revision = "0022_doctor_workspace_ai"
down_revision = "0021_soap_ai_provenance_and_clinical_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE doctor_accounts ADD COLUMN IF NOT EXISTS previous_login_at TIMESTAMP;

        CREATE INDEX IF NOT EXISTS idx_consult_audit_doctor
            ON consult_audit_log(doctor_id, created_at DESC);

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


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS soap_note_section_verifications;
        DROP INDEX IF EXISTS idx_consult_audit_doctor;
        ALTER TABLE doctor_accounts DROP COLUMN IF EXISTS previous_login_at;
        """
    )
