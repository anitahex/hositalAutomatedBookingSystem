from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.api.routes import admin as admin_route
from app.services import admin_management, doctor_auth


class _Cursor:
    def __init__(self, fetchone_by_marker=None):
        self.calls = []
        self._fetchone_by_marker = fetchone_by_marker or {}

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        sql, _ = self.calls[-1]
        for marker, value in self._fetchone_by_marker.items():
            if marker in sql:
                return value
        return None

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Connection:
    def __init__(self, fetchone_by_marker=None):
        self.cursor_instance = _Cursor(fetchone_by_marker)
        self.committed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True


def _admin():
    return {"role": "admin", "email": "admin@example.com", "name": "Admin"}


# ── _derive_doctor_login_status precedence ──────────────────────────────────

def test_login_status_not_invited_when_no_account():
    status, action = admin_management._derive_doctor_login_status(None, None, None, None)
    assert (status, action) == ("not_invited", "invite")


def test_login_status_invited_when_account_not_active():
    status, action = admin_management._derive_doctor_login_status("acct-1", False, False, None)
    assert (status, action) == ("invited", "resend")


def test_login_status_active_when_active_and_mfa_not_enabled():
    status, action = admin_management._derive_doctor_login_status("acct-1", True, False, None)
    assert (status, action) == ("active", "reset")


def test_login_status_mfa_enrolled_when_mfa_enabled():
    status, action = admin_management._derive_doctor_login_status("acct-1", True, True, None)
    assert (status, action) == ("mfa_enrolled", "reset")


def test_login_status_locked_takes_precedence_over_mfa_enrolled():
    future = datetime.now() + timedelta(minutes=10)
    status, action = admin_management._derive_doctor_login_status("acct-1", True, True, future)
    assert (status, action) == ("locked", "reset")


def test_login_status_locked_even_when_account_not_yet_active():
    # authenticate_doctor_password can lock an account before is_active is ever true.
    future = datetime.now() + timedelta(minutes=10)
    status, action = admin_management._derive_doctor_login_status("acct-1", False, False, future)
    assert (status, action) == ("locked", "reset")


def test_login_status_expired_lock_does_not_count_as_locked():
    past = datetime.now() - timedelta(minutes=10)
    status, action = admin_management._derive_doctor_login_status("acct-1", True, False, past)
    assert (status, action) == ("active", "reset")


# ── unlock_doctor_account ────────────────────────────────────────────────────

def test_unlock_doctor_account_clears_lock_and_audits(monkeypatch):
    connection = _Connection(fetchone_by_marker={
        "SELECT id, email": ("account-1", "doctor@example.com"),
        "SELECT failed_attempts": (5,),
    })

    @contextmanager
    def fake_connect_db():
        yield connection

    monkeypatch.setattr(doctor_auth, "connect_db", fake_connect_db)
    monkeypatch.setattr(doctor_auth, "ensure_doctor_auth_schema", lambda conn: None)
    monkeypatch.setattr(doctor_auth, "ensure_lockout_schema", lambda conn: None)

    doctor_auth.unlock_doctor_account("doctor-1", actor_email="Admin@Example.com")

    # Lockout state lives in the shared login_lockouts table now, not on the account row.
    delete_call = next(call for call in connection.cursor_instance.calls if "DELETE FROM login_lockouts" in call[0])
    assert delete_call[1] == ("doctor@example.com",)

    audit_call = next(call for call in connection.cursor_instance.calls if "INSERT INTO doctor_auth_audit_log" in call[0])
    sql, params = audit_call
    assert params[2] == "account_unlocked_by_admin"
    import json
    metadata = json.loads(params[3])
    assert metadata["admin_email"] == "admin@example.com"
    assert metadata["had_failed_attempts"] == 5
    assert connection.committed is True


def test_unlock_doctor_account_missing_account_raises(monkeypatch):
    connection = _Connection(fetchone_by_marker={})

    @contextmanager
    def fake_connect_db():
        yield connection

    monkeypatch.setattr(doctor_auth, "connect_db", fake_connect_db)
    monkeypatch.setattr(doctor_auth, "ensure_doctor_auth_schema", lambda conn: None)

    with pytest.raises(ValueError):
        doctor_auth.unlock_doctor_account("doctor-1", actor_email="admin@example.com")


# ── list_doctor_auth_audit_log ──────────────────────────────────────────────

def test_list_doctor_auth_audit_log_never_selects_star(monkeypatch):
    connection = _Connection(fetchone_by_marker={"SELECT COUNT(*)": (0,)})

    @contextmanager
    def fake_connect_db():
        yield connection

    monkeypatch.setattr(doctor_auth, "connect_db", fake_connect_db)
    monkeypatch.setattr(doctor_auth, "ensure_doctor_auth_schema", lambda conn: None)

    result = doctor_auth.list_doctor_auth_audit_log(page=1, page_size=10)

    for sql, _ in connection.cursor_instance.calls:
        assert "SELECT *" not in sql
    assert result == {"entries": [], "total": 0, "page": 1, "page_size": 10}


def test_list_doctor_auth_audit_log_entry_shape_excludes_secrets(monkeypatch):
    row = (
        "audit-1", "doctor-1", "doctor@example.com", "recovery_code_used",
        {"recovery_code": True}, datetime(2026, 1, 1, 12, 0, 0),
    )

    class _RowCursor(_Cursor):
        def fetchone(self):
            sql, _ = self.calls[-1]
            if "SELECT COUNT(*)" in sql:
                return (1,)
            return None

        def fetchall(self):
            return [row]

    class _RowConnection(_Connection):
        def __init__(self):
            self.cursor_instance = _RowCursor()
            self.committed = False

    connection = _RowConnection()

    @contextmanager
    def fake_connect_db():
        yield connection

    monkeypatch.setattr(doctor_auth, "connect_db", fake_connect_db)
    monkeypatch.setattr(doctor_auth, "ensure_doctor_auth_schema", lambda conn: None)

    result = doctor_auth.list_doctor_auth_audit_log(doctor_id="doctor-1")
    assert result["total"] == 1
    entry = result["entries"][0]
    assert set(entry.keys()) == {"audit_id", "doctor_id", "attempted_email", "action_type", "metadata", "created_at"}
    assert "token" not in str(entry).lower()
    assert "password" not in str(entry).lower()
    assert "secret" not in str(entry).lower()


# ── Route-level: non-admin rejection is enforced by current_admin (Depends) ──
# (current_admin's own behavior is covered by test_admin_dependencies.py; here
# we only verify the new/extended routes call through to the service layer.)

def test_admin_unlock_doctor_route_success(monkeypatch):
    monkeypatch.setattr(admin_route, "unlock_doctor_account", lambda doctor_id, actor_email: None)
    response = admin_route.admin_unlock_doctor("doctor-1", admin=_admin())
    assert response == {"status": "unlocked"}


def test_admin_unlock_doctor_route_missing_account(monkeypatch):
    def fail(doctor_id, actor_email):
        raise ValueError("Doctor account not found.")

    monkeypatch.setattr(admin_route, "unlock_doctor_account", fail)
    with pytest.raises(HTTPException) as exc:
        admin_route.admin_unlock_doctor("doctor-1", admin=_admin())
    assert exc.value.status_code == 404


def test_admin_doctor_auth_audit_log_route_delegates(monkeypatch):
    captured = {}

    def fake_list(**kwargs):
        captured.update(kwargs)
        return {"entries": [], "total": 0, "page": 1, "page_size": 50}

    monkeypatch.setattr(admin_route, "list_doctor_auth_audit_log", fake_list)
    response = admin_route.admin_doctor_auth_audit_log(admin=_admin(), doctor_id="doctor-1")
    assert response == {"entries": [], "total": 0, "page": 1, "page_size": 50}
    assert captured["doctor_id"] == "doctor-1"


def test_admin_doctors_route_returns_login_status_fields(monkeypatch):
    doctor_payload = {
        "doctor_id": "doctor-1", "name": "Dr. Test", "department": "Cardiology",
        "experience_years": 5, "is_active": True, "total_slots": 0, "available_slots": 0,
        "next_available_time": None, "holiday_count": 0,
        "account_id": "account-1", "account_email": "doctor@example.com",
        "mfa_enabled": True, "login_status": "mfa_enrolled", "invite_action": "reset",
    }
    monkeypatch.setattr(admin_route, "list_doctors", lambda: [doctor_payload])
    response = admin_route.admin_doctors(admin=_admin())
    assert response["doctors"][0]["login_status"] == "mfa_enrolled"
    assert response["doctors"][0]["invite_action"] == "reset"


# ── list_slots ───────────────────────────────────────────────────────────────

def test_list_slots_filters_to_upcoming_by_default(monkeypatch):
    connection = _Connection()

    @contextmanager
    def fake_connect_db():
        yield connection

    monkeypatch.setattr(admin_management, "connect_db", fake_connect_db)
    monkeypatch.setattr(admin_management, "ensure_booking_schema", lambda conn: None)

    admin_management.list_slots()

    query, _ = connection.cursor_instance.calls[-1]
    assert "NOW()" in query, (
        "list_slots() has no upcoming-time filter, so with far more historical than "
        "future slots, 'ORDER BY start_time ASC LIMIT 500' always returns the oldest "
        "rows and the admin Slots panel can never scroll to current availability."
    )
