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
POOL_MAX_CONNECTIONS = max(
    POOL_MIN_CONNECTIONS,
    int(os.getenv("DB_POOL_MAX_CONNECTIONS", "10")),
)

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
    """Borrow a PostgreSQL connection and return it to the pool after use."""
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
