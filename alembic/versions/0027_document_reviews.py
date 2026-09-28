"""Doctors verifying a document's AI summary and values against the original.

Every treating doctor sees the same document, so a verification is SHARED: each doctor's
review is a row here, everyone sees who verified and when, and anyone may report the
summary inaccurate (with a reason), which everyone then sees too.

APPEND-ONLY. A doctor's current position on a document is their LATEST row; withdrawing a
verification or clearing a report adds a row rather than deleting one, so the history of
who said what, and when, is never lost.

TIED TO THE SUMMARY IT REVIEWED. `summary_generated_at` records which version of the
summary the doctor looked at. When a document is re-processed the summary gets a new
generated_at, and every earlier review stops counting automatically — a doctor never
appears to have verified text they never saw. NULL when the document has no summary (the
doctor verified the extracted values alone).

`review_seq` orders two rows written in the same instant; created_at alone cannot.

revision: 0027_document_reviews
"""
from alembic import op

revision = "0027_document_reviews"
down_revision = "0026_findings_report_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_reviews (
            review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            review_seq BIGSERIAL NOT NULL,
            document_id TEXT NOT NULL,
            patient_id TEXT NOT NULL,
            doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
            action TEXT NOT NULL
                CHECK (action IN ('verified', 'withdrawn', 'flagged_inaccurate', 'flag_cleared')),
            reason TEXT,
            summary_generated_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            CHECK (action <> 'flagged_inaccurate' OR length(btrim(coalesce(reason, ''))) > 0)
        );
        CREATE INDEX IF NOT EXISTS ix_document_reviews_document
            ON document_reviews (document_id, doctor_id, review_seq DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_reviews;")
