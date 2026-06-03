from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import current_user
from app.agents.graph import run_patient_chat
from app.services.appointments import active_bookings_for_patient
from app.services.chat_history import append_chat_messages, load_recent_chat_history


router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    patient_id: str | None = None
    state: dict | None = None


@router.post("")
def chat(request: ChatRequest, user: dict = Depends(current_user)):
    state = dict(request.state or {})
    patient_id = user["patient_id"]
    state["patient_profile"] = user

    if patient_id and "conversation_history" not in state:
        try:
            state["conversation_history"] = load_recent_chat_history(patient_id)
        except Exception as exc:
            print(f"Could not load chat history for {patient_id}: {exc}")

    if patient_id:
        try:
            appointments = active_bookings_for_patient(patient_id, limit=5)
            state["active_appointments"] = appointments
            if appointments and not state.get("confirmed_bookings"):
                state["confirmed_bookings"] = appointments
                state["confirmed_booking"] = appointments[-1]
        except Exception as exc:
            print(f"Could not load active appointments for {patient_id}: {exc}")

    result = run_patient_chat(
        user_input=request.message,
        patient_id=patient_id,
        state=state,
    )
    response_text = result.get("final_response") or "I'm still processing your information, could you tell me a bit more?"

    if patient_id:
        try:
            append_chat_messages(
                patient_id,
                [
                    {"role": "patient", "text": request.message},
                    {"role": "assistant", "text": response_text},
                ],
            )
        except Exception as exc:
            print(f"Could not save chat history for {patient_id}: {exc}")

    return {"response": response_text, "state": result}
