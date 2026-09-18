"""Add refresh_tokens for patient and admin sessions.

Only the SHA-256 hash of a refresh token is ever stored, mirroring the doctor-invite
token pattern in app/services/doctor_auth.py (_token_hash). Rotation is single-use:
app/services/refresh_tokens.py::rotate_refresh_token marks the presented row
revoked_at=NOW() in the same transaction that issues its replacement, so a reused
(already-rotated) token can never succeed twice. Doctor sessions are deliberately not
covered here (see the plan) — only patient/admin issuance sites call into this.
"""
from alembic import op

revision = "0010_refresh_tokens"
down_revision = "0009_patient_email_verification"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    CREATE TABLE IF NOT EXISTS refresh_tokens (
        token_hash TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        role TEXT NOT NULL,
        email TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        revoked_at TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS refresh_tokens;")
