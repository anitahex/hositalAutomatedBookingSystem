"""Long-lived refresh tokens for patient and admin sessions, paired with short-lived
access tokens (app/services/tokens.py::ACCESS_TOKEN_TTL_SECONDS). Doctor sessions are
deliberately not covered — only patient/admin login/verification sites issue these.

Only a SHA-256 hash is ever stored, mirroring the doctor-invite token pattern in
app/services/doctor_auth.py (_token_hash). Rotation is single-use: the presented row is
revoked in the same transaction its replacement is issued, so a reused
(already-rotated) refresh token can never succeed twice.
"""
import hashlib
import secrets

from app.db.connection import connect_db

REFRESH_TOKEN_TTL_DAYS = 30


def ensure_refresh_token_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS refresh_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                email TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                revoked_at TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
            """
        )


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_refresh_token(*, user_id: str, role: str, email: str) -> str:
    raw = secrets.token_urlsafe(32)
    with connect_db() as conn:
        try:
            ensure_refresh_token_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO refresh_tokens (token_hash, user_id, role, email, expires_at)
                    VALUES (%s, %s, %s, %s, NOW() + INTERVAL '30 days');
                    """,
                    (_hash(raw), user_id, role, email),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return raw


def rotate_refresh_token(raw_token: str) -> tuple[str, str, str, str] | None:
    """Validate and single-use rotate a refresh token.

    Returns (new_raw_token, user_id, role, email), or None if the presented token is
    unknown, already revoked (reused), or expired.
    """
    digest = _hash(raw_token)
    with connect_db() as conn:
        try:
            ensure_refresh_token_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, role, email, expires_at, revoked_at
                    FROM refresh_tokens
                    WHERE token_hash = %s
                    FOR UPDATE;
                    """,
                    (digest,),
                )
                row = cur.fetchone()
                if not row:
                    conn.commit()
                    return None

                user_id, role, email, expires_at, revoked_at = row
                if revoked_at is not None:
                    conn.commit()
                    return None

                cur.execute("SELECT NOW() > %s;", (expires_at,))
                if cur.fetchone()[0]:
                    conn.commit()
                    return None

                cur.execute(
                    "UPDATE refresh_tokens SET revoked_at = NOW() WHERE token_hash = %s;",
                    (digest,),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    new_raw = issue_refresh_token(user_id=user_id, role=role, email=email)
    return new_raw, user_id, role, email


def revoke_all_refresh_tokens(user_id: str) -> None:
    """Called on password change/reset — otherwise a stolen or old refresh token would
    survive the change indefinitely, since /auth/refresh mints a brand-new access token
    with a fresh iat that trivially passes current_user's password_changed_at check."""
    with connect_db() as conn:
        try:
            ensure_refresh_token_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = %s AND revoked_at IS NULL;",
                    (user_id,),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
