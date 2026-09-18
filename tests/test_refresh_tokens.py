"""Regression coverage for POST /auth/refresh (app/services/refresh_tokens.py):
single-use rotation, expiry, and coverage for both patient and admin sessions.

Skips (not fails) if no database is reachable.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.connection import connect_db
from app.services.passwords import hash_password
from app.services.refresh_tokens import issue_refresh_token


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


def _make_patient(email: str) -> str:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash, email_verified)
                VALUES (%s, %s, TRUE) RETURNING user_id;
                """,
                (email, hash_password("Str0ng!Pass")),
            )
            user_id = str(cur.fetchone()[0])
            cur.execute(
                """
                INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
                VALUES (%s, 'Refresh Test', 30, '+919876500001', '1 Test St', %s, 'O+');
                """,
                (user_id, email),
            )
        conn.commit()
    return user_id


def _make_admin(email: str) -> str:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO admin_accounts (email, password_hash, name, is_active)
                VALUES (%s, %s, 'Refresh Admin', TRUE) RETURNING admin_id;
                """,
                (email, hash_password("Str0ng!Pass")),
            )
            return str(cur.fetchone()[0])


def _cleanup(email: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE email = %s;", (email,))
            cur.execute("DELETE FROM admin_accounts WHERE email = %s;", (email,))
        conn.commit()


def test_patient_refresh_issues_new_access_token_and_rotates(client):
    _skip_if_no_database()
    email = f"refresh-patient-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user_id = _make_patient(email)
        raw = issue_refresh_token(user_id=user_id, role="patient", email=email)

        response = client.post("/auth/refresh", json={"refresh_token": raw})
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["refresh_token"] != raw

        # New access token actually works against a protected route.
        protected = client.get("/appointments/departments", headers={"Authorization": f"Bearer {data['access_token']}"})
        assert protected.status_code == 200

        # The OLD refresh token is now rotated (used) — reusing it must fail.
        reuse = client.post("/auth/refresh", json={"refresh_token": raw})
        assert reuse.status_code == 401
    finally:
        _cleanup(email)


def test_admin_refresh_issues_new_access_token_and_rotates(client):
    _skip_if_no_database()
    email = f"refresh-admin-{uuid.uuid4().hex[:8]}@example.com"
    try:
        admin_id = _make_admin(email)
        raw = issue_refresh_token(user_id=admin_id, role="admin", email=email)

        response = client.post("/auth/refresh", json={"refresh_token": raw})
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"]
        assert data["refresh_token"] != raw

        protected = client.get("/admin/me", headers={"Authorization": f"Bearer {data['access_token']}"})
        assert protected.status_code == 200

        reuse = client.post("/auth/refresh", json={"refresh_token": raw})
        assert reuse.status_code == 401
    finally:
        _cleanup(email)


def test_expired_refresh_token_is_rejected(client):
    _skip_if_no_database()
    email = f"refresh-expired-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user_id = _make_patient(email)
        raw = issue_refresh_token(user_id=user_id, role="patient", email=email)

        import hashlib
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE refresh_tokens SET expires_at = NOW() - INTERVAL '1 day' WHERE token_hash = %s;",
                    (digest,),
                )
            conn.commit()

        response = client.post("/auth/refresh", json={"refresh_token": raw})
        assert response.status_code == 401
    finally:
        _cleanup(email)


def test_unknown_refresh_token_is_rejected(client):
    _skip_if_no_database()
    response = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401
