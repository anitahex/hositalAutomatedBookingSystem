from __future__ import annotations
from datetime import date, timedelta

from app.db.connection import connect_db
from app.services.passwords import hash_password, verify_password

_DUMMY = hash_password("not-a-real-password")

def ensure_registry_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS account_email_registry (email TEXT PRIMARY KEY, account_type TEXT NOT NULL CHECK (account_type IN ('patient','doctor','admin')), account_id UUID NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT NOW());
        CREATE TABLE IF NOT EXISTS unified_auth_audit_log (audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email TEXT NOT NULL, account_type TEXT, action_type TEXT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT NOW());""")
        # Deleting a users/doctor_accounts/admin_accounts row (manual SQL, a future
        # admin "delete account" feature, test cleanup) previously left its
        # account_email_registry row behind forever — there was no FK/cascade, and
        # reserve_email() only ever inserts — permanently blocking that email from
        # ever signing up again even though the account no longer exists. These
        # triggers make the registry self-cleaning for any deletion path. Guarded by
        # information_schema checks because this runs before each account table is
        # guaranteed to exist (e.g. during a patient signup, doctor_accounts may not
        # have been created yet) — it self-heals next time this runs after that table
        # shows up.
        cur.execute(_TRIGGER_FUNCTIONS_SQL)
        cur.execute(_TRIGGER_GUARDS_SQL)


_TRIGGER_FUNCTIONS_SQL = """
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
"""

_TRIGGER_GUARDS_SQL = """
DO $do$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        DROP TRIGGER IF EXISTS trg_account_email_registry_cleanup ON users;
        CREATE TRIGGER trg_account_email_registry_cleanup AFTER DELETE ON users
            FOR EACH ROW EXECUTE FUNCTION account_email_registry_cleanup_patient();
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'doctor_accounts') THEN
        DROP TRIGGER IF EXISTS trg_account_email_registry_cleanup ON doctor_accounts;
        CREATE TRIGGER trg_account_email_registry_cleanup AFTER DELETE ON doctor_accounts
            FOR EACH ROW EXECUTE FUNCTION account_email_registry_cleanup_doctor();
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'admin_accounts') THEN
        DROP TRIGGER IF EXISTS trg_account_email_registry_cleanup ON admin_accounts;
        CREATE TRIGGER trg_account_email_registry_cleanup AFTER DELETE ON admin_accounts
            FOR EACH ROW EXECUTE FUNCTION account_email_registry_cleanup_admin();
    END IF;
END
$do$;
"""

def reserve_email(cur, email: str, account_type: str, account_id) -> None:
    cur.execute("INSERT INTO account_email_registry (email, account_type, account_id) VALUES (%s,%s,%s) ON CONFLICT (email) DO NOTHING RETURNING email", (email.lower(), account_type, account_id))
    if not cur.fetchone():
        raise ValueError("An account with this email already exists.")

def lookup(cur, email: str):
    cur.execute("SELECT account_type, account_id FROM account_email_registry WHERE email=%s", (email.lower(),))
    return cur.fetchone()

def dummy_verify(password: str): verify_password(password, _DUMMY)

def audit(cur, email, account_type, action):
    cur.execute("INSERT INTO unified_auth_audit_log (email,account_type,action_type) VALUES (%s,%s,%s)", (email.lower(), account_type, action))


def list_unified_auth_audit_log(
    *,
    email: str | None = None,
    account_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Exposes unified_auth_audit_log (login success/failure across every role,
    populated since unified-login was built but never read by anything) — same
    filter/paginate/response shape as doctor_auth.py::list_doctor_auth_audit_log. This
    table has no metadata column, so every entry reports metadata: {}."""
    offset = (page - 1) * page_size
    clauses: list[str] = []
    params: list[object] = []
    if email:
        clauses.append("email = %s")
        params.append(email.strip().lower())
    if account_type:
        clauses.append("account_type = %s")
        params.append(account_type)
    if start_date:
        clauses.append("created_at >= %s")
        params.append(start_date)
    if end_date:
        clauses.append("created_at < %s")
        params.append(end_date + timedelta(days=1))
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with connect_db() as conn:
        ensure_registry_schema(conn)
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM unified_auth_audit_log {where_sql}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""SELECT audit_id, email, account_type, action_type, created_at
                    FROM unified_auth_audit_log {where_sql}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s""",
                (*params, page_size, offset),
            )
            rows = cur.fetchall()

    return {
        "entries": [
            {
                "audit_id": str(audit_id),
                "attempted_email": row_email,
                "action_type": f"{account_type}:{action_type}" if account_type else action_type,
                "metadata": {},
                "created_at": created_at.isoformat() if created_at else None,
            }
            for audit_id, row_email, account_type, action_type, created_at in rows
        ],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }
