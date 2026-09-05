from contextlib import contextmanager

import pytest

from app.services import admin_auth


class _Cursor:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        if "SELECT admin_id" in self.calls[-1][0]:
            return ("00000000-0000-0000-0000-000000000001",)
        if "RETURNING email" in self.calls[-1][0]:
            return ("admin@example.com",)
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Connection:
    def __init__(self):
        self.cursor_instance = _Cursor()

    def cursor(self):
        return self.cursor_instance


def test_admin_bootstrap_is_opt_in(monkeypatch):
    monkeypatch.setenv("ADMIN_BOOTSTRAP_ENABLED", "false")
    assert admin_auth.bootstrap_admin_from_env() is False


def test_admin_bootstrap_requires_credentials(monkeypatch):
    monkeypatch.setenv("ADMIN_BOOTSTRAP_ENABLED", "true")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="ADMIN_EMAIL"):
        admin_auth.bootstrap_admin_from_env()


def test_admin_bootstrap_upserts_configured_account(monkeypatch):
    connection = _Connection()

    @contextmanager
    def fake_connect_db():
        yield connection

    monkeypatch.setenv("ADMIN_BOOTSTRAP_ENABLED", "true")
    monkeypatch.setenv("ADMIN_EMAIL", " Admin@Example.com ")
    monkeypatch.setenv("ADMIN_PASSWORD", "StrongPass1!")
    monkeypatch.setenv("ADMIN_NAME", "Hospital Admin")
    monkeypatch.setattr(admin_auth, "connect_db", fake_connect_db)
    monkeypatch.setattr(admin_auth, "ensure_admin_schema", lambda conn: None)

    assert admin_auth.bootstrap_admin_from_env() is True
    sql, values = next(
        call for call in connection.cursor_instance.calls if "INSERT INTO admin_accounts" in call[0]
    )
    assert "ON CONFLICT (email)" in sql
    assert values[0] == "admin@example.com"
    assert values[2] == "Hospital Admin"
    assert values[1] != "StrongPass1!"
