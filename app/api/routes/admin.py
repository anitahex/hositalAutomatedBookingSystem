from fastapi import APIRouter

from app.db.connection import connect_db


router = APIRouter()


@router.get("/analytics/summary")
def analytics_summary():
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM doctors;")
            doctors = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM appointment_slots;")
            slots = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM appointment_slots WHERE is_booked = TRUE;")
            booked_slots = cur.fetchone()[0]

    return {
        "doctors": doctors,
        "appointment_slots": slots,
        "booked_slots": booked_slots,
    }
