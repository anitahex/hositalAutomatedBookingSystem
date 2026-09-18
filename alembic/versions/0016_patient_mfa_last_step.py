"""Add users.last_totp_step for patient MFA replay protection.

0015 already applied without this column by the time it was recognized as needed —
mirrors doctor_accounts.last_totp_step, tracked so the same TOTP code can never be
replayed even within its own valid clock-skew window (app/services/totp.py::verify_totp).
"""
from alembic import op

revision = "0016_patient_mfa_last_step"
down_revision = "0015_patient_mfa"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_totp_step BIGINT;")


def downgrade():
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS last_totp_step;")
