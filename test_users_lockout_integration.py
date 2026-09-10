"""Integration regression coverage for patient login brute-force lockout
(FULL_SYSTEM_AUDIT.md P0 #4: authenticate_user previously had zero rate limiting
or lockout, unlike doctor/admin login). Requires a real database — the row-locked
failure-counter logic can't be meaningfully verified against a mocked cursor.

Skips (not fails) if no database is reachable, matching
test_admin_doctor_management_integration.py's convention.
"""
import uuid

import pytest

from app.db.connection import connect_db
from app.services.passwords import hash_password
from app.services.users import LOCKOUT_THRESHOLD, authenticate_user, ensure_user_schema


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _seed_user(email: str, password: str) -> str:
    with connect_db() as conn:
        ensure_user_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING user_id;",
                (email, hash_password(password)),
            )
            user_id = str(cur.fetchone()[0])
            cur.execute(
                """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
                   VALUES (%s, 'Regression Test Patient', 30, '1234567890', 'Test Address', %s, 'O+')""",
                (user_id, email),
            )
        conn.commit()
    return user_id


def _delete_user(user_id: str | None):
    if not user_id:
        return
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM patient_profiles WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()


def test_correct_password_succeeds_and_resets_failure_counter():
    _skip_if_no_database()
    email = f"lockout-test-{uuid.uuid4().hex}@example.com"
    user_id = None
    try:
        user_id = _seed_user(email, "CorrectHorse1!")
        profile = authenticate_user(email, "CorrectHorse1!")
        assert profile is not None
        assert profile["login_email"] == email

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT failed_login_attempts, locked_until FROM users WHERE user_id = %s", (user_id,))
                failures, locked_until = cur.fetchone()
        assert failures == 0
        assert locked_until is None
    finally:
        _delete_user(user_id)


def test_wrong_password_returns_none_and_increments_failure_counter():
    _skip_if_no_database()
    email = f"lockout-test-{uuid.uuid4().hex}@example.com"
    user_id = None
    try:
        user_id = _seed_user(email, "CorrectHorse1!")
        assert authenticate_user(email, "WrongPassword1!") is None

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT failed_login_attempts FROM users WHERE user_id = %s", (user_id,))
                failures = cur.fetchone()[0]
        assert failures == 1
    finally:
        _delete_user(user_id)


def test_account_locks_after_threshold_failures_and_rejects_correct_password_while_locked():
    _skip_if_no_database()
    email = f"lockout-test-{uuid.uuid4().hex}@example.com"
    user_id = None
    try:
        user_id = _seed_user(email, "CorrectHorse1!")
        for _ in range(LOCKOUT_THRESHOLD):
            authenticate_user(email, "WrongPassword1!")

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT failed_login_attempts, locked_until FROM users WHERE user_id = %s", (user_id,))
                failures, locked_until = cur.fetchone()
        assert failures == LOCKOUT_THRESHOLD
        assert locked_until is not None

        # Even the correct password is rejected while locked — no account-state leak.
        assert authenticate_user(email, "CorrectHorse1!") is None
    finally:
        _delete_user(user_id)


def test_unknown_email_returns_none_without_error():
    _skip_if_no_database()
    assert authenticate_user(f"no-such-user-{uuid.uuid4().hex}@example.com", "whatever") is None
