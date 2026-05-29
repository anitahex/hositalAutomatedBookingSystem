from fastapi import APIRouter

from app.db.connection import connect_db
from app.services.appointments import ensure_booking_schema


router = APIRouter()


@router.get("/analytics/summary")
def analytics_summary():
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM doctors;")
            doctors = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM appointment_slots;")
            slots = cur.fetchone()[0]
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
        "bookings": bookings,
        "active_bookings": active_bookings,
    }
