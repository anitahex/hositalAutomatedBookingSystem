"""Add patient_profiles.mobile_number_normalized (nullable, no default).

Instant, no-lock DDL — this migration only adds the column. Backfilling existing rows
(scripts/backfill_mobile_number_normalized.py) and the duplicate-check report
(scripts/report_duplicate_normalized_mobiles.py) are deliberately separate,
individually-run steps, not part of this migration — see 0013 for the unique index
that depends on both having been run and reviewed first.
"""
from alembic import op

revision = "0012_add_mobile_number_normalized_column"
down_revision = "0011_password_changed_at"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS mobile_number_normalized TEXT;")


def downgrade():
    op.execute("ALTER TABLE patient_profiles DROP COLUMN IF EXISTS mobile_number_normalized;")
