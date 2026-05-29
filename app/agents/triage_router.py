from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import PatientExtraction
from app.agents.state import GraphState
from app.inference.llm import generate_text


parser = PydanticOutputParser(pydantic_object=PatientExtraction)


def _clean_json(raw_output: str) -> str:
    return raw_output.replace("```json", "").replace("```", "").strip()


def _build_history_text(history: list[dict]) -> str:
    lines = []
    for entry in history:
        role = "Patient" if entry["role"] == "patient" else "Assistant"
        lines.append(f"{role}: {entry['text']}")
    return "\n".join(lines)


def _merge_symptoms(existing: list[str], extracted: list[str]) -> list[str]:
    merged = []
    for symptom in [*existing, *extracted]:
        symptom = symptom.strip() if isinstance(symptom, str) else ""
        if symptom and symptom not in merged:
            merged.append(symptom)
    return merged


def _max_severity(existing: str | None, extracted: str) -> str:
    order = {"mild": 0, "moderate": 1, "severe": 2, "emergency": 3}
    if not existing:
        return extracted
    return existing if order.get(existing, 0) >= order.get(extracted, 0) else extracted


def _extraction_state(state: GraphState, updated_history: list[dict], extracted: PatientExtraction):
    symptoms = _merge_symptoms(state.get("symptoms") or [], extracted.symptoms)
    severity = _max_severity(state.get("severity"), extracted.severity)
    return {
        "conversation_history": updated_history,
        "intent": extracted.intent,
        "symptoms": symptoms,
        "severity": severity,
        "remedy_given": False,
        "remedy_requested": False,
        "collected_info": {},
        "questions_asked": [],
    }


def triage_router_node(state: GraphState):
    history = state.get("conversation_history") or []
    user_input = state["user_input"]
    updated_history = list(history)
    updated_history.append({"role": "patient", "text": user_input})

    prompt = f"""
You are the Triage Router Agent for a hospital portal.

Understand the patient's intent and symptoms from natural language. Do not rely on
keyword matching. Infer meaning from the whole message and prior conversation.

Intent meanings:
- greeting: the latest message is only a greeting or social opener, with no care request.
- triage_symptoms: the patient describes symptoms, discomfort, injury, illness, or asks for help/remedy.
- direct_booking: the patient wants a doctor, specialist, department, appointment, or booking.
- unclear: you cannot safely infer a medical or booking intent.

Severity meanings:
- emergency: potentially life-threatening or self-harm risk; needs immediate emergency care.
- severe: should be seen urgently within hours.
- moderate: needs medical review but is not immediately dangerous.
- mild: minor or non-urgent.

Previous conversation:
{_build_history_text(history) if history else "None"}

Latest patient message:
{user_input}

Extract clean symptoms in the patient's own medical meaning. For greetings or unclear
messages, return an empty symptoms list and mild severity unless prior context changes that.

Return only JSON:
{parser.get_format_instructions()}
""".strip()

    raw_output = generate_text(prompt)
    clean_json = _clean_json(raw_output)
    print(f"Triage Router clean JSON: {clean_json}")

    try:
        extracted = parser.parse(clean_json)
    except Exception as exc:
        print(f"Triage parser failed: {exc}")
        response = (
            "I could not reliably understand what you need yet. Could you describe your "
            "symptoms, or tell me if you want to book an appointment?"
        )
        updated_history.append({"role": "assistant", "text": response})
        return {
            "conversation_history": updated_history,
            "intent": "unclear",
            "symptoms": state.get("symptoms") or [],
            "severity": state.get("severity") or "mild",
            "final_response": response,
        }

    if extracted.intent == "greeting":
        greeting = (
            "Hello, welcome to the hospital assistant. How can I help you today? "
            "You can describe your symptoms or tell me if you want to book an appointment."
        )
        updated_history.append({"role": "assistant", "text": greeting})
        print("Triage Router detected greeting only, responding with greeting.")
        return {
            "conversation_history": updated_history,
            "greeted": True,
            "final_response": greeting,
        }

    if extracted.intent == "unclear":
        response = (
            "I want to make sure I understand. Are you describing symptoms, or would "
            "you like help booking an appointment?"
        )
        updated_history.append({"role": "assistant", "text": response})
        return {
            "conversation_history": updated_history,
            "intent": "unclear",
            "symptoms": state.get("symptoms") or [],
            "severity": state.get("severity") or extracted.severity,
            "final_response": response,
        }

    return _extraction_state(state, updated_history, extracted)
