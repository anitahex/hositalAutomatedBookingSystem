"""Add users.password_changed_at for session invalidation on password change.

Nullable, no default, no backfill: every pre-existing account stays NULL, which
current_user (app/api/dependencies.py) treats as "never invalidated" — this migration
must never force-log-out an existing account. Only a real password change (change-
password, reset-password) sets it going forward.
"""
from alembic import op

revision = "0011_password_changed_at"
down_revision = "0010_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP;")


def downgrade():
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS password_changed_at;")
