"""Integration regression coverage for login brute-force lockout
(app/services/login_lockout.py — the shared, escalating, email-keyed store all three
roles authenticate behind).

Requires a real database: the row-locked counter logic can't be meaningfully verified
against a mocked cursor. Skips (not fails) if none is reachable, matching
test_admin_doctor_management_integration.py's convention.
"""
import uuid
from datetime import timedelta

import pytest

from app.db.connection import connect_db
from app.services.login_lockout import (
    ESCALATION_DECAY,
    LOCKOUT_LADDER,
    LOCKOUT_THRESHOLD,
    AccountLockedError,
)
from app.services.passwords import hash_password
from app.services.users import authenticate_user, ensure_user_schema


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


def _delete_user(user_id: str | None, email: str | None = None):
    if not user_id:
        return
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM patient_profiles WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            if email:
                cur.execute("DELETE FROM login_lockouts WHERE email = %s", (email.lower(),))
        conn.commit()


def _lockout_row(email: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT failed_attempts, lockout_count, locked_until FROM login_lockouts WHERE email = %s",
                (email.lower(),),
            )
            return cur.fetchone()


def _backdate_lock(email: str, interval: str):
    """Serve the wait without sleeping through it."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE login_lockouts SET locked_until = NOW() - INTERVAL '{interval}' WHERE email = %s",
                (email.lower(),),
            )
        conn.commit()


def test_correct_password_succeeds_and_clears_lockout_state():
    _skip_if_no_database()
    email = f"lockout-test-{uuid.uuid4().hex}@example.com"
    user_id = None
    try:
        user_id = _seed_user(email, "CorrectHorse1!")
        authenticate_user(email, "WrongPassword1!")
        assert _lockout_row(email) is not None

        profile = authenticate_user(email, "CorrectHorse1!")
        assert profile is not None
        assert profile["login_email"] == email
        # A successful login is one of the four reset conditions — the row goes entirely.
        assert _lockout_row(email) is None
    finally:
        _delete_user(user_id, email)


def test_wrong_password_returns_none_and_increments_failure_counter():
    _skip_if_no_database()
    email = f"lockout-test-{uuid.uuid4().hex}@example.com"
    user_id = None
    try:
        user_id = _seed_user(email, "CorrectHorse1!")
        assert authenticate_user(email, "WrongPassword1!") is None
        assert _lockout_row(email)[0] == 1
    finally:
        _delete_user(user_id, email)


def test_account_locks_after_threshold_and_rejects_correct_password_while_locked():
    _skip_if_no_database()
    email = f"lockout-test-{uuid.uuid4().hex}@example.com"
    user_id = None
    try:
        user_id = _seed_user(email, "CorrectHorse1!")
        for _ in range(LOCKOUT_THRESHOLD):
            authenticate_user(email, "WrongPassword1!")

        failed_attempts, lockout_count, locked_until = _lockout_row(email)
        assert locked_until is not None
        assert lockout_count == 1

        # The correct password is still refused while locked — but now it says so
        # explicitly instead of claiming the password was wrong.
        with pytest.raises(AccountLockedError) as caught:
            authenticate_user(email, "CorrectHorse1!")
        assert caught.value.retry_after_seconds > 0
    finally:
        _delete_user(user_id, email)


def test_unknown_email_locks_out_identically_so_it_cannot_be_enumerated():
    """An address with no account behind it has to lock on exactly the same schedule,
    otherwise the presence of a countdown reveals which emails are registered."""
    _skip_if_no_database()
    email = f"no-such-user-{uuid.uuid4().hex}@example.com"
    try:
        for _ in range(LOCKOUT_THRESHOLD):
            assert authenticate_user(email, "whatever") is None

        failed_attempts, lockout_count, locked_until = _lockout_row(email)
        assert locked_until is not None
        assert lockout_count == 1

        with pytest.raises(AccountLockedError):
            authenticate_user(email, "whatever")
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM login_lockouts WHERE email = %s", (email.lower(),))
            conn.commit()


def test_expired_lockout_starts_over_instead_of_instantly_relocking():
    """Once the window has passed the account gets a full set of attempts again.
    Regression: the counter used to survive the expiry still sitting at the threshold,
    so a single wrong password immediately re-locked for another full duration."""
    _skip_if_no_database()
    email = f"lockout-test-{uuid.uuid4().hex}@example.com"
    user_id = None
    try:
        user_id = _seed_user(email, "CorrectHorse1!")
        for _ in range(LOCKOUT_THRESHOLD):
            authenticate_user(email, "WrongPassword1!")
        _backdate_lock(email, "1 minute")

        assert authenticate_user(email, "WrongPassword1!") is None
        failed_attempts, _, locked_until = _lockout_row(email)
        assert failed_attempts == 1
        assert locked_until is None

        # ...and the correct password works right after that single failure.
        assert authenticate_user(email, "CorrectHorse1!") is not None
    finally:
        _delete_user(user_id, email)


def test_each_further_lockout_climbs_the_ladder_and_stops_at_the_cap():
    _skip_if_no_database()
    email = f"lockout-test-{uuid.uuid4().hex}@example.com"
    user_id = None
    try:
        user_id = _seed_user(email, "CorrectHorse1!")
        for expected_rung, expected_duration in enumerate(LOCKOUT_LADDER):
            for _ in range(LOCKOUT_THRESHOLD):
                authenticate_user(email, "WrongPassword1!")

            _, lockout_count, locked_until = _lockout_row(email)
            assert lockout_count == expected_rung + 1
            with pytest.raises(AccountLockedError) as caught:
                authenticate_user(email, "WrongPassword1!")
            # Allow a few seconds of slack for the time the calls themselves took.
            assert abs(caught.value.retry_after_seconds - expected_duration.total_seconds()) < 60
            _backdate_lock(email, "1 second")

        # One rung past the end of the ladder stays at the cap rather than growing.
        for _ in range(LOCKOUT_THRESHOLD):
            authenticate_user(email, "WrongPassword1!")
        with pytest.raises(AccountLockedError) as caught:
            authenticate_user(email, "WrongPassword1!")
        assert abs(caught.value.retry_after_seconds - LOCKOUT_LADDER[-1].total_seconds()) < 60
    finally:
        _delete_user(user_id, email)


def test_escalation_decays_after_a_quiet_period():
    """Fumbles months apart must not stack — otherwise escalation is permanent."""
    _skip_if_no_database()
    email = f"lockout-test-{uuid.uuid4().hex}@example.com"
    user_id = None
    try:
        user_id = _seed_user(email, "CorrectHorse1!")
        for _ in range(LOCKOUT_THRESHOLD):
            authenticate_user(email, "WrongPassword1!")
        assert _lockout_row(email)[1] == 1

        # Backdate both the lock and the last failure beyond the decay window.
        stale = int(ESCALATION_DECAY.total_seconds()) + 3600
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""UPDATE login_lockouts
                        SET locked_until = NOW() - INTERVAL '{stale} seconds',
                            last_failed_at = NOW() - INTERVAL '{stale} seconds'
                        WHERE email = %s""",
                    (email.lower(),),
                )
            conn.commit()

        for _ in range(LOCKOUT_THRESHOLD):
            authenticate_user(email, "WrongPassword1!")

        # Back at rung one, so the duration is the bottom of the ladder again.
        _, lockout_count, _ = _lockout_row(email)
        assert lockout_count == 1
        with pytest.raises(AccountLockedError) as caught:
            authenticate_user(email, "CorrectHorse1!")
        assert abs(caught.value.retry_after_seconds - LOCKOUT_LADDER[0].total_seconds()) < 60
    finally:
        _delete_user(user_id, email)
