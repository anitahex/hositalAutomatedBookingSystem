from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.admin_auth import get_admin_account_by_email
from app.services.tokens import verify_access_token
from app.services.users import get_user_profile
from app.services.doctor_auth import get_doctor_profile


bearer_scheme = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication token is required.")

    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")

    if payload.get("role") not in (None, "patient"):
        raise HTTPException(status_code=401, detail="Patient authentication is required.")

    # A real patient session token never carries a token_kind claim (only special-
    # purpose tokens do, e.g. patient_email_pending below) — reject any such token
    # here so a pending-verification token can't be used as a full session token.
    if payload.get("token_kind") is not None:
        raise HTTPException(status_code=401, detail="Patient authentication is required.")

    profile = get_user_profile(payload["sub"])
    if not profile:
        raise HTTPException(status_code=401, detail="User account was not found.")

    # A token issued before the account's last password change is stale — reject it so
    # changing/resetting a password actually invalidates any session token issued
    # under the old password. password_changed_at is NULL for every pre-existing
    # account (no backfill on that migration), which is deliberately treated as "never
    # invalidated" so this never force-logs-out an account that hasn't changed its
    # password since this check was added.
    # iat carries full sub-second precision (see tokens.py::create_access_token) so
    # this correctly orders a token against a password change even within the same
    # wall-clock second.
    password_changed_at = profile.get("password_changed_at")
    if password_changed_at is not None and payload.get("iat", 0) < password_changed_at.timestamp():
        raise HTTPException(status_code=401, detail="Session has expired due to a password change. Please log in again.")

    return profile


def pending_patient_email(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """Gate for /auth/verify-email and /auth/resend-verification: a short-lived token
    that proves 'this signup just happened' without granting real session access —
    mirrors get_current_doctor's doctor_mfa_pending check. Deliberately does not fetch
    the user profile: the account isn't usable yet, so there's nothing to return but
    the identity the code should be checked against."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Verification session is required.")

    payload = verify_access_token(credentials.credentials)
    if (
        not payload
        or payload.get("role") != "patient"
        or payload.get("token_kind") != "patient_email_pending"
    ):
        raise HTTPException(status_code=401, detail="Verification session is invalid or has expired.")

    return {"user_id": payload["sub"], "email": payload.get("email")}


def pending_patient_mfa(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """Gate for /auth/mfa/verify — mirrors pending_patient_email exactly, checking
    token_kind == "patient_mfa_pending" instead. This is the exact bug class from the
    email-verification incident: current_user already rejects any token carrying a
    non-None token_kind, so this pending token is automatically unusable against a
    real protected route with zero additional code there."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="MFA challenge session is required.")

    payload = verify_access_token(credentials.credentials)
    if (
        not payload
        or payload.get("role") != "patient"
        or payload.get("token_kind") != "patient_mfa_pending"
    ):
        raise HTTPException(status_code=401, detail="MFA challenge session is invalid or has expired.")

    return {"user_id": payload["sub"], "email": payload.get("email")}


def current_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication token is required.")

    payload = verify_access_token(credentials.credentials)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Admin authentication is required.")

    email = str(payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Admin account was not found.")

    admin = get_admin_account_by_email(email)
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin account was not found.")

    return {"role": "admin", "email": admin.email, "name": admin.name}


def get_current_doctor(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Doctor authentication is required.")
    payload = verify_access_token(credentials.credentials)
    if (
        not payload
        or payload.get("role") != "doctor"
        or payload.get("token_kind") != "doctor_session"
        or payload.get("sub") != payload.get("doctor_id")
    ):
        raise HTTPException(status_code=401, detail="Doctor authentication is required.")
    profile = get_doctor_profile(str(payload["doctor_id"]), str(payload.get("account_id") or ""))
    if not profile:
        raise HTTPException(status_code=401, detail="Doctor account was not found.")
    return profile
