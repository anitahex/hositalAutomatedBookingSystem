"""Food guidance written once per finding or symptom, and reused for every patient.

The AI nutritionist is model-written, but it must say the same thing to every patient with
the same result. So the model never sees a patient: it writes guidance for one TERM —
"Vitamin D, low", "Blood lipids, abnormal", "symptom: constipation" — which is checked by
code and stored here. Every later patient with that term gets this exact row; the patient-
specific part ("Vitamin D 13.8 ng/mL, low — Blood Report, 20 Sep, p2") is attached by code
from the record, never written by the model.

Keyed by prompt_version as well, so changing the prompt produces new rows rather than
silently mixing two generations of advice. `entry` holds only what passed the checks in
app/services/nutrition.py.

revision: 0028_nutrition_guidance
"""
from alembic import op

revision = "0028_nutrition_guidance"
down_revision = "0027_document_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS nutrition_guidance (
            kind TEXT NOT NULL CHECK (kind IN ('finding', 'symptom')),
            term TEXT NOT NULL,
            direction TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            entry JSONB NOT NULL,
            model TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (kind, term, direction, prompt_version)
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS nutrition_guidance;")
