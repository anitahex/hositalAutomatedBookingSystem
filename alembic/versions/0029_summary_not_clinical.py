"""The lines a summary set aside as non-clinical, so every other line can be accounted for.

A summary written to "the abnormal findings" lost every medication and instruction on a
real prescription, and nothing noticed. Completeness is now checked by code: each line of
the document must be inside a verified sentence's quote, a parsed result, or one of these
set-aside lines (letterhead, phone numbers, signatures), which are themselves checked
verbatim against the page before they are stored. Any other line is shown to the doctor as
written. See document_grounding.uncovered_lines.

revision: 0029_summary_not_clinical
"""
from alembic import op

revision = "0029_summary_not_clinical"
down_revision = "0028_nutrition_guidance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE document_summaries ADD COLUMN IF NOT EXISTS not_clinical JSONB NOT NULL DEFAULT '[]'::jsonb;"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE document_summaries DROP COLUMN IF EXISTS not_clinical;")
