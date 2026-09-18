"""Shared, escalating brute-force lockout for every login path (patient, doctor, admin).

Keyed on the submitted email rather than on an account row, deliberately: an email with
no account behind it is tracked and locked exactly like a real one, so a caller cannot
tell the two apart by probing. That is only trustworthy because both cases run through
this same code — a parallel "simulate a lockout for unknown emails" branch would drift
out of sync the first time either side changed.

Escalating: each further lockout on the same email climbs one rung of LOCKOUT_LADDER, so
a typo costs five minutes while a script costs an hour. The rung drops back to the bottom
on a successful login, a password reset, an admin unlock, or ESCALATION_DECAY of quiet.

Every function takes a cursor rather than opening its own connection, so the lockout
bookkeeping commits atomically with the caller's own authentication decision — a failure
can never be recorded against an attempt whose transaction later rolls back.
"""
from datetime import datetime, timedelta

LOCKOUT_THRESHOLD = 5

# Rung N is applied to the (N+1)th lockout; the last entry is the cap and repeats
# forever. Chosen so a human fumbling their own password pays minutes, not half an hour.
LOCKOUT_LADDER = (
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(minutes=30),
    timedelta(minutes=60),
)

# Quiet time after the most recent failure that returns the email to the bottom rung.
# Without this, escalation is permanent: five fumbles in January would still be punished
# at the harsher tier in June.
ESCALATION_DECAY = timedelta(hours=24)


class AccountLockedError(PermissionError):
    """Raised instead of a plain auth failure so the caller can report how long is left.

    Subclasses PermissionError so any existing `except PermissionError` handler that
    doesn't care about the distinction still treats it as an auth failure — but routes
    that want to surface the countdown must catch this FIRST, before that broader
    handler, or the 423 degrades back into an indistinguishable 401.
    """

    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Too many failed attempts. Please try again later.")


def ensure_lockout_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS login_lockouts (
                email TEXT PRIMARY KEY,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                lockout_count INTEGER NOT NULL DEFAULT 0,
                locked_until TIMESTAMP,
                last_failed_at TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )


def _normalise(email: str) -> str:
    return (email or "").strip().lower()


def check_lockout(cur, email: str) -> None:
    """Raise AccountLockedError if this email is currently locked out."""
    cur.execute("SELECT locked_until FROM login_lockouts WHERE email = %s;", (_normalise(email),))
    row = cur.fetchone()
    if not row or not row[0]:
        return

    now = datetime.now()
    if row[0] > now:
        # +1 so a partial second never renders as "try again in 0 seconds".
        raise AccountLockedError(int((row[0] - now).total_seconds()) + 1)


def record_failure(cur, email: str) -> None:
    """Count one failed attempt, locking (and escalating) once the threshold is hit."""
    email = _normalise(email)
    now = datetime.now()
    cur.execute(
        """
        SELECT failed_attempts, lockout_count, last_failed_at
        FROM login_lockouts WHERE email = %s FOR UPDATE;
        """,
        (email,),
    )
    row = cur.fetchone()
    attempts, lockout_count, last_failed_at = row if row else (0, 0, None)
    attempts = int(attempts or 0)
    lockout_count = int(lockout_count or 0)

    if last_failed_at and now - last_failed_at >= ESCALATION_DECAY:
        attempts, lockout_count = 0, 0

    attempts += 1
    locked_until = None
    if attempts >= LOCKOUT_THRESHOLD:
        locked_until = now + LOCKOUT_LADDER[min(lockout_count, len(LOCKOUT_LADDER) - 1)]
        lockout_count += 1
        # The lock itself is now the penalty, so the attempt counter starts clean —
        # that is what gives a full set of tries again once the lock expires, instead
        # of a stale counter re-locking on the very next keystroke.
        attempts = 0

    cur.execute(
        """
        INSERT INTO login_lockouts (email, failed_attempts, lockout_count, locked_until, last_failed_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (email) DO UPDATE SET
            failed_attempts = EXCLUDED.failed_attempts,
            lockout_count = EXCLUDED.lockout_count,
            locked_until = EXCLUDED.locked_until,
            last_failed_at = EXCLUDED.last_failed_at,
            updated_at = NOW();
        """,
        (email, attempts, lockout_count, locked_until, now),
    )


def clear_lockout(cur, email: str) -> None:
    """Drop all lockout state for an email — attempts, escalation rung, and any active
    lock. Used by every reset condition: successful login, password reset, admin unlock."""
    cur.execute("DELETE FROM login_lockouts WHERE email = %s;", (_normalise(email),))
