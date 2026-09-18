"""Regression coverage for the Postgres-backed check_rate_limit
(app/services/doctor_auth.py), replacing the original in-memory implementation so it
stays correct regardless of worker/process count.

Skips (not fails) if no database is reachable.
"""
import threading
import uuid

import pytest

from app.db.connection import connect_db
from app.services.doctor_auth import check_rate_limit


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _cleanup(*keys_prefixes: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for prefix in keys_prefixes:
                cur.execute("DELETE FROM rate_limit_events WHERE rate_key LIKE %s;", (f"{prefix}%",))
        conn.commit()


def test_limit_plus_one_request_is_rejected():
    _skip_if_no_database()
    scope = f"test-scope-{uuid.uuid4().hex[:8]}"
    ip = "203.0.113.10"
    account_key = f"account-{uuid.uuid4().hex[:8]}"
    try:
        for _ in range(5):
            check_rate_limit(scope, ip, account_key, limit=5, window_seconds=3600)
        with pytest.raises(PermissionError):
            check_rate_limit(scope, ip, account_key, limit=5, window_seconds=3600)
    finally:
        _cleanup(f"{scope}:")


def test_aged_window_allows_a_further_request():
    """Simulated by backdating rows directly rather than a real sleep — this repo's
    own testing standard: tests must not depend on wall-clock timing."""
    _skip_if_no_database()
    scope = f"test-aging-{uuid.uuid4().hex[:8]}"
    ip = "203.0.113.11"
    account_key = f"account-{uuid.uuid4().hex[:8]}"
    try:
        for _ in range(5):
            check_rate_limit(scope, ip, account_key, limit=5, window_seconds=300)
        with pytest.raises(PermissionError):
            check_rate_limit(scope, ip, account_key, limit=5, window_seconds=300)

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE rate_limit_events SET occurred_at = NOW() - INTERVAL '400 seconds' WHERE rate_key LIKE %s;",
                    (f"{scope}:%",),
                )
            conn.commit()

        check_rate_limit(scope, ip, account_key, limit=5, window_seconds=300)
    finally:
        _cleanup(f"{scope}:")


def test_ip_and_account_dimensions_are_independently_enforced():
    _skip_if_no_database()
    scope = f"test-dims-{uuid.uuid4().hex[:8]}"
    shared_ip = "203.0.113.12"
    account_a = f"account-a-{uuid.uuid4().hex[:8]}"
    account_b = f"account-b-{uuid.uuid4().hex[:8]}"
    try:
        # Exhaust the IP-scoped bucket via account_a.
        for _ in range(3):
            check_rate_limit(scope, shared_ip, account_a, limit=3, window_seconds=3600)
        # Same IP, different account — the shared IP bucket still blocks it, even
        # though account_b's own bucket is fresh (matches original both-keys-checked
        # behavior).
        with pytest.raises(PermissionError):
            check_rate_limit(scope, shared_ip, account_b, limit=3, window_seconds=3600)
    finally:
        _cleanup(f"{scope}:")


def test_concurrent_requests_never_let_more_than_limit_through():
    _skip_if_no_database()
    scope = f"test-concurrency-{uuid.uuid4().hex[:8]}"
    ip = "203.0.113.13"
    account_key = f"account-{uuid.uuid4().hex[:8]}"
    limit = 5
    # Attempt count deliberately stays within DB_POOL_MAX_CONNECTIONS (default 10,
    # app/db/connection.py) — a thread count exceeding the pool raises PoolError, a
    # different failure mode than the PermissionError this test is actually about.
    attempt_count = 8
    successes = []
    lock = threading.Lock()

    def attempt():
        try:
            check_rate_limit(scope, ip, account_key, limit=limit, window_seconds=3600)
            with lock:
                successes.append(1)
        except PermissionError:
            pass

    try:
        threads = [threading.Thread(target=attempt) for _ in range(attempt_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(successes) == limit
    finally:
        _cleanup(f"{scope}:")
