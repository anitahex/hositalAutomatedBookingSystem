from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.api.dependencies import bearer_scheme, get_current_doctor
from app.services.appointments import doctor_appointments, doctor_patient_detail, doctor_patients
from app.services.consults import list_latest_consult_status_by_booking
from app.services.login_lockout import AccountLockedError
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
    if account["mfa_enabled"]:
        return {"status": "password_reset"}
    token = create_doctor_mfa_enrollment_token(
        doctor_id=account["doctor_id"], account_id=account["account_id"], email=account["email"]
    )
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
    except AccountLockedError as exc:
        # Ahead of the PermissionError branch below, which AccountLockedError subclasses.
        minutes = max(1, round(exc.retry_after_seconds / 60))
        raise HTTPException(
            status_code=423,
            detail={
                "message": f"Too many failed attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
                "retry_after_seconds": exc.retry_after_seconds,
            },
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )
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


@router.get("/appointments")
def doctor_appointments_route(
    scope: str = Query(...),
    doctor: dict = Depends(get_current_doctor),
):
    normalized_scope = scope.strip().lower()
    if normalized_scope not in ("upcoming", "past"):
        raise HTTPException(status_code=400, detail="scope must be 'upcoming' or 'past'.")

    appointments = doctor_appointments(doctor["doctor_id"], normalized_scope)
    consult_by_booking = list_latest_consult_status_by_booking(
        doctor["doctor_id"], [appt["booking_id"] for appt in appointments]
    )
    for appt in appointments:
        consult = consult_by_booking.get(appt["booking_id"])
        appt["consult_id"] = consult["id"] if consult else None
        appt["consult_status"] = consult["status"] if consult else None
        appt["consult_started_at"] = consult["started_at"] if consult else None
        appt["consult_ended_at"] = consult["ended_at"] if consult else None
    return {"appointments": appointments}


@router.get("/patients")
def doctor_patients_route(doctor: dict = Depends(get_current_doctor)):
    return {"patients": doctor_patients(doctor["doctor_id"])}


@router.get("/patients/{patient_id}")
def doctor_patient_detail_route(patient_id: str, doctor: dict = Depends(get_current_doctor)):
    detail = doctor_patient_detail(doctor["doctor_id"], patient_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return detail
