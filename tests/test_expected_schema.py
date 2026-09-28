"""scripts/expected_schema.json must describe what a migrated, started database has.

It is what scripts/check_schema.py compares a server against. If a migration adds a table
or column and this file is not regenerated, the check stops noticing that column missing
on a server — which is how a stamped production database broke four screens.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.db.connection import connect_db

EXPECTED = Path(__file__).resolve().parents[1] / "scripts" / "expected_schema.json"


def _live():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT table_name, column_name FROM information_schema.columns
                       WHERE table_schema = current_schema()"""
                )
                rows = cur.fetchall()
            conn.commit()
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")
    live: dict[str, set[str]] = {}
    for table, column in rows:
        live.setdefault(table, set()).add(column)
    return live


def test_every_expected_column_exists_in_a_migrated_database():
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    live = _live()
    missing = sorted(f"{t}.{c}" for t, cols in expected.items() for c in cols if c not in live.get(t, set()))
    assert not missing, missing


def test_every_migrated_column_is_expected():
    """A column the migrations create but the file does not list would go unchecked."""
    expected = {t: set(cols) for t, cols in json.loads(EXPECTED.read_text(encoding="utf-8")).items()}
    live = _live()
    unlisted = sorted(f"{t}.{c}" for t, cols in live.items() for c in cols if c not in expected.get(t, set()))
    assert not unlisted, f"regenerate with: python scripts/check_schema.py --write-expected  ({unlisted})"


def test_the_filename_column_the_repair_restores_is_checked():
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    assert "original_filename" in expected["document_catalog"]
