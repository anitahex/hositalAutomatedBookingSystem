"""Opt-in TOTP MFA for patients — mirrors app/services/doctor_auth.py's enrollment/
challenge shape (including last_totp_step replay protection) using the shared
app/services/totp.py mechanics, but with its own users.mfa_enabled/
mfa_secret_encrypted/last_totp_step columns and mfa_backup_codes table. Doctor and
patient accounts stay fully separate; only the TOTP algorithm and encryption
mechanics are shared.

Reuses DOCTOR_AUTH_ENCRYPTION_KEY as the Fernet key (same reasoning as reusing the
doctor SMTP config for patient email earlier this session) — one encryption key for
all TOTP secrets at rest, no new required env var.
"""
import json
import os
import threading
from datetime import date, timedelta

from app.db.connection import connect_db
from app.services import totp
from app.services.email import send_email
from app.services.login_lockout import clear_lockout, ensure_lockout_schema
from app.services.passwords import hash_password, verify_password


def _fernet_key() -> str:
    key = os.getenv("DOCTOR_AUTH_ENCRYPTION_KEY", "").strip()
    if not key:
        raise RuntimeError("DOCTOR_AUTH_ENCRYPTION_KEY must be configured.")
    return key


def ensure_patient_auth_audit_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS patient_auth_audit_log (
                audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                patient_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
                email TEXT,
                action_type TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_patient_auth_audit_patient_created
                ON patient_auth_audit_log(patient_id, created_at DESC);
            """
        )


def _audit_patient(cur, action: str, patient_id: str, email: str | None, **metadata) -> None:
    cur.execute(
        "INSERT INTO patient_auth_audit_log (patient_id, email, action_type, metadata) VALUES (%s, %s, %s, %s::jsonb)",
        (patient_id, email.strip().lower() if email else None, action, json.dumps(metadata)),
    )


def _send_security_notification(email: str, subject: str, body: str) -> None:
    """Best-effort — never raises. The security action itself has already committed by
    the time this is called; a bounced/failed notification must not undo it."""
    try:
        if os.getenv("PATIENT_AUTH_EMAIL_NO_SEND", "false").lower() == "true":
            print(f"[patient-mfa:no-send] {subject} -> {email}", flush=True)
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
        print(f"[patient-mfa:notify-failed] {subject} -> {email}: {exc}", flush=True)


def ensure_mfa_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret_encrypted TEXT;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS last_totp_step BIGINT;

            CREATE TABLE IF NOT EXISTS mfa_backup_codes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                code_hash TEXT NOT NULL,
                used_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_mfa_backup_codes_user ON mfa_backup_codes(user_id);
            """
        )


def start_mfa_setup(user_id: str) -> str:
    """Returns the otpauth:// provisioning URI. Stores the secret immediately, but
    mfa_enabled stays FALSE until verify_mfa_setup succeeds — mirrors
    doctor_auth.py::start_mfa_enrollment."""
    secret = totp.generate_secret()
    encrypted = totp.encrypt_secret(secret, _fernet_key())
    with connect_db() as conn:
        try:
            ensure_mfa_schema(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT email, mfa_enabled FROM users WHERE user_id = %s FOR UPDATE;", (user_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError("User account was not found.")
                if row[1]:
                    raise PermissionError("MFA is already enabled for this account.")
                cur.execute(
                    "UPDATE users SET mfa_secret_encrypted = %s WHERE user_id = %s;",
                    (encrypted, user_id),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return totp.provisioning_uri(secret, name=row[0])


def verify_mfa_setup(user_id: str, code: str) -> list[str]:
    """Enables MFA and generates 10 backup codes, returned once (only their hashes
    are persisted)."""
    with connect_db() as conn:
        try:
            ensure_mfa_schema(conn)
            ensure_patient_auth_audit_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT mfa_secret_encrypted, mfa_enabled, email FROM users WHERE user_id = %s FOR UPDATE;",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row or row[1] or not row[0]:
                    raise PermissionError("MFA setup is not available.")

                secret = totp.decrypt_secret(row[0], _fernet_key())
                if totp.verify_totp(secret, code, None) is None:
                    raise PermissionError("Invalid MFA code.")

                recovery_codes = totp.generate_backup_codes()
                hashes = [hash_password(value) for value in recovery_codes]
                cur.execute("UPDATE users SET mfa_enabled = TRUE WHERE user_id = %s;", (user_id,))
                cur.executemany(
                    "INSERT INTO mfa_backup_codes (user_id, code_hash) VALUES (%s, %s);",
                    [(user_id, code_hash) for code_hash in hashes],
                )
                _audit_patient(cur, "mfa_enabled", user_id, row[2])
            conn.commit()
            return recovery_codes
        except Exception:
            conn.rollback()
            raise


def verify_mfa_challenge(user_id: str, code: str) -> bool:
    """Accepts either a live TOTP code (replay-protected via last_totp_step,
    mirroring doctor_auth.py::complete_mfa_challenge) or an unused backup code
    (single-use)."""
    with connect_db() as conn:
        try:
            ensure_mfa_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT mfa_secret_encrypted, mfa_enabled, last_totp_step FROM users WHERE user_id = %s FOR UPDATE;",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row or not row[1] or not row[0]:
                    conn.commit()
                    return False

                secret = totp.decrypt_secret(row[0], _fernet_key())
                last_step = row[2]
                try:
                    matching_step = totp.verify_totp(secret, code, last_step)
                except totp.TotpReplayError:
                    conn.commit()
                    return False

                if matching_step is not None:
                    cur.execute("UPDATE users SET last_totp_step = %s WHERE user_id = %s;", (matching_step, user_id))
                    conn.commit()
                    return True

                cur.execute(
                    "SELECT id, code_hash FROM mfa_backup_codes WHERE user_id = %s AND used_at IS NULL;",
                    (user_id,),
                )
                backup_rows = cur.fetchall()
                matched_id = next((bid for bid, bhash in backup_rows if verify_password(code, bhash)), None)
                if matched_id is None:
                    conn.commit()
                    return False

                cur.execute("UPDATE mfa_backup_codes SET used_at = NOW() WHERE id = %s;", (matched_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise


def disable_mfa(user_id: str, current_password: str, code: str) -> None:
    """Requires BOTH the current password AND a valid live TOTP/backup code."""
    with connect_db() as conn:
        try:
            ensure_mfa_schema(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT password_hash, email FROM users WHERE user_id = %s;", (user_id,))
                row = cur.fetchone()
                if not row or not verify_password(current_password, row[0]):
                    raise PermissionError("Current password is incorrect.")
                email = row[1]
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    if not verify_mfa_challenge(user_id, code):
        raise PermissionError("Invalid MFA code.")

    with connect_db() as conn:
        try:
            ensure_mfa_schema(conn)
            ensure_patient_auth_audit_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET mfa_enabled = FALSE, mfa_secret_encrypted = NULL, last_totp_step = NULL WHERE user_id = %s;",
                    (user_id,),
                )
                cur.execute("DELETE FROM mfa_backup_codes WHERE user_id = %s;", (user_id,))
                _audit_patient(cur, "mfa_disabled", user_id, email)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    threading.Thread(
        target=_send_security_notification,
        args=(email, "Two-factor authentication was disabled",
              "Two-factor authentication was just disabled on your hospital account. If this wasn't you, contact support immediately."),
        daemon=True,
    ).start()


def regenerate_backup_codes(user_id: str, code: str) -> list[str]:
    """Requires a valid live TOTP/backup code. Invalidates all existing backup codes."""
    if not verify_mfa_challenge(user_id, code):
        raise PermissionError("Invalid MFA code.")

    recovery_codes = totp.generate_backup_codes()
    hashes = [hash_password(value) for value in recovery_codes]
    with connect_db() as conn:
        try:
            ensure_mfa_schema(conn)
            ensure_patient_auth_audit_schema(conn)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM mfa_backup_codes WHERE user_id = %s;", (user_id,))
                cur.executemany(
                    "INSERT INTO mfa_backup_codes (user_id, code_hash) VALUES (%s, %s);",
                    [(user_id, code_hash) for code_hash in hashes],
                )
                cur.execute("SELECT email FROM users WHERE user_id = %s;", (user_id,))
                email = cur.fetchone()[0]
                _audit_patient(cur, "backup_codes_regenerated", user_id, email)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    threading.Thread(
        target=_send_security_notification,
        args=(email, "Your backup codes were regenerated",
              "Your hospital account's two-factor backup codes were just regenerated — your old codes no longer work. If this wasn't you, contact support immediately."),
        daemon=True,
    ).start()
    return recovery_codes


def ensure_admin_patient_actions_log_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS admin_patient_actions_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                admin_email TEXT NOT NULL,
                patient_id UUID NOT NULL,
                action TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_admin_patient_actions_log_patient
                ON admin_patient_actions_log(patient_id, created_at DESC);
            """
        )


def reset_patient_mfa(patient_id: str, *, actor_email: str) -> None:
    """Admin-assisted MFA reset for a locked-out patient — force-disables MFA WITHOUT
    requiring their password or a live TOTP/backup code. Logged to
    admin_patient_actions_log (mirrors doctor_auth.py's unlock_doctor_account +
    audit-log convention)."""
    with connect_db() as conn:
        try:
            ensure_mfa_schema(conn)
            ensure_admin_patient_actions_log_schema(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT mfa_enabled FROM users WHERE user_id = %s FOR UPDATE;", (patient_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError("Patient account not found.")
                had_mfa_enabled = bool(row[0])

                cur.execute(
                    "UPDATE users SET mfa_enabled = FALSE, mfa_secret_encrypted = NULL, last_totp_step = NULL WHERE user_id = %s;",
                    (patient_id,),
                )
                cur.execute("DELETE FROM mfa_backup_codes WHERE user_id = %s;", (patient_id,))
                cur.execute(
                    """
                    INSERT INTO admin_patient_actions_log (admin_email, patient_id, action, metadata)
                    VALUES (%s, %s, %s, %s::jsonb);
                    """,
                    (
                        actor_email.strip().lower(),
                        patient_id,
                        "mfa_reset_by_admin",
                        json.dumps({"had_mfa_enabled": had_mfa_enabled}),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def unlock_patient_login(patient_id: str, *, actor_email: str) -> None:
    """Admin-assisted release of a patient's brute-force lockout (and its escalation
    rung). Mirrors doctor_auth.py::unlock_doctor_account, and is logged to
    admin_patient_actions_log the same way reset_patient_mfa is."""
    with connect_db() as conn:
        try:
            ensure_lockout_schema(conn)
            ensure_admin_patient_actions_log_schema(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT email FROM users WHERE user_id = %s;", (patient_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError("Patient account not found.")
                email = row[0]

                cur.execute(
                    "SELECT failed_attempts, lockout_count, locked_until FROM login_lockouts WHERE email = %s;",
                    (email.strip().lower(),),
                )
                existing = cur.fetchone()
                clear_lockout(cur, email)
                cur.execute(
                    """
                    INSERT INTO admin_patient_actions_log (admin_email, patient_id, action, metadata)
                    VALUES (%s, %s, %s, %s::jsonb);
                    """,
                    (
                        actor_email.strip().lower(),
                        patient_id,
                        "login_unlocked_by_admin",
                        json.dumps({
                            "had_failed_attempts": int(existing[0]) if existing else 0,
                            "had_lockout_count": int(existing[1]) if existing else 0,
                            "was_locked": bool(existing and existing[2]),
                        }),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def list_patient_auth_audit_log(
    *,
    patient_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Mirrors doctor_auth.py::list_doctor_auth_audit_log's filter/paginate/response
    shape exactly, reading patient_auth_audit_log instead."""
    offset = (page - 1) * page_size
    clauses: list[str] = []
    params: list[object] = []
    if patient_id:
        clauses.append("patient_id = %s")
        params.append(patient_id)
    if start_date:
        clauses.append("created_at >= %s")
        params.append(start_date)
    if end_date:
        clauses.append("created_at < %s")
        params.append(end_date + timedelta(days=1))
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with connect_db() as conn:
        ensure_patient_auth_audit_schema(conn)
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM patient_auth_audit_log {where_sql}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""SELECT audit_id, patient_id, email, action_type, metadata, created_at
                    FROM patient_auth_audit_log {where_sql}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s""",
                (*params, page_size, offset),
            )
            rows = cur.fetchall()

    return {
        "entries": [
            {
                "audit_id": str(audit_id),
                "patient_id": str(row_patient_id) if row_patient_id else None,
                "attempted_email": email,
                "action_type": action_type,
                "metadata": metadata,
                "created_at": created_at.isoformat() if created_at else None,
            }
            for audit_id, row_patient_id, email, action_type, metadata, created_at in rows
        ],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


def list_admin_patient_actions_log(
    *,
    patient_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Exposes admin_patient_actions_log (populated by reset_patient_mfa, previously
    write-only with no admin-facing read path) — same shape as
    list_doctor_auth_audit_log."""
    offset = (page - 1) * page_size
    clauses: list[str] = []
    params: list[object] = []
    if patient_id:
        clauses.append("patient_id = %s")
        params.append(patient_id)
    if start_date:
        clauses.append("created_at >= %s")
        params.append(start_date)
    if end_date:
        clauses.append("created_at < %s")
        params.append(end_date + timedelta(days=1))
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with connect_db() as conn:
        ensure_admin_patient_actions_log_schema(conn)
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM admin_patient_actions_log {where_sql}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""SELECT id, patient_id, admin_email, action, metadata, created_at
                    FROM admin_patient_actions_log {where_sql}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s""",
                (*params, page_size, offset),
            )
            rows = cur.fetchall()

    return {
        "entries": [
            {
                "audit_id": str(audit_id),
                "patient_id": str(row_patient_id) if row_patient_id else None,
                "attempted_email": admin_email,
                "action_type": action,
                "metadata": metadata,
                "created_at": created_at.isoformat() if created_at else None,
            }
            for audit_id, row_patient_id, admin_email, action, metadata, created_at in rows
        ],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }
