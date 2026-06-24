import re
from difflib import get_close_matches
from datetime import date, timedelta

from app.db.connection import connect_db


BOOKING_LOOKAHEAD_DAYS = 7


DEPARTMENT_ALIASES = {
    "physician": "General Physician",
    "general physician": "General Physician",
    "general": "General Physician",
    "general medicine": "General Physician",
    "gp": "General Physician",
    "cardio": "Cardiology",
    "cardiologist": "Cardiology",
    "heart": "Cardiology",
    "neuro": "Neurology",
    "neurologist": "Neurology",
    "ortho": "Orthopedics",
    "orthopedic": "Orthopedics",
    "orthopaedic": "Orthopedics",
    "derm": "Dermatology",
    "skin": "Dermatology",
    "gastro": "Gastroenterology",
    "pulmo": "Pulmonology",
    "psych": "Psychiatry",
    "nephro": "Nephrology",
    "endo": "Endocrinology",
    "hema": "Hematology",
    "onco": "Oncology",
}

CANONICAL_DEPARTMENTS = [
    "General Physician",
    "Gastroenterology",
    "Cardiology",
    "Neurology",
    "Orthopedics",
    "Oncology",
    "Pulmonology",
    "Psychiatry",
    "Nephrology",
    "Endocrinology",
    "Hematology",
    "Dermatology",
]

_NORMALIZED_CANONICAL_DEPARTMENTS = {
    " ".join(department.lower().split()): department
    for department in CANONICAL_DEPARTMENTS
}

_NORMALIZED_DEPARTMENT_ALIASES = {
    " ".join(alias.lower().split()): canonical
    for alias, canonical in DEPARTMENT_ALIASES.items()
}

_DEPARTMENT_STOPWORDS = {
    "department",
    "dept",
    "doctor",
    "dr",
    "specialist",
    "specialists",
    "clinic",
    "unit",
    "center",
    "centre",
    "care",
}


def normalize_department_name(department: str | None) -> str:
    if not department:
        return "General Physician"

    cleaned = " ".join(str(department).strip().lower().replace("-", " ").replace("/", " ").split())
    if not cleaned:
        return "General Physician"

    words = [word for word in cleaned.split() if word not in _DEPARTMENT_STOPWORDS]
    candidate = " ".join(words).strip() or cleaned

    if candidate in _NORMALIZED_DEPARTMENT_ALIASES:
        return _NORMALIZED_DEPARTMENT_ALIASES[candidate]

    if candidate in _NORMALIZED_CANONICAL_DEPARTMENTS:
        return _NORMALIZED_CANONICAL_DEPARTMENTS[candidate]

    matches = get_close_matches(
        candidate,
        list(_NORMALIZED_CANONICAL_DEPARTMENTS.keys()) + list(_NORMALIZED_DEPARTMENT_ALIASES.keys()),
        n=1,
        cutoff=0.78,
    )
    if matches:
        match = matches[0]
        if match in _NORMALIZED_CANONICAL_DEPARTMENTS:
            return _NORMALIZED_CANONICAL_DEPARTMENTS[match]
        return _NORMALIZED_DEPARTMENT_ALIASES[match]

    return " ".join(word.capitalize() for word in candidate.split())


def available_departments(limit: int = 20):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    d.department,
                    COUNT(DISTINCT d.doctor_id) AS doctor_count,
                    COUNT(s.slot_id) AS available_slot_count,
                    MIN(s.start_time) AS next_available_time
                FROM doctors d
                JOIN appointment_slots s ON s.doctor_id = d.doctor_id
                WHERE s.start_time > NOW()
                    AND s.start_time <= NOW() + INTERVAL '7 days'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                GROUP BY d.department
                ORDER BY next_available_time ASC, d.department ASC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "department": str(department),
            "doctor_count": int(doctor_count),
            "available_slot_count": int(available_slot_count),
            "next_available_time": next_available_time.isoformat() if next_available_time else None,
        }
        for department, doctor_count, available_slot_count, next_available_time in rows
    ]


def _requested_date_within_booking_window(requested_date: str | None) -> bool:
    if not requested_date:
        return False
    try:
        parsed = date.fromisoformat(requested_date)
    except ValueError:
        return False

    today = date.today()
    return today <= parsed <= today + timedelta(days=BOOKING_LOOKAHEAD_DAYS)


def _parse_requested_date(requested_date: str | None) -> date | None:
    if not requested_date:
        return None
    try:
        parsed = date.fromisoformat(requested_date)
    except ValueError:
        return None
    if not _requested_date_within_booking_window(parsed.isoformat()):
        return None
    return parsed


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
                booking_note TEXT,
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

            ALTER TABLE appointment_bookings
                ADD COLUMN IF NOT EXISTS booking_note TEXT;

            INSERT INTO appointment_bookings (
                slot_id,
                doctor_id,
                patient_id,
                booking_note,
                start_time,
                end_time
            )
            SELECT
                slot_id,
                doctor_id,
                booked_by_patient_id,
                NULL,
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
    department = normalize_department_name(department)
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
                    AND s.start_time <= NOW() + INTERVAL '7 days'
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
    department = normalize_department_name(department)
    parsed_date = _parse_requested_date(requested_date)
    if not parsed_date:
        return []
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
                    AND s.start_time <= NOW() + INTERVAL '7 days'
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
                (department, parsed_date, limit),
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
                    AND s.start_time <= NOW() + INTERVAL '7 days'
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
    parsed_date = _parse_requested_date(requested_date)
    if not parsed_date:
        return []
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
                    AND s.start_time <= NOW() + INTERVAL '7 days'
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
                (search, parsed_date, limit),
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
                    AND s.start_time <= NOW() + INTERVAL '7 days'
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
    parsed_date = _parse_requested_date(requested_date)
    if not parsed_date:
        return []
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
                    AND s.start_time <= NOW() + INTERVAL '7 days'
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
                (doctor_id, parsed_date, limit),
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
    department = normalize_department_name(department)
    doctors = available_doctors_for_department(department=department, limit=limit)
    slots = []

    for doctor in doctors:
        doctor_slots = available_slots_for_doctor(doctor["doctor_id"], limit=1)
        slots.extend(doctor_slots)

    return slots[:limit]


def book_selected_slot(slot_id: str, patient_id: str | None = None, booking_note: str | None = None):
    note = " ".join(str(booking_note).strip().split()) if booking_note else None
    if note == "":
        note = None
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
                        AND s.start_time <= NOW() + INTERVAL '7 days'
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
                        booking_note,
                        start_time,
                        end_time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (booked_slot_id, doctor_id, patient_id, note, start_time, end_time),
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
        "doctor": doctor_name,
        "doctor_name": doctor_name,
        "department": department,
        "time": start_time.isoformat(),
        "start_time": start_time,
        "end_time": end_time,
        "slot_id": booked_slot_id,
        "booking_id": booking_id,
        "booking_note": note,
    }


def _normalized_booking_note(note: str | None) -> str | None:
    if not note:
        return None
    cleaned = " ".join(str(note).strip().split())
    return cleaned or None


def update_booking_note(booking_id: str, patient_id: str, booking_note: str):
    note = _normalized_booking_note(booking_note)
    if not note:
        return None

    with connect_db() as conn:
        try:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT booking_note
                    FROM appointment_bookings
                    WHERE booking_id::text = %s
                        AND patient_id = %s
                        AND status = 'booked';
                    """,
                    (booking_id, patient_id),
                )
                existing_row = cur.fetchone()
                if not existing_row:
                    conn.rollback()
                    return None

                existing_note = _normalized_booking_note(existing_row[0])
                combined_note = note if not existing_note else f"{existing_note}\n{note}"

                cur.execute(
                    """
                    UPDATE appointment_bookings
                    SET booking_note = %s
                    WHERE booking_id::text = %s
                        AND patient_id = %s
                        AND status = 'booked'
                    RETURNING booking_id;
                    """,
                    (combined_note, booking_id, patient_id),
                )
                updated = cur.fetchone()
                if not updated:
                    conn.rollback()
                    return None

                cur.execute(
                    """
                    SELECT
                        b.booking_id,
                        b.slot_id,
                        d.name,
                        d.department,
                        b.booking_note,
                        b.start_time,
                        b.end_time,
                        b.status,
                        b.start_time > NOW() + INTERVAL '24 hours' AS can_modify
                    FROM appointment_bookings b
                    JOIN doctors d ON d.doctor_id = b.doctor_id
                    WHERE b.booking_id::text = %s
                        AND b.patient_id = %s
                        AND b.status = 'booked';
                    """,
                    (booking_id, patient_id),
                )
                row = cur.fetchone()
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    if not row:
        return None

    booking_id, slot_id, doctor_name, department, booking_note, start_time, end_time, status, can_modify = row
    return {
        "booking_id": str(booking_id),
        "slot_id": str(slot_id),
        "doctor": str(doctor_name),
        "department": str(department),
        "booking_note": booking_note,
        "time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": str(status),
        "can_modify": bool(can_modify),
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
                    b.booking_note,
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
                    b.booking_note,
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
            "booking_note": booking_note,
            "time": str(start_time),
            "end_time": str(end_time),
        }
        for booking_id, slot_id, doctor_name, department, booking_note, start_time, end_time in rows
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
                    b.booking_note,
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
            "booking_note": booking_note,
            "time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": str(status),
            "can_modify": bool(can_modify),
        }
        for booking_id, slot_id, doctor_name, department, booking_note, start_time, end_time, status, can_modify in rows
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
                    b.booking_note,
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
            "booking_note": booking_note,
            "time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": str(status),
        }
        for booking_id, slot_id, doctor_name, department, booking_note, start_time, end_time, status in rows
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
            b.booking_note,
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

                booking_id, slot_id, doctor_id, doctor_name, department, booking_note, start_time, end_time = row
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
        "booking_note": booking_note,
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
    parsed_date = _parse_requested_date(requested_date)
    if not parsed_date:
        return []
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
                    AND s.start_time <= NOW() + INTERVAL '7 days'
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
                (doctor_id, parsed_date, limit),
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
                    booking_note,
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
                        AND s.start_time <= NOW() + INTERVAL '7 days'
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
        "booking_note": booking_note,
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
                        b.booking_note,
                        b.start_time,
                        b.end_time
                    FROM appointment_bookings b
                    JOIN doctors d ON d.doctor_id = b.doctor_id
                    WHERE (b.booking_id::text = %s OR b.slot_id::text = %s)
                        AND b.status = 'booked'
                        AND b.end_time > NOW()
                        AND b.start_time > NOW() + INTERVAL '24 hours'
                        {patient_clause}
                    FOR UPDATE OF b;
                    """,
                    tuple(params),
                )
                row = cur.fetchone()

                if not row:
                    conn.rollback()
                    return None

                booking_id, slot_id, doctor_name, department, booking_note, start_time, end_time = row
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
        "booking_note": booking_note,
        "time": str(start_time),
        "end_time": str(end_time),
    }
