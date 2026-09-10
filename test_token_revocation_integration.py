"""Regression coverage for FULL_SYSTEM_AUDIT.md P1 #7: there was no server-side way
to invalidate a JWT before its natural expiry for any role (patient/doctor/admin) —
"logout" only cleared client-side storage. Requires a real database (revoke_token/
verify_access_token's revocation check both hit Postgres); skips cleanly if
unreachable, matching this repo's convention.
"""
import time

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.routes import auth as auth_route
from app.db.connection import connect_db
from app.services.tokens import create_access_token, revoke_token, verify_access_token


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _cleanup(jti: str | None):
    if not jti:
        return
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM revoked_tokens WHERE jti = %s", (jti,))
        conn.commit()


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_created_tokens_have_a_unique_jti():
    _skip_if_no_database()
    token_a = create_access_token(patient_id="patient-1", email="a@example.com")
    token_b = create_access_token(patient_id="patient-1", email="a@example.com")
    payload_a = verify_access_token(token_a)
    payload_b = verify_access_token(token_b)
    assert payload_a["jti"]
    assert payload_b["jti"]
    assert payload_a["jti"] != payload_b["jti"]


def test_revoked_token_is_rejected_by_verify_access_token():
    _skip_if_no_database()
    token = create_access_token(patient_id="patient-revoke-1", email="revoke1@example.com")
    payload = verify_access_token(token)
    assert payload is not None  # valid before revocation

    jti = None
    try:
        jti = payload["jti"]
        revoke_token(jti, payload["exp"])
        assert verify_access_token(token) is None
    finally:
        _cleanup(jti)


def test_revoking_a_token_twice_does_not_error():
    _skip_if_no_database()
    token = create_access_token(patient_id="patient-revoke-2", email="revoke2@example.com")
    payload = verify_access_token(token)
    jti = None
    try:
        jti = payload["jti"]
        revoke_token(jti, payload["exp"])
        revoke_token(jti, payload["exp"])  # second call, same jti — must not raise
        assert verify_access_token(token) is None
    finally:
        _cleanup(jti)


def test_revoke_token_opportunistically_deletes_expired_entries():
    _skip_if_no_database()
    now = int(time.time())
    already_expired_jti = "test-already-expired-jti"
    fresh_jti = None
    try:
        revoke_token(already_expired_jti, now - 3600)  # expired an hour ago

        token = create_access_token(patient_id="patient-revoke-3", email="revoke3@example.com")
        payload = verify_access_token(token)
        fresh_jti = payload["jti"]
        revoke_token(fresh_jti, payload["exp"])  # triggers the opportunistic cleanup

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM revoked_tokens WHERE jti = %s", (already_expired_jti,))
                assert cur.fetchone() is None, "expired revocation entry should have been cleaned up"
                cur.execute("SELECT 1 FROM revoked_tokens WHERE jti = %s", (fresh_jti,))
                assert cur.fetchone() is not None, "the fresh revocation itself should still be present"
    finally:
        _cleanup(already_expired_jti)
        _cleanup(fresh_jti)


def test_token_with_no_jti_is_never_treated_as_revoked():
    """Tokens issued before this feature existed have no jti — verify_access_token
    must not crash or wrongly reject them on that basis."""
    from app.services.tokens import _is_token_revoked
    assert _is_token_revoked(None) is False


def test_logout_route_revokes_the_presented_token_role_agnostically():
    """One shared /auth/logout works for any role — this test uses a doctor-session
    token to confirm it isn't patient-only, without needing a real doctor account
    (verify_access_token doesn't care what role a token carries)."""
    _skip_if_no_database()
    from app.services.tokens import create_doctor_session_token

    token = create_doctor_session_token(doctor_id="doctor-1", account_id="account-1", email="doc@example.com")
    payload = verify_access_token(token)
    jti = None
    try:
        jti = payload["jti"]
        result = auth_route.logout(credentials=_credentials(token))
        assert result == {"status": "logged_out"}
        assert verify_access_token(token) is None
    finally:
        _cleanup(jti)


def test_logout_route_rejects_missing_credentials():
    with pytest.raises(HTTPException) as exc:
        auth_route.logout(credentials=None)
    assert exc.value.status_code == 401


def test_logout_route_rejects_invalid_token():
    with pytest.raises(HTTPException) as exc:
        auth_route.logout(credentials=_credentials("not-a-real-token"))
    assert exc.value.status_code == 401
