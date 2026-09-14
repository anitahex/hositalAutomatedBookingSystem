"""Make account_email_registry self-cleaning and purge existing orphaned rows.

account_email_registry.account_id has no FK/cascade back to users, doctor_accounts,
or admin_accounts, and reserve_email() only ever inserts — so a deleted account
(manual SQL, a DB reset that skipped this table, test cleanup) leaves its email
reserved forever, permanently blocking that email from ever signing up again even
though the underlying account no longer exists. This adds AFTER DELETE triggers on
all three account tables so the registry cleans itself up going forward, and
one-time deletes rows that are already orphaned.
"""
from alembic import op

revision = "0008_registry_cascade_cleanup"
down_revision = "0007_consult_and_soap_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    DELETE FROM account_email_registry r
    WHERE (r.account_type = 'patient' AND NOT EXISTS (SELECT 1 FROM users u WHERE u.user_id = r.account_id))
       OR (r.account_type = 'doctor' AND NOT EXISTS (SELECT 1 FROM doctor_accounts d WHERE d.id = r.account_id))
       OR (r.account_type = 'admin' AND NOT EXISTS (SELECT 1 FROM admin_accounts a WHERE a.admin_id = r.account_id));

    CREATE OR REPLACE FUNCTION account_email_registry_cleanup_patient() RETURNS trigger AS $$
    BEGIN
        DELETE FROM account_email_registry WHERE account_type = 'patient' AND account_id = OLD.user_id;
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;

    CREATE OR REPLACE FUNCTION account_email_registry_cleanup_doctor() RETURNS trigger AS $$
    BEGIN
        DELETE FROM account_email_registry WHERE account_type = 'doctor' AND account_id = OLD.id;
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;

    CREATE OR REPLACE FUNCTION account_email_registry_cleanup_admin() RETURNS trigger AS $$
    BEGIN
        DELETE FROM account_email_registry WHERE account_type = 'admin' AND account_id = OLD.admin_id;
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trg_account_email_registry_cleanup ON users;
    CREATE TRIGGER trg_account_email_registry_cleanup AFTER DELETE ON users
        FOR EACH ROW EXECUTE FUNCTION account_email_registry_cleanup_patient();

    DROP TRIGGER IF EXISTS trg_account_email_registry_cleanup ON doctor_accounts;
    CREATE TRIGGER trg_account_email_registry_cleanup AFTER DELETE ON doctor_accounts
        FOR EACH ROW EXECUTE FUNCTION account_email_registry_cleanup_doctor();

    DROP TRIGGER IF EXISTS trg_account_email_registry_cleanup ON admin_accounts;
    CREATE TRIGGER trg_account_email_registry_cleanup AFTER DELETE ON admin_accounts
        FOR EACH ROW EXECUTE FUNCTION account_email_registry_cleanup_admin();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_account_email_registry_cleanup ON users;")
    op.execute("DROP TRIGGER IF EXISTS trg_account_email_registry_cleanup ON doctor_accounts;")
    op.execute("DROP TRIGGER IF EXISTS trg_account_email_registry_cleanup ON admin_accounts;")
    op.execute("DROP FUNCTION IF EXISTS account_email_registry_cleanup_patient();")
    op.execute("DROP FUNCTION IF EXISTS account_email_registry_cleanup_doctor();")
    op.execute("DROP FUNCTION IF EXISTS account_email_registry_cleanup_admin();")
    # Orphan cleanup is not reversible.
