import json
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
OPENROUTER_ROUTER_MODEL = os.getenv("OPENROUTER_ROUTER_MODEL", OPENROUTER_MODEL)
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_ROUTER_TIMEOUT_SECONDS = float(
    os.getenv("OPENROUTER_ROUTER_TIMEOUT_SECONDS", "4")
)

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY must be set in your .env file.")

llm = ChatOpenAI(
    model=OPENROUTER_MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    temperature=0.1,
    max_tokens=512,
)

router_llm = ChatOpenAI(
    model=OPENROUTER_ROUTER_MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    temperature=0,
    max_tokens=120,
    timeout=OPENROUTER_ROUTER_TIMEOUT_SECONDS,
)


def generate_text(prompt: str) -> str:
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = (response.content or "").strip()
        if not content:
            raise RuntimeError(f"Model {OPENROUTER_MODEL} returned an empty response.")
        return content
    except Exception as exc:
        print(f"LLM call failed for {OPENROUTER_MODEL}: {exc}")
        return _local_fallback(prompt)


def generate_router_text(prompt: str) -> str:
    try:
        response = router_llm.invoke([HumanMessage(content=prompt)])
        content = (response.content or "").strip()
        if not content:
            raise RuntimeError(f"Router model {OPENROUTER_ROUTER_MODEL} returned empty response.")
        return content
    except Exception as exc:
        print(f"Router LLM call failed for {OPENROUTER_ROUTER_MODEL}: {exc}")
        return _local_fallback(prompt)


def _local_fallback(prompt: str) -> str:
    if "Supervisor Router Agent" in prompt:
        return json.dumps(
            {
                "next_agent": "continue_current",
                "intent": None,
                "reason": "router fallback",
            }
        )

    if "Triage Router Agent" in prompt:
        return json.dumps(_fallback_triage(_latest_patient_message(prompt)))

    if "hospital intake assistant" in prompt:
        collected = _structured_info(prompt)
        has_duration = bool(collected.get("duration"))
        has_cause = bool(
            collected.get("cause")
            or collected.get("trigger")
            or collected.get("onset")
        )

        if has_duration and has_cause:
            return json.dumps(
                {
                    "has_enough_info": True,
                    "next_question": None,
                    "collected_info": collected,
                }
            )

        if has_duration:
            next_question = (
                "Can you tell me how this started? Was it after an injury, a fall, "
                "sudden onset, or something else?"
            )
        else:
            next_question = (
                "How long have you been experiencing this, and did anything seem to trigger it?"
            )

        return json.dumps(
            {
                "has_enough_info": False,
                "next_question": next_question,
                "collected_info": collected,
            }
        )

    if "compassionate medical assistant" in prompt:
        return json.dumps(
            {
                "remedy_text": (
                    "Based on what you described, please rest, stay hydrated, and avoid anything "
                    "that makes the symptoms worse. If symptoms are severe, worsening, or unusual "
                    "for you, it is best to speak with a doctor promptly."
                ),
                "follow_up_question": (
                    "Please try this and let me know how you feel. Are your symptoms improving, "
                    "or are they still persisting or getting worse?"
                ),
            }
        )

    return "I am having trouble reaching the language model right now. Please try again shortly."


def _latest_patient_message(prompt: str) -> str:
    marker = "Latest patient message:"
    if marker not in prompt:
        return ""

    after_marker = prompt.split(marker, 1)[1].strip()
    return after_marker.splitlines()[0].strip()


def _structured_info(prompt: str) -> dict:
    marker = "Structured info collected so far:"
    end_marker = "Questions already asked:"
    if marker not in prompt or end_marker not in prompt:
        return {}

    raw_json = prompt.split(marker, 1)[1].split(end_marker, 1)[0].strip()
    try:
        value = json.loads(raw_json)
    except json.JSONDecodeError:
        return {}

    return value if isinstance(value, dict) else {}


def _fallback_triage(message: str) -> dict:
    text = message.lower()
    symptoms = []

    known_symptoms = [
        "allergy",
        "bleeding",
        "breathlessness",
        "chest pain",
        "chest tightness",
        "cough",
        "dizziness",
        "fever",
        "headache",
        "nausea",
        "pain",
        "rash",
        "vomiting",
    ]
    for symptom in known_symptoms:
        if symptom in text:
            symptoms.append(symptom)

    if "tight" in text and "chest tightness" not in symptoms:
        symptoms.append("chest tightness")
    if "dizzy" in text and "dizziness" not in symptoms:
        symptoms.append("dizziness")

    if any(word in text for word in ["appointment", "book", "doctor"]):
        intent = "direct_booking"
    else:
        intent = "triage_symptoms"

    emergency_terms = ["unconscious", "stroke", "suicidal", "major bleeding", "cannot breathe"]
    severe_terms = ["chest pain", "chest tightness", "shortness of breath", "severe", "worse"]

    if any(term in text for term in emergency_terms):
        severity = "emergency"
    elif any(term in text for term in severe_terms):
        severity = "severe"
    else:
        severity = "moderate"

    return {
        "intent": intent,
        "symptoms": symptoms,
        "severity": severity,
    }
