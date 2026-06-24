from __future__ import annotations

from typing import Annotated, Any, Optional, TypedDict


def rolling_message_reducer(existing: list[dict] | None, new: list[dict] | None) -> list[dict]:
    merged: list[dict] = []
    system_messages: list[dict] = []

    for message in list(existing or []) + list(new or []):
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "").strip().lower()
        if role == "system":
            if not system_messages:
                system_messages.append(message)
            continue
        merged.append(message)

    merged = merged[-6:]
    if system_messages:
        return [system_messages[0], *merged][-6:]
    return merged


class GraphState(TypedDict, total=False):
    # Identity / session
    user_input: str
    patient_id: Optional[str]
    session_id: Optional[str]
    chat_session_id: Optional[str]
    patient_profile: Optional[dict[str, Any]]

    # Rolling state / public context
    messages: Annotated[list[dict[str, Any]], rolling_message_reducer]
    recent_history: Optional[list[dict[str, Any]]]
    conversation_history: Optional[list[dict[str, Any]]]
    chat_summary: Optional[str]

    # Routing / intent
    active_intent: Optional[str]
    intent: Optional[str]
    awaiting: Optional[str]
    next_agent: Optional[str]
    supervisor_checked_input: Optional[bool]
    chat_closed: Optional[bool]
    greeted: Optional[bool]

    # Clinical memory
    collected_facts: Optional[dict[str, Any]]
    collected_data: Optional[dict[str, Any]]
    collected_info: Optional[dict[str, Any]]
    symptoms: Optional[list[str]]
    severity: Optional[str]
    questions_asked: Optional[list[str]]

    # Remedy / follow-up
    remedy_given: Optional[bool]
    remedy_text: Optional[str]
    remedy_requested: Optional[bool]
    persisting: Optional[bool]
    note_forwarded: Optional[bool]

    # Booking / appointments
    target_department: Optional[str]
    candidate_departments: Optional[list[dict[str, Any]]]
    requested_department: Optional[str]
    requested_doctor_name: Optional[str]
    requested_date: Optional[str]
    department_match_source: Optional[str]
    department_match_confidence: Optional[float]
    department_match_reason: Optional[str]
    retrieval_attempted: Optional[bool]
    retrieval_confidence: Optional[float]
    date_options: Optional[list[dict[str, str]]]
    booking_declined: Optional[bool]
    doctor_options: Optional[list[dict[str, Any]]]
    selected_doctor_id: Optional[str]
    selected_doctor_name: Optional[str]
    slot_options: Optional[list[dict[str, Any]]]
    selected_slot_id: Optional[str]
    booking_active: Optional[bool]
    upcoming_bookings: Optional[list[dict[str, Any]]]
    confirmed_booking: Optional[dict[str, Any]]
    confirmed_bookings: Optional[list[dict[str, Any]]]
    cancellation_options: Optional[list[dict[str, Any]]]
    reschedule_options: Optional[list[dict[str, Any]]]
    reschedule_date_options: Optional[list[dict[str, str]]]
    reschedule_slot_options: Optional[list[dict[str, Any]]]
    selected_booking_id: Optional[str]

    # File uploads (in-memory, current turn)
    pending_file_data: Optional[dict[str, Any]]        # single file — kept for graph compat
    pending_files_data: Optional[list[dict[str, Any]]] # all files queued in this send
    pending_file_name: Optional[str]
    pending_file_mime_type: Optional[str]
    file_clarification_context: Optional[str]

    # Blob-catalog document pipeline
    user_id: Optional[str]
    active_document_id: Optional[str]   # document_id of the most recently processed upload
    document_session_cache: Optional[dict[str, Any]]  # per-session in-memory blob summary cache

    # Persistent document analysis history — survives across turns so supervisor never forgets
    analyzed_documents: Optional[list[dict[str, Any]]]  # [{file_name, document_type, department, summary}]

    # Legacy / compatibility
    symptom_duration: Optional[str]
    follow_up_answer: Optional[str]
    active_appointments: Optional[list[dict[str, Any]]]
    pending_file_text: Optional[str]

    # Final response
    final_response: Optional[str]
