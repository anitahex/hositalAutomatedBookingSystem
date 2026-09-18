"""Shared pytest fixtures.

Autouse: clears the Postgres-backed rate limiter (app/services/doctor_auth.py::
check_rate_limit) before every test. That limiter is intentionally shared/global —
correct across multiple app workers/replicas in production — which means its state
also persists across the whole pytest session. Without this, a test late in the run
can start already over some scope's limit (login, signup, patient_mfa, ...) purely
because of how many earlier tests, possibly in other files, happened to hit the same
scope from the shared TestClient IP. Skips silently if no database is reachable —
the individual tests' own _skip_if_no_database() guards handle that case.
"""
import pytest

from app.db.connection import connect_db
from app.services.doctor_auth import ensure_rate_limit_schema


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    try:
        with connect_db() as conn:
            ensure_rate_limit_schema(conn)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM rate_limit_events;")
            conn.commit()
    except Exception:
        pass
    yield
