"""Add email verification gate for patient signup.

users.email_verified defaults to TRUE so every pre-existing account is grandfathered in
and never gets locked out retroactively by this migration — only new signups explicitly
insert email_verified = FALSE at the application layer (see
app/services/users.py::create_user_with_profile). email_verification_codes holds a
short-lived, single-active-per-user, hashed 6-digit code (never the raw code) used to
confirm ownership of the submitted email before the account becomes usable.
"""
from alembic import op

revision = "0009_patient_email_verification"
down_revision = "0008_registry_cascade_cleanup"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE;

    CREATE TABLE IF NOT EXISTS email_verification_codes (
        verification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
        code_hash TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)


def downgrade():
    op.execute("""
    DROP TABLE IF EXISTS email_verification_codes;
    ALTER TABLE users DROP COLUMN IF EXISTS email_verified;
    """)
