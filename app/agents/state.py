from typing import Optional, TypedDict


class GraphState(TypedDict, total=False):
    # Core input
    user_input: str
    patient_id: Optional[str]

    # Routing
    next_agent: Optional[str]
    awaiting: Optional[str]
    supervisor_checked_input: Optional[bool]

    # Triage extraction
    intent: Optional[str]
    symptoms: Optional[list[str]]
    severity: Optional[str]

    # Dynamic conversation history
    # Each entry: {"role": "assistant"|"patient", "text": str}
    conversation_history: Optional[list[dict]]
    greeted: Optional[bool]

    # What info has been collected via conversation
    collected_info: Optional[dict]   # e.g. {"duration": "3 days", "cause": "injury", ...}
    questions_asked: Optional[list[str]]  # track what we've already asked

    # Remedy phase
    remedy_given: Optional[bool]
    remedy_text: Optional[str]
    remedy_requested: Optional[bool]
    persisting: Optional[bool]       # True when patient says remedy didn't help

    # Legacy follow-up (kept for backward compat)
    symptom_duration: Optional[str]
    follow_up_answer: Optional[str]

    # Department + booking
    target_department: Optional[str]
    booking_declined: Optional[bool]
    doctor_options: Optional[list[dict]]
    selected_doctor_id: Optional[str]
    selected_doctor_name: Optional[str]
    slot_options: Optional[list[dict]]
    selected_slot_id: Optional[str]
    booking_active: Optional[bool]
    confirmed_booking: Optional[dict[str, str]]
    note_forwarded: Optional[bool]

    # Final output
    final_response: Optional[str]
