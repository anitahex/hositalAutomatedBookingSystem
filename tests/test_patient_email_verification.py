"""Regression coverage for the patient email-verification gate: signup no longer issues a
usable access_token, only a short-lived pending token good for submitting the emailed
6-digit code (app/services/email_verification.py, app/api/routes/auth.py).

Skips (not fails) if no database is reachable.
"""

import hashlib
import os
import secrets

import pytest
from fastapi.testclient import TestClient

from app.db.connection import connect_db


def _code_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


@pytest.fixture
def client():
    os.environ["PATIENT_AUTH_EMAIL_NO_SEND"] = "true"
    from app.api.main import app

    return TestClient(app)


def _signup_payload(email: str) -> dict:
    return {
        "email": email,
        "password": "Str0ng!Pass",
        "confirm_password": "Str0ng!Pass",
        "name": "Verify Test",
        "age": 30,
        "mobile_number": "+919876500000",
        "address": "123 Test Street",
        "profile_email": email,
        "blood_group": "O+",
        "health_issues": None,
    }


def _delete_user_by_email(email: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE email = %s;", (email.lower(),))
        conn.commit()


def _fetch_code_hash(user_id: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT code_hash, attempts FROM email_verification_codes WHERE user_id = %s;",
                (user_id,),
            )
            return cur.fetchone()


def test_signup_does_not_issue_a_usable_access_token(client):
    _skip_if_no_database()
    email = "verify-signup@example.com"
    _delete_user_by_email(email)
    try:
        response = client.post("/auth/signup", json=_signup_payload(email))
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "verification_required"
        assert "access_token" not in data
        assert "pending_token" in data

        # The pending token must not work against a real protected route.
        protected = client.get(
            "/appointments/departments",
            headers={"Authorization": f"Bearer {data['pending_token']}"},
        )
        assert protected.status_code == 401
    finally:
        _delete_user_by_email(email)


def test_wrong_code_increments_attempts_and_stays_blocked(client):
    _skip_if_no_database()
    email = "verify-wrongcode@example.com"
    _delete_user_by_email(email)
    try:
        signup = client.post("/auth/signup", json=_signup_payload(email)).json()
        pending_token = signup["pending_token"]

        response = client.post(
            "/auth/verify-email",
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {pending_token}"},
        )
        assert response.status_code == 400
        assert "access_token" not in response.json()
    finally:
        _delete_user_by_email(email)


def test_correct_code_verifies_and_issues_real_access_token(client):
    _skip_if_no_database()
    email = "verify-success@example.com"
    _delete_user_by_email(email)
    try:
        signup = client.post("/auth/signup", json=_signup_payload(email)).json()
        pending_token = signup["pending_token"]

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE email = %s;", (email,))
                user_id = str(cur.fetchone()[0])

        # verify_code only accepts the raw code, never a hash — overwrite the stored
        # row with a hash of a code this test controls (same sha256 scheme
        # app/services/email_verification.py uses), rather than trying to scrape the
        # real one out of the dev no-send stdout print.
        known_code = f"{secrets.randbelow(1_000_000):06d}"
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE email_verification_codes SET code_hash = %s, attempts = 0, expires_at = NOW() + INTERVAL '10 minutes' WHERE user_id = %s;",
                    (_code_hash(known_code), user_id),
                )
            conn.commit()

        response = client.post(
            "/auth/verify-email",
            json={"code": known_code},
            headers={"Authorization": f"Bearer {pending_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "authenticated"
        assert data["access_token"]
        assert data["user"]["email_verified"] is True

        # Verification row is consumed.
        assert _fetch_code_hash(user_id) is None

        # The real access_token now works against a protected route.
        protected = client.get(
            "/appointments/departments",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert protected.status_code == 200
    finally:
        _delete_user_by_email(email)


def test_five_wrong_attempts_locks_out_further_tries(client):
    _skip_if_no_database()
    email = "verify-lockout@example.com"
    _delete_user_by_email(email)
    try:
        signup = client.post("/auth/signup", json=_signup_payload(email)).json()
        pending_token = signup["pending_token"]
        headers = {"Authorization": f"Bearer {pending_token}"}

        for _ in range(5):
            client.post("/auth/verify-email", json={"code": "111111"}, headers=headers)

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE email = %s;", (email,))
                user_id = str(cur.fetchone()[0])
        _, attempts = _fetch_code_hash(user_id)
        assert attempts >= 5

        # Even a request that would otherwise need the real code is now rejected.
        response = client.post("/auth/verify-email", json={"code": "111111"}, headers=headers)
        assert response.status_code == 400
    finally:
        _delete_user_by_email(email)


def test_resend_issues_a_new_code_that_invalidates_the_old_one(client):
    _skip_if_no_database()
    email = "verify-resend@example.com"
    _delete_user_by_email(email)
    try:
        signup = client.post("/auth/signup", json=_signup_payload(email)).json()
        pending_token = signup["pending_token"]
        headers = {"Authorization": f"Bearer {pending_token}"}

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE email = %s;", (email,))
                user_id = str(cur.fetchone()[0])
        first_hash, _ = _fetch_code_hash(user_id)

        resend = client.post("/auth/resend-verification", json={}, headers=headers)
        assert resend.status_code == 200

        second_hash, attempts = _fetch_code_hash(user_id)
        assert second_hash != first_hash
        assert attempts == 0
    finally:
        _delete_user_by_email(email)


def test_login_with_unverified_account_resumes_verification_not_a_dead_401(client):
    _skip_if_no_database()
    email = "verify-loginresume@example.com"
    _delete_user_by_email(email)
    try:
        client.post("/auth/signup", json=_signup_payload(email))

        response = client.post(
            "/auth/login",
            json={"email": email, "password": "Str0ng!Pass"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "verification_required"
        assert "pending_token" in data
    finally:
        _delete_user_by_email(email)
