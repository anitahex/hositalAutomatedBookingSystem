from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import Counter
from datetime import datetime, timedelta
from urllib.parse import quote

from app.db.connection import connect_db
from app.services.appointments import ensure_booking_schema, normalize_department_name

logger = logging.getLogger(__name__)

try:
    import aiohttp
except ImportError:  # pragma: no cover — declared in requirements.txt
    aiohttp = None  # type: ignore[assignment]

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
DEEPGRAM_MODEL = os.getenv("DEEPGRAM_MODEL", "nova-3-medical")
CONSULT_RETENTION_DAYS = int(os.getenv("CONSULT_RETENTION_DAYS", "60"))
CONSULT_MAX_RECORDING_HOURS = float(os.getenv("CONSULT_MAX_RECORDING_HOURS", "4"))

# Statuses that mean "there is already an active or completed recording for this booking" —
# a 'discarded' one may always be superseded by a fresh start, per spec.
_ACTIVE_CONSULT_STATUSES = ("recording", "transcribing", "transcript_ready")

_TRANSCRIPT_SEGMENT_COLUMNS = "id, speaker, start_ms, end_ms, text, confidence, is_final"


def ensure_consult_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS consultations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                booking_id UUID NOT NULL REFERENCES appointment_bookings(booking_id) ON DELETE CASCADE,
                doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                patient_id TEXT,
                status TEXT NOT NULL DEFAULT 'not_started',
                consent_confirmed_by UUID,
                consent_confirmed_at TIMESTAMP,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                audio_blob_path TEXT,
                audio_sample_rate INTEGER,
                transcript_source TEXT,
                transcript_fallback_error TEXT,
                retention_expires_at TIMESTAMP,
                audio_deleted_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            ALTER TABLE consultations ADD COLUMN IF NOT EXISTS audio_sample_rate INTEGER;
            ALTER TABLE consultations ADD COLUMN IF NOT EXISTS transcript_source TEXT;
            ALTER TABLE consultations ADD COLUMN IF NOT EXISTS transcript_fallback_error TEXT;
            CREATE INDEX IF NOT EXISTS idx_consultations_doctor ON consultations(doctor_id);
            CREATE INDEX IF NOT EXISTS idx_consultations_booking ON consultations(booking_id);
            CREATE INDEX IF NOT EXISTS idx_consultations_retention
                ON consultations(retention_expires_at)
                WHERE audio_deleted_at IS NULL AND audio_blob_path IS NOT NULL;
            -- Defense-in-depth backstop for the FOR UPDATE lock in start_consult()
            -- (FULL_SYSTEM_AUDIT.md P1 #8): at most one row per booking may be in an
            -- active-recording status at a time. Mirrors the same lock+unique-index
            -- pairing already used for appointment_slots/appointment_bookings.
            CREATE UNIQUE INDEX IF NOT EXISTS ux_consultations_active_booking
                ON consultations(booking_id)
                WHERE status IN ('recording', 'transcribing', 'transcript_ready');

            CREATE TABLE IF NOT EXISTS transcript_segments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                consultation_id UUID NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
                speaker TEXT NOT NULL DEFAULT 'unknown',
                start_ms INTEGER NOT NULL,
                end_ms INTEGER NOT NULL,
                text TEXT NOT NULL,
                confidence REAL,
                is_final BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_transcript_segments_consultation
                ON transcript_segments(consultation_id, start_ms);

            CREATE TABLE IF NOT EXISTS keyterm_vocabulary (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                term TEXT NOT NULL,
                department TEXT,
                source TEXT NOT NULL DEFAULT 'doctor_submitted',
                created_by UUID,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_keyterm_vocabulary_department ON keyterm_vocabulary(department);

            CREATE TABLE IF NOT EXISTS consult_audit_log (
                audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                consultation_id UUID REFERENCES consultations(id) ON DELETE SET NULL,
                doctor_id UUID REFERENCES doctors(doctor_id) ON DELETE SET NULL,
                action_type TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_consult_audit_consultation
                ON consult_audit_log(consultation_id, created_at DESC);
            """
        )


def _audit(cur, action: str, consultation_id: str | None, doctor_id: str | None, **metadata) -> None:
    cur.execute(
        "INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata) VALUES (%s, %s, %s, %s::jsonb)",
        (consultation_id, doctor_id, action, json.dumps(metadata)),
    )


def _row_to_dict(row) -> dict:
    (
        id_, booking_id, doctor_id, patient_id, status, consent_confirmed_by, consent_confirmed_at,
        started_at, ended_at, audio_blob_path, audio_sample_rate, transcript_source,
        transcript_fallback_error, retention_expires_at, audio_deleted_at,
    ) = row
    return {
        "id": str(id_),
        "booking_id": str(booking_id),
        "doctor_id": str(doctor_id),
        "patient_id": patient_id,
        "status": status,
        "consent_confirmed_by": str(consent_confirmed_by) if consent_confirmed_by else None,
        "consent_confirmed_at": consent_confirmed_at.isoformat() if consent_confirmed_at else None,
        "started_at": started_at.isoformat() if started_at else None,
        "ended_at": ended_at.isoformat() if ended_at else None,
        "audio_sample_rate": audio_sample_rate,
        "transcript_source": transcript_source,
        "transcript_fallback_error": transcript_fallback_error,
        "retention_expires_at": retention_expires_at.isoformat() if retention_expires_at else None,
        "audio_deleted_at": audio_deleted_at.isoformat() if audio_deleted_at else None,
    }


_CONSULT_COLUMNS = (
    "id, booking_id, doctor_id, patient_id, status, consent_confirmed_by, consent_confirmed_at, "
    "started_at, ended_at, audio_blob_path, audio_sample_rate, transcript_source, "
    "transcript_fallback_error, retention_expires_at, audio_deleted_at"
)


def get_consult_owned(consultation_id: str, doctor_id: str) -> dict | None:
    """Returns None if this consult doesn't exist OR doesn't belong to this doctor —
    the caller must treat both cases identically (404), never distinguishing them."""
    with connect_db() as conn:
        ensure_booking_schema(conn)
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_CONSULT_COLUMNS} FROM consultations WHERE id = %s AND doctor_id = %s",
                (consultation_id, doctor_id),
            )
            row = cur.fetchone()
    return _row_to_dict(row) if row else None


def start_consult(*, doctor_id: str, booking_id: str) -> dict:
    with connect_db() as conn:
        try:
            ensure_booking_schema(conn)
            ensure_consult_schema(conn)
            with conn.cursor() as cur:
                # FOR UPDATE serializes concurrent start_consult calls for the SAME
                # booking (double-click, two tabs) — without it, two transactions can
                # both pass the "no active consult yet" check below before either
                # commits its INSERT, creating two simultaneous consultations for one
                # booking (FULL_SYSTEM_AUDIT.md P1 #8). Matches the FOR UPDATE
                # discipline every other consult-mutating function in this file uses.
                cur.execute(
                    "SELECT patient_id, status FROM appointment_bookings WHERE booking_id = %s AND doctor_id = %s FOR UPDATE",
                    (booking_id, doctor_id),
                )
                booking = cur.fetchone()
                if not booking:
                    raise ValueError("Booking not found.")
                patient_id, booking_status = booking
                if booking_status == "cancelled":
                    raise ValueError("This booking has been cancelled.")

                cur.execute(
                    "SELECT status FROM consultations WHERE booking_id = %s",
                    (booking_id,),
                )
                existing_statuses = {r[0] for r in cur.fetchall()}
                # Block on ANY non-discarded consult, not just an already-actively-recording
                # one — a lingering 'not_started'/'consented'/'ended' row is still a real
                # consult for this booking, and only 'discarded' is meant to be freely
                # superseded by a fresh start (see the module-level _ACTIVE_CONSULT_STATUSES
                # comment). Previously this only checked _ACTIVE_CONSULT_STATUSES, which let
                # two calls that both land on 'not_started' both succeed even under the FOR
                # UPDATE lock above — confirmed by a real concurrency test before this fix
                # (FULL_SYSTEM_AUDIT.md P1 #8).
                if existing_statuses - {"discarded"}:
                    raise PermissionError("A consult already exists for this booking.")

                cur.execute(
                    """
                    INSERT INTO consultations (booking_id, doctor_id, patient_id, status)
                    VALUES (%s, %s, %s, 'not_started')
                    RETURNING """ + _CONSULT_COLUMNS,
                    (booking_id, doctor_id, patient_id),
                )
                row = cur.fetchone()
                _audit(cur, "consult_started", str(row[0]), doctor_id, booking_id=booking_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return _row_to_dict(row)


def record_consent(consultation_id: str, doctor_id: str, *, account_id: str) -> dict:
    with connect_db() as conn:
        try:
            ensure_consult_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {_CONSULT_COLUMNS} FROM consultations WHERE id = %s AND doctor_id = %s FOR UPDATE",
                    (consultation_id, doctor_id),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Consult not found.")
                consult = _row_to_dict(row)
                if consult["status"] not in ("not_started", "consented"):
                    raise ValueError(f"Cannot record consent for a consult in status '{consult['status']}'.")

                cur.execute(
                    """
                    UPDATE consultations
                    SET status = 'consented', consent_confirmed_by = %s, consent_confirmed_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    RETURNING """ + _CONSULT_COLUMNS,
                    (account_id, consultation_id),
                )
                row = cur.fetchone()
                _audit(cur, "consult_consent_confirmed", consultation_id, doctor_id, account_id=account_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return _row_to_dict(row)


def begin_recording(consultation_id: str, doctor_id: str, *, sample_rate: int | None = None) -> dict:
    """Called when the audio WebSocket connects. Requires status == 'consented'.

    sample_rate must be the ACTUAL rate the browser's AudioContext used to capture and
    encode the raw linear16 PCM audio (there is no WAV header to self-describe it) —
    persisted here so the batch re-transcription pass can later tell Deepgram's
    prerecorded API the true rate, instead of guessing. Previously this was hardcoded to
    16000 in the batch-pass call regardless of what was actually recorded (typically
    44100/48000 from a real browser AudioContext), which silently fed Deepgram
    mis-decoded audio and produced empty or garbage results — the root cause of "batch
    re-transcription never produces output.\""""
    with connect_db() as conn:
        try:
            ensure_consult_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {_CONSULT_COLUMNS} FROM consultations WHERE id = %s AND doctor_id = %s FOR UPDATE",
                    (consultation_id, doctor_id),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Consult not found.")
                consult = _row_to_dict(row)
                if consult["status"] != "consented":
                    raise PermissionError("Recording requires a consented consult.")

                cur.execute(
                    """
                    UPDATE consultations
                    SET status = 'recording', started_at = NOW(), audio_sample_rate = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING """ + _CONSULT_COLUMNS,
                    (sample_rate, consultation_id),
                )
                row = cur.fetchone()
                _audit(cur, "consult_recording_started", consultation_id, doctor_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return _row_to_dict(row)


def append_transcript_segment(
    consultation_id: str, *, speaker: str, start_ms: int, end_ms: int, text: str,
    confidence: float | None, is_final: bool,
) -> None:
    with connect_db() as conn:
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transcript_segments (consultation_id, speaker, start_ms, end_ms, text, confidence, is_final)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (consultation_id, speaker, start_ms, end_ms, text, confidence, is_final),
            )
        conn.commit()


def set_audio_blob_path(consultation_id: str, blob_path: str) -> None:
    with connect_db() as conn:
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE consultations SET audio_blob_path = %s, updated_at = NOW() WHERE id = %s",
                (blob_path, consultation_id),
            )
        conn.commit()


def end_consult(consultation_id: str, doctor_id: str) -> dict:
    """Idempotent: ending an already-ended/transcribing/transcript_ready/discarded consult
    just returns its current state rather than erroring (mirrors unlock_doctor_account's
    idempotent design — a doctor retrying 'end' after a flaky connection shouldn't 400)."""
    with connect_db() as conn:
        try:
            ensure_consult_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {_CONSULT_COLUMNS} FROM consultations WHERE id = %s AND doctor_id = %s FOR UPDATE",
                    (consultation_id, doctor_id),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Consult not found.")
                consult = _row_to_dict(row)
                if consult["status"] not in ("consented", "recording"):
                    conn.commit()
                    return consult

                retention_expires_at = datetime.now() + timedelta(days=CONSULT_RETENTION_DAYS)
                cur.execute(
                    """
                    UPDATE consultations
                    SET status = 'ended', ended_at = NOW(), retention_expires_at = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING """ + _CONSULT_COLUMNS,
                    (retention_expires_at, consultation_id),
                )
                row = cur.fetchone()
                _audit(cur, "consult_ended", consultation_id, doctor_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return _row_to_dict(row)


def sweep_stale_recording_consults(max_hours: float | None = None) -> int:
    """Safety net independent of relying solely on Deepgram/websockets' own ping-pong
    liveness detection to eventually unblock a truly dead WS connection (reasoned through
    as bounded to roughly the ping_interval+ping_timeout window used when connecting to
    Deepgram, but that reasoning couldn't be verified against a live Deepgram connection
    in this environment). Force-transitions any consult stuck in 'recording' for longer
    than max_hours to 'ended', so a doctor never sees a permanently stuck status from the
    UI's perspective, regardless of what's actually happening server-side.

    Deliberately does NOT kick off batch re-transcription itself: if the original WS
    handler coroutine is still alive and eventually does unblock, it will call
    end_consult() on its own — which is idempotent and safely no-ops once this sweep has
    already moved the row to 'ended' — and finalize_recording()/set_audio_blob_path() from
    that handler still run normally afterward. Scheduling re-transcription from here too
    could race ahead of that with no audio_blob_path yet set.
    """
    max_age = CONSULT_MAX_RECORDING_HOURS if max_hours is None else max_hours

    with connect_db() as conn:
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, doctor_id
                FROM consultations
                WHERE status = 'recording'
                    AND started_at IS NOT NULL
                    AND started_at <= NOW() - (%s * INTERVAL '1 hour')
                """,
                (max_age,),
            )
            stale = cur.fetchall()

    swept = 0
    for consultation_id, doctor_id in stale:
        with connect_db() as conn:
            with conn.cursor() as cur:
                retention_expires_at = datetime.now() + timedelta(days=CONSULT_RETENTION_DAYS)
                cur.execute(
                    """
                    UPDATE consultations
                    SET status = 'ended', ended_at = NOW(), retention_expires_at = %s, updated_at = NOW()
                    WHERE id = %s AND status = 'recording'
                    """,
                    (retention_expires_at, str(consultation_id)),
                )
                if cur.rowcount:
                    _audit(
                        cur, "consult_recording_force_ended_stale", str(consultation_id), str(doctor_id),
                        max_hours=max_age,
                    )
                    swept += 1
            conn.commit()

    return swept


def set_status(consultation_id: str, status: str) -> None:
    with connect_db() as conn:
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE consultations SET status = %s, updated_at = NOW() WHERE id = %s",
                (status, consultation_id),
            )
        conn.commit()


def discard_consult(consultation_id: str, doctor_id: str) -> dict:
    """Returns {"row": <consult dict>, "audio_blob_path": <str | None>} — the caller
    (route) is responsible for actually deleting the blob at that path, since blob
    deletion is async and this function's DB work is not."""
    audio_blob_path = None
    with connect_db() as conn:
        try:
            ensure_consult_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {_CONSULT_COLUMNS}, audio_blob_path FROM consultations WHERE id = %s AND doctor_id = %s FOR UPDATE",
                    (consultation_id, doctor_id),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Consult not found.")
                *consult_row, audio_blob_path = row
                consult = _row_to_dict(tuple(consult_row))
                if consult["status"] == "discarded":
                    conn.commit()
                    return {"row": consult, "audio_blob_path": None}

                cur.execute("DELETE FROM transcript_segments WHERE consultation_id = %s", (consultation_id,))
                cur.execute(
                    """
                    UPDATE consultations
                    SET status = 'discarded', updated_at = NOW()
                    WHERE id = %s
                    RETURNING """ + _CONSULT_COLUMNS,
                    (consultation_id,),
                )
                row = cur.fetchone()
                _audit(cur, "consult_discarded", consultation_id, doctor_id, had_audio=bool(audio_blob_path))
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {"row": _row_to_dict(row), "audio_blob_path": audio_blob_path}


def get_transcript(consultation_id: str, doctor_id: str) -> dict | None:
    """is_final=TRUE only ever means "the batch re-transcription pass produced this
    segment" (see replace_final_transcript / parse_deepgram_streaming_result's
    docstrings) — so the normal case filters to those rows only, since the live/interim
    ones stored during streaming are superseded by design once the batch pass succeeds.
    If the batch pass failed (transcript_source == 'live_fallback'), there ARE no
    is_final=TRUE rows for this consult at all; the only content available is the raw
    live capture, returned in full so the doctor isn't left with nothing, but the
    response makes that fallback explicit via transcript_source/transcript_fallback_error
    rather than presenting it as an equally-authoritative result."""
    consult = get_consult_owned(consultation_id, doctor_id)
    if not consult:
        return None

    segments: list[dict] = []
    if consult["status"] == "transcript_ready":
        is_fallback = consult.get("transcript_source") == "live_fallback"
        with connect_db() as conn:
            ensure_consult_schema(conn)
            with conn.cursor() as cur:
                if is_fallback:
                    cur.execute(
                        f"SELECT {_TRANSCRIPT_SEGMENT_COLUMNS} FROM transcript_segments "
                        "WHERE consultation_id = %s ORDER BY start_ms ASC",
                        (consultation_id,),
                    )
                else:
                    cur.execute(
                        f"SELECT {_TRANSCRIPT_SEGMENT_COLUMNS} FROM transcript_segments "
                        "WHERE consultation_id = %s AND is_final = TRUE ORDER BY start_ms ASC",
                        (consultation_id,),
                    )
                rows = cur.fetchall()
        segments = [
            {
                "id": str(segment_id), "speaker": speaker, "start_ms": start_ms, "end_ms": end_ms,
                "text": text, "confidence": confidence, "is_final": is_final,
            }
            for segment_id, speaker, start_ms, end_ms, text, confidence, is_final in rows
        ]

    return {
        "status": consult["status"],
        "segments": segments,
        "transcript_source": consult.get("transcript_source"),
        "transcript_fallback_error": consult.get("transcript_fallback_error"),
    }


_VALID_SPEAKERS = ("doctor", "patient", "unknown")


def _reject_if_note_signed(consultation_id: str) -> None:
    from app.services.soap_notes import get_note_status_for_consultation

    if get_note_status_for_consultation(consultation_id) == "signed":
        raise PermissionError("Cannot correct speaker labels after the SOAP note has been signed.")


def swap_all_speakers(consultation_id: str, doctor_id: str) -> dict:
    """Flips doctor<->patient across every segment that currently counts as part of 'the'
    transcript — the same is_final/transcript_source-conditioned set get_transcript()
    itself returns, so a correction always matches what the doctor is actually looking
    at (a live_fallback consult has no is_final=TRUE rows at all, so restricting to
    those would silently no-op there). This is the cheap, high-value fix for the most
    likely diarization failure mode: the whole mapping being backwards, not just a few
    misattributed lines."""
    consult = get_consult_owned(consultation_id, doctor_id)
    if not consult:
        raise ValueError("Consult not found.")
    _reject_if_note_signed(consultation_id)

    is_fallback = consult.get("transcript_source") == "live_fallback"
    with connect_db() as conn:
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            final_clause = "" if is_fallback else "AND is_final = TRUE"
            cur.execute(
                f"""
                UPDATE transcript_segments
                SET speaker = CASE speaker
                    WHEN 'doctor' THEN 'patient'
                    WHEN 'patient' THEN 'doctor'
                END
                WHERE consultation_id = %s {final_clause} AND speaker IN ('doctor', 'patient')
                """,
                (consultation_id,),
            )
            # Restricting the WHERE to speaker IN ('doctor','patient') (rather than just
            # relying on the CASE's ELSE branch to no-op) makes rowcount accurately
            # reflect segments that actually flipped — an 'unknown'-speaker row matches
            # neither branch of the CASE, but a plain UPDATE's rowcount otherwise counts
            # every row the WHERE clause matched, changed or not.
            swapped_count = cur.rowcount
            _audit(cur, "consult_transcript_speakers_swapped", consultation_id, doctor_id, segment_count=swapped_count)
        conn.commit()

    from app.services.soap_notes import mark_note_stale_if_draft_exists

    note_marked_stale = mark_note_stale_if_draft_exists(consultation_id)
    return {"swapped_segments": swapped_count, "note_marked_stale": note_marked_stale}


def correct_segment_speaker(consultation_id: str, doctor_id: str, segment_id: str, speaker: str) -> dict:
    """Reassigns a single segment's speaker — for cases where diarization drifted
    mid-conversation rather than being globally inverted (see swap_all_speakers for
    that case). Scoped by BOTH segment_id and consultation_id in the same UPDATE, so a
    segment_id belonging to a different (even a different doctor's) consultation simply
    matches zero rows rather than being reassignable by guessing a UUID."""
    if speaker not in _VALID_SPEAKERS:
        raise ValueError(f"speaker must be one of {_VALID_SPEAKERS}.")

    consult = get_consult_owned(consultation_id, doctor_id)
    if not consult:
        raise ValueError("Consult not found.")
    _reject_if_note_signed(consultation_id)

    with connect_db() as conn:
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE transcript_segments SET speaker = %s WHERE id = %s AND consultation_id = %s",
                (speaker, segment_id, consultation_id),
            )
            updated = cur.rowcount > 0
            if updated:
                _audit(
                    cur, "consult_transcript_segment_corrected", consultation_id, doctor_id,
                    segment_id=segment_id, speaker=speaker,
                )
        conn.commit()

    if not updated:
        raise ValueError("Transcript segment not found.")

    from app.services.soap_notes import mark_note_stale_if_draft_exists

    note_marked_stale = mark_note_stale_if_draft_exists(consultation_id)
    return {"updated": True, "note_marked_stale": note_marked_stale}


def list_latest_consult_status_by_booking(doctor_id: str, booking_ids: list[str]) -> dict[str, dict]:
    """For each booking_id, the most recent non-discarded consult's
    {id, status, started_at, ended_at} — a booking with no entry in the returned dict has
    either never had a consult started, or every consult for it was discarded (which the
    spec treats as 'may be superseded', i.e. equivalent to never started). Lets the
    frontend recover which consult (if any) belongs to an appointment after a page
    reload, since nothing before this tracked that client-side. started_at/ended_at are
    included so the appointments list can show a recording-duration badge without a
    second round trip per row."""
    if not booking_ids:
        return {}
    with connect_db() as conn:
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (booking_id) booking_id, id, status, started_at, ended_at
                FROM consultations
                WHERE doctor_id = %s AND booking_id::text = ANY(%s) AND status != 'discarded'
                ORDER BY booking_id, created_at DESC
                """,
                (doctor_id, booking_ids),
            )
            rows = cur.fetchall()
    return {
        str(booking_id): {
            "id": str(id_),
            "status": status,
            "started_at": started_at.isoformat() if started_at else None,
            "ended_at": ended_at.isoformat() if ended_at else None,
        }
        for booking_id, id_, status, started_at, ended_at in rows
    }


def list_keyterms_for_department(department: str | None) -> list[str]:
    normalized = normalize_department_name(department) if department else None
    with connect_db() as conn:
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            if normalized:
                cur.execute(
                    "SELECT term FROM keyterm_vocabulary WHERE department IS NULL OR department = %s",
                    (normalized,),
                )
            else:
                cur.execute("SELECT term FROM keyterm_vocabulary WHERE department IS NULL")
            rows = cur.fetchall()
    return [r[0] for r in rows]


def _majority_speaker(words: list[dict]) -> str:
    """Deepgram diarization returns a numeric speaker cluster id per word, not an identity.
    There is no reliable way to know which numeric id is the doctor vs. the patient from
    Deepgram's output alone. Heuristic (unverified against real audio): speaker 0 -> doctor
    (the device holder is usually first to speak, e.g. greeting the patient), speaker 1 ->
    patient, anything else -> unknown. This is a reasonable default, not a guarantee — flag
    this to users if diarized speaker labels ever look swapped."""
    speaker_ids = [w.get("speaker") for w in words if w.get("speaker") is not None]
    if not speaker_ids:
        return "unknown"
    common = Counter(speaker_ids).most_common(1)[0][0]
    if common == 0:
        return "doctor"
    if common == 1:
        return "patient"
    return "unknown"


def parse_deepgram_streaming_result(data: dict) -> dict | None:
    """Extract one persistable segment from a single Deepgram streaming 'Results' message,
    or None if the message carries nothing worth storing (e.g. silence, non-Results events).

    is_final is ALWAYS False here, regardless of Deepgram's own 'is_final' flag on the
    message (which just means "Deepgram is done refining this one utterance" — a
    streaming-ASR concept, arriving continuously throughout the recording). That is a
    different thing from this schema's is_final, which specifically means "our batch
    re-transcription pass produced and replaced this segment" (see replace_final_transcript).
    Conflating the two here previously made every live segment indistinguishable from a
    genuine batch-pass result once Deepgram happened to mark an utterance done — is_final
    must only ever be set True by replace_final_transcript."""
    if data.get("type") != "Results":
        return None
    channel = data.get("channel") or {}
    alternatives = channel.get("alternatives") or []
    if not alternatives:
        return None
    alt = alternatives[0]
    text = (alt.get("transcript") or "").strip()
    if not text:
        return None

    start = data.get("start")
    duration = data.get("duration")
    start_ms = int(float(start) * 1000) if start is not None else 0
    end_ms = start_ms + int(float(duration) * 1000) if duration is not None else start_ms

    return {
        "speaker": _majority_speaker(alt.get("words") or []),
        "start_ms": start_ms,
        "end_ms": end_ms,
        "text": text,
        "confidence": alt.get("confidence"),
        "is_final": False,
    }


def build_deepgram_streaming_url(*, sample_rate: str, keyterms: list[str]) -> str:
    params = [
        f"model={DEEPGRAM_MODEL}",
        "encoding=linear16",
        f"sample_rate={sample_rate}",
        "channels=1",
        "interim_results=true",
        "smart_format=true",
        "punctuate=true",
        "diarize=true",
        "filler_words=true",
    ]
    for term in keyterms:
        params.append(f"keyterm={quote(term)}")
    return "wss://api.deepgram.com/v1/listen?" + "&".join(params)


def _parse_prerecorded_segments(payload: dict) -> list[dict]:
    """Group consecutive same-speaker words from Deepgram's prerecorded (batch) response
    into segments. Untested against a live Deepgram response in this environment (no API
    key configured here) — verify against a real recording before relying on this in
    production."""
    try:
        channels = payload["results"]["channels"]
        words = channels[0]["alternatives"][0].get("words") or []
    except (KeyError, IndexError, TypeError):
        return []

    segments: list[dict] = []
    current: dict | None = None
    for word in words:
        speaker_id = word.get("speaker")
        speaker = "doctor" if speaker_id == 0 else "patient" if speaker_id == 1 else "unknown"
        token = word.get("punctuated_word") or word.get("word") or ""
        start_ms = int(float(word.get("start", 0)) * 1000)
        end_ms = int(float(word.get("end", 0)) * 1000)
        confidence = word.get("confidence")

        if current and current["speaker"] == speaker:
            current["text"] = f"{current['text']} {token}".strip()
            current["end_ms"] = end_ms
        else:
            if current:
                segments.append(current)
            current = {
                "speaker": speaker, "start_ms": start_ms, "end_ms": end_ms,
                "text": token, "confidence": confidence, "is_final": True,
            }
    if current:
        segments.append(current)
    return segments


async def _deepgram_prerecorded_transcribe(
    audio_bytes: bytes, *, department: str | None, sample_rate: int,
) -> list[dict]:
    if aiohttp is None:
        raise RuntimeError("aiohttp is not installed.")
    if not DEEPGRAM_API_KEY:
        raise RuntimeError("Deepgram is not configured.")

    keyterms = list_keyterms_for_department(department)
    # sample_rate MUST match what the browser's AudioContext actually used to encode the
    # raw linear16 PCM — there's no WAV header to self-describe it, so telling Deepgram
    # the wrong rate here silently mis-decodes the whole recording (previously hardcoded
    # to 16000 regardless of the real rate, typically 44100/48000 from a real browser).
    params = [
        f"model={DEEPGRAM_MODEL}", "diarize=true", "smart_format=true", "punctuate=true",
        "filler_words=true", "encoding=linear16", f"sample_rate={sample_rate}", "channels=1",
    ]
    for term in keyterms:
        params.append(f"keyterm={quote(term)}")
    url = "https://api.deepgram.com/v1/listen?" + "&".join(params)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/octet-stream"},
            data=audio_bytes,
            timeout=aiohttp.ClientTimeout(total=300),
        ) as resp:
            resp.raise_for_status()
            payload = await resp.json()

    return _parse_prerecorded_segments(payload)


def replace_final_transcript(consultation_id: str, segments: list[dict]) -> None:
    """Batch re-transcription replaces live segments rather than duplicating them."""
    with connect_db() as conn:
        try:
            ensure_consult_schema(conn)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM transcript_segments WHERE consultation_id = %s", (consultation_id,))
                for segment in segments:
                    cur.execute(
                        """
                        INSERT INTO transcript_segments
                            (consultation_id, speaker, start_ms, end_ms, text, confidence, is_final)
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                        """,
                        (
                            consultation_id, segment["speaker"], segment["start_ms"], segment["end_ms"],
                            segment["text"], segment.get("confidence"),
                        ),
                    )
                cur.execute(
                    """
                    UPDATE consultations
                    SET status = 'transcript_ready', transcript_source = 'batch',
                        transcript_fallback_error = NULL, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (consultation_id,),
                )
                _audit(cur, "consult_transcript_ready", consultation_id, None, segment_count=len(segments))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


# Confirmed empirically against a real Postgres instance (two raw connections doing a
# manual DELETE+INSERT interleave): a DELETE blocked on another transaction's row lock,
# once that transaction commits, only re-checks the SPECIFIC rows it originally matched
# (Postgres's EvalPlanQual) — it does NOT expand to catch rows the other transaction
# also just inserted. So two concurrent replace_final_transcript() calls for the same
# consultation_id can both survive: the second one's DELETE affects 0 rows (the first
# already removed and committed the old ones), then its INSERT lands alongside the
# first's, producing duplicate segments. run_batch_retranscription can now legitimately
# be scheduled twice for the same consult (see _should_schedule_retranscription's
# docstring for why) — serialize with a per-consultation in-process lock rather than
# relying on the database to do it. Safe only because this app is confirmed
# single-process (see TECH_DEBT.md item 3) — would need a distributed lock otherwise.
_retranscription_locks: dict[str, asyncio.Lock] = {}


def _retranscription_lock(consultation_id: str) -> asyncio.Lock:
    lock = _retranscription_locks.get(consultation_id)
    if lock is None:
        lock = asyncio.Lock()
        _retranscription_locks[consultation_id] = lock
    return lock


async def run_batch_retranscription(consultation_id: str) -> None:
    """Downloads the stored audio, re-transcribes it via Deepgram's prerecorded API, and
    replaces the live segments with the higher-accuracy final ones. Falls back to keeping
    the live ('is_final=false') segments as the final transcript if anything about this
    pass fails, rather than leaving the consult stuck in 'transcribing' forever.

    Serialized per consultation_id (see _retranscription_lock above) — a second,
    concurrent call for the same consult waits for the first to finish rather than
    racing it, so its (possibly redundant, but always safe) run just cleanly replaces
    whatever the first one wrote."""
    async with _retranscription_lock(consultation_id):
        await _run_batch_retranscription_locked(consultation_id)


async def _run_batch_retranscription_locked(consultation_id: str) -> None:
    """Everything from function entry is now inside the same try/except (previously the
    initial DB reads — fetching audio_blob_path/audio_sample_rate/department — sat
    outside it). This function runs fire-and-forget via asyncio.create_task, never
    awaited by its caller, so an exception in that earlier window used to propagate
    uncaught, get silently dropped by asyncio's default handler, and leave the consult
    stuck at 'ended' forever with nothing watching for it (the stale-recording sweep only
    watches 'recording'). reached_terminal_state tracks whether we actually know the
    consult reached transcript_ready before broadcasting that it did — if even the
    fallback UPDATE can't be persisted (e.g. the database itself is unreachable), that is
    a genuinely unrecoverable, accepted limitation shared with the rest of this codebase,
    and this at least logs it loudly instead of pretending otherwise. See also
    retry_stuck_transcriptions(), the periodic-sweep-side safety net for this same
    narrow window."""
    from app.services.audio_storage import download_audio

    reached_terminal_state = False
    try:
        with connect_db() as conn:
            ensure_consult_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT audio_blob_path, audio_sample_rate, doctor_id FROM consultations WHERE id = %s",
                    (consultation_id,),
                )
                row = cur.fetchone()
        if not row:
            return
        audio_blob_path, audio_sample_rate, doctor_id = row

        with connect_db() as conn:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT department FROM doctors WHERE doctor_id = %s", (doctor_id,))
                doctor_row = cur.fetchone()
        department = doctor_row[0] if doctor_row else None

        set_status(consultation_id, "transcribing")

        if not audio_blob_path:
            raise RuntimeError("No audio was recorded for this consult.")
        if not audio_sample_rate:
            # Must not guess (e.g. defaulting to 16000) — feeding Deepgram the wrong
            # sample rate for headerless raw PCM silently mis-decodes the whole
            # recording rather than failing loudly, which is exactly what caused batch
            # re-transcription to previously produce empty/garbage results unnoticed.
            raise RuntimeError("No audio sample rate was recorded for this consult; cannot safely decode the audio.")
        audio_bytes = await download_audio(audio_blob_path)
        segments = await _deepgram_prerecorded_transcribe(
            audio_bytes, department=department, sample_rate=audio_sample_rate,
        )
        if not segments:
            raise RuntimeError("Batch re-transcription returned no segments.")
        replace_final_transcript(consultation_id, segments)
        reached_terminal_state = True
    except Exception as exc:
        logger.error("consult %s: batch re-transcription failed, keeping live segments: %s", consultation_id, exc)
        try:
            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE consultations
                        SET status = 'transcript_ready', transcript_source = 'live_fallback',
                            transcript_fallback_error = %s, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (str(exc), consultation_id),
                    )
                    _audit(cur, "consult_transcript_fallback_to_live", consultation_id, None, error=str(exc))
                conn.commit()
            reached_terminal_state = True
        except Exception as inner_exc:
            logger.error(
                "consult %s: could not even persist the live_fallback state after batch "
                "re-transcription failed — consult may be stuck at its prior status: %s",
                consultation_id, inner_exc,
            )

    if reached_terminal_state:
        try:
            from app.api.main import connection_manager
            await connection_manager.broadcast(consultation_id, {"status": "transcript_ready", "consultation_id": consultation_id})
        except Exception as exc:
            logger.warning("consult %s: could not push transcript_ready notification: %s", consultation_id, exc)


CONSULT_MAX_TRANSCRIBING_HOURS = float(os.getenv("CONSULT_MAX_TRANSCRIBING_HOURS", "1"))


async def retry_stuck_transcriptions() -> int:
    """Safety net for the narrow window _run_batch_retranscription_locked's own
    try/except now covers, but only once a run actually starts: if a run never got
    scheduled at all, or died before entering that try (extremely rare — process crash
    between end_consult() and the task actually running), nothing else watches for it.
    Retries run_batch_retranscription for any consult stuck in 'ended' or 'transcribing'
    past CONSULT_MAX_TRANSCRIBING_HOURS — safe to retry since that function is now
    guaranteed to reach some terminal state on its own as long as the database is
    reachable at retry time."""
    with connect_db() as conn:
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM consultations
                WHERE status IN ('ended', 'transcribing')
                    AND updated_at <= NOW() - (%s * INTERVAL '1 hour')
                """,
                (CONSULT_MAX_TRANSCRIBING_HOURS,),
            )
            stuck = [str(r[0]) for r in cur.fetchall()]

    for consultation_id in stuck:
        logger.warning("consult %s: retrying stuck batch re-transcription", consultation_id)
        await run_batch_retranscription(consultation_id)

    return len(stuck)


async def run_retention_sweep() -> int:
    """Finds consultations past retention_expires_at with audio not yet deleted, deletes
    the blob, and marks audio_deleted_at. Never touches transcript rows."""
    from app.services.audio_storage import delete_audio

    with connect_db() as conn:
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, doctor_id, audio_blob_path
                FROM consultations
                WHERE retention_expires_at IS NOT NULL
                    AND retention_expires_at <= NOW()
                    AND audio_deleted_at IS NULL
                    AND audio_blob_path IS NOT NULL
                """
            )
            candidates = cur.fetchall()

    deleted_count = 0
    for consultation_id, doctor_id, audio_blob_path in candidates:
        try:
            await delete_audio(audio_blob_path)
        except Exception as exc:
            logger.error("retention sweep: could not delete audio %s for consult %s: %s", audio_blob_path, consultation_id, exc)
            continue

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE consultations SET audio_deleted_at = NOW(), updated_at = NOW() WHERE id = %s",
                    (str(consultation_id),),
                )
                _audit(cur, "consult_audio_auto_deleted", str(consultation_id), str(doctor_id), blob_path=audio_blob_path)
            conn.commit()
        deleted_count += 1

    return deleted_count
