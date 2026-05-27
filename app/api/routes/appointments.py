from fastapi import APIRouter

from app.services.appointments import first_available_slots


router = APIRouter()


@router.get("/available")
def available_slots(department: str = "General Physician", limit: int = 5):
    return {"slots": first_available_slots(department=department, limit=limit)}
