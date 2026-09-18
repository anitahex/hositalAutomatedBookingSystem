"""Add a unique index on patient_profiles.mobile_number_normalized (partial, concurrent).

Only run this after scripts/backfill_mobile_number_normalized.py and
scripts/report_duplicate_normalized_mobiles.py have both been run and the duplicate
report is confirmed clean — CREATE UNIQUE INDEX fails outright (does not silently
succeed) if any duplicate normalized values remain.

CREATE INDEX CONCURRENTLY cannot run inside a transaction block. Alembic's documented
mechanism for this is `op.get_context().autocommit_block()`, used below — without it,
Alembic's default per-migration transaction wrapper would make this statement fail.
"""
from alembic import op

revision = "0013_add_mobile_normalized_unique_index"
down_revision = "0012_add_mobile_number_normalized_column"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_patient_mobile_normalized
            ON patient_profiles (mobile_number_normalized)
            WHERE mobile_number_normalized IS NOT NULL;
            """
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_patient_mobile_normalized;")
