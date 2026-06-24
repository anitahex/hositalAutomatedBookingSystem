import asyncio
import re

from langchain_core.output_parsers import PydanticOutputParser
from app.agents.schemas import RemedyFollowUpDecision, RemedyResponse
from app.agents.state import GraphState
from app.agents.intake_utils import compact_booking_summary, compact_fact_summary, compact_state_summary
from app.inference.llm import agenerate_text
from app.services.appointments import update_booking_note
from app.services.memory_policy import get_memory_policy

parser = PydanticOutputParser(pydantic_object=RemedyResponse)
follow_up_parser = PydanticOutputParser(pydantic_object=RemedyFollowUpDecision)
MEMORY_POLICY = get_memory_policy("remedy_agent")

STATIC_REMEDY_PROMPT = """You are a compassionate medical assistant agent. Review the patient's symptoms and context, then provide 2 brief, personalised care tips.
- If 'Confirmed Booking' is empty/None, DO NOT offer a new booking.
- If 'Confirmed Booking' contains data, close your response by asking if they would like you to forward these new symptoms as a clinical note to their upcoming doctor.

Return ONLY valid JSON matching this exact structure:
{"remedy_text":"string","follow_up_question":"string"}"""

STATIC_FOLLOWUP_PROMPT = """You are a hospital assistant interpreting a patient's reply after remedy advice. Use meaning and context, not keyword matching.

Classify the reply:
- improving: patient says the remedy helped or they feel better.
- persisting_or_worsening: patient says symptoms continue, worsened, did not improve, or they want doctor help now.
- agrees_to_forward_note: patient agrees to forward new symptoms to the booked doctor.
- declines_forward_note: patient declines forwarding the note.
- unclear: not enough information.

Return ONLY valid JSON matching this exact structure:
{"patient_status":"improving|persisting_or_worsening|agrees_to_forward_note|declines_forward_note|unclear","reason":"string"}"""

def _clean_json(raw_output: str) -> str:
    return raw_output.replace("```json", "").replace("```", "").strip()


def _matches_phrase(text: str, phrase: str) -> bool:
    pattern = r"\b" + re.escape(phrase) + r"\b"
    return re.search(pattern, text) is not None


def _looks_like_affirmative_forward(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return any(
        _matches_phrase(lowered, phrase)
        for phrase in (
            "yes",
            "yes please",
            "please do",
            "do it",
            "forward it",
            "send it",
            "sure",
            "ok",
            "okay",
            "go ahead",
        )
    )


def _looks_like_decline_forward(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return any(
        _matches_phrase(lowered, phrase)
        for phrase in (
            "no",
            "not now",
            "dont",
            "do not",
            "skip",
            "later",
        )
    )


def _latest_booking(state: GraphState) -> dict | None:
    bookings = state.get("upcoming_bookings") or state.get("confirmed_bookings") or []
    for item in reversed(bookings):
        if isinstance(item, dict) and item.get("booking_id"):
            return item

    booking = state.get("confirmed_booking")
    if isinstance(booking, dict) and booking.get("booking_id"):
        return booking

    appointments = state.get("active_appointments") or []
    for item in reversed(appointments):
        if isinstance(item, dict) and item.get("booking_id"):
            return item

    return None


def _summarise_clinical_note(state: GraphState, user_text: str | None = None) -> str:
    symptoms = [str(item).strip() for item in (state.get("symptoms") or []) if str(item).strip()]
    if not symptoms and state.get("symptom_duration"):
        symptoms = [str(state.get("symptom_duration")).strip()]

    collected = state.get("collected_info") or {}
    note_parts: list[str] = []

    if symptoms:
        note_parts.append(f"Reported symptoms: {', '.join(symptoms)}")

    duration = collected.get("duration") or state.get("symptom_duration")
    if duration:
        note_parts.append(f"Duration: {duration}")

    for label, keys in (
        ("Location", ("location",)),
        ("Trigger/cause", ("cause", "trigger", "onset")),
        ("Pattern", ("severity_pattern", "pattern")),
        ("Associated symptoms", ("associated_symptoms",)),
        ("Relevant history", ("history", "existing_conditions")),
        ("Medications", ("medications",)),
        ("Allergies", ("allergies",)),
    ):
        value = next((collected.get(key) for key in keys if collected.get(key)), None)
        if value:
            note_parts.append(f"{label}: {value}")

    if state.get("remedy_text"):
        remedy_preview = " ".join(str(state["remedy_text"]).split())
        note_parts.append(f"Recent remedy advice: {remedy_preview[:220]}")

    if user_text and user_text.strip() and len(note_parts) < 2:
        note_parts.append(f"Patient message: {user_text.strip()}")

    if not note_parts:
        return "Patient requested the latest symptoms be forwarded to the upcoming doctor."

    return "Clinical note forwarded from chat: " + "; ".join(note_parts)


def _update_current_booking_context(state: GraphState, booking_note: str, booking: dict) -> dict:
    updated_booking = {**booking, "booking_note": booking_note}
    upcoming_bookings = list(state.get("upcoming_bookings") or state.get("confirmed_bookings") or [])
    replaced = False
    for index, item in enumerate(upcoming_bookings):
        if item.get("booking_id") == updated_booking.get("booking_id") or item.get("slot_id") == updated_booking.get("slot_id"):
            upcoming_bookings[index] = updated_booking
            replaced = True
            break
    if not replaced:
        upcoming_bookings.append(updated_booking)

    active_appointments = list(state.get("active_appointments") or [])
    for index, item in enumerate(active_appointments):
        if item.get("booking_id") == updated_booking.get("booking_id") or item.get("slot_id") == updated_booking.get("slot_id"):
            active_appointments[index] = updated_booking
            break

    return {
        "upcoming_bookings": upcoming_bookings,
        "confirmed_booking": updated_booking,
        "confirmed_bookings": upcoming_bookings,
        "active_appointments": active_appointments or upcoming_bookings,
    }

async def _classify_follow_up(state: GraphState, user_text: str) -> RemedyFollowUpDecision | None:
    if _latest_booking(state):
        if _looks_like_affirmative_forward(user_text):
            return RemedyFollowUpDecision(
                patient_status="agrees_to_forward_note",
                reason="Patient clearly agreed to forward the symptom update.",
            )
        if _looks_like_decline_forward(user_text):
            return RemedyFollowUpDecision(
                patient_status="declines_forward_note",
                reason="Patient clearly declined forwarding the symptom update.",
            )

    dynamic_user_prompt = f"""Current state: {compact_state_summary(state)}
Confirmed booking: {compact_booking_summary(state.get('upcoming_bookings') or state.get('confirmed_bookings'))}
Collected facts: {compact_fact_summary(state.get('collected_data') or state.get('collected_info'))}
Previous remedy: {state.get('remedy_text') or 'None'}
Latest reply: {user_text}"""
    raw_output = await agenerate_text(
        system_prompt=STATIC_FOLLOWUP_PROMPT,
        user_prompt=dynamic_user_prompt,
        node_name="remedy_agent",
        chat_summary=state.get("chat_summary"),
        include_history=True,
        history_turns=min(4, MEMORY_POLICY.prompt_window_turns),
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    try: return follow_up_parser.parse(_clean_json(raw_output))
    except Exception: return None

async def remedy_agent_node(state: GraphState):
    if state.get("awaiting") == "remedy_check":
        user_text = state.get("user_input", "")
        updated_history = list(state.get("conversation_history") or [])
        decision = await _classify_follow_up(state, user_text)
        patient_status = decision.patient_status if decision else "unclear"

        if patient_status == "agrees_to_forward_note":
            response = "I am ready to attach the note when the supervisor sends this turn through the continue flow."
            updated_history.append({"role": "assistant", "text": response})
            return {"conversation_history": updated_history, "messages": updated_history[-6:], "awaiting": None, "note_forwarded": False, "final_response": response}

        if patient_status == "persisting_or_worsening":
            bridge = "I am sorry to hear the remedy has not helped. Since your symptoms are persisting, let me find the right specialist for you."
            updated_history.append({"role": "assistant", "text": bridge})
            return {
                "conversation_history": updated_history,
                "messages": updated_history[-6:],
                "awaiting": None,
                "persisting": True,
                "active_intent": "direct_booking",
                "intent": "direct_booking",
                "final_response": bridge,
            }
        
        closing = "I'm glad you're feeling better! Take care, and let me know if symptoms return."
        updated_history.append({"role": "assistant", "text": closing})
        return {"conversation_history": updated_history, "messages": updated_history[-6:], "awaiting": None, "persisting": False, "final_response": closing}

    dynamic_user_prompt = f"""Current state: {compact_state_summary(state)}
Upcoming bookings: {compact_booking_summary(state.get('upcoming_bookings') or state.get('confirmed_bookings'))}
Current symptoms: {', '.join(state.get('symptoms') or []) or 'None'}
Collected facts: {compact_fact_summary(state.get('collected_data') or state.get('collected_info'))}"""
    raw_output = await agenerate_text(
        system_prompt=STATIC_REMEDY_PROMPT,
        user_prompt=dynamic_user_prompt,
        node_name="remedy_agent",
        chat_summary=state.get("chat_summary"),
        include_history=True,
        history_turns=min(4, MEMORY_POLICY.prompt_window_turns),
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    
    try:
        remedy = parser.parse(_clean_json(raw_output))
        full_response = f"{remedy.remedy_text}\n\n{remedy.follow_up_question}"
    except Exception:
        full_response = "Please rest and seek medical care if symptoms are getting worse. Let me know how you feel soon."

    updated_history = list(state.get("conversation_history") or [])
    updated_history.append({"role": "assistant", "text": full_response})
    return {"conversation_history": updated_history, "messages": updated_history[-6:], "remedy_given": True, "remedy_text": full_response, "awaiting": "remedy_check", "final_response": full_response}
