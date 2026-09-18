from fastapi import HTTPException
import pytest

from app.api import dependencies
from app.db.connection import connect_db
from app.services import tokens


def _skip_if_no_database():
    # verify_access_token checks token revocation (FULL_SYSTEM_AUDIT.md P1 #7), which
    # needs a real database for any token whose signature actually verifies.
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def test_current_admin_requires_credentials():
    with pytest.raises(HTTPException) as exc:
        dependencies.current_admin(None)
    assert exc.value.status_code == 401


def test_current_admin_rejects_doctor_token():
    _skip_if_no_database()
    doctor = tokens.create_doctor_session_token(
        doctor_id="doctor-1", account_id="account-1", email="doctor@example.com"
    )
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=doctor)
    with pytest.raises(HTTPException) as exc:
        dependencies.current_admin(credentials)
    assert exc.value.status_code == 401


def test_current_admin_rejects_patient_token():
    _skip_if_no_database()
    patient = tokens.create_access_token(patient_id="patient-1", email="patient@example.com")
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=patient)
    with pytest.raises(HTTPException) as exc:
        dependencies.current_admin(credentials)
    assert exc.value.status_code == 401


def test_current_admin_rejects_admin_token_for_unknown_account(monkeypatch):
    _skip_if_no_database()
    admin_token = tokens.create_access_token(subject="admin-1", email="admin@example.com", role="admin")
    monkeypatch.setattr(dependencies, "get_admin_account_by_email", lambda email: None)
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=admin_token)
    with pytest.raises(HTTPException) as exc:
        dependencies.current_admin(credentials)
    assert exc.value.status_code == 401
