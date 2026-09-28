import logging
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
from app.services.soap_notes import list_shared_notes_for_patient


logger = logging.getLogger(__name__)

router = APIRouter()


def _with_visit_summaries(bookings: list[dict], patient_id: str) -> list[dict]:
    """Attaches the doctor-verified visit summary to any booking whose clinical note has
    been signed AND explicitly shared. One batched query for the whole list — the same
    enrichment shape doctor.py uses for consult status, never a query per row.

    A booking with no shared note gets visit_summary=None, which is the normal case: a
    note is only ever here after a clinician signed it and chose to disclose it.
    """
    try:
        summaries = list_shared_notes_for_patient(patient_id, [b["booking_id"] for b in bookings])
    except Exception as exc:
        # Deliberately non-fatal, and deliberately a broad catch. Listing appointments is
        # this endpoint's actual job; a shared visit summary is an enhancement layered on
        # top of it. The consult/SOAP tables live only in Alembic and the runtime ensure_*
        # helpers — never in app/db/schema.sql — so they can legitimately be absent on a
        # database bootstrapped from that file alone, and a failure over there must not
        # take a patient's appointment list away from them. Degrading this way can only
        # ever HIDE a summary, never expose one, so it cannot fail open.
        logger.error("appointments: could not load shared visit summaries: %s", exc)
        summaries = {}
    for booking in bookings:
        booking["visit_summary"] = summaries.get(booking["booking_id"])
    return bookings
class RescheduleRequest(BaseModel):
    slot_id: str


class BookRequest(BaseModel):
    slot_id: str


@router.get("/departments")
def departments(limit: int = 20, user: dict = Depends(current_user)):
    return {"departments": available_departments(limit=limit)}


@router.get("/doctors")
def doctors(
    department: str,
    date: str | None = None,
    limit: int = 8,
    user: dict = Depends(current_user),
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
    user: dict = Depends(current_user),
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
def available_slots(department: str = "General Physician", limit: int = 5, user: dict = Depends(current_user)):
    return {"slots": first_available_slots(department=department, limit=limit)}


@router.get("/upcoming")
def upcoming_bookings(user: dict = Depends(current_user)):
    bookings = upcoming_bookings_for_patient(patient_id=user["patient_id"], limit=30)
    return {"bookings": _with_visit_summaries(bookings, user["patient_id"])}


@router.get("/previous")
def previous_bookings(user: dict = Depends(current_user)):
    bookings = previous_bookings_for_patient(patient_id=user["patient_id"], limit=30)
    return {"bookings": _with_visit_summaries(bookings, user["patient_id"])}


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
