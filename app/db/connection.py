import os
from contextlib import contextmanager
from threading import Lock

from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set in your .env file.")

POOL_MIN_CONNECTIONS = max(1, int(os.getenv("DB_POOL_MIN_CONNECTIONS", "1")))
# 40, with the request threadpool capped BELOW it (DB_HANDLER_THREADS, applied in main.py).
#
# The pool was 10 while FastAPI ran up to 40 sync request handlers at once, and
# ThreadedConnectionPool does not queue: the 11th concurrent request got "connection pool
# exhausted" and a 500 immediately. One doctor opening the workspace fires about eight
# requests in parallel, so two doctors at once was enough — measured: 347 of 600 requests
# failed this way under parallel page loads. The threadpool is capped below the pool so
# excess requests WAIT for a thread instead; the headroom covers callers that take a
# connection outside that threadpool (async handlers, the background overview rebuild, the
# retention sweep). Postgres allows ~97; with more than one server process, workers x this
# must stay under that.
POOL_MAX_CONNECTIONS = max(
    POOL_MIN_CONNECTIONS,
    int(os.getenv("DB_POOL_MAX_CONNECTIONS", "40")),
)
# Sync request handlers that may run at once. Kept below POOL_MAX_CONNECTIONS; see above.
HANDLER_THREADS = max(1, min(
    int(os.getenv("DB_HANDLER_THREADS", "32")),
    POOL_MAX_CONNECTIONS - 4,
))

_pool: ThreadedConnectionPool | None = None
_pool_lock = Lock()


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ThreadedConnectionPool(
                    POOL_MIN_CONNECTIONS,
                    POOL_MAX_CONNECTIONS,
                    dsn=DATABASE_URL,
                )
    return _pool


@contextmanager
def connect_db():
    """Borrow a PostgreSQL connection and return it to the pool after use.

    DANGER — do not call this (directly or via a function that calls it) from *inside*
    an already-open `with connect_db() as conn:` block on the same thread.
    `ThreadedConnectionPool.getconn()` (called here with no explicit key) keys checked-out
    connections by the current thread id, so a nested call on the same thread returns the
    SAME physical connection as the outer one. That nested call's own exit then commits
    and returns the connection to the pool while the outer block still believes it owns
    an open transaction — this has already happened once (see TECH_DEBT.md item 5) and
    left a connection stuck 'idle in transaction', deadlocking every later
    `CREATE INDEX IF NOT EXISTS` in an `ensure_*_schema()` call. If you need to check
    something mid-transaction, query it with the cursor you already have — never open a
    second `connect_db()`."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        if conn.closed:
            pool.putconn(conn, close=True)
            conn = pool.getconn()
        yield conn
        if not conn.closed:
            conn.commit()
    except Exception:
        if not conn.closed:
            conn.rollback()
        raise
    finally:
        if not conn.closed:
            pool.putconn(conn)
        else:
            pool.putconn(conn, close=True)


def close_db_pool() -> None:
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.closeall()
            _pool = None
