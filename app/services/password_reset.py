"""Forgot/reset password for patients — email or mobile-number identifier.

Reuses this session's established patterns: hashed OTP storage
(app/services/email_verification.py's shape), the shared SMTP helper
(app/services/email.py), and password hashing/validation
(app/services/passwords.py, app/services/users.py::validate_password). Deliberately
NOT shared code with email_verification.py's tiny generate/hash helpers — different
table, different purpose, ~4 lines each ("three similar lines is better than a
premature abstraction").
"""
import hashlib
import hmac
import logging
import os
import secrets
import threading
from datetime import datetime, timedelta

from app.db.connection import connect_db
from app.services.email import send_email
from app.services.passwords import hash_password
from app.services.login_lockout import clear_lockout, ensure_lockout_schema
from app.services.patient_mfa import _audit_patient, ensure_patient_auth_audit_schema
from app.services.refresh_tokens import revoke_all_refresh_tokens
from app.services.users import normalize_mobile_number_india, validate_password

OTP_TTL_MINUTES = 4
RESEND_COOLDOWN_SECONDS = 240
PURPOSE_PASSWORD_RESET = "password_reset"
PURPOSE_CHANGE_PASSWORD = "change_password"

logger = logging.getLogger(__name__)


def ensure_password_reset_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS otp_verifications (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT NOT NULL,
                purpose TEXT NOT NULL,
                otp_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 5,
                consumed_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (email, purpose)
            );
            """
        )


def mask_email(email: str) -> str:
    """a**********3@gmail.com — first char + asterisks + last char of the local part,
    full domain visible."""
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked_local = local[0] + "*" * max(0, len(local) - 1) if local else ""
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _otp_hash(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


_OTP_EMAIL_TEXT = {
    PURPOSE_PASSWORD_RESET: (
        "Reset your hospital account password",
        "Your password reset code is {otp}. It expires in {minutes} minutes.",
    ),
    PURPOSE_CHANGE_PASSWORD: (
        "Confirm your password change",
        "Your password change confirmation code is {otp}. It expires in {minutes} minutes.",
    ),
}


def _send_otp_email(email: str, otp: str, purpose: str) -> None:
    if os.getenv("PATIENT_AUTH_EMAIL_NO_SEND", "false").lower() == "true":
        print(f"[password-reset:no-send] otp for {email}: {otp}", flush=True)
        return

    host = os.getenv("DOCTOR_AUTH_SMTP_HOST", "").strip()
    sender = os.getenv("DOCTOR_AUTH_EMAIL_FROM", "").strip()
    if not host or not sender:
        raise RuntimeError("SMTP host and sender are required when patient email delivery is enabled.")

    subject, body_template = _OTP_EMAIL_TEXT[purpose]
    send_email(
        host=host,
        port=int(os.getenv("DOCTOR_AUTH_SMTP_PORT", "587")),
        use_tls=os.getenv("DOCTOR_AUTH_SMTP_USE_TLS", "true").lower() == "true",
        username=os.getenv("DOCTOR_AUTH_SMTP_USERNAME"),
        password=os.getenv("DOCTOR_AUTH_SMTP_PASSWORD", ""),
        sender=sender,
        to=email,
        subject=subject,
        body=body_template.format(otp=otp, minutes=OTP_TTL_MINUTES),
    )


def _send_otp_email_safe(email: str, otp: str, purpose: str) -> None:
    # Same rationale as email_verification.py's _send_verification_email_safe: this
    # runs on a daemon thread with nothing left to propagate a failure to, so without
    # explicit logging a broken SMTP send is indistinguishable from one that never ran.
    try:
        _send_otp_email(email, otp, purpose)
    except Exception:
        logger.exception("Failed to send %s OTP email to domain %s", purpose, email.rsplit("@", 1)[-1])
    else:
        logger.info("Sent %s OTP email to domain %s", purpose, email.rsplit("@", 1)[-1])


def _send_security_notification(email: str, subject: str, body: str) -> None:
    """Best-effort — never raises. The password change has already committed by the
    time this is called; a bounced/failed notification must not undo it."""
    try:
        if os.getenv("PATIENT_AUTH_EMAIL_NO_SEND", "false").lower() == "true":
            print(f"[password-reset:no-send] {subject} -> {email}", flush=True)
            return
        host = os.getenv("DOCTOR_AUTH_SMTP_HOST", "").strip()
        sender = os.getenv("DOCTOR_AUTH_EMAIL_FROM", "").strip()
        if not host or not sender:
            return
        send_email(
            host=host,
            port=int(os.getenv("DOCTOR_AUTH_SMTP_PORT", "587")),
            use_tls=os.getenv("DOCTOR_AUTH_SMTP_USE_TLS", "true").lower() == "true",
            username=os.getenv("DOCTOR_AUTH_SMTP_USERNAME"),
            password=os.getenv("DOCTOR_AUTH_SMTP_PASSWORD", ""),
            sender=sender,
            to=email,
            subject=subject,
            body=body,
        )
    except Exception as exc:
        print(f"[password-reset:notify-failed] {subject} -> {email}: {exc}", flush=True)


def _issue_otp(email: str, purpose: str) -> None:
    # expires_at/created_at are computed in Python (not Postgres NOW()) specifically
    # so expiry/cooldown are testable with freezegun — a database round trip can't be
    # time-traveled by patching Python's clock.
    otp = _generate_otp()
    now = datetime.now()
    expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)
    with connect_db() as conn:
        try:
            ensure_password_reset_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO otp_verifications (email, purpose, otp_hash, expires_at, attempts, consumed_at, created_at)
                    VALUES (%s, %s, %s, %s, 0, NULL, %s)
                    ON CONFLICT (email, purpose) DO UPDATE SET
                        otp_hash = EXCLUDED.otp_hash,
                        expires_at = EXCLUDED.expires_at,
                        attempts = 0,
                        consumed_at = NULL,
                        created_at = EXCLUDED.created_at;
                    """,
                    (email, purpose, _otp_hash(otp), expires_at, now),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    # Fire-and-forget: the real SMTP round-trip (Gmail etc.) can take several
    # seconds, and the caller (a route the frontend is waiting on to move to the
    # next screen) has already durably persisted the OTP by this point — nothing
    # downstream needs to wait for the send itself to finish.
    threading.Thread(target=_send_otp_email_safe, args=(email, otp, purpose), daemon=True).start()


def _find_email_by_mobile(mobile_number: str) -> str | None:
    normalized = normalize_mobile_number_india(mobile_number)
    if normalized is None:
        return None
    with connect_db() as conn:
        ensure_password_reset_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.email FROM users u
                JOIN patient_profiles p ON p.user_id = u.user_id
                WHERE p.mobile_number_normalized = %s;
                """,
                (normalized,),
            )
            row = cur.fetchone()
    return row[0] if row else None


def start_forgot_password(identifier: str) -> dict:
    identifier = identifier.strip()
    if "@" in identifier:
        email = identifier.lower()
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE email = %s;", (email,))
                found = cur.fetchone() is not None
        if not found:
            return {"status": "not_found", "message": "No account found with this email."}
        _issue_otp(email, PURPOSE_PASSWORD_RESET)
        return {"status": "otp_sent", "email": mask_email(email)}

    real_email = _find_email_by_mobile(identifier)
    if not real_email:
        return {"status": "not_found", "message": "No account found with this mobile number."}
    return {"status": "confirm_email_required", "masked_email": mask_email(real_email)}


def confirm_email_for_mobile(mobile_number: str, email: str) -> dict:
    real_email = _find_email_by_mobile(mobile_number)
    if not real_email or real_email.strip().lower() != email.strip().lower():
        return {"status": "email_mismatch", "message": "That email doesn't match our records."}

    _issue_otp(real_email, PURPOSE_PASSWORD_RESET)
    return {"status": "otp_sent", "email": mask_email(real_email)}


def start_change_password_otp(email: str) -> dict:
    """Issues a change-password OTP to an already-authenticated user's own email.
    Unlike start_forgot_password, the caller (the route) has already verified the
    current password and already knows the email from the session — no identifier
    lookup needed here."""
    _issue_otp(email, PURPOSE_CHANGE_PASSWORD)
    return {"status": "otp_sent", "masked_email": mask_email(email), "retry_after_seconds": RESEND_COOLDOWN_SECONDS}


def resend_otp(email: str, purpose: str = PURPOSE_PASSWORD_RESET) -> dict:
    email = email.strip().lower()
    with connect_db() as conn:
        ensure_password_reset_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE email = %s;", (email,))
            account_exists = cur.fetchone() is not None

            cur.execute(
                "SELECT created_at FROM otp_verifications WHERE email = %s AND purpose = %s;",
                (email, purpose),
            )
            row = cur.fetchone()
            if row:
                elapsed = (datetime.now() - row[0]).total_seconds()
                if elapsed < RESEND_COOLDOWN_SECONDS:
                    return {"status": "cooldown", "retry_after_seconds": int(RESEND_COOLDOWN_SECONDS - elapsed) + 1}

    # Non-distinguishing response either way (mirrors account_registry.py's
    # dummy_verify philosophy) — but only actually send when a real account exists,
    # so resend can't be used to spam an arbitrary address that never started a flow.
    if account_exists:
        _issue_otp(email, purpose)
    return {"status": "otp_sent", "retry_after_seconds": RESEND_COOLDOWN_SECONDS}


def check_otp(email: str, otp: str, purpose: str = PURPOSE_PASSWORD_RESET) -> bool:
    """Validate an OTP without consuming it, so the code can be its own step ahead of
    the new-password screen instead of being submitted together with it.

    A wrong code still burns an attempt — otherwise this would be a free oracle for
    brute-forcing the OTP that the real reset_password call below is protected against.
    A correct one leaves consumed_at untouched, so the subsequent reset_password with
    the same code still succeeds.
    """
    email = email.strip().lower()
    with connect_db() as conn:
        try:
            ensure_password_reset_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, otp_hash, expires_at, attempts, max_attempts, consumed_at
                    FROM otp_verifications
                    WHERE email = %s AND purpose = %s
                    FOR UPDATE;
                    """,
                    (email, purpose),
                )
                row = cur.fetchone()
                if not row:
                    conn.commit()
                    return False

                otp_id, otp_hash, expires_at, attempts, max_attempts, consumed_at = row
                if consumed_at is not None or attempts >= max_attempts or datetime.now() > expires_at:
                    conn.commit()
                    return False

                if not hmac.compare_digest(otp_hash, _otp_hash(str(otp))):
                    cur.execute(
                        "UPDATE otp_verifications SET attempts = attempts + 1 WHERE id = %s;",
                        (otp_id,),
                    )
                    conn.commit()
                    return False
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise


def reset_password(email: str, otp: str, new_password: str, confirm_password: str, purpose: str = PURPOSE_PASSWORD_RESET) -> bool:
    email = email.strip().lower()
    if new_password != confirm_password:
        raise ValueError("New password and confirmed password do not match.")
    validate_password(new_password)

    with connect_db() as conn:
        try:
            ensure_password_reset_schema(conn)
            ensure_patient_auth_audit_schema(conn)
            ensure_lockout_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, otp_hash, expires_at, attempts, max_attempts, consumed_at
                    FROM otp_verifications
                    WHERE email = %s AND purpose = %s
                    FOR UPDATE;
                    """,
                    (email, purpose),
                )
                row = cur.fetchone()
                if not row:
                    conn.commit()
                    return False

                otp_id, otp_hash, expires_at, attempts, max_attempts, consumed_at = row

                if consumed_at is not None or attempts >= max_attempts:
                    conn.commit()
                    return False

                if datetime.now() > expires_at:
                    conn.commit()
                    return False

                if not hmac.compare_digest(otp_hash, _otp_hash(str(otp))):
                    cur.execute(
                        "UPDATE otp_verifications SET attempts = attempts + 1 WHERE id = %s;",
                        (otp_id,),
                    )
                    conn.commit()
                    return False

                cur.execute("SELECT user_id FROM users WHERE email = %s;", (email,))
                user_row = cur.fetchone()
                if not user_row:
                    conn.commit()
                    return False

                cur.execute(
                    "UPDATE users SET password_hash = %s, password_changed_at = NOW() WHERE user_id = %s;",
                    (hash_password(new_password), user_row[0]),
                )
                # Releasing the brute-force lockout here is deliberate: the caller just
                # proved control of the account's email inbox (the OTP above), which is a
                # stronger signal than the password itself. Without this, an account that
                # locked out stays unloggable even after a correct reset — and because a
                # lockout is reported as "invalid email or password", the user is told
                # their brand-new password is wrong and resets again, forever.
                clear_lockout(cur, email)
                cur.execute("UPDATE otp_verifications SET consumed_at = NOW() WHERE id = %s;", (otp_id,))
                _audit_patient(cur, "password_changed", str(user_row[0]), email, purpose=purpose)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    user_id = str(user_row[0])
    # A stolen/old refresh token must not survive this — /auth/refresh would otherwise
    # mint a fresh access token with a new iat that trivially passes the
    # password_changed_at check.
    revoke_all_refresh_tokens(user_id)
    threading.Thread(
        target=_send_security_notification,
        args=(email, "Your password was changed", "Your hospital account password was just changed. If this wasn't you, contact support immediately."),
        daemon=True,
    ).start()
    return True
