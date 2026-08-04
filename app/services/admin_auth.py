from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from app.db.connection import connect_db
from app.services.passwords import hash_password, verify_password
from app.services.tokens import create_access_token

logger = logging.getLogger(__name__)


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


def ensure_bootstrap_admin() -> None:
    """
    Create the first admin account from ADMIN_EMAIL/ADMIN_PASSWORD/ADMIN_NAME
    env vars, but ONLY if admin_accounts is completely empty. Never touches an
    existing account - a redeploy with the same .env must not silently reset
    a password that's since been changed through the app.
    """
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    name = os.getenv("ADMIN_NAME", "Admin").strip() or "Admin"

    if not email or not password:
        return

    with connect_db() as conn:
        ensure_admin_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM admin_accounts;")
            (existing_count,) = cur.fetchone()

            if existing_count > 0:
                logger.info("startup: admin bootstrap skipped (%d admin account(s) already exist)", existing_count)
                return

            cur.execute(
                """
                INSERT INTO admin_accounts (email, password_hash, name, is_active)
                VALUES (%s, %s, %s, TRUE);
                """,
                (email, hash_password(password), name),
            )
        conn.commit()
    logger.info("startup: bootstrapped first admin account for %s", email)


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
