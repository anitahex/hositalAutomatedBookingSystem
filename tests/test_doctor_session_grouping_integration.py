"""Whether a login starts a new "visit" — against the real UPDATE.

THE INCIDENT. doctor_accounts.previous_login_at is the lower bound of the overview's
"AI activity · since your last visit" window. Both login branches advanced it on EVERY
login, so a doctor who signed out and back in set that bound to moments ago and the whole
panel read as 0. Observed live: previous_login_at 15:24:56 against last_login_at 15:27:36.

The fix is doctor_auth.SESSION_GROUPING_MINUTES — a login within that gap is the same
visit and must not advance the bound.

Why these run against a real database: the rule lives entirely in SQL
(_ADVANCE_LOGIN_WINDOW_SQL), evaluated by Postgres against its own clock and against the
pre-UPDATE row. Reimplementing that in Python would test a different expression than the
one that runs.

Only the TOTP verification itself is stubbed — that algorithm has its own tests, and
driving it here would mean fighting the replay guard and the 30-second step window. Every
statement that touches doctor_accounts is the real one.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services import doctor_auth


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


@pytest.fixture
def _stub_totp(monkeypatch):
    """Makes any code verify, so the real UPDATE below is what is being tested."""
    monkeypatch.setattr(doctor_auth, "_fernet_key", lambda: "unused-by-the-stub")
    monkeypatch.setattr(doctor_auth.totp, "decrypt_secret", lambda value, key: "SECRET")
    monkeypatch.setattr(
        doctor_auth.totp, "verify_totp", lambda secret, code, last_step, **kw: 12345
    )


def _make_account(cur, email, last_login_at, previous_login_at):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
        (f"Session {email}", "Testing", 1),
    )
    doctor_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO doctor_accounts (doctor_id, email, hashed_password, is_active,
                                        mfa_enabled, totp_secret, last_login_at,
                                        previous_login_at)
           VALUES (%s, %s, 'x', TRUE, TRUE, 'encrypted', %s, %s) RETURNING id""",
        (doctor_id, email, last_login_at, previous_login_at),
    )
    return doctor_id, str(cur.fetchone()[0])


def _login_window(account_id):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT previous_login_at, last_login_at FROM doctor_accounts WHERE id = %s",
                (account_id,),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def _cleanup(doctor_id):
    with connect_db() as conn:
        with conn.cursor() as cur:
            if doctor_id:
                cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        conn.commit()


def _run_login(email, last_login_at, previous_login_at):
    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id, account_id = _make_account(
                    cur, email, last_login_at, previous_login_at
                )
            conn.commit()
        doctor_auth.complete_mfa_challenge(account_id, "000000")
        return _login_window(account_id)
    finally:
        _cleanup(doctor_id)


# ---- the incident ----

def test_signing_back_in_minutes_later_does_not_destroy_the_window(_stub_totp):
    """The reported bug, with the live numbers as the fixture: last login 2m40s ago. The
    old code moved previous_login_at to that, leaving a 2m40s activity window."""
    _skip_if_no_database()
    real_previous = (datetime.now() - timedelta(hours=6)).replace(microsecond=0)

    previous_after, last_after = _run_login(
        "session-quick@example.com",
        last_login_at=datetime.now() - timedelta(minutes=2, seconds=40),
        previous_login_at=real_previous,
    )

    assert previous_after == real_previous, "a re-login inside the session gap moved the window"
    assert last_after > real_previous, "last_login_at must still advance on every login"


def test_coming_back_after_a_real_absence_does_advance_the_window(_stub_totp):
    """The other half. If nothing ever advanced it, "since your last visit" would creep
    back forever and eventually report months of activity."""
    _skip_if_no_database()
    previous_login = (datetime.now() - timedelta(hours=9)).replace(microsecond=0)
    last_login = (datetime.now() - timedelta(minutes=45)).replace(microsecond=0)

    previous_after, _ = _run_login(
        "session-real@example.com",
        last_login_at=last_login,
        previous_login_at=previous_login,
    )

    assert previous_after == last_login


@pytest.mark.parametrize(
    "minutes_ago,should_advance",
    [
        (doctor_auth.SESSION_GROUPING_MINUTES - 5, False),
        (doctor_auth.SESSION_GROUPING_MINUTES + 5, True),
    ],
)
def test_the_boundary_is_the_named_constant(_stub_totp, minutes_ago, should_advance):
    """Pins the behaviour to SESSION_GROUPING_MINUTES rather than to the number 30, so
    changing the constant changes the rule and does not just break this test."""
    _skip_if_no_database()
    previous_login = (datetime.now() - timedelta(hours=9)).replace(microsecond=0)
    last_login = (datetime.now() - timedelta(minutes=minutes_ago)).replace(microsecond=0)

    previous_after, _ = _run_login(
        f"session-boundary-{minutes_ago}@example.com",
        last_login_at=last_login,
        previous_login_at=previous_login,
    )

    assert (previous_after == last_login) is should_advance


def test_a_first_ever_login_leaves_the_window_unset(_stub_totp):
    """NULL is a real state — "no previous visit" — and the summary turns it into the 24h
    fallback. Coalescing it to NOW() here would silently make every new doctor's first
    session report zero activity."""
    _skip_if_no_database()

    previous_after, last_after = _run_login(
        "session-first@example.com", last_login_at=None, previous_login_at=None
    )

    assert previous_after is None
    assert last_after is not None


# ---- the two branches cannot drift ----

def test_both_login_branches_use_the_same_carry_forward_sql():
    """A login via recovery code is still a login. These were two hand-written UPDATEs
    that had to stay in agreement; they now share one fragment, and this asserts that
    rather than trusting whoever edits them next to remember."""
    import inspect

    source = inspect.getsource(doctor_auth.complete_mfa_challenge)

    # The interpolation specifically, not the name — prose mentioning it does not count.
    assert source.count("{_ADVANCE_LOGIN_WINDOW_SQL}") == 2
    # And neither branch has quietly grown its own copy of the old unconditional version.
    assert "previous_login_at = last_login_at," not in source
