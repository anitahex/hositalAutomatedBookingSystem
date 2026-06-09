from typing import Literal, Optional

from pydantic import BaseModel, Field


class PatientExtraction(BaseModel):
    intent: Literal["greeting", "triage_symptoms", "direct_booking", "unclear"] = Field(
        description="Goal of the patient."
    )
    symptoms: list[str] = Field(
        description="Clean physical or mental symptoms extracted from the patient text."
    )
    severity: Literal["mild", "moderate", "severe", "emergency"] = Field(
        description="Estimated urgency of the patient's health issue."
    )


class ConversationDecision(BaseModel):
    intent: Optional[Literal["continue_intake", "direct_booking"]] = Field(
        default="continue_intake",
        description="Whether the patient wants to keep answering intake questions or switch to booking.",
    )
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


class RemedyFollowUpDecision(BaseModel):
    patient_status: Literal[
        "improving",
        "persisting_or_worsening",
        "agrees_to_forward_note",
        "declines_forward_note",
        "unclear",
    ] = Field(description="The intent/status in the patient's reply to the remedy follow-up.")
    reason: str = Field(description="Brief explanation for the classification.")


class BookingMenuDecision(BaseModel):
    action: Literal[
        "select_option",
        "decline_booking",
        "request_remedy",
        "cancel_appointment",
        "unclear",
    ] = Field(
        description="What the patient is trying to do while viewing booking options."
    )
    selected_value: Optional[str] = Field(
        default=None,
        description="The doctor/slot number, id, name, or time the patient selected, if any.",
    )
    reason: str = Field(description="Brief explanation for the classification.")


class DepartmentDecision(BaseModel):
    department: Optional[str] = Field(
        default=None,
        description="Best hospital department for the symptoms, or None if unclear.",
    )
    confidence: float = Field(description="Confidence from 0.0 to 1.0.")
    needs_clarification: bool = Field(description="True if more symptom detail is needed.")
    reason: str = Field(description="Brief clinical routing explanation.")


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


class UserRequestUnderstanding(BaseModel):
    action: Literal[
        "profile_query",
        "symptom_or_care",
        "direct_booking",
        "booking_lookup",
        "cancel_appointment",
        "end_chat",
        "thanks_only",
        "non_medical",
        "continue_current",
        "unclear",
    ] = Field(description="The user's latest request in the current state.")
    profile_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Requested profile fields, e.g. name, age, blood_group, health_issues, "
            "mobile_number, email, address."
        ),
    )
    requested_department: Optional[str] = Field(
        default=None,
        description="Department explicitly requested by the user, if any.",
    )
    requested_doctor_name: Optional[str] = Field(
        default=None,
        description="Specific doctor name explicitly requested by the user, if any.",
    )
    requested_date: Optional[str] = Field(
        default=None,
        description="Requested appointment date as YYYY-MM-DD, if the user asked for a date.",
    )
    reason: str = Field(description="Brief explanation for the classification.")
