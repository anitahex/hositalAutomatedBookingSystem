from datetime import date
from langchain_core.output_parsers import PydanticOutputParser
from app.agents.schemas import PatientExtraction
from app.agents.state import GraphState
from app.inference.llm import generate_text
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

def triage_router_node(state: GraphState):
    history = state.get("conversation_history") or []
    user_input = state["user_input"]
    updated_history = list(history)
    updated_history.append({"role": "patient", "text": user_input})
    
    profile = f"Name: {state.get('patient_profile', {}).get('name', 'Unknown')}, Age: {state.get('patient_profile', {}).get('age', 'Unknown')}"

    dynamic_user_prompt = f"""Current date: {date.today().isoformat()}
Minimal profile: {profile}
Latest message: {user_input}"""

    raw_output = generate_text(
        system_prompt=STATIC_TRIAGE_PROMPT,
        user_prompt=dynamic_user_prompt,
        node_name="triage_router",
        chat_summary=state.get("chat_summary"),
        include_history=True,
        history_turns=MEMORY_POLICY.prompt_window_turns,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    clean_json = _clean_json(raw_output)
    
    try:
        extracted = parser.parse(clean_json)
    except Exception:
        return {"conversation_history": updated_history, "intent": "unclear", "symptoms": state.get("symptoms") or [], "severity": "mild", "final_response": "I could not reliably understand what you need yet. Could you describe your symptoms, or tell me if you want to book an appointment?"}

    if extracted.intent == "greeting":
        greeting = "Hello, welcome to the hospital assistant. How can I help you today? You can describe your symptoms or tell me if you want to book an appointment."
        updated_history.append({"role": "assistant", "text": greeting})
        return {"conversation_history": updated_history, "greeted": True, "final_response": greeting}

    symptoms = list(set((state.get("symptoms") or []) + extracted.symptoms))
    return {"conversation_history": updated_history, "intent": extracted.intent, "symptoms": symptoms, "severity": extracted.severity, "remedy_given": False, "remedy_requested": False, "collected_info": {}, "questions_asked": []}
