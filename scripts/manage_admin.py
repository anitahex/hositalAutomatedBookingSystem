from __future__ import annotations

import argparse
import sys
from getpass import getpass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.connection import connect_db
from app.services.admin_auth import ensure_admin_schema, get_admin_account_by_email
from app.services.passwords import hash_password


def _prompt_email(value: str | None) -> str:
    email = (value or input("Admin email: ")).strip().lower()
    if not email:
        raise SystemExit("Admin email is required.")
    return email


def _prompt_name(value: str | None) -> str:
    name = (value or input("Admin name: ")).strip()
    if not name:
        raise SystemExit("Admin name is required.")
    return name


def _prompt_password(value: str | None) -> str:
    password = value or getpass("Admin password: ")
    if not password:
        raise SystemExit("Admin password is required.")
    return password


def create_or_update_admin(*, email: str, name: str, password: str, is_active: bool = True) -> None:
    with connect_db() as conn:
        ensure_admin_schema(conn)
        password_hash = hash_password(password)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO admin_accounts (email, password_hash, name, is_active)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email)
                DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    name = EXCLUDED.name,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW();
                """,
                (email, password_hash, name, is_active),
            )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update an admin account in the database.")
    parser.add_argument("--email", help="Admin email address.")
    parser.add_argument("--name", help="Admin display name.")
    parser.add_argument("--password", help="Admin password. If omitted, you will be prompted.")
    parser.add_argument("--inactive", action="store_true", help="Store the account as inactive.")
    parser.add_argument("--show", action="store_true", help="Print the stored account after saving.")
    args = parser.parse_args()

    email = _prompt_email(args.email)
    name = _prompt_name(args.name)
    password = _prompt_password(args.password)

    create_or_update_admin(email=email, name=name, password=password, is_active=not args.inactive)
    print(f"Saved admin account for {email}.")

    if args.show:
        admin = get_admin_account_by_email(email)
        if admin:
            print(f"Admin ID: {admin.admin_id}")
            print(f"Active: {admin.is_active}")


if __name__ == "__main__":
    main()
