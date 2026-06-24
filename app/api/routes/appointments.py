from datetime import date as dt_date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import current_user
from app.services.appointments import (
    available_departments,
    available_doctors_for_department,
    available_doctors_for_department_on_date,
    available_slots_for_doctor,
    available_slots_for_doctor_on_date,
    book_selected_slot,
    cancel_patient_booking,
    first_available_slots,
    previous_bookings_for_patient,
    reschedule_options_for_booking,
    reschedule_patient_booking,
    upcoming_bookings_for_patient,
)


router = APIRouter()
class RescheduleRequest(BaseModel):
    slot_id: str


class BookRequest(BaseModel):
    slot_id: str


@router.get("/departments")
def departments(limit: int = 20):
    return {"departments": available_departments(limit=limit)}


@router.get("/doctors")
def doctors(
    department: str,
    date: str | None = None,
    limit: int = 8,
):
    if date:
        doctors = available_doctors_for_department_on_date(department=department, requested_date=date, limit=limit)
    else:
        doctors = available_doctors_for_department(department=department, limit=limit)
    return {"doctors": doctors}


@router.get("/slots")
def slots(
    doctor_id: str,
    date: str | None = None,
    limit: int = 8,
):
    if date:
        slots = available_slots_for_doctor_on_date(doctor_id=doctor_id, requested_date=date, limit=limit)
    else:
        slots = available_slots_for_doctor(doctor_id=doctor_id, limit=limit)
    return {"slots": slots}


@router.post("/book")
def book_slot(request: BookRequest, user: dict = Depends(current_user)):
    booking = book_selected_slot(slot_id=request.slot_id, patient_id=user["patient_id"])
    if not booking:
        raise HTTPException(
            status_code=400,
            detail="This slot is no longer available or is outside the booking window.",
        )
    return {"booking": booking}


@router.get("/available")
def available_slots(department: str = "General Physician", limit: int = 5):
    return {"slots": first_available_slots(department=department, limit=limit)}


@router.get("/upcoming")
def upcoming_bookings(user: dict = Depends(current_user)):
    return {
        "bookings": upcoming_bookings_for_patient(
            patient_id=user["patient_id"],
            limit=30,
        )
    }


@router.get("/previous")
def previous_bookings(user: dict = Depends(current_user)):
    return {
        "bookings": previous_bookings_for_patient(
            patient_id=user["patient_id"],
            limit=30,
        )
    }


@router.post("/{booking_id}/cancel")
def cancel_upcoming_booking(booking_id: str, user: dict = Depends(current_user)):
    booking = cancel_patient_booking(
        booking_id=booking_id,
        patient_id=user["patient_id"],
    )
    if not booking:
        raise HTTPException(
            status_code=400,
            detail="This booking cannot be cancelled. Changes are allowed only more than 24 hours before the appointment.",
        )
    return {"booking": booking}


@router.get("/{booking_id}/reschedule-options")
def reschedule_options(
    booking_id: str,
    date: str,
    user: dict = Depends(current_user),
):
    try:
        requested_date = dt_date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Please provide the date in YYYY-MM-DD format.")

    slots = reschedule_options_for_booking(
        booking_id=booking_id,
        patient_id=user["patient_id"],
        requested_date=requested_date.isoformat(),
        limit=10,
    )
    return {"slots": slots}


@router.post("/{booking_id}/reschedule")
def reschedule_booking(
    booking_id: str,
    request: RescheduleRequest,
    user: dict = Depends(current_user),
):
    booking = reschedule_patient_booking(
        booking_id=booking_id,
        patient_id=user["patient_id"],
        new_slot_id=request.slot_id,
    )
    if not booking:
        raise HTTPException(
            status_code=400,
            detail="This booking cannot be changed. Changes are allowed only more than 24 hours before the appointment and the selected slot must be available.",
        )
    return {"booking": booking}
