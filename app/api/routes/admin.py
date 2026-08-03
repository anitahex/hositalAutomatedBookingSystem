from __future__ import annotations

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.dependencies import current_admin
from app.db.connection import connect_db
from app.services.admin_management import (
    create_doctor,
    create_holiday,
    create_slot,
    create_slot_series,
    list_doctors,
    list_holidays,
    list_slots,
    set_holiday_active,
    set_slot_active,
    update_doctor,
)
from app.services.appointments import ensure_booking_schema


router = APIRouter()


class DoctorRequest(BaseModel):
    name: str
    department: str
    experience_years: int = Field(ge=0, le=80)
    is_active: bool = True


class SlotRequest(BaseModel):
    doctor_id: str
    start_date: date | None = None
    end_date: date | None = None
    work_start_time: time | None = None
    lunch_start_time: time | None = None
    lunch_end_time: time | None = None
    work_end_time: time | None = None
    slot_duration_minutes: int | None = Field(default=None, ge=5, le=480)
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool = True


class HolidayRequest(BaseModel):
    doctor_id: str | None = None
    scope: str = "universal"
    start_date: date
    end_date: date
    reason: str | None = None
    is_active: bool = True


class ToggleRequest(BaseModel):
    is_active: bool = True


def _clinical_summary_expression(cur) -> str:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
            AND table_name = 'appointment_bookings'
            AND column_name IN ('clinical_summary', 'booking_note')
        """
    )
    columns = {row[0] for row in cur.fetchall()}

    if "clinical_summary" in columns and "booking_note" in columns:
        return "COALESCE(b.clinical_summary, b.booking_note)"
    if "clinical_summary" in columns:
        return "b.clinical_summary"
    if "booking_note" in columns:
        return "b.booking_note"
    return "NULL::text"


def _appointment_state(status: str | None, appointment_time) -> str:
    status_value = (status or "").lower()
    if status_value in {"cancelled", "completed"}:
        return "past"

    if appointment_time is not None:
        # Future-dated booked appointments are considered upcoming.
        try:
            from datetime import datetime

            now = datetime.now().astimezone()
            if appointment_time.tzinfo is None:
                appointment_time = appointment_time.replace(tzinfo=now.tzinfo)
            if appointment_time <= now:
                return "past"
        except Exception:
            pass

    return "upcoming"


@router.get("/analytics/summary")
def analytics_summary(admin: dict = Depends(current_admin)):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM doctors;")
            doctors = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM appointment_slots;")
            slots = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM schedule_holidays WHERE is_active = TRUE;")
            holidays = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM appointment_bookings;")
            bookings = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(*)
                FROM appointment_bookings
                WHERE status = 'booked' AND end_time > NOW();
                """
            )
            active_bookings = cur.fetchone()[0]

    return {
        "doctors": doctors,
        "appointment_slots": slots,
        "holidays": holidays,
        "bookings": bookings,
        "active_bookings": active_bookings,
    }


@router.get("/me")
def admin_me(admin: dict = Depends(current_admin)):
    return {"status": "authenticated", "admin": admin}


@router.get("/departments")
def admin_departments(admin: dict = Depends(current_admin)):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT department, COUNT(*) AS doctor_count
                FROM doctors
                GROUP BY department
                ORDER BY department ASC;
                """
            )
            rows = cur.fetchall()

    return {
        "departments": [
            {"department": department, "doctor_count": int(doctor_count)}
            for department, doctor_count in rows
        ]
    }


@router.get("/doctors")
def admin_doctors(admin: dict = Depends(current_admin)):
    return {"doctors": list_doctors()}


@router.post("/doctors")
def admin_create_doctor(request: DoctorRequest, admin: dict = Depends(current_admin)):
    try:
        doctor = create_doctor(
            name=request.name,
            department=request.department,
            experience_years=request.experience_years,
            is_active=request.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"doctor": doctor}


@router.patch("/doctors/{doctor_id}")
def admin_update_doctor(doctor_id: str, request: DoctorRequest, admin: dict = Depends(current_admin)):
    try:
        doctor = update_doctor(
            doctor_id,
            name=request.name,
            department=request.department,
            experience_years=request.experience_years,
            is_active=request.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found.")
    return {"doctor": doctor}


@router.get("/slots")
def admin_slots(doctor_id: str | None = None, upcoming_only: bool = True, admin: dict = Depends(current_admin)):
    return {"slots": list_slots(doctor_id=doctor_id, upcoming_only=upcoming_only)}


@router.post("/slots")
def admin_create_slot(request: SlotRequest, admin: dict = Depends(current_admin)):
    try:
        if request.start_time and request.end_time and not request.start_date and not request.end_date:
            slot = create_slot(
                doctor_id=request.doctor_id,
                start_time=request.start_time,
                end_time=request.end_time,
                is_active=request.is_active,
            )
            return {"slot": slot, "created_slots": 1}

        if not all(
            [
                request.start_date,
                request.end_date,
                request.work_start_time,
                request.work_end_time,
                request.slot_duration_minutes,
            ]
        ):
            raise HTTPException(
                status_code=400,
                detail="Provide start_date, end_date, work_start_time, work_end_time, and slot_duration_minutes.",
            )

        if request.end_date < request.start_date:
            raise HTTPException(status_code=400, detail="End date must be on or after start date.")

        lunch_start = request.lunch_start_time
        lunch_end = request.lunch_end_time
        if bool(lunch_start) ^ bool(lunch_end):
            raise HTTPException(status_code=400, detail="Provide both lunch start and lunch end, or leave both empty.")

        slots = create_slot_series(
            doctor_id=request.doctor_id,
            start_date=request.start_date,
            end_date=request.end_date,
            work_start_time=request.work_start_time,
            work_end_time=request.work_end_time,
            lunch_start_time=lunch_start,
            lunch_end_time=lunch_end,
            slot_duration_minutes=request.slot_duration_minutes,
            is_active=request.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not slots:
        raise HTTPException(status_code=400, detail="Unable to create slots.")
    return {"created_slots": len(slots), "slots": slots}


@router.patch("/slots/{slot_id}")
def admin_toggle_slot(slot_id: str, request: ToggleRequest, admin: dict = Depends(current_admin)):
    updated = set_slot_active(slot_id, request.is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="Slot not found.")
    return {"status": "updated"}


@router.get("/holidays")
def admin_holidays(admin: dict = Depends(current_admin)):
    return {"holidays": list_holidays()}


@router.post("/holidays")
def admin_create_holiday(request: HolidayRequest, admin: dict = Depends(current_admin)):
    try:
        holiday = create_holiday(
            doctor_id=request.doctor_id if request.scope == "doctor" else None,
            start_date=request.start_date,
            end_date=request.end_date,
            reason=request.reason,
            is_active=request.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"holiday": holiday}


@router.patch("/holidays/{holiday_id}")
def admin_toggle_holiday(holiday_id: str, request: ToggleRequest, admin: dict = Depends(current_admin)):
    updated = set_holiday_active(holiday_id, request.is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="Holiday not found.")
    return {"status": "updated"}


@router.get("/appointments")
def appointment_dashboard(
    admin: dict = Depends(current_admin),
    doctor_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    normalized_status = status.lower().strip() if status else None
    if normalized_status and normalized_status not in {"upcoming", "past"}:
        raise HTTPException(status_code=400, detail="status must be either 'upcoming' or 'past'.")

    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            clinical_summary_expr = _clinical_summary_expression(cur)

            where_clauses: list[str] = []
            params: list[object] = []

            if doctor_id:
                where_clauses.append("b.doctor_id::text = %s")
                params.append(doctor_id)

            if normalized_status == "upcoming":
                where_clauses.append("b.status = 'booked' AND b.start_time >= NOW()")
            elif normalized_status == "past":
                where_clauses.append("(b.status IN ('completed', 'cancelled') OR b.start_time < NOW())")

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            cur.execute(
                f"""
                SELECT
                    b.booking_id,
                    b.doctor_id,
                    b.patient_id,
                    COALESCE(pp.name, b.patient_id, 'Unknown patient') AS patient_name,
                    d.name AS doctor_name,
                    b.start_time AS appointment_time,
                    b.status,
                    {clinical_summary_expr} AS clinical_summary
                FROM appointment_bookings b
                JOIN doctors d ON d.doctor_id = b.doctor_id
                LEFT JOIN patient_profiles pp ON pp.user_id::text = b.patient_id
                {where_sql}
                ORDER BY b.start_time ASC, b.created_at ASC;
                """,
                tuple(params),
            )
            rows = cur.fetchall()

    appointments = []
    for booking_id, db_doctor_id, patient_id, patient_name, doctor_name, appointment_time, booking_status, clinical_summary in rows:
        state = _appointment_state(booking_status, appointment_time)
        appointments.append(
            {
                "appointment_id": str(booking_id),
                "booking_id": str(booking_id),
                "doctor_id": str(db_doctor_id),
                "patient_id": str(patient_id) if patient_id is not None else None,
                "patient_name": str(patient_name),
                "doctor_name": str(doctor_name),
                "time": appointment_time.isoformat() if appointment_time else None,
                "appointment_time": appointment_time.isoformat() if appointment_time else None,
                "status": str(booking_status),
                "appointment_state": state,
                "clinical_summary": clinical_summary or "",
            }
        )

    return appointments
