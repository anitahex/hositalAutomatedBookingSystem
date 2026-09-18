"""Add otp_verifications for forgot/reset-password OTPs.

One active OTP per (email, purpose) — a resend overwrites it (same ON CONFLICT upsert
shape as email_verification_codes). Only the SHA-256 hash of the OTP is ever stored.
"""
from alembic import op

revision = "0014_otp_verifications"
down_revision = "0013_add_mobile_normalized_unique_index"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    CREATE TABLE IF NOT EXISTS otp_verifications (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email TEXT NOT NULL,
        purpose TEXT NOT NULL,
        otp_hash TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 5,
        consumed_at TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        UNIQUE (email, purpose)
    );
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS otp_verifications;")
