import json
import re

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.dependencies import current_user
from app.agents.graph import initialise_hybrid_memory, run_patient_chat
from app.services.appointments import active_bookings_for_patient
from app.services.chat_history import (
    append_chat_messages,
    load_chat_history_with_timestamps,
    load_chat_sessions_with_messages,
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


class ChatRequest(BaseModel):
    message: str
    patient_id: str | None = None
    state: dict | None = None


def _prepare_chat_state(request: ChatRequest, user: dict):
    state = dict(request.state or {})
    patient_id = user["patient_id"]
    state["patient_profile"] = user
    ensure_chat_session_id(state)

    if patient_id and "conversation_history" not in state and "recent_history" not in state:
        try:
            state["recent_history"] = load_recent_chat_history(
                patient_id,
                chat_session_id=state.get("chat_session_id"),
            )
        except Exception as exc:
            print(f"Could not load chat history for {patient_id}: {exc}")

    if patient_id and not state.get("chat_summary") and state.get("chat_session_id"):
        try:
            state["chat_summary"] = load_chat_session_memory(
                patient_id=patient_id,
                chat_session_id=state.get("chat_session_id"),
            )
        except Exception as exc:
            print(f"Could not load chat summary for {patient_id}: {exc}")

    if patient_id:
        try:
            appointments = active_bookings_for_patient(patient_id, limit=5)
            state["active_appointments"] = appointments
            if appointments and not state.get("confirmed_bookings"):
                state["confirmed_bookings"] = appointments
                state["confirmed_booking"] = appointments[-1]
        except Exception as exc:
            print(f"Could not load active appointments for {patient_id}: {exc}")

    state = initialise_hybrid_memory(state)
    return state, patient_id


def _run_chat_with_usage(request: ChatRequest, user: dict):
    state, patient_id = _prepare_chat_state(request, user)

    with collect_llm_usage() as usage_records:
        result = run_patient_chat(
            user_input=request.message,
            patient_id=patient_id,
            state=state,
        )

    response_text = (
        result.get("final_response")
        or "I'm still processing your information, could you tell me a bit more?"
    )
    result["chat_session_id"] = state["chat_session_id"]

    if patient_id:
        try:
            append_chat_messages(
                patient_id,
                [
                    {"role": "patient", "text": request.message},
                    {"role": "assistant", "text": response_text},
                ],
                chat_session_id=state["chat_session_id"],
            )
        except Exception as exc:
            print(f"Could not save chat history for {patient_id}: {exc}")

        try:
            usage_summary = persist_llm_usage_records(
                patient_id=patient_id,
                chat_session_id=state["chat_session_id"],
                records=usage_records,
            )
        except Exception as exc:
            print(f"Could not save LLM token usage for {patient_id}: {exc}")
            usage_summary = summarize_usage(usage_records)

        try:
            persist_chat_session_memory(
                patient_id=patient_id,
                chat_session_id=state["chat_session_id"],
                chat_summary=result.get("chat_summary") or state.get("chat_summary") or "",
            )
        except Exception as exc:
            print(f"Could not save chat summary for {patient_id}: {exc}")
    else:
        usage_summary = summarize_usage(usage_records)

    result["token_usage"] = usage_summary
    return response_text, result, usage_summary


def _text_tokens(text: str):
    for match in re.finditer(r"\S+\s*", text or ""):
        yield match.group(0)


def _stream_event(event_type: str, **payload) -> str:
    return json.dumps({"type": event_type, **payload}, default=str) + "\n"


@router.post("")
def chat(request: ChatRequest, user: dict = Depends(current_user)):
    response_text, result, usage_summary = _run_chat_with_usage(request, user)
    return {"response": response_text, "state": result}


@router.post("/stream")
def chat_stream(request: ChatRequest, user: dict = Depends(current_user)):
    def event_stream():
        try:
            for token in _text_tokens("I am reviewing your message and checking the right next step.\n\n"):
                yield _stream_event("status_token", token=token)

            response_text, result, usage_summary = _run_chat_with_usage(request, user)
            yield _stream_event("start_response")
            for token in _text_tokens(response_text):
                yield _stream_event("token", token=token)
            yield _stream_event(
                "final",
                response=response_text,
                state=result,
                token_usage=usage_summary,
            )
        except Exception as exc:
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
        )
    }
