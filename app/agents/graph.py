import asyncio

from langgraph.graph import END, StateGraph

from app.agents.appointment_booker import appointment_booker_node
from app.agents.checkup_report import checkup_report_node
from app.agents.conversation_agent import conversation_agent_node
from app.agents.document_analyzer import document_analyzer_node
from app.agents.language_identifier import language_identification_node
from app.agents.supervisor import continue_current_node
from app.agents.supervisor import general_qa_node
from app.agents.medical_rag import medical_rag_node
from app.agents.remedy_agent import remedy_agent_node
from app.agents.state import GraphState
from app.agents.supervisor import route_from_supervisor, supervisor_node
from app.agents.triage_router import triage_router_node
from app.inference.llm import summarize_chat_history
from app.inference.llm import generate_text
from app.services.language import normalize_language
from app.services.memory_policy import get_memory_policy
from app.services.checkpoint_store import SQLiteCheckpointer
from app.services.patient_text import is_localized_choice


MEMORY_POLICY = get_memory_policy("memory_compactor")


workflow = StateGraph(GraphState)

# Register all nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("triage_router", triage_router_node)
workflow.add_node("conversation_agent", conversation_agent_node)
workflow.add_node("remedy_agent", remedy_agent_node)
workflow.add_node("medical_rag", medical_rag_node)
workflow.add_node("checkup_report", checkup_report_node)
workflow.add_node("general_qa", general_qa_node)
workflow.add_node("appointment_booker", appointment_booker_node)
workflow.add_node("appointment_resolver", appointment_booker_node)
workflow.add_node("continue_current", continue_current_node)
workflow.add_node("document_analyzer", document_analyzer_node)
workflow.add_node("language_identification", language_identification_node)

# Entry point
workflow.set_entry_point("language_identification")
workflow.add_edge("language_identification", "supervisor")

# Supervisor routes conditionally to any node or END
workflow.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "continue_current": "continue_current",
        "triage_router": "triage_router",
        "conversation_agent": "conversation_agent",
        "remedy_agent": "remedy_agent",
        "medical_rag": "medical_rag",
        "checkup_report": "checkup_report",
        "general_qa": "general_qa",
        "appointment_booker": "appointment_booker",
        "appointment_resolver": "appointment_resolver",
        "document_analyzer": "document_analyzer",
        "finish": END,
    },
)

# Triage hands directly into the follow-up conversation flow so the user can continue naturally.
workflow.add_edge("triage_router", "conversation_agent")
workflow.add_edge("conversation_agent", "supervisor")
workflow.add_edge("remedy_agent", "supervisor")
workflow.add_edge("medical_rag", "supervisor")
workflow.add_edge("checkup_report", "supervisor")
workflow.add_edge("general_qa", "supervisor")
workflow.add_edge("appointment_booker", "supervisor")
workflow.add_edge("appointment_resolver", "supervisor")
workflow.add_edge("document_analyzer", "supervisor")
workflow.add_edge("continue_current", "supervisor")

CHECKPOINTER = SQLiteCheckpointer()
graph = workflow.compile(checkpointer=CHECKPOINTER)


def _normalize_message(message: dict) -> dict | None:
    if not isinstance(message, dict):
        return None

    role = message.get("role")
    text = message.get("text")
    content = message.get("content")
    value = content if content is not None else text
    if role not in {"patient", "assistant", "system"} or value is None:
        return None

    return {"role": role, "text": str(value)}


def _history_to_turns(history: list[dict] | None) -> list[dict]:
    return [
        normalized
        for normalized in (_normalize_message(message) for message in (history or []))
        if normalized is not None
    ]


def _trim_recent_history(history: list[dict], max_turns: int = MEMORY_POLICY.compaction_window_turns) -> tuple[list[dict], list[dict]]:
    if not history:
        return [], []

    kept = []
    patient_turns = 0
    for message in reversed(history):
        kept.append(message)
        if message.get("role") == "patient":
            patient_turns += 1
            if patient_turns >= max_turns:
                break

    recent = list(reversed(kept))
    overflow = history[: max(0, len(history) - len(recent))]
    return recent, overflow


def _build_summary_prompt(existing_summary: str, overflow: list[dict]) -> str:
    overflow_text = "\n".join(
        f"{message['role'].title()}: {message['text']}"
        for message in overflow
    )
    return f"""You are compressing hospital chat history into a structured clinical memory for a follow-up AI assistant.

Output ONLY the sections that have actual information. Use this exact format — one short line per field:

Symptoms: <comma-separated>
Duration: <e.g. "since yesterday", "3 days">
Location: <body area>
Severity: <mild/moderate/severe/emergency>
Facts: <key=value pairs for cause, pattern, medications, allergies — only if known>
Topics covered: <intake topics already asked, e.g. "duration, location, triggers">
Booking: <doctor, department, time — only if confirmed>
Next step: <e.g. "intake in progress", "awaiting remedy confirmation", "booking flow">

Rules:
- Skip any section with no information
- Do NOT invent or assume facts not stated in the conversation
- Merge the existing summary with new turns; update changed values
- Keep each section to one line

Existing summary:
{existing_summary or "None yet."}

New conversation to fold in:
{overflow_text or "None."}""".strip()


def compact_hybrid_memory(state: GraphState) -> GraphState:
    current_state = dict(state)
    full_history = _history_to_turns(
        current_state.get("conversation_history") or current_state.get("recent_history")
    )
    recent_history, overflow = _trim_recent_history(full_history, MEMORY_POLICY.compaction_window_turns)
    summary = current_state.get("chat_summary") or ""

    if overflow:
        summary_prompt = _build_summary_prompt(summary, overflow)
        summary = summarize_chat_history(
            summary_prompt,
            node_name="memory_compactor",
            chat_history=recent_history,
            chat_summary=summary,
            patient_id=str(current_state.get("patient_id") or ""),
            chat_session_id=str(current_state.get("chat_session_id") or ""),
        )

    current_state["recent_history"] = recent_history
    current_state["conversation_history"] = full_history
    current_state["messages"] = list(recent_history[-6:])
    current_state["chat_summary"] = summary or ""
    return current_state


def initialise_hybrid_memory(state: GraphState) -> GraphState:
    current_state = dict(state)
    history = _history_to_turns(
        current_state.get("conversation_history") or current_state.get("recent_history")
    )
    current_state["conversation_history"] = list(history)
    current_state["recent_history"] = _trim_recent_history(history, MEMORY_POLICY.compaction_window_turns)[0]
    current_state["messages"] = list(current_state["recent_history"][-6:])
    current_state["chat_summary"] = current_state.get("chat_summary") or ""
    return current_state


async def arun_patient_chat(
    user_input: str,
    patient_id: str | None = None,
    state: GraphState | None = None,
):
    """
    Call this on every user message, passing the previous state back in.
    The state carries the full conversation history so context is never lost.
    """
    current_state = compact_hybrid_memory(initialise_hybrid_memory(dict(state or {})))
    current_state["user_input"] = user_input
    # This marker belongs to the current response only; never let it suppress
    # localization of a newly generated response on the next turn.
    current_state.pop("patient_response_language", None)

    # Keep the original patient message in history, but canonicalize localized
    # Yes/No labels for deterministic workflow routing (e.g. German ja/nein).
    if is_localized_choice(user_input, "yes"):
        current_state["user_input"] = "yes"
    elif is_localized_choice(user_input, "no"):
        current_state["user_input"] = "no"

    if patient_id is not None:
        current_state["patient_id"] = patient_id

    if current_state.get("chat_closed"):
        return {
            **current_state,
            "next_agent": "finish",
            "awaiting": None,
            "final_response": "This chat is closed. Please start a new chat to continue.",
        }

    # Clear output fields so supervisor doesn't short-circuit on stale data
    current_state.pop("final_response", None)
    current_state.pop("next_agent", None)
    current_state["supervisor_checked_input"] = False

    # Namespace thread_id by patient so LangGraph checkpoints are strictly
    # per-user. Using only session_id risks cross-user state leakage if the
    # session_id falls back to patient_id or the literal "default-session".
    _pid = str(patient_id or current_state.get("patient_id") or "anon")
    _sid = str(current_state.get("session_id") or current_state.get("chat_session_id") or "default")
    thread_id = f"{_pid}::{_sid}"
    result = await graph.ainvoke(
        current_state,
        config={"configurable": {"thread_id": thread_id}},
    )
    result = _ensure_patient_response_language(result)
    return compact_hybrid_memory(result)


def _ensure_patient_response_language(result: GraphState) -> GraphState:
    """Apply active language to the final patient-facing response boundary."""
    response = result.get("final_response")
    code = normalize_language(result.get("active_language")) or "en"
    if not response or code == "en" or result.get("patient_response_language") == code:
        return result
    localized = generate_text(
        system_prompt=(
            f"You are the final patient-facing healthcare assistant. Respond entirely in language code {code}. "
            "Preserve the exact meaning, safety guidance, doctor names, department names, dates, times, numbers, "
            "IDs, option numbers, and markdown structure. Do not add or remove information. "
            "This is a patient workflow message, not the internal English clinical summary. Return only the response."
        ),
        user_prompt=str(response),
        node_name="patient_response_language_boundary",
        chat_summary=result.get("chat_summary"),
        include_history=False,
        history_turns=0,
        patient_id=str(result.get("patient_id") or ""),
        chat_session_id=str(result.get("chat_session_id") or ""),
    ).strip()
    if not localized:
        return result
    updated = {**result, "final_response": localized, "patient_response_language": code}
    for history_key in ("conversation_history", "messages"):
        history = updated.get(history_key)
        if isinstance(history, list) and history:
            copied = [dict(item) if isinstance(item, dict) else item for item in history]
            for item in reversed(copied):
                if isinstance(item, dict) and item.get("role") == "assistant":
                    item["text"] = localized
                    break
            updated[history_key] = copied
    return updated


def run_patient_chat(
    user_input: str,
    patient_id: str | None = None,
    state: GraphState | None = None,
):
    return asyncio.run(arun_patient_chat(user_input=user_input, patient_id=patient_id, state=state))
