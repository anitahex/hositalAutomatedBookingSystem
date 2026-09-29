"""Accounts older than the login registry can log in and recover their password.

Reproduced first: an account in `users` but missing from account_email_registry got
"Invalid email or password" with the right password, and again after a successful
password reset; forgot-password by phone said "No account found" when its normalized
number had never been filled in. Migration 0031 repairs existing data; login and the
phone lookup repair future gaps themselves.
"""
from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

import pytest

from app.db.connection import connect_db
from app.services.account_registry import lookup, register_existing_account
from app.services.password_reset import _find_email_by_mobile

MIGRATION = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0031_repair_account_lookups.py"


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM account_email_registry LIMIT 0")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _run_migration():
    """Runs 0031's upgrade() SQL against the test database."""
    spec = importlib.util.spec_from_file_location("m0031", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    statements = []

    class _Op:
        @staticmethod
        def execute(sql):
            statements.append(sql)

    import alembic
    real_op = alembic.op
    try:
        alembic.op = _Op
        spec.loader.exec_module(module)
        module.op = _Op
        module.upgrade()
    finally:
        alembic.op = real_op
    with connect_db() as conn:
        with conn.cursor() as cur:
            for sql in statements:
                cur.execute(sql)
        conn.commit()


@pytest.fixture
def people():
    """Creates old-style patient accounts: in users, NOT in the registry, mobile not normalized."""
    _skip_if_no_database()
    made: list[str] = []
    tag = uuid.uuid4().hex[:8]

    def make(email: str, mobile: str | None = None) -> str:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id", (email,))
                user_id = str(cur.fetchone()[0])
                if mobile is not None:
                    cur.execute(
                        """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
                           VALUES (%s, 'Old Account', 40, %s, 'x', %s, 'O+')""",
                        (user_id, mobile, email.lower()),
                    )
                cur.execute("DELETE FROM account_email_registry WHERE account_id = %s", (user_id,))
            conn.commit()
        made.append(user_id)
        return user_id

    make.tag = tag
    try:
        yield make
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                for user_id in made:
                    cur.execute("DELETE FROM account_email_registry WHERE account_id = %s", (user_id,))
                    cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            conn.commit()


def _registered(email):
    with connect_db() as conn:
        with conn.cursor() as cur:
            row = lookup(cur, email)
        conn.commit()
    return row


def _profile(user_id):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT u.email, p.mobile_number_normalized FROM users u
                           LEFT JOIN patient_profiles p ON p.user_id = u.user_id WHERE u.user_id = %s""", (user_id,))
            row = cur.fetchone()
        conn.commit()
    return row


# ---- the migration ----

def test_the_migration_makes_an_old_account_findable_by_login_and_by_phone(people):
    mobile = f"098{int(people.tag, 16) % 10**8:08d}"  # a leading 0, then 10 digits
    user_id = people(f"Old.User.{people.tag}@Example.COM", mobile)
    assert _registered(f"old.user.{people.tag}@example.com") is None

    _run_migration()

    email, normalized = _profile(user_id)
    assert email == f"old.user.{people.tag}@example.com"
    assert normalized == "+91" + mobile[1:]
    account_type, account_id = _registered(email)
    assert (account_type, str(account_id)) == ("patient", user_id)


def test_an_email_that_would_collide_when_lowercased_is_left_alone(people):
    lower = people(f"twin.{people.tag}@example.com")
    upper = people(f"Twin.{people.tag}@example.com")
    _run_migration()
    assert _profile(upper)[0] == f"Twin.{people.tag}@example.com"
    assert _profile(lower)[0] == f"twin.{people.tag}@example.com"


def test_a_phone_number_two_profiles_share_is_given_to_one_only(people):
    mobile = f"97{int(people.tag, 16) % 10**8:08d}"
    first = people(f"first.{people.tag}@example.com", mobile)
    second = people(f"second.{people.tag}@example.com", mobile)
    _run_migration()
    normalized = [_profile(first)[1], _profile(second)[1]]
    assert normalized.count("+91" + mobile) == 1 and normalized.count(None) == 1


def test_the_migration_is_safe_to_run_twice(people):
    user_id = people(f"again.{people.tag}@example.com", f"96{int(people.tag, 16) % 10**8:08d}")
    _run_migration()
    before = _profile(user_id)
    _run_migration()
    assert _profile(user_id) == before


# ---- the runtime fallbacks ----

def test_login_registers_an_account_the_registry_is_missing(people):
    email = f"fallback.{people.tag}@example.com"
    user_id = people(email)
    with connect_db() as conn:
        with conn.cursor() as cur:
            registered = lookup(cur, email) or register_existing_account(cur, email)
        conn.commit()
    assert (registered[0], str(registered[1])) == ("patient", user_id)
    assert _registered(email) is not None


def test_an_unknown_email_is_not_registered(people):
    with connect_db() as conn:
        with conn.cursor() as cur:
            assert register_existing_account(cur, f"nobody.{people.tag}@example.com") is None
        conn.commit()


def test_forgot_password_by_phone_finds_an_unnormalized_number(people):
    mobile = f"95{int(people.tag, 16) % 10**8:08d}"
    email = f"phone.{people.tag}@example.com"
    people(email, f"+91 {mobile[:5]} {mobile[5:]}")
    assert _find_email_by_mobile(mobile) == email


def test_a_phone_number_two_accounts_share_finds_neither(people):
    """Two accounts on one number: the lookup cannot say whose password is being reset."""
    mobile = f"94{int(people.tag, 16) % 10**8:08d}"
    people(f"a.{people.tag}@example.com", mobile)
    people(f"b.{people.tag}@example.com", mobile)
    assert _find_email_by_mobile(mobile) is None


def test_login_falls_back_to_the_account_tables():
    """Login reads ONLY the registry; without the fallback a missing entry is a 401."""
    import re
    source = (Path(__file__).resolve().parents[1] / "app" / "api" / "routes" / "auth.py").read_text(encoding="utf-8")
    login = source[source.index("def unified_login"):source.index("@router.post(\"/signup\")")]
    assert re.search(r"registered = lookup\(cur, email\) or register_existing_account\(cur, email\)", login)
