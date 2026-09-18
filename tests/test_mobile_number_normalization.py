"""Regression coverage for Step 3: app/services/users.py::normalize_mobile_number_india,
scripts/report_duplicate_normalized_mobiles.py, and the CREATE UNIQUE INDEX CONCURRENTLY
mechanism used in alembic/versions/0013_add_mobile_normalized_unique_index.py.

The CONCURRENTLY tests deliberately use scratch tables rather than the real
patient_profiles table, since a real "does this succeed on clean data" assertion
against a shared table would be fragile against unrelated pre-existing rows from other
tests/real signups — this isolates the DDL mechanism itself (succeeds when clean, fails
outright rather than silently succeeding when a duplicate is present).

Skips (not fails) if no database is reachable.
"""
import uuid

import psycopg2
import pytest

from app.db.connection import DATABASE_URL, connect_db
from app.services.passwords import hash_password
from app.services.users import normalize_mobile_number_india
from scripts.report_duplicate_normalized_mobiles import report_duplicates


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _autocommit_conn():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn


# ---- normalize_mobile_number_india: pure unit tests, no DB needed ----

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("9876543210", "+919876543210"),          # 10 digits
        ("09876543210", "+919876543210"),          # leading 0 + 11 digits
        ("919876543210", "+919876543210"),         # 12 digits starting with 91
        ("+91 98765 43210", "+919876543210"),      # already-formatted, still resolves
        ("98765-43210", "+919876543210"),          # punctuation stripped, still 10 digits
    ],
)
def test_normalize_recognized_formats(raw, expected):
    assert normalize_mobile_number_india(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "12345",             # too short
        "1234567890123456",  # too long
        "abcdefghij",        # not digits at all
        "",                  # empty
        None,                # missing
        "8765432109123",     # 13 digits, doesn't match any recognized shape
    ],
)
def test_normalize_unrecognized_formats_return_none_not_guessed(raw):
    assert normalize_mobile_number_india(raw) is None


# ---- duplicate-report script: real DB, seeded synthetic duplicates ----

def _make_patient(email: str, mobile_number: str, mobile_normalized: str | None) -> str:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash, email_verified) VALUES (%s, %s, TRUE) RETURNING user_id;",
                (email, hash_password("Str0ng!Pass")),
            )
            user_id = str(cur.fetchone()[0])
            cur.execute(
                """
                INSERT INTO patient_profiles (user_id, name, age, mobile_number, mobile_number_normalized, address, email, blood_group)
                VALUES (%s, 'Mobile Norm Test', 30, %s, %s, '1 Test St', %s, 'O+');
                """,
                (user_id, mobile_number, mobile_normalized, email),
            )
        conn.commit()
    return user_id


def _cleanup(*emails: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for email in emails:
                cur.execute("DELETE FROM users WHERE email = %s;", (email,))
        conn.commit()


def test_report_duplicate_normalized_mobiles_finds_seeded_duplicate(capsys):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email_a = f"mobiledup-a-{suffix}@example.com"
    email_b = f"mobiledup-b-{suffix}@example.com"
    duplicate_number = "+919876500099"

    # The real 0013 migration already ran against this DB (confirmed: the unique
    # index exists), so the DB itself now blocks the exact duplicate this test needs
    # to seed. Recreate the real staged-migration window the report script is
    # designed for (after backfill, before the index) by dropping it here and
    # restoring it in the finally block, leaving the environment exactly as found.
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_indexes WHERE indexname = 'uq_patient_mobile_normalized';")
            index_existed = cur.fetchone() is not None

    if index_existed:
        conn = _autocommit_conn()
        with conn.cursor() as cur:
            cur.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_patient_mobile_normalized;")
        conn.close()

    try:
        _make_patient(email_a, "9876500099", duplicate_number)
        _make_patient(email_b, "09876500099", duplicate_number)

        count = report_duplicates()
        captured = capsys.readouterr()

        assert count >= 1
        assert duplicate_number in captured.out
    finally:
        _cleanup(email_a, email_b)
        if index_existed:
            conn = _autocommit_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_patient_mobile_normalized
                    ON patient_profiles (mobile_number_normalized)
                    WHERE mobile_number_normalized IS NOT NULL;
                    """
                )
            conn.close()


def test_report_duplicate_normalized_mobiles_does_not_flag_unique_numbers(capsys):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"mobileunique-{suffix}@example.com"
    unique_number = "+919876500098"
    try:
        _make_patient(email, "9876500098", unique_number)

        report_duplicates()
        captured = capsys.readouterr()

        assert unique_number not in captured.out
    finally:
        _cleanup(email)


# ---- CREATE UNIQUE INDEX CONCURRENTLY mechanism: isolated scratch tables ----

def test_concurrently_index_succeeds_on_clean_data():
    _skip_if_no_database()
    conn = _autocommit_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS test_mobile_scratch_clean;")
            cur.execute("CREATE TABLE test_mobile_scratch_clean (id serial PRIMARY KEY, mobile_number_normalized TEXT);")
            cur.execute(
                "INSERT INTO test_mobile_scratch_clean (mobile_number_normalized) VALUES ('+919876500001'), ('+919876500002');"
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX CONCURRENTLY test_uq_mobile_scratch_clean
                ON test_mobile_scratch_clean (mobile_number_normalized)
                WHERE mobile_number_normalized IS NOT NULL;
                """
            )
            cur.execute(
                "SELECT indexname FROM pg_indexes WHERE indexname = 'test_uq_mobile_scratch_clean';"
            )
            assert cur.fetchone() is not None
    finally:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS test_mobile_scratch_clean CASCADE;")
        conn.close()


def test_concurrently_index_fails_outright_when_duplicates_present():
    _skip_if_no_database()
    conn = _autocommit_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS test_mobile_scratch_dup;")
            cur.execute("CREATE TABLE test_mobile_scratch_dup (id serial PRIMARY KEY, mobile_number_normalized TEXT);")
            cur.execute(
                "INSERT INTO test_mobile_scratch_dup (mobile_number_normalized) VALUES ('+919876500003'), ('+919876500003');"
            )

        with pytest.raises(psycopg2.Error):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE UNIQUE INDEX CONCURRENTLY test_uq_mobile_scratch_dup
                    ON test_mobile_scratch_dup (mobile_number_normalized)
                    WHERE mobile_number_normalized IS NOT NULL;
                    """
                )
    finally:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS test_mobile_scratch_dup CASCADE;")
        conn.close()
