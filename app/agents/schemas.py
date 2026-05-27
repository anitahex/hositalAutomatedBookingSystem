from typing import Literal, Optional

from pydantic import BaseModel, Field


class PatientExtraction(BaseModel):
    intent: Literal["triage_symptoms", "direct_booking"] = Field(
        description="Goal of the patient."
    )
    symptoms: list[str] = Field(
        description="Clean physical or mental symptoms extracted from the patient text."
    )
    severity: Literal["mild", "moderate", "severe", "emergency"] = Field(
        description="Estimated urgency of the patient's health issue."
    )


class ConversationDecision(BaseModel):
    has_enough_info: bool = Field(
        description=(
            "True only when you know: symptoms, approximate duration, cause/trigger "
            "(injury/allergy/gradual/sudden), severity pattern, and any relevant history. "
            "False if any of these are still unclear."
        )
    )
    next_question: Optional[str] = Field(
        default=None,
        description=(
            "The single most important follow-up question to ask next, written in a warm, "
            "conversational tone. None if has_enough_info is True."
        )
    )
    collected_info: dict = Field(
        default_factory=dict,
        description=(
            "All structured info collected so far. Keys can include: "
            "duration, cause, severity_pattern, location, history, allergies, "
            "medications, trigger, associated_symptoms, lifestyle, etc."
        )
    )


class RemedyResponse(BaseModel):
    remedy_text: str = Field(
        description=(
            "A warm, personalised home remedy or first-aid advice tailored to the "
            "specific patient's symptoms, cause, duration, and severity. "
            "Be specific — not generic. Reference what the patient told you."
        )
    )
    follow_up_question: str = Field(
        description=(
            "A warm question asking the patient to try the remedy and report back. "
            "e.g. 'Please try this for a day or two and let me know how you feel. "
            "Are your symptoms improving, or are they persisting/worsening?'"
        )
    )


class SupervisorDecision(BaseModel):
    next_agent: Literal[
        "continue_current",
        "triage_router",
        "conversation_agent",
        "remedy_agent",
        "medical_rag",
        "appointment_booker",
        "finish",
    ] = Field(description="The best next graph step for the latest patient message.")
    intent: Optional[Literal["triage_symptoms", "direct_booking"]] = Field(
        default=None,
        description="Updated high-level intent if the patient changed direction.",
    )
    reason: str = Field(description="Short routing reason for debugging.")
