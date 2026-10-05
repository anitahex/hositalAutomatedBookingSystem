"""Earlier versions of a document's summary and measurements, kept when they are replaced.

Re-summarising or re-deriving a document rewrote its summary and measurements in place, so
the text a doctor had verified was lost. Before every overwrite the row is now copied here,
whole, in the same transaction (app/services/document_versions.py).

The app creates these tables at startup too (document_versions.ensure_document_versions_schema),
because production's database is stamped rather than migrated; IF NOT EXISTS keeps the two
safe together.

revision: 0034_document_versions
"""
from alembic import op

revision = "0034_document_versions"
down_revision = "0033_nutrition_handouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_summary_versions (
            id BIGSERIAL PRIMARY KEY,
            document_id TEXT NOT NULL,
            generated_at TIMESTAMPTZ,
            previous JSONB NOT NULL,
            replaced_by TEXT NOT NULL,
            replaced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_document_summary_versions_document
            ON document_summary_versions (document_id, generated_at DESC);
        CREATE TABLE IF NOT EXISTS document_findings_versions (
            id BIGSERIAL PRIMARY KEY,
            document_id TEXT NOT NULL,
            printed_name TEXT,
            previous JSONB NOT NULL,
            replaced_by TEXT NOT NULL,
            replaced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_document_findings_versions_document
            ON document_findings_versions (document_id, replaced_at DESC);
        """
    )


def downgrade() -> None:
    # Dropping these would delete the only copy of what doctors verified before a document
    # was re-processed. A downgrade leaves them in place.
    pass
