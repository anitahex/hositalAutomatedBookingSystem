from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import websockets
from websockets.exceptions import ConnectionClosed

from app.api.dependencies import current_user
from app.agents.document_followup import AWAITING_DOCUMENT_FOLLOW_UP
from app.agents.graph import arun_patient_chat, initialise_hybrid_memory, run_patient_chat
from app.agents.intake_utils import CRISIS_SAFETY_RESPONSE, looks_like_crisis_or_harm
from app.services.appointments import upcoming_bookings_for_patient
from app.services.language import apply_language_turn
from app.services.tokens import verify_access_token
from app.services.document_pipeline import (
    ALLOWED_UPLOAD_MIME_TYPES,
    _extract_pdf_text,
    extract_pdf_pages,
    extract_uploaded_document,
)
from app.services.blob_storage import (
    delete_blob,
    move_blob,
    staging_blob_path,
    upload_blob,
    upload_json_blob,
    vault_blob_path,
    summary_blob_path,
)
from app.services.document_catalog import (
    PAGE_SOURCE_PDF_TEXT,
    PAGE_SOURCE_VISION,
    consume_pending_upload,
    create_catalog_row,
    get_catalog_entry,
    mark_catalog_failed,
    list_user_documents,
    save_document_pages,
    save_pending_upload,
    update_catalog_after_extraction,
)

logger = logging.getLogger(__name__)

# Backward-compatible alias for tests and any existing monkeypatches.
active_bookings_for_patient = upcoming_bookings_for_patient

# Server-side cache for extracted file data from /chat/upload.
# Keyed by (user_id, session_id). Consumed on the next /chat/stream call for that
# session. Bypasses LangGraph checkpoint merging which silently drops large base64
# payloads. Session-scoped so an upload in one browser tab never gets injected into
# a different concurrent tab/session for the same patient.
_doc_analysis_cache: dict[str, list[dict]] = {}


def _doc_cache_key(user_id: str, session_id: str | None) -> str:
    return f"{user_id}:{session_id or ''}"


# Documents one message can carry. Each is analysed in full, one after another, so a bound
# keeps the reply to something a patient will read and the stream inside its timeout.
MAX_DOCUMENTS_PER_MESSAGE = 3


def _discard_cached_document(user_id: str, session_id: str | None, document_token: str) -> None:
    """Removes ONE staged document from the session's queue and leaves the others.

    Declining used to drop the whole queue, so declining a second file silently threw
    away a first file the patient had just agreed to.
    """
    key = _doc_cache_key(user_id, session_id)
    kept = [e for e in _doc_analysis_cache.get(key, []) if e.get("document_token") != document_token]
    if kept:
        _doc_analysis_cache[key] = kept
    else:
        _doc_analysis_cache.pop(key, None)


def _mark_cached_document_consented(user_id: str, session_id: str | None, document_token: str) -> None:
    for entry in _doc_analysis_cache.get(_doc_cache_key(user_id, session_id), []):
        if entry.get("document_token") == document_token:
            entry["consented"] = True


def _take_consented_documents(key: str) -> list[dict]:
    """Removes and returns the queued documents the patient consented to, in upload order.

    Consent is asked when the message is sent, so a file can wait in the queue without it;
    that file stays queued and is never analysed until the patient agrees.
    """
    queued = _doc_analysis_cache.get(key, [])
    taken = [e for e in queued if e.get("consented")]
    waiting = [e for e in queued if not e.get("consented")]
    if waiting:
        _doc_analysis_cache[key] = waiting
    else:
        _doc_analysis_cache.pop(key, None)
    return taken

from app.services.chat_history import (
    append_chat_messages,
    load_chat_history_with_timestamps,
    load_chat_sessions_with_messages,
    load_chat_session_history,
    load_recent_chat_history,
)
from app.services.llm_usage import (
    collect_llm_usage,
    ensure_chat_session_id,
    load_chat_session_memory,
    persist_chat_session_memory,
    persist_llm_usage_records,
    summarize_usage,
)

router = APIRouter()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
DEEPGRAM_MODEL = os.getenv("DEEPGRAM_MODEL", "nova-3-medical")

SAFETY_DISCLAIMER = (
    "This information is provided for reference only. "
    "Always verify medical details with a licensed healthcare practitioner "
    "before making any health or treatment decisions."
)


def _merge_booking_lists(existing: list[dict] | None, incoming: list[dict] | None) -> list[dict]:
    merged: list[dict] = []
    seen: set[tuple[str | None, str | None]] = set()
    for item in list(existing or []) + list(incoming or []):
        if not isinstance(item, dict):
            continue
        key = (str(item.get("booking_id") or "") or None, str(item.get("slot_id") or "") or None)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


class ChatRequest(BaseModel):
    message: str
    patient_id: str | None = None
    state: dict | None = None


class ConfirmProcessingRequest(BaseModel):
    document_token: str
    consent_granted: bool


def _safe_json_loads(value: str | None) -> dict | None:
    if not value:
        return None
    try:
        loaded = json.loads(value)
    except Exception:
        return None
    return loaded if isinstance(loaded, dict) else None


def _normalize_session_id(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except Exception:
        return str(uuid.uuid4())


def _current_user_payload_from_token(token: str | None) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token is required.")
    payload = verify_access_token(token)
    if not payload or payload.get("role") not in (None, "patient"):
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")
    return payload


def _prepare_uploaded_file(upload: UploadFile) -> dict[str, object]:
    extracted = extract_uploaded_document(upload)
    return {
        "pending_file_data": extracted,
        "pending_file_name": extracted.get("file_name") or upload.filename or "uploaded-file",
        "pending_file_mime_type": extracted.get("mime_type") or upload.content_type or "application/octet-stream",
    }


def _prepare_chat_state(payload: dict, user: dict):
    state = dict(payload.get("state") or {})
    patient_id = user["patient_id"]
    state["patient_profile"] = user
    state["session_id"] = _normalize_session_id(
        payload.get("session_id") or state.get("session_id") or state.get("chat_session_id")
    )
    ensure_chat_session_id(state)
    if state.get("session_id"):
        state["chat_session_id"] = state["session_id"]
    else:
        state["session_id"] = state.get("chat_session_id")

    if patient_id and "conversation_history" not in state and "recent_history" not in state:
        try:
            session_id = state.get("chat_session_id")
            if session_id:
                state["conversation_history"] = load_chat_session_history(patient_id, session_id)
            else:
                state["recent_history"] = load_recent_chat_history(patient_id)
        except Exception as exc:
            logger.warning("Could not load chat history for %s: %s", patient_id, exc)

    if patient_id and not state.get("chat_summary") and state.get("chat_session_id"):
        try:
            state["chat_summary"] = load_chat_session_memory(
                patient_id=patient_id,
                chat_session_id=state.get("chat_session_id"),
            )
        except Exception as exc:
            logger.warning("Could not load chat summary for %s: %s", patient_id, exc)

    if patient_id:
        try:
            # Always use the DB as the authoritative source for appointments.
            # Never merge with client-sent state — that would leak bookings
            # from a previous user's session if the same browser logs in as
            # a different account without a full page reload.
            appointments = upcoming_bookings_for_patient(patient_id, limit=5)
            state["active_appointments"] = appointments
            state["upcoming_bookings"] = appointments
            state["confirmed_bookings"] = appointments
            if appointments:
                state["confirmed_booking"] = appointments[-1]
        except Exception as exc:
            logger.warning("Could not load active appointments for %s: %s", patient_id, exc)

    state = initialise_hybrid_memory(state)
    return state, patient_id


def _append_user_message_to_state(state: dict, message: str) -> dict:
    text = str(message or "").strip()
    if not text:
        return state

    updated = dict(state)
    user_turn = {"role": "patient", "text": text}

    conversation_history = updated.get("conversation_history")
    if isinstance(conversation_history, list) and conversation_history:
        if conversation_history[-1] != user_turn:
            conversation_history = [*conversation_history, user_turn]
        updated["conversation_history"] = conversation_history
        updated["recent_history"] = conversation_history[-6:]
    else:
        recent_history = list(updated.get("recent_history") or [])
        if not recent_history or recent_history[-1] != user_turn:
            recent_history.append(user_turn)
        updated["recent_history"] = recent_history[-6:]

    messages = list(updated.get("messages") or [])
    if not messages or messages[-1] != user_turn:
        messages.append(user_turn)
    updated["messages"] = messages[-6:]
    return updated


async def _run_chat_with_usage(payload: dict, user: dict):
    state, patient_id = _prepare_chat_state(payload, user)

    # Inject cached file data from the most recent /chat/upload for this session.
    # The cache is populated in upload_document() and consumed here exactly once.
    user_id_str = str(patient_id or "")
    cache_key = _doc_cache_key(user_id_str, state.get("chat_session_id"))
    if user_id_str and cache_key in _doc_analysis_cache:
        pending_files = _take_consented_documents(cache_key)
        if pending_files:
            first = pending_files[0]
            # Always use the server-side cache — it contains full extracted images
            # from /chat/upload. Never blocked by FormData-injected state.
            state["pending_file_data"] = first
            state["pending_file_name"] = first.get("file_name", "uploaded-file")
            state["pending_file_mime_type"] = first.get("mime_type", "application/octet-stream")
            state["pending_files_data"] = pending_files
            state.setdefault(
                "file_clarification_context",
                "The patient uploaded a medical file and wants help interpreting it.",
            )
            logger.info(
                "run_chat: injected %d cached file(s) for user=%s files=%s",
                len(pending_files), user_id_str,
                [f.get("file_name") for f in pending_files],
            )

    message = payload["message"]
    state = _append_user_message_to_state(state, message)

    with collect_llm_usage() as usage_records:
        result = await arun_patient_chat(
            user_input=message,
            patient_id=patient_id,
            state=state,
        )

    response_text = (
        result.get("final_response")
        or "I'm still processing your information, could you tell me a bit more?"
    )
    result["session_id"] = state["session_id"]
    result["chat_session_id"] = state["chat_session_id"]

    if patient_id:
        try:
            append_chat_messages(
                patient_id,
                [
                    {"role": "patient", "text": message},
                    {"role": "assistant", "text": response_text},
                ],
                chat_session_id=state["chat_session_id"],
            )
        except Exception as exc:
            logger.warning("Could not save chat history for %s: %s", patient_id, exc)

        try:
            usage_summary = persist_llm_usage_records(
                patient_id=patient_id,
                chat_session_id=state["chat_session_id"],
                records=usage_records,
            )
        except Exception as exc:
            logger.warning("Could not save LLM token usage for %s: %s", patient_id, exc)
            usage_summary = summarize_usage(usage_records)

        try:
            persist_chat_session_memory(
                patient_id=patient_id,
                chat_session_id=state["chat_session_id"],
                chat_summary=result.get("chat_summary") or state.get("chat_summary") or "",
            )
        except Exception as exc:
            logger.warning("Could not save chat summary for %s: %s", patient_id, exc)
    else:
        usage_summary = summarize_usage(usage_records)

    result["token_usage"] = usage_summary
    return response_text, result, usage_summary


@router.websocket("/deepgram")
async def deepgram_bridge(websocket: WebSocket):
    token = websocket.query_params.get("token")
    sample_rate = websocket.query_params.get("sample_rate") or "16000"
    await websocket.accept()
    payload = verify_access_token(token) if token else None
    if not payload or payload.get("role") not in (None, "patient"):
        await websocket.send_json({"type": "error", "message": "Invalid or expired authentication token."})
        await websocket.close(code=1008)
        return

    if not DEEPGRAM_API_KEY:
        await websocket.send_json({"type": "error", "message": "Deepgram is not configured."})
        await websocket.close(code=1011)
        return

    deepgram_url = (
        "wss://api.deepgram.com/v1/listen"
        f"?model={DEEPGRAM_MODEL}"
        "&encoding=linear16"
        f"&sample_rate={sample_rate}"
        "&channels=1"
        "&interim_results=true"
        "&smart_format=true"
        "&punctuate=true"
    )

    try:
        async with websockets.connect(
            deepgram_url,
            additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
        ) as deepgram_ws:

            async def relay_audio() -> None:
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
                        await deepgram_ws.send(data)
                    elif message.get("text") == "__stop__":
                        await deepgram_ws.send(b"")
                        break

            async def relay_results() -> None:
                async for payload in deepgram_ws:
                    if isinstance(payload, bytes):
                        await websocket.send_bytes(payload)
                    else:
                        await websocket.send_text(payload)

            audio_task = asyncio.create_task(relay_audio())
            results_task = asyncio.create_task(relay_results())
            done, pending = await asyncio.wait(
                {audio_task, results_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
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
        try:
            await websocket.close()
        except Exception:
            pass


def _text_tokens(text: str):
    for match in re.finditer(r"\S+\s*", text or ""):
        yield match.group(0)


# Content keywords, used only when the analysis did not name a specialist itself.
#
# Pathology, Radiology, Gynecology and Urology were here and have been removed: none is a
# department in this hospital, so each resolved to zero bookable doctors, and the first two
# are the services that PRODUCED the document rather than ones that treat the patient. A
# blood report matched "Pathology" on the word "cbc" — which is where the document came
# from, not where the patient should go.
_CONTENT_DEPT_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Orthopedics",      ["ortho", "spine", "lumbar", "fracture", "bone", "lba", "vertebra"]),
    ("Cardiology",       ["cardio", "heart", "ecg", "hypertension", "coronary"]),
    ("Neurology",        ["neuro", "brain", "nerve", "epilepsy", "stroke"]),
    ("Endocrinology",    ["diabetes", "thyroid", "hba1c", "insulin"]),
    ("Pulmonology",      ["lung", "asthma", "copd", "respiratory"]),
    ("Gastroenterology", ["gastro", "liver", "bowel", "hepatitis"]),
    ("Nephrology",       ["kidney", "renal", "creatinine", "dialysis"]),
    ("Oncology",         ["cancer", "tumor", "malignant", "biopsy"]),
    ("Dermatology",      ["skin", "rash", "eczema", "derma"]),
    ("Psychiatry",       ["anxiety", "depression", "insomnia", "psychiatric", "mental health"]),
    ("Hematology",       ["anaemia", "anemia", "leukemia", "clotting", "haemophilia"]),
]


def _extract_labelled_line(text: str, label: str) -> str | None:
    """Pulls a '- **Label:** value' line out of the generated analysis.

    The streaming prompt now asks for Referred By and Clinical History on every document
    type, which is how this path sees a referral at all — it never calls the structured
    extractor (that runs later, in the background ingestion pipeline). "Not stated" is
    the prompt's own placeholder for absent and is treated as absent.
    """
    match = re.search(
        rf"\*\*{re.escape(label)}:\*\*\s*(.+)",
        text or "",
        re.IGNORECASE,
    )
    if not match:
        return None
    value = match.group(1).strip().strip("*").strip()
    if not value or value.lower().lstrip("[").rstrip("]").strip() in {
        "not stated", "none", "n/a", "na", "unknown",
    }:
        return None
    return value[:200]


def _referring_department_from_text(text: str) -> str | None:
    """The department named in a 'Referred By' line, if it names one.

    "Dr. Sunita Panday, Psychiatry" -> Psychiatry. A name with no specialty yields None
    rather than a guess — inferring a department from a doctor's name is exactly the kind
    of invention this work exists to stop.
    """
    from app.services.appointments import match_department, routable_departments

    referred_by = _extract_labelled_line(text, "Referred By")
    if not referred_by:
        return None
    return match_department(referred_by, routable_departments())


def _extract_dept_from_text(text: str) -> str:
    """The department a patient should be offered after a document analysis.

    Whatever the model named is UNTRUSTED and re-checked against the departments this
    hospital actually staffs — the analysis prompt is free text, so "Pathology",
    "Radiology" or a specialty we do not have could otherwise be written straight into
    state as a bookable department.

    Always returns a real department, falling back to General Physician. The return type
    stays `str` so the single call site is unchanged; deciding to ASK instead of defaulting
    belongs to the resolver, in the slice that removes the forced booking intent.
    """
    from app.services.appointments import match_department, routable_departments

    routable = routable_departments()

    match = re.search(
        r"###\s*Recommended Specialist\s*\n+\*{0,2}([A-Za-z /\-]+?)\*{0,2}\s*\n",
        text, re.IGNORECASE,
    )
    if match:
        named = match_department(match.group(1).strip(), routable)
        if named:
            return named
        # The model named something we cannot book. Fall through to the content keywords
        # rather than trusting it.

    lowered = text.lower()
    allowed = set(routable)
    for department, keywords in _CONTENT_DEPT_KEYWORDS:
        if department in allowed and any(keyword in lowered for keyword in keywords):
            return department
    return "General Physician"


def _extract_doctype_from_text(text: str) -> str:
    m = re.search(r"^##\s+(.+?)\s+(?:Summary|Analysis|Report)", text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return "other"
    label = m.group(1).lower()
    for key, val in [
        ("prescription", "prescription"), ("blood", "blood_report"),
        ("mri", "mri_report"), ("ct", "ct_report"),
        ("x-ray", "xray_report"), ("xray", "xray_report"),
        ("discharge", "discharge_summary"), ("pathology", "pathology_report"),
    ]:
        if key in label:
            return val
    return "other"


def _stream_event(event_type: str, **payload) -> str:
    return json.dumps({"type": event_type, **payload}, default=str) + "\n"


@router.post("")
def chat(request: ChatRequest, user: dict = Depends(current_user)):
    payload = {
        "message": request.message,
        "session_id": request.state.get("session_id") if request.state else None,
        "state": request.state,
    }
    response_text, result, usage_summary = asyncio.run(_run_chat_with_usage(payload, user))
    return {
        "response": response_text,
        "language": result.get("active_language") or "en",
        "state": result,
        "safety_disclaimer": SAFETY_DISCLAIMER,
    }


@router.post("/stream")
async def chat_stream(request: Request, user: dict = Depends(current_user)):
    payload, _ = await _parse_chat_request(request)
    user_id_str = str((user or {}).get("patient_id") or "")
    stream_cache_key = _doc_cache_key(
        user_id_str, payload.get("session_id") or (payload.get("state") or {}).get("chat_session_id")
    )

    async def event_stream():
        # ── Fast path: direct GPT-4o streaming for document analysis ──────────
        if user_id_str and stream_cache_key in _doc_analysis_cache:
            # Only documents the patient agreed to store and analyse; any still waiting
            # for that decision stay queued.
            files = _take_consented_documents(stream_cache_key)
            if files:
                from app.agents import document_followup
                from app.inference.azure_client import gpt4o_stream_analysis
                from app.services.appointments import routable_departments

                yield _stream_event("start_response")
                full_text = ""
                # Each document's own analysis. Type, department, referral and findings are
                # read from these one at a time: reading them from the combined text gave
                # every document of a multi-file upload the first one's labels.
                file_texts: list[str] = []

                try:
                    for file_idx, fp in enumerate(files):
                        if file_idx > 0:
                            sep = "\n\n---\n\n"
                            yield _stream_event("token", token=sep)
                            full_text += sep
                        if len(files) > 1:
                            heading = f"**Document {file_idx + 1} of {len(files)} — {fp.get('file_name') or 'document'}**\n\n"
                            yield _stream_event("token", token=heading)
                            full_text += heading

                        mime = fp.get("mime_type", "application/octet-stream")
                        images = fp.get("images") or []
                        extracted = fp.get("text") or ""

                        # Decode first image for GPT-4o vision
                        if mime.startswith("image/") and images:
                            data_url = images[0].get("data_url", "")
                            file_bytes = base64.b64decode(data_url.split(",", 1)[1]) if "," in data_url else b""
                        elif mime == "application/pdf" and images and not extracted:
                            data_url = images[0].get("data_url", "")
                            file_bytes = base64.b64decode(data_url.split(",", 1)[1]) if "," in data_url else b""
                            mime = images[0].get("mime_type", "image/jpeg")
                        else:
                            file_bytes = b""

                        file_texts.append("")
                        async for token in gpt4o_stream_analysis(
                            mime_type=mime,
                            file_bytes=file_bytes,
                            extracted_text=extracted,
                            user_question=payload["message"],
                            # Constrains the visible "Recommended Specialist" to
                            # departments the patient can actually book. The value is
                            # re-validated by _extract_dept_from_text regardless — the
                            # model's output is never trusted on its own.
                            valid_departments=routable_departments(),
                        ):
                            yield _stream_event("token", token=token)
                            full_text += token
                            file_texts[-1] += token

                except Exception as exc:
                    logger.error("event_stream: document streaming failed: %s", exc, exc_info=True)
                    err = "\n\n*Analysis encountered an error — please try again.*"
                    yield _stream_event("token", token=err)
                    full_text += err

                # Build minimal state so frontend can show department / analyzed docs
                state, patient_id = _prepare_chat_state(payload, user)
                state = _append_user_message_to_state(state, payload["message"])
                # A new upload is a new round: its own questions, and a summary rebuilt to
                # cover every document shared so far.
                state.update(document_followup.start_round(state))
                current_round = state["document_followup_round"]
                doc_log = list(state.get("analyzed_documents") or [])
                departments: list[str] = []
                for index, fp in enumerate(files):
                    text = file_texts[index] if index < len(file_texts) else ""
                    dept = _extract_dept_from_text(text)
                    departments.append(dept)
                    # Parsed from the analysis the model just wrote, because the streaming
                    # path never calls the structured extractor. Keeping these means a later
                    # turn can reason about the document instead of re-reading 150 truncated
                    # characters of its own prose.
                    doc_log.append({
                        "file_name": fp.get("file_name") or "document",
                        "document_type": _extract_doctype_from_text(text),
                        "department": dept,
                        "referring_doctor": _extract_labelled_line(text, "Referred By"),
                        "referring_department": _referring_department_from_text(text),
                        "clinical_history": _extract_labelled_line(text, "Clinical History"),
                        "key_findings": document_followup.parse_key_findings(text),
                        "summary": (text[:150] + "…") if len(text) > 150 else text,
                        "followup_round": current_round,
                    })
                # The suggestion is the department most of the documents point to (the
                # first one on a tie). A SUGGESTION: the resolver decides after the questions.
                suggested = max(departments, key=departments.count) if departments else None
                # Uploading a document is not a request to be booked.
                #
                # This used to set active_intent="direct_booking" and a target_department
                # in one assignment, before the patient had said anything — so the
                # department guessed from the model's prose became the patient's own
                # "request", stuck, and could not be talked out of. awaiting was set to
                # "user_input", which no router consumes, so nothing could follow up either.
                #
                # Now: the analysis is offered, the department is remembered as a
                # SUGGESTION, and the first question about the documents comes with it.
                # awaiting is a value the supervisor actually routes.
                state.update({
                    "suggested_department": suggested,
                    "awaiting": AWAITING_DOCUMENT_FOLLOW_UP,
                    "active_intent": "document_review",
                    "intent": "document_review",
                    "analyzed_documents": doc_log,
                })

                # The first question arrives with the analysis, so the patient is not left
                # to type something before the questions begin.
                closing = ""
                if document_followup.wants_to_only_store(payload["message"]):
                    closing = (
                        "\n\n---\n\nSaved to your records. I won't book anything. "
                        "Tell me any time if you'd like to see a doctor about it."
                    )
                    state.update({"awaiting": None, "active_intent": None, "intent": None})
                elif any(t.strip() for t in file_texts):
                    try:
                        choice = await asyncio.to_thread(
                            document_followup.choose_next_question, dict(state), payload["message"]
                        )
                    except Exception as exc:
                        logger.warning("event_stream: first follow-up question failed: %s", exc)
                        choice = {"question": None, "symptoms": []}
                    if choice.get("question"):
                        topic, question = choice["question"]
                        state.update(document_followup.merge_symptoms(state, choice.get("symptoms") or []))
                        state.update(document_followup.register_question(state, topic, question))
                        closing = (
                            "\n\n---\n\n**A few quick questions so I can guide you to the right doctor.**\n\n"
                            f"{question}"
                        )
                if closing:
                    yield _stream_event("token", token=closing)
                    full_text += closing

                history = list(state.get("conversation_history") or [])
                history.append({"role": "assistant", "text": full_text})
                state.update({
                    "final_response": full_text,
                    "conversation_history": history,
                    "messages": history[-6:],
                })

                if patient_id:
                    try:
                        append_chat_messages(
                            patient_id,
                            [
                                {"role": "patient", "text": payload["message"]},
                                {"role": "assistant", "text": full_text},
                            ],
                            chat_session_id=state["chat_session_id"],
                        )
                    except Exception as exc:
                        logger.warning("stream path: could not save chat history: %s", exc)

                usage_summary = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "calls": 1}
                yield _stream_event(
                    "final",
                    response=full_text,
                    state=state,
                    token_usage=usage_summary,
                    safety_disclaimer=SAFETY_DISCLAIMER,
                )
                return

        # ── Conversational streaming paths ────────────────────────────────────
        from app.agents.conversation_agent import (
            conversation_agent_stream,
            finalize_conv_stream_state,
            should_stream_intake,
        )
        from app.agents.triage_router import (
            finalize_triage_stream_state,
            should_do_triage_stream,
            triage_intake_stream,
        )

        # Prepare state once for routing checks (payload state, not full LangGraph)
        stream_state, stream_patient_id = _prepare_chat_state(payload, user)
        language_updates = apply_language_turn(stream_state, payload["message"])
        stream_state.update(language_updates)
        if language_updates.get("language_control_response"):
            response_text = language_updates["language_control_response"]
            history = list(stream_state.get("conversation_history") or [])
            history.append({"role": "assistant", "text": response_text})
            stream_state.update({"conversation_history": history, "messages": history[-6:], "final_response": response_text})
            if stream_patient_id:
                try:
                    append_chat_messages(
                        stream_patient_id,
                        [{"role": "patient", "text": payload["message"]}, {"role": "assistant", "text": response_text}],
                        chat_session_id=stream_state.get("chat_session_id"),
                    )
                except Exception as exc:
                    logger.warning("language switch stream: could not save history: %s", exc)
            yield _stream_event("start_response")
            yield _stream_event("token", token=response_text)
            yield _stream_event("final", response=response_text, language=stream_state.get("active_language") or "en",
                                state=stream_state, token_usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "calls": 0},
                                safety_disclaimer=SAFETY_DISCLAIMER)
            return
        stream_state = _append_user_message_to_state(stream_state, payload["message"])
        # CRITICAL: expose current message as user_input so extraction/prompts work correctly
        stream_state["user_input"] = payload["message"]

        # ── Hard safety gate: self-harm / intent-to-harm-others language ─────
        # Checked before any streaming fast-path or LLM call — a freeform LLM
        # reaction to this kind of input is not reliable, and the no-LLM-routing
        # fast paths below have no way to recognize it at all, which previously
        # left the conversation stuck repeating "tell me what's upsetting you"
        # for several turns regardless of what the patient said next.
        if looks_like_crisis_or_harm(payload["message"]):
            yield _stream_event("start_response")
            yield _stream_event("token", token=CRISIS_SAFETY_RESPONSE)
            history = list(stream_state.get("conversation_history") or [])
            history.append({"role": "assistant", "text": CRISIS_SAFETY_RESPONSE})
            # Deliberately reset awaiting (not left as "conversation") so the very
            # next message is routed fresh instead of being absorbed as an intake answer.
            updated_state = {
                **stream_state,
                "conversation_history": history,
                "messages": history[-6:],
                "awaiting": None,
                "final_response": CRISIS_SAFETY_RESPONSE,
            }
            if stream_patient_id:
                try:
                    append_chat_messages(
                        stream_patient_id,
                        [{"role": "patient", "text": payload["message"]}, {"role": "assistant", "text": CRISIS_SAFETY_RESPONSE}],
                        chat_session_id=updated_state.get("chat_session_id"),
                    )
                except Exception as exc:
                    logger.warning("crisis gate: could not save history: %s", exc)
            yield _stream_event(
                "final",
                response=CRISIS_SAFETY_RESPONSE,
                language=updated_state.get("active_language") or "en",
                state=updated_state,
                token_usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "calls": 0},
                safety_disclaimer=SAFETY_DISCLAIMER,
            )
            return

        awaiting = stream_state.get("awaiting")
        active_intent = stream_state.get("active_intent") or stream_state.get("intent")

        # ── Path A: mid-intake follow-up (0 LLM routing calls) ───────────────
        if awaiting == "conversation" and should_stream_intake(stream_state):
            yield _stream_event("start_response")
            full_text = ""
            try:
                async for token in conversation_agent_stream(stream_state):
                    yield _stream_event("token", token=token)
                    full_text += token
            except Exception as exc:
                logger.error("conv_stream failed: %s", exc, exc_info=True)
                err = "I had trouble generating the next question — could you repeat that?"
                yield _stream_event("token", token=err)
                full_text = err

            updated_state = finalize_conv_stream_state(stream_state, full_text)
            if stream_patient_id:
                try:
                    append_chat_messages(
                        stream_patient_id,
                        [{"role": "patient", "text": payload["message"]}, {"role": "assistant", "text": full_text}],
                        chat_session_id=updated_state.get("chat_session_id"),
                    )
                except Exception as exc:
                    logger.warning("conv_stream: could not save history: %s", exc)
            yield _stream_event(
                "final",
                response=full_text,
                language=updated_state.get("active_language") or "en",
                state=updated_state,
                token_usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "calls": 1},
                safety_disclaimer=SAFETY_DISCLAIMER,
            )
            return

        # ── Path B: new symptom / greeting (merged triage + intake, 1 HF call) ─
        if not awaiting and not active_intent and should_do_triage_stream(payload["message"]):
            triage_updates: dict = {}
            full_text = ""
            yield _stream_event("start_response")
            try:
                async for item in triage_intake_stream(stream_state, payload["message"]):
                    if isinstance(item, dict):
                        triage_updates = item
                    else:
                        yield _stream_event("token", token=item)
                        full_text += item
            except Exception as exc:
                logger.error("triage_stream failed: %s", exc, exc_info=True)
                err = "I am here to help. Could you describe what you are feeling?"
                yield _stream_event("token", token=err)
                full_text = err

            updated_state = finalize_triage_stream_state(stream_state, triage_updates, full_text)
            if stream_patient_id:
                try:
                    append_chat_messages(
                        stream_patient_id,
                        [{"role": "patient", "text": payload["message"]}, {"role": "assistant", "text": full_text}],
                        chat_session_id=updated_state.get("chat_session_id"),
                    )
                except Exception as exc:
                    logger.warning("triage_stream: could not save history: %s", exc)
            yield _stream_event(
                "final",
                response=full_text,
                language=updated_state.get("active_language") or "en",
                state=updated_state,
                token_usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "calls": 1},
                safety_disclaimer=SAFETY_DISCLAIMER,
            )
            return

        # ── Normal path: full LangGraph pipeline (appointments, remedy, booking) ─
        try:
            for token in _text_tokens("Reviewing your request...\n\n"):
                yield _stream_event("status_token", token=token)

            response_text, result, usage_summary = await _run_chat_with_usage(payload, user)
            yield _stream_event("start_response")
            for token in _text_tokens(response_text):
                yield _stream_event("token", token=token)
            yield _stream_event(
                "final",
                response=response_text,
                language=result.get("active_language") or "en",
                state=result,
                token_usage=usage_summary,
                safety_disclaimer=SAFETY_DISCLAIMER,
            )
        except Exception as exc:
            logger.error("event_stream error: %s", exc, exc_info=True)
            yield _stream_event("error", message=str(exc))

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.get("/records")
def patient_records(user: dict = Depends(current_user)):
    """The patient's own documents — processing, done or failed, with which doctors have
    verified each — and the food handouts their doctors gave them (patient_records)."""
    from app.services.nutrition_plan import handouts_for_patient
    from app.services.patient_records import documents_for_patient

    patient_id = str(user["patient_id"])
    return {
        "documents": documents_for_patient(patient_id),
        "handouts": handouts_for_patient(patient_id),
    }


@router.get("/documents/{document_id}/file")
async def patient_document_file(document_id: str, user: dict = Depends(current_user)):
    """The patient's own uploaded file, as an attachment — the same rules as the doctors'
    download: an allowlisted content type, never rendered inline by the browser."""
    from fastapi.responses import Response

    from app.services.blob_storage import sanitize_filename
    from app.services.patient_records import read_own_document_file

    try:
        data, filename, content_type = await read_own_document_file(str(user["patient_id"]), document_id)
    except PermissionError:
        raise HTTPException(status_code=404, detail="Document not found.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="The original file for this document is no longer available.")
    except RuntimeError as exc:
        logger.error("patient document download failed (document_id=%s): %s", document_id, exc)
        raise HTTPException(status_code=502, detail="This document could not be read right now.")
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{sanitize_filename(filename)}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/history")
def chat_history(user: dict = Depends(current_user)):
    documents = list_user_documents(user["patient_id"])
    return {
        "sessions": load_chat_sessions_with_messages(
            patient_id=user["patient_id"],
            limit=100,
        ),
        "messages": load_chat_history_with_timestamps(
            patient_id=user["patient_id"],
            limit=100,
        ),
        "documents": [
            {
                "document_id": entry.document_id,
                "user_id": entry.user_id,
                "session_id": entry.session_id,
                "original_filename": entry.original_filename,
                "document_type": entry.document_type,
                "clinical_date": entry.clinical_date,
                "created_at": entry.created_at.isoformat() if hasattr(entry.created_at, "isoformat") else str(entry.created_at),
                "ingestion_status": entry.ingestion_status,
            }
            for entry in documents
        ],
    }


# ---- Document upload with consent gating ----

@router.post("/upload")
async def upload_document(
    request: Request,
    user: dict = Depends(current_user),
) -> dict:
    """
    POST /chat/upload

    Stage a medical document after GPT-4o relevance verification.

    Guardrail 1 (GPT-4o): verify the file is a medical document.
      - Images → vision message with base64.
      - PDFs   → extracted text sample.
    If not medical → 400.

    On pass → stage the file in blob storage, persist a short-lived
    pending_upload token (30 min TTL), return 202 with document_token.
    """
    from app.inference.azure_client import gpt4o_relevance_check

    form = await request.form()
    file: UploadFile | None = form.get("file")  # type: ignore[assignment]
    session_id: str = str(form.get("session_id") or "").strip() or str(uuid.uuid4())

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="A file is required.")

    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in ALLOWED_UPLOAD_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and JPEG/PNG uploads are supported.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Uploaded file is too large (max 15 MB).")

    # Checked before the relevance check so a refused file costs no model call.
    if len(_doc_analysis_cache.get(_doc_cache_key(str(user["patient_id"]), session_id), [])) >= MAX_DOCUMENTS_PER_MESSAGE:
        raise HTTPException(
            status_code=400,
            detail=f"You can attach up to {MAX_DOCUMENTS_PER_MESSAGE} documents per message. "
                   "Send these first, then attach more.",
        )

    extracted_text: str | None = None
    if mime_type == "application/pdf":
        try:
            extracted_text = _extract_pdf_text(file_bytes)
        except Exception as exc:
            logger.warning("upload: PDF text extraction failed: %s", exc)
            extracted_text = None

    # Guardrail 1 — medical relevance check via GPT-4o
    try:
        is_medical = await gpt4o_relevance_check(
            mime_type=mime_type,
            file_bytes=file_bytes,
            extracted_text=extracted_text,
        )
    except Exception as exc:
        logger.error("upload: relevance check failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Document verification unavailable: {exc}")

    if not is_medical:
        raise HTTPException(
            status_code=400,
            detail="Invalid document type. Only verified medical records are supported.",
        )

    # Guardrail 2 — staging + consent token
    user_id: str = str(user["patient_id"])
    document_id: str = str(uuid.uuid4())
    document_token: str = str(uuid.uuid4())
    original_filename: str = file.filename or "upload"

    # Extract document content and cache it so the next /chat/stream call can
    # inject it directly into LangGraph state (bypasses checkpoint merge issues).
    try:
        from app.services.document_pipeline import _extract_image, _extract_pdf_images
        if mime_type == "application/pdf":
            images = _extract_pdf_images(file_bytes)
            page_count = len(images) or max(1, (extracted_text or "").count("\f") + 1)
            source = "pdf"
        else:
            images = _extract_image(file_bytes, mime_type)
            page_count = 1
            source = "image"
        entry = {
            "file_name": original_filename,
            "mime_type": mime_type,
            "text": extracted_text or "",
            "images": images,
            "page_count": page_count,
            "source": source,
            # Ties the queued analysis to its consent decision, so one file can be declined
            # or removed without touching the others.
            "document_token": document_token,
            "consented": False,
        }
        cache_key = _doc_cache_key(user_id, session_id)
        _doc_analysis_cache.setdefault(cache_key, []).append(entry)
        logger.info(
            "upload: cached extracted data for user=%s session=%s file=%s images=%d queued=%d",
            user_id, session_id, original_filename, len(images), len(_doc_analysis_cache[cache_key]),
        )
    except Exception as exc:
        logger.warning("upload: could not extract/cache doc for user=%s: %s", user_id, exc)

    blob_path = staging_blob_path(user_id, document_id, original_filename)

    try:
        await upload_blob(blob_path, file_bytes, content_type=mime_type)
    except Exception as exc:
        logger.error("upload: staging blob upload failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Could not stage document: {exc}")

    save_pending_upload(
        document_token=document_token,
        user_id=user_id,
        session_id=session_id,
        document_id=document_id,
        blob_path=blob_path,
        original_filename=original_filename,
    )

    logger.info(
        "upload: staged document_id=%s token=%s user=%s",
        document_id, document_token, user_id,
    )
    return {
        "requires_consent": True,
        "document_token": document_token,
        "message": "Medical file validated. Please confirm processing consent.",
    }


@router.post("/confirm-processing")
async def confirm_processing(
    body: ConfirmProcessingRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(current_user),
) -> dict:
    """
    POST /chat/confirm-processing

    Consume the staging token and either:
      - consent_granted=False  → delete staged blob, return 200.
      - consent_granted=True   → move blob to vault, launch background ingestion.

    user_id / session_id / document_id are resolved server-side from the token
    record — the client-supplied token is the only trusted input.
    """
    record = consume_pending_upload(body.document_token)
    if not record or str(record["user_id"]) != str(user["patient_id"]):
        raise HTTPException(
            status_code=410,
            detail="Document token not found, already used, or expired.",
        )

    user_id = str(record["user_id"])
    session_id = str(record["session_id"])
    document_id = str(record["document_id"])
    staged_path = str(record["blob_path"])
    original_filename = str(record["original_filename"])

    if not body.consent_granted:
        # Also discard this file's queued analysis so it doesn't bleed into a later turn —
        # this file's only; the patient may have agreed to the others.
        _discard_cached_document(user_id, session_id, body.document_token)
        try:
            await delete_blob(staged_path)
        except Exception as exc:
            logger.warning("confirm-processing: could not delete staged blob: %s", exc)
        logger.info("confirm-processing: consent declined — document_id=%s deleted", document_id)
        return {"status": "cancelled", "message": "Document was discarded per your request."}

    vault_path = vault_blob_path(user_id, session_id, document_id, original_filename)
    try:
        await move_blob(staged_path, vault_path)
    except asyncio.CancelledError as exc:
        # On Windows, ProactorEventLoop + aiohttp can cancel I/O operations spuriously
        # (WinError 995). Catching here prevents the CancelledError from propagating
        # through FastAPI middleware and crashing the entire event loop.
        logger.error("confirm-processing: blob move cancelled (Windows I/O): %s", exc)
        _discard_cached_document(user_id, session_id, body.document_token)
        raise HTTPException(status_code=502, detail="Could not vault document: connection cancelled — try again")
    except Exception as exc:
        logger.error("confirm-processing: blob move failed: %s", exc)
        _discard_cached_document(user_id, session_id, body.document_token)
        raise HTTPException(status_code=502, detail=f"Could not vault document: {exc}")

    # Stored with consent, so its queued analysis may now run with the next message.
    _mark_cached_document_consented(user_id, session_id, body.document_token)

    summary_path = summary_blob_path(user_id, document_id)
    background_tasks.add_task(
        _run_ingestion_pipeline,
        user_id=user_id,
        session_id=session_id,
        document_id=document_id,
        vault_path=vault_path,
        summary_path=summary_path,
        original_filename=original_filename,
        mime_type=_guess_mime(original_filename),
    )

    logger.info(
        "confirm-processing: consent granted, ingestion queued — document_id=%s", document_id
    )
    return {
        "status": "processing",
        "document_id": document_id,
        "message": "Your document is being securely processed. You will be notified when ready.",
    }


@router.get("/document-status/{document_id}")
def document_status(document_id: str, user: dict = Depends(current_user)) -> dict:
    """
    Poll endpoint for clients that connect to the WebSocket AFTER ingestion
    finished and missed the live broadcast.
    """
    entry = get_catalog_entry(document_id)
    if not entry or entry.user_id != str(user["patient_id"]):
        raise HTTPException(status_code=404, detail="Document not found.")
    return {
        "document_id": document_id,
        "ingestion_status": entry.ingestion_status,
        "document_type": entry.document_type,
        "clinical_date": entry.clinical_date,
    }


# ---- Background ingestion pipeline ----

async def _run_ingestion_pipeline(
    *,
    user_id: str,
    session_id: str,
    document_id: str,
    vault_path: str,
    summary_path: str,
    original_filename: str,
    mime_type: str,
) -> None:
    """
    Background worker — runs after consent is granted.

    Step 1: Insert catalog row (status=processing).
    Step 2: Structured extraction via GPT-4o (last GPT-4o call for this doc).
    Step 3: Write summary JSON to blob.
    Step 4: Flip catalog row to status=complete.
    Step 5: Broadcast WebSocket 'complete' event.

    On any error: mark catalog failed, delete partial summary blob,
    broadcast WebSocket 'error' event.
    """
    from app.inference.azure_client import (
        gpt4o_structured_extraction, gpt4o_transcribe_document_image,
    )
    from app.api.main import connection_manager

    logger.info("ingestion: starting document_id=%s vault=%s", document_id, vault_path)

    # Step 1 — catalog row (processing) before any blob writes
    create_catalog_row(
        document_id=document_id,
        user_id=user_id,
        session_id=session_id,
        original_filename=original_filename,
        blob_summary_path=summary_path,
        ingestion_status="processing",
    )

    try:
        # Download raw file bytes from vault for extraction
        from app.services.blob_storage import _get_blob_service_client, AZURE_CONTAINER_NAME
        async with _get_blob_service_client() as svc:
            container = svc.get_container_client(AZURE_CONTAINER_NAME)
            blob = container.get_blob_client(vault_path)
            stream = await blob.download_blob()
            file_bytes: bytes = await stream.readall()

        extracted_text: str | None = None
        if mime_type == "application/pdf":
            try:
                # Per page, then flattened for the extractor. The pages are stored so a
                # summary sentence can cite one and still be verifiable against it months
                # later, when the file is only in blob storage.
                pdf_pages = extract_pdf_pages(file_bytes)
                extracted_text = "\n\n".join(page["text"] for page in pdf_pages).strip() or None
                try:
                    save_document_pages(document_id, pdf_pages, PAGE_SOURCE_PDF_TEXT)
                except Exception as exc:
                    # Losing page text costs citation precision later; it must not cost
                    # the patient their document, which is already stored by this point.
                    logger.warning("ingestion: could not store page text: %s", exc)
            except Exception as exc:
                logger.warning("ingestion: PDF text extraction failed: %s", exc)
        elif mime_type.startswith("image/"):
            # A photographed or scanned report has no text layer, so there is nothing for
            # a summary to be verified against. Transcribing it gives the verifier a
            # source of record — a weaker one, which is why it is stored under a different
            # `source` and labelled in the UI, but far better than the alternative of
            # showing an unverifiable summary or none at all.
            try:
                transcription = await gpt4o_transcribe_document_image(
                    mime_type=mime_type, file_bytes=file_bytes
                )
                if transcription:
                    save_document_pages(
                        document_id, [{"page_no": 1, "text": transcription}], PAGE_SOURCE_VISION
                    )
            except Exception as exc:
                logger.warning("ingestion: image transcription failed: %s", exc)

        # Step 2 — GPT-4o structured extraction (last GPT-4o call for this document)
        extraction = await gpt4o_structured_extraction(
            mime_type=mime_type,
            file_bytes=file_bytes,
            extracted_text=extracted_text,
        )

        # Step 3 — write summary JSON to blob
        # referring_doctor / referring_department / body_region are carried through rather
        # than dropped. The extractor has always produced them; discarding them here is
        # what made a report that said "Referred by Dr Panday, Psychiatry" untraceable to
        # that referral five minutes later.
        summary_payload = {
            "document_id": document_id,
            "user_id": user_id,
            "session_id": session_id,
            "document_type": extraction["document_type"],
            "clinical_date": extraction["clinical_date"],
            "overall_impression": extraction["overall_impression"],
            "findings": extraction["findings"],
            "referring_doctor": extraction.get("referring_doctor"),
            "referring_department": extraction.get("referring_department"),
            "body_region": extraction.get("body_region"),
        }
        await upload_json_blob(summary_path, summary_payload)
        logger.info("ingestion: summary written to blob — %s", summary_path)

        # Step 4 — flip catalog row to complete
        update_catalog_after_extraction(
            document_id=document_id,
            document_type=extraction["document_type"],
            clinical_date=extraction["clinical_date"],
            findings_keys=list(extraction["findings"].keys()),
            ingestion_status="complete",
            referring_doctor=extraction.get("referring_doctor"),
            referring_department=extraction.get("referring_department"),
            body_region=extraction.get("body_region"),
        )

        # Step 4b — measurements and the clinician summary.
        #
        # Both are deliberately AFTER the catalog flips to 'complete': the document is
        # already usable at this point, and neither of these may be allowed to hold it
        # back or fail it. A document with no chips and no summary is a degraded record;
        # a document stuck in 'processing' because a summary call timed out is a document
        # the patient cannot see at all.
        try:
            from app.services.document_catalog import get_document_pages
            from app.services.document_findings import apply_report_flags, flatten_findings, save_findings

            # Re-classified with the flag and range the report printed beside each value,
            # read from the page text stored in step 1 — the lab's own verdict first.
            measurements = apply_report_flags(
                flatten_findings(extraction["findings"]), get_document_pages(document_id)
            )
            save_findings(document_id, user_id, measurements, extraction["clinical_date"])
        except Exception as exc:
            logger.warning("ingestion: could not store measurements for %s: %s", document_id, exc)

        try:
            from app.services.document_catalog import get_document_pages
            from app.services.document_grounding import summarise_document

            # summarise_document verifies before storing, so nothing unverified can be
            # persisted even if this call returns something odd.
            await summarise_document(document_id, get_document_pages(document_id))
        except Exception as exc:
            logger.warning("ingestion: clinician summary failed for %s: %s", document_id, exc)

        try:
            from app.services.nutrition import prewarm_for_document

            # Guidance for any result nobody has had before is written now, once, so the
            # first doctor to open the nutritionist does not wait on it.
            await prewarm_for_document(document_id)
        except Exception as exc:
            logger.warning("ingestion: nutrition guidance prewarm failed for %s: %s", document_id, exc)

        # The document's results and medications are now on the record, so any cached
        # at-a-glance card for this patient is out of date. Rebuilt in the background, so
        # the next doctor to open the patient does not wait for it.
        try:
            from app.services.patient_overview import schedule_overview_refresh

            schedule_overview_refresh(patient_id=user_id)
        except Exception as exc:
            logger.warning("ingestion: could not schedule overview refresh for %s: %s", document_id, exc)

        # Step 5 — notify connected clients
        await connection_manager.broadcast(
            session_id,
            {
                "status": "complete",
                "document_id": document_id,
                "message": "Document successfully indexed to your secure vault.",
            },
        )
        logger.info("ingestion: COMPLETE document_id=%s", document_id)

    except Exception as exc:
        logger.error("ingestion: FAILED document_id=%s: %s", document_id, exc, exc_info=True)
        mark_catalog_failed(document_id, str(exc))

        # Clean up any partially written summary blob
        try:
            await delete_blob(summary_path)
        except Exception:
            pass

        await connection_manager.broadcast(
            session_id,
            {
                "status": "error",
                "error": f"Document processing failed: {exc}",
            },
        )


def _guess_mime(filename: str) -> str:
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    return {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
    }.get(ext, "application/octet-stream")


# ---- Existing request parser ----

async def _parse_chat_request(request: Request) -> tuple[dict, UploadFile | None]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        payload = {
            "message": str(form.get("message") or "").strip(),
            "session_id": str(form.get("session_id") or "").strip() or None,
            "state": _safe_json_loads(form.get("state")),
        }
        upload = form.get("file")
        if isinstance(upload, UploadFile) and upload.filename:
            payload.update(_prepare_uploaded_file(upload))
            payload["state"] = {
                **(payload.get("state") or {}),
                "pending_file_data": payload["pending_file_data"],
                "pending_file_name": payload["pending_file_name"],
                "pending_file_mime_type": payload["pending_file_mime_type"],
            }
            payload["state"]["file_clarification_context"] = (
                "The patient uploaded a medical file and wants help interpreting it."
            )
        if not payload["message"]:
            raise HTTPException(status_code=400, detail="Message is required.")
        return payload, upload if isinstance(upload, UploadFile) else None

    body = await request.json()
    payload = {
        "message": str(body.get("message") or "").strip(),
        "session_id": str(body.get("session_id") or "").strip() or None,
        "state": body.get("state") if isinstance(body.get("state"), dict) else None,
    }
    if not payload["message"]:
        raise HTTPException(status_code=400, detail="Message is required.")
    return payload, None
