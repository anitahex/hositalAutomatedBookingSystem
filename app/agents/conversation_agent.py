import json
from datetime import date
from langchain_core.output_parsers import PydanticOutputParser
from app.agents.schemas import ConversationDecision
from app.agents.state import GraphState
from app.inference.llm import generate_text
from app.services.memory_policy import get_memory_policy

parser = PydanticOutputParser(pydantic_object=ConversationDecision)
MEMORY_POLICY = get_memory_policy("conversation_agent")

# 100% STATIC CACHEABLE PREFIX
STATIC_CONVERSATION_PROMPT = """You are the backend AI reasoning engine for a hospital intake assistant. You are NOT chatting directly with the patient. 
Your job is to silently track what information has been collected and generate the NEXT empathetic question for the frontend to display.

Important intake details usually include duration, onset/trigger/cause, location, pattern, associated symptoms, allergies, existing conditions, and medications.

IMPORTANT rules:
- Write your warm, empathetic question ONLY inside the "next_question" JSON field.
- Ask ONE question at a time.
- Never ask something already answered.
- Do not repeat a duration/time question. If the patient already gave a timeframe, ask about a trigger or another clinically useful detail instead.
- If there is enough context to give tailored care guidance safely, set has_enough_info to true.

CRITICAL: Do NOT output conversational text or markdown. Output ONLY valid JSON matching this exact structure:
{"intent":"continue_intake|direct_booking","has_enough_info":true|false,"next_question":"string or null","collected_info":{"key":"value"}}"""

MAX_INTAKE_QUESTIONS = 8
OPEN_ENDED_FALLBACK = "What feels most important about this symptom that I have not asked yet?"

def _clean_json(raw_output: str) -> str:
    return raw_output.replace("```json", "").replace("```", "").strip()

def _get_minimal_profile(profile: dict | None) -> str:
    if not profile: return "Unknown"
    return f"Name: {profile.get('name', 'Unknown')}, Age: {profile.get('age', 'Unknown')}, Health Issues: {profile.get('health_issues', 'None')}"

def _compact_collected_info(collected: dict | None) -> str:
    if not collected: return "None"
    return " | ".join([f"{k}={v}" for k, v in collected.items() if v])

def _compact_state_summary(state: GraphState) -> str:
    return f"awaiting={state.get('awaiting')} | intent={state.get('intent')} | collected={_compact_collected_info(state.get('collected_info'))}"

def _with_initial_greeting(state: GraphState, question: str) -> tuple[str, bool]:
    if state.get("greeted"): return question, False
    symptom_text = ", ".join(state.get("symptoms") or []) or "what you are experiencing"
    return f"Hello, I am here to help. I understand you mentioned {symptom_text}. {question}", True


def _question_asks_about_duration(question: str) -> bool:
    lowered = " ".join((question or "").lower().split())
    return any(term in lowered for term in ("how long", "when did", "since when", "when started", "when did this start"))


def _conversation_intake_complete(collected: dict | None, questions_asked: list[str] | None) -> bool:
    collected = collected or {}
    questions_asked = questions_asked or []
    if len(questions_asked) >= MAX_INTAKE_QUESTIONS:
        return True
    return bool(
        collected.get("duration")
        and collected.get("location")
        and (collected.get("severity_pattern") or collected.get("pattern"))
        and (collected.get("cause") or collected.get("trigger") or collected.get("onset"))
    )

def conversation_agent_node(state: GraphState):
    history = state.get("conversation_history") or []
    symptoms = state.get("symptoms") or []
    existing_collected = state.get("collected_info") or {}
    questions_asked = state.get("questions_asked") or []
    user_text = state.get("user_input", "").strip()

    updated_history = list(history)
    if state.get("awaiting") == "conversation" and user_text:
        updated_history.append({"role": "patient", "text": user_text})

    dynamic_user_prompt = f"""Current date: {date.today().isoformat()}
Current state: {_compact_state_summary(state)}
Minimal profile: {_get_minimal_profile(state.get("patient_profile"))}
Latest user message: {user_text or "None"}
Current known symptoms: {', '.join(symptoms) if symptoms else 'unclear'}"""

    raw_output = generate_text(
        system_prompt=STATIC_CONVERSATION_PROMPT,
        user_prompt=dynamic_user_prompt,
        node_name="conversation_agent",
        chat_summary=state.get("chat_summary"),
        include_history=True,
        history_turns=MEMORY_POLICY.prompt_window_turns,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    
    clean_json = _clean_json(raw_output)
    print(f"Conversation Agent JSON: {clean_json}")

    try:
        decision = parser.parse(clean_json)
    except Exception as exc:
        print(f"Conversation parser failed: {exc}")
        fallback_q, greeted_now = _with_initial_greeting(state, "Could you tell me a little more about what you are feeling and when it started?")
        updated_history.append({"role": "assistant", "text": fallback_q})
        return {"conversation_history": updated_history, "collected_info": existing_collected, "questions_asked": questions_asked + [fallback_q], "greeted": state.get("greeted") or greeted_now, "awaiting": "conversation", "final_response": fallback_q}

    if decision.intent == "direct_booking":
        return {"conversation_history": updated_history, "intent": "direct_booking", "collected_info": {**existing_collected, **decision.collected_info}, "questions_asked": questions_asked, "awaiting": None}

    merged_collected = {**existing_collected, **decision.collected_info}
    if decision.has_enough_info or _conversation_intake_complete(merged_collected, questions_asked):
        return {"conversation_history": updated_history, "collected_info": merged_collected, "questions_asked": questions_asked, "awaiting": None, "remedy_requested": True}

    question = decision.next_question or "Can you describe your symptoms in a bit more detail?"
    if _question_asks_about_duration(question) and any(_question_asks_about_duration(previous) for previous in questions_asked):
        question = OPEN_ENDED_FALLBACK
    if question == OPEN_ENDED_FALLBACK and _conversation_intake_complete(merged_collected, questions_asked):
        return {"conversation_history": updated_history, "collected_info": merged_collected, "questions_asked": questions_asked, "awaiting": None, "remedy_requested": True}

    question, greeted_now = _with_initial_greeting(state, question)
    updated_history.append({"role": "assistant", "text": question})
    
    return {"conversation_history": updated_history, "collected_info": merged_collected, "questions_asked": questions_asked + [question], "greeted": state.get("greeted") or greeted_now, "awaiting": "conversation", "final_response": question}
