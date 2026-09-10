"""Add patient login lockout columns and the token revocation table."""
from alembic import op

revision = "0006_patient_lockout_and_token_revocation"
down_revision = "0005_unified_account_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;

        CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti TEXT PRIMARY KEY,
            revoked_at TIMESTAMP NOT NULL DEFAULT NOW(),
            expires_at_epoch BIGINT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expiry ON revoked_tokens(expires_at_epoch);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revoked_tokens;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS locked_until;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS failed_login_attempts;")
