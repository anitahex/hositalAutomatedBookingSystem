from datetime import date
from langchain_core.output_parsers import PydanticOutputParser
from app.agents.schemas import ConversationDecision
from app.agents.state import GraphState
from app.services.language import language_prompt_context
from app.agents.intake_utils import (
    compact_state_summary,
    extract_json_object,
    extract_local_intake_info,
    looks_like_general_knowledge_question,
    looks_like_intake_wrapup,
    looks_like_non_answer,
    next_missing_intake_question,
    question_topic,
    topic_already_asked,
)
from app.inference.llm import astream_text, generate_text
from app.services.memory_policy import get_memory_policy

parser = PydanticOutputParser(pydantic_object=ConversationDecision)
MEMORY_POLICY = get_memory_policy("conversation_agent")

# 100% STATIC CACHEABLE PREFIX
STATIC_CONVERSATION_PROMPT = """You are a clinical intake specialist. Your job is to LISTEN deeply and ask DYNAMIC, PROBING questions based on what the patient actually said.

DO NOT use generic questions. DO NOT assume "not asked" means "doesn't exist".

RULES:
1. **Read the patient's message carefully** - extract ALL clinical details mentioned
2. **Follow up on specifics they mentioned** - if they say "leg pain", ask if it's related to their back; if they mention a medication, ask what happened when they took it
3. **Ask ONE dynamic question** based on their actual symptoms, not a template
4. **Probe for severity** - if pain, ask where it radiates; if weakness, ask what movements are affected
5. **Probe for context** - if symptoms started recently, ask what changed in their life; if they've had it before, ask what's different this time
6. **Probe for triggers & patterns** - what makes it worse/better? time of day? certain activities? weather? stress?
7. **Probe for functional impact** - how does this affect daily life? work? sleep? exercise?
8. **Look for red flags** - ask about loss of function, numbness, tingling, balance issues, vision changes, fever, spreading
9. **Never ask the same thing twice** - track what's been discussed
10. **Be specific, not generic** - e.g., instead of "how long", ask "Did this start this week, last week, or longer ago?"
11. **Check if the patient actually answered** - set "reply_addresses_question" to false if their latest message is a greeting, filler ("hi", "ok", "hmm"), an off-topic remark, or a question back at you instead of an answer. When false, do NOT invent a new clinical question or extract any collected_info from it — instead write a short, warm "next_question" that re-engages them and gently repeats what you need to know (e.g. "No worries! Can you tell me a bit more about the pain you mentioned?"). When true, proceed normally.

SYMPTOM-SPECIFIC PROBING:
- Skin conditions: onset, triggers (products/detergents/stress/weather), spread pattern, discharge/weeping, itchiness severity, sleep impact
- Pain: exact location, radiation pattern, constant vs intermittent, aggravating activities, relieving positions, impact on work/sitting/standing
- Fever/illness: temperature, associated symptoms, duration, exposed to sick people recently
- Weakness/numbness: which body part, when did it start, spreading or stable, affecting movements

EXAMPLES OF EXCELLENT DYNAMIC QUESTIONS:
- If "itching + rash": "When did this start—this week or earlier? And did it appear suddenly or gradually spread?"
- If "pimples all over back": "Are they painful, just itchy, or both? And did something change recently—new soap, detergent, or clothing?"
- If "back pain": "Where exactly—lower back, mid-back, or upper back? And does it feel like muscle pain or something deeper?"
- If "for 5 days": "On a scale where 0 is no pain and 10 is worst pain ever, where are you right now?"
- If "worsens in evening": "What are you doing during the day—sitting at desk, heavy lifting, or something else?"

CRITICAL: Do NOT output conversational text or markdown. Output ONLY valid JSON matching this exact structure:
{"intent":"continue_intake|direct_booking","reply_addresses_question":true|false,"has_enough_info":true|false,"next_question":"string or null","collected_info":{"key":"value"}}"""

MAX_INTAKE_QUESTIONS = 6
MAX_IRRELEVANT_STREAK = 2
OPEN_ENDED_FALLBACK = "Is there anything else about your symptoms that feels important or concerning that I haven't asked?"

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
    # MUST ask at least MAX_INTAKE_QUESTIONS (6) to get thorough clinical details
    # Do NOT allow early exit based on field collection alone
    if len(questions_asked) >= MAX_INTAKE_QUESTIONS:
        return True
    return False

def conversation_agent_node(state: GraphState):
    print(f"[CONVERSATION_AGENT_NODE] ENTRY - awaiting={state.get('awaiting')}, questions={len(state.get('questions_asked', []))}")
    history = state.get("messages") or state.get("conversation_history") or []
    symptoms = state.get("symptoms") or []
    existing_collected = state.get("collected_data") or state.get("collected_info") or {}
    questions_asked = state.get("questions_asked") or []
    user_text = (state.get("user_input") or "").strip()
    if not user_text:
        for turn in reversed(history):
            if isinstance(turn, dict) and turn.get("role") in ("patient", "user") and turn.get("text"):
                user_text = str(turn.get("text")).strip()
                break

    updated_history = list(history)

    if state.get("greeted") and not symptoms and state.get("intent") == "greeting":
        return {
            "conversation_history": updated_history,
            "messages": updated_history[-6:],
            "awaiting": state.get("awaiting") or None,
        }

    # Fast-path: once we've hit the question cap, complete intake and trigger booking flow.
    # After 6 questions, user gets clinical analysis and can book with appropriate specialist.
    if len(questions_asked) >= MAX_INTAKE_QUESTIONS and symptoms:
        print(f"[CONVERSATION_AGENT] FAST-PATH: questions >= {MAX_INTAKE_QUESTIONS}, symptoms={len(symptoms)}")
        local_collected = extract_local_intake_info(user_text)
        merged_collected = {**existing_collected, **local_collected}
        result = {
            "conversation_history": updated_history,
            "messages": updated_history[-6:],
            "collected_data": merged_collected,
            "collected_info": merged_collected,
            "questions_asked": questions_asked,
            "awaiting": None,
            "intake_complete": True,
            "active_intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
            "intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
        }
        print(f"[CONVERSATION_AGENT] RETURNING with awaiting=None, intake_complete=True")
        return result

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
        system_prompt=STATIC_CONVERSATION_PROMPT + language_prompt_context(state),
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
            reply_addresses_question=decision.reply_addresses_question,
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

    # The patient's latest message did not actually answer the question just asked
    # (a greeting, filler, or off-topic remark). Don't let it silently consume one of
    # the scripted intake questions or pollute collected_info — nudge them back on
    # topic instead, up to a couple of tries before moving on regardless.
    reply_relevant = decision.reply_addresses_question and not looks_like_non_answer(user_text)
    if not reply_relevant:
        streak = int(state.get("irrelevant_reply_streak") or 0) + 1
        if streak < MAX_IRRELEVANT_STREAK:
            clarifying_question = (decision.next_question or "").strip() or next_missing_intake_question(
                existing_collected, questions_asked, OPEN_ENDED_FALLBACK
            )
            clarifying_question, greeted_now = _with_initial_greeting(state, clarifying_question)
            updated_history.append({"role": "assistant", "text": clarifying_question})
            return {
                "conversation_history": updated_history,
                "messages": updated_history[-6:],
                "collected_data": existing_collected,
                "collected_info": existing_collected,
                "questions_asked": questions_asked,
                "irrelevant_reply_streak": streak,
                "greeted": state.get("greeted") or greeted_now,
                "awaiting": "conversation",
                "final_response": clarifying_question,
                "active_intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
                "intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
            }
        # Safety valve: the patient hasn't engaged for a couple of turns in a row —
        # move on with the next scripted question rather than looping forever.
        question = next_missing_intake_question(existing_collected, questions_asked, OPEN_ENDED_FALLBACK)
        question, greeted_now = _with_initial_greeting(state, question)
        updated_history.append({"role": "assistant", "text": question})
        return {
            "conversation_history": updated_history,
            "messages": updated_history[-6:],
            "collected_data": existing_collected,
            "collected_info": existing_collected,
            "questions_asked": questions_asked + [question],
            "irrelevant_reply_streak": 0,
            "greeted": state.get("greeted") or greeted_now,
            "awaiting": "conversation",
            "final_response": question,
            "active_intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
            "intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
        }

    merged_collected = {**existing_collected, **local_collected, **decision.collected_info}
    if decision.has_enough_info or _conversation_intake_complete(merged_collected, questions_asked):
        return {
            "conversation_history": updated_history,
            "messages": updated_history[-6:],
            "collected_data": merged_collected,
            "collected_info": merged_collected,
            "questions_asked": questions_asked,
            "irrelevant_reply_streak": 0,
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
            "irrelevant_reply_streak": 0,
            "awaiting": None,
            "remedy_requested": True,
            "active_intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
            "intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
        }

    question, greeted_now = _with_initial_greeting(state, question)
    updated_history.append({"role": "assistant", "text": question})

    result = {
        "conversation_history": updated_history,
        "messages": updated_history[-6:],
        "collected_data": merged_collected,
        "collected_info": merged_collected,
        "questions_asked": questions_asked + [question],
        "irrelevant_reply_streak": 0,
        "greeted": state.get("greeted") or greeted_now,
        "awaiting": "conversation",
        "final_response": question,
        "active_intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
        "intent": state.get("active_intent") or state.get("intent") or "triage_symptoms",
    }
    print(f"[CONV_AGENT] Returning awaiting='conversation' with {len(questions_asked)+1} questions asked")
    return result


# ── Streaming variant (bypasses LangGraph, 1 direct HF call) ─────────────────

STATIC_CONV_STREAM_SYSTEM = """\
You are a clinically-trained intake specialist. Ask ONE dynamic, probing follow-up question based on what the patient actually said.

DO NOT ask generic questions. READ their message and follow up on specifics.

Guidelines:
- Ask ONE targeted question only that digs deeper into what they actually mentioned
- Connect to what they specifically mentioned: "You mentioned gabapentin didn't help — how long were you taking it?"
- Probe deeper on their actual symptoms: if they mention leg pain with back pain, ask if it radiates
- Test functional impact: "Can you sit/stand/walk without worsening the pain?"
- Ask about triggers: "What activities or positions make it worse or better?"
- Ask about patterns: "Is it constant or does it come and go? And when did it start?"
- Never ask something already answered
- If red flags detected (numbness, weakness, loss of bladder control, severe chest pain), escalate
- If the patient's latest reply is a greeting, filler, or otherwise does not answer what you just asked, do NOT move on to a new topic — instead briefly and warmly ask them to answer the previous question again

PROBE FOR THESE DETAILS:
- Onset: When exactly did this start? Sudden or gradual?
- Severity: On a scale of 0-10, how bad is it?
- Pattern: Constant, intermittent, or getting worse?
- Triggers: What makes it better or worse? Time of day? Activities?
- Spread: Is it localized or spreading?
- Functional impact: How does it affect your daily life, work, sleep?

Examples of excellent questions:
- "Is the leg pain connected to your back, or are they separate problems?"
- "When you say it's worse in the evening, what are you usually doing earlier in the day?"
- "How much gabapentin were you taking and for how long?"
- "Does changing positions (sitting, standing, lying) make the pain better or worse?"
- "On a scale of 1-10, how severe is the itching right now?"
- "Did this rash appear suddenly all over, or did it start in one place and spread?"

Output ONLY the question itself — no preamble, no labels. 1-2 sentences, conversational.\
"""


def should_stream_intake(state: GraphState) -> bool:
    """
    True when we can stream a follow-up question directly without a full LangGraph run.
    False when intake is complete, after 5 streaming questions, or when the patient's
    latest reply looks like a greeting/filler/off-topic question rather than an answer —
    those fall through to the full LangGraph path, which can route a genuinely unrelated
    message (e.g. "who is the prime minister") to general_qa instead of this fast path
    silently absorbing it as if it were the next intake answer.
    """
    questions_asked = state.get("questions_asked") or []
    # Safety valve: after 5 questions the LangGraph path uses LLM to properly
    # extract facts from all prior answers and decide if intake is truly complete.
    if len(questions_asked) >= 5:
        return False
    user_text = state.get("user_input") or ""
    if looks_like_non_answer(user_text) or looks_like_general_knowledge_question(user_text):
        return False
    existing_collected = state.get("collected_data") or state.get("collected_info") or {}
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
        system_prompt=STATIC_CONV_STREAM_SYSTEM + language_prompt_context(state),
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
