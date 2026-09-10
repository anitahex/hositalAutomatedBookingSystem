import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid

from app.db.connection import connect_db

logger = logging.getLogger(__name__)

_DEV_DEFAULT_SECRET = "dev-only-change-me"

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = _DEV_DEFAULT_SECRET
    # Loud, impossible-to-miss warning rather than a silent fallback: this literal
    # string is public (it's in this source file), so any token signed with it can
    # be forged by anyone. Previously it was ALSO accepted permanently even when a
    # real JWT_SECRET was configured (see FULL_SYSTEM_AUDIT.md P0 #1) — that
    # unconditional acceptance has been removed; this warning now covers the one
    # remaining real risk, an operator never setting JWT_SECRET at all.
    logger.warning(
        "JWT_SECRET is not set — falling back to a PUBLIC, INSECURE default signing "
        "key ('%s'). Anyone who reads this source can forge valid tokens for any "
        "role. Set JWT_SECRET to a long random value before deploying.",
        _DEV_DEFAULT_SECRET,
    )

JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", str(60 * 60 * 24 * 7)))

# For a genuine secret-rotation window only: set JWT_LEGACY_SECRET to the PREVIOUS
# JWT_SECRET value while rotating, so tokens issued before the rotation still verify
# until they naturally expire. Unlike the old behavior, nothing is accepted here
# unless an operator deliberately configured it.
LEGACY_JWT_SECRETS = [secret for secret in {os.getenv("JWT_LEGACY_SECRET")} if secret]


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_access_token(
    *,
    patient_id: str | None = None,
    subject: str | None = None,
    email: str,
    role: str = "patient",
    extra_claims: dict | None = None,
    expires_in_seconds: int | None = None,
) -> str:
    token_subject = subject or patient_id
    if not token_subject:
        raise ValueError("A token subject is required.")

    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": token_subject,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + (expires_in_seconds or JWT_EXP_SECONDS),
        # Unique per-token id so a specific token can be revoked (see revoke_token/
        # is_token_revoked below) without needing a blacklist keyed on the raw token
        # string. Tokens issued before this field existed simply have no jti and can't
        # be explicitly revoked — they still expire normally.
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)

    signing_input = ".".join(
        [
            _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(
        JWT_SECRET.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def create_doctor_session_token(*, doctor_id: str, account_id: str, email: str) -> str:
    return create_access_token(
        subject=doctor_id,
        email=email,
        role="doctor",
        extra_claims={"token_kind": "doctor_session", "doctor_id": doctor_id, "account_id": account_id},
    )


def create_doctor_mfa_pending_token(*, doctor_id: str, account_id: str, email: str) -> str:
    return create_access_token(
        subject=doctor_id,
        email=email,
        role="doctor",
        expires_in_seconds=300,
        extra_claims={"token_kind": "doctor_mfa_pending", "aud": "doctor_mfa_challenge", "doctor_id": doctor_id, "account_id": account_id},
    )


def create_doctor_mfa_enrollment_token(*, doctor_id: str, account_id: str, email: str) -> str:
    return create_access_token(
        subject=doctor_id,
        email=email,
        role="doctor",
        expires_in_seconds=1800,
        extra_claims={"token_kind": "doctor_mfa_enrollment", "aud": "doctor_mfa_enrollment", "doctor_id": doctor_id, "account_id": account_id},
    )


def ensure_token_revocation_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                jti TEXT PRIMARY KEY,
                revoked_at TIMESTAMP NOT NULL DEFAULT NOW(),
                expires_at_epoch BIGINT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expiry ON revoked_tokens(expires_at_epoch);
            """
        )


def revoke_token(jti: str, expires_at_epoch: int) -> None:
    """Called by POST /auth/logout (works for any role — patient/doctor/admin all
    verify through verify_access_token below). Also opportunistically deletes rows
    past their own expiry on every call: once a token's exp has passed it already
    fails verify_access_token's exp check before ever reaching the revocation lookup,
    so keeping an expired entry around serves no purpose — this keeps the table
    self-bounding without a separate scheduled job."""
    if not jti:
        return
    now_epoch = int(time.time())
    with connect_db() as conn:
        try:
            ensure_token_revocation_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO revoked_tokens (jti, expires_at_epoch) VALUES (%s, %s) ON CONFLICT (jti) DO NOTHING;",
                    (jti, expires_at_epoch),
                )
                cur.execute("DELETE FROM revoked_tokens WHERE expires_at_epoch < %s;", (now_epoch,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _is_token_revoked(jti: str | None) -> bool:
    if not jti:
        return False
    with connect_db() as conn:
        ensure_token_revocation_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM revoked_tokens WHERE jti = %s;", (jti,))
            return cur.fetchone() is not None


def verify_access_token(token: str) -> dict | None:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".", 2)
    except ValueError:
        return None

    signing_input = f"{header_b64}.{payload_b64}"
    try:
        supplied_signature = _b64url_decode(signature_b64)
    except Exception:
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None

    if payload.get("exp", 0) < int(time.time()):
        return None

    if not payload.get("sub"):
        return None

    candidate_secrets = [JWT_SECRET, *LEGACY_JWT_SECRETS]
    signature_valid = False
    for secret in candidate_secrets:
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if hmac.compare_digest(expected_signature, supplied_signature):
            signature_valid = True
            break

    if not signature_valid:
        return None

    if _is_token_revoked(payload.get("jti")):
        return None

    return payload
