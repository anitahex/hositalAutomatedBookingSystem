"""The food handouts doctors give patients, kept in the patient's account.

A doctor makes a handout from the AI nutritionist; the patient then finds the same handout
under Records & history, with the doctor and the date. `content` is built by code from the
checked guidance (nutrition_plan.build_handout): theme titles, foods, things to go easy on,
tips and a sample day — no values, no document names, no doses. Creating one is also
audited in consult_audit_log.

The app creates this table at startup too (nutrition_plan.ensure_handout_schema), because
production's database is stamped rather than migrated; IF NOT EXISTS keeps the two safe
together.

revision: 0033_nutrition_handouts
"""
from alembic import op

revision = "0033_nutrition_handouts"
down_revision = "0032_nutrition_discussions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS nutrition_handouts (
            id BIGSERIAL PRIMARY KEY,
            patient_id TEXT NOT NULL,
            doctor_id UUID NOT NULL,
            booking_id UUID,
            document_id TEXT,
            diet TEXT NOT NULL,
            content JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_nutrition_handouts_patient
            ON nutrition_handouts (patient_id, created_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS nutrition_handouts;")
