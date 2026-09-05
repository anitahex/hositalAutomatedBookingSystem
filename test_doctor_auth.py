from fastapi import HTTPException
import pytest

from app.api import dependencies
from app.api.routes import doctor as doctor_route
from app.services import tokens


def _credentials(token: str):
    from fastapi.security import HTTPAuthorizationCredentials
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_doctor_tokens_are_structurally_separate():
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
    patient = tokens.create_access_token(patient_id="patient-1", email="patient@example.com")
    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_doctor(_credentials(patient))
    assert exc.value.status_code == 401


def test_doctor_token_cannot_be_used_for_patient_routes(monkeypatch):
    doctor = tokens.create_doctor_session_token(
        doctor_id="doctor-1", account_id="account-1", email="doctor@example.com"
    )
    with pytest.raises(HTTPException) as exc:
        dependencies.current_user(_credentials(doctor))
    assert exc.value.status_code == 401


def test_complete_invite_issues_enrollment_only_token(monkeypatch):
    monkeypatch.setattr(
        doctor_route, "complete_invite",
        lambda token, password: {"doctor_id": "doctor-1", "account_id": "account-1", "email": "doctor@example.com"},
    )
    response = doctor_route.complete_invite_route(
        doctor_route.CompleteInviteRequest(token="invite", password="Password1!")
    )
    payload = tokens.verify_access_token(response["mfa_enrollment_token"])
    assert payload["token_kind"] == "doctor_mfa_enrollment"


def test_login_happy_path_requires_mfa_and_challenge_issues_session(monkeypatch):
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


def test_mfa_challenge_rejects_bad_or_reused_recovery_code(monkeypatch):
    pending = tokens.create_doctor_mfa_pending_token(doctor_id="doctor-1", account_id="account-1", email="doctor@example.com")
    monkeypatch.setattr(doctor_route, "check_rate_limit", lambda *args: None)
    monkeypatch.setattr(doctor_route, "complete_mfa_challenge", lambda *args: (_ for _ in ()).throw(PermissionError("Invalid MFA code.")))
    with pytest.raises(HTTPException) as exc:
        doctor_route.mfa_challenge(doctor_route.MfaCodeRequest(code="reused"), type("R", (), {"client": None})(), _credentials(pending))
    assert exc.value.status_code == 401
