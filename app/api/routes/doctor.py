from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.api.dependencies import bearer_scheme, get_current_doctor
from app.services.doctor_auth import (
    authenticate_doctor_password, check_rate_limit, complete_invite, complete_mfa_challenge,
    issue_invite, start_mfa_enrollment, verify_mfa_enrollment,
)
from app.services.tokens import (
    create_doctor_mfa_enrollment_token, create_doctor_mfa_pending_token,
    create_doctor_session_token, verify_access_token,
)

router = APIRouter()


class InviteRequest(BaseModel):
    email: str


class ResetInviteRequest(InviteRequest):
    confirm_reset: bool


class CompleteInviteRequest(BaseModel):
    token: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class MfaCodeRequest(BaseModel):
    code: str


def _error(exc: Exception, status: int = 400):
    raise HTTPException(status_code=status, detail=str(exc))


def _mfa_token(credentials: HTTPAuthorizationCredentials | None, kind: str) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="MFA authentication token is required.")
    payload = verify_access_token(credentials.credentials)
    if not payload or payload.get("role") != "doctor" or payload.get("token_kind") != kind:
        raise HTTPException(status_code=401, detail="Invalid MFA authentication token.")
    return payload


@router.post("/auth/complete-invite")
def complete_invite_route(request: CompleteInviteRequest):
    try:
        account = complete_invite(request.token, request.password)
    except PermissionError as exc:
        _error(exc, 400)
    except ValueError as exc:
        _error(exc, 400)
    token = create_doctor_mfa_enrollment_token(**account)
    return {"status": "password_set", "mfa_enrollment_token": token, "token_type": "bearer"}


@router.post("/auth/mfa/enroll")
def mfa_enroll(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    payload = _mfa_token(credentials, "doctor_mfa_enrollment")
    try:
        uri = start_mfa_enrollment(str(payload["account_id"]))
    except (PermissionError, ValueError, RuntimeError) as exc:
        _error(exc, 400)
    return {"provisioning_uri": uri}


@router.post("/auth/mfa/verify")
def mfa_verify(request: MfaCodeRequest, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    payload = _mfa_token(credentials, "doctor_mfa_enrollment")
    try:
        recovery_codes = verify_mfa_enrollment(str(payload["account_id"]), request.code)
    except PermissionError as exc:
        _error(exc, 400)
    return {"status": "mfa_enabled", "recovery_codes": recovery_codes}


@router.post("/auth/login")
def doctor_login(request: LoginRequest, http_request: Request):
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("login", ip, request.email.strip().lower())
        account_id, doctor_id, email = authenticate_doctor_password(request.email, request.password)
    except PermissionError as exc:
        if str(exc).startswith("Too many"):
            raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "300"})
        _error(exc, 401)
    token = create_doctor_mfa_pending_token(account_id=account_id, doctor_id=doctor_id, email=email)
    return {"status": "mfa_required", "mfa_token": token, "token_type": "bearer"}


@router.post("/auth/mfa/challenge")
def mfa_challenge(request: MfaCodeRequest, http_request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    payload = _mfa_token(credentials, "doctor_mfa_pending")
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("mfa", ip, str(payload["account_id"]))
        doctor_id, email, account_id, recovery_used = complete_mfa_challenge(str(payload["account_id"]), request.code)
    except PermissionError as exc:
        if str(exc).startswith("Too many"):
            raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "300"})
        _error(exc, 401)
    token = create_doctor_session_token(doctor_id=doctor_id, account_id=account_id, email=email)
    return {"status": "authenticated", "access_token": token, "token_type": "bearer", "recovery_code_used": recovery_used}


@router.get("/me")
def doctor_me(doctor: dict = Depends(get_current_doctor)):
    return {"status": "authenticated", "doctor": doctor}
