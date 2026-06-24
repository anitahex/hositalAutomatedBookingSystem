from datetime import date
from langchain_core.output_parsers import PydanticOutputParser
from app.agents.schemas import PatientExtraction
from app.agents.state import GraphState
from app.inference.llm import agenerate_text, astream_text
from app.services.memory_policy import get_memory_policy

parser = PydanticOutputParser(pydantic_object=PatientExtraction)
MEMORY_POLICY = get_memory_policy("triage_router")

# 100% STATIC CACHEABLE PREFIX
STATIC_TRIAGE_PROMPT = """You are the Triage Router Agent for a hospital portal.
Understand the patient's intent and symptoms from meaning and context. 

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

Extract clean symptoms in the patient's own medical meaning. For greetings or unclear messages, return an empty symptoms list and mild severity unless prior context changes that.

Return ONLY valid JSON matching this exact structure:
{"intent":"greeting|triage_symptoms|direct_booking|unclear","symptoms":["string"],"severity":"mild|moderate|severe|emergency"}"""

def _clean_json(raw_output: str) -> str:
    return raw_output.replace("```json", "").replace("```", "").strip()

async def triage_router_node(state: GraphState):
    # Guard: if we're already mid-intake (have symptoms AND asked questions),
    # skip re-triage entirely. Returning minimal updates lets conversation_agent
    # continue the existing intake without resetting collected data.
    if state.get("symptoms") and state.get("questions_asked"):
        preserved_intent = state.get("active_intent") or state.get("intent") or "triage_symptoms"
        return {
            "active_intent": preserved_intent,
            "intent": preserved_intent,
        }

    history = state.get("messages") or state.get("conversation_history") or []
    user_input = state["user_input"]
    updated_history = list(history)

    profile = f"Name: {state.get('patient_profile', {}).get('name', 'Unknown')}, Age: {state.get('patient_profile', {}).get('age', 'Unknown')}"

    dynamic_user_prompt = f"""Current date: {date.today().isoformat()}
Minimal profile: {profile}
Latest message: {user_input}"""

    raw_output = await agenerate_text(
        system_prompt=STATIC_TRIAGE_PROMPT,
        user_prompt=dynamic_user_prompt,
        node_name="triage_router",
        chat_summary=state.get("chat_summary"),
        include_history=False,
        history_turns=0,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    clean_json = _clean_json(raw_output)

    try:
        extracted = parser.parse(clean_json)
    except Exception:
        return {"conversation_history": updated_history, "messages": updated_history[-6:], "intent": "unclear", "symptoms": state.get("symptoms") or [], "severity": "mild", "final_response": "I could not reliably understand what you need yet. Could you describe your symptoms, or tell me if you want to book an appointment?"}

    if extracted.intent == "greeting":
        greeting = (
            "Hello, welcome to the hospital assistant. How can I help you today? "
            "You can describe your symptoms, tell me if you want to book an appointment, "
            "or upload medical documents (lab reports, prescriptions, or scans) using the attachment button below."
        )
        updated_history.append({"role": "assistant", "text": greeting})
        return {
            "conversation_history": updated_history,
            "messages": updated_history[-6:],
            "greeted": True,
            "intent": "greeting",
            "final_response": greeting,
        }

    symptoms = list(dict.fromkeys((state.get("symptoms") or []) + extracted.symptoms))
    intent = "triage_symptoms" if extracted.intent == "triage_symptoms" else extracted.intent
    return {
        "conversation_history": updated_history,
        "messages": updated_history[-6:],
        "active_intent": intent,
        "intent": intent,
        "symptoms": symptoms,
        "severity": extracted.severity,
        "remedy_given": False,
        "remedy_requested": False,
        "collected_data": {},
        "collected_info": {},
        "questions_asked": [],
        "candidate_departments": [],
    }


# ── Merged triage + first intake question (streaming, 1 HF call) ─────────────

_TRIAGE_SYMPTOM_KEYWORDS = frozenset({
    "pain", "ache", "fever", "cough", "nausea", "vomit", "diarrhea", "rash",
    "headache", "dizzy", "dizziness", "tired", "fatigue", "swollen", "swelling",
    "bleed", "bleeding", "breath", "chest", "burning", "itching", "sore",
    "injury", "hurt", "weak", "weakness", "cramp", "numb", "tingle",
    "stomach", "abdomen", "back pain", "joint", "muscle", "throat",
    "allergic", "allergy", "infection", "inflammation", "discharge",
    "anxiety", "depression", "dizzy", "vision", "hearing",
})

MERGED_TRIAGE_STREAM_SYSTEM = """\
You are a hospital triage assistant. Process the patient's message in two parts.

PART 1 — Output a single compact JSON line (no newline inside):
{"intent":"triage_symptoms|greeting|direct_booking|unclear","symptoms":["symptom1"],"severity":"mild|moderate|severe|emergency"}

PART 2 — On the very next line, write a warm natural-language response:
- triage_symptoms: show empathy about their specific symptoms, then ask ONE focused intake question (duration, onset, or location). At the end of the first response only, add one brief sentence: "If you have any medical documents like lab reports, prescriptions, or imaging, feel free to attach them using the button below."
- greeting: warmly welcome them, invite them to share symptoms or book an appointment, and mention they can upload medical documents (lab reports, prescriptions, or scans) using the attachment button below
- direct_booking: acknowledge the booking request and confirm what department/doctor they need
- unclear: gently ask them to clarify what they need help with

Rules: Output ONLY the two parts above — JSON line, newline, then plain text. No extra headers or labels.\
"""


def should_do_triage_stream(message: str) -> bool:
    """True when the user's message looks like a first symptom report or greeting."""
    lowered = message.lower()
    return any(kw in lowered for kw in _TRIAGE_SYMPTOM_KEYWORDS) or len(message.split()) <= 6


async def triage_intake_stream(state: GraphState, message: str):
    """
    Async generator — merged triage extraction + first intake question in ONE streaming call.
    Yields:
      - One dict (state updates from JSON line 1 — triage extraction)
      - Then string tokens for the plain-text response (line 2+)
    """
    profile = state.get("patient_profile") or {}
    profile_str = f"Name: {profile.get('name','Unknown')}, Age: {profile.get('age','Unknown')}"

    user_prompt = (
        f"Current date: {date.today().isoformat()}\n"
        f"Patient profile: {profile_str}\n"
        f"Patient message: {message}"
    )

    json_buf = ""
    json_yielded = False

    async for token in astream_text(
        system_prompt=MERGED_TRIAGE_STREAM_SYSTEM,
        user_prompt=user_prompt,
        node_name="triage_intake_stream",
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    ):
        if not json_yielded:
            json_buf += token
            if "\n" in json_buf:
                json_line, rest = json_buf.split("\n", 1)
                updates = _parse_triage_json_line(json_line.strip(), state)
                yield updates           # dict — caller uses this for state updates
                json_yielded = True
                if rest:
                    yield rest          # remaining text tokens after the JSON line
        else:
            yield token


def _parse_triage_json_line(raw: str, state: GraphState) -> dict:
    import json as _json
    try:
        data = _json.loads(raw)
    except Exception:
        return {"intent": "triage_symptoms", "symptoms": state.get("symptoms") or [], "severity": "mild"}

    raw_intent = str(data.get("intent") or "unclear")
    intent = "triage_symptoms" if raw_intent == "triage_symptoms" else raw_intent
    new_symptoms = [str(s) for s in (data.get("symptoms") or []) if str(s).strip()]
    symptoms = list(dict.fromkeys((state.get("symptoms") or []) + new_symptoms))
    severity = str(data.get("severity") or "mild")

    return {
        "active_intent": intent,
        "intent": intent,
        "symptoms": symptoms,
        "severity": severity,
        "remedy_given": False,
        "remedy_requested": False,
        "collected_data": {},
        "collected_info": {},
        "questions_asked": [],
        "candidate_departments": [],
        "greeted": True,
    }


def finalize_triage_stream_state(state: GraphState, triage_updates: dict, full_text: str) -> dict:
    """Merge triage extraction results + streamed text into final state dict."""
    history = list(state.get("conversation_history") or [])
    history.append({"role": "assistant", "text": full_text})

    intent = triage_updates.get("intent") or triage_updates.get("active_intent") or "triage_symptoms"

    if intent == "triage_symptoms":
        # First triage question — start fresh questions_asked with just this question
        awaiting_out = "conversation"
        questions_asked = []
        if full_text.strip():
            questions_asked.append(full_text.strip())
    elif intent == "direct_booking":
        # User wants to book; skip intake and fall to LangGraph booking path on next turn
        awaiting_out = None
        questions_asked = list(state.get("questions_asked") or [])
    else:
        # greeting or unclear — clear active_intent so the next user turn re-triages cleanly
        triage_updates = {**triage_updates, "active_intent": None, "intent": None}
        awaiting_out = None
        questions_asked = list(state.get("questions_asked") or [])

    merged = {
        **state,
        **triage_updates,
        "conversation_history": history,
        "messages": history[-6:],
        "final_response": full_text,
        "awaiting": awaiting_out,
        "questions_asked": questions_asked,
    }
    return merged
