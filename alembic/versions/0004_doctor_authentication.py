"""Add isolated doctor authentication and audit tables."""

from alembic import op

revision = "0004_doctor_authentication"
down_revision = "0003_add_preferred_language"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE doctor_accounts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            doctor_id UUID NOT NULL UNIQUE REFERENCES doctors(doctor_id) ON DELETE CASCADE,
            email TEXT NOT NULL UNIQUE, hashed_password TEXT, totp_secret TEXT,
            mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            recovery_codes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            invite_token_hash TEXT, invite_expires_at TIMESTAMP, invite_consumed_at TIMESTAMP,
            failed_login_attempts INTEGER NOT NULL DEFAULT 0, locked_until TIMESTAMP,
            last_login_at TIMESTAMP, last_totp_step BIGINT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(), updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        CREATE TABLE doctor_auth_audit_log (
            audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            doctor_id UUID REFERENCES doctors(doctor_id) ON DELETE SET NULL,
            attempted_email TEXT, action_type TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_doctor_auth_audit_doctor_created
            ON doctor_auth_audit_log(doctor_id, created_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_doctor_auth_audit_doctor_created;")
    op.execute("DROP TABLE IF EXISTS doctor_auth_audit_log;")
    op.execute("DROP TABLE IF EXISTS doctor_accounts;")
