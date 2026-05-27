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

DOCTOR_REQUEST_WORDS = {
    "doctor",
    "appointment",
    "book",
    "hospital",
    "clinic",
    "specialist",
}

DURATION_WORDS = {
    "today",
    "yesterday",
    "last night",
    "morning",
    "evening",
    "hour",
    "hours",
    "day",
    "days",
    "week",
    "weeks",
    "month",
    "months",
    "since",
}

CAUSE_WORDS = {
    "fall",
    "fell",
    "injury",
    "hurt",
    "hit",
    "accident",
    "slipped",
    "bed",
    "sudden",
    "gradual",
    "allergy",
    "trigger",
}


def _build_history_text(history: list[dict]) -> str:
    lines = []
    for entry in history:
        role = "Patient" if entry["role"] == "patient" else "Assistant"
        lines.append(f"{role}: {entry['text']}")
    return "\n".join(lines)


def _patient_wants_doctor(text: str) -> bool:
    normalized = text.lower()
    return any(word in normalized for word in DOCTOR_REQUEST_WORDS)


def _looks_like_duration(text: str) -> bool:
    normalized = text.lower()
    return any(word in normalized for word in DURATION_WORDS)


def _looks_like_cause(text: str) -> bool:
    normalized = text.lower()
    return any(word in normalized for word in CAUSE_WORDS)


def _merge_patient_answer(state: GraphState, collected: dict) -> dict:
    merged = dict(collected)
    user_text = state.get("user_input", "").strip()
    if not user_text:
        return merged

    questions_asked = state.get("questions_asked") or []
    last_question = questions_asked[-1].lower() if questions_asked else ""

    captured_duration = False
    if not merged.get("duration") and (
        "how long" in last_question
        or "when" in last_question
        or _looks_like_duration(user_text)
    ):
        merged["duration"] = user_text
        captured_duration = True

    if not (merged.get("cause") or merged.get("trigger") or merged.get("onset")) and (
        (
            not captured_duration
            and (
                "started" in last_question
                or "trigger" in last_question
                or "caused" in last_question
                or "injury" in last_question
            )
        )
        or _looks_like_cause(user_text)
    ):
        merged["cause"] = user_text

    symptoms = state.get("symptoms") or []
    if symptoms and not merged.get("location"):
        if any("chest" in symptom.lower() for symptom in symptoms):
            merged["location"] = "chest"

    return merged


def _has_enough_info(state: GraphState, collected: dict) -> bool:
    if not state.get("symptoms"):
        return False

    has_duration = bool(collected.get("duration"))
    has_cause = bool(
        collected.get("cause")
        or collected.get("trigger")
        or collected.get("onset")
    )
    questions_asked = state.get("questions_asked") or []

    return (has_duration and has_cause) or len(questions_asked) >= 3


def _next_fast_question(collected: dict) -> str | None:
    if not collected.get("duration"):
        return "How long have you been experiencing this?"

    if not (
        collected.get("cause")
        or collected.get("trigger")
        or collected.get("onset")
    ):
        return (
            "Did this start suddenly, gradually, after an injury, "
            "or after something like an allergy?"
        )

    return None


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

    return [
        symptom
        for symptom in unique
        if not (
            symptom.lower() in {"pain", "tightness", "breath"}
            and any(symptom.lower() in other.lower() for other in unique if other != symptom)
        )
    ] or unique


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

    if _patient_wants_doctor(user_text):
        return {
            "conversation_history": updated_history,
            "intent": "direct_booking",
            "collected_info": existing_collected,
            "questions_asked": questions_asked,
            "awaiting": None,
        }

    collected = _merge_patient_answer(state, existing_collected)

    if _has_enough_info(state, collected):
        return {
            "conversation_history": updated_history,
            "collected_info": collected,
            "questions_asked": questions_asked,
            "awaiting": None,
        }

    history_text = _build_history_text(updated_history)
    collected_text = json.dumps(collected, indent=2) if collected else "{}"
    questions_text = "\n".join(f"- {q}" for q in questions_asked) if questions_asked else "None yet"

    prompt = f"""
You are a warm, empathetic hospital intake assistant having a real conversation with a patient.

Your job: gather enough information to give a personalised remedy and, if needed, refer them to a doctor.

Current known symptoms: {', '.join(symptoms) if symptoms else 'unclear'}
Estimated severity: {severity}

Full conversation so far:
{history_text if history_text else "Just started."}

Structured info collected so far:
{collected_text}

Questions already asked:
{questions_text}

You need to find out only what is still unknown:
1. How long have they had this problem? (duration)
2. How it started: sudden onset, gradual, after an injury, allergic reaction, or recurring.
3. Where exactly the problem is located, if relevant.
4. Whether it is constant or comes and goes.
5. Any allergies, existing conditions, medications, or associated symptoms.

IMPORTANT rules:
- Ask ONE question at a time.
- Never ask something already answered in the conversation or structured info.
- If duration and cause/trigger are known, set has_enough_info to true.

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
        fallback_q = _next_fast_question(collected) or (
            "Could you tell me a bit more about when this started and what might have caused it?"
        )
        fallback_q, greeted_now = _with_initial_greeting(state, fallback_q)
        updated_history.append({"role": "assistant", "text": fallback_q})
        return {
            "conversation_history": updated_history,
            "collected_info": collected,
            "questions_asked": questions_asked + [fallback_q],
            "greeted": state.get("greeted") or greeted_now,
            "awaiting": "conversation",
            "final_response": fallback_q,
        }

    merged_collected = {**collected, **decision.collected_info}
    updated_questions = list(questions_asked)

    if decision.has_enough_info or _has_enough_info(state, merged_collected):
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
