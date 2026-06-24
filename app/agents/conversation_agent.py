from datetime import date
from langchain_core.output_parsers import PydanticOutputParser
from app.agents.schemas import ConversationDecision
from app.agents.state import GraphState
from app.agents.intake_utils import (
    compact_state_summary,
    extract_json_object,
    extract_local_intake_info,
    looks_like_intake_wrapup,
    next_missing_intake_question,
    question_topic,
    topic_already_asked,
)
from app.inference.llm import astream_text, generate_text
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

MAX_INTAKE_QUESTIONS = 5
OPEN_ENDED_FALLBACK = "What feels most important about this symptom that I have not asked yet?"

def _clean_json(raw_output: str) -> str:
    return (raw_output or "").replace("```json", "").replace("```", "").strip()

def _get_minimal_profile(profile: dict | None) -> str:
    if not profile: return "Unknown"
    return f"Name: {profile.get('name', 'Unknown')}, Age: {profile.get('age', 'Unknown')}, Health Issues: {profile.get('health_issues', 'None')}"

def _with_initial_greeting(state: GraphState, question: str) -> tuple[str, bool]:
    if state.get("greeted"): return question, False
    symptom_text = ", ".join(state.get("symptoms") or []) or "what you are experiencing"
    return f"Hello, I am here to help. I understand you mentioned {symptom_text}. {question}", True


def _question_asks_about_duration(question: str) -> bool:
    lowered = " ".join((question or "").lower().split())
    return any(term in lowered for term in ("how long", "when did", "since when", "when started", "when did this start"))

def _build_fallback_decision(merged_collected: dict, questions_asked: list[str]) -> ConversationDecision:
    if _conversation_intake_complete(merged_collected, questions_asked):
        return ConversationDecision(
            intent="continue_intake",
            has_enough_info=True,
            next_question=None,
            collected_info=merged_collected,
        )

    return ConversationDecision(
        intent="continue_intake",
        has_enough_info=False,
        next_question=next_missing_intake_question(merged_collected, questions_asked, OPEN_ENDED_FALLBACK),
        collected_info=merged_collected,
    )


def _conversation_intake_complete(collected: dict | None, questions_asked: list[str] | None) -> bool:
    collected = collected or {}
    questions_asked = questions_asked or []
    if len(questions_asked) >= MAX_INTAKE_QUESTIONS:
        return True
    has_duration = bool(collected.get("duration"))
    has_location = bool(collected.get("location"))
    has_pattern = bool(collected.get("severity_pattern") or collected.get("pattern"))
    has_cause = bool(collected.get("cause") or collected.get("trigger") or collected.get("onset"))
    # Classic 4-field completion (location-bearing symptoms like chest pain, knee pain)
    if has_duration and has_location and has_pattern and has_cause:
        return True
    # Relaxed: systemic/non-localised symptoms (fatigue, nausea, anxiety, etc.) have no body location
    if has_duration and has_pattern and has_cause:
        return True
    if has_duration and has_location and has_cause:
        return True
    return False

def conversation_agent_node(state: GraphState):
    history = state.get("messages") or state.get("conversation_history") or []
    symptoms = state.get("symptoms") or []
    existing_collected = state.get("collected_data") or state.get("collected_info") or {}
    questions_asked = state.get("questions_asked") or []
    user_text = state.get("user_input", "").strip()

    updated_history = list(history)

    if state.get("greeted") and not symptoms and state.get("intent") == "greeting":
        return {
            "conversation_history": updated_history,
            "messages": updated_history[-6:],
            "awaiting": state.get("awaiting") or None,
        }

    # Fast-path: once we've hit the question cap, skip the LLM and complete intake directly.
    # This prevents infinite loops when the LLM keeps returning has_enough_info=False.
    if len(questions_asked) >= MAX_INTAKE_QUESTIONS and symptoms:
        local_collected = extract_local_intake_info(user_text)
        merged_collected = {**existing_collected, **local_collected}
        return {
            "conversation_history": updated_history,
            "messages": updated_history[-6:],
            "collected_data": merged_collected,
            "collected_info": merged_collected,
            "questions_asked": questions_asked,
            "awaiting": None,
            "remedy_requested": True,
            "active_intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
            "intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
        }

    local_collected = extract_local_intake_info(user_text)
    user_wants_to_wrap_up = looks_like_intake_wrapup(user_text)
    prompt_collected = {**existing_collected, **local_collected}
    # Use ALL questions to build topic set — prevents re-asking a topic from earlier turns
    asked_topics = {t for q in questions_asked if (t := question_topic(q))}
    dynamic_user_prompt = f"""Current date: {date.today().isoformat()}
Current state: {compact_state_summary(state)}
Minimal profile: {_get_minimal_profile(state.get("patient_profile"))}
Latest user message: {user_text or "None"}
Current known symptoms: {', '.join(symptoms) if symptoms else 'unclear'}
Topics ALREADY COVERED — do NOT ask about these again: {', '.join(sorted(asked_topics)) or "none"}
Do not ask again about any topic already covered above."""

    raw_output = generate_text(
        system_prompt=STATIC_CONVERSATION_PROMPT,
        user_prompt=dynamic_user_prompt,
        node_name="conversation_agent",
        chat_summary=state.get("chat_summary"),
        include_history=False,
        history_turns=0,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    
    clean_json = _clean_json(raw_output)
    print(f"Conversation Agent JSON: {clean_json}")

    try:
        decision = parser.parse(extract_json_object(clean_json))
    except Exception as exc:
        print(f"Conversation parser failed: {exc}")
        decision = _build_fallback_decision(prompt_collected, questions_asked)

    if local_collected:
        decision = ConversationDecision(
            intent=decision.intent or "continue_intake",
            has_enough_info=bool(decision.has_enough_info),
            next_question=decision.next_question,
            collected_info={**decision.collected_info, **local_collected},
        )

    if user_wants_to_wrap_up and symptoms:
        merged_collected = {**existing_collected, **local_collected, **decision.collected_info}
        return {
            "conversation_history": updated_history,
            "messages": updated_history[-6:],
            "collected_info": merged_collected,
            "collected_data": merged_collected,
            "questions_asked": questions_asked,
            "awaiting": None,
            "remedy_requested": True,
        }

    if decision.intent == "direct_booking":
        merged_collected = {**existing_collected, **local_collected, **decision.collected_info}
        return {
            "conversation_history": updated_history,
            "messages": updated_history[-6:],
            "active_intent": "direct_booking",
            "intent": "direct_booking",
            "collected_data": merged_collected,
            "collected_info": merged_collected,
            "questions_asked": questions_asked,
            "awaiting": None,
        }

    merged_collected = {**existing_collected, **local_collected, **decision.collected_info}
    if decision.has_enough_info or _conversation_intake_complete(merged_collected, questions_asked):
        return {
            "conversation_history": updated_history,
            "messages": updated_history[-6:],
            "collected_data": merged_collected,
            "collected_info": merged_collected,
            "questions_asked": questions_asked,
            "awaiting": None,
            "remedy_requested": True,
            "active_intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
            "intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
        }

    question = decision.next_question or "Can you describe your symptoms in a bit more detail?"
    if _question_asks_about_duration(question) and any(_question_asks_about_duration(previous) for previous in questions_asked):
        question = next_missing_intake_question(merged_collected, questions_asked, OPEN_ENDED_FALLBACK)
    elif topic_already_asked(question_topic(question), questions_asked):
        question = next_missing_intake_question(merged_collected, questions_asked, question)
    elif not question.strip():
        question = next_missing_intake_question(merged_collected, questions_asked, OPEN_ENDED_FALLBACK)
    if question == OPEN_ENDED_FALLBACK and _conversation_intake_complete(merged_collected, questions_asked):
        return {
            "conversation_history": updated_history,
            "messages": updated_history[-6:],
            "collected_data": merged_collected,
            "collected_info": merged_collected,
            "questions_asked": questions_asked,
            "awaiting": None,
            "remedy_requested": True,
            "active_intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
            "intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
        }

    question, greeted_now = _with_initial_greeting(state, question)
    updated_history.append({"role": "assistant", "text": question})
    
    return {
        "conversation_history": updated_history,
        "messages": updated_history[-6:],
        "collected_data": merged_collected,
        "collected_info": merged_collected,
        "questions_asked": questions_asked + [question],
        "greeted": state.get("greeted") or greeted_now,
        "awaiting": "conversation",
        "final_response": question,
        "active_intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
        "intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
    }


# ── Streaming variant (bypasses LangGraph, 1 direct HF call) ─────────────────

STATIC_CONV_STREAM_SYSTEM = """\
You are a caring hospital intake assistant asking follow-up questions to understand a patient's symptoms.

Your task: ask the SINGLE most useful next intake question based on what you already know.

Focus areas (pick the most important unknown): duration, onset/trigger, location, severity pattern, \
associated symptoms, existing conditions, medications, allergies.

Rules:
- Ask ONE question only
- Never repeat a topic already answered or asked
- Be warm, empathetic, and concise (1–2 sentences)
- Output ONLY the question — no JSON, no preamble, no labels\
"""


def should_stream_intake(state: GraphState) -> bool:
    """
    True when we can stream a follow-up question directly without a full LangGraph run.
    False when intake is complete or after 5 streaming questions (fall to LangGraph
    which uses LLM extraction to synthesise all answers and route to remedy/RAG).
    """
    questions_asked = state.get("questions_asked") or []
    # Safety valve: after 5 questions the LangGraph path uses LLM to properly
    # extract facts from all prior answers and decide if intake is truly complete.
    if len(questions_asked) >= 5:
        return False
    existing_collected = state.get("collected_data") or state.get("collected_info") or {}
    user_text = state.get("user_input") or ""
    local_collected = extract_local_intake_info(user_text)
    merged = {**existing_collected, **local_collected}
    return not _conversation_intake_complete(merged, questions_asked)


async def conversation_agent_stream(state: GraphState):
    """
    Async generator — yields question tokens from HF with stream=True.
    Call should_stream_intake() first; if False, fall through to LangGraph.
    """
    symptoms = state.get("symptoms") or []
    existing_collected = state.get("collected_data") or state.get("collected_info") or {}
    questions_asked = state.get("questions_asked") or []
    user_text = (state.get("user_input") or "").strip()

    local_collected = extract_local_intake_info(user_text)
    merged_collected = {**existing_collected, **local_collected}

    # Derive topic set from ALL questions — prevents re-asking earlier topics
    asked_topics = {t for q in questions_asked if (t := question_topic(q))}

    # Include recent conversation turns so the model sees the actual patient answers
    history = state.get("conversation_history") or state.get("messages") or []
    recent_turns = []
    for turn in history[-6:]:
        role = turn.get("role", "")
        text = str(turn.get("text") or turn.get("content") or "").strip()
        if role and text:
            label = "Patient" if role in ("patient", "user") else "Assistant"
            recent_turns.append(f"{label}: {text}")
    history_block = "\n".join(recent_turns) if recent_turns else "none"

    user_prompt = (
        f"Current date: {date.today().isoformat()}\n"
        f"Known symptoms: {', '.join(symptoms) if symptoms else 'not yet specified'}\n"
        f"Already collected: {', '.join(f'{k}={v}' for k, v in merged_collected.items() if v) or 'nothing yet'}\n"
        f"Topics ALREADY COVERED — DO NOT ask about these again: {', '.join(sorted(asked_topics)) or 'none'}\n"
        f"Recent conversation:\n{history_block}\n"
        f"Patient's latest reply: {user_text or 'none'}"
    )

    async for token in astream_text(
        system_prompt=STATIC_CONV_STREAM_SYSTEM,
        user_prompt=user_prompt,
        node_name="conv_stream",
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    ):
        yield token


def finalize_conv_stream_state(state: GraphState, full_text: str) -> dict:
    """Build the updated state dict after streaming a follow-up question."""
    user_text = (state.get("user_input") or "").strip()
    local_collected = extract_local_intake_info(user_text)
    existing_collected = state.get("collected_data") or state.get("collected_info") or {}
    merged_collected = {**existing_collected, **local_collected}

    question = full_text.strip()
    questions_asked = list(state.get("questions_asked") or [])
    if question:
        questions_asked.append(question)

    history = list(state.get("conversation_history") or [])
    history.append({"role": "assistant", "text": question})

    return {
        **state,
        "conversation_history": history,
        "messages": history[-6:],
        "collected_data": merged_collected,
        "collected_info": merged_collected,
        "questions_asked": questions_asked,
        "greeted": state.get("greeted") or True,
        "awaiting": "conversation",
        "final_response": question,
        "active_intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
        "intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
    }
