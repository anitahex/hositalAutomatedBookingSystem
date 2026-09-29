"""Which nutrition topics a doctor has discussed with the patient.

The AI nutritionist groups a patient's food guidance into themes (Inflammation & pain,
Vitamins & blood, ...). A doctor marks a theme discussed; the next visit shows who discussed
it and when, so the same advice is not given from scratch each time. One row per mark;
withdrawing a mark deletes that doctor's own row for that visit. Every mark and withdrawal is
also audited in consult_audit_log.

The app creates this table at startup too (nutrition_plan.ensure_discussion_schema), because
production's database is stamped rather than migrated; IF NOT EXISTS keeps the two safe
together.

revision: 0032_nutrition_discussions
"""
from alembic import op

revision = "0032_nutrition_discussions"
down_revision = "0031_repair_account_lookups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS nutrition_discussions (
            id BIGSERIAL PRIMARY KEY,
            patient_id TEXT NOT NULL,
            theme TEXT NOT NULL,
            doctor_id UUID NOT NULL,
            booking_id UUID,
            discussed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_nutrition_discussions_patient
            ON nutrition_discussions (patient_id, theme, discussed_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS nutrition_discussions;")
