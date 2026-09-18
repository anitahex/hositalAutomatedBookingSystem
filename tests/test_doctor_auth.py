from fastapi import HTTPException
import pytest

from app.api import dependencies
from app.api.routes import doctor as doctor_route
from app.db.connection import connect_db
from app.services import tokens


def _credentials(token: str):
    from fastapi.security import HTTPAuthorizationCredentials
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _skip_if_no_database():
    # verify_access_token now checks token revocation (FULL_SYSTEM_AUDIT.md P1 #7),
    # which requires a real database for any token whose signature actually verifies —
    # these tests aren't testing revocation, just structural/routing behavior, so they
    # skip cleanly rather than erroring when no DB is reachable, matching this repo's
    # convention for genuinely DB-backed tests.
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def test_doctor_tokens_are_structurally_separate():
    _skip_if_no_database()
    pending = tokens.create_doctor_mfa_pending_token(
        doctor_id="doctor-1", account_id="account-1", email="doctor@example.com"
    )
    session = tokens.create_doctor_session_token(
        doctor_id="doctor-1", account_id="account-1", email="doctor@example.com"
    )
    assert tokens.verify_access_token(pending)["token_kind"] == "doctor_mfa_pending"
    assert tokens.verify_access_token(session)["token_kind"] == "doctor_session"
    with pytest.raises(HTTPException) as exc:
        doctor_route._mfa_token(_credentials(session), "doctor_mfa_pending")
    assert exc.value.status_code == 401


def test_patient_token_cannot_be_used_as_doctor_session(monkeypatch):
    _skip_if_no_database()
    patient = tokens.create_access_token(patient_id="patient-1", email="patient@example.com")
    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_doctor(_credentials(patient))
    assert exc.value.status_code == 401


def test_doctor_token_cannot_be_used_for_patient_routes(monkeypatch):
    _skip_if_no_database()
    doctor = tokens.create_doctor_session_token(
        doctor_id="doctor-1", account_id="account-1", email="doctor@example.com"
    )
    with pytest.raises(HTTPException) as exc:
        dependencies.current_user(_credentials(doctor))
    assert exc.value.status_code == 401


def test_complete_invite_issues_enrollment_only_token(monkeypatch):
    _skip_if_no_database()
    monkeypatch.setattr(
        doctor_route, "complete_invite",
        lambda token, password: {
            "doctor_id": "doctor-1", "account_id": "account-1", "email": "doctor@example.com", "mfa_enabled": False,
        },
    )
    response = doctor_route.complete_invite_route(
        doctor_route.CompleteInviteRequest(token="invite", password="Password1!")
    )
    assert response["status"] == "password_set"
    payload = tokens.verify_access_token(response["mfa_enrollment_token"])
    assert payload["token_kind"] == "doctor_mfa_enrollment"


def test_complete_invite_skips_enrollment_when_mfa_already_enabled(monkeypatch):
    monkeypatch.setattr(
        doctor_route, "complete_invite",
        lambda token, password: {
            "doctor_id": "doctor-1", "account_id": "account-1", "email": "doctor@example.com", "mfa_enabled": True,
        },
    )
    response = doctor_route.complete_invite_route(
        doctor_route.CompleteInviteRequest(token="reset", password="Password1!")
    )
    assert response == {"status": "password_reset"}


def test_login_happy_path_requires_mfa_and_challenge_issues_session(monkeypatch):
    _skip_if_no_database()
    monkeypatch.setattr(doctor_route, "check_rate_limit", lambda *args: None)
    monkeypatch.setattr(
        doctor_route, "authenticate_doctor_password", lambda email, password: ("account-1", "doctor-1", email)
    )
    login = doctor_route.doctor_login(
        doctor_route.LoginRequest(email="doctor@example.com", password="Password1!"),
        type("Request", (), {"client": type("Client", (), {"host": "127.0.0.1"})()})(),
    )
    pending = login["mfa_token"]
    monkeypatch.setattr(
        doctor_route, "complete_mfa_challenge", lambda account_id, code: ("doctor-1", "doctor@example.com", account_id, False)
    )
    response = doctor_route.mfa_challenge(
        doctor_route.MfaCodeRequest(code="123456"),
        type("Request", (), {"client": type("Client", (), {"host": "127.0.0.1"})()})(),
        _credentials(pending),
    )
    assert tokens.verify_access_token(response["access_token"])["token_kind"] == "doctor_session"


@pytest.mark.parametrize("message", ["Invite token has expired.", "Invite token has already been used."])
def test_consumed_and_expired_invites_are_rejected(monkeypatch, message):
    def fail(*args):
        raise PermissionError(message)
    monkeypatch.setattr(doctor_route, "complete_invite", fail)
    with pytest.raises(HTTPException) as exc:
        doctor_route.complete_invite_route(doctor_route.CompleteInviteRequest(token="bad", password="Password1!"))
    assert exc.value.status_code == 400
    assert exc.value.detail == message


def test_login_mfa_block_and_lockout_errors_are_not_tokens(monkeypatch):
    monkeypatch.setattr(doctor_route, "check_rate_limit", lambda *args: None)
    for message in ("MFA enrollment is required before login.", "Invalid email or password."):
        monkeypatch.setattr(doctor_route, "authenticate_doctor_password", lambda *args, _message=message: (_ for _ in ()).throw(PermissionError(_message)))
        with pytest.raises(HTTPException) as exc:
            doctor_route.doctor_login(doctor_route.LoginRequest(email="doctor@example.com", password="bad"), type("R", (), {"client": None})())
        assert exc.value.status_code == 401


def test_mfa_challenge_accepts_recovery_code(monkeypatch):
    _skip_if_no_database()
    pending = tokens.create_doctor_mfa_pending_token(doctor_id="doctor-1", account_id="account-1", email="doctor@example.com")
    monkeypatch.setattr(doctor_route, "check_rate_limit", lambda *args: None)
    monkeypatch.setattr(
        doctor_route, "complete_mfa_challenge",
        lambda account_id, code: ("doctor-1", "doctor@example.com", account_id, True),
    )
    response = doctor_route.mfa_challenge(
        doctor_route.MfaCodeRequest(code="a-recovery-code"),
        type("R", (), {"client": None})(),
        _credentials(pending),
    )
    assert response["recovery_code_used"] is True
    assert tokens.verify_access_token(response["access_token"])["token_kind"] == "doctor_session"


def test_invite_completion_to_login_round_trip(monkeypatch):
    _skip_if_no_database()
    monkeypatch.setattr(
        doctor_route, "complete_invite",
        lambda token, password: {
            "doctor_id": "doctor-1", "account_id": "account-1", "email": "doctor@example.com", "mfa_enabled": False,
        },
    )
    invite_response = doctor_route.complete_invite_route(
        doctor_route.CompleteInviteRequest(token="invite", password="Password1!")
    )
    enrollment_token = invite_response["mfa_enrollment_token"]
    assert tokens.verify_access_token(enrollment_token)["token_kind"] == "doctor_mfa_enrollment"

    monkeypatch.setattr(doctor_route, "start_mfa_enrollment", lambda account_id: "otpauth://totp/example")
    enroll_response = doctor_route.mfa_enroll(_credentials(enrollment_token))
    assert enroll_response == {"provisioning_uri": "otpauth://totp/example"}

    monkeypatch.setattr(doctor_route, "verify_mfa_enrollment", lambda account_id, code: ["code1", "code2"])
    verify_response = doctor_route.mfa_verify(
        doctor_route.MfaCodeRequest(code="123456"), _credentials(enrollment_token)
    )
    assert verify_response == {"status": "mfa_enabled", "recovery_codes": ["code1", "code2"]}

    monkeypatch.setattr(doctor_route, "check_rate_limit", lambda *args: None)
    monkeypatch.setattr(
        doctor_route, "authenticate_doctor_password", lambda email, password: ("account-1", "doctor-1", email)
    )
    login_response = doctor_route.doctor_login(
        doctor_route.LoginRequest(email="doctor@example.com", password="Password1!"),
        type("R", (), {"client": type("Client", (), {"host": "127.0.0.1"})()})(),
    )
    pending = login_response["mfa_token"]
    monkeypatch.setattr(
        doctor_route, "complete_mfa_challenge",
        lambda account_id, code: ("doctor-1", "doctor@example.com", account_id, False),
    )
    challenge_response = doctor_route.mfa_challenge(
        doctor_route.MfaCodeRequest(code="123456"),
        type("R", (), {"client": type("Client", (), {"host": "127.0.0.1"})()})(),
        _credentials(pending),
    )
    assert tokens.verify_access_token(challenge_response["access_token"])["token_kind"] == "doctor_session"


def test_mfa_challenge_rejects_bad_or_reused_recovery_code(monkeypatch):
    _skip_if_no_database()
    pending = tokens.create_doctor_mfa_pending_token(doctor_id="doctor-1", account_id="account-1", email="doctor@example.com")
    monkeypatch.setattr(doctor_route, "check_rate_limit", lambda *args: None)
    monkeypatch.setattr(doctor_route, "complete_mfa_challenge", lambda *args: (_ for _ in ()).throw(PermissionError("Invalid MFA code.")))
    with pytest.raises(HTTPException) as exc:
        doctor_route.mfa_challenge(doctor_route.MfaCodeRequest(code="reused"), type("R", (), {"client": None})(), _credentials(pending))
    assert exc.value.status_code == 401
