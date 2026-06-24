import json
import re
from datetime import date, datetime, timedelta, timezone

from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import CombinedSupervisorDecision
from app.agents.state import GraphState
from app.agents.intake_utils import compact_booking_summary, compact_fact_summary, compact_state_summary
from app.inference.llm import generate_router_text, generate_text
from app.services.appointments import CANONICAL_DEPARTMENTS, DEPARTMENT_ALIASES, normalize_department_name, update_booking_note

_TEMPORAL_TERMS = frozenset({
    "today", "tonight", "this morning", "this afternoon", "this evening",
    "this week", "this month", "now", "currently", "at the moment",
    "scheduled", "right now", "soon", "shortly", "upcoming", "today's",
})


parser = PydanticOutputParser(pydantic_object=CombinedSupervisorDecision)

STATIC_SUPERVISOR_PROMPT = """
You are the Master Supervisor for a hospital AI assistant. You control the flow of conversation.
You receive the latest user message, the recent chat history, and the current internal system state.

Your job is to parse the user's intent and decide which specialist agent handles the next turn.

# CONVERSATION DYNAMICS & CONTEXT RETENTION
- The user can ask anything at any time. If they ask a random question mid-triage, route them to a QA/general agent, but DO NOT erase the `active_intent` or `collected_data`.
- If the user provides a short answer like "sure", "yes", or "since morning", look at the `Awaiting` state to understand what they are replying to.
- If the user wants to change topics entirely (e.g., goes from booking to symptoms), route to the new agent and change the intent.

# AGENT ROUTING RULES
- `continue_current`: Use when the user answers an intake question, agrees to an assistant's proposal (like forwarding notes), or selects an active menu option.
- `triage_router`: Use when the user describes NEW symptoms or a new illness.
- `conversation_agent`: Use when the user is providing follow-up details about their symptoms (duration, onset, triggers).
- `remedy_agent`: Use when the user explicitly asks for relief, home care, or we have enough symptom data to suggest care.
- `appointment_booker`: Use when the user wants to book, check availability, or cancel.
- `appointment_resolver`: Use when the user wants to cancel or change an appointment and there are multiple upcoming bookings.
- `document_analyzer`: Use when the user uploaded a document and it relates to the current issue.
- `general_qa`: Use when the user asks a medical question unrelated to their immediate symptoms, or asks about hospital policies.
- `finish`: Use when the user wants to end the chat or says that's all.

Return ONLY valid JSON:
{
  "user_action_summary": "Short description of what the user just did",
  "next_agent": "<choose from routing rules>",
  "update_active_intent": "<triage_symptoms | direct_booking | null_if_no_change>",
  "extracted_facts": {"key": "value", "note": "only include NEW facts extracted from this turn"}
}
""".strip()


def _clean_json(raw_output: str) -> str:
    cleaned = (raw_output or "").replace("```json", "").replace("```", "").strip()
    cleaned = re.sub(
        r'"update_active_intent"\s*:\s*"null_if_no_change"',
        '"update_active_intent": null',
        cleaned,
    )
    cleaned = re.sub(
        r"'update_active_intent'\s*:\s*'null_if_no_change'",
        '"update_active_intent": null',
        cleaned,
    )
    return cleaned


def _route(next_agent: str, **updates):
    return {"next_agent": next_agent, "supervisor_checked_input": True, **updates}


def _current_intent(state: GraphState) -> str | None:
    return state.get("active_intent") or state.get("intent")


def _current_facts(state: GraphState) -> dict:
    collected = state.get("collected_facts") or state.get("collected_data") or state.get("collected_info") or {}
    return dict(collected) if isinstance(collected, dict) else {}


def _current_messages(state: GraphState) -> list[dict]:
    messages = state.get("messages") or state.get("recent_history") or state.get("conversation_history") or []
    normalized: list[dict] = []
    for message in messages[-4:]:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "user").strip().lower()
        if role == "patient":
            role = "user"
        elif role not in {"system", "user", "assistant", "tool"}:
            role = "user"
        content = message.get("content")
        if content is None:
            content = message.get("text", "")
        normalized.append({"role": role, "content": str(content)})
    return normalized


def _format_facts(facts: dict) -> str:
    if not facts:
        return "None"
    parts = []
    for key, value in facts.items():
        if value in (None, "", [], {}):
            continue
        parts.append(f"{key}={value}")
    return "; ".join(parts) if parts else "None"


def _format_bookings(bookings: list[dict] | None) -> str:
    if not bookings:
        return "None"
    parts = []
    for booking in bookings[:3]:
        if not isinstance(booking, dict):
            continue
        doctor = booking.get("doctor") or booking.get("doctor_name") or "Doctor"
        time = booking.get("time") or booking.get("start_time")
        if doctor and time:
            parts.append(f"{doctor} @ {time}")
        elif doctor:
            parts.append(str(doctor))
    return " | ".join(parts) if parts else "None"


def _extract_requested_department(text: str | None) -> str | None:
    if not text:
        return None

    cleaned = " ".join(str(text).lower().replace("-", " ").replace("/", " ").split())
    patterns = (
        r"department(?:\s+of)?\s+([a-z ]+)",
        r"with\s+the\s+([a-z ]+?)\s+department",
        r"in\s+the\s+([a-z ]+?)\s+department",
        r"for\s+the\s+([a-z ]+?)\s+department",
    )
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return normalize_department_name(candidate)

    for candidate in CANONICAL_DEPARTMENTS:
        if candidate and candidate.lower() in cleaned:
            return normalize_department_name(candidate)

    return None


def _state_summary(state: GraphState) -> str:
    return (
        f"State: Intent=[{_current_intent(state) or 'None'}] | "
        f"Awaiting=[{state.get('awaiting') or 'None'}] | "
        f"Known Facts: [{_format_facts(_current_facts(state))}] | "
        f"Doctors: [{_format_bookings(state.get('upcoming_bookings') or state.get('confirmed_bookings'))}] | "
        f"File: [{state.get('pending_file_name') or 'None'}]"
    )


def _should_route_to_resolver(state: GraphState, user_input: str) -> bool:
    lowered = " ".join((user_input or "").lower().split())
    if not lowered or not any(term in lowered for term in ("cancel", "change", "modify", "resched", "reschedule")):
        return False
    bookings = state.get("upcoming_bookings") or state.get("confirmed_bookings") or []
    return len(bookings) > 1


def _merge_unique_dicts(existing: list[dict] | None, incoming: list[dict] | None) -> list[dict]:
    merged: list[dict] = []
    seen: set[tuple[str | None, str | None]] = set()

    for item in list(existing or []) + list(incoming or []):
        if not isinstance(item, dict):
            continue
        booking_id = str(item.get("booking_id") or "") or None
        slot_id = str(item.get("slot_id") or "") or None
        key = (booking_id, slot_id)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)

    return merged


def _latest_booking(state: GraphState) -> dict | None:
    for source in (
        state.get("upcoming_bookings"),
        state.get("confirmed_bookings"),
        state.get("active_appointments"),
    ):
        for booking in reversed(source or []):
            if isinstance(booking, dict) and (booking.get("booking_id") or booking.get("slot_id")):
                return booking
    booking = state.get("confirmed_booking")
    if isinstance(booking, dict) and (booking.get("booking_id") or booking.get("slot_id")):
        return booking
    return None


def _is_affirmative(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return lowered in {
        "yes",
        "y",
        "yeah",
        "yep",
        "sure",
        "ok",
        "okay",
        "please do",
        "do it",
        "go ahead",
        "forward it",
        "send it",
    } or any(phrase in lowered for phrase in ("yes please", "sure please", "go ahead", "please forward"))


def _is_negative(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return lowered in {"no", "nope", "nah", "not now", "no thanks", "no thank you"} or any(
        phrase in lowered for phrase in ("not right now", "maybe later", "no need", "dont need", "do not need")
    )


def _looks_like_thanks(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    if not lowered:
        return False
    return any(
        phrase in lowered
        for phrase in (
            "thank you",
            "thanks",
            "thx",
            "appreciate it",
        )
    )


def _looks_like_end_chat(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    if not lowered:
        return False
    return any(
        phrase in lowered
        for phrase in (
            "end the chat",
            "end chat",
            "close the chat",
            "that's all",
            "thats all",
            "that is all",
            "i am done",
            "bye",
            "goodbye",
            "no more",
            "nothing else",
        )
    )


def _looks_like_billing_request(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return any(term in lowered for term in ("billing", "payment", "invoice", "insurance", "bill"))


def _looks_like_upcoming_booking_query(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return any(term in lowered for term in ("upcoming booking", "upcoming bookings", "my bookings", "my appointment", "my appointments"))


def _looks_like_clinical_note_query(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return any(term in lowered for term in ("what symptoms were forwarded", "clinical note", "forwarded to my doctor", "forwarded notes"))


def _looks_like_add_symptoms_request(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return any(term in lowered for term in ("add these symptoms", "please add these symptoms", "forward these symptoms", "send these symptoms"))


def _looks_like_new_symptoms(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return any(term in lowered for term in (
        "fever", "vomiting", "vomit", "pain", "burn", "rash", "cough", "nausea", "diarrhea",
        "headache", "fatigue", "tired", "exhausted", "dizzy", "dizziness", "bleeding", "bleed",
        "swollen", "swelling", "ache", "cramp", "chest", "breathless", "itching", "sore",
        "weakness", "numb", "tingling", "injury", "hurt",
    ))


def _looks_like_general_doctor_request(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return any(term in lowered for term in (
        "see a doctor", "want to see a doctor", "doctor appointment", "need a doctor",
        "show me a doctor", "find me a doctor", "book a doctor", "want a doctor",
        "consult a doctor", "talk to a doctor", "speak to a doctor", "meet a doctor",
        "book an appointment", "book appointment", "want to book", "see a specialist",
        "see a specialist", "find a specialist", "book a specialist", "see a physician",
        "want to see", "want to visit", "visit a doctor",
    ))


def _looks_like_remedy_request(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return any(term in lowered for term in (
        "remedy", "remedies", "home remedy", "what can i take", "what should i take",
        "medicine for", "medication for", "any cure", "natural cure", "relieve",
        "relief", "home care", "home treatment", "treat this", "treat it",
        "what can i do", "how to treat", "how do i treat", "manage this",
    ))


def _looks_like_unsafe_non_medical(text: str) -> bool:
    lowered = " ".join((text or "").lower().replace("'", "").split())
    return any(term in lowered for term in ("bomb", "weapon", "hack", "kill", "make poison"))


def _fallback_profile_response(state: GraphState) -> dict | None:
    text = (state.get("user_input") or "").lower()
    profile = state.get("patient_profile") or {}
    if not profile:
        return None
    if any(term in text for term in ("my name", "my age", "who am i", "what is my name", "what is my age")):
        response = f"Your profile shows {profile.get('name', 'Unknown')} and age {profile.get('age', 'Unknown')}. I am only for health-related support, so tell me your symptoms or ask about a doctor appointment."
        return _route("finish", awaiting=None, final_response=response)
    return None


def _heuristic_supervisor_route(state: GraphState) -> dict | None:
    user_input = (state.get("user_input") or "").strip()
    if not user_input:
        return None

    lowered = " ".join(user_input.lower().replace("'", "").split())
    awaiting = state.get("awaiting")
    profile_route = _fallback_profile_response(state)
    if profile_route:
        return profile_route

    if _looks_like_unsafe_non_medical(lowered):
        return _route(
            "finish",
            awaiting=None,
            chat_closed=False,
            final_response=(
                "I am only for health-related support, symptoms, and doctor appointments. "
                "If you need medical guidance, tell me your symptoms or ask about a doctor appointment."
            ),
        )

    if _looks_like_end_chat(lowered):
        return _route(
            "finish",
            awaiting=None,
            chat_closed=True,
            final_response="The chat is now closed. Take care, and you can start a new chat anytime if you need help again.",
        )

    if _looks_like_thanks(lowered):
        return _route(
            "finish",
            awaiting=None,
            chat_closed=False,
            final_response="You're welcome. Tell me your symptoms if you still need health-related support.",
        )

    # Remedy persisting: go find the right department immediately without an LLM call.
    if state.get("persisting") and not state.get("target_department") and state.get("symptoms"):
        return _route(
            "medical_rag",
            active_intent="direct_booking",
            intent="direct_booking",
            awaiting=None,
        )

    if awaiting == "end_confirmation":
        if _looks_like_new_symptoms(lowered):
            return _route(
                "triage_router",
                awaiting=None,
                intent=None,
                active_intent=None,
                doctor_options=[],
                slot_options=[],
                remedy_requested=False,
            )
        if _is_affirmative(lowered):
            return _route(
                "finish",
                awaiting=None,
                chat_closed=True,
                final_response="The chat is now closed. Take care, and you can start a new chat anytime if you need help again.",
            )
        if _looks_like_thanks(lowered):
            return _route(
                "finish",
                awaiting=None,
                chat_closed=False,
                final_response="You're welcome. Tell me your symptoms if you still need health-related support.",
            )
        return _route(
            "finish",
            awaiting="end_confirmation",
            chat_closed=False,
            final_response="reply yes to end the chat, or tell me your symptoms if you need more help.",
        )

    # Remedy-check: route to triage only for unambiguously NEW symptoms (fever,
    # vomiting, rash, etc.) — not for "pain" or "ache" which are almost always
    # the same existing symptom the patient is describing as persisting.
    _UNAMBIGUOUS_NEW_SYMPTOMS = frozenset({
        "fever", "vomiting", "vomit", "rash", "cough", "nausea", "diarrhea",
        "headache", "fatigue", "dizzy", "dizziness", "bleeding", "bleed",
        "swollen", "swelling", "cramp", "breathless", "itching",
    })
    if awaiting == "remedy_check" and any(term in lowered for term in _UNAMBIGUOUS_NEW_SYMPTOMS):
        return _route(
            "triage_router",
            awaiting=None,
            intent=None,
            active_intent=None,
            doctor_options=[],
            slot_options=[],
            remedy_requested=False,
        )

    # Patient responded to the post-checkup booking prompt.
    # Match on explicit awaiting OR on the combined state signals so that
    # routing still works even if awaiting drifted between turns.
    _in_booking_decision = awaiting == "booking_decision" or (
        state.get("checkup_summary_shown")
        and (_current_intent(state) == "direct_booking")
        and state.get("target_department")
        and not state.get("doctor_options")
    )
    if _in_booking_decision:
        if _is_affirmative(lowered):
            return _route(
                "appointment_booker",
                active_intent="direct_booking",
                intent="direct_booking",
                awaiting=None,
            )
        if _is_negative(lowered):
            return _route(
                "finish",
                awaiting=None,
                final_response=(
                    "No problem. If you change your mind or feel worse, feel free to start a new chat. "
                    "Take care and rest well!"
                ),
            )
        if awaiting == "booking_decision":
            # Ambiguous reply — re-ask
            return _route(
                "finish",
                awaiting="booking_decision",
                final_response="Would you like me to find available appointment slots for you? (yes / no)",
            )

    if awaiting == "conversation":
        if _looks_like_remedy_request(lowered) and state.get("symptoms"):
            return _route("remedy_agent", awaiting=None, remedy_requested=True)
        if _looks_like_general_doctor_request(lowered) and state.get("symptoms"):
            return _route(
                "medical_rag",
                active_intent="direct_booking",
                intent="direct_booking",
                awaiting=None,
            )
        if (
            not _looks_like_end_chat(lowered)
            and not _looks_like_thanks(lowered)
            and not _extract_requested_department(user_input)
            and not _looks_like_upcoming_booking_query(lowered)
            and not _looks_like_billing_request(lowered)
            and not _looks_like_clinical_note_query(lowered)
            and not _looks_like_add_symptoms_request(lowered)
        ):
            return _route("conversation_agent")

    if _looks_like_billing_request(lowered):
        return _route(
            "finish",
            awaiting=None,
            chat_closed=False,
            final_response="For billing or payment questions, please contact the hospital help desk. I can still help with symptoms or doctor appointments.",
        )

    if _looks_like_clinical_note_query(lowered):
        booking = _latest_booking(state)
        note = None
        if booking:
            note = booking.get("booking_note")
        if note:
            response = f"The clinical note forwarded to {booking.get('doctor') or booking.get('doctor_name') or 'your doctor'} was: {note}"
        else:
            response = "I could not find a forwarded clinical note in your current booking."
        return _route("finish", awaiting=None, chat_closed=False, final_response=response)

    if _looks_like_upcoming_booking_query(lowered):
        bookings = state.get("upcoming_bookings") or state.get("confirmed_bookings") or state.get("active_appointments") or []
        if bookings:
            lines = []
            for booking in bookings[:3]:
                doctor = booking.get("doctor") or booking.get("doctor_name") or "Doctor"
                time = booking.get("time") or booking.get("start_time") or "Unknown time"
                lines.append(f"{doctor} at {time}")
            response = "Your upcoming bookings are:\n" + "\n".join(lines)
        else:
            response = "I could not find any upcoming bookings right now."
        return _route("finish", awaiting=None, chat_closed=False, final_response=response)

    if _looks_like_add_symptoms_request(lowered) and (state.get("confirmed_booking") or state.get("upcoming_bookings")):
        return _route("remedy_agent", awaiting=None, remedy_requested=True)

    requested_department = _extract_requested_department(user_input)
    if requested_department:
        return _route(
            "appointment_booker",
            active_intent="direct_booking",
            intent="direct_booking",
            requested_department=requested_department,
            target_department=requested_department,
            awaiting=None,
        )

    if _looks_like_general_doctor_request(lowered) and state.get("symptoms"):
        return _route(
            "medical_rag",
            active_intent="direct_booking",
            intent="direct_booking",
            awaiting=None,
        )

    if _looks_like_remedy_request(lowered) and state.get("symptoms"):
        return _route("remedy_agent", awaiting=None, remedy_requested=True)

    # Fast-path for known booking sub-states: skip the LLM when the user is
    # simply picking from a menu we showed them. Special queries (upcoming
    # bookings, billing, etc.) are handled above and take priority.
    if awaiting in {
        "doctor_selection",
        "slot_selection",
        "cancellation_selection",
        "date_selection",
        "reschedule_selection",
        "reschedule_date_selection",
        "reschedule_slot_selection",
        "department_selection",
        "symptom_follow_up",
    }:
        return _route("appointment_booker")

    if awaiting == "appointment_resolver":
        return _route("appointment_resolver", awaiting="appointment_resolver")

    # Only re-triage if intake hasn't started yet (no questions asked).
    # If we're mid-intake (questions_asked is non-empty), fall through to the
    # LLM supervisor which has full context — prevents greeting resets.
    if (
        state.get("symptoms")
        and not state.get("target_department")
        and not state.get("requested_department")
        and not state.get("questions_asked")
    ):
        return _route(
            "triage_router",
            active_intent=None,
            intent=None,
            awaiting=None,
            doctor_options=[],
            slot_options=[],
        )

    return None


def _summarise_clinical_note(state: GraphState, user_text: str | None = None) -> str:
    # Prefer the pre-checkup report note generated during intake when available
    if state.get("pre_checkup_note"):
        extra = f"; Patient reply: {user_text.strip()}" if (user_text and user_text.strip()) else ""
        return str(state["pre_checkup_note"]) + extra

    symptoms = [str(item).strip() for item in (state.get("symptoms") or []) if str(item).strip()]
    collected = _current_facts(state)
    note_parts: list[str] = []

    if symptoms:
        note_parts.append(f"Reported symptoms: {', '.join(symptoms)}")

    for label, keys in (
        ("Duration", ("duration",)),
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
        note_parts.append(f"Recent remedy advice: {' '.join(str(state['remedy_text']).split())[:220]}")

    if user_text and user_text.strip():
        note_parts.append(f"Patient reply: {user_text.strip()}")

    if not note_parts:
        return "Patient requested the latest symptoms be forwarded to the upcoming doctor."

    return "Clinical note forwarded from chat: " + "; ".join(note_parts)


def _sync_state_aliases(updates: dict) -> dict:
    synced = dict(updates)

    if "session_id" in synced and "chat_session_id" not in synced:
        synced["chat_session_id"] = synced["session_id"]
    if "chat_session_id" in synced and "session_id" not in synced:
        synced["session_id"] = synced["chat_session_id"]

    if "active_intent" in synced and "intent" not in synced:
        synced["intent"] = synced["active_intent"]
    if "intent" in synced and "active_intent" not in synced:
        synced["active_intent"] = synced["intent"]

    if "collected_facts" in synced and "collected_data" not in synced:
        synced["collected_data"] = synced["collected_facts"]
    if "collected_data" in synced and "collected_facts" not in synced:
        synced["collected_facts"] = synced["collected_data"]
    if "collected_data" in synced and "collected_info" not in synced:
        synced["collected_info"] = synced["collected_data"]
    if "collected_info" in synced and "collected_data" not in synced:
        synced["collected_data"] = synced["collected_info"]

    if "upcoming_bookings" in synced:
        synced["confirmed_bookings"] = list(synced["upcoming_bookings"])
        synced["confirmed_booking"] = synced["upcoming_bookings"][-1] if synced["upcoming_bookings"] else None
        synced["active_appointments"] = synced.get("active_appointments") or list(synced["upcoming_bookings"])
    elif "confirmed_bookings" in synced:
        synced["upcoming_bookings"] = list(synced["confirmed_bookings"])
        synced["confirmed_booking"] = synced["confirmed_bookings"][-1] if synced["confirmed_bookings"] else None
        synced["active_appointments"] = synced.get("active_appointments") or list(synced["confirmed_bookings"])

    return synced


def _apply_extracted_facts(state: GraphState, extracted_facts: dict | None) -> dict:
    if not isinstance(extracted_facts, dict):
        return {}

    updates: dict = {}
    collected = _current_facts(state)
    upcoming_bookings = list(state.get("upcoming_bookings") or state.get("confirmed_bookings") or [])

    for key, value in extracted_facts.items():
        if value in (None, "", [], {}):
            continue
        if key == "note":
            continue
        if key in {"active_intent", "intent", "update_active_intent"}:
            updates["active_intent"] = value
            continue
        if key in {"collected_data", "collected_info"} and isinstance(value, dict):
            collected.update(value)
            continue
        if key == "upcoming_bookings" and isinstance(value, list):
            upcoming_bookings = _merge_unique_dicts(upcoming_bookings, value)
            continue
        if key == "symptoms" and isinstance(value, list):
            updates["symptoms"] = list(dict.fromkeys((state.get("symptoms") or []) + [str(item) for item in value if str(item).strip()]))
            continue
        collected[key] = value

    if collected:
        updates["collected_facts"] = collected
        updates["collected_data"] = collected
    if upcoming_bookings:
        updates["upcoming_bookings"] = upcoming_bookings

    return updates


def _temporal_context_injection(user_input: str) -> str:
    """
    Pure string-matching step — no LLM call.
    If the user's message contains time-sensitive terms, prepend a hidden
    temporal context block so downstream agents know the current time.
    """
    lowered = user_input.lower()
    if not any(term in lowered for term in _TEMPORAL_TERMS):
        return user_input
    now = datetime.now(timezone.utc)
    tag = (
        f"[Temporal Context: Current time is {now.strftime('%H:%M')} UTC, "
        f"Date is {now.strftime('%Y-%m-%d')}, "
        f"Day is {now.strftime('%A')}]\n"
    )
    return tag + user_input


def _generate_supervisor_decision(state: GraphState) -> CombinedSupervisorDecision | None:
    user_input = (state.get("user_input") or "").strip()
    if not user_input:
        return None

    user_input_with_context = _temporal_context_injection(user_input)
    dynamic_user_prompt = f"""{_state_summary(state)}
Latest user message: {user_input_with_context}"""

    raw_output = generate_router_text(
        system_prompt=STATIC_SUPERVISOR_PROMPT,
        user_prompt=dynamic_user_prompt,
        node_name="supervisor",
        chat_history=_current_messages(state),
        chat_summary=state.get("chat_summary"),
        include_history=True,
        history_turns=4,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
        raise_on_error=True,
    )

    clean_json = _clean_json(raw_output)
    print(f"Supervisor router JSON: {clean_json}")

    try:
        return parser.parse(clean_json)
    except Exception as exc:
        print(f"Supervisor router parse failed: {exc}")
        return None


def _fallback_route_after_node(state: GraphState) -> str:
    awaiting = state.get("awaiting")
    active_intent = _current_intent(state)

    if state.get("final_response"):
        return "finish"

    if state.get("chat_closed"):
        return "finish"

    if state.get("note_forwarded") and not awaiting:
        return "finish"

    if awaiting == "remedy_check":
        return "remedy_agent"

    if awaiting == "conversation":
        return "conversation_agent"

    if awaiting == "file_clarification":
        return "document_analyzer"

    if awaiting == "appointment_resolver":
        return "appointment_resolver"

    if awaiting in {
        "doctor_selection",
        "slot_selection",
        "cancellation_selection",
        "date_selection",
        "reschedule_selection",
        "reschedule_date_selection",
        "reschedule_slot_selection",
        "department_selection",
        "symptom_follow_up",
        "booking_decision",
    }:
        return "appointment_booker"

    if active_intent == "direct_booking":
        if state.get("target_department") or state.get("requested_department") or state.get("requested_doctor_name"):
            return "appointment_booker"
        return "medical_rag"

    # When the remedy didn't help, skip back to RAG for department matching.
    if state.get("persisting") and not state.get("target_department"):
        return "medical_rag"

    if active_intent == "triage_symptoms":
        if state.get("remedy_requested") or state.get("remedy_given"):
            # First visit (no prior booking): show pre-checkup summary + department match
            # instead of giving home remedies. Remedy path is kept only for patients
            # who already have a booking and want to forward new symptoms.
            if not state.get("checkup_summary_shown") and not _latest_booking(state):
                return "checkup_report"
            return "remedy_agent"
        return "conversation_agent"

    if state.get("symptoms"):
        return "conversation_agent"

    return "finish"


def continue_current_node(state: GraphState):
    user_input = (state.get("user_input") or "").strip()
    awaiting = state.get("awaiting")
    history = list(state.get("messages") or state.get("conversation_history") or [])

    if awaiting == "file_clarification":
        response = "I see you uploaded a document. Is this regarding your current symptom, or is this a completely new issue?"
        history.append({"role": "assistant", "text": response})
        return {
            "awaiting": "file_clarification",
            "conversation_history": history,
            "messages": history[-10:],
            "final_response": response,
        }

    if awaiting == "remedy_check" and user_input and _is_affirmative(user_input):
        booking = _latest_booking(state)
        if not booking:
            response = (
                "I can prepare the clinical note, but I could not find an upcoming booking to attach it to."
            )
            history.append({"role": "assistant", "text": response})
            return {
                "awaiting": None,
                "note_forwarded": False,
                "conversation_history": history,
                "messages": history[-10:],
                "final_response": response,
            }

        booking_note = _summarise_clinical_note(state, user_input)
        updated_booking = update_booking_note(
            booking_id=str(booking["booking_id"]),
            patient_id=str(state.get("patient_id") or ""),
            booking_note=booking_note,
        )

        if not updated_booking:
            response = (
                "I could not attach the clinical note to your upcoming appointment right now."
            )
            history.append({"role": "assistant", "text": response})
            return {
                "awaiting": None,
                "note_forwarded": False,
                "conversation_history": history,
                "messages": history[-10:],
                "final_response": response,
            }

        upcoming_bookings = list(state.get("upcoming_bookings") or state.get("confirmed_bookings") or [])
        synced_bookings = []
        for item in upcoming_bookings:
            if not isinstance(item, dict):
                continue
            if item.get("booking_id") == updated_booking.get("booking_id") or item.get("slot_id") == updated_booking.get("slot_id"):
                synced_bookings.append(updated_booking)
            else:
                synced_bookings.append(item)
        if not synced_bookings:
            synced_bookings = [updated_booking]

        response = (
            f"I've forwarded the note to {updated_booking['doctor']} for your upcoming appointment on {updated_booking['time']}."
        )
        history.append({"role": "assistant", "text": response})
        return _sync_state_aliases(
            {
                "awaiting": None,
                "note_forwarded": True,
                "conversation_history": history,
                "messages": history[-10:],
                "upcoming_bookings": synced_bookings,
                "active_appointments": synced_bookings,
                "final_response": response,
            }
        )

    return {"awaiting": None, "conversation_history": history, "messages": history[-10:]}


def general_qa_node(state: GraphState):
    user_text = (state.get("user_input") or "").strip()
    history = list(state.get("messages") or state.get("conversation_history") or [])

    dynamic_user_prompt = f"""Current date: {date.today().isoformat()}
{_state_summary(state)}
Latest user message: {user_text}
Answer the user's hospital-related question clearly, safely, and concisely. If the question is medical and urgent, advise appropriate escalation."""

    response = (
        generate_text(
        system_prompt=(
            "You are a helpful hospital assistant answering general questions, policies, and simple medical explanations. "
            "Be careful, concise, and do not invent facts."
        ),
        user_prompt=dynamic_user_prompt,
        node_name="general_qa",
        chat_history=history,
        chat_summary=state.get("chat_summary"),
        include_history=True,
        history_turns=4,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    ).strip()

    if not response:
        response = "I can help with general hospital questions. Please tell me what you need."

    history.append({"role": "assistant", "text": response})
    return {
        "conversation_history": history,
        "messages": history[-10:],
        "final_response": response,
        "awaiting": state.get("awaiting"),
    }


def supervisor_node(state: GraphState):
    if state.get("final_response"):
        return _route("finish")

    # After a node completes and returns to supervisor, use fallback routing
    # instead of re-running heuristics on the stale user_input. This prevents
    # loops where medical_rag re-routes to itself because the heuristic still
    # sees "book appointment" in user_input even after the department was found.
    if state.get("supervisor_checked_input"):
        return _route(_fallback_route_after_node(state))

    user_input = state.get("user_input") or ""
    heuristic_route = _heuristic_supervisor_route(state)
    if heuristic_route:
        return heuristic_route

    if _looks_like_end_chat(user_input):
        return _route(
            "finish",
            awaiting=None,
            chat_closed=True,
            final_response="The chat is now closed. Take care, and you can start a new chat anytime if you need help again.",
        )

    if _looks_like_thanks(user_input) and state.get("note_forwarded"):
        return _route(
            "finish",
            awaiting=None,
            chat_closed=True,
            final_response="You're welcome. Take care, and please reach out again if you need anything else.",
        )

    if state.get("pending_file_data"):
        return _route("document_analyzer")

    if _should_route_to_resolver(state, user_input):
        return _route("appointment_resolver", awaiting="appointment_resolver")

    if state.get("awaiting") == "remedy_check" and _is_affirmative(user_input):
        return _route("continue_current")

    try:
        decision = _generate_supervisor_decision(state)
    except Exception as exc:
        print(f"Supervisor router hard failure: {exc}")
        response = "Currently we are facing heavy traffic, Please come back later"
        return _route(
            "finish",
            awaiting="error_recovery",
            chat_closed=False,
            conversation_history=[*list(state.get("conversation_history") or []), {"role": "assistant", "text": response}],
            messages=[*list(state.get("messages") or []), {"role": "assistant", "text": response}][-10:],
            final_response=response,
        )

    current_intent = _current_intent(state)

    if not decision:
        return _route(_fallback_route_after_node(state))

    updates = {
        "user_action_summary": decision.user_action_summary,
    }

    if decision.update_active_intent is None:
        updates["active_intent"] = current_intent
    else:
        updates["active_intent"] = decision.update_active_intent

    updates.update(_apply_extracted_facts(state, decision.extracted_facts))
    updates = _sync_state_aliases(updates)

    next_agent = decision.next_agent

    if next_agent == "continue_current":
        if state.get("awaiting") == "remedy_check" and _is_affirmative(state.get("user_input") or ""):
            return _route("continue_current", **updates)
        return _route("continue_current", **updates)

    if next_agent == "general_qa":
        return _route("general_qa", **updates)

    if next_agent == "triage_router":
        updates.update(
            {
                "awaiting": None,
                "remedy_requested": False,
                "booking_declined": None,
                "candidate_departments": [],
                "doctor_options": [],
                "slot_options": [],
                "reschedule_options": [],
                "reschedule_date_options": [],
                "reschedule_slot_options": [],
                "selected_booking_id": None,
                "selected_doctor_id": None,
                "selected_doctor_name": None,
                "selected_slot_id": None,
            }
        )
        return _route("triage_router", **updates)

    if next_agent == "conversation_agent":
        return _route("conversation_agent", **updates)

    if next_agent == "remedy_agent":
        updates.update({"awaiting": None, "remedy_requested": True})
        return _route("remedy_agent", **updates)

    if next_agent == "medical_rag":
        return _route("medical_rag", **updates)

    if next_agent == "appointment_booker":
        if (
            not state.get("target_department")
            and not state.get("requested_department")
            and not state.get("requested_doctor_name")
        ):
            return _route("medical_rag", **updates)
        updates["active_intent"] = updates.get("active_intent") or "direct_booking"
        updates["intent"] = updates["active_intent"]
        updates["awaiting"] = None
        return _route("appointment_booker", **updates)

    if next_agent == "appointment_resolver":
        updates["awaiting"] = "appointment_resolver"
        return _route("appointment_resolver", **updates)

    if next_agent == "document_analyzer":
        updates["awaiting"] = "file_clarification"
        return _route("document_analyzer", **updates)

    if next_agent == "finish":
        updates.update({"awaiting": None, "chat_closed": True})
        return _route("finish", **updates)

    return _route("finish", **updates)


def route_from_supervisor(state: GraphState):
    return state.get("next_agent", "finish")
