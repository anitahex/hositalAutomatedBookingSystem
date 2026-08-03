from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.db.connection import connect_db
from app.services.appointments import ensure_booking_schema, normalize_department_name


def _normalise_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(str(value).strip().split())
    return cleaned or None


def _doctor_row(row):
    (
        doctor_id,
        name,
        department,
        experience_years,
        is_active,
        total_slots,
        available_slots,
        next_available_time,
        holiday_count,
    ) = row

    return {
        "doctor_id": str(doctor_id),
        "name": name,
        "department": department,
        "experience_years": int(experience_years),
        "is_active": bool(is_active),
        "total_slots": int(total_slots or 0),
        "available_slots": int(available_slots or 0),
        "next_available_time": next_available_time.isoformat() if next_available_time else None,
        "holiday_count": int(holiday_count or 0),
    }


def list_doctors(limit: int = 500):
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
                    COALESCE(d.is_active, TRUE),
                    COUNT(s.slot_id) AS total_slots,
                    COUNT(s.slot_id) FILTER (
                        WHERE COALESCE(s.is_active, TRUE)
                            AND s.start_time > NOW() + INTERVAL '30 minutes'
                            AND s.start_time <= NOW() + INTERVAL '7 days'
                            AND NOT EXISTS (
                                SELECT 1
                                FROM appointment_bookings b
                                WHERE b.slot_id = s.slot_id
                                    AND b.status = 'booked'
                                    AND b.end_time > NOW()
                            )
                            AND NOT EXISTS (
                                SELECT 1
                                FROM schedule_holidays h
                                WHERE h.is_active = TRUE
                                    AND (
                                        h.doctor_id IS NULL
                                        OR h.doctor_id = d.doctor_id
                                    )
                                    AND DATE(s.start_time) BETWEEN h.start_date AND h.end_date
                            )
                    ) AS available_slots,
                    MIN(s.start_time) FILTER (
                        WHERE COALESCE(s.is_active, TRUE)
                            AND s.start_time > NOW() + INTERVAL '30 minutes'
                            AND s.start_time <= NOW() + INTERVAL '7 days'
                            AND NOT EXISTS (
                                SELECT 1
                                FROM appointment_bookings b
                                WHERE b.slot_id = s.slot_id
                                    AND b.status = 'booked'
                                    AND b.end_time > NOW()
                            )
                            AND NOT EXISTS (
                                SELECT 1
                                FROM schedule_holidays h
                                WHERE h.is_active = TRUE
                                    AND (
                                        h.doctor_id IS NULL
                                        OR h.doctor_id = d.doctor_id
                                    )
                                    AND DATE(s.start_time) BETWEEN h.start_date AND h.end_date
                            )
                    ) AS next_available_time,
                    (
                        SELECT COUNT(*)
                        FROM schedule_holidays h
                        WHERE h.is_active = TRUE
                            AND (
                                h.doctor_id IS NULL
                                OR h.doctor_id = d.doctor_id
                            )
                    ) AS holiday_count
                FROM doctors d
                LEFT JOIN appointment_slots s ON s.doctor_id = d.doctor_id
                GROUP BY d.doctor_id, d.name, d.department, d.experience_years, d.is_active
                ORDER BY d.department ASC, d.name ASC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [_doctor_row(row) for row in rows]


def get_doctor(doctor_id: str):
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
                    COALESCE(d.is_active, TRUE),
                    COUNT(s.slot_id) AS total_slots,
                    COUNT(s.slot_id) FILTER (
                        WHERE COALESCE(s.is_active, TRUE)
                            AND s.start_time > NOW() + INTERVAL '30 minutes'
                            AND s.start_time <= NOW() + INTERVAL '7 days'
                            AND NOT EXISTS (
                                SELECT 1
                                FROM appointment_bookings b
                                WHERE b.slot_id = s.slot_id
                                    AND b.status = 'booked'
                                    AND b.end_time > NOW()
                            )
                            AND NOT EXISTS (
                                SELECT 1
                                FROM schedule_holidays h
                                WHERE h.is_active = TRUE
                                    AND (
                                        h.doctor_id IS NULL
                                        OR h.doctor_id = d.doctor_id
                                    )
                                    AND DATE(s.start_time) BETWEEN h.start_date AND h.end_date
                            )
                    ) AS available_slots,
                    MIN(s.start_time) FILTER (
                        WHERE COALESCE(s.is_active, TRUE)
                            AND s.start_time > NOW() + INTERVAL '30 minutes'
                            AND s.start_time <= NOW() + INTERVAL '7 days'
                            AND NOT EXISTS (
                                SELECT 1
                                FROM appointment_bookings b
                                WHERE b.slot_id = s.slot_id
                                    AND b.status = 'booked'
                                    AND b.end_time > NOW()
                            )
                            AND NOT EXISTS (
                                SELECT 1
                                FROM schedule_holidays h
                                WHERE h.is_active = TRUE
                                    AND (
                                        h.doctor_id IS NULL
                                        OR h.doctor_id = d.doctor_id
                                    )
                                    AND DATE(s.start_time) BETWEEN h.start_date AND h.end_date
                            )
                    ) AS next_available_time,
                    (
                        SELECT COUNT(*)
                        FROM schedule_holidays h
                        WHERE h.is_active = TRUE
                            AND (
                                h.doctor_id IS NULL
                                OR h.doctor_id = d.doctor_id
                            )
                    ) AS holiday_count
                FROM doctors d
                LEFT JOIN appointment_slots s ON s.doctor_id = d.doctor_id
                WHERE d.doctor_id::text = %s
                GROUP BY d.doctor_id, d.name, d.department, d.experience_years, d.is_active;
                """,
                (doctor_id,),
            )
            row = cur.fetchone()

    return _doctor_row(row) if row else None


def create_doctor(*, name: str, department: str, experience_years: int, is_active: bool = True):
    clean_name = _normalise_text(name)
    clean_department = normalize_department_name(department)
    if not clean_name:
        raise ValueError("Doctor name is required.")

    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO doctors (name, department, experience_years, is_active)
                VALUES (%s, %s, %s, %s)
                RETURNING doctor_id;
                """,
                (clean_name, clean_department, experience_years, is_active),
            )
            doctor_id = cur.fetchone()[0]
        conn.commit()

    return get_doctor(str(doctor_id))


def update_doctor(
    doctor_id: str,
    *,
    name: str | None = None,
    department: str | None = None,
    experience_years: int | None = None,
    is_active: bool | None = None,
):
    fields: list[str] = []
    params: list[object] = []

    if name is not None:
        clean_name = _normalise_text(name)
        if not clean_name:
            raise ValueError("Doctor name is required.")
        fields.append("name = %s")
        params.append(clean_name)

    if department is not None:
        fields.append("department = %s")
        params.append(normalize_department_name(department))

    if experience_years is not None:
        fields.append("experience_years = %s")
        params.append(experience_years)

    if is_active is not None:
        fields.append("is_active = %s")
        params.append(is_active)

    if not fields:
        return get_doctor(doctor_id)

    params.extend([doctor_id])
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE doctors
                SET {", ".join(fields)},
                    updated_at = NOW()
                WHERE doctor_id::text = %s;
                """,
                params,
            )
        conn.commit()

    return get_doctor(doctor_id)


def list_slots(doctor_id: str | None = None, limit: int = 500):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            params: list[object] = [limit]
            where_sql = ""
            if doctor_id:
                where_sql = "WHERE s.doctor_id::text = %s"
                params = [doctor_id, limit]
            cur.execute(
                f"""
                SELECT
                    s.slot_id,
                    s.doctor_id,
                    d.name,
                    d.department,
                    s.start_time,
                    s.end_time,
                    s.is_booked,
                    COALESCE(s.is_active, TRUE),
                    s.booked_by_patient_id
                FROM appointment_slots s
                JOIN doctors d ON d.doctor_id = s.doctor_id
                {where_sql}
                ORDER BY s.start_time ASC
                LIMIT %s;
                """,
                tuple(params),
            )
            rows = cur.fetchall()

    return [
        {
            "slot_id": str(slot_id),
            "doctor_id": str(db_doctor_id),
            "doctor_name": doctor_name,
            "department": department,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "is_booked": bool(is_booked),
            "is_active": bool(is_active),
            "booked_by_patient_id": str(booked_by_patient_id) if booked_by_patient_id else None,
        }
        for slot_id, db_doctor_id, doctor_name, department, start_time, end_time, is_booked, is_active, booked_by_patient_id in rows
    ]


def create_slot(*, doctor_id: str, start_time: datetime, end_time: datetime, is_active: bool = True):
    if end_time <= start_time:
        raise ValueError("End time must be later than start time.")

    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_active)
                VALUES (%s, %s, %s, %s)
                RETURNING slot_id;
                """,
                (doctor_id, start_time, end_time, is_active),
            )
            slot_id = cur.fetchone()[0]
        conn.commit()

    return get_slot(str(slot_id)) if slot_id else None


def create_slot_series(
    *,
    doctor_id: str,
    start_date: date,
    end_date: date,
    work_start_time: time,
    work_end_time: time,
    lunch_start_time: time | None,
    lunch_end_time: time | None,
    slot_duration_minutes: int,
    is_active: bool = True,
):
    if slot_duration_minutes <= 0:
        raise ValueError("Slot duration must be greater than zero.")

    if work_end_time <= work_start_time:
        raise ValueError("Work end time must be later than work start time.")

    if lunch_start_time and lunch_end_time and lunch_end_time <= lunch_start_time:
        raise ValueError("Lunch end time must be later than lunch start time.")

    generated: list[dict] = []
    current_date = start_date

    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.name, d.department
                FROM doctors d
                WHERE d.doctor_id::text = %s;
                """,
                (doctor_id,),
            )
            doctor_row = cur.fetchone()
            if not doctor_row:
                raise ValueError("Doctor not found.")
            doctor_name, department = doctor_row

            while current_date <= end_date:
                window_start = datetime.combine(current_date, work_start_time)
                window_end = datetime.combine(current_date, work_end_time)
                lunch_window = None
                if lunch_start_time and lunch_end_time:
                    lunch_window = (
                        datetime.combine(current_date, lunch_start_time),
                        datetime.combine(current_date, lunch_end_time),
                    )

                cursor = window_start
                while cursor + timedelta(minutes=slot_duration_minutes) <= window_end:
                    slot_end = cursor + timedelta(minutes=slot_duration_minutes)
                    if lunch_window and cursor < lunch_window[1] and slot_end > lunch_window[0]:
                        cursor = lunch_window[1]
                        continue
                    cur.execute(
                        """
                        INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_active)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (doctor_id, start_time)
                        DO UPDATE SET
                            end_time = EXCLUDED.end_time,
                            is_active = EXCLUDED.is_active,
                            updated_at = NOW()
                        RETURNING slot_id;
                        """,
                        (doctor_id, cursor, slot_end, is_active),
                    )
                    slot_id = cur.fetchone()[0]
                    generated.append(
                        {
                            "slot_id": str(slot_id),
                            "doctor_id": str(doctor_id),
                            "doctor_name": doctor_name,
                            "department": department,
                            "start_time": cursor.isoformat(),
                            "end_time": slot_end.isoformat(),
                            "is_booked": False,
                            "is_active": bool(is_active),
                            "booked_by_patient_id": None,
                        }
                    )
                    cursor = slot_end
                current_date += timedelta(days=1)
        conn.commit()

    return generated


def get_slot(slot_id: str):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.slot_id,
                    s.doctor_id,
                    d.name,
                    d.department,
                    s.start_time,
                    s.end_time,
                    s.is_booked,
                    COALESCE(s.is_active, TRUE),
                    s.booked_by_patient_id
                FROM appointment_slots s
                JOIN doctors d ON d.doctor_id = s.doctor_id
                WHERE s.slot_id::text = %s;
                """,
                (slot_id,),
            )
            row = cur.fetchone()

    if not row:
        return None

    (
        db_slot_id,
        db_doctor_id,
        doctor_name,
        department,
        start_time,
        end_time,
        is_booked,
        is_active,
        booked_by_patient_id,
    ) = row
    return {
        "slot_id": str(db_slot_id),
        "doctor_id": str(db_doctor_id),
        "doctor_name": doctor_name,
        "department": department,
        "start_time": start_time.isoformat() if start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "is_booked": bool(is_booked),
        "is_active": bool(is_active),
        "booked_by_patient_id": str(booked_by_patient_id) if booked_by_patient_id else None,
    }


def set_slot_active(slot_id: str, is_active: bool):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE appointment_slots
                SET is_active = %s,
                    updated_at = NOW()
                WHERE slot_id::text = %s
                RETURNING slot_id;
                """,
                (is_active, slot_id),
            )
            row = cur.fetchone()
        conn.commit()

    return bool(row)


def create_holiday(
    *,
    start_date: date,
    end_date: date,
    reason: str | None = None,
    doctor_id: str | None = None,
    is_active: bool = True,
):
    if end_date < start_date:
        raise ValueError("End date must be on or after start date.")

    clean_reason = _normalise_text(reason)
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO schedule_holidays (doctor_id, start_date, end_date, reason, is_active)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING holiday_id;
                """,
                (doctor_id, start_date, end_date, clean_reason, is_active),
            )
            holiday_id = cur.fetchone()[0]
        conn.commit()

    return get_holiday(str(holiday_id))


def list_holidays(limit: int = 500):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    h.holiday_id,
                    h.doctor_id,
                    d.name,
                    h.start_date,
                    h.end_date,
                    h.reason,
                    COALESCE(h.is_active, TRUE)
                FROM schedule_holidays h
                LEFT JOIN doctors d ON d.doctor_id = h.doctor_id
                ORDER BY h.start_date ASC, h.created_at DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "holiday_id": str(holiday_id),
            "doctor_id": str(db_doctor_id) if db_doctor_id else None,
            "doctor_name": doctor_name,
            "scope": "doctor" if db_doctor_id else "universal",
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "reason": reason,
            "is_active": bool(is_active),
        }
        for holiday_id, db_doctor_id, doctor_name, start_date, end_date, reason, is_active in rows
    ]


def get_holiday(holiday_id: str):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    h.holiday_id,
                    h.doctor_id,
                    d.name,
                    h.start_date,
                    h.end_date,
                    h.reason,
                    COALESCE(h.is_active, TRUE)
                FROM schedule_holidays h
                LEFT JOIN doctors d ON d.doctor_id = h.doctor_id
                WHERE h.holiday_id::text = %s;
                """,
                (holiday_id,),
            )
            row = cur.fetchone()

    if not row:
        return None

    holiday_id, db_doctor_id, doctor_name, start_date, end_date, reason, is_active = row
    return {
        "holiday_id": str(holiday_id),
        "doctor_id": str(db_doctor_id) if db_doctor_id else None,
        "doctor_name": doctor_name,
        "scope": "doctor" if db_doctor_id else "universal",
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "reason": reason,
        "is_active": bool(is_active),
    }


def set_holiday_active(holiday_id: str, is_active: bool):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE schedule_holidays
                SET is_active = %s,
                    updated_at = NOW()
                WHERE holiday_id::text = %s
                RETURNING holiday_id;
                """,
                (is_active, holiday_id),
            )
            row = cur.fetchone()
        conn.commit()

    return bool(row)
