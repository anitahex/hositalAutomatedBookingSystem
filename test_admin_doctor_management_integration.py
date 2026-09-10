"""Integration regression coverage for list_doctors()/get_doctor() against a real database.

Every other test in this suite (including test_admin_doctor_management.py) mocks the
psycopg2 cursor/connection, so a type error in the raw SQL string itself — e.g.
MAX(da.id) failing with psycopg2.errors.UndefinedFunction because Postgres has no
MAX() aggregate for uuid — is invisible to that layer of test. These tests actually
open a connection and run the query, which is the only way to catch that class of bug.

Skips (not fails) if no database is reachable, so environments without Postgres
configured don't get a false failure here.
"""

import pytest

from app.db.connection import connect_db
from app.services.admin_management import get_doctor, list_doctors


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def test_list_and_get_doctor_against_a_real_doctor_with_an_account():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO doctors (name, department, experience_years, is_active)
                       VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
                    ("Regression Test Doctor", "Testing", 1),
                )
                doctor_id = str(cur.fetchone()[0])
                cur.execute(
                    """INSERT INTO doctor_accounts (doctor_id, email, is_active, mfa_enabled)
                       VALUES (%s, %s, TRUE, TRUE)""",
                    (doctor_id, "regression-test-doctor@example.com"),
                )
            conn.commit()

        doctors = list_doctors()
        assert isinstance(doctors, list)
        match = next((d for d in doctors if d["doctor_id"] == doctor_id), None)
        assert match is not None, "seeded doctor was not returned by list_doctors()"
        assert match["account_email"] == "regression-test-doctor@example.com"
        assert match["login_status"] == "mfa_enrolled"
        assert match["invite_action"] == "reset"

        single = get_doctor(doctor_id)
        assert single is not None
        assert single["account_email"] == "regression-test-doctor@example.com"
        assert single["login_status"] == "mfa_enrolled"
    finally:
        if doctor_id:
            with connect_db() as conn:
                with conn.cursor() as cur:
                    # doctor_accounts has ON DELETE CASCADE from doctors, so this
                    # also removes the seeded account row.
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                conn.commit()


def test_list_and_get_doctor_against_a_doctor_with_no_account():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO doctors (name, department, experience_years, is_active)
                       VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
                    ("Regression Test Doctor No Account", "Testing", 1),
                )
                doctor_id = str(cur.fetchone()[0])
            conn.commit()

        doctors = list_doctors()
        match = next((d for d in doctors if d["doctor_id"] == doctor_id), None)
        assert match is not None
        assert match["account_id"] is None
        assert match["login_status"] == "not_invited"
        assert match["invite_action"] == "invite"

        single = get_doctor(doctor_id)
        assert single is not None
        assert single["login_status"] == "not_invited"
    finally:
        if doctor_id:
            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                conn.commit()
