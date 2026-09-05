"""Add persisted patient preferred language."""

from alembic import op

revision = "0003_add_preferred_language"
down_revision = "0002_add_document_original_filename"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS preferred_language TEXT NOT NULL DEFAULT 'en';")


def downgrade():
    op.execute("ALTER TABLE patient_profiles DROP COLUMN IF EXISTS preferred_language;")
