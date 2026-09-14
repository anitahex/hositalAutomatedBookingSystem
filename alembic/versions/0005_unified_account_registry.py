"""Add global account email registry and admin login protection."""
from alembic import op

revision = "0005_unified_account_registry"
down_revision = "0004_doctor_authentication"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
    -- admin_accounts was previously only ever created lazily by
    -- app.services.admin_auth.ensure_admin_schema() at runtime, never by a tracked
    -- migration — so a fresh database (migrations only, no prior app boot) reached
    -- this point with no admin_accounts table at all and crashed. IF NOT EXISTS
    -- makes this a no-op on any deployment where the table already exists.
    CREATE TABLE IF NOT EXISTS admin_accounts (
      admin_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      name TEXT NOT NULL,
      is_active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMP NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    CREATE TABLE account_email_registry (
      email TEXT PRIMARY KEY, account_type TEXT NOT NULL CHECK (account_type IN ('patient','doctor','admin')),
      account_id UUID NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    ALTER TABLE admin_accounts ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE admin_accounts ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;
    CREATE TABLE unified_auth_audit_log (
      audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email TEXT NOT NULL,
      account_type TEXT, action_type TEXT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    INSERT INTO account_email_registry (email, account_type, account_id)
      SELECT lower(email), 'patient', user_id FROM users;
    INSERT INTO account_email_registry (email, account_type, account_id)
      SELECT lower(email), 'doctor', id FROM doctor_accounts;
    INSERT INTO account_email_registry (email, account_type, account_id)
      SELECT lower(email), 'admin', admin_id FROM admin_accounts;
    """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS unified_auth_audit_log;")
    op.execute("DROP TABLE IF EXISTS account_email_registry;")
    op.execute("ALTER TABLE admin_accounts DROP COLUMN IF EXISTS locked_until;")
    op.execute("ALTER TABLE admin_accounts DROP COLUMN IF EXISTS failed_login_attempts;")
