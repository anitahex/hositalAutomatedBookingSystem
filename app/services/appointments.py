from app.db.connection import connect_db


def available_doctors_for_department(department: str, limit: int = 5):
    with connect_db() as conn:
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
                WHERE d.department = %s AND s.is_booked = FALSE
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
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.slot_id, s.start_time, s.end_time, d.name
                FROM appointment_slots s
                JOIN doctors d ON s.doctor_id = d.doctor_id
                WHERE s.doctor_id = %s AND s.is_booked = FALSE
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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT d.name, d.department, s.start_time, s.end_time, s.slot_id
                    FROM appointment_slots s
                    JOIN doctors d ON s.doctor_id = d.doctor_id
                    WHERE s.slot_id = %s AND s.is_booked = FALSE
                    FOR UPDATE OF s SKIP LOCKED;
                    """,
                    (slot_id,),
                )
                slot = cur.fetchone()

                if not slot:
                    conn.rollback()
                    return None

                doctor_name, department, start_time, end_time, booked_slot_id = slot
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
