"""Regression coverage for Step 6: admin-assisted MFA reset
(app/services/patient_mfa.py::reset_patient_mfa, POST /admin/patients/{id}/mfa/reset).

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
from app.services.tokens import create_access_token

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


def _make_patient(email: str) -> str:
    with connect_db() as conn:
        ensure_registry_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash, email_verified) VALUES (%s, %s, TRUE) RETURNING user_id;",
                (email, hash_password(CURRENT_PASSWORD)),
            )
            user_id = str(cur.fetchone()[0])
            cur.execute(
                """
                INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
                VALUES (%s, 'Admin Reset Test', 30, '+919876500079', '1 Test St', %s, 'O+');
                """,
                (user_id, email),
            )
            reserve_email(cur, email, "patient", user_id)
        conn.commit()
    return user_id


def _make_admin(email: str) -> str:
    with connect_db() as conn:
        ensure_registry_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO admin_accounts (email, password_hash, name, is_active) VALUES (%s, %s, 'Reset Admin', TRUE) RETURNING admin_id;",
                (email, hash_password(CURRENT_PASSWORD)),
            )
            admin_id = str(cur.fetchone()[0])
            reserve_email(cur, email, "admin", admin_id)
        conn.commit()
    return admin_id


def _cleanup(*emails: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for email in emails:
                cur.execute("DELETE FROM users WHERE email = %s;", (email,))
                cur.execute("DELETE FROM admin_accounts WHERE email = %s;", (email,))
        conn.commit()


def _enroll_mfa(client, patient_token: str, patient_email: str):
    client.post("/auth/mfa/setup/start", headers={"Authorization": f"Bearer {patient_token}"})
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT mfa_secret_encrypted FROM users WHERE email = %s;", (patient_email,))
            encrypted = cur.fetchone()[0]
    secret = totp_module.decrypt_secret(encrypted, _fernet_key())
    code = pyotp.TOTP(secret).now()
    client.post(
        "/auth/mfa/setup/verify", json={"code": code}, headers={"Authorization": f"Bearer {patient_token}"},
    )


def test_admin_reset_works_without_patient_password_or_code(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    patient_email = f"adminreset-patient-{suffix}@example.com"
    admin_email = f"adminreset-admin-{suffix}@example.com"
    try:
        patient_id = _make_patient(patient_email)
        _make_admin(admin_email)

        login = client.post("/auth/login", json={"email": patient_email, "password": CURRENT_PASSWORD})
        patient_token = login.json()["access_token"]
        _enroll_mfa(client, patient_token, patient_email)

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT mfa_enabled FROM users WHERE email = %s;", (patient_email,))
                assert cur.fetchone()[0] is True

        admin_token = create_access_token(subject=patient_id, email=admin_email, role="admin")
        # Note: subject value doesn't matter to current_admin (it keys off the email
        # claim), only role + email + is_active — mirrors test_admin_dependencies.py.
        reset = client.post(
            f"/admin/patients/{patient_id}/mfa/reset",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert reset.status_code == 200
        assert reset.json()["status"] == "mfa_reset"

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT mfa_enabled, mfa_secret_encrypted FROM users WHERE email = %s;", (patient_email,)
                )
                mfa_enabled, mfa_secret = cur.fetchone()
                assert mfa_enabled is False
                assert mfa_secret is None
                cur.execute("SELECT COUNT(*) FROM mfa_backup_codes WHERE user_id = %s;", (patient_id,))
                assert cur.fetchone()[0] == 0
    finally:
        _cleanup(patient_email, admin_email)


def test_admin_reset_is_logged(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    patient_email = f"adminresetlog-patient-{suffix}@example.com"
    admin_email = f"adminresetlog-admin-{suffix}@example.com"
    try:
        patient_id = _make_patient(patient_email)
        _make_admin(admin_email)
        login = client.post("/auth/login", json={"email": patient_email, "password": CURRENT_PASSWORD})
        patient_token = login.json()["access_token"]
        _enroll_mfa(client, patient_token, patient_email)

        admin_token = create_access_token(subject=patient_id, email=admin_email, role="admin")
        client.post(f"/admin/patients/{patient_id}/mfa/reset", headers={"Authorization": f"Bearer {admin_token}"})

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT admin_email, action FROM admin_patient_actions_log WHERE patient_id = %s;",
                    (patient_id,),
                )
                rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == admin_email.lower()
        assert rows[0][1] == "mfa_reset_by_admin"
    finally:
        _cleanup(patient_email, admin_email)


def test_patient_can_login_with_password_alone_and_reenroll_after_reset(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    patient_email = f"adminresetreenroll-patient-{suffix}@example.com"
    admin_email = f"adminresetreenroll-admin-{suffix}@example.com"
    try:
        patient_id = _make_patient(patient_email)
        _make_admin(admin_email)
        login = client.post("/auth/login", json={"email": patient_email, "password": CURRENT_PASSWORD})
        patient_token = login.json()["access_token"]
        _enroll_mfa(client, patient_token, patient_email)

        admin_token = create_access_token(subject=patient_id, email=admin_email, role="admin")
        client.post(f"/admin/patients/{patient_id}/mfa/reset", headers={"Authorization": f"Bearer {admin_token}"})

        relogin = client.post("/auth/login", json={"email": patient_email, "password": CURRENT_PASSWORD})
        assert relogin.status_code == 200
        assert relogin.json()["status"] == "authenticated"

        new_token = relogin.json()["access_token"]
        _enroll_mfa(client, new_token, patient_email)
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT mfa_enabled FROM users WHERE email = %s;", (patient_email,))
                assert cur.fetchone()[0] is True
    finally:
        _cleanup(patient_email, admin_email)


def test_non_admin_token_cannot_call_the_reset_endpoint(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    patient_email = f"adminresetnonadmin-{suffix}@example.com"
    try:
        patient_id = _make_patient(patient_email)
        patient_token = create_access_token(patient_id=patient_id, email=patient_email, role="patient")

        response = client.post(
            f"/admin/patients/{patient_id}/mfa/reset",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 401
    finally:
        _cleanup(patient_email)
