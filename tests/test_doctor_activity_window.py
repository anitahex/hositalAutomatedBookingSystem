"""Which period the doctor's AI activity counts cover.

THE INCIDENT. The overview's "AI activity · since your last visit" panel read as blank —
every tile 0 — while the doctor had plenty of recent activity. It was not a load failure:
the window itself was three minutes wide. `previous_login_at` was advanced on EVERY login,
so signing out and straight back in set the lower bound to moments ago, and nothing had
happened inside it. Verified in the running database: previous_login_at 15:24:56 against
last_login_at 15:27:36, a 2m40s window, while the same account's 24h window held 2 drafted
notes and 2 summarised documents.

Two independent guards, both needed:

  1. doctor_auth.SESSION_GROUPING_MINUTES stops the window being destroyed in the first
     place — a re-login inside that gap is the same visit and does not advance the bound.
     Covered against real SQL in test_doctor_session_grouping_integration.py.
  2. doctor_ai_activity.MIN_LAST_VISIT_MINUTES is the read-side floor, covered here. It
     also protects rows written before guard 1 existed.

These use a real database because the window is resolved by Postgres against its own
clock — computing it in Python would test a different expression than the one that runs.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services import doctor_auth
from app.services.doctor_ai_activity import (
    ACTIVITY_WINDOWS,
    DEFAULT_WINDOW,
    MIN_LAST_VISIT_MINUTES,
    WINDOW_LAST_VISIT,
    get_activity_summary,
)


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _make_doctor_with_account(cur, name, email, previous_login_at):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
        (name, "Testing", 1),
    )
    doctor_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO doctor_accounts (doctor_id, email, hashed_password, is_active,
                                        mfa_enabled, previous_login_at)
           VALUES (%s, %s, 'x', TRUE, TRUE, %s) RETURNING id""",
        (doctor_id, email, previous_login_at),
    )
    return doctor_id, str(cur.fetchone()[0])


def _cleanup(doctor_ids):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for doctor_id in doctor_ids:
                if doctor_id:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        conn.commit()


# ---- the two guards agree on what a visit is ----

def test_the_read_floor_and_the_login_grouping_use_the_same_visit_boundary():
    """Two numbers defining one concept drift apart the moment they are allowed to. A gap
    too short to START a new visit must also be too short to REPORT one, or a re-login can
    still produce a window the read side is willing to serve."""
    assert MIN_LAST_VISIT_MINUTES == doctor_auth.SESSION_GROUPING_MINUTES


def test_the_default_window_is_the_last_visit():
    assert DEFAULT_WINDOW == WINDOW_LAST_VISIT
    assert ACTIVITY_WINDOWS == ("last_visit", "24h", "7d")


# ---- the incident ----

def test_a_last_visit_window_narrower_than_a_session_falls_back_to_24h():
    """The reported bug. previous_login_at 2m40s ago is not a visit — it is the same
    person signing back in — and reporting a 2m40s window makes the panel read as blank."""
    _skip_if_no_database()
    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id, account_id = _make_doctor_with_account(
                    cur, "Window Narrow", "window-narrow@example.com",
                    datetime.now() - timedelta(minutes=2, seconds=40),
                )
            conn.commit()

        summary = get_activity_summary(doctor_id, account_id, WINDOW_LAST_VISIT)

        assert summary["window_requested"] == WINDOW_LAST_VISIT
        assert summary["window"] == "24h"
        assert summary["window_is_fallback"] is True
    finally:
        _cleanup((doctor_id,))


def test_a_genuine_last_visit_is_used_as_the_lower_bound():
    """The other half: a real absence must NOT be widened to 24h, or "since your last
    visit" would silently become "since yesterday"."""
    _skip_if_no_database()
    doctor_id = None
    previous_login = (datetime.now() - timedelta(hours=6)).replace(microsecond=0)
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id, account_id = _make_doctor_with_account(
                    cur, "Window Real", "window-real@example.com", previous_login,
                )
            conn.commit()

        summary = get_activity_summary(doctor_id, account_id, WINDOW_LAST_VISIT)

        assert summary["window"] == WINDOW_LAST_VISIT
        assert summary["window_is_fallback"] is False
        assert summary["window_start"].startswith(previous_login.isoformat()[:16])
    finally:
        _cleanup((doctor_id,))


def test_an_account_that_has_never_logged_in_before_gets_the_24h_fallback():
    _skip_if_no_database()
    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id, account_id = _make_doctor_with_account(
                    cur, "Window None", "window-none@example.com", None,
                )
            conn.commit()

        summary = get_activity_summary(doctor_id, account_id, WINDOW_LAST_VISIT)

        assert summary["window"] == "24h"
        assert summary["window_is_fallback"] is True
    finally:
        _cleanup((doctor_id,))


# ---- the fixed windows ----

@pytest.mark.parametrize("window,expected_hours", [("24h", 24), ("7d", 24 * 7)])
def test_a_fixed_window_measures_back_from_now(window, expected_hours):
    """And is never reported as a fallback: the doctor asked for it and got it. Saying
    "we could not find your last visit" to someone who chose 24 hours is a lie about why
    they are looking at those numbers."""
    _skip_if_no_database()
    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                # A previous login so recent it would trigger the floor, to prove a fixed
                # window ignores previous_login_at entirely.
                doctor_id, account_id = _make_doctor_with_account(
                    cur, f"Window {window}", f"window-{window}@example.com",
                    datetime.now() - timedelta(minutes=1),
                )
            conn.commit()

        summary = get_activity_summary(doctor_id, account_id, window)

        assert summary["window"] == window
        assert summary["window_is_fallback"] is False
        started = datetime.fromisoformat(summary["window_start"])
        age_hours = (datetime.now() - started).total_seconds() / 3600
        assert expected_hours - 1 < age_hours < expected_hours + 1
    finally:
        _cleanup((doctor_id,))


def test_an_unknown_window_is_rejected_rather_than_quietly_defaulted():
    """A typo in a caller must not silently change what a clinical figure counts."""
    with pytest.raises(ValueError):
        get_activity_summary("some-doctor", "some-account", "last_week")


# ---- what the window does and does not move ----

def test_current_state_counts_are_identical_in_every_window():
    """notes_blocked and awaiting_signature answer "what is stuck right now", not "what
    happened in this period". If the window moved them, the tiles beside them would be
    measuring two different things under one heading."""
    _skip_if_no_database()
    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id, account_id = _make_doctor_with_account(
                    cur, "Window State", "window-state@example.com",
                    datetime.now() - timedelta(hours=3),
                )
            conn.commit()

        summaries = [
            get_activity_summary(doctor_id, account_id, window) for window in ACTIVITY_WINDOWS
        ]
        blocked = {s["counts"]["notes_blocked"] for s in summaries}
        awaiting = {s["counts"]["awaiting_signature"] for s in summaries}

        assert len(blocked) == 1
        assert len(awaiting) == 1
    finally:
        _cleanup((doctor_id,))
