from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import PatientExtraction
from app.agents.state import GraphState
from app.inference.llm import generate_text


parser = PydanticOutputParser(pydantic_object=PatientExtraction)

GREETING_WORDS = {
    "hi",
    "hello",
    "hey",
    "hey hi",
    "good morning",
    "good afternoon",
    "good evening",
}

SYMPTOM_HINTS = {
    "ache",
    "allergy",
    "bleeding",
    "breath",
    "cough",
    "dizzy",
    "dizziness",
    "doctor",
    "fever",
    "headache",
    "hurt",
    "nausea",
    "pain",
    "rash",
    "sick",
    "tight",
    "vomit",
    "weak",
}

SYMPTOM_ALIASES = {
    "allergy": ["allergy", "allergic"],
    "bleeding": ["bleeding", "blood"],
    "breathlessness": ["breathless", "shortness of breath", "cannot breathe"],
    "chest pain": ["chest pain"],
    "chest tightness": ["chest tightness", "chest is tight", "tight chest"],
    "cough": ["cough"],
    "dizziness": ["dizzy", "dizziness"],
    "fever": ["fever", "temperature"],
    "headache": ["headache", "head ache", "head pain", "pain in the head"],
    "knee pain": ["knee pain", "knees hurt", "knee hurts", "pain in knee", "pain in my knee"],
    "nausea": ["nausea", "nauseous"],
    "pain": ["pain", "ache", "hurt"],
    "rash": ["rash"],
    "vomiting": ["vomit", "vomiting"],
    "weakness": ["weak", "weakness"],
}

BODY_PARTS = {
    "ankle",
    "arm",
    "back",
    "calf",
    "chest",
    "elbow",
    "foot",
    "hand",
    "hip",
    "knee",
    "leg",
    "neck",
    "shoulder",
    "thigh",
    "wrist",
}

DIRECT_BOOKING_WORDS = {
    "appointment",
    "book",
    "booking",
    "doctor",
    "specialist",
}

EMERGENCY_TERMS = {
    "cannot breathe",
    "crushing chest pain",
    "major bleeding",
    "stroke",
    "suicidal",
    "unconscious",
}

SEVERE_TERMS = {
    "chest pain",
    "chest tightness",
    "severe",
    "shortness of breath",
    "worse",
    "worsening",
    "immediate",
    "immediately",
}


def _is_greeting_only(text: str) -> bool:
    normalized = " ".join(text.lower().strip().split())
    if not normalized:
        return False
    if any(hint in normalized for hint in SYMPTOM_HINTS):
        return False
    return normalized in GREETING_WORDS or all(part in GREETING_WORDS for part in normalized.split())


def _fast_extract(text: str):
    normalized = text.lower()
    symptom_matches = []

    for body_part in BODY_PARTS:
        for alias in (
            f"{body_part} pain",
            f"pain in {body_part}",
            f"pain in my {body_part}",
            f"{body_part} hurts",
            f"{body_part} hurt",
            f"{body_part} ache",
        ):
            position = normalized.find(alias)
            if position != -1:
                symptom_matches.append((position, f"{body_part} pain"))
                break

    for symptom, aliases in SYMPTOM_ALIASES.items():
        positions = [
            normalized.find(alias)
            for alias in aliases
            if alias in normalized
        ]
        if positions:
            symptom_matches.append((min(positions), symptom))

    symptoms = [
        symptom
        for _, symptom in sorted(symptom_matches, key=lambda match: match[0])
    ]
    if "pain" in symptoms and len(symptoms) > 1:
        symptoms = [symptom for symptom in symptoms if symptom != "pain"]

    wants_booking = any(word in normalized for word in DIRECT_BOOKING_WORDS)
    if not symptoms and not wants_booking:
        return None

    if any(term in normalized for term in EMERGENCY_TERMS):
        severity = "emergency"
    elif any(term in normalized for term in SEVERE_TERMS) or any(
        symptom in {"breathlessness", "chest pain", "chest tightness"}
        for symptom in symptoms
    ):
        severity = "severe"
    elif symptoms:
        severity = "moderate"
    else:
        severity = "mild"

    return {
        "intent": "direct_booking" if wants_booking else "triage_symptoms",
        "symptoms": symptoms,
        "severity": severity,
    }


def _merge_symptoms(existing: list[str], extracted: list[str]) -> list[str]:
    merged = []
    for symptom in [*existing, *extracted]:
        if symptom and symptom not in merged:
            merged.append(symptom)
    return merged


def _max_severity(existing: str | None, extracted: str) -> str:
    order = {"mild": 0, "moderate": 1, "severe": 2, "emergency": 3}
    if not existing:
        return extracted
    return existing if order.get(existing, 0) >= order.get(extracted, 0) else extracted


def _extraction_state(state: GraphState, updated_history: list[dict], extracted: dict):
    symptoms = _merge_symptoms(state.get("symptoms") or [], extracted["symptoms"])
    severity = _max_severity(state.get("severity"), extracted["severity"])
    return {
        "conversation_history": updated_history,
        "intent": extracted["intent"],
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

    if _is_greeting_only(user_input):
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

    # Build conversation context for the LLM
    history_text = ""
    if history:
        lines = []
        for entry in history:
            role = "Patient" if entry["role"] == "patient" else "Assistant"
            lines.append(f"{role}: {entry['text']}")
        history_text = "\n".join(lines)

    prompt = f"""
You are the Triage Router Agent for a hospital portal.

Return only JSON that follows these instructions:
{parser.get_format_instructions()}

Severity rules:
- emergency: life-threatening symptoms such as crushing chest pain, severe breathing trouble,
  stroke signs, unconsciousness, major bleeding, suicidal intent.
- severe: serious symptoms that should be seen urgently within hours.
- moderate: uncomfortable or persistent symptoms that need medical review.
- mild: minor or non-urgent symptoms.

Previous conversation:
{history_text if history_text else "None"}

Latest patient message:
{user_input}

Extract or update symptoms and severity based on everything said so far.
""".strip()

    raw_output = generate_text(prompt)
    clean_json = raw_output.replace("```json", "").replace("```", "").strip()
    print(f"Triage Router clean JSON: {clean_json}")

    try:
        extracted = parser.parse(clean_json)
    except Exception as exc:
        print(f"Triage parser failed: {exc}")
        fast_extracted = _fast_extract(user_input)
        if fast_extracted:
            print(f"Triage Router fallback extraction: {fast_extracted}")
            return _extraction_state(state, updated_history, fast_extracted)

        return {
            "conversation_history": updated_history,
            "intent": "triage_symptoms",
            "symptoms": state.get("symptoms") or [],
            "severity": state.get("severity") or "moderate",
            "final_response": (
                "I could not reliably understand your symptoms. "
                "Could you describe what you are feeling, when it started, "
                "and how severe it feels?"
            ),
        }

    return _extraction_state(
        state,
        updated_history,
        {
            "intent": extracted.intent,
            "symptoms": extracted.symptoms,
            "severity": extracted.severity,
        },
    )
