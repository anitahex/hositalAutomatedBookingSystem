import re
from datetime import datetime, timedelta
from uuid import UUID

from app.db.connection import connect_db
from app.services.passwords import hash_password, verify_password
from app.services.account_registry import ensure_registry_schema, reserve_email
from app.services.login_lockout import (
    AccountLockedError,
    check_lockout,
    clear_lockout,
    ensure_lockout_schema,
    record_failure,
)


PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
)


def normalize_mobile_number(value: str | None) -> str:
    """Return a stable comparison form for E.164-like phone numbers."""
    raw = str(value or "").strip()
    if raw.lower().startswith("whatsapp:"):
        raw = raw.split(":", 1)[1]
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+"):
        return f"+{digits}"
    if digits.startswith("00"):
        return f"+{digits[2:]}"
    return digits


def normalize_mobile_number_india(value: str | None) -> str | None:
    """Strict India-specific normalization for patient_profiles.mobile_number_normalized.

    Deliberately separate from normalize_mobile_number above (used for WhatsApp-sender
    matching, with more lenient semantics other code already depends on — not changed).
    Returns None — never guessed — for anything outside these three exact shapes:
      - 10 digits                   -> +91<digits>
      - leading 0 + 11 digits total -> +91<digits without the leading 0>
      - 12 digits starting with 91  -> +<digits>
    """
    raw = str(value or "").strip()
    if raw.lower().startswith("whatsapp:"):
        raw = raw.split(":", 1)[1]
    digits = re.sub(r"\D", "", raw)

    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"+91{digits[1:]}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    return None


def ensure_user_schema(conn):
    ensure_lockout_schema(conn)
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
            -- DEFAULT TRUE so pre-existing accounts are grandfathered in and never
            -- retroactively locked out; new signups explicitly insert FALSE (see
            -- create_user_with_profile) and only flip to TRUE once the emailed code
            -- is confirmed (app/services/email_verification.py).
            ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE;
            -- Nullable, no default: NULL means "never changed" and current_user treats
            -- that as no invalidation, so existing accounts are never force-logged-out.
            ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP;
            -- Owned in detail by app/services/patient_mfa.py::ensure_mfa_schema;
            -- declared here too (same redundant-safety-net convention as every other
            -- ensure_*_schema in this codebase) so get_user_profile's SELECT below is
            -- safe even if patient_mfa.py's own ensure call hasn't run yet on this
            -- connection.
            ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret_encrypted TEXT;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS last_totp_step BIGINT;

            CREATE TABLE IF NOT EXISTS patient_profiles (
                user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                age INTEGER NOT NULL CHECK (age > 0 AND age < 130),
                mobile_number TEXT NOT NULL,
                address TEXT NOT NULL,
                email TEXT NOT NULL,
                blood_group TEXT NOT NULL,
                health_issues TEXT,
                preferred_language TEXT NOT NULL DEFAULT 'en',
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS preferred_language TEXT NOT NULL DEFAULT 'en';
            -- Nullable, no default: populated going forward at signup/profile-update
            -- time (normalize_mobile_number_india), backfilled separately for
            -- existing rows via scripts/backfill_mobile_number_normalized.py.
            ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS mobile_number_normalized TEXT;
            -- Split out of name for the editable profile form (migration 0020); name
            -- itself is kept in sync as the combined value for every other reader.
            ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS first_name TEXT;
            ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS last_name TEXT;
            ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS gender TEXT;
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
    preferred_language: str = "en",
):
    email = _normalise_email(email)
    profile_email = _normalise_email(profile_email)

    if password != confirm_password:
        raise ValueError("Password and confirmed password do not match.")

    validate_password(password)

    with connect_db() as conn:
        try:
            ensure_user_schema(conn)
            ensure_registry_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash, email_verified)
                    VALUES (%s, %s, FALSE)
                    RETURNING user_id;
                    """,
                    (email, hash_password(password)),
                )
                user_id = cur.fetchone()[0]
                reserve_email(cur, email, "patient", user_id)
                cur.execute(
                    """
                    INSERT INTO patient_profiles (
                        user_id,
                        name,
                        age,
                        mobile_number,
                        mobile_number_normalized,
                        address,
                        email,
                        blood_group,
                        health_issues,
                        preferred_language
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        user_id,
                        name.strip(),
                        age,
                        mobile_number.strip(),
                        normalize_mobile_number_india(mobile_number),
                        address.strip(),
                        profile_email,
                        blood_group.strip(),
                        (health_issues or "").strip() or None,
                        preferred_language,
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return get_user_profile(str(user_id))


VALID_GENDERS = ("male", "female", "other", "prefer_not_to_say")


def update_patient_profile(
    patient_id: str,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    health_issues: str | None = None,
    address: str | None = None,
    preferred_language: str | None = None,
):
    """Update editable profile fields. Only supplied (non-None) fields are changed.

    Email and mobile number are deliberately absent: both identify the account (email is
    the login and the address every verification/OTP goes to, mobile is the WhatsApp
    sender key and is uniquely indexed), so they are fixed here and would need a
    verified change flow of their own rather than a silent profile edit.
    """
    updates: list[str] = []
    params: list = []

    if first_name is not None:
        updates.append("first_name = %s")
        params.append(first_name.strip() or None)
    if last_name is not None:
        updates.append("last_name = %s")
        params.append(last_name.strip() or None)
    if age is not None:
        if not 0 < int(age) < 130:
            raise ValueError("Age must be between 1 and 129.")
        updates.append("age = %s")
        params.append(int(age))
    if gender is not None:
        normalized_gender = gender.strip().lower().replace(" ", "_") or None
        if normalized_gender and normalized_gender not in VALID_GENDERS:
            raise ValueError("Gender must be one of: " + ", ".join(VALID_GENDERS))
        updates.append("gender = %s")
        params.append(normalized_gender)
    if health_issues is not None:
        updates.append("health_issues = %s")
        params.append((health_issues.strip() or None))
    if address is not None:
        updates.append("address = %s")
        params.append(address.strip() or None)
    if preferred_language is not None:
        updates.append("preferred_language = %s")
        params.append(preferred_language)

    if not updates:
        return get_user_profile(patient_id)

    # name stays the combined value so the chat greeting, admin cards and doctor views
    # keep working off the single column they already read. COALESCE against the stored
    # halves so updating only one of them still rebuilds the whole thing correctly.
    if first_name is not None or last_name is not None:
        updates.append(
            "name = NULLIF(trim(concat_ws(' ', "
            "COALESCE(%s, first_name), COALESCE(%s, last_name))), '')"
        )
        params.append(first_name.strip() if first_name is not None else None)
        params.append(last_name.strip() if last_name is not None else None)

    params.append(patient_id)
    with connect_db() as conn:
        ensure_user_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE patient_profiles SET {', '.join(updates)} "
                "WHERE user_id = %s;",
                params,
            )
        conn.commit()

    return get_user_profile(patient_id)


def authenticate_user(email: str, password: str):
    """Verify patient credentials behind the shared escalating lockout
    (app/services/login_lockout.py).

    Returns None for an unknown email or a wrong password — never a distinguishing
    error. An account that is currently locked out raises AccountLockedError instead,
    carrying the seconds remaining so the caller can say how long rather than claiming
    the password was wrong; note that unknown emails accumulate failures and lock on
    exactly the same schedule, so that distinction still leaks nothing.
    """
    email = _normalise_email(email)
    with connect_db() as conn:
        try:
            ensure_user_schema(conn)
            ensure_lockout_schema(conn)
            with conn.cursor() as cur:
                check_lockout(cur, email)

                cur.execute(
                    "SELECT user_id, password_hash FROM users WHERE email = %s FOR UPDATE;",
                    (email,),
                )
                row = cur.fetchone()

                if not row or not verify_password(password, row[1]):
                    record_failure(cur, email)
                    conn.commit()
                    return None

                user_id = row[0]
                clear_lockout(cur, email)
            conn.commit()
        except AccountLockedError:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise

    return get_user_profile(str(user_id))


def verify_current_password(user_id: str, current_password: str) -> bool:
    """Identity check only — does not change anything. Step 1 of the OTP-gated
    change-password flow (app/services/password_reset.py handles step 2, the actual
    update, once the OTP is confirmed)."""
    with connect_db() as conn:
        ensure_user_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM users WHERE user_id = %s;", (user_id,))
            row = cur.fetchone()
    return bool(row) and verify_password(current_password, row[0])


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
                    p.first_name,
                    p.last_name,
                    p.gender,
                    p.age,
                    p.mobile_number,
                    p.address,
                    p.email,
                    p.blood_group,
                    p.health_issues,
                    p.preferred_language,
                    u.email_verified,
                    u.password_changed_at,
                    u.mfa_enabled
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
        first_name,
        last_name,
        gender,
        age,
        mobile_number,
        address,
        profile_email,
        blood_group,
        health_issues,
        preferred_language,
        email_verified,
        password_changed_at,
        mfa_enabled,
    ) = row

    return {
        "patient_id": str(profile_user_id),
        "login_email": login_email,
        "name": name,
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender,
        "age": age,
        "mobile_number": mobile_number,
        "address": address,
        "email": profile_email,
        "blood_group": blood_group,
        "health_issues": health_issues,
        "preferred_language": preferred_language or "en",
        "email_verified": bool(email_verified),
        "password_changed_at": password_changed_at,
        "mfa_enabled": bool(mfa_enabled),
    }


def get_user_profile_by_mobile(mobile_number: str):
    """Find a patient by the phone number supplied by Twilio."""
    normalized = normalize_mobile_number(mobile_number)
    if not normalized:
        return None

    with connect_db() as conn:
        ensure_user_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id
                FROM patient_profiles
                WHERE (
                    regexp_replace(mobile_number, '[^0-9]', '', 'g') =
                    regexp_replace(%s, '[^0-9]', '', 'g')
                    OR RIGHT(regexp_replace(mobile_number, '[^0-9]', '', 'g'), 10) =
                       RIGHT(regexp_replace(%s, '[^0-9]', '', 'g'), 10)
                )
                LIMIT 1;
                """,
                (normalized, normalized),
            )
            row = cur.fetchone()
    return get_user_profile(str(row[0])) if row else None
