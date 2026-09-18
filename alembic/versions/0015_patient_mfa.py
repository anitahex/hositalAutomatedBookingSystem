"""Add opt-in TOTP MFA for patients: users.mfa_enabled/mfa_secret_encrypted +
mfa_backup_codes. Mirrors doctor_accounts' MFA columns/doctor_auth_audit_log-adjacent
shape, but patients opt in themselves rather than being invite-gated.
"""
from alembic import op

revision = "0015_patient_mfa"
down_revision = "0014_otp_verifications"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret_encrypted TEXT;

    CREATE TABLE IF NOT EXISTS mfa_backup_codes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        code_hash TEXT NOT NULL,
        used_at TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_mfa_backup_codes_user ON mfa_backup_codes(user_id);
    """)


def downgrade():
    op.execute("""
    DROP TABLE IF EXISTS mfa_backup_codes;
    ALTER TABLE users DROP COLUMN IF EXISTS mfa_secret_encrypted;
    ALTER TABLE users DROP COLUMN IF EXISTS mfa_enabled;
    """)
