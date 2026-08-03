from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.admin_auth import get_admin_account_by_email
from app.services.tokens import verify_access_token
from app.services.users import get_user_profile


bearer_scheme = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication token is required.")

    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")

    if payload.get("role") not in (None, "patient"):
        raise HTTPException(status_code=401, detail="Patient authentication is required.")

    profile = get_user_profile(payload["sub"])
    if not profile:
        raise HTTPException(status_code=401, detail="User account was not found.")

    return profile


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
