"""Move brute-force lockout state out of the three per-role account tables and into a
single email-keyed login_lockouts table (app/services/login_lockout.py).

Two reasons the per-role columns had to go rather than being kept alongside:

1. An email with no account behind it now has to be locked out exactly like a real one,
   otherwise "locked, try again in N minutes" tells an attacker which emails are
   registered. There is no account row to hang that state on, so the store has to be
   keyed on the submitted email.
2. Three copies of the counter meant three copies of the escalation logic, which would
   drift. One table, one ladder, one implementation.

Nothing is migrated forward: the old columns hold ephemeral security counters (a partial
failure count and a short-lived lock), not user data, so starting everyone from a clean
slate is both acceptable and the friendlier outcome for anyone mid-lockout.

revision: 0019_login_lockouts
"""
from alembic import op

revision = "0019_login_lockouts"
down_revision = "0018_rate_limit_events"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS login_lockouts (
        email TEXT PRIMARY KEY,
        failed_attempts INTEGER NOT NULL DEFAULT 0,
        lockout_count INTEGER NOT NULL DEFAULT 0,
        locked_until TIMESTAMP,
        last_failed_at TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

    ALTER TABLE users DROP COLUMN IF EXISTS failed_login_attempts;
    ALTER TABLE users DROP COLUMN IF EXISTS locked_until;
    """)

    # doctor_accounts/admin_accounts are created by their own ensure_*_schema helpers,
    # which may not have run yet on a fresh database — guard so this migration is safe
    # in either order.
    op.execute("""
    DO $do$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'doctor_accounts') THEN
            ALTER TABLE doctor_accounts DROP COLUMN IF EXISTS failed_login_attempts;
            ALTER TABLE doctor_accounts DROP COLUMN IF EXISTS locked_until;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'admin_accounts') THEN
            ALTER TABLE admin_accounts DROP COLUMN IF EXISTS failed_login_attempts;
            ALTER TABLE admin_accounts DROP COLUMN IF EXISTS locked_until;
        END IF;
    END
    $do$;
    """)


def downgrade():
    op.execute("""
    ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;

    DO $do$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'doctor_accounts') THEN
            ALTER TABLE doctor_accounts ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE doctor_accounts ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'admin_accounts') THEN
            ALTER TABLE admin_accounts ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE admin_accounts ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;
        END IF;
    END
    $do$;

    DROP TABLE IF EXISTS login_lockouts;
    """)
