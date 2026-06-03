import hashlib
import hmac
import os
import re
from uuid import UUID

from app.db.connection import connect_db


PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
)


def ensure_user_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS users (
                user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS patient_profiles (
                user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                age INTEGER NOT NULL CHECK (age > 0 AND age < 130),
                mobile_number TEXT NOT NULL,
                address TEXT NOT NULL,
                email TEXT NOT NULL,
                blood_group TEXT NOT NULL,
                health_issues TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )


def validate_password(password: str):
    if not PASSWORD_PATTERN.match(password):
        raise ValueError(
            "Password must be at least 8 characters and include uppercase, lowercase, "
            "number, and special character."
        )


def _normalise_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = stored_hash.split("$", 2)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    expected = _hash_password(password, bytes.fromhex(salt_hex)).split("$", 2)[2]
    return hmac.compare_digest(expected, digest_hex)


def create_user_with_profile(
    *,
    email: str,
    password: str,
    confirm_password: str,
    name: str,
    age: int,
    mobile_number: str,
    address: str,
    profile_email: str,
    blood_group: str,
    health_issues: str | None = None,
):
    email = _normalise_email(email)
    profile_email = _normalise_email(profile_email)

    if password != confirm_password:
        raise ValueError("Password and confirmed password do not match.")

    validate_password(password)

    with connect_db() as conn:
        try:
            ensure_user_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash)
                    VALUES (%s, %s)
                    RETURNING user_id;
                    """,
                    (email, _hash_password(password)),
                )
                user_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO patient_profiles (
                        user_id,
                        name,
                        age,
                        mobile_number,
                        address,
                        email,
                        blood_group,
                        health_issues
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        user_id,
                        name.strip(),
                        age,
                        mobile_number.strip(),
                        address.strip(),
                        profile_email,
                        blood_group.strip(),
                        (health_issues or "").strip() or None,
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return get_user_profile(str(user_id))


def authenticate_user(email: str, password: str):
    email = _normalise_email(email)
    with connect_db() as conn:
        ensure_user_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.user_id, u.password_hash
                FROM users u
                WHERE u.email = %s;
                """,
                (email,),
            )
            row = cur.fetchone()

    if not row:
        return None

    user_id, password_hash = row
    if not _verify_password(password, password_hash):
        return None

    return get_user_profile(str(user_id))


def get_user_profile(user_id: str):
    try:
        UUID(str(user_id))
    except ValueError:
        return None

    with connect_db() as conn:
        ensure_user_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    u.user_id,
                    u.email,
                    p.name,
                    p.age,
                    p.mobile_number,
                    p.address,
                    p.email,
                    p.blood_group,
                    p.health_issues
                FROM users u
                JOIN patient_profiles p ON p.user_id = u.user_id
                WHERE u.user_id = %s;
                """,
                (user_id,),
            )
            row = cur.fetchone()

    if not row:
        return None

    (
        profile_user_id,
        login_email,
        name,
        age,
        mobile_number,
        address,
        profile_email,
        blood_group,
        health_issues,
    ) = row

    return {
        "patient_id": str(profile_user_id),
        "login_email": login_email,
        "name": name,
        "age": age,
        "mobile_number": mobile_number,
        "address": address,
        "email": profile_email,
        "blood_group": blood_group,
        "health_issues": health_issues,
    }
