from app.db.connection import connect_db


def ensure_booking_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS appointment_bookings (
                booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                slot_id UUID NOT NULL REFERENCES appointment_slots(slot_id) ON DELETE CASCADE,
                doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                patient_id TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'booked',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (slot_id, status)
            );

            CREATE INDEX IF NOT EXISTS idx_appointment_bookings_active
                ON appointment_bookings(slot_id, end_time)
                WHERE status = 'booked';

            INSERT INTO appointment_bookings (
                slot_id,
                doctor_id,
                patient_id,
                start_time,
                end_time
            )
            SELECT
                slot_id,
                doctor_id,
                booked_by_patient_id,
                start_time,
                end_time
            FROM appointment_slots
            WHERE is_booked = TRUE
            ON CONFLICT (slot_id, status) DO NOTHING;

            UPDATE appointment_bookings
            SET status = 'completed'
            WHERE status = 'booked' AND end_time <= NOW();

            UPDATE appointment_slots s
            SET is_booked = FALSE,
                booked_by_patient_id = NULL
            WHERE s.is_booked = TRUE
                AND NOT EXISTS (
                    SELECT 1
                    FROM appointment_bookings b
                    WHERE b.slot_id = s.slot_id
                        AND b.status = 'booked'
                        AND b.end_time > NOW()
                );
            """
        )


def available_doctors_for_department(department: str, limit: int = 5):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    d.doctor_id,
                    d.name,
                    d.experience_years,
                    MIN(s.start_time) AS next_available_time,
                    COUNT(s.slot_id) AS available_slot_count
                FROM doctors d
                JOIN appointment_slots s ON s.doctor_id = d.doctor_id
                WHERE d.department = %s
                    AND s.start_time > NOW()
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                GROUP BY d.doctor_id, d.name, d.experience_years
                ORDER BY next_available_time ASC, d.experience_years DESC
                LIMIT %s;
                """,
                (department, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "doctor_id": str(doctor_id),
            "doctor_name": doctor_name,
            "experience_years": experience_years,
            "next_available_time": next_available_time.isoformat(),
            "available_slot_count": int(available_slot_count),
        }
        for doctor_id, doctor_name, experience_years, next_available_time, available_slot_count in rows
    ]


def available_slots_for_doctor(doctor_id: str, limit: int = 5):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.slot_id, s.start_time, s.end_time, d.name
                FROM appointment_slots s
                JOIN doctors d ON s.doctor_id = d.doctor_id
                WHERE s.doctor_id = %s
                    AND s.start_time > NOW()
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                ORDER BY s.start_time ASC
                LIMIT %s;
                """,
                (doctor_id, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "slot_id": str(slot_id),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "doctor_name": doctor_name,
        }
        for slot_id, start_time, end_time, doctor_name in rows
    ]


def first_available_slots(department: str, limit: int = 5):
    doctors = available_doctors_for_department(department=department, limit=limit)
    slots = []

    for doctor in doctors:
        doctor_slots = available_slots_for_doctor(doctor["doctor_id"], limit=1)
        slots.extend(doctor_slots)

    return slots[:limit]


def book_selected_slot(slot_id: str, patient_id: str | None = None):
    with connect_db() as conn:
        try:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT d.name, d.department, s.start_time, s.end_time, s.slot_id, s.doctor_id
                    FROM appointment_slots s
                    JOIN doctors d ON s.doctor_id = d.doctor_id
                    WHERE s.slot_id = %s
                        AND s.start_time > NOW()
                        AND NOT EXISTS (
                            SELECT 1
                            FROM appointment_bookings b
                            WHERE b.slot_id = s.slot_id
                                AND b.status = 'booked'
                                AND b.end_time > NOW()
                        )
                    FOR UPDATE OF s SKIP LOCKED;
                    """,
                    (slot_id,),
                )
                slot = cur.fetchone()

                if not slot:
                    conn.rollback()
                    return None

                doctor_name, department, start_time, end_time, booked_slot_id, doctor_id = slot
                cur.execute(
                    """
                    INSERT INTO appointment_bookings (
                        slot_id,
                        doctor_id,
                        patient_id,
                        start_time,
                        end_time
                    )
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (booked_slot_id, doctor_id, patient_id, start_time, end_time),
                )
                cur.execute(
                    """
                    UPDATE appointment_slots
                    SET is_booked = TRUE,
                        booked_by_patient_id = %s
                    WHERE slot_id = %s;
                    """,
                    (patient_id, booked_slot_id),
                )
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "doctor_name": doctor_name,
        "department": department,
        "start_time": start_time,
        "end_time": end_time,
        "slot_id": booked_slot_id,
    }
