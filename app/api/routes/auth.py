from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from psycopg2.errors import UniqueViolation
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.admin_auth import authenticate_admin, authenticate_admin_with_lockout
from app.services.tokens import create_access_token
from app.services.users import (
    authenticate_user,
    create_user_with_profile,
    get_user_profile,
    normalize_mobile_number,
    update_patient_profile,
    verify_current_password,
)
from app.services.language import normalize_language
from app.api.dependencies import bearer_scheme, current_user, pending_patient_email, pending_patient_mfa
from app.db.connection import connect_db
from app.services.account_registry import audit, dummy_verify, ensure_registry_schema, lookup
from app.services.doctor_auth import authenticate_doctor_password, check_rate_limit
from app.services.login_lockout import (
    AccountLockedError,
    check_lockout,
    ensure_lockout_schema,
    record_failure,
)
from app.services.email_verification import generate_and_send_code, verify_code
from app.services.password_reset import (
    PURPOSE_CHANGE_PASSWORD,
    check_otp,
    confirm_email_for_mobile,
    resend_otp,
    reset_password,
    start_change_password_otp,
    start_forgot_password,
)
from app.services.patient_mfa import (
    disable_mfa,
    regenerate_backup_codes,
    start_mfa_setup,
    verify_mfa_challenge,
    verify_mfa_setup,
)
from app.services.refresh_tokens import issue_refresh_token, rotate_refresh_token
from app.services.tokens import (
    ACCESS_TOKEN_TTL_SECONDS,
    create_doctor_mfa_pending_token,
    create_patient_email_pending_token,
    create_patient_mfa_pending_token,
    revoke_token,
    verify_access_token,
)


router = APIRouter()


VALID_BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str
    name: str = Field(min_length=2, max_length=100)
    age: int = Field(gt=0, lt=130)
    mobile_number: str
    address: str = Field(min_length=5, max_length=500)
    profile_email: EmailStr
    blood_group: str
    health_issues: str | None = None
    preferred_language: str = "en"

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name cannot be blank.")
        return value

    @field_validator("address")
    @classmethod
    def _validate_address(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Address cannot be blank.")
        return value

    @field_validator("blood_group")
    @classmethod
    def _validate_blood_group(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in VALID_BLOOD_GROUPS:
            raise ValueError("Blood group must be one of: " + ", ".join(sorted(VALID_BLOOD_GROUPS)))
        return normalized

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


def _locked_response(exc: AccountLockedError) -> HTTPException:
    """423 Locked, carrying both a human sentence and the raw seconds.

    detail is an object rather than a bare string so the frontend can drive a live
    countdown off retry_after_seconds (the same key the OTP resend endpoints already
    return) instead of parsing minutes back out of English. Retry-After is set too, for
    anything speaking plain HTTP rather than this app's JSON.
    """
    minutes = max(1, round(exc.retry_after_seconds / 60))
    return HTTPException(
        status_code=423,
        detail={
            "message": f"Too many failed attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
            "retry_after_seconds": exc.retry_after_seconds,
        },
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


@router.post("/unified-login")
def unified_login(request: LoginRequest, http_request: Request):
    email = request.email.strip().lower()
    with connect_db() as conn:
        ensure_registry_schema(conn)
        with conn.cursor() as cur:
            registered = lookup(cur, email)
    if not registered:
        dummy_verify(request.password)
        # An unregistered email is counted and locked on exactly the same schedule as a
        # real one. Without this, "locked, try again in N minutes" would appear only for
        # addresses that actually have accounts — handing an attacker a reliable way to
        # test whether any given email is registered here.
        with connect_db() as conn:
            ensure_registry_schema(conn)
            ensure_lockout_schema(conn)
            with conn.cursor() as cur:
                try:
                    check_lockout(cur, email)
                except AccountLockedError as exc:
                    audit(cur, email, None, "login_rejected_locked")
                    conn.commit()
                    raise _locked_response(exc)
                record_failure(cur, email)
                audit(cur, email, None, "login_failure")
            conn.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    account_type, account_id = registered
    ip = http_request.client.host if http_request.client else "unknown"
    # Hoisted out of the three role branches (where it was identical) and given its own
    # handler: inside the try below, this raises PermissionError and would be caught by
    # the same branch as a wrong password, reporting "invalid email or password" for what
    # is actually throttling — the same misleading-message trap the lockout had.
    try:
        check_rate_limit("login", ip, str(account_id))
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "300"})
    try:
        if account_type == "doctor":
            aid, did, db_email = authenticate_doctor_password(email, request.password)
            token = create_doctor_mfa_pending_token(account_id=aid, doctor_id=did, email=db_email)
            result={"status":"mfa_required","mfa_token":token,"token_type":"bearer"}
        elif account_type == "admin":
            result=authenticate_admin_with_lockout(email, request.password)
            if not result: raise PermissionError
            # Re-mint the access token at the short refresh-backed TTL and attach a
            # refresh token, rather than threading expires_in_seconds through
            # authenticate_admin_with_lockout — keeps that function's signature (and
            # its own legacy default-TTL callers) untouched.
            admin_id = result["account_id"]
            result["access_token"] = create_access_token(
                subject=admin_id, email=result["email"], role="admin",
                expires_in_seconds=ACCESS_TOKEN_TTL_SECONDS,
            )
            result["refresh_token"] = issue_refresh_token(user_id=admin_id, role="admin", email=result["email"])
            result={"status":"authenticated", **result}
        else:
            profile=authenticate_user(email, request.password)
            if not profile: raise PermissionError
            if not profile.get("email_verified", True):
                # Correct password, but the account never finished email verification
                # (e.g. the patient closed the tab mid-signup) — resume that flow with a
                # fresh code instead of a dead-end "invalid credentials" error.
                pending_token = create_patient_email_pending_token(user_id=profile["patient_id"], email=profile["login_email"])
                generate_and_send_code(profile["patient_id"], profile["login_email"])
                result={"status":"verification_required","pending_token":pending_token,"token_type":"bearer","email":profile["login_email"]}
            elif profile.get("mfa_enabled"):
                # Email-verified and password correct, but this account has opted
                # into TOTP MFA — challenge for it before issuing a real session.
                # Must come strictly after the email-verified branch above (an
                # unverified account with MFA somehow enabled still resumes
                # verification first, never the MFA challenge).
                # Deliberately NOT "mfa_required" (the doctor flow's status, whose
                # response carries mfa_token not pending_token) — a distinct status
                # avoids ambiguity for whoever wires up the frontend for this later.
                mfa_pending_token = create_patient_mfa_pending_token(user_id=profile["patient_id"], email=profile["login_email"])
                result={"status":"patient_mfa_required","pending_token":mfa_pending_token,"token_type":"bearer"}
            else:
                token=create_access_token(patient_id=profile["patient_id"],email=profile["login_email"],role="patient", expires_in_seconds=ACCESS_TOKEN_TTL_SECONDS)
                refresh_token=issue_refresh_token(user_id=profile["patient_id"], role="patient", email=profile["login_email"])
                result={"status":"authenticated","access_token":token,"refresh_token":refresh_token,"token_type":"bearer","user":profile}
    except AccountLockedError as exc:
        # Must precede the PermissionError handler below — AccountLockedError subclasses
        # it, so catching the broader one first would collapse the countdown back into an
        # indistinguishable 401.
        with connect_db() as conn:
            ensure_registry_schema(conn)
            with conn.cursor() as cur: audit(cur,email,account_type,"login_rejected_locked")
        raise _locked_response(exc)
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
def signup(request: SignupRequest, http_request: Request):
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("signup", ip, request.email.strip().lower())
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc))

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

    # The account exists but is not usable yet — no access_token is issued here.
    # Only a short-lived pending token is returned, just enough to submit the code
    # sent to the account's login email (see /auth/verify-email below).
    generate_and_send_code(profile["patient_id"], profile["login_email"])
    pending_token = create_patient_email_pending_token(
        user_id=profile["patient_id"],
        email=profile["login_email"],
    )
    return {
        "status": "verification_required",
        "pending_token": pending_token,
        "token_type": "bearer",
        "email": profile["login_email"],
    }


class VerifyEmailRequest(BaseModel):
    code: str


@router.post("/verify-email")
def verify_email(request: VerifyEmailRequest, pending: dict = Depends(pending_patient_email)):
    if not verify_code(pending["user_id"], request.code):
        raise HTTPException(status_code=400, detail="That code is invalid or has expired.")

    profile = get_user_profile(pending["user_id"])
    token = create_access_token(
        patient_id=profile["patient_id"],
        email=profile["login_email"],
        role="patient",
        expires_in_seconds=ACCESS_TOKEN_TTL_SECONDS,
    )
    refresh_token = issue_refresh_token(user_id=profile["patient_id"], role="patient", email=profile["login_email"])
    return {"status": "authenticated", "access_token": token, "refresh_token": refresh_token, "token_type": "bearer", "user": profile}


@router.post("/resend-verification")
def resend_verification(http_request: Request, pending: dict = Depends(pending_patient_email)):
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("email_verify_resend", ip, pending["user_id"])
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc))

    generate_and_send_code(pending["user_id"], pending["email"])
    return {"status": "sent"}


@router.post("/login")
def login(request: LoginRequest):
    try:
        profile = authenticate_user(request.email, request.password)
    except AccountLockedError as exc:
        raise _locked_response(exc)
    if not profile:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not profile.get("email_verified", True):
        generate_and_send_code(profile["patient_id"], profile["login_email"])
        pending_token = create_patient_email_pending_token(
            user_id=profile["patient_id"],
            email=profile["login_email"],
        )
        return {
            "status": "verification_required",
            "pending_token": pending_token,
            "token_type": "bearer",
            "email": profile["login_email"],
        }

    if profile.get("mfa_enabled"):
        # Must come strictly after the email-verified check above — see
        # unified_login's matching branch for why.
        mfa_pending_token = create_patient_mfa_pending_token(user_id=profile["patient_id"], email=profile["login_email"])
        return {"status": "patient_mfa_required", "pending_token": mfa_pending_token, "token_type": "bearer"}

    token = create_access_token(
        patient_id=profile["patient_id"],
        email=profile["login_email"],
        role="patient",
        expires_in_seconds=ACCESS_TOKEN_TTL_SECONDS,
    )
    refresh_token = issue_refresh_token(user_id=profile["patient_id"], role="patient", email=profile["login_email"])
    return {"status": "authenticated", "access_token": token, "refresh_token": refresh_token, "token_type": "bearer", "user": profile}


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh(request: RefreshRequest):
    """No auth header — the refresh token itself is the credential. Covers patient and
    admin sessions only; doctor sessions don't use refresh tokens (see the plan)."""
    result = rotate_refresh_token(request.refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    new_refresh_token, user_id, role, email = result
    access_token = create_access_token(
        subject=user_id, email=email, role=role, expires_in_seconds=ACCESS_TOKEN_TTL_SECONDS,
    )
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}


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


class ChangePasswordStartRequest(BaseModel):
    current_password: str


@router.post("/change-password/start")
def change_password_start(request: ChangePasswordStartRequest, http_request: Request, user: dict = Depends(current_user)):
    """Step 1 of the OTP-gated change-password flow: verify identity, then mail a
    confirmation code. Does not change the password yet — see /change-password/confirm."""
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("change_password_start", ip, user["patient_id"])
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc))

    if not verify_current_password(user["patient_id"], request.current_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    return start_change_password_otp(user["login_email"])


@router.post("/change-password/resend")
def change_password_resend(http_request: Request, user: dict = Depends(current_user)):
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("change_password_resend", ip, user["patient_id"])
    except PermissionError:
        return {"status": "rate_limited"}

    return resend_otp(user["login_email"], purpose=PURPOSE_CHANGE_PASSWORD)


class ChangePasswordOtpRequest(BaseModel):
    otp: str


@router.post("/change-password/verify-otp")
def change_password_verify_otp(request: ChangePasswordOtpRequest, http_request: Request, user: dict = Depends(current_user)):
    """Step 2 of 3: confirm the emailed code before showing the new-password fields, so
    a wrong code is caught there rather than after the user has typed a new password
    twice. The code is checked but not consumed — /confirm below still needs it."""
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("change_password_verify_otp", ip, user["patient_id"])
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc))

    if not check_otp(user["login_email"], request.otp, purpose=PURPOSE_CHANGE_PASSWORD):
        raise HTTPException(status_code=400, detail="That code is invalid, has expired, or has already been used.")
    return {"status": "otp_verified"}


class ChangePasswordConfirmRequest(BaseModel):
    otp: str
    new_password: str
    confirm_password: str


@router.post("/change-password/confirm")
def change_password_confirm(request: ChangePasswordConfirmRequest, user: dict = Depends(current_user)):
    try:
        success = reset_password(
            user["login_email"], request.otp, request.new_password, request.confirm_password,
            purpose=PURPOSE_CHANGE_PASSWORD,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not success:
        raise HTTPException(status_code=400, detail="That code is invalid, has expired, or has already been used.")

    return {"status": "password_changed"}


@router.post("/mfa/setup/start")
def mfa_setup_start(user: dict = Depends(current_user)):
    try:
        provisioning_uri = start_mfa_setup(user["patient_id"])
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {"provisioning_uri": provisioning_uri}


class MfaCodeRequest(BaseModel):
    code: str


def _check_patient_mfa_rate_limit(http_request: Request, account_key: str) -> None:
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("patient_mfa", ip, account_key)
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc))


@router.post("/mfa/setup/verify")
def mfa_setup_verify(request: MfaCodeRequest, http_request: Request, user: dict = Depends(current_user)):
    _check_patient_mfa_rate_limit(http_request, user["patient_id"])
    try:
        recovery_codes = verify_mfa_setup(user["patient_id"], request.code)
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"status": "mfa_enabled", "recovery_codes": recovery_codes}


@router.post("/mfa/verify")
def mfa_verify(request: MfaCodeRequest, http_request: Request, pending: dict = Depends(pending_patient_mfa)):
    _check_patient_mfa_rate_limit(http_request, pending["user_id"])
    if not verify_mfa_challenge(pending["user_id"], request.code):
        raise HTTPException(status_code=400, detail="Invalid MFA code.")

    profile = get_user_profile(pending["user_id"])
    token = create_access_token(
        patient_id=profile["patient_id"], email=profile["login_email"], role="patient",
        expires_in_seconds=ACCESS_TOKEN_TTL_SECONDS,
    )
    refresh_token = issue_refresh_token(user_id=profile["patient_id"], role="patient", email=profile["login_email"])
    return {"status": "authenticated", "access_token": token, "refresh_token": refresh_token, "token_type": "bearer", "user": profile}


class MfaDisableRequest(BaseModel):
    current_password: str
    code: str


@router.post("/mfa/disable")
def mfa_disable(request: MfaDisableRequest, http_request: Request, user: dict = Depends(current_user)):
    _check_patient_mfa_rate_limit(http_request, user["patient_id"])
    try:
        disable_mfa(user["patient_id"], request.current_password, request.code)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    return {"status": "mfa_disabled"}


@router.post("/mfa/backup-codes/regenerate")
def mfa_backup_codes_regenerate(request: MfaCodeRequest, http_request: Request, user: dict = Depends(current_user)):
    _check_patient_mfa_rate_limit(http_request, user["patient_id"])
    try:
        recovery_codes = regenerate_backup_codes(user["patient_id"], request.code)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    return {"status": "backup_codes_regenerated", "recovery_codes": recovery_codes}


class ForgotPasswordStartRequest(BaseModel):
    identifier: str


@router.post("/forgot-password/start")
def forgot_password_start(request: ForgotPasswordStartRequest):
    return start_forgot_password(request.identifier)


class ConfirmEmailRequest(BaseModel):
    mobile_number: str
    email: str


@router.post("/forgot-password/confirm-email")
def forgot_password_confirm_email(request: ConfirmEmailRequest, http_request: Request):
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("forgot_password_confirm_email", ip, request.mobile_number)
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc))

    return confirm_email_for_mobile(request.mobile_number, request.email)


class ResendOtpRequest(BaseModel):
    email: str


@router.post("/resend-otp")
def resend_otp_route(request: ResendOtpRequest, http_request: Request):
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("password_reset_resend", ip, request.email.strip().lower(), limit=5, window_seconds=3600)
    except PermissionError:
        return {"status": "rate_limited"}

    return resend_otp(request.email)


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str
    confirm_password: str


@router.post("/reset-password")
def reset_password_route(request: ResetPasswordRequest):
    try:
        success = reset_password(
            request.email, request.otp, request.new_password, request.confirm_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not success:
        raise HTTPException(status_code=400, detail="That code is invalid, has expired, or has already been used.")

    return {"status": "password_reset"}


class UpdateProfileRequest(BaseModel):
    # No email or mobile_number: both identify the account, so they are read-only here
    # and would need their own verified change flow rather than a silent profile edit.
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    age: int | None = Field(default=None, gt=0, lt=130)
    gender: str | None = None
    health_issues: str | None = None
    address: str | None = None
    preferred_language: str | None = None


@router.patch("/profile")
def update_profile(request: UpdateProfileRequest, user: dict = Depends(current_user)):
    try:
        updated = update_patient_profile(
            patient_id=user["patient_id"],
            first_name=request.first_name,
            last_name=request.last_name,
            age=request.age,
            gender=request.gender,
            health_issues=request.health_issues,
            address=request.address,
            preferred_language=normalize_language(request.preferred_language) if request.preferred_language else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return {"status": "updated", "user": updated}
