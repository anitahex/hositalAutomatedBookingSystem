"""
Conversation Agent
------------------
Asks dynamic, patient-specific follow-up questions until enough context is
available for a remedy and, if needed, referral to a doctor.
"""

import json

from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import ConversationDecision
from app.agents.state import GraphState
from app.inference.llm import generate_text


parser = PydanticOutputParser(pydantic_object=ConversationDecision)

MAX_INTAKE_QUESTIONS = 8
OPEN_ENDED_FALLBACK = "What feels most important about this symptom that I have not asked yet?"
SUFFICIENT_INTAKE_FIELDS = {
    "duration",
    "location",
    "severity_pattern",
    "cause",
    "trigger",
    "associated_symptoms",
    "existing_conditions",
    "lifestyle",
    "daily_activity",
}


def _build_history_text(history: list[dict]) -> str:
    lines = []
    for entry in history:
        role = "Patient" if entry["role"] == "patient" else "Assistant"
        lines.append(f"{role}: {entry['text']}")
    return "\n".join(lines)


def _with_initial_greeting(state: GraphState, question: str) -> tuple[str, bool]:
    if state.get("greeted"):
        return question, False

    symptoms = _display_symptoms(state.get("symptoms") or [])
    symptom_text = ", ".join(symptoms) if symptoms else "what you are experiencing"
    greeting = (
        f"Hello, I am here to help. I understand you mentioned {symptom_text}. "
        f"{question}"
    )
    return greeting, True


def _display_symptoms(symptoms: list[str]) -> list[str]:
    unique = []
    for symptom in symptoms:
        if symptom not in unique:
            unique.append(symptom)
    return unique


def _normalise_question(text: str) -> str:
    return " ".join(text.lower().replace("?", " ").replace(",", " ").split())


def _asked_about_duration_count(questions_asked: list[str]) -> int:
    markers = ("how long", "since when", "when did", "duration", "started", "start")
    return sum(
        1
        for question in questions_asked
        if any(marker in _normalise_question(question) for marker in markers)
    )


def _asked_open_ended_fallback(questions_asked: list[str]) -> bool:
    fallback = _normalise_question(OPEN_ENDED_FALLBACK)
    return any(_normalise_question(question) == fallback for question in questions_asked)


def _looks_like_no_more_info(text: str) -> bool:
    normalised = _normalise_question(text)
    if not normalised:
        return False

    no_more_phrases = (
        "nothing more",
        "nothing else",
        "no more",
        "there is nothing more",
        "nothing as such",
        "no other symptoms",
        "no other symptom",
        "thats all",
        "that's all",
    )
    return any(phrase in normalised for phrase in no_more_phrases)


def _known_intake_field_count(collected: dict) -> int:
    return len(
        {
            key
            for key in SUFFICIENT_INTAKE_FIELDS
            if collected.get(key)
        }
    )


def _looks_like_repeated_question(question: str, questions_asked: list[str]) -> bool:
    normalised = _normalise_question(question)
    if not normalised:
        return False

    for previous in questions_asked:
        previous_normalised = _normalise_question(previous)
        if normalised == previous_normalised:
            return True
        if normalised in previous_normalised or previous_normalised in normalised:
            return True

    duration_markers = ("how long", "since when", "when did", "duration", "started", "start")
    if (
        any(marker in normalised for marker in duration_markers)
        and _asked_about_duration_count(questions_asked) >= 1
    ):
        return True

    return False


def _next_distinct_question(collected: dict, questions_asked: list[str]) -> str:
    candidates = []
    if not collected.get("location"):
        candidates.append("Where exactly do you feel it most strongly?")
    if not (collected.get("severity_pattern") or collected.get("pattern")):
        candidates.append("Is it constant, or does it come and go?")
    if not (collected.get("cause") or collected.get("trigger") or collected.get("onset")):
        candidates.append("Did anything seem to trigger it, such as activity, injury, food, or stress?")
    if not collected.get("associated_symptoms"):
        candidates.append("Are you noticing anything else with it, like numbness, swelling, fever, or weakness?")
    if not (collected.get("medications") or collected.get("allergies") or collected.get("existing_conditions")):
        candidates.append("Are you taking any medicines, or do you have allergies or existing conditions I should know about?")

    for candidate in candidates:
        if not _looks_like_repeated_question(candidate, questions_asked):
            return candidate

    return OPEN_ENDED_FALLBACK


def _has_sufficient_intake_context(collected: dict, questions_asked: list[str]) -> bool:
    if len(questions_asked) >= MAX_INTAKE_QUESTIONS:
        return True

    has_duration = bool(collected.get("duration"))
    has_location = bool(collected.get("location"))
    has_pattern = bool(collected.get("severity_pattern") or collected.get("pattern"))
    has_cause = bool(
        collected.get("cause")
        or collected.get("trigger")
        or collected.get("onset")
    )
    has_context = any(
        collected.get(key)
        for key in (
            "associated_symptoms",
            "existing_conditions",
            "medications",
            "allergies",
            "lifestyle",
            "daily_activity",
            "history",
        )
    )

    known_field_count = _known_intake_field_count(collected)

    if _asked_open_ended_fallback(questions_asked) and known_field_count >= 4:
        return True

    if not has_duration and _asked_about_duration_count(questions_asked) >= 2 and known_field_count >= 4:
        return True

    return (
        has_duration
        and has_location
        and has_pattern
        and has_cause
        and has_context
    ) or known_field_count >= 6


def conversation_agent_node(state: GraphState):
    history = state.get("conversation_history") or []
    symptoms = state.get("symptoms") or []
    severity = state.get("severity") or "moderate"
    existing_collected = state.get("collected_info") or {}
    questions_asked = state.get("questions_asked") or []
    user_text = state.get("user_input", "").strip()

    updated_history = list(history)
    if state.get("awaiting") == "conversation" and user_text:
        updated_history.append({"role": "patient", "text": user_text})

    history_text = _build_history_text(updated_history)
    collected_text = json.dumps(existing_collected, indent=2) if existing_collected else "{}"
    questions_text = "\n".join(f"- {q}" for q in questions_asked) if questions_asked else "None yet"

    prompt = f"""
You are a warm, empathetic hospital intake assistant having a real conversation with a patient.

Your job: gather enough information to give a personalised remedy and, if needed, refer them to a doctor.

Current known symptoms: {', '.join(symptoms) if symptoms else 'unclear'}
Estimated severity: {severity}

Patient profile from hospital records:
{state.get("patient_profile") or "Unknown"}

Active appointments:
{state.get("active_appointments") or state.get("confirmed_bookings") or []}

Full conversation so far:
{history_text if history_text else "Just started."}

Structured info collected so far:
{collected_text}

Questions already asked:
{questions_text}

Use the full conversation to infer what is known and what is still unknown.
Important intake details usually include duration, onset/trigger/cause, location,
pattern, associated symptoms, allergies, existing conditions, and medications.

IMPORTANT rules:
- Ask ONE question at a time.
- Never ask something already answered in the conversation or structured info.
- Do not repeat a duration/time question if you already asked it. If the patient
  does not provide duration, ask about another clinically useful detail instead.
- If the patient now wants a doctor/appointment instead of continuing intake, set intent to direct_booking.
- If there is enough context to give tailored care guidance safely, set has_enough_info to true.

Return only JSON:
{parser.get_format_instructions()}
""".strip()
    print(f"Conversation Agent prompt: {prompt}")
    raw_output = generate_text(
        prompt,
        node_name="conversation_agent",
        chat_history=state.get("conversation_history"),
        chat_summary=state.get("chat_summary"),
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    clean_json = raw_output.replace("```json", "").replace("```", "").strip()
    print(f"Conversation Agent clean JSON: {clean_json}")

    try:
        decision = parser.parse(clean_json)
        print(f"Conversation Agent decision: {decision}")
    except Exception as exc:
        print(f"Conversation parser failed: {exc}")
        fallback_q = "Could you tell me a little more about what you are feeling and when it started?"
        fallback_q, greeted_now = _with_initial_greeting(state, fallback_q)
        updated_history.append({"role": "assistant", "text": fallback_q})
        return {
            "conversation_history": updated_history,
            "collected_info": existing_collected,
            "questions_asked": questions_asked + [fallback_q],
            "greeted": state.get("greeted") or greeted_now,
            "awaiting": "conversation",
            "final_response": fallback_q,
        }

    if decision.intent == "direct_booking":
        return {
            "conversation_history": updated_history,
            "intent": "direct_booking",
            "collected_info": {**existing_collected, **decision.collected_info},
            "questions_asked": questions_asked,
            "awaiting": None,
        }

    merged_collected = {**existing_collected, **decision.collected_info}
    updated_questions = list(questions_asked)

    if (
        _asked_open_ended_fallback(updated_questions)
        and user_text
        and _looks_like_no_more_info(user_text)
    ):
        return {
            "conversation_history": updated_history,
            "collected_info": merged_collected,
            "questions_asked": updated_questions,
            "awaiting": None,
            "remedy_requested": True,
        }

    if decision.has_enough_info or _has_sufficient_intake_context(
        merged_collected,
        updated_questions,
    ):
        return {
            "conversation_history": updated_history,
            "collected_info": merged_collected,
            "questions_asked": updated_questions,
            "awaiting": None,
            "remedy_requested": True,
        }

    question = decision.next_question or "Can you describe your symptoms in a bit more detail?"
    if _looks_like_repeated_question(question, updated_questions):
        question = _next_distinct_question(merged_collected, updated_questions)
    question, greeted_now = _with_initial_greeting(state, question)
    updated_history.append({"role": "assistant", "text": question})
    updated_questions.append(question)

    return {
        "conversation_history": updated_history,
        "collected_info": merged_collected,
        "questions_asked": updated_questions,
        "greeted": state.get("greeted") or greeted_now,
        "awaiting": "conversation",
        "final_response": question,
    }
