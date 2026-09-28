"""The ensure_*_schema() functions run once per process, and at startup rather than in requests.

Their DDL takes table locks even when there is nothing to change. Run from request handlers,
two parallel requests deadlocked (DeadlockDetected) and the doctor workspace showed 500s and
empty timeline filters. See app/db/schema_once.py.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from app.db import schema_once
from app.db.schema_once import is_done, once_per_process

ROOT = Path(__file__).resolve().parents[1]
MAIN_PY = ROOT / "app" / "api" / "main.py"


@pytest.fixture
def fresh_registry():
    saved = set(schema_once._done)
    schema_once._done.clear()
    yield
    schema_once._done.clear()
    schema_once._done.update(saved)


def test_runs_once_then_does_nothing(fresh_registry):
    calls = []

    @once_per_process
    def ensure_thing_schema(conn):
        calls.append(conn)

    ensure_thing_schema("first")
    ensure_thing_schema("second")
    assert calls == ["first"]
    assert is_done(ensure_thing_schema)


def test_a_failed_run_is_not_marked_done(fresh_registry):
    """If the DDL raised, the table may not be right yet — the next caller must try again."""
    attempts = []

    @once_per_process
    def ensure_flaky_schema(conn):
        attempts.append(conn)
        if len(attempts) == 1:
            raise RuntimeError("lock timeout")

    with pytest.raises(RuntimeError):
        ensure_flaky_schema("a")
    assert not is_done(ensure_flaky_schema)
    ensure_flaky_schema("b")
    ensure_flaky_schema("c")
    assert attempts == ["a", "b"]


def test_run_again_bypasses_the_memo(fresh_registry):
    calls = []

    @once_per_process
    def ensure_other_schema(conn):
        calls.append(conn)

    ensure_other_schema(1)
    ensure_other_schema.run_again(2)
    assert calls == [1, 2]


def _ensure_functions() -> dict[str, list[str]]:
    """Every `def ensure_*_schema` under app/, with its decorators."""
    found: dict[str, list[str]] = {}
    for path in (ROOT / "app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and re.fullmatch(r"ensure_\w+_schema", node.name):
                found[f"{path.relative_to(ROOT).as_posix()}::{node.name}"] = [
                    ast.unparse(d) for d in node.decorator_list
                ]
    return found


def test_every_schema_function_runs_once_per_process():
    functions = _ensure_functions()
    assert len(functions) >= 21, functions
    undecorated = [name for name, decorators in functions.items() if "once_per_process" not in decorators]
    assert not undecorated, f"these would run DDL on every request again: {undecorated}"


def test_startup_runs_every_schema_function():
    """Anything missing here runs its DDL inside the first request that needs it instead."""
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))
    runner = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_schema_checks_once")
    # The names in the tuple that is actually run, not merely imported.
    ordered = next(
        node.value for node in ast.walk(runner)
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "ordered" for t in node.targets)
    )
    run = {element.id for element in ordered.elts if isinstance(element, ast.Name)}
    missing = sorted({name.split("::")[1] for name in _ensure_functions()} - run)
    assert not missing, missing


def test_the_lifespan_runs_the_schema_checks_before_serving():
    source = MAIN_PY.read_text(encoding="utf-8")
    lifespan = source[source.index("async def lifespan"):]
    lifespan = lifespan[: lifespan.index("yield")]
    assert "_run_schema_checks_once()" in lifespan


def test_request_threads_are_capped_below_the_pool():
    """ThreadedConnectionPool raises when empty instead of waiting. With more handler
    threads than connections, a burst of parallel requests got 'connection pool exhausted'."""
    from app.db.connection import HANDLER_THREADS, POOL_MAX_CONNECTIONS

    assert HANDLER_THREADS < POOL_MAX_CONNECTIONS
    source = MAIN_PY.read_text(encoding="utf-8")
    lifespan = source[source.index("async def lifespan"):]
    lifespan = lifespan[: lifespan.index("yield")]
    assert "current_default_thread_limiter().total_tokens = HANDLER_THREADS" in lifespan


def test_the_limit_leaves_headroom_whatever_the_environment_says():
    """Checked in a child process: reloading the module here would orphan the live pool."""
    import os
    import subprocess
    import sys

    env = {**os.environ, "DB_POOL_MAX_CONNECTIONS": "10", "DB_HANDLER_THREADS": "40"}
    out = subprocess.run(
        [sys.executable, "-c",
         "from app.db.connection import HANDLER_THREADS, POOL_MAX_CONNECTIONS;"
         "print(POOL_MAX_CONNECTIONS, HANDLER_THREADS)"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert out == ["10", "6"]
