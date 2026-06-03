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

    known_fields = {
        key
        for key in SUFFICIENT_INTAKE_FIELDS
        if collected.get(key)
    }

    return (
        has_duration
        and has_location
        and has_pattern
        and has_cause
        and has_context
    ) or len(known_fields) >= 6


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
- If the patient now wants a doctor/appointment instead of continuing intake, set intent to direct_booking.
- If there is enough context to give tailored care guidance safely, set has_enough_info to true.

Return only JSON:
{parser.get_format_instructions()}
""".strip()

    raw_output = generate_text(prompt)
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

    if decision.has_enough_info or _has_sufficient_intake_context(
        merged_collected,
        updated_questions,
    ):
        return {
            "conversation_history": updated_history,
            "collected_info": merged_collected,
            "questions_asked": updated_questions,
            "awaiting": None,
        }

    question = decision.next_question or "Can you describe your symptoms in a bit more detail?"
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
