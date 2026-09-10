from __future__ import annotations

import asyncio
import json
import logging
import os
import time

import websockets
from fastapi import APIRouter, Depends, HTTPException, WebSocket
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from websockets.exceptions import ConnectionClosed

from app.api.dependencies import get_current_doctor
from app.services.audio_storage import finalize_recording, open_recording_tempfile
from app.services.consults import (
    CONSULT_MAX_RECORDING_HOURS,
    DEEPGRAM_API_KEY,
    append_transcript_segment,
    begin_recording,
    build_deepgram_streaming_url,
    correct_segment_speaker,
    discard_consult,
    end_consult,
    get_consult_owned,
    get_transcript,
    list_keyterms_for_department,
    parse_deepgram_streaming_result,
    record_consent,
    run_batch_retranscription,
    set_audio_blob_path,
    start_consult,
    swap_all_speakers,
)
from app.services.doctor_auth import get_doctor_profile
from app.services.soap_notes import (
    add_addendum,
    generate_soap_note,
    get_soap_note,
    sign_soap_note,
    update_soap_note,
)
from app.services.tokens import verify_access_token

logger = logging.getLogger(__name__)

router = APIRouter()

# Sanity ceiling on a single recording, independent of elapsed time — bounds worst-case
# disk/memory usage from an abnormally-high-bitrate or malicious stream. 2GB comfortably
# exceeds a legitimate CONSULT_MAX_RECORDING_HOURS=4 recording at typical browser rates
# (48kHz/16-bit mono ≈ 1.4GB for 4 hours) while still being a real bound, not unbounded
# (FULL_SYSTEM_AUDIT.md P1 #9 — previously only a periodic background sweep enforced any
# limit at all, and it doesn't close the live socket).
CONSULT_MAX_RECORDING_BYTES = int(os.getenv("CONSULT_MAX_RECORDING_BYTES", str(2 * 1024 * 1024 * 1024)))

# Deepgram only flushes its final Results message for already-sent audio after it
# receives the closing empty-bytes frame that relay_audio() sends on stop — cancelling
# relay_results() the instant relay_audio() returns (the old behavior) cut that message
# off on every normal stop, silently dropping the last transcript segment. This bounds
# how long we wait for Deepgram to flush before giving up.
RESULTS_DRAIN_TIMEOUT_SECONDS = float(os.getenv("CONSULT_RESULTS_DRAIN_TIMEOUT_SECONDS", "5"))


class StartConsultRequest(BaseModel):
    booking_id: str


class SegmentCorrectionRequest(BaseModel):
    speaker: str


class SoapNoteUpdateRequest(BaseModel):
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None


class AddendumRequest(BaseModel):
    content: str


def _error(exc: Exception, status: int = 400):
    raise HTTPException(status_code=status, detail=str(exc))


def _should_schedule_retranscription(end_result_status: str, storage_ref: str | None) -> bool:
    """Schedule whenever end_consult() just performed the '...' -> 'ended' transition,
    OR real audio just became available in this call (storage_ref truthy) even if the
    consult was already ended/transcript_ready by someone else first — e.g. a doctor
    manually recovering an "orphaned" session, or the stale-recording sweep, both of
    which can mark a consult done before a genuinely-still-hung WS handler ever reaches
    its own finally block with the real recording. Without the storage_ref branch, that
    real audio would sit in storage unprocessed forever, and the transcript would stay
    stuck at whatever live-only fallback ran earlier. Shared by end_consult_route and
    consult_audio_ws's finally block so both follow the identical rule."""
    return end_result_status == "ended" or bool(storage_ref)


def _parse_sample_rate(raw: str | None) -> int | None:
    """Sanity range only (8kHz telephone-quality through 192kHz professional audio
    comfortably brackets any real browser AudioContext.sampleRate) — rejects obvious
    garbage/spoofed values. This is NOT a real cross-check against the audio itself: it
    cannot detect a plausible-but-wrong rate (e.g. the client claims 16000 while actually
    encoding at 48000) — there is no server-side way to verify that without decoding and
    heuristically analyzing the audio, which this does not attempt. The rate is
    otherwise trusted entirely from the client."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if not (8000 <= value <= 192000):
        return None
    return value


@router.post("/start")
def start_consult_route(request: StartConsultRequest, doctor: dict = Depends(get_current_doctor)):
    try:
        consult = start_consult(doctor_id=doctor["doctor_id"], booking_id=request.booking_id)
    except ValueError as exc:
        _error(exc, 404)
    except PermissionError as exc:
        _error(exc, 409)
    return consult


@router.post("/{consultation_id}/consent")
def consent_route(consultation_id: str, doctor: dict = Depends(get_current_doctor)):
    try:
        consult = record_consent(consultation_id, doctor["doctor_id"], account_id=doctor["account_id"])
    except ValueError as exc:
        _error(exc, 404 if "not found" in str(exc).lower() else 400)
    return consult


@router.post("/{consultation_id}/end")
async def end_consult_route(consultation_id: str, doctor: dict = Depends(get_current_doctor)):
    try:
        consult = end_consult(consultation_id, doctor["doctor_id"])
    except ValueError as exc:
        _error(exc, 404)
    if _should_schedule_retranscription(consult["status"], storage_ref=None):
        asyncio.create_task(run_batch_retranscription(consultation_id))
    return consult


@router.post("/{consultation_id}/discard")
async def discard_consult_route(consultation_id: str, doctor: dict = Depends(get_current_doctor)):
    try:
        result = discard_consult(consultation_id, doctor["doctor_id"])
    except ValueError as exc:
        _error(exc, 404)
    if result["audio_blob_path"]:
        from app.services.audio_storage import delete_audio
        try:
            await delete_audio(result["audio_blob_path"])
        except Exception as exc:
            logger.warning("consult %s: discard could not delete audio %s: %s", consultation_id, result["audio_blob_path"], exc)
    return result["row"]


@router.get("/{consultation_id}/transcript")
def transcript_route(consultation_id: str, doctor: dict = Depends(get_current_doctor)):
    transcript = get_transcript(consultation_id, doctor["doctor_id"])
    if not transcript:
        raise HTTPException(status_code=404, detail="Consult not found.")
    return transcript


@router.post("/{consultation_id}/transcript/swap-speakers")
def swap_speakers_route(consultation_id: str, doctor: dict = Depends(get_current_doctor)):
    try:
        result = swap_all_speakers(consultation_id, doctor["doctor_id"])
    except ValueError as exc:
        _error(exc, 404)
    except PermissionError as exc:
        _error(exc, 409)
    return result


@router.patch("/{consultation_id}/transcript/segments/{segment_id}")
def correct_segment_route(
    consultation_id: str, segment_id: str, request: SegmentCorrectionRequest,
    doctor: dict = Depends(get_current_doctor),
):
    try:
        result = correct_segment_speaker(consultation_id, doctor["doctor_id"], segment_id, request.speaker)
    except ValueError as exc:
        _error(exc, 404 if "not found" in str(exc).lower() else 400)
    except PermissionError as exc:
        _error(exc, 409)
    return result


@router.post("/{consultation_id}/soap/generate")
async def generate_soap_note_route(consultation_id: str, doctor: dict = Depends(get_current_doctor)):
    try:
        note = await generate_soap_note(consultation_id, doctor["doctor_id"])
    except ValueError as exc:
        _error(exc, 404 if "consult not found" in str(exc).lower() else 400)
    except PermissionError as exc:
        _error(exc, 409)
    except RuntimeError as exc:
        _error(exc, 502)
    return note


@router.get("/{consultation_id}/soap")
def get_soap_note_route(consultation_id: str, doctor: dict = Depends(get_current_doctor)):
    note = get_soap_note(consultation_id, doctor["doctor_id"])
    if not note:
        raise HTTPException(status_code=404, detail="No clinical note found for this consult.")
    return note


@router.patch("/{consultation_id}/soap")
def update_soap_note_route(
    consultation_id: str, request: SoapNoteUpdateRequest, doctor: dict = Depends(get_current_doctor),
):
    try:
        note = update_soap_note(consultation_id, doctor["doctor_id"], request.model_dump())
    except ValueError as exc:
        _error(exc, 404 if "not found" in str(exc).lower() or "no clinical note" in str(exc).lower() else 400)
    except PermissionError as exc:
        _error(exc, 409)
    return note


@router.post("/{consultation_id}/soap/sign")
def sign_soap_note_route(consultation_id: str, doctor: dict = Depends(get_current_doctor)):
    try:
        note = sign_soap_note(consultation_id, doctor["doctor_id"])
    except ValueError as exc:
        _error(exc, 404)
    except PermissionError as exc:
        _error(exc, 409)
    return note


@router.post("/{consultation_id}/soap/addendum")
def add_addendum_route(
    consultation_id: str, request: AddendumRequest, doctor: dict = Depends(get_current_doctor),
):
    try:
        note = add_addendum(consultation_id, doctor["doctor_id"], request.content)
    except ValueError as exc:
        _error(exc, 404 if "not found" in str(exc).lower() or "no clinical note" in str(exc).lower() else 400)
    except PermissionError as exc:
        _error(exc, 409)
    return note


def _authenticate_doctor_from_token(token: str | None) -> dict | None:
    """Mirrors get_current_doctor's exact checks — cannot use Depends() on a WebSocket
    route the way HTTP routes do, so the same validation is replicated manually here,
    against a query-param token instead of an Authorization header (same approach as
    the existing /chat/deepgram WebSocket route)."""
    if not token:
        return None
    payload = verify_access_token(token)
    if (
        not payload
        or payload.get("role") != "doctor"
        or payload.get("token_kind") != "doctor_session"
        or payload.get("sub") != payload.get("doctor_id")
    ):
        return None
    return get_doctor_profile(str(payload["doctor_id"]), str(payload.get("account_id") or ""))


@router.websocket("/{consultation_id}/audio")
async def consult_audio_ws(websocket: WebSocket, consultation_id: str):
    token = websocket.query_params.get("token")
    sample_rate = websocket.query_params.get("sample_rate") or "16000"
    await websocket.accept()

    doctor = _authenticate_doctor_from_token(token)
    if not doctor:
        await websocket.send_json({"type": "error", "message": "Doctor authentication is required."})
        await websocket.close(code=1008)
        return

    consult = get_consult_owned(consultation_id, doctor["doctor_id"])
    if not consult:
        await websocket.send_json({"type": "error", "message": "Consult not found."})
        await websocket.close(code=1008)
        return

    if consult["status"] != "consented":
        await websocket.send_json({"type": "error", "message": "Recording requires a consented consult."})
        await websocket.close(code=1008)
        return

    if not DEEPGRAM_API_KEY:
        await websocket.send_json({"type": "error", "message": "Deepgram is not configured."})
        await websocket.close(code=1011)
        return

    sample_rate_int = _parse_sample_rate(sample_rate)
    if sample_rate_int is None:
        await websocket.send_json({"type": "error", "message": "Invalid sample_rate."})
        await websocket.close(code=1008)
        return

    # The REAL rate the browser's AudioContext used — persisted so the batch
    # re-transcription pass can later tell Deepgram's prerecorded API the true rate
    # instead of guessing (see begin_recording's docstring for why that guess was wrong).
    begin_recording(consultation_id, doctor["doctor_id"], sample_rate=sample_rate_int)
    keyterms = list_keyterms_for_department(doctor.get("department"))
    deepgram_url = build_deepgram_streaming_url(sample_rate=sample_rate, keyterms=keyterms)

    # Audio is written incrementally to a local temp file as it arrives — never
    # buffered fully in memory. finalize_recording() hands it to whichever storage
    # backend is active (local: move into place; azure: upload then discard) once,
    # at session end.
    temp_handle, temp_path = open_recording_tempfile()

    recording_started_at = time.monotonic()
    max_recording_seconds = CONSULT_MAX_RECORDING_HOURS * 3600
    bytes_written = 0

    try:
        async with websockets.connect(
            deepgram_url,
            additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
        ) as deepgram_ws:

            async def relay_audio() -> None:
                nonlocal bytes_written
                while True:
                    message = await websocket.receive()
                    if message.get("type") == "websocket.disconnect":
                        try:
                            await deepgram_ws.send(b"")
                        except Exception:
                            pass
                        break
                    if message.get("bytes") is not None:
                        data = message["bytes"]
                        if data == b"":
                            await deepgram_ws.send(b"")
                            break
                        temp_handle.write(data)
                        bytes_written += len(data)
                        await deepgram_ws.send(data)
                        # Stop the recording (not the whole consult) once either limit is
                        # hit — whatever was captured so far still finalizes normally in
                        # the `finally` block below, it just doesn't grow any further.
                        elapsed = time.monotonic() - recording_started_at
                        if bytes_written >= CONSULT_MAX_RECORDING_BYTES or elapsed >= max_recording_seconds:
                            logger.warning(
                                "consult %s: recording stopped at limit (bytes=%d, elapsed=%.0fs)",
                                consultation_id, bytes_written, elapsed,
                            )
                            try:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Recording reached the maximum allowed size or duration and was stopped.",
                                })
                            except Exception:
                                pass
                            await deepgram_ws.send(b"")
                            break
                    elif message.get("text") == "__stop__":
                        await deepgram_ws.send(b"")
                        break

            async def relay_results() -> None:
                async for payload in deepgram_ws:
                    if isinstance(payload, bytes):
                        await websocket.send_bytes(payload)
                        continue
                    await websocket.send_text(payload)
                    try:
                        data = json.loads(payload)
                    except (TypeError, ValueError):
                        continue
                    segment = parse_deepgram_streaming_result(data)
                    if segment:
                        append_transcript_segment(consultation_id, **segment)

            audio_task = asyncio.create_task(relay_audio())
            results_task = asyncio.create_task(relay_results())
            done, pending = await asyncio.wait(
                {audio_task, results_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if pending == {results_task}:
                # relay_audio() finished because it already sent Deepgram the closing
                # frame (normal stop/disconnect/limit) — give Deepgram a moment to send
                # its last Results message instead of cancelling the listener out from
                # under it and losing the final transcript segment.
                done2, pending = await asyncio.wait(
                    {results_task}, timeout=RESULTS_DRAIN_TIMEOUT_SECONDS
                )
                done |= done2
            for task in pending:
                task.cancel()
            for task in done:
                task.result()
    except ConnectionClosed:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        # Close before finalizing — a still-open file handle can't be moved/renamed on
        # Windows (the local backend's "upload" step), and there's no reason to hold it
        # open for the azure backend either.
        try:
            temp_handle.close()
        except Exception:
            pass

        storage_ref = None
        try:
            storage_ref = await finalize_recording(
                temp_path, doctor_id=doctor["doctor_id"], consultation_id=consultation_id
            )
            if storage_ref:
                set_audio_blob_path(consultation_id, storage_ref)
        except Exception as exc:
            logger.error("consult %s: could not finalize recorded audio: %s", consultation_id, exc)

        result = end_consult(consultation_id, doctor["doctor_id"])
        if _should_schedule_retranscription(result["status"], storage_ref):
            asyncio.create_task(run_batch_retranscription(consultation_id))

        try:
            await websocket.close()
        except Exception:
            pass
