"""Regression coverage for booking_note sanitization/length-capping
(FULL_SYSTEM_AUDIT.md P0 #5 / P2 #24): booking_note is ultimately sourced from
patient chat input (directly or via an LLM-generated summary), which is untrusted,
and previously had no length cap or control-character stripping — a client could
grow the field unboundedly via repeated forwarding requests, or embed control
characters. `_sanitize_booking_note` is a pure function (no DB); the two call
sites (book_selected_slot, update_booking_note) need a real database, following
the same skip-if-unreachable convention as test_appointments_rest_e2e.py.
"""
from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services import appointments as appointments_service
from app.services.appointments import BOOKING_NOTE_MAX_LENGTH, _sanitize_booking_note


# ── Pure unit tests: _sanitize_booking_note ──────────────────────────────────

def test_sanitize_booking_note_strips_control_characters():
    dirty = "Chief complaint: fever\x00\x07 and chills"
    assert _sanitize_booking_note(dirty) == "Chief complaint: fever and chills"


def test_sanitize_booking_note_preserves_newlines_and_markdown():
    note = "**Chief Complaint:**\nFever for 3 days\n- worsening at night"
    assert _sanitize_booking_note(note) == note


def test_sanitize_booking_note_caps_length():
    huge = "a" * (BOOKING_NOTE_MAX_LENGTH + 500)
    result = _sanitize_booking_note(huge)
    assert len(result) <= BOOKING_NOTE_MAX_LENGTH + len("\n[truncated]")
    assert result.endswith("[truncated]")


def test_sanitize_booking_note_returns_none_for_empty_or_whitespace_only():
    assert _sanitize_booking_note(None) is None
    assert _sanitize_booking_note("") is None
    assert _sanitize_booking_note("   \x00\x07  ") is None


# ── DB-backed: the two write points actually apply sanitization ─────────────

def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _make_doctor(cur, name):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, 'Testing', 5, TRUE) RETURNING doctor_id""",
        (name,),
    )
    return str(cur.fetchone()[0])


def _make_slot(cur, doctor_id, offset=timedelta(hours=2)):
    start_time = datetime.now() + offset
    end_time = start_time + timedelta(minutes=30)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
           VALUES (%s, %s, %s, FALSE) RETURNING slot_id""",
        (doctor_id, start_time, end_time),
    )
    return str(cur.fetchone()[0])


def _cleanup(doctor_id):
    if not doctor_id:
        return
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        conn.commit()


def test_book_selected_slot_sanitizes_oversized_note():
    _skip_if_no_database()
    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Note Sanitization")
                slot_id = _make_slot(cur, doctor_id)
            conn.commit()

        huge_note = "x" * (BOOKING_NOTE_MAX_LENGTH + 1000)
        booking = appointments_service.book_selected_slot(slot_id, patient_id="patient-note-test", booking_note=huge_note)

        assert booking is not None
        assert len(booking["booking_note"]) <= BOOKING_NOTE_MAX_LENGTH + len("\n[truncated]")
    finally:
        _cleanup(doctor_id)


def test_update_booking_note_caps_combined_length_across_repeated_calls():
    _skip_if_no_database()
    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Repeated Note")
                slot_id = _make_slot(cur, doctor_id)
            conn.commit()

        booking = appointments_service.book_selected_slot(slot_id, patient_id="patient-note-test-2", booking_note="Initial note")
        booking_id = booking["booking_id"]

        # Repeatedly append near-max-length notes — the combined field must stay bounded.
        chunk = "y" * (BOOKING_NOTE_MAX_LENGTH - 100)
        for _ in range(3):
            appointments_service.update_booking_note(
                booking_id=booking_id, patient_id="patient-note-test-2", booking_note=chunk
            )

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT booking_note FROM appointment_bookings WHERE booking_id::text = %s", (booking_id,))
                final_note = cur.fetchone()[0]

        assert len(final_note) <= BOOKING_NOTE_MAX_LENGTH + len("\n[truncated]")
    finally:
        _cleanup(doctor_id)
