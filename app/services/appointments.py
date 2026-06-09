import re

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
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            ALTER TABLE appointment_bookings
                DROP CONSTRAINT IF EXISTS appointment_bookings_slot_id_status_key;

            CREATE INDEX IF NOT EXISTS idx_appointment_bookings_active
                ON appointment_bookings(slot_id, end_time)
                WHERE status = 'booked';

            CREATE UNIQUE INDEX IF NOT EXISTS ux_appointment_bookings_booked_slot
                ON appointment_bookings(slot_id)
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
            ON CONFLICT DO NOTHING;

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


def available_doctors_for_department_on_date(department: str, requested_date: str, limit: int = 5):
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
                    AND DATE(s.start_time) = %s
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
                (department, requested_date, limit),
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


def available_doctors_by_name(name: str, limit: int = 5):
    clean_name = re.sub(r"\b(dr\.?|doctor)\b", "", name, flags=re.IGNORECASE)
    clean_name = " ".join(clean_name.replace(".", " ").split())
    search = f"%{clean_name or name.strip()}%"
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    d.doctor_id,
                    d.name,
                    d.department,
                    d.experience_years,
                    MIN(s.start_time) AS next_available_time,
                    COUNT(s.slot_id) AS available_slot_count
                FROM doctors d
                JOIN appointment_slots s ON s.doctor_id = d.doctor_id
                WHERE d.name ILIKE %s
                    AND s.start_time > NOW()
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                GROUP BY d.doctor_id, d.name, d.department, d.experience_years
                ORDER BY next_available_time ASC, d.experience_years DESC
                LIMIT %s;
                """,
                (search, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "doctor_id": str(doctor_id),
            "doctor_name": doctor_name,
            "department": department,
            "experience_years": experience_years,
            "next_available_time": next_available_time.isoformat(),
            "available_slot_count": int(available_slot_count),
        }
        for doctor_id, doctor_name, department, experience_years, next_available_time, available_slot_count in rows
    ]


def available_doctors_by_name_on_date(name: str, requested_date: str, limit: int = 5):
    clean_name = re.sub(r"\b(dr\.?|doctor)\b", "", name, flags=re.IGNORECASE)
    clean_name = " ".join(clean_name.replace(".", " ").split())
    search = f"%{clean_name or name.strip()}%"
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    d.doctor_id,
                    d.name,
                    d.department,
                    d.experience_years,
                    MIN(s.start_time) AS next_available_time,
                    COUNT(s.slot_id) AS available_slot_count
                FROM doctors d
                JOIN appointment_slots s ON s.doctor_id = d.doctor_id
                WHERE d.name ILIKE %s
                    AND s.start_time > NOW()
                    AND DATE(s.start_time) = %s
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                GROUP BY d.doctor_id, d.name, d.department, d.experience_years
                ORDER BY next_available_time ASC, d.experience_years DESC
                LIMIT %s;
                """,
                (search, requested_date, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "doctor_id": str(doctor_id),
            "doctor_name": doctor_name,
            "department": department,
            "experience_years": experience_years,
            "next_available_time": next_available_time.isoformat(),
            "available_slot_count": int(available_slot_count),
        }
        for doctor_id, doctor_name, department, experience_years, next_available_time, available_slot_count in rows
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


def available_slots_for_doctor_on_date(doctor_id: str, requested_date: str, limit: int = 5):
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
                    AND DATE(s.start_time) = %s
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
                (doctor_id, requested_date, limit),
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
                    SELECT booking_id
                    FROM appointment_bookings
                    WHERE slot_id = %s
                        AND status = 'booked'
                    ORDER BY created_at DESC
                    LIMIT 1;
                    """,
                    (booked_slot_id,),
                )
                booking_id = cur.fetchone()[0]
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
        "booking_id": booking_id,
    }


def active_bookings_for_patient(patient_id: str | None = None, limit: int = 10):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            if patient_id:
                cur.execute(
                    """
                    SELECT
                        b.booking_id,
                        b.slot_id,
                        d.name,
                        d.department,
                        b.start_time,
                        b.end_time
                    FROM appointment_bookings b
                    JOIN doctors d ON d.doctor_id = b.doctor_id
                    WHERE b.patient_id = %s
                        AND b.status = 'booked'
                        AND b.end_time > NOW()
                    ORDER BY b.start_time ASC
                    LIMIT %s;
                    """,
                    (patient_id, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        b.booking_id,
                        b.slot_id,
                        d.name,
                        d.department,
                        b.start_time,
                        b.end_time
                    FROM appointment_bookings b
                    JOIN doctors d ON d.doctor_id = b.doctor_id
                    WHERE b.status = 'booked'
                        AND b.end_time > NOW()
                    ORDER BY b.start_time ASC
                    LIMIT %s;
                    """,
                    (limit,),
                )
            rows = cur.fetchall()

    return [
        {
            "booking_id": str(booking_id),
            "slot_id": str(slot_id),
            "doctor": str(doctor_name),
            "department": str(department),
            "time": str(start_time),
            "end_time": str(end_time),
        }
        for booking_id, slot_id, doctor_name, department, start_time, end_time in rows
    ]


def upcoming_bookings_for_patient(patient_id: str, limit: int = 20):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    b.booking_id,
                    b.slot_id,
                    d.name,
                    d.department,
                    b.start_time,
                    b.end_time,
                    b.status,
                    b.start_time > NOW() + INTERVAL '24 hours' AS can_modify
                FROM appointment_bookings b
                JOIN doctors d ON d.doctor_id = b.doctor_id
                WHERE b.patient_id = %s
                    AND b.status = 'booked'
                    AND b.end_time > NOW()
                ORDER BY b.start_time ASC
                LIMIT %s;
                """,
                (patient_id, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "booking_id": str(booking_id),
            "slot_id": str(slot_id),
            "doctor": str(doctor_name),
            "department": str(department),
            "time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": str(status),
            "can_modify": bool(can_modify),
        }
        for booking_id, slot_id, doctor_name, department, start_time, end_time, status, can_modify in rows
    ]


def previous_bookings_for_patient(patient_id: str, limit: int = 20):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE appointment_bookings
                SET status = 'completed'
                WHERE patient_id = %s
                    AND status = 'booked'
                    AND end_time <= NOW();

                SELECT
                    b.booking_id,
                    b.slot_id,
                    d.name,
                    d.department,
                    b.start_time,
                    b.end_time,
                    b.status
                FROM appointment_bookings b
                JOIN doctors d ON d.doctor_id = b.doctor_id
                WHERE b.patient_id = %s
                    AND (
                        b.status IN ('completed', 'cancelled')
                        OR b.end_time <= NOW()
                    )
                ORDER BY b.start_time DESC
                LIMIT %s;
                """,
                (patient_id, patient_id, limit),
            )
            rows = cur.fetchall()
        conn.commit()

    return [
        {
            "booking_id": str(booking_id),
            "slot_id": str(slot_id),
            "doctor": str(doctor_name),
            "department": str(department),
            "time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": str(status),
        }
        for booking_id, slot_id, doctor_name, department, start_time, end_time, status in rows
    ]


def _modifiable_booking(cur, booking_id: str, patient_id: str):
    cur.execute(
        """
        SELECT
            b.booking_id,
            b.slot_id,
            b.doctor_id,
            d.name,
            d.department,
            b.start_time,
            b.end_time
        FROM appointment_bookings b
        JOIN doctors d ON d.doctor_id = b.doctor_id
        WHERE b.booking_id::text = %s
            AND b.patient_id = %s
            AND b.status = 'booked'
            AND b.start_time > NOW() + INTERVAL '24 hours'
        FOR UPDATE OF b;
        """,
        (booking_id, patient_id),
    )
    return cur.fetchone()


def cancel_patient_booking(booking_id: str, patient_id: str):
    with connect_db() as conn:
        try:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                row = _modifiable_booking(cur, booking_id, patient_id)
                if not row:
                    conn.rollback()
                    return None

                booking_id, slot_id, doctor_id, doctor_name, department, start_time, end_time = row
                cur.execute(
                    """
                    UPDATE appointment_bookings
                    SET status = 'cancelled'
                    WHERE booking_id = %s;
                    """,
                    (booking_id,),
                )
                cur.execute(
                    """
                    UPDATE appointment_slots
                    SET is_booked = FALSE,
                        booked_by_patient_id = NULL
                    WHERE slot_id = %s;
                    """,
                    (slot_id,),
                )
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "booking_id": str(booking_id),
        "slot_id": str(slot_id),
        "doctor": str(doctor_name),
        "department": str(department),
        "time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": "cancelled",
    }


def reschedule_options_for_booking(
    booking_id: str,
    patient_id: str,
    requested_date: str,
    limit: int = 8,
):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.doctor_id
                FROM appointment_bookings b
                WHERE b.booking_id::text = %s
                    AND b.patient_id = %s
                    AND b.status = 'booked'
                    AND b.start_time > NOW() + INTERVAL '24 hours';
                """,
                (booking_id, patient_id),
            )
            booking = cur.fetchone()
            if not booking:
                return []

            doctor_id = booking[0]
            cur.execute(
                """
                SELECT s.slot_id, s.start_time, s.end_time, d.name
                FROM appointment_slots s
                JOIN doctors d ON d.doctor_id = s.doctor_id
                WHERE s.doctor_id = %s
                    AND DATE(s.start_time) = %s
                    AND s.start_time > NOW() + INTERVAL '24 hours'
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
                (doctor_id, requested_date, limit),
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


def reschedule_patient_booking(booking_id: str, patient_id: str, new_slot_id: str):
    with connect_db() as conn:
        try:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                booking = _modifiable_booking(cur, booking_id, patient_id)
                if not booking:
                    conn.rollback()
                    return None

                (
                    current_booking_id,
                    old_slot_id,
                    _old_doctor_id,
                    _doctor_name,
                    _department,
                    _old_start_time,
                    _old_end_time,
                ) = booking

                cur.execute(
                    """
                    SELECT s.slot_id, s.doctor_id, d.name, d.department, s.start_time, s.end_time
                    FROM appointment_slots s
                    JOIN doctors d ON d.doctor_id = s.doctor_id
                    WHERE s.slot_id::text = %s
                        AND s.start_time > NOW() + INTERVAL '24 hours'
                        AND NOT EXISTS (
                            SELECT 1
                            FROM appointment_bookings b
                            WHERE b.slot_id = s.slot_id
                                AND b.status = 'booked'
                                AND b.end_time > NOW()
                        )
                    FOR UPDATE OF s SKIP LOCKED;
                    """,
                    (new_slot_id,),
                )
                slot = cur.fetchone()
                if not slot:
                    conn.rollback()
                    return None

                slot_id, doctor_id, doctor_name, department, start_time, end_time = slot
                cur.execute(
                    """
                    UPDATE appointment_bookings
                    SET slot_id = %s,
                        doctor_id = %s,
                        start_time = %s,
                        end_time = %s
                    WHERE booking_id = %s;
                    """,
                    (slot_id, doctor_id, start_time, end_time, current_booking_id),
                )
                cur.execute(
                    """
                    UPDATE appointment_slots
                    SET is_booked = FALSE,
                        booked_by_patient_id = NULL
                    WHERE slot_id = %s;
                    """,
                    (old_slot_id,),
                )
                cur.execute(
                    """
                    UPDATE appointment_slots
                    SET is_booked = TRUE,
                        booked_by_patient_id = %s
                    WHERE slot_id = %s;
                    """,
                    (patient_id, slot_id),
                )
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "booking_id": str(current_booking_id),
        "slot_id": str(slot_id),
        "doctor": str(doctor_name),
        "department": str(department),
        "time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": "booked",
        "can_modify": True,
    }


def cancel_booking(reference: str, patient_id: str | None = None):
    with connect_db() as conn:
        try:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                params = [reference, reference]
                patient_clause = ""
                if patient_id:
                    patient_clause = "AND b.patient_id = %s"
                    params.append(patient_id)

                cur.execute(
                    f"""
                    SELECT
                        b.booking_id,
                        b.slot_id,
                        d.name,
                        d.department,
                        b.start_time,
                        b.end_time
                    FROM appointment_bookings b
                    JOIN doctors d ON d.doctor_id = b.doctor_id
                    WHERE (b.booking_id::text = %s OR b.slot_id::text = %s)
                        AND b.status = 'booked'
                        AND b.end_time > NOW()
                        {patient_clause}
                    FOR UPDATE OF b;
                    """,
                    tuple(params),
                )
                row = cur.fetchone()

                if not row:
                    conn.rollback()
                    return None

                booking_id, slot_id, doctor_name, department, start_time, end_time = row
                cur.execute(
                    """
                    UPDATE appointment_bookings
                    SET status = 'cancelled'
                    WHERE booking_id = %s;
                    """,
                    (booking_id,),
                )
                cur.execute(
                    """
                    UPDATE appointment_slots
                    SET is_booked = FALSE,
                        booked_by_patient_id = NULL
                    WHERE slot_id = %s;
                    """,
                    (slot_id,),
                )
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "booking_id": str(booking_id),
        "slot_id": str(slot_id),
        "doctor": str(doctor_name),
        "department": str(department),
        "time": str(start_time),
        "end_time": str(end_time),
    }
