from fastapi import APIRouter, Depends, HTTPException
from psycopg2.errors import UniqueViolation
from pydantic import BaseModel, Field

from app.services.admin_auth import authenticate_admin
from app.services.tokens import create_access_token
from app.services.users import authenticate_user, create_user_with_profile, update_patient_profile
from app.api.dependencies import current_user


router = APIRouter()


class SignupRequest(BaseModel):
    email: str
    password: str
    confirm_password: str
    name: str
    age: int = Field(gt=0, lt=130)
    mobile_number: str
    address: str
    profile_email: str
    blood_group: str
    health_issues: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


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
def admin_login(request: AdminLoginRequest):
    admin = authenticate_admin(request.email, request.password)
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid admin email or password.")
    return {"status": "authenticated", **admin}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {"status": "authenticated", "user": user}


class UpdateProfileRequest(BaseModel):
    health_issues: str | None = None
    mobile_number: str | None = None
    address: str | None = None


@router.patch("/profile")
def update_profile(request: UpdateProfileRequest, user: dict = Depends(current_user)):
    updated = update_patient_profile(
        patient_id=user["patient_id"],
        health_issues=request.health_issues,
        mobile_number=request.mobile_number,
        address=request.address,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return {"status": "updated", "user": updated}
