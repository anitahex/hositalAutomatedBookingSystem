import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.connection import connect_db


def main():
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(1), MIN(start_time), MAX(start_time)
                FROM appointment_slots
                WHERE start_time >= DATE '2026-09-01'
                  AND start_time < DATE '2026-11-01';
                """
            )
            print("new-range slots:", cur.fetchone())

            cur.execute(
                """
                SELECT COUNT(1),
                       COUNT(1) FILTER (WHERE status = 'booked'),
                       COUNT(1) FILTER (WHERE status = 'cancelled'),
                       COUNT(1) FILTER (WHERE status = 'completed')
                FROM appointment_bookings;
                """
            )
            print("bookings total/booked/cancelled/completed:", cur.fetchone())

            cur.execute("SELECT COUNT(1) FROM appointment_slots WHERE is_booked;")
            print("booked slots:", cur.fetchone()[0])

            cur.execute(
                """
                SELECT COUNT(1)
                FROM appointment_bookings b
                LEFT JOIN appointment_slots s ON s.slot_id = b.slot_id
                WHERE b.status = 'booked'
                  AND (s.slot_id IS NULL OR NOT s.is_booked);
                """
            )
            print("booked booking/slot mismatches:", cur.fetchone()[0])

            cur.execute(
                """
                SELECT COUNT(DISTINCT DATE(start_time)), COUNT(DISTINCT doctor_id)
                FROM appointment_slots
                WHERE start_time >= DATE '2026-09-01'
                  AND start_time < DATE '2026-11-01';
                """
            )
            print("new-range working days/doctors:", cur.fetchone())


if __name__ == "__main__":
    main()
