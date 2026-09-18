from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from app.db.connection import connect_db
from app.services.email import send_email
from app.services.passwords import hash_password, verify_password
from app.services.users import validate_password
from app.services.account_registry import ensure_registry_schema, reserve_email
from app.services.login_lockout import (
    AccountLockedError,
    check_lockout,
    clear_lockout,
    ensure_lockout_schema,
    record_failure,
)
from app.services import totp


class DoctorInviteEmailConfigError(RuntimeError):
    """Raised only for the deliberate, safe-to-display config checks in _send_invite_email.

    Kept distinct from a bare RuntimeError so callers can surface this message to an
    admin without risking exposure of some other, unanticipated RuntimeError's text.
    """


INVITE_TTL = timedelta(hours=48)


def ensure_doctor_auth_schema(conn) -> None:
    # login_lockouts is owned by app/services/login_lockout.py but ensured here too:
    # every doctor auth path and admin_management's doctor-list join both read it.
    ensure_lockout_schema(conn)
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS doctor_accounts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(), doctor_id UUID NOT NULL UNIQUE REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                email TEXT NOT NULL UNIQUE, hashed_password TEXT, totp_secret TEXT,
                mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE, recovery_codes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
                is_active BOOLEAN NOT NULL DEFAULT FALSE, invite_token_hash TEXT, invite_expires_at TIMESTAMP,
                invite_consumed_at TIMESTAMP,
                last_login_at TIMESTAMP, last_totp_step BIGINT, created_at TIMESTAMP NOT NULL DEFAULT NOW(), updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS doctor_auth_audit_log (
                audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), doctor_id UUID REFERENCES doctors(doctor_id) ON DELETE SET NULL,
                attempted_email TEXT, action_type TEXT NOT NULL, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_doctor_auth_audit_doctor_created ON doctor_auth_audit_log(doctor_id, created_at DESC);
        """)


def _email(value: str) -> str:
    return value.strip().lower()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _audit(cur, action: str, doctor_id=None, email: str | None = None, **metadata) -> None:
    cur.execute(
        "INSERT INTO doctor_auth_audit_log (doctor_id, attempted_email, action_type, metadata) VALUES (%s, %s, %s, %s::jsonb)",
        (doctor_id, _email(email) if email else None, action, json.dumps(metadata)),
    )


def _fernet_key() -> str:
    key = os.getenv("DOCTOR_AUTH_ENCRYPTION_KEY", "").strip()
    if not key:
        raise RuntimeError("DOCTOR_AUTH_ENCRYPTION_KEY must be configured.")
    return key


def _send_invite_email(email: str, token: str, *, reset: bool) -> str | None:
    frontend = os.getenv("DOCTOR_AUTH_FRONTEND_URL", "").rstrip("/")
    if not frontend:
        raise DoctorInviteEmailConfigError("DOCTOR_AUTH_FRONTEND_URL must be configured.")
    link = f"{frontend}/doctor/set-password?token={token}"
    if os.getenv("DOCTOR_AUTH_EMAIL_NO_SEND", "false").lower() == "true":
        # Dev/test mode: no email is actually sent, so the link is the only way
        # to retrieve it. print() (not logging, which can be filtered below the
        # console's visible level) and flush explicitly so it's never lost to
        # buffering. Gated behind the same flag that disables real delivery —
        # this never fires in a configuration where DOCTOR_AUTH_EMAIL_NO_SEND
        # isn't explicitly set to true, i.e. never when email is actually live.
        print(f"[doctor-invite:no-send] {'reset' if reset else 'invite'} link for {email}: {link}", flush=True)
        return link
    host = os.getenv("DOCTOR_AUTH_SMTP_HOST", "").strip()
    sender = os.getenv("DOCTOR_AUTH_EMAIL_FROM", "").strip()
    if not host or not sender:
        raise DoctorInviteEmailConfigError("SMTP host and sender are required when doctor email delivery is enabled.")
    send_email(
        host=host,
        port=int(os.getenv("DOCTOR_AUTH_SMTP_PORT", "587")),
        use_tls=os.getenv("DOCTOR_AUTH_SMTP_USE_TLS", "true").lower() == "true",
        username=os.getenv("DOCTOR_AUTH_SMTP_USERNAME"),
        password=os.getenv("DOCTOR_AUTH_SMTP_PASSWORD", ""),
        sender=sender,
        to=email,
        subject="Reset your hospital doctor account password" if reset else "Set up your hospital doctor account",
        body=f"Use this one-time link within 48 hours: {link}",
    )
    return None


def issue_invite(doctor_id: str, email: str, *, reset: bool = False) -> None:
    try:
        UUID(doctor_id)
    except ValueError as exc:
        raise ValueError("Doctor not found.") from exc
    normalized = _email(email)
    token = secrets.token_urlsafe(32)
    with connect_db() as conn:
        ensure_doctor_auth_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT doctor_id FROM doctors WHERE doctor_id = %s", (doctor_id,))
            if not cur.fetchone():
                raise ValueError("Doctor not found.")
            cur.execute(
                "SELECT doctor_id FROM doctor_accounts WHERE email = %s AND doctor_id <> %s",
                (normalized, doctor_id),
            )
            if cur.fetchone():
                _audit(cur, "invite_rejected_email_in_use", doctor_id, normalized)
                raise ValueError("This email is already associated with another doctor account.")
            cur.execute("SELECT id, email, is_active FROM doctor_accounts WHERE doctor_id = %s FOR UPDATE", (doctor_id,))
            account = cur.fetchone()
            if account and account[2] and not reset:
                _audit(cur, "invite_rejected_active_account", doctor_id, normalized)
                raise PermissionError("An active account requires the explicit reset-invite endpoint.")
            if account and reset and account[1] != normalized:
                _audit(cur, "password_reset_rejected_email_mismatch", doctor_id, normalized)
                raise PermissionError("The supplied email does not match the doctor account.")
            if not account and reset:
                _audit(cur, "password_reset_rejected_no_account", doctor_id, normalized)
                raise ValueError("Doctor account not found.")
            if account:
                cur.execute("""UPDATE doctor_accounts SET email = %s, invite_token_hash = %s,
                    invite_expires_at = NOW() + INTERVAL '48 hours', invite_consumed_at = NULL, updated_at = NOW()
                    WHERE doctor_id = %s""", (normalized, _token_hash(token), doctor_id))
            else:
                cur.execute("""INSERT INTO doctor_accounts (doctor_id, email, invite_token_hash, invite_expires_at)
                    VALUES (%s, %s, %s, NOW() + INTERVAL '48 hours') RETURNING id""", (doctor_id, normalized, _token_hash(token)))
                account_id = cur.fetchone()[0]
                ensure_registry_schema(conn)
                reserve_email(cur, normalized, "doctor", account_id)
            _audit(cur, "password_reset_invite_sent" if reset else "invite_sent", doctor_id, normalized)
    try:
        dev_preview_link = _send_invite_email(normalized, token, reset=reset)
    except Exception:
        # The token remains valid; the event records that issuance happened without disclosing it.
        with connect_db() as conn:
            ensure_doctor_auth_schema(conn)
            with conn.cursor() as cur:
                _audit(cur, "invite_email_delivery_failed", doctor_id, normalized, reset=reset)
        raise
    if dev_preview_link:
        # Only set when DOCTOR_AUTH_EMAIL_NO_SEND=true, i.e. no real email was sent —
        # surface the link via the admin audit log so it can be shared manually until
        # SMTP is configured. Never populated when real delivery is enabled.
        with connect_db() as conn:
            ensure_doctor_auth_schema(conn)
            with conn.cursor() as cur:
                _audit(cur, "invite_link_no_send", doctor_id, normalized, link=dev_preview_link)


def complete_invite(token: str, password: str) -> dict:
    validate_password(password)
    digest = _token_hash(token)
    with connect_db() as conn:
        ensure_doctor_auth_schema(conn)
        with conn.cursor() as cur:
            cur.execute("""SELECT id, doctor_id, email, invite_expires_at, invite_consumed_at, mfa_enabled
                FROM doctor_accounts WHERE invite_token_hash = %s FOR UPDATE""", (digest,))
            row = cur.fetchone()
            if not row:
                raise PermissionError("Invite token is invalid or has already been used.")
            account_id, doctor_id, email, expires_at, consumed_at, mfa_enabled = row
            now = datetime.now()
            if consumed_at:
                _audit(cur, "invite_completion_rejected_consumed", doctor_id, email)
                raise PermissionError("Invite token has already been used.")
            if not expires_at or expires_at < now:
                _audit(cur, "invite_completion_rejected_expired", doctor_id, email)
                raise PermissionError("Invite token has expired.")
            cur.execute("""UPDATE doctor_accounts SET hashed_password = %s, is_active = TRUE,
                invite_consumed_at = NOW(), updated_at = NOW()
                WHERE id = %s""", (hash_password(password), account_id))
            ensure_lockout_schema(conn)
            clear_lockout(cur, email)
            _audit(cur, "invite_completed", doctor_id, email)
    return {"doctor_id": str(doctor_id), "account_id": str(account_id), "email": email, "mfa_enabled": bool(mfa_enabled)}


def start_mfa_enrollment(account_id: str) -> str:
    secret = totp.generate_secret()
    encrypted = totp.encrypt_secret(secret, _fernet_key())
    with connect_db() as conn:
        ensure_doctor_auth_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT doctor_id, email, is_active, mfa_enabled FROM doctor_accounts WHERE id = %s FOR UPDATE", (account_id,))
            row = cur.fetchone()
            if not row or not row[2] or row[3]:
                raise PermissionError("MFA enrollment is not available.")
            cur.execute("UPDATE doctor_accounts SET totp_secret = %s, updated_at = NOW() WHERE id = %s", (encrypted, account_id))
            _audit(cur, "mfa_enrollment_started", row[0], row[1])
            return totp.provisioning_uri(secret, name=row[1])


def verify_mfa_enrollment(account_id: str, code: str) -> list[str]:
    with connect_db() as conn:
        ensure_doctor_auth_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT doctor_id, email, totp_secret, is_active, mfa_enabled FROM doctor_accounts WHERE id = %s FOR UPDATE", (account_id,))
            row = cur.fetchone()
            if not row or not row[3] or row[4] or not row[2]:
                raise PermissionError("MFA enrollment is not available.")
            secret = totp.decrypt_secret(row[2], _fernet_key())
            if totp.verify_totp(secret, code, None) is None:
                _audit(cur, "mfa_enrollment_verification_failed", row[0], row[1])
                raise PermissionError("Invalid MFA code.")
            recovery_codes = totp.generate_backup_codes()
            hashes = [hash_password(value) for value in recovery_codes]
            cur.execute("UPDATE doctor_accounts SET mfa_enabled = TRUE, recovery_codes = %s, updated_at = NOW() WHERE id = %s", (hashes, account_id))
            _audit(cur, "mfa_enrolled", row[0], row[1])
            return recovery_codes


def authenticate_doctor_password(email: str, password: str) -> tuple[str, str, str]:
    normalized = _email(email)
    with connect_db() as conn:
        ensure_doctor_auth_schema(conn)
        ensure_lockout_schema(conn)
        try:
            with conn.cursor() as cur:
                check_lockout(cur, normalized)
                cur.execute("""SELECT id, doctor_id, email, hashed_password, is_active, mfa_enabled
                    FROM doctor_accounts WHERE email = %s FOR UPDATE""", (normalized,))
                row = cur.fetchone()
                if not row:
                    record_failure(cur, normalized)
                    _audit(cur, "login_failed_unknown_email", None, normalized)
                    raise PermissionError("Invalid email or password.")
                account_id, doctor_id, db_email, password_hash, active, mfa_enabled = row
                if not active or not password_hash or not verify_password(password, password_hash):
                    record_failure(cur, normalized)
                    _audit(cur, "login_failed", doctor_id, db_email)
                    raise PermissionError("Invalid email or password.")
                if not mfa_enabled:
                    _audit(cur, "login_rejected_mfa_not_enrolled", doctor_id, db_email)
                    raise PermissionError("MFA enrollment is required before login.")
                clear_lockout(cur, normalized)
                _audit(cur, "password_verified_mfa_pending", doctor_id, db_email)
                return str(account_id), str(doctor_id), db_email
        except AccountLockedError:
            with conn.cursor() as cur:
                _audit(cur, "login_rejected_locked", None, normalized)
            conn.commit()
            raise
        except PermissionError:
            # connect_db() rolls back on any exception, which would silently discard the
            # failure counter and audit row written just above — the reason doctor
            # lockout never actually engaged before. Commit the bookkeeping, then let
            # the rejection propagate. Only our own control-flow exception is committed
            # this way; a real database error still rolls back.
            conn.commit()
            raise


def complete_mfa_challenge(account_id: str, code: str) -> tuple[str, str, str, bool]:
    with connect_db() as conn:
        ensure_doctor_auth_schema(conn)
        with conn.cursor() as cur:
            cur.execute("""SELECT doctor_id, email, totp_secret, recovery_codes, is_active, mfa_enabled, last_totp_step
                FROM doctor_accounts WHERE id = %s FOR UPDATE""", (account_id,))
            row = cur.fetchone()
            if not row or not row[4] or not row[5] or not row[2]:
                raise PermissionError("Invalid MFA challenge.")
            doctor_id, email, encrypted_secret, recovery_hashes, _, _, last_step = row
            secret = totp.decrypt_secret(encrypted_secret, _fernet_key())
            try:
                matching_step = totp.verify_totp(secret, code, last_step)
            except totp.TotpReplayError:
                _audit(cur, "mfa_challenge_rejected_replay", doctor_id, email)
                raise PermissionError("Invalid MFA code.")
            if matching_step is not None:
                cur.execute("UPDATE doctor_accounts SET last_totp_step = %s, last_login_at = NOW(), updated_at = NOW() WHERE id = %s", (matching_step, account_id))
                _audit(cur, "login_success", doctor_id, email)
                return str(doctor_id), email, str(account_id), False
            # else: not a valid TOTP code at all — fall through to recovery-code check.
            matched_hash = next((stored for stored in recovery_hashes if verify_password(code, stored)), None)
            if not matched_hash:
                _audit(cur, "mfa_challenge_failed", doctor_id, email)
                raise PermissionError("Invalid MFA code.")
            cur.execute("UPDATE doctor_accounts SET recovery_codes = array_remove(recovery_codes, %s), last_login_at = NOW(), updated_at = NOW() WHERE id = %s", (matched_hash, account_id))
            _audit(cur, "recovery_code_used", doctor_id, email)
            _audit(cur, "login_success", doctor_id, email, recovery_code=True)
            return str(doctor_id), email, str(account_id), True


def get_doctor_profile(doctor_id: str, account_id: str) -> dict | None:
    with connect_db() as conn:
        ensure_doctor_auth_schema(conn)
        with conn.cursor() as cur:
            cur.execute("""SELECT d.doctor_id, d.name, d.department, d.experience_years, d.is_active,
                a.id, a.email, a.mfa_enabled, a.is_active
                FROM doctor_accounts a JOIN doctors d ON d.doctor_id = a.doctor_id
                WHERE a.id = %s AND d.doctor_id = %s""", (account_id, doctor_id))
            row = cur.fetchone()
    if not row or not row[8] or not row[4]:
        return None
    return {"doctor_id": str(row[0]), "name": row[1], "department": row[2], "experience_years": row[3],
            "is_active": bool(row[4]), "account_id": str(row[5]), "email": row[6], "mfa_enabled": bool(row[7])}


def unlock_doctor_account(doctor_id: str, *, actor_email: str) -> None:
    with connect_db() as conn:
        ensure_doctor_auth_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email FROM doctor_accounts WHERE doctor_id = %s FOR UPDATE",
                (doctor_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Doctor account not found.")
            account_id, email = row
            ensure_lockout_schema(conn)
            cur.execute("SELECT failed_attempts FROM login_lockouts WHERE email = %s;", (_email(email),))
            existing = cur.fetchone()
            clear_lockout(cur, email)
            _audit(
                cur, "account_unlocked_by_admin", doctor_id, email,
                admin_email=_email(actor_email),
                had_failed_attempts=int(existing[0]) if existing else 0,
            )
        conn.commit()


def list_doctor_auth_audit_log(
    *,
    doctor_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    offset = (page - 1) * page_size
    clauses: list[str] = []
    params: list[object] = []
    if doctor_id:
        clauses.append("doctor_id = %s")
        params.append(doctor_id)
    if start_date:
        clauses.append("created_at >= %s")
        params.append(start_date)
    if end_date:
        clauses.append("created_at < %s")
        params.append(end_date + timedelta(days=1))
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with connect_db() as conn:
        ensure_doctor_auth_schema(conn)
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM doctor_auth_audit_log {where_sql}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""SELECT audit_id, doctor_id, attempted_email, action_type, metadata, created_at
                    FROM doctor_auth_audit_log {where_sql}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s""",
                (*params, page_size, offset),
            )
            rows = cur.fetchall()

    return {
        "entries": [
            {
                "audit_id": str(audit_id),
                "doctor_id": str(row_doctor_id) if row_doctor_id else None,
                "attempted_email": attempted_email,
                "action_type": action_type,
                "metadata": metadata,
                "created_at": created_at.isoformat() if created_at else None,
            }
            for audit_id, row_doctor_id, attempted_email, action_type, metadata, created_at in rows
        ],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


def ensure_rate_limit_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_limit_events (
                id BIGSERIAL PRIMARY KEY,
                rate_key TEXT NOT NULL,
                occurred_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_rate_limit_events_key_time ON rate_limit_events(rate_key, occurred_at);
            """
        )


def check_rate_limit(scope: str, ip: str, account_key: str, *, limit: int | None = None, window_seconds: int = 300) -> None:
    """limit/window_seconds are optional, additive overrides — every existing caller
    (doctor login/MFA, email_verify_resend) omits them and gets today's exact
    behavior (env-var-derived limit, 300s window) unchanged. New callers (password-
    reset resend) pass both explicitly.

    Postgres-backed sliding-window log (rate_limit_events) rather than the original
    in-memory dict — the in-memory version is only correct for a single worker
    process; every process would otherwise get its own independent counters.
    pg_advisory_xact_lock(hashtext(key)) serializes concurrent checks on the SAME key
    only (an improvement over the original's single global lock across every key),
    closing the check-then-insert race a naive port would have."""
    if limit is None:
        limit = int(os.getenv("DOCTOR_AUTH_LOGIN_RATE_LIMIT" if scope == "login" else "DOCTOR_AUTH_MFA_RATE_LIMIT", "10"))

    # Deliberately a SEPARATE, sequential (not nested) connect_db() call from the one
    # below, fully committed before the advisory lock is ever requested. Combining
    # ensure_rate_limit_schema's CREATE INDEX IF NOT EXISTS (a table-level lock) with
    # pg_advisory_xact_lock in the SAME transaction reproduced the exact deadlock
    # class already documented in app/db/connection.py's DANGER docstring — caught
    # by this test's own concurrency test (a genuine `deadlock detected` from
    # Postgres, not a flake). This is a hot path (every login/resend attempt), so the
    # two lock kinds must never be held in the same transaction.
    with connect_db() as conn:
        ensure_rate_limit_schema(conn)

    with connect_db() as conn:
        try:
            with conn.cursor() as cur:
                for key in (f"{scope}:ip:{ip}", f"{scope}:account:{account_key}"):
                    cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s));", (key,))
                    cur.execute(
                        "DELETE FROM rate_limit_events WHERE rate_key = %s AND occurred_at < NOW() - (%s * INTERVAL '1 second');",
                        (key, window_seconds),
                    )
                    cur.execute("SELECT COUNT(*) FROM rate_limit_events WHERE rate_key = %s;", (key,))
                    if cur.fetchone()[0] >= limit:
                        conn.commit()
                        raise PermissionError("Too many authentication attempts. Please try again later.")
                    cur.execute("INSERT INTO rate_limit_events (rate_key) VALUES (%s);", (key,))
            conn.commit()
        except PermissionError:
            raise
        except Exception:
            conn.rollback()
            raise
