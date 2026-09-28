"""Run each ensure_*_schema() at most once per process.

THE PROBLEM. Twenty-one ensure_*_schema() functions are called from 174 places, most of them
at the top of ordinary request handlers. Each runs DDL — CREATE TABLE IF NOT EXISTS,
ALTER TABLE ... ADD COLUMN IF NOT EXISTS, ALTER COLUMN ... SET DEFAULT, CREATE INDEX IF NOT
EXISTS — and that DDL takes heavy locks even when there is nothing to change: ALTER TABLE
takes an AccessExclusiveLock, CREATE INDEX a ShareLock. Two requests arriving together, one
inside its schema checks and one reading, lock the same tables in opposite orders and
Postgres kills one of them:

    psycopg2.errors.DeadlockDetected: deadlock detected
    Process A waits for AccessShareLock on relation appointment_bookings; blocked by B.
    Process B waits for AccessExclusiveLock on relation consultations; blocked by A.

That was the 500 behind "things on the patient page sometimes don't load", and behind the
empty timeline filters: the doctor workspace loads several panels in parallel, so every
page open was a chance to collide. Seen in the running app on activity-log, reviews,
timeline filters and the visit brief.

THE FIX. The schema is already applied by `alembic upgrade head` before the server starts
(docker-entrypoint.sh), so after the first run in a process these calls change nothing — they
only take locks. Each is wrapped so it runs once per process, and main.py's lifespan runs
all of them once, in their own committed transaction, before the server accepts requests.
In a running server, no request runs DDL at all.

Marked done only after the function returns without raising. A test process (no lifespan)
runs each once on first use, against a database migrations have already built.
"""
from __future__ import annotations

import functools

_done: set[str] = set()


def once_per_process(fn):
    key = f"{fn.__module__}.{fn.__qualname__}"

    @functools.wraps(fn)
    def wrapper(conn, *args, **kwargs):
        if key in _done:
            return None
        result = fn(conn, *args, **kwargs)
        _done.add(key)
        return result

    wrapper.schema_key = key
    wrapper.run_again = fn  # the unwrapped function, for the rare caller that must re-run it
    return wrapper


def is_done(fn) -> bool:
    return getattr(fn, "schema_key", None) in _done


def forget_all() -> None:
    """For tests that need a schema function to run again."""
    _done.clear()
