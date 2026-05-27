from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.graph import run_patient_chat


router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    patient_id: str | None = None
    state: dict | None = None


@router.post("")
def chat(request: ChatRequest):
    result = run_patient_chat(
        user_input=request.message,
        patient_id=request.patient_id,
        state=request.state,
    )
    response_text = result.get("final_response") or "I'm still processing your information, could you tell me a bit more?"
    return {"response": response_text, "state": result}