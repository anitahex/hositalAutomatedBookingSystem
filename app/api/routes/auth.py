from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(_: LoginRequest):
    return {
        "status": "pending_2fa",
        "message": "Auth/2FA boundary is reserved for the application layer.",
    }


@router.post("/2fa/verify")
def verify_2fa():
    return {"status": "verified"}
