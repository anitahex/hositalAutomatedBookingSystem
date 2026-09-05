from __future__ import annotations
from app.services.passwords import hash_password, verify_password

_DUMMY = hash_password("not-a-real-password")

def ensure_registry_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS account_email_registry (email TEXT PRIMARY KEY, account_type TEXT NOT NULL CHECK (account_type IN ('patient','doctor','admin')), account_id UUID NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT NOW());
        CREATE TABLE IF NOT EXISTS unified_auth_audit_log (audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email TEXT NOT NULL, account_type TEXT, action_type TEXT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT NOW());""")

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
