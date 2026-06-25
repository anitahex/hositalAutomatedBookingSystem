from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.dependencies import current_user
from app.agents.graph import arun_patient_chat, initialise_hybrid_memory, run_patient_chat
from app.services.appointments import upcoming_bookings_for_patient
from app.services.document_pipeline import (
    ALLOWED_UPLOAD_MIME_TYPES,
    _extract_pdf_text,
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
    consume_pending_upload,
    create_catalog_row,
    get_catalog_entry,
    mark_catalog_failed,
    save_pending_upload,
    update_catalog_after_extraction,
)

logger = logging.getLogger(__name__)

# Backward-compatible alias for tests and any existing monkeypatches.
active_bookings_for_patient = upcoming_bookings_for_patient

# Server-side cache for extracted file data from /chat/upload.
# Keyed by user_id (str). Consumed on the next /chat/stream call for that user.
# Bypasses LangGraph checkpoint merging which silently drops large base64 payloads.
_doc_analysis_cache: dict[str, list[dict]] = {}

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
            appointments = upcoming_bookings_for_patient(patient_id, limit=5)
            state["active_appointments"] = appointments
            if appointments:
                merged_bookings = _merge_booking_lists(state.get("upcoming_bookings"), appointments)
                state["upcoming_bookings"] = merged_bookings
                state["confirmed_bookings"] = merged_bookings
                state["confirmed_booking"] = merged_bookings[-1]
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

    # Inject cached file data from the most recent /chat/upload for this user.
    # The cache is populated in upload_document() and consumed here exactly once.
    user_id_str = str(patient_id or "")
    if user_id_str and user_id_str in _doc_analysis_cache:
        pending_files = _doc_analysis_cache.pop(user_id_str)
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


def _text_tokens(text: str):
    for match in re.finditer(r"\S+\s*", text or ""):
        yield match.group(0)


def _extract_dept_from_text(text: str) -> str:
    m = re.search(r"###\s*Recommended Specialist\s*\n+\*{0,2}([A-Za-z /\-]+?)\*{0,2}\s*\n", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    lw = text.lower()
    for dept, kws in [
        ("Orthopedics",    ["ortho", "spine", "lumbar", "fracture", "bone", "lba", "vertebra"]),
        ("Cardiology",     ["cardio", "heart", "ecg", "hypertension", "coronary"]),
        ("Neurology",      ["neuro", "brain", "nerve", "epilepsy", "stroke"]),
        ("Pathology",      ["blood report", "cbc", "haemoglobin", "rbc", "wbc", "platelet"]),
        ("Radiology",      ["mri", "ct scan", "x-ray", "xray", "imaging", "ultrasound"]),
        ("Endocrinology",  ["diabetes", "thyroid", "hba1c", "insulin"]),
        ("Pulmonology",    ["lung", "asthma", "copd", "respiratory"]),
        ("Gastroenterology", ["gastro", "liver", "bowel", "hepatitis"]),
        ("Oncology",       ["cancer", "tumor", "malignant", "biopsy"]),
        ("Dermatology",    ["skin", "rash", "eczema", "derma"]),
        ("Gynecology",     ["gynae", "uterus", "ovary", "pregnancy"]),
        ("Urology",        ["urology", "prostate", "bladder", "urinary"]),
    ]:
        if any(kw in lw for kw in kws):
            return dept
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
        "state": result,
        "safety_disclaimer": SAFETY_DISCLAIMER,
    }


@router.post("/stream")
async def chat_stream(request: Request, user: dict = Depends(current_user)):
    payload, _ = await _parse_chat_request(request)
    user_id_str = str((user or {}).get("patient_id") or "")

    async def event_stream():
        # ── Fast path: direct GPT-4o streaming for document analysis ──────────
        if user_id_str and user_id_str in _doc_analysis_cache:
            files = _doc_analysis_cache.pop(user_id_str, [])
            if files:
                from app.inference.azure_client import gpt4o_stream_analysis

                yield _stream_event("start_response")
                full_text = ""

                try:
                    for file_idx, fp in enumerate(files):
                        if file_idx > 0:
                            sep = "\n\n---\n\n"
                            yield _stream_event("token", token=sep)
                            full_text += sep

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

                        async for token in gpt4o_stream_analysis(
                            mime_type=mime,
                            file_bytes=file_bytes,
                            extracted_text=extracted,
                            user_question=payload["message"],
                        ):
                            yield _stream_event("token", token=token)
                            full_text += token

                except Exception as exc:
                    logger.error("event_stream: document streaming failed: %s", exc, exc_info=True)
                    err = "\n\n*Analysis encountered an error — please try again.*"
                    yield _stream_event("token", token=err)
                    full_text += err

                # Build minimal state so frontend can show department / analyzed docs
                state, patient_id = _prepare_chat_state(payload, user)
                state = _append_user_message_to_state(state, payload["message"])
                dept = _extract_dept_from_text(full_text)
                doc_type = _extract_doctype_from_text(full_text)
                doc_log = list(state.get("analyzed_documents") or [])
                for fp in files:
                    doc_log.append({
                        "file_name": fp.get("file_name") or "document",
                        "document_type": doc_type,
                        "department": dept,
                        "summary": (full_text[:150] + "…") if len(full_text) > 150 else full_text,
                    })
                history = list(state.get("conversation_history") or [])
                history.append({"role": "assistant", "text": full_text})
                state.update({
                    "final_response": full_text,
                    "target_department": dept,
                    "awaiting": "user_input",
                    "active_intent": "direct_booking",
                    "intent": "direct_booking",
                    "analyzed_documents": doc_log,
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
        stream_state = _append_user_message_to_state(stream_state, payload["message"])
        # CRITICAL: expose current message as user_input so extraction/prompts work correctly
        stream_state["user_input"] = payload["message"]
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
                state=result,
                token_usage=usage_summary,
                safety_disclaimer=SAFETY_DISCLAIMER,
            )
        except Exception as exc:
            logger.error("event_stream error: %s", exc, exc_info=True)
            yield _stream_event("error", message=str(exc))

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.get("/history")
def chat_history(user: dict = Depends(current_user)):
    return {
        "sessions": load_chat_sessions_with_messages(
            patient_id=user["patient_id"],
            limit=100,
        ),
        "messages": load_chat_history_with_timestamps(
            patient_id=user["patient_id"],
            limit=100,
        ),
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
        }
        _doc_analysis_cache.setdefault(user_id, []).append(entry)
        logger.info(
            "upload: cached extracted data for user=%s file=%s images=%d queued=%d",
            user_id, original_filename, len(images), len(_doc_analysis_cache[user_id]),
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
    if not record:
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
        # Also discard the in-memory extraction cache so it doesn't bleed into a later turn.
        _doc_analysis_cache.pop(user_id, None)
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
        raise HTTPException(status_code=502, detail="Could not vault document: connection cancelled — try again")
    except Exception as exc:
        logger.error("confirm-processing: blob move failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Could not vault document: {exc}")

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
    from app.inference.azure_client import gpt4o_structured_extraction
    from app.api.main import connection_manager

    logger.info("ingestion: starting document_id=%s vault=%s", document_id, vault_path)

    # Step 1 — catalog row (processing) before any blob writes
    create_catalog_row(
        document_id=document_id,
        user_id=user_id,
        session_id=session_id,
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
                extracted_text = _extract_pdf_text(file_bytes)
            except Exception as exc:
                logger.warning("ingestion: PDF text extraction failed: %s", exc)

        # Step 2 — GPT-4o structured extraction (last GPT-4o call for this document)
        extraction = await gpt4o_structured_extraction(
            mime_type=mime_type,
            file_bytes=file_bytes,
            extracted_text=extracted_text,
        )

        # Step 3 — write summary JSON to blob
        summary_payload = {
            "document_id": document_id,
            "user_id": user_id,
            "session_id": session_id,
            "document_type": extraction["document_type"],
            "clinical_date": extraction["clinical_date"],
            "overall_impression": extraction["overall_impression"],
            "findings": extraction["findings"],
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
        )

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
