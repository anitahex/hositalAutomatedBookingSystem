from __future__ import annotations

from dataclasses import dataclass
import os

from app.db.connection import connect_db
from app.services.passwords import hash_password, verify_password
from app.services.tokens import create_access_token
from app.services.account_registry import ensure_registry_schema, reserve_email
from app.services.login_lockout import check_lockout, clear_lockout, ensure_lockout_schema, record_failure


@dataclass(frozen=True)
class AdminAccount:
    admin_id: str
    email: str
    password_hash: str
    name: str
    is_active: bool


def ensure_admin_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS admin_accounts (
                admin_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )


def _normalise_email(email: str) -> str:
    return email.strip().lower()


def get_admin_account_by_email(email: str) -> AdminAccount | None:
    normalised_email = _normalise_email(email)
    with connect_db() as conn:
        ensure_admin_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT admin_id, email, password_hash, name, is_active
                FROM admin_accounts
                WHERE email = %s;
                """,
                (normalised_email,),
            )
            row = cur.fetchone()

    if not row:
        return None

    admin_id, db_email, password_hash, name, is_active = row
    return AdminAccount(
        admin_id=str(admin_id),
        email=str(db_email),
        password_hash=str(password_hash),
        name=str(name),
        is_active=bool(is_active),
    )


def authenticate_admin(email: str, password: str) -> dict | None:
    admin = get_admin_account_by_email(email)
    if not admin or not admin.is_active:
        return None

    if not verify_password(password, admin.password_hash):
        return None

    token = create_access_token(subject=admin.email, email=admin.email, role="admin")
    return {
        "role": "admin",
        "email": admin.email,
        "name": admin.name,
        "access_token": token,
        "token_type": "bearer",
    }


def authenticate_admin_with_lockout(email: str, password: str) -> dict | None:
    """Public-login variant; legacy admin login remains compatible."""
    from datetime import datetime
    email = _normalise_email(email)
    with connect_db() as conn:
        ensure_admin_schema(conn)
        with conn.cursor() as cur:
            ensure_lockout_schema(conn)
            check_lockout(cur, email)
            cur.execute("SELECT admin_id,email,password_hash,name,is_active FROM admin_accounts WHERE email=%s FOR UPDATE", (email,))
            row=cur.fetchone()
            if not row:
                record_failure(cur, email)
                return None
            admin_id, db_email, password_hash, name, active = row
            if not active or not verify_password(password, password_hash):
                record_failure(cur, email)
                return None
            clear_lockout(cur, email)
    token=create_access_token(subject=str(admin_id), email=db_email, role="admin")
    return {"role":"admin","email":db_email,"name":name,"access_token":token,"token_type":"bearer","account_id":str(admin_id)}


def bootstrap_admin_from_env() -> bool:
    """Create or update the configured admin account at application startup.

    This is deliberately opt-in so an old value left in a deployment environment
    cannot unexpectedly overwrite an admin password on every restart.
    """
    if os.getenv("ADMIN_BOOTSTRAP_ENABLED", "false").strip().lower() != "true":
        return False

    email = _normalise_email(os.getenv("ADMIN_EMAIL", ""))
    password = os.getenv("ADMIN_PASSWORD", "")
    name = os.getenv("ADMIN_NAME", "Administrator").strip() or "Administrator"
    if not email or not password:
        raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD are required when ADMIN_BOOTSTRAP_ENABLED=true.")

    with connect_db() as conn:
        ensure_admin_schema(conn)
        ensure_registry_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO admin_accounts (email, password_hash, name, is_active)
                VALUES (%s, %s, %s, TRUE)
                ON CONFLICT (email)
                DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    name = EXCLUDED.name,
                    is_active = TRUE,
                    updated_at = NOW();
                """,
                (email, hash_password(password), name),
            )
            cur.execute("SELECT admin_id FROM admin_accounts WHERE email=%s", (email,))
            admin_id = cur.fetchone()[0]
            cur.execute("SELECT 1 FROM account_email_registry WHERE email=%s", (email,))
            if not cur.fetchone(): reserve_email(cur, email, "admin", admin_id)
    return True
