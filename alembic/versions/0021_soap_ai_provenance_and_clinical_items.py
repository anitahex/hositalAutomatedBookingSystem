"""AI provenance on soap_notes, and doctor-authored clinical items.

Two additions, both purely additive:

1. soap_notes.ai_model / ai_prompt_version — which model and which prompt+style produced
   a draft. Before this, "which model wrote what the doctor signed?" was only answerable
   indirectly via token_logs, and only when patient_id happened to be non-empty. Nullable
   because every note generated before this migration genuinely has no provenance, and
   reporting none is honest where guessing one would not be.

2. consult_clinical_items — prescription / care plan / referral, authored and approved by
   the doctor. Nothing in it is AI-generated, suggested or validated; there is no
   formulary, dose or interaction checking anywhere in this application.

Mirrors the runtime ensure_soap_schema() / ensure_clinical_items_schema() helpers, per
this repo's convention of keeping both in step (see 0007, which did the same for the
consult and SOAP tables).

Reversible: downgrade drops the two columns and the new table. Dropping the columns
discards provenance for notes generated while this revision was applied, which is
acceptable because nothing else reads them.

revision: 0021_soap_ai_provenance_and_clinical_items
"""
from alembic import op

revision = "0021_soap_ai_provenance_and_clinical_items"
down_revision = "0020_patient_name_parts_and_gender"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE soap_notes ADD COLUMN IF NOT EXISTS ai_model TEXT;
        ALTER TABLE soap_notes ADD COLUMN IF NOT EXISTS ai_prompt_version TEXT;

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


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS consult_clinical_items;
        ALTER TABLE soap_notes DROP COLUMN IF EXISTS ai_prompt_version;
        ALTER TABLE soap_notes DROP COLUMN IF EXISTS ai_model;
        """
    )
