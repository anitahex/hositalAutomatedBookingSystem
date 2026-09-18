"""Regression coverage for Step 4: forgot/reset password
(app/services/password_reset.py, the /auth/forgot-password/*, /auth/resend-otp,
/auth/reset-password routes).

Skips (not fails) if no database is reachable.
"""
import hashlib
import os
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time

from app.db.connection import connect_db
from app.services.passwords import hash_password

CURRENT_PASSWORD = "Str0ng!Pass"


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


@pytest.fixture
def client():
    # Must not depend on .env's actual value (this repo's own testing standard:
    # tests can't depend on a live third-party service) — these tests send OTPs to
    # fake @example.com addresses and must never attempt a real SMTP send regardless
    # of how PATIENT_AUTH_EMAIL_NO_SEND happens to be set for real usage.
    os.environ["PATIENT_AUTH_EMAIL_NO_SEND"] = "true"
    from app.api.main import app

    return TestClient(app)


def _otp_hash(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _ten_digit_number(seed: str) -> str:
    # Deterministic-but-unique-per-test 10-digit number derived from a uuid seed,
    # avoiding collisions with uq_patient_mobile_normalized across test runs.
    digits = "".join(ch for ch in seed if ch.isdigit())
    return (digits + "9876543210")[:10]


def _make_patient(email: str, mobile_number: str) -> str:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash, email_verified)
                VALUES (%s, %s, TRUE) RETURNING user_id;
                """,
                (email, hash_password(CURRENT_PASSWORD)),
            )
            user_id = str(cur.fetchone()[0])
            from app.services.users import normalize_mobile_number_india
            cur.execute(
                """
                INSERT INTO patient_profiles (user_id, name, age, mobile_number, mobile_number_normalized, address, email, blood_group)
                VALUES (%s, 'Reset Test', 30, %s, %s, '1 Test St', %s, 'O+');
                """,
                (user_id, mobile_number, normalize_mobile_number_india(mobile_number), email),
            )
        conn.commit()
    return user_id


def _cleanup(email: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE email = %s;", (email,))
            cur.execute("DELETE FROM otp_verifications WHERE email = %s;", (email,))
        conn.commit()


def _set_known_otp(email: str, otp: str):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE otp_verifications SET otp_hash = %s WHERE email = %s AND purpose = 'password_reset';",
                (_otp_hash(otp), email),
            )
        conn.commit()


def test_preexisting_account_with_null_password_changed_at_logs_in_and_completes_reset(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"reset-preexisting-{suffix}@example.com"
    mobile = _ten_digit_number(suffix)
    try:
        _make_patient(email, mobile)
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT password_changed_at FROM users WHERE email = %s;", (email,))
                assert cur.fetchone()[0] is None

        login = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        assert login.status_code == 200

        start = client.post("/auth/forgot-password/start", json={"identifier": email})
        assert start.status_code == 200
        assert start.json()["status"] == "otp_sent"

        _set_known_otp(email, "111222")
        reset = client.post(
            "/auth/reset-password",
            json={"email": email, "otp": "111222", "new_password": "NewStr0ng!Pass1", "confirm_password": "NewStr0ng!Pass1"},
        )
        assert reset.status_code == 200

        new_login = client.post("/auth/login", json={"email": email, "password": "NewStr0ng!Pass1"})
        assert new_login.status_code == 200
    finally:
        _cleanup(email)


def test_otp_past_expiry_is_rejected_even_with_correct_code(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"reset-expiry-{suffix}@example.com"
    mobile = _ten_digit_number(suffix)
    try:
        _make_patient(email, mobile)
        client.post("/auth/forgot-password/start", json={"identifier": email})
        _set_known_otp(email, "222333")

        frozen_future = datetime.now() + timedelta(minutes=11)
        with freeze_time(frozen_future):
            response = client.post(
                "/auth/reset-password",
                json={"email": email, "otp": "222333", "new_password": "NewStr0ng!Pass1", "confirm_password": "NewStr0ng!Pass1"},
            )
        assert response.status_code == 400
    finally:
        _cleanup(email)


def test_five_wrong_attempts_locks_out_a_sixth_even_correct_attempt(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"reset-lockout-{suffix}@example.com"
    mobile = _ten_digit_number(suffix)
    try:
        _make_patient(email, mobile)
        client.post("/auth/forgot-password/start", json={"identifier": email})
        _set_known_otp(email, "333444")

        for _ in range(5):
            resp = client.post(
                "/auth/reset-password",
                json={"email": email, "otp": "000000", "new_password": "NewStr0ng!Pass1", "confirm_password": "NewStr0ng!Pass1"},
            )
            assert resp.status_code == 400

        sixth = client.post(
            "/auth/reset-password",
            json={"email": email, "otp": "333444", "new_password": "NewStr0ng!Pass1", "confirm_password": "NewStr0ng!Pass1"},
        )
        assert sixth.status_code == 400
    finally:
        _cleanup(email)


def test_resend_cooldown_blocks_then_succeeds_after_via_freezegun(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"reset-resend-{suffix}@example.com"
    mobile = _ten_digit_number(suffix)
    try:
        _make_patient(email, mobile)
        client.post("/auth/forgot-password/start", json={"identifier": email})

        immediate = client.post("/auth/resend-otp", json={"email": email})
        assert immediate.status_code == 200
        body = immediate.json()
        assert body["status"] == "cooldown"
        assert body["retry_after_seconds"] > 0

        frozen_future = datetime.now() + timedelta(seconds=241)
        with freeze_time(frozen_future):
            after_cooldown = client.post("/auth/resend-otp", json={"email": email})
        assert after_cooldown.status_code == 200
        assert after_cooldown.json()["status"] == "otp_sent"
    finally:
        _cleanup(email)


def test_resend_hourly_cap_enforced():
    """check_rate_limit's underlying state is in-memory, shared, and process-global
    (a documented characteristic, not something this step changes) — keyed on both IP
    and account. Going through the real /auth/resend-otp endpoint would share the
    TestClient's fixed IP across every test in this file and get cross-polluted by
    whichever ran first. Testing the exact mechanism the route calls
    (check_rate_limit with the same scope/limit/window it uses) with a synthetic,
    per-test-unique ip/account_key isolates this from that shared state."""
    from app.services.doctor_auth import check_rate_limit

    fake_ip = f"203.0.113.{uuid.uuid4().int % 250 + 1}"
    account_key = f"cap-test-{uuid.uuid4().hex[:8]}"

    for i in range(5):
        check_rate_limit("password_reset_resend", fake_ip, account_key, limit=5, window_seconds=3600)

    with pytest.raises(PermissionError):
        check_rate_limit("password_reset_resend", fake_ip, account_key, limit=5, window_seconds=3600)


def test_full_mobile_path_flow_end_to_end_including_old_session_invalidation(client):
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"reset-mobilepath-{suffix}@example.com"
    mobile = _ten_digit_number(suffix)
    try:
        _make_patient(email, mobile)

        old_login = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        old_token = old_login.json()["access_token"]
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 200

        start = client.post("/auth/forgot-password/start", json={"identifier": mobile})
        assert start.status_code == 200
        assert start.json()["status"] == "confirm_email_required"
        assert "masked_email" in start.json()

        wrong_email = client.post(
            "/auth/forgot-password/confirm-email",
            json={"mobile_number": mobile, "email": "not-the-real-email@example.com"},
        )
        assert wrong_email.json()["status"] == "email_mismatch"

        confirm = client.post(
            "/auth/forgot-password/confirm-email",
            json={"mobile_number": mobile, "email": email},
        )
        assert confirm.status_code == 200
        assert confirm.json()["status"] == "otp_sent"

        _set_known_otp(email, "444555")
        reset = client.post(
            "/auth/reset-password",
            json={"email": email, "otp": "444555", "new_password": "NewStr0ng!Pass1", "confirm_password": "NewStr0ng!Pass1"},
        )
        assert reset.status_code == 200

        # Old session invalidated by the reset (password_changed_at gate in current_user).
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401

        new_login = client.post("/auth/login", json={"email": email, "password": "NewStr0ng!Pass1"})
        assert new_login.status_code == 200
        new_token = new_login.json()["access_token"]
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {new_token}"}).status_code == 200
    finally:
        _cleanup(email)


def test_reset_releases_a_brute_force_lockout(client):
    """A locked-out account must be able to log in immediately after a successful
    reset. The OTP proves control of the inbox — a stronger signal than the password.
    Regression: the lockout survived the reset, and since authenticate_user reports a
    lockout as "invalid email or password", the user was told their brand-new password
    was wrong and looped through reset after reset with no way in."""
    _skip_if_no_database()
    suffix = uuid.uuid4().hex[:8]
    email = f"reset-lockedout-{suffix}@example.com"
    mobile = _ten_digit_number(suffix)
    try:
        _make_patient(email, mobile)

        # Trip the lockout with repeated wrong passwords.
        for _ in range(6):
            client.post("/auth/login", json={"email": email, "password": "WrongPassword1!"})

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT locked_until FROM login_lockouts WHERE email = %s;", (email,))
                assert cur.fetchone()[0] is not None

        # Even the correct current password is refused while locked — but now with a
        # 423 that says how long, rather than a 401 claiming the password is wrong.
        locked = client.post("/auth/login", json={"email": email, "password": CURRENT_PASSWORD})
        assert locked.status_code == 423
        assert locked.json()["detail"]["retry_after_seconds"] > 0

        client.post("/auth/forgot-password/start", json={"identifier": email})
        _set_known_otp(email, "606060")
        reset = client.post(
            "/auth/reset-password",
            json={"email": email, "otp": "606060", "new_password": "NewStr0ng!Pass1", "confirm_password": "NewStr0ng!Pass1"},
        )
        assert reset.status_code == 200

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM login_lockouts WHERE email = %s;", (email,))
                assert cur.fetchone() is None

        # The whole point: log in right away, no waiting out the lockout.
        assert client.post("/auth/login", json={"email": email, "password": "NewStr0ng!Pass1"}).status_code == 200
    finally:
        _cleanup(email)


def test_not_found_for_unknown_email_and_unknown_mobile(client):
    _skip_if_no_database()
    unknown_email = f"never-signed-up-{uuid.uuid4().hex[:8]}@example.com"
    unknown_mobile = _ten_digit_number(uuid.uuid4().hex)

    by_email = client.post("/auth/forgot-password/start", json={"identifier": unknown_email})
    assert by_email.json()["status"] == "not_found"

    by_mobile = client.post("/auth/forgot-password/start", json={"identifier": unknown_mobile})
    assert by_mobile.json()["status"] == "not_found"
