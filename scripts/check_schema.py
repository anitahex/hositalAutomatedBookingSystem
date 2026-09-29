"""Compares this database's tables and columns with what the code expects.

WHY. Production's database was not built purely by the migrations: some tables were
created by the app's startup SQL and the database was stamped past migrations that then
never ran. So "the migrations passed" does not prove the columns exist, and a missing one
surfaces only as a 500 in whichever screen first reads it (document_catalog.
original_filename did exactly that). This finds every such gap in one run.

scripts/expected_schema.json is the schema of a database built by the migrations and
started once (the app creates a few tables at startup). Regenerate it after adding a
migration:  python scripts/check_schema.py --write-expected   (against a correct database)

Run after the app has started at least once:
    docker compose exec backend python scripts/check_schema.py
Exits 1 when anything the code expects is missing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.connection import connect_db  # noqa: E402

EXPECTED = Path(__file__).resolve().parent / "expected_schema.json"
PLACEHOLDER_FILENAME = "uploaded-file"


def live_schema() -> dict[str, list[str]]:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT table_name, column_name FROM information_schema.columns
                   WHERE table_schema = current_schema() ORDER BY table_name, column_name"""
            )
            rows = cur.fetchall()
        conn.commit()
    schema: dict[str, list[str]] = {}
    for table, column in rows:
        schema.setdefault(table, []).append(column)
    return schema


def placeholder_filenames() -> int | None:
    """Documents whose real filename could not be recovered: their original file cannot be
    opened in the viewer (it is stored under the real name)."""
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM document_catalog WHERE original_filename = %s",
                            (PLACEHOLDER_FILENAME,))
                count = cur.fetchone()[0]
            conn.commit()
        return int(count)
    except Exception:
        return None


def account_gaps() -> dict[str, int]:
    """Accounts login or forgot-password cannot find (see migration 0031). All zero on a
    healthy database; the migration and login's own fallback repair them."""
    checks = {
        "accounts missing from the login registry": """
            SELECT (SELECT COUNT(*) FROM users u WHERE NOT EXISTS
                       (SELECT 1 FROM account_email_registry r WHERE r.email = lower(btrim(u.email))))
                 + (SELECT COUNT(*) FROM doctor_accounts d WHERE NOT EXISTS
                       (SELECT 1 FROM account_email_registry r WHERE r.email = lower(btrim(d.email))))""",
        "patient emails not stored in lowercase": """
            SELECT COUNT(*) FROM users WHERE email <> lower(btrim(email))""",
        "patient mobile numbers not searchable by forgot-password": """
            SELECT COUNT(*) FROM patient_profiles
             WHERE mobile_number_normalized IS NULL AND COALESCE(mobile_number, '') <> ''""",
    }
    found: dict[str, int] = {}
    for label, sql in checks.items():
        try:
            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    found[label] = int(cur.fetchone()[0])
                conn.commit()
        except Exception:
            found[label] = -1  # the table itself is missing; the schema check reports it
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write-expected", action="store_true",
                        help="record THIS database as the expected schema")
    args = parser.parse_args()

    live = live_schema()
    if args.write_expected:
        EXPECTED.write_text(json.dumps(live, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {EXPECTED.name}: {len(live)} tables")
        return 0

    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    missing_tables = sorted(set(expected) - set(live))
    missing_columns = sorted(
        f"{table}.{column}"
        for table, columns in expected.items() if table in live
        for column in columns if column not in live[table]
    )
    print(f"database: {os.getenv('DATABASE_URL', '').rsplit('/', 1)[-1] or '?'}")
    print(f"tables expected {len(expected)}, present {len(set(expected) & set(live))}")
    print("missing tables:", ", ".join(missing_tables) if missing_tables else "none")
    print("missing columns:", ", ".join(missing_columns) if missing_columns else "none")
    unresolved = placeholder_filenames()
    if unresolved:
        print(f"documents with no recoverable filename (original file cannot be opened): {unresolved}")
    for label, count in account_gaps().items():
        print(f"{label}: {count if count >= 0 else 'could not check'}")
    return 1 if (missing_tables or missing_columns) else 0


if __name__ == "__main__":
    raise SystemExit(main())
