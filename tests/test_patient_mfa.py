"""Regression coverage for Step 5: opt-in TOTP MFA for patients
(app/services/patient_mfa.py, app/services/totp.py, the /auth/mfa/* routes, and the
login-flow ordering in /auth/login and /auth/unified-login).

Skips (not fails) if no database is reachable.
"""
import uuid

import pyotp
import pytest
from fastapi.testclient import TestClient

from app.db.connection import connect_db
from app.services.account_registry import ensure_registry_schema, reserve_email
from app.services.passwords import hash_password
from app.services.patient_mfa import _fernet_key
from app.services import totp as totp_module

CURRENT_PASSWORD = "Str0ng!Pass"


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


@pytest.fixture
def client():
    from app.api.main import app

    return TestClient(app)


def _make_patient(email: str, *, email_verified: bool = True, mfa_enabled: bool = False) -> str:
    with connect_db() as conn:
        ensure_registry_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash, email_verified, mfa_enabled)
                VALUES (%s, %s, %s, %s) RETURNING user_id;
                """,
                (email, hash_password(CURRENT_PASSWORD), email_verified, mfa_enabled),
            )
            user_id = str(cur.fetchone()[0])
            cur.execute(
                """
                INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
                VALUES (%s, 'MFA Test', 30, '+919876500077', '1 Test St', %s, 'O+');
                """,
                (user_id, email),
            )
            # unified-login's registry lookup requires this — real signup populates
            # it via create_user_with_profile -> reserve_email; a direct-SQL test
            # user needs the same to exercise /auth/unified-login's real HTTP path.
            reserve_email(cur, email, "patient", user_id)
        conn.commit()
    return user_id


def _cleanup(email: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE email = %s;", (email,))
        conn.commit()


def _decrypted_secret(email: str) -> str:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT mfa_secret_encrypted FROM users WHERE email = %s;", (email,))
            encrypted = cur.fetchone()[0]
    return totp_module.decrypt_secret(encrypted, _fernet_key())


def _current_code(secret: str) -> str:
    return pyotp.TOTP(secret).now()


def _enroll(client, token: str, email: str) -> list[str]:
    start = client.post("/auth/mfa/setup/start", headers={"Authorization": f"Bearer {token}"})
    assert start.status_code == 200
    secret = _decrypted_secret(email)
    verify = client.post(
        "/auth/mfa/setup/verify",
        json={"code": _current_code(secret)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify.status_code == 200
    body = verify.json()
    assert body["status"] == "mfa_enabled"
    assert len(body["recovery_codes"]) == 10
    return body["recovery_codes"]


def test_mfa_pending_token_cannot_access_a_protected_route(client):
    """The exact bug class from the email-verification incident, now for MFA."""
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"mfa-pendingbug-{suffix}@example.com"
    try:
        _make_patient(email)
        login1 = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        token = login1.json()["access_token"]
        _enroll(client, token, email)

        login2 = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        assert login2.status_code == 200
        assert login2.json()["status"] == "patient_mfa_required"
        pending_token = login2.json()["pending_token"]

        protected = client.get("/auth/me", headers={"Authorization": f"Bearer {pending_token}"})
        assert protected.status_code == 401
    finally:
        _cleanup(email)


def test_full_enroll_logout_login_challenge_session_flow(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"mfa-fullflow-{suffix}@example.com"
    try:
        _make_patient(email)
        login1 = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        token = login1.json()["access_token"]
        _enroll(client, token, email)

        client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})

        login2 = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        assert login2.json()["status"] == "patient_mfa_required"
        pending_token = login2.json()["pending_token"]

        secret = _decrypted_secret(email)
        challenge = client.post(
            "/auth/mfa/verify",
            json={"code": _current_code(secret)},
            headers={"Authorization": f"Bearer {pending_token}"},
        )
        assert challenge.status_code == 200
        body = challenge.json()
        assert body["status"] == "authenticated"
        assert body["access_token"]

        me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert me.status_code == 200
    finally:
        _cleanup(email)


def test_backup_code_is_single_use(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"mfa-backupcode-{suffix}@example.com"
    try:
        _make_patient(email)
        login1 = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        token = login1.json()["access_token"]
        recovery_codes = _enroll(client, token, email)
        one_code = recovery_codes[0]

        login2 = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        pending_token_1 = login2.json()["pending_token"]
        first_use = client.post(
            "/auth/mfa/verify", json={"code": one_code}, headers={"Authorization": f"Bearer {pending_token_1}"},
        )
        assert first_use.status_code == 200

        login3 = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        pending_token_2 = login3.json()["pending_token"]
        second_use = client.post(
            "/auth/mfa/verify", json={"code": one_code}, headers={"Authorization": f"Bearer {pending_token_2}"},
        )
        assert second_use.status_code == 400
    finally:
        _cleanup(email)


def test_disable_requires_both_factors(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"mfa-disable-{suffix}@example.com"
    try:
        _make_patient(email)
        login1 = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        token = login1.json()["access_token"]
        _enroll(client, token, email)
        secret = _decrypted_secret(email)
        headers = {"Authorization": f"Bearer {token}"}

        password_only = client.post(
            "/auth/mfa/disable",
            json={"current_password": "WrongPassword!1", "code": _current_code(secret)},
            headers=headers,
        )
        assert password_only.status_code == 401

        code_only = client.post(
            "/auth/mfa/disable",
            json={"current_password": CURRENT_PASSWORD, "code": "000000"},
            headers=headers,
        )
        assert code_only.status_code == 401

        both_correct = client.post(
            "/auth/mfa/disable",
            json={"current_password": CURRENT_PASSWORD, "code": _current_code(secret)},
            headers=headers,
        )
        assert both_correct.status_code == 200
        assert both_correct.json()["status"] == "mfa_disabled"

        # MFA is now off — a normal login no longer challenges for it.
        login2 = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        assert login2.json()["status"] == "authenticated"
    finally:
        _cleanup(email)


def test_unverified_account_with_mfa_enabled_still_hits_email_verification_first(client):
    """A state the app itself can't normally produce (MFA setup requires an already-
    verified, logged-in session), but the ordering guard must hold even if it somehow
    occurs — email-verification branch must win over the MFA branch in both routes."""
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"mfa-unverified-{suffix}@example.com"
    try:
        _make_patient(email, email_verified=False, mfa_enabled=True)

        via_login = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        assert via_login.json()["status"] == "verification_required"

        via_unified = client.post("/auth/unified-login", json={"email": email, "password": CURRENT_PASSWORD})
        assert via_unified.json()["status"] == "verification_required"
    finally:
        _cleanup(email)
