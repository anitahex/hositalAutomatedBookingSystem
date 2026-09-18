"""Admin slot/holiday CRUD coverage — the gap left by test_admin_doctor_management.py
(mocked-cursor unit tests) and test_admin_doctor_management_integration.py (doctor
list/get only). Per FULL_SYSTEM_AUDIT.md, slots and holidays have no dedicated tests.

Same convention as test_admin_doctor_management_integration.py: hit a real Postgres via
connect_db(), skip cleanly if it's unreachable, and clean up every row this file
creates. Each test creates its own doctor row so appointment_slots/schedule_holidays/
appointment_bookings rows (all FK ON DELETE CASCADE from doctors) can be cleaned up by
deleting just that doctor.

Three of the tests below are CHARACTERIZATION tests: they pin down gaps that were
verified by reading admin_management.py directly (not assumed) —
  1. create_slot_series() has no overlap check against existing active slots (only an
     ON CONFLICT (doctor_id, start_time) *exact-start-time* upsert — a different
     start_time that still overlaps an existing slot's range is never checked).
  2. create_slot_series() and create_holiday() never validate start_date against
     today — only internal ordering (end >= start, work_end > work_start, lunch
     ordering) is checked.
  3. create_holiday() never cross-references appointment_bookings — nothing in
     admin_management.py (or anywhere else, per a repo-wide grep for
     "schedule_holidays") joins holidays against bookings to cancel or flag them.
If any of these were ever fixed, these tests would start failing (not silently pass),
which is the point of a characterization test.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pytest

from app.db.connection import connect_db
from app.services.admin_management import create_holiday, create_slot, create_slot_series, get_slot


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _make_doctor(name: str) -> str:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO doctors (name, department, experience_years, is_active)
                   VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
                (name, "Testing", 5),
            )
            doctor_id = str(cur.fetchone()[0])
        conn.commit()
    return doctor_id


def _delete_doctor(doctor_id: str) -> None:
    with connect_db() as conn:
        with conn.cursor() as cur:
            # ON DELETE CASCADE also removes appointment_slots, schedule_holidays and
            # appointment_bookings rows for this doctor.
            cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        conn.commit()


# ── create_slot_series: happy path ───────────────────────────────────────────

def test_create_slot_series_happy_path_generates_expected_slots():
    _skip_if_no_database()
    doctor_id = _make_doctor("Slot Series Doctor")
    try:
        target_date = date.today() + timedelta(days=30)
        generated = create_slot_series(
            doctor_id=doctor_id,
            start_date=target_date,
            end_date=target_date,
            work_start_time=time(9, 0),
            work_end_time=time(12, 0),
            lunch_start_time=None,
            lunch_end_time=None,
            slot_duration_minutes=30,
        )

        assert len(generated) == 6  # 09:00-12:00 in 30-minute slots, no lunch break
        assert generated[0]["doctor_id"] == doctor_id
        assert generated[0]["start_time"] == datetime.combine(target_date, time(9, 0)).isoformat()
        assert generated[-1]["end_time"] == datetime.combine(target_date, time(12, 0)).isoformat()
        assert all(slot["is_active"] is True and slot["is_booked"] is False for slot in generated)

        # Confirm it actually persisted, not just returned in-memory.
        for slot in generated:
            persisted = get_slot(slot["slot_id"])
            assert persisted is not None
            assert persisted["doctor_id"] == doctor_id
    finally:
        _delete_doctor(doctor_id)


def test_create_slot_series_respects_lunch_break():
    _skip_if_no_database()
    doctor_id = _make_doctor("Slot Series Lunch Doctor")
    try:
        target_date = date.today() + timedelta(days=31)
        generated = create_slot_series(
            doctor_id=doctor_id,
            start_date=target_date,
            end_date=target_date,
            work_start_time=time(9, 0),
            work_end_time=time(13, 0),
            lunch_start_time=time(12, 0),
            lunch_end_time=time(13, 0),
            slot_duration_minutes=60,
        )
        # 09:00-10:00, 10:00-11:00, 11:00-12:00, then lunch 12:00-13:00 swallows the rest.
        assert len(generated) == 3
        assert generated[-1]["end_time"] == datetime.combine(target_date, time(12, 0)).isoformat()
    finally:
        _delete_doctor(doctor_id)


# ── Characterization: no overlap validation ──────────────────────────────────

def test_create_slot_series_does_not_reject_overlap_with_existing_active_slot():
    """Verified by reading create_slot()/create_slot_series(): neither checks for a
    time-range overlap against existing rows — only the DB's UNIQUE (doctor_id,
    start_time) constraint applies, and that only fires on an *exact* matching
    start_time. A series that overlaps an existing slot's range at a different
    start_time inserts cleanly today."""
    _skip_if_no_database()
    doctor_id = _make_doctor("Overlap Doctor")
    try:
        target_date = date.today() + timedelta(days=32)

        existing = create_slot(
            doctor_id=doctor_id,
            start_time=datetime.combine(target_date, time(10, 0)),
            end_time=datetime.combine(target_date, time(10, 30)),
        )
        assert existing is not None

        # This series' first generated slot (10:15-10:45) overlaps the existing
        # 10:00-10:30 slot by 15 minutes, but starts at a different start_time.
        generated = create_slot_series(
            doctor_id=doctor_id,
            start_date=target_date,
            end_date=target_date,
            work_start_time=time(10, 15),
            work_end_time=time(11, 0),
            lunch_start_time=None,
            lunch_end_time=None,
            slot_duration_minutes=30,
        )

        assert len(generated) == 1  # no exception, no rejection — it just inserted
        overlapping = generated[0]
        overlap_start = datetime.fromisoformat(overlapping["start_time"])
        overlap_end = datetime.fromisoformat(overlapping["end_time"])
        existing_start = datetime.fromisoformat(existing["start_time"])
        existing_end = datetime.fromisoformat(existing["end_time"])
        assert overlap_start < existing_end and overlap_end > existing_start  # genuinely overlaps

        # Both rows now coexist for the same doctor — proves nothing rejected the series.
        assert get_slot(existing["slot_id"]) is not None
        assert get_slot(overlapping["slot_id"]) is not None
    finally:
        _delete_doctor(doctor_id)


# ── Characterization: no past-date validation ────────────────────────────────

def test_create_slot_series_accepts_past_start_date_without_rejection():
    """Verified by reading create_slot_series(): it only validates slot_duration_minutes
    > 0, work_end_time > work_start_time, and lunch ordering — never start_date against
    today. A wholly-past date range is accepted and generates real (unbookable-in-
    practice, but persisted) slots."""
    _skip_if_no_database()
    doctor_id = _make_doctor("Past Date Series Doctor")
    try:
        past_date = date.today() - timedelta(days=5)
        generated = create_slot_series(
            doctor_id=doctor_id,
            start_date=past_date,
            end_date=past_date,
            work_start_time=time(9, 0),
            work_end_time=time(10, 0),
            lunch_start_time=None,
            lunch_end_time=None,
            slot_duration_minutes=30,
        )
        assert len(generated) == 2
        assert generated[0]["start_time"].startswith(past_date.isoformat())
    finally:
        _delete_doctor(doctor_id)


def test_create_holiday_accepts_past_start_date_without_rejection():
    """Verified by reading create_holiday(): it only checks end_date >= start_date,
    never start_date against today."""
    _skip_if_no_database()
    doctor_id = _make_doctor("Past Date Holiday Doctor")
    try:
        past_start = date.today() - timedelta(days=10)
        past_end = date.today() - timedelta(days=8)
        holiday = create_holiday(
            start_date=past_start,
            end_date=past_end,
            reason="Backdated holiday (no rejection today)",
            doctor_id=doctor_id,
        )
        assert holiday is not None
        assert holiday["start_date"] == past_start.isoformat()
        assert holiday["end_date"] == past_end.isoformat()
    finally:
        _delete_doctor(doctor_id)


# ── create_holiday: happy path ────────────────────────────────────────────────

def test_create_holiday_happy_path():
    _skip_if_no_database()
    doctor_id = _make_doctor("Holiday Doctor")
    try:
        start = date.today() + timedelta(days=20)
        end = date.today() + timedelta(days=22)
        holiday = create_holiday(
            start_date=start,
            end_date=end,
            reason="Annual leave",
            doctor_id=doctor_id,
        )
        assert holiday["doctor_id"] == doctor_id
        assert holiday["scope"] == "doctor"
        assert holiday["start_date"] == start.isoformat()
        assert holiday["end_date"] == end.isoformat()
        assert holiday["reason"] == "Annual leave"
        assert holiday["is_active"] is True
    finally:
        _delete_doctor(doctor_id)


def test_create_holiday_universal_scope_when_no_doctor_given():
    _skip_if_no_database()
    start = date.today() + timedelta(days=40)
    end = date.today() + timedelta(days=40)
    holiday = create_holiday(start_date=start, end_date=end, reason="Hospital-wide closure", doctor_id=None)
    try:
        assert holiday["doctor_id"] is None
        assert holiday["scope"] == "universal"
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM schedule_holidays WHERE holiday_id = %s", (holiday["holiday_id"],))
            conn.commit()


# ── Characterization: holidays never cross-reference bookings ───────────────

def test_create_holiday_does_not_cancel_or_flag_overlapping_booked_slots():
    """Verified by reading create_holiday() and grepping the repo for "schedule_holidays":
    nothing joins schedule_holidays against appointment_bookings (or appointment_slots)
    to cancel, flag, or even surface a warning about a conflict. A holiday can be created
    over a date range that already has a confirmed, booked appointment, and that booking
    (and its slot) is left completely untouched."""
    _skip_if_no_database()
    doctor_id = _make_doctor("Holiday Vs Booking Doctor")
    try:
        target_date = date.today() + timedelta(days=25)
        slot = create_slot(
            doctor_id=doctor_id,
            start_time=datetime.combine(target_date, time(10, 0)),
            end_time=datetime.combine(target_date, time(10, 30)),
        )

        booking_id = None
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE appointment_slots
                       SET is_booked = TRUE, booked_by_patient_id = %s
                       WHERE slot_id = %s""",
                    ("test-patient-1", slot["slot_id"]),
                )
                cur.execute(
                    """INSERT INTO appointment_bookings
                           (slot_id, doctor_id, patient_id, start_time, end_time, status)
                       VALUES (%s, %s, %s, %s, %s, 'booked')
                       RETURNING booking_id""",
                    (
                        slot["slot_id"], doctor_id, "test-patient-1",
                        datetime.combine(target_date, time(10, 0)),
                        datetime.combine(target_date, time(10, 30)),
                    ),
                )
                booking_id = str(cur.fetchone()[0])
            conn.commit()

        holiday = create_holiday(
            start_date=target_date,
            end_date=target_date,
            reason="Emergency closure covering an already-booked slot",
            doctor_id=doctor_id,
        )
        assert holiday is not None  # creation itself is never blocked either

        # The booking and slot are completely unaffected by the overlapping holiday.
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT status FROM appointment_bookings WHERE booking_id = %s", (booking_id,))
                booking_status = cur.fetchone()[0]

        persisted_slot = get_slot(slot["slot_id"])
        assert booking_status == "booked"  # not cancelled, not flagged
        assert persisted_slot["is_booked"] is True
        assert persisted_slot["is_active"] is True
    finally:
        _delete_doctor(doctor_id)
