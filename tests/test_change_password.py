"""Regression coverage for the OTP-gated change-password flow
(POST /auth/change-password/start, /resend, /confirm — app/services/password_reset.py's
PURPOSE_CHANGE_PASSWORD path, app/services/users.py::verify_current_password) and the
password_changed_at session-invalidation check in app/api/dependencies.py::current_user.

Reuses the forgot-password OTP machinery (same otp_verifications table, same
OTP_TTL_MINUTES/RESEND_COOLDOWN_SECONDS constants, different purpose) — see
test_forgot_reset_password.py for the sibling flow's coverage.

Skips (not fails) if no database is reachable.
"""
import hashlib
import os
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time

from app.db.connection import connect_db
from app.services.passwords import hash_password

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
    # This flow actually mails an OTP (unlike the old single-step /auth/change-password) —
    # must not depend on .env's live value, same testing standard as
    # test_forgot_reset_password.py and test_patient_email_verification.py.
    os.environ["PATIENT_AUTH_EMAIL_NO_SEND"] = "true"
    from app.api.main import app

    return TestClient(app)


def _otp_hash(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _make_patient(email: str) -> str:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash, email_verified)
                VALUES (%s, %s, TRUE) RETURNING user_id;
                """,
                (email, hash_password(CURRENT_PASSWORD)),
            )
            user_id = str(cur.fetchone()[0])
            cur.execute(
                """
                INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
                VALUES (%s, 'Change PW Test', 30, '+919876500002', '1 Test St', %s, 'O+');
                """,
                (user_id, email),
            )
        conn.commit()
    return user_id


def _cleanup(email: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE email = %s;", (email,))
            cur.execute("DELETE FROM otp_verifications WHERE email = %s AND purpose = 'change_password';", (email,))
        conn.commit()


def _set_known_otp(email: str, otp: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE otp_verifications SET otp_hash = %s WHERE email = %s AND purpose = 'change_password';",
                (_otp_hash(otp), email),
            )
        conn.commit()


def _login(client, email):
    return client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD}).json()["access_token"]


def test_correct_current_password_then_otp_confirm_succeeds_and_new_password_logs_in(client):
    _skip_if_no_database()
    email = f"changepw-success-{uuid.uuid4().hex[:8]}@example.com"
    try:
        _make_patient(email)
        token = _login(client, email)

        start = client.post(
            "/auth/change-password/start",
            json={"current_password": CURRENT_PASSWORD},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert start.status_code == 200
        assert start.json()["status"] == "otp_sent"

        _set_known_otp(email, "111222")
        confirm = client.post(
            "/auth/change-password/confirm",
            json={"otp": "111222", "new_password": "NewStr0ng!Pass", "confirm_password": "NewStr0ng!Pass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert confirm.status_code == 200

        old_password_login = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        assert old_password_login.status_code == 401

        new_password_login = client.post("/auth/login", json={"email": email, "password": "NewStr0ng!Pass"})
        assert new_password_login.status_code == 200
    finally:
        _cleanup(email)


def test_wrong_current_password_at_start_is_rejected_and_no_otp_issued(client):
    _skip_if_no_database()
    email = f"changepw-wrongcurrent-{uuid.uuid4().hex[:8]}@example.com"
    try:
        _make_patient(email)
        token = _login(client, email)

        start = client.post(
            "/auth/change-password/start",
            json={"current_password": "WrongPassword!1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert start.status_code == 401

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM otp_verifications WHERE email = %s AND purpose = 'change_password';",
                    (email,),
                )
                assert cur.fetchone() is None
    finally:
        _cleanup(email)


def test_confirm_with_wrong_otp_is_rejected(client):
    _skip_if_no_database()
    email = f"changepw-wrongotp-{uuid.uuid4().hex[:8]}@example.com"
    try:
        _make_patient(email)
        token = _login(client, email)
        client.post(
            "/auth/change-password/start",
            json={"current_password": CURRENT_PASSWORD},
            headers={"Authorization": f"Bearer {token}"},
        )
        _set_known_otp(email, "333444")

        confirm = client.post(
            "/auth/change-password/confirm",
            json={"otp": "000000", "new_password": "NewStr0ng!Pass", "confirm_password": "NewStr0ng!Pass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert confirm.status_code == 400

        # Password must still be the original.
        still_old = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        assert still_old.status_code == 200
    finally:
        _cleanup(email)


def test_new_password_confirmation_mismatch_is_rejected(client):
    _skip_if_no_database()
    email = f"changepw-mismatch-{uuid.uuid4().hex[:8]}@example.com"
    try:
        _make_patient(email)
        token = _login(client, email)
        client.post(
            "/auth/change-password/start",
            json={"current_password": CURRENT_PASSWORD},
            headers={"Authorization": f"Bearer {token}"},
        )
        _set_known_otp(email, "555666")

        confirm = client.post(
            "/auth/change-password/confirm",
            json={"otp": "555666", "new_password": "NewStr0ng!Pass", "confirm_password": "Different!Pass1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert confirm.status_code == 400
    finally:
        _cleanup(email)


def test_weak_new_password_is_rejected(client):
    _skip_if_no_database()
    email = f"changepw-weak-{uuid.uuid4().hex[:8]}@example.com"
    try:
        _make_patient(email)
        token = _login(client, email)
        client.post(
            "/auth/change-password/start",
            json={"current_password": CURRENT_PASSWORD},
            headers={"Authorization": f"Bearer {token}"},
        )
        _set_known_otp(email, "777888")

        confirm = client.post(
            "/auth/change-password/confirm",
            json={"otp": "777888", "new_password": "weak", "confirm_password": "weak"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert confirm.status_code == 400
    finally:
        _cleanup(email)


def test_token_issued_before_change_is_invalidated_token_issued_after_still_works(client):
    _skip_if_no_database()
    email = f"changepw-invalidate-{uuid.uuid4().hex[:8]}@example.com"
    try:
        _make_patient(email)
        old_token = _login(client, email)

        pre_change = client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"})
        assert pre_change.status_code == 200

        client.post(
            "/auth/change-password/start",
            json={"current_password": CURRENT_PASSWORD},
            headers={"Authorization": f"Bearer {old_token}"},
        )
        _set_known_otp(email, "999000")
        client.post(
            "/auth/change-password/confirm",
            json={"otp": "999000", "new_password": "NewStr0ng!Pass", "confirm_password": "NewStr0ng!Pass"},
            headers={"Authorization": f"Bearer {old_token}"},
        )

        post_change_old_token = client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"})
        assert post_change_old_token.status_code == 401

        new_login = client.post("/auth/login", json={"email": email, "password": "NewStr0ng!Pass"})
        new_token = new_login.json()["access_token"]
        post_change_new_token = client.get("/auth/me", headers={"Authorization": f"Bearer {new_token}"})
        assert post_change_new_token.status_code == 200
    finally:
        _cleanup(email)


def test_resend_cooldown_blocks_then_succeeds_after_via_freezegun(client):
    _skip_if_no_database()
    email = f"changepw-resend-{uuid.uuid4().hex[:8]}@example.com"
    try:
        _make_patient(email)
        token = _login(client, email)
        client.post(
            "/auth/change-password/start",
            json={"current_password": CURRENT_PASSWORD},
            headers={"Authorization": f"Bearer {token}"},
        )

        immediate = client.post("/auth/change-password/resend", headers={"Authorization": f"Bearer {token}"})
        assert immediate.status_code == 200
        body = immediate.json()
        assert body["status"] == "cooldown"
        assert body["retry_after_seconds"] > 0

        frozen_future = datetime.now() + timedelta(seconds=241)
        with freeze_time(frozen_future):
            after_cooldown = client.post("/auth/change-password/resend", headers={"Authorization": f"Bearer {token}"})
        assert after_cooldown.status_code == 200
        assert after_cooldown.json()["status"] == "otp_sent"
    finally:
        _cleanup(email)


def test_old_single_step_route_no_longer_exists(client):
    _skip_if_no_database()
    email = f"changepw-oldroute-{uuid.uuid4().hex[:8]}@example.com"
    try:
        _make_patient(email)
        token = _login(client, email)
        response = client.post(
            "/auth/change-password",
            json={"current_password": CURRENT_PASSWORD, "new_password": "NewStr0ng!Pass", "confirm_password": "NewStr0ng!Pass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
    finally:
        _cleanup(email)


def test_preexisting_account_with_null_password_changed_at_still_logs_in(client):
    """password_changed_at is NULL for every account until it's actually changed —
    confirm current_user's check doesn't misfire against that NULL."""
    _skip_if_no_database()
    email = f"changepw-null-{uuid.uuid4().hex[:8]}@example.com"
    try:
        _make_patient(email)
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT password_changed_at FROM users WHERE email = %s;", (email,))
                assert cur.fetchone()[0] is None

        login = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        assert login.status_code == 200
        token = login.json()["access_token"]
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
    finally:
        _cleanup(email)
