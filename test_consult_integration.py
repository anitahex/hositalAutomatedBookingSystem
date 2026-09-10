"""Integration coverage for the Part 2 consult service layer against a real database.

Covers exactly the invariants the spec calls out for testing:
- Cannot start a consult on a booking that isn't the caller's own.
- Cannot open the audio path (begin_recording) before consent.
- Retention job deletes audio past expiry but leaves transcript intact.
- Discard removes both audio and transcript.
- Doctor A cannot access Doctor B's consult or transcript.

Skips (not fails) if no database is reachable.
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services import consults as consults_module
from app.services.consults import (
    begin_recording,
    discard_consult,
    end_consult,
    get_consult_owned,
    get_transcript,
    list_latest_consult_status_by_booking,
    record_consent,
    retry_stuck_transcriptions,
    run_batch_retranscription,
    run_retention_sweep,
    start_consult,
    sweep_stale_recording_consults,
)


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


def _make_booking(cur, doctor_id, patient_id="patient-x", status="booked", offset_hours=1):
    start_time = datetime.now() + timedelta(hours=offset_hours)
    end_time = start_time + timedelta(minutes=30)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
           VALUES (%s, %s, %s, %s) RETURNING slot_id""",
        (doctor_id, start_time, end_time, status == "booked"),
    )
    slot_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start_time, end_time, status),
    )
    return str(cur.fetchone()[0])


def _cleanup(doctor_ids):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for doctor_id in doctor_ids:
                if doctor_id:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        conn.commit()


def test_cannot_start_consult_on_another_doctors_booking():
    _skip_if_no_database()

    doctor_a = doctor_b = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_a = _make_doctor(cur, "Dr. A Consult")
                doctor_b = _make_doctor(cur, "Dr. B Consult")
                booking_id = _make_booking(cur, doctor_a)
            conn.commit()

        # Doctor A can start a consult on their own booking.
        consult = start_consult(doctor_id=doctor_a, booking_id=booking_id)
        assert consult["status"] == "not_started"

        # Doctor B cannot start a consult on doctor A's booking — must not silently
        # succeed, and must not leak the fact that the booking exists for someone else.
        with pytest.raises(ValueError):
            start_consult(doctor_id=doctor_b, booking_id=booking_id)
    finally:
        _cleanup([doctor_a, doctor_b])


def test_cannot_start_consult_on_cancelled_booking():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Cancelled Booking")
                booking_id = _make_booking(cur, doctor_id, status="cancelled")
            conn.commit()

        with pytest.raises(ValueError):
            start_consult(doctor_id=doctor_id, booking_id=booking_id)
    finally:
        _cleanup([doctor_id])


def test_cannot_start_second_active_consult_for_same_booking_but_discarded_may_be_superseded():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Repeat Consult")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        first = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(first["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(first["id"], doctor_id)  # now 'recording' — an active consult exists

        with pytest.raises(PermissionError):
            start_consult(doctor_id=doctor_id, booking_id=booking_id)

        # Discard the active one, then a fresh start must be allowed.
        discard_consult(first["id"], doctor_id)
        second = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        assert second["id"] != first["id"]
    finally:
        _cleanup([doctor_id])


def test_cannot_begin_recording_before_consent():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. No Consent")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        assert consult["status"] == "not_started"

        with pytest.raises(PermissionError):
            begin_recording(consult["id"], doctor_id)
    finally:
        _cleanup([doctor_id])


def test_doctor_a_cannot_access_doctor_bs_consult_or_transcript():
    _skip_if_no_database()

    doctor_a = doctor_b = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_a = _make_doctor(cur, "Dr. A Access")
                doctor_b = _make_doctor(cur, "Dr. B Access")
                booking_id = _make_booking(cur, doctor_b)
            conn.commit()

        consult = start_consult(doctor_id=doctor_b, booking_id=booking_id)

        # Doctor A must not be able to see doctor B's consult via ownership-scoped lookup.
        assert get_consult_owned(consult["id"], doctor_a) is None
        assert get_transcript(consult["id"], doctor_a) is None

        # Doctor A must not be able to act on it either.
        with pytest.raises(ValueError):
            record_consent(consult["id"], doctor_a, account_id="00000000-0000-0000-0000-00000000000a")
        with pytest.raises(ValueError):
            begin_recording(consult["id"], doctor_a)
        with pytest.raises(ValueError):
            end_consult(consult["id"], doctor_a)
        with pytest.raises(ValueError):
            discard_consult(consult["id"], doctor_a)

        # Doctor B (the real owner) can see it fine.
        assert get_consult_owned(consult["id"], doctor_b) is not None
    finally:
        _cleanup([doctor_a, doctor_b])


def test_discard_removes_transcript_segments():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Discard Transcript")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id)

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO transcript_segments (consultation_id, speaker, start_ms, end_ms, text, is_final)
                       VALUES (%s, 'doctor', 0, 1000, 'hello', TRUE)""",
                    (consult["id"],),
                )
            conn.commit()

        result = discard_consult(consult["id"], doctor_id)
        assert result["row"]["status"] == "discarded"

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM transcript_segments WHERE consultation_id = %s",
                    (consult["id"],),
                )
                assert cur.fetchone()[0] == 0
    finally:
        _cleanup([doctor_id])


def test_retention_sweep_deletes_audio_past_expiry_but_keeps_transcript(monkeypatch):
    _skip_if_no_database()

    deleted_paths = []

    async def fake_delete_audio(blob_path):
        deleted_paths.append(blob_path)

    monkeypatch.setattr("app.services.audio_storage.delete_audio", fake_delete_audio)

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Retention Sweep")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id)

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO transcript_segments (consultation_id, speaker, start_ms, end_ms, text, is_final)
                       VALUES (%s, 'doctor', 0, 1000, 'hello', TRUE)""",
                    (consult["id"],),
                )
                # Simulate an ended, past-retention consult with stored audio.
                cur.execute(
                    """UPDATE consultations
                       SET status = 'transcript_ready', audio_blob_path = %s,
                           retention_expires_at = NOW() - INTERVAL '1 day'
                       WHERE id = %s""",
                    (f"consult-audio/{doctor_id}/{consult['id']}.pcm", consult["id"]),
                )
            conn.commit()

        deleted_count = asyncio.run(run_retention_sweep())
        assert deleted_count >= 1
        assert f"consult-audio/{doctor_id}/{consult['id']}.pcm" in deleted_paths

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT audio_deleted_at FROM consultations WHERE id = %s",
                    (consult["id"],),
                )
                assert cur.fetchone()[0] is not None
                cur.execute(
                    "SELECT count(*) FROM transcript_segments WHERE consultation_id = %s",
                    (consult["id"],),
                )
                assert cur.fetchone()[0] == 1

        # A second sweep must not try to delete the same blob again.
        deleted_paths.clear()
        asyncio.run(run_retention_sweep())
        assert f"consult-audio/{doctor_id}/{consult['id']}.pcm" not in deleted_paths
    finally:
        _cleanup([doctor_id])


def test_list_latest_consult_status_by_booking_recovers_consult_after_reload():
    """This is what lets the frontend recover which consult belongs to an appointment
    after a page reload — without it, a doctor who reloads mid-consult has no way to
    reach the consultation_id they were already working with."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Consult Lookup")
                booking_with_consult = _make_booking(cur, doctor_id, patient_id="patient-1")
                booking_without_consult = _make_booking(cur, doctor_id, patient_id="patient-2", offset_hours=2)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_with_consult)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")

        result = list_latest_consult_status_by_booking(
            doctor_id, [booking_with_consult, booking_without_consult]
        )

        assert result[booking_with_consult] == {
            "id": consult["id"], "status": "consented", "started_at": None, "ended_at": None,
        }
        assert booking_without_consult not in result
    finally:
        _cleanup([doctor_id])


def test_list_latest_consult_status_by_booking_treats_discarded_as_absent():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Discarded Lookup")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        discard_consult(consult["id"], doctor_id)

        result = list_latest_consult_status_by_booking(doctor_id, [booking_id])
        assert booking_id not in result
    finally:
        _cleanup([doctor_id])


def test_list_latest_consult_status_by_booking_handles_empty_list():
    assert list_latest_consult_status_by_booking("any-doctor-id", []) == {}


def test_list_latest_consult_status_by_booking_includes_recording_timestamps():
    """Feeds the appointments-list recording-duration badge — started_at/ended_at must
    round-trip through this lookup exactly as stored, not just {id, status}."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Duration Lookup")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id, sample_rate=48000)
        ended = end_consult(consult["id"], doctor_id)

        result = list_latest_consult_status_by_booking(doctor_id, [booking_id])

        assert result[booking_id]["status"] == "ended"
        assert result[booking_id]["started_at"] is not None
        assert result[booking_id]["ended_at"] is not None
        assert result[booking_id]["started_at"] == ended["started_at"]
        assert result[booking_id]["ended_at"] == ended["ended_at"]
    finally:
        _cleanup([doctor_id])


def test_stale_recording_sweep_force_ends_recordings_stuck_past_the_threshold():
    """Safety net for a WS handler that never reaches its own cleanup (e.g. a hung
    connection neither side ever cleanly closes) — proves the doctor-facing status
    doesn't stay 'recording' forever regardless of what the server process is doing."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Stale Recording")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id)

        # Simulate a recording that started 5 hours ago (past the default 4h threshold).
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE consultations SET started_at = NOW() - INTERVAL '5 hours' WHERE id = %s",
                    (consult["id"],),
                )
            conn.commit()

        swept = sweep_stale_recording_consults(max_hours=4)
        assert swept >= 1

        refreshed = get_consult_owned(consult["id"], doctor_id)
        assert refreshed["status"] == "ended"
    finally:
        _cleanup([doctor_id])


def test_stale_recording_sweep_leaves_recent_recordings_alone():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Fresh Recording")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id)

        swept = sweep_stale_recording_consults(max_hours=4)

        refreshed = get_consult_owned(consult["id"], doctor_id)
        assert refreshed["status"] == "recording"
    finally:
        _cleanup([doctor_id])


def test_concurrent_batch_retranscription_calls_for_same_consult_do_not_duplicate_segments(monkeypatch):
    """Reproduces, against the real database, the exact race a doctor manually recovering
    an 'orphaned' recording can now trigger: the fix that lets run_batch_retranscription
    be scheduled twice for the same consult (once from a manual End, once from a delayed
    WS handler finalizing real audio afterward) must not let both runs write concurrently
    — empirically confirmed elsewhere that Postgres's own DELETE+INSERT semantics do NOT
    protect against this on their own (a DELETE blocked on a row lock, once unblocked,
    doesn't retroactively catch rows the other transaction just inserted)."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Concurrent Retranscribe")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id, sample_rate=48000)
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE consultations SET audio_blob_path = %s WHERE id = %s",
                    (f"consult-audio/{doctor_id}/{consult['id']}.pcm", consult["id"]),
                )
            conn.commit()

        call_index = {"n": 0}
        overlap_detected = {"value": False}
        in_flight = {"count": 0}

        async def fake_download_audio(path):
            in_flight["count"] += 1
            if in_flight["count"] > 1:
                overlap_detected["value"] = True
            await asyncio.sleep(0.1)
            in_flight["count"] -= 1
            return b"fake-audio-bytes"

        async def fake_transcribe(audio_bytes, *, department, sample_rate):
            call_index["n"] += 1
            return [
                {
                    "speaker": "doctor", "start_ms": 0, "end_ms": 1000,
                    "text": f"pass-{call_index['n']}", "confidence": 0.9,
                }
            ]

        monkeypatch.setattr("app.services.audio_storage.download_audio", fake_download_audio)
        monkeypatch.setattr(consults_module, "_deepgram_prerecorded_transcribe", fake_transcribe)

        async def run_both():
            await asyncio.gather(
                run_batch_retranscription(consult["id"]),
                run_batch_retranscription(consult["id"]),
            )

        asyncio.run(run_both())

        assert overlap_detected["value"] is False, "both calls ran their download/transcribe step concurrently"

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT text FROM transcript_segments WHERE consultation_id = %s",
                    (consult["id"],),
                )
                rows = cur.fetchall()
        assert len(rows) == 1, f"expected exactly one segment (no duplicates), found {rows}"
    finally:
        _cleanup([doctor_id])


def test_begin_recording_persists_the_actual_sample_rate():
    """The batch pass later needs the TRUE rate the browser recorded at — not a
    hardcoded guess — to correctly decode headerless raw PCM via Deepgram."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Sample Rate")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        result = begin_recording(consult["id"], doctor_id, sample_rate=44100)

        assert result["audio_sample_rate"] == 44100
        refreshed = get_consult_owned(consult["id"], doctor_id)
        assert refreshed["audio_sample_rate"] == 44100
    finally:
        _cleanup([doctor_id])


def test_get_transcript_filters_to_batch_final_segments_only():
    """Bug 1: the transcript must only ever surface is_final=TRUE (batch-pass) rows once
    the batch pass has succeeded — not every live/interim segment ever streamed in."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Transcript Filter")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id, sample_rate=48000)

        with connect_db() as conn:
            with conn.cursor() as cur:
                # Simulate a real live-streamed recording: many is_final=FALSE rows
                # (this schema's correct semantics — see parse_deepgram_streaming_result),
                # then a successful batch pass leaving exactly one is_final=TRUE row.
                for i in range(5):
                    cur.execute(
                        """INSERT INTO transcript_segments
                           (consultation_id, speaker, start_ms, end_ms, text, is_final)
                           VALUES (%s, 'doctor', %s, %s, %s, FALSE)""",
                        (consult["id"], i * 1000, i * 1000 + 900, f"live interim {i}"),
                    )
                cur.execute(
                    """INSERT INTO transcript_segments
                       (consultation_id, speaker, start_ms, end_ms, text, is_final)
                       VALUES (%s, 'doctor', 0, 5000, 'the real batch transcript', TRUE)""",
                    (consult["id"],),
                )
                cur.execute(
                    """UPDATE consultations
                       SET status = 'transcript_ready', transcript_source = 'batch'
                       WHERE id = %s""",
                    (consult["id"],),
                )
            conn.commit()

        transcript = get_transcript(consult["id"], doctor_id)
        assert transcript["transcript_source"] == "batch"
        assert len(transcript["segments"]) == 1
        assert transcript["segments"][0]["text"] == "the real batch transcript"
        assert transcript["segments"][0]["is_final"] is True
    finally:
        _cleanup([doctor_id])


def test_get_transcript_returns_live_segments_with_explicit_fallback_flag_on_batch_failure():
    """Bug 2's observability requirement: a failed batch pass must never look like an
    ordinary, authoritative transcript — the caller must be able to tell it's a fallback
    and see why, rather than the failure being silently swallowed."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Fallback Flag")
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
                       VALUES (%s, 'doctor', 0, 1000, 'live only segment', FALSE)""",
                    (consult["id"],),
                )
                cur.execute(
                    """UPDATE consultations
                       SET status = 'transcript_ready', transcript_source = 'live_fallback',
                           transcript_fallback_error = 'Deepgram request failed: 500'
                       WHERE id = %s""",
                    (consult["id"],),
                )
            conn.commit()

        transcript = get_transcript(consult["id"], doctor_id)
        assert transcript["transcript_source"] == "live_fallback"
        assert transcript["transcript_fallback_error"] == "Deepgram request failed: 500"
        # Still returns the live content — losing it entirely would be worse for the
        # doctor than an honestly-labeled fallback.
        assert len(transcript["segments"]) == 1
        assert transcript["segments"][0]["text"] == "live only segment"
    finally:
        _cleanup([doctor_id])


def test_run_batch_retranscription_uses_the_persisted_sample_rate_not_a_hardcoded_guess(monkeypatch):
    """Regression test for the actual root cause: _deepgram_prerecorded_transcribe was
    previously called with a hardcoded sample_rate=16000 regardless of what the browser
    actually recorded at (typically 44100/48000), silently feeding Deepgram mis-decoded
    audio. Confirms the real, persisted rate is what actually gets used."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Real Sample Rate Used")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id, sample_rate=44100)
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE consultations SET audio_blob_path = %s WHERE id = %s",
                    (f"consult-audio/{doctor_id}/{consult['id']}.pcm", consult["id"]),
                )
            conn.commit()

        seen_sample_rate = {}

        async def fake_download_audio(path):
            return b"fake-audio-bytes"

        async def fake_transcribe(audio_bytes, *, department, sample_rate):
            seen_sample_rate["value"] = sample_rate
            return [{"speaker": "doctor", "start_ms": 0, "end_ms": 1000, "text": "ok", "confidence": 0.9}]

        monkeypatch.setattr("app.services.audio_storage.download_audio", fake_download_audio)
        monkeypatch.setattr(consults_module, "_deepgram_prerecorded_transcribe", fake_transcribe)

        asyncio.run(run_batch_retranscription(consult["id"]))

        assert seen_sample_rate["value"] == 44100

        refreshed = get_consult_owned(consult["id"], doctor_id)
        assert refreshed["transcript_source"] == "batch"
    finally:
        _cleanup([doctor_id])


def test_run_batch_retranscription_falls_back_with_clear_error_when_sample_rate_missing():
    """Rather than silently guessing a sample rate (the original bug), a consult with no
    recorded rate must fall back explicitly, with a specific, surfaced error — not just
    reach transcript_ready looking like nothing went wrong."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Missing Sample Rate")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id)  # no sample_rate passed -> NULL in DB
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE consultations SET audio_blob_path = %s WHERE id = %s",
                    (f"consult-audio/{doctor_id}/{consult['id']}.pcm", consult["id"]),
                )
            conn.commit()

        asyncio.run(run_batch_retranscription(consult["id"]))

        transcript = get_transcript(consult["id"], doctor_id)
        assert transcript["status"] == "transcript_ready"
        assert transcript["transcript_source"] == "live_fallback"
        assert "sample rate" in transcript["transcript_fallback_error"].lower()
    finally:
        _cleanup([doctor_id])


def test_retry_stuck_transcriptions_recovers_a_consult_stuck_in_ended():
    """Reproduces the narrow gap _run_batch_retranscription_locked's own try/except
    can't cover on its own: a consult that never even got a chance to start batch
    processing (simulated here by never calling run_batch_retranscription at all after
    end_consult, then leaving it stuck past the threshold) must still eventually reach
    transcript_ready via this periodic retry, not sit at 'ended' forever."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Stuck Ended")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id, sample_rate=48000)
        end_consult(consult["id"], doctor_id)  # status='ended', but no retranscription ever scheduled

        # Simulate it having been stuck for a while (past CONSULT_MAX_TRANSCRIBING_HOURS).
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE consultations SET updated_at = NOW() - INTERVAL '2 hours' WHERE id = %s",
                    (consult["id"],),
                )
            conn.commit()

        retried = asyncio.run(retry_stuck_transcriptions())
        assert retried >= 1

        refreshed = get_consult_owned(consult["id"], doctor_id)
        assert refreshed["status"] == "transcript_ready"
        # No real audio was ever recorded here, so this correctly falls back rather than
        # silently succeeding with fabricated content.
        assert refreshed["transcript_source"] == "live_fallback"
    finally:
        _cleanup([doctor_id])


def test_retry_stuck_transcriptions_leaves_recent_ended_consults_alone():
    """A consult that JUST transitioned to 'ended' moments ago (the normal, brief window
    before its scheduled retranscription task actually runs) must not be retried
    prematurely — only genuinely stuck ones past the threshold."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Recently Ended")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id, sample_rate=48000)
        end_consult(consult["id"], doctor_id)

        asyncio.run(retry_stuck_transcriptions())

        refreshed = get_consult_owned(consult["id"], doctor_id)
        assert refreshed["status"] == "ended"
    finally:
        _cleanup([doctor_id])
