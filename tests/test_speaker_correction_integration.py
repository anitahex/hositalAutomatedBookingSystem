"""Integration coverage for Phase 3 Part 1 (speaker label correction) against a real
database.

Covers exactly the invariants the spec calls out for testing:
- Bulk swap correctly flips every segment; per-segment correction affects only the
  targeted segment.
- A correction after a draft exists marks it stale and requires regeneration.
- Doctor cannot correct another doctor's consultation.
- Corrections are rejected once the SOAP note is signed (immutability starts there,
  not just at PATCH /soap — see also test_soap_notes_integration.py for the PATCH-level
  enforcement once Part 2 exists).

Skips (not fails) if no database is reachable.
"""

from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.consults import (
    begin_recording,
    correct_segment_speaker,
    get_transcript,
    record_consent,
    start_consult,
    swap_all_speakers,
)
from app.services.soap_notes import ensure_soap_schema


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
           VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
        (name, "Testing", 1),
    )
    return str(cur.fetchone()[0])


def _make_booking(cur, doctor_id, patient_id="patient-x", offset_hours=1):
    start_time = datetime.now() + timedelta(hours=offset_hours)
    end_time = start_time + timedelta(minutes=30)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
           VALUES (%s, %s, %s, TRUE) RETURNING slot_id""",
        (doctor_id, start_time, end_time),
    )
    slot_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, 'booked') RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start_time, end_time),
    )
    return str(cur.fetchone()[0])


def _seed_consult_with_final_segments(doctor_id, segments):
    """segments: list of (speaker, start_ms, end_ms, text). Returns consult dict."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            booking_id = _make_booking(cur, doctor_id)
        conn.commit()

    consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
    record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
    begin_recording(consult["id"], doctor_id, sample_rate=48000)

    with connect_db() as conn:
        with conn.cursor() as cur:
            for speaker, start_ms, end_ms, text in segments:
                cur.execute(
                    """INSERT INTO transcript_segments
                       (consultation_id, speaker, start_ms, end_ms, text, is_final)
                       VALUES (%s, %s, %s, %s, %s, TRUE)""",
                    (consult["id"], speaker, start_ms, end_ms, text),
                )
            cur.execute(
                "UPDATE consultations SET status = 'transcript_ready', transcript_source = 'batch' WHERE id = %s",
                (consult["id"],),
            )
        conn.commit()

    return consult


def _cleanup(doctor_ids):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for doctor_id in doctor_ids:
                if doctor_id:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        conn.commit()


def _seed_soap_note(doctor_id, consultation_id, status="draft"):
    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO soap_notes (consultation_id, doctor_id, status)
                   VALUES (%s, %s, %s) RETURNING id""",
                (consultation_id, doctor_id, status),
            )
            note_id = str(cur.fetchone()[0])
        conn.commit()
    return note_id


def _note_status(consultation_id):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM soap_notes WHERE consultation_id = %s", (consultation_id,))
            row = cur.fetchone()
    return row[0] if row else None


def test_swap_all_speakers_flips_every_final_segment():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Swap Speakers")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [
            ("doctor", 0, 1000, "How are you feeling today?"),
            ("patient", 1000, 2000, "I have a headache."),
            ("doctor", 2000, 3000, "How long has it been going on?"),
            ("unknown", 3000, 3500, "(inaudible)"),
        ])

        result = swap_all_speakers(consult["id"], doctor_id)
        assert result["swapped_segments"] == 3  # unknown is left alone

        transcript = get_transcript(consult["id"], doctor_id)
        speakers = [s["speaker"] for s in transcript["segments"]]
        assert speakers == ["patient", "doctor", "patient", "unknown"]
    finally:
        _cleanup([doctor_id])


def test_correct_segment_speaker_affects_only_the_targeted_segment():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Per Segment Correction")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [
            ("doctor", 0, 1000, "First line"),
            ("doctor", 1000, 2000, "Second line — actually the patient said this"),
            ("patient", 2000, 3000, "Third line"),
        ])

        transcript_before = get_transcript(consult["id"], doctor_id)
        target_segment = transcript_before["segments"][1]
        untouched_segment_ids = {
            s["id"] for s in transcript_before["segments"] if s["id"] != target_segment["id"]
        }

        result = correct_segment_speaker(consult["id"], doctor_id, target_segment["id"], "patient")
        assert result["updated"] is True

        transcript_after = get_transcript(consult["id"], doctor_id)
        by_id = {s["id"]: s for s in transcript_after["segments"]}
        assert by_id[target_segment["id"]]["speaker"] == "patient"
        for segment_id in untouched_segment_ids:
            original = next(s for s in transcript_before["segments"] if s["id"] == segment_id)
            assert by_id[segment_id]["speaker"] == original["speaker"]
    finally:
        _cleanup([doctor_id])


def test_correct_segment_speaker_rejects_invalid_speaker_value():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Invalid Speaker")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("doctor", 0, 1000, "hi")])
        segment_id = get_transcript(consult["id"], doctor_id)["segments"][0]["id"]

        with pytest.raises(ValueError):
            correct_segment_speaker(consult["id"], doctor_id, segment_id, "nurse")
    finally:
        _cleanup([doctor_id])


def test_correct_segment_speaker_scoped_to_consultation_not_just_segment_id():
    """A segment_id belonging to a DIFFERENT consultation (even a different doctor's)
    must not be reassignable just by guessing the UUID — proves the UPDATE really is
    scoped by both segment_id AND consultation_id together."""
    _skip_if_no_database()

    doctor_a = doctor_b = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_a = _make_doctor(cur, "Dr. A Cross Consult")
                doctor_b = _make_doctor(cur, "Dr. B Cross Consult")
            conn.commit()

        consult_a = _seed_consult_with_final_segments(doctor_a, [("doctor", 0, 1000, "A's segment")])
        consult_b = _seed_consult_with_final_segments(doctor_b, [("doctor", 0, 1000, "B's segment")])
        segment_a_id = get_transcript(consult_a["id"], doctor_a)["segments"][0]["id"]

        # Doctor B tries to correct A's segment by pairing it with B's OWN consultation_id.
        with pytest.raises(ValueError):
            correct_segment_speaker(consult_b["id"], doctor_b, segment_a_id, "patient")

        # A's segment is untouched.
        assert get_transcript(consult_a["id"], doctor_a)["segments"][0]["speaker"] == "doctor"
    finally:
        _cleanup([doctor_a, doctor_b])


def test_correction_marks_existing_draft_note_stale_and_returns_that_fact():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Stale Draft")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [
            ("doctor", 0, 1000, "line one"),
            ("patient", 1000, 2000, "line two"),
        ])
        _seed_soap_note(doctor_id, consult["id"], status="draft")

        segment_id = get_transcript(consult["id"], doctor_id)["segments"][0]["id"]
        result = correct_segment_speaker(consult["id"], doctor_id, segment_id, "patient")

        assert result["note_marked_stale"] is True
        assert _note_status(consult["id"]) == "stale"
    finally:
        _cleanup([doctor_id])


def test_correction_does_not_mark_note_stale_when_no_draft_exists():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. No Note Yet")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("doctor", 0, 1000, "line one")])
        segment_id = get_transcript(consult["id"], doctor_id)["segments"][0]["id"]

        result = correct_segment_speaker(consult["id"], doctor_id, segment_id, "patient")

        assert result["note_marked_stale"] is False
        assert _note_status(consult["id"]) is None
    finally:
        _cleanup([doctor_id])


def test_corrections_are_rejected_once_note_is_signed():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Signed Note Blocks Correction")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [
            ("doctor", 0, 1000, "line one"),
            ("patient", 1000, 2000, "line two"),
        ])
        _seed_soap_note(doctor_id, consult["id"], status="signed")
        segment_id = get_transcript(consult["id"], doctor_id)["segments"][0]["id"]

        with pytest.raises(PermissionError):
            correct_segment_speaker(consult["id"], doctor_id, segment_id, "patient")

        with pytest.raises(PermissionError):
            swap_all_speakers(consult["id"], doctor_id)

        # Untouched — the rejection happened before any write.
        assert get_transcript(consult["id"], doctor_id)["segments"][0]["speaker"] == "doctor"
    finally:
        _cleanup([doctor_id])


def test_swap_speakers_respects_live_fallback_transcript_source():
    """A live_fallback consult has no is_final=TRUE rows at all — swap must operate on
    ALL segments in that case (matching what get_transcript() itself returns), not
    silently no-op because nothing matches an is_final=TRUE filter."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Fallback Swap")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id, sample_rate=48000)

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO transcript_segments
                       (consultation_id, speaker, start_ms, end_ms, text, is_final)
                       VALUES (%s, 'doctor', 0, 1000, 'live only line', FALSE)""",
                    (consult["id"],),
                )
                cur.execute(
                    """UPDATE consultations
                       SET status = 'transcript_ready', transcript_source = 'live_fallback'
                       WHERE id = %s""",
                    (consult["id"],),
                )
            conn.commit()

        result = swap_all_speakers(consult["id"], doctor_id)
        assert result["swapped_segments"] == 1

        transcript = get_transcript(consult["id"], doctor_id)
        assert transcript["segments"][0]["speaker"] == "patient"
    finally:
        _cleanup([doctor_id])
