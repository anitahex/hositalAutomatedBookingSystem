from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from psycopg2.errors import UniqueViolation
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.admin_auth import authenticate_admin, authenticate_admin_with_lockout
from app.services.tokens import create_access_token
from app.services.users import (
    authenticate_user,
    create_user_with_profile,
    normalize_mobile_number,
    update_patient_profile,
)
from app.services.language import normalize_language
from app.api.dependencies import bearer_scheme, current_user
from app.db.connection import connect_db
from app.services.account_registry import audit, dummy_verify, ensure_registry_schema, lookup
from app.services.doctor_auth import authenticate_doctor_password, check_rate_limit
from app.services.tokens import create_doctor_mfa_pending_token, revoke_token, verify_access_token


router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str
    name: str
    age: int = Field(gt=0, lt=130)
    mobile_number: str
    address: str
    profile_email: EmailStr
    blood_group: str
    health_issues: str | None = None
    preferred_language: str = "en"

    @field_validator("mobile_number")
    @classmethod
    def _validate_mobile_number(cls, value: str) -> str:
        # Same normalization used for WhatsApp-sender matching (app/services/users.py) —
        # accept the same digit-count range that produces a plausible phone number,
        # reject anything else at the boundary instead of storing it unvalidated
        # (see FULL_SYSTEM_AUDIT.md P1 #14).
        normalized = normalize_mobile_number(value)
        digit_count = len(normalized.lstrip("+"))
        if not (7 <= digit_count <= 15):
            raise ValueError("Mobile number must contain 7 to 15 digits.")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/unified-login")
def unified_login(request: LoginRequest, http_request: Request):
    email = request.email.strip().lower()
    with connect_db() as conn:
        ensure_registry_schema(conn)
        with conn.cursor() as cur:
            registered = lookup(cur, email)
    if not registered:
        dummy_verify(request.password)
        with connect_db() as conn:
            ensure_registry_schema(conn)
            with conn.cursor() as cur: audit(cur,email,None,"login_failure")
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    account_type, account_id = registered
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        if account_type == "doctor":
            check_rate_limit("login", ip, str(account_id))
            aid, did, db_email = authenticate_doctor_password(email, request.password)
            token = create_doctor_mfa_pending_token(account_id=aid, doctor_id=did, email=db_email)
            result={"status":"mfa_required","mfa_token":token,"token_type":"bearer"}
        elif account_type == "admin":
            check_rate_limit("login", ip, str(account_id))
            result=authenticate_admin_with_lockout(email, request.password)
            if not result: raise PermissionError
            result={"status":"authenticated", **result}
        else:
            check_rate_limit("login", ip, str(account_id))
            profile=authenticate_user(email, request.password)
            if not profile: raise PermissionError
            token=create_access_token(patient_id=profile["patient_id"],email=profile["login_email"],role="patient")
            result={"status":"authenticated","access_token":token,"token_type":"bearer","user":profile}
    except PermissionError:
        with connect_db() as conn:
            ensure_registry_schema(conn)
            with conn.cursor() as cur: audit(cur,email,account_type,"login_failure")
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    with connect_db() as conn:
        ensure_registry_schema(conn)
        with conn.cursor() as cur: audit(cur,email,account_type,"login_success")
    return result


@router.post("/signup")
def signup(request: SignupRequest):
    try:
        profile = create_user_with_profile(
            email=request.email,
            password=request.password,
            confirm_password=request.confirm_password,
            name=request.name,
            age=request.age,
            mobile_number=request.mobile_number,
            address=request.address,
            profile_email=request.profile_email,
            blood_group=request.blood_group,
            health_issues=request.health_issues,
            preferred_language=normalize_language(request.preferred_language) or "en",
        )
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    token = create_access_token(
        patient_id=profile["patient_id"],
        email=profile["login_email"],
        role="patient",
    )
    return {"status": "created", "access_token": token, "token_type": "bearer", "user": profile}


@router.post("/login")
def login(request: LoginRequest):
    profile = authenticate_user(request.email, request.password)
    if not profile:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(
        patient_id=profile["patient_id"],
        email=profile["login_email"],
        role="patient",
    )
    return {"status": "authenticated", "access_token": token, "token_type": "bearer", "user": profile}


class AdminLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/admin/login")
def admin_login(request: AdminLoginRequest, http_request: Request):
    """Compatibility endpoint; now follows the protected unified-login path."""
    return unified_login(LoginRequest(email=request.email, password=request.password), http_request)


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {"status": "authenticated", "user": user}


@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """Role-agnostic: works for a patient, doctor, or admin session token alike, since
    all three are verified through the same verify_access_token/jti mechanism
    (FULL_SYSTEM_AUDIT.md P1 #7 — previously there was no server-side way to invalidate
    a token before its natural expiry for any role). Revokes only the presented token,
    not all of that account's sessions."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication token is required.")

    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")

    revoke_token(payload.get("jti"), int(payload.get("exp") or 0))
    return {"status": "logged_out"}


class UpdateProfileRequest(BaseModel):
    health_issues: str | None = None
    mobile_number: str | None = None
    address: str | None = None
    preferred_language: str | None = None


@router.patch("/profile")
def update_profile(request: UpdateProfileRequest, user: dict = Depends(current_user)):
    updated = update_patient_profile(
        patient_id=user["patient_id"],
        health_issues=request.health_issues,
        mobile_number=request.mobile_number,
        address=request.address,
        preferred_language=normalize_language(request.preferred_language) if request.preferred_language else None,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return {"status": "updated", "user": updated}
