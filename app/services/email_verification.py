"""Patient signup email verification — a 6-digit code, entered inline in the signup UI,
that must be confirmed before an account is usable. Mirrors the doctor-invite flow's
security conventions (only a hash of the secret is ever stored, single active
code/token per account) and reuses its email transport (app/services/email.py,
DOCTOR_AUTH_EMAIL_FROM) rather than adding a second, parallel set of email config.
"""
import hashlib
import hmac
import logging
import os
import secrets
import threading
from datetime import timedelta

from app.db.connection import connect_db
from app.services.email import send_email
from app.services.users import ensure_user_schema

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5

logger = logging.getLogger(__name__)


def ensure_email_verification_schema(conn) -> None:
    # users.email_verified is owned by app/services/users.py::ensure_user_schema (the
    # existing owner of the users table's schema, same as failed_login_attempts/
    # locked_until) — call it here too so this module's functions work standalone,
    # without redeclaring that column's DDL a second time.
    ensure_user_schema(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS email_verification_codes (
                verification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
                code_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )


def _code_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_and_send_code(user_id: str, email: str) -> None:
    code = _generate_code()
    with connect_db() as conn:
        try:
            ensure_email_verification_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO email_verification_codes (user_id, code_hash, expires_at, attempts, created_at)
                    VALUES (%s, %s, NOW() + INTERVAL '10 minutes', 0, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        code_hash = EXCLUDED.code_hash,
                        expires_at = EXCLUDED.expires_at,
                        attempts = 0,
                        created_at = EXCLUDED.created_at;
                    """,
                    (user_id, _code_hash(code)),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # Fire-and-forget — the code is already durably persisted above; the caller
    # (signup / resend-verification) shouldn't block on the real SMTP round-trip to
    # move the UI to the next screen.
    threading.Thread(target=_send_verification_email_safe, args=(email, code), daemon=True).start()


def _send_verification_email_safe(email: str, code: str) -> None:
    # Runs on a daemon thread with no caller left to propagate to, so a failure here
    # would otherwise only surface as Python's default unhandled-thread-exception
    # traceback on stderr — easy to miss and hard to tell apart from "nothing ran at
    # all". Logging explicitly, with the email's domain (not the full address) as
    # context, makes success/failure/never-ran distinguishable in `docker logs`.
    try:
        _send_verification_email(email, code)
    except Exception:
        logger.exception("Failed to send patient verification email to domain %s", email.rsplit("@", 1)[-1])
    else:
        logger.info("Sent patient verification email to domain %s", email.rsplit("@", 1)[-1])


def _send_verification_email(email: str, code: str) -> None:
    # Deliberately a SEPARATE flag from DOCTOR_AUTH_EMAIL_NO_SEND: the two flows share
    # one transport (app/services/email.py) but need independent on/off switches —
    # e.g. doctor invites still log-only for now while patient verification sends
    # real email.
    if os.getenv("PATIENT_AUTH_EMAIL_NO_SEND", "false").lower() == "true":
        # Same dev/test fallback convention as doctor_auth.py's _send_invite_email —
        # gated behind this flag so this only ever fires when email delivery is
        # deliberately disabled, never in a live-email configuration.
        print(f"[patient-verify:no-send] code for {email}: {code}", flush=True)
        return

    sender = os.getenv("DOCTOR_AUTH_EMAIL_FROM", "").strip()
    if not sender:
        raise RuntimeError("DOCTOR_AUTH_EMAIL_FROM is required when patient email delivery is enabled.")

    send_email(
        sender=sender,
        to=email,
        subject="Verify your hospital account email",
        body=f"Your verification code is {code}. It expires in 10 minutes.",
    )


def verify_code(user_id: str, submitted_code: str) -> bool:
    with connect_db() as conn:
        try:
            ensure_email_verification_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT code_hash, expires_at, attempts
                    FROM email_verification_codes
                    WHERE user_id = %s
                    FOR UPDATE;
                    """,
                    (user_id,),
                )
                row = cur.fetchone()

                if not row:
                    conn.commit()
                    return False

                code_hash, expires_at, attempts = row

                if attempts >= MAX_ATTEMPTS:
                    conn.commit()
                    return False

                cur.execute(
                    "SELECT NOW() > %s;",
                    (expires_at,),
                )
                expired = cur.fetchone()[0]
                if expired:
                    conn.commit()
                    return False

                if not hmac.compare_digest(code_hash, _code_hash(str(submitted_code))):
                    cur.execute(
                        "UPDATE email_verification_codes SET attempts = attempts + 1 WHERE user_id = %s;",
                        (user_id,),
                    )
                    conn.commit()
                    return False

                cur.execute("UPDATE users SET email_verified = TRUE WHERE user_id = %s;", (user_id,))
                cur.execute("DELETE FROM email_verification_codes WHERE user_id = %s;", (user_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
