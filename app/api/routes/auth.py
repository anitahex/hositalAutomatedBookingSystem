from fastapi import APIRouter, HTTPException
from psycopg2.errors import UniqueViolation
from pydantic import BaseModel, Field

from app.services.tokens import create_access_token
from app.services.users import authenticate_user, create_user_with_profile


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
    )
    return {"status": "authenticated", "access_token": token, "token_type": "bearer", "user": profile}


@router.post("/2fa/verify")
def verify_2fa():
    return {"status": "verified"}
