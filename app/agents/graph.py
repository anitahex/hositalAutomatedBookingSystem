import os

from langgraph.graph import END, StateGraph

from app.agents.appointment_booker import appointment_booker_node
from app.agents.conversation_agent import conversation_agent_node
from app.agents.medical_rag import medical_rag_node
from app.agents.remedy_agent import remedy_agent_node
from app.agents.state import GraphState
from app.agents.supervisor import route_from_supervisor, supervisor_node
from app.agents.triage_router import triage_router_node
from app.inference.llm import summarize_chat_history


MAX_RECENT_TURNS = int(os.getenv("HF_RECENT_TURNS", "5"))


workflow = StateGraph(GraphState)

# Register all nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("triage_router", triage_router_node)
workflow.add_node("conversation_agent", conversation_agent_node)
workflow.add_node("remedy_agent", remedy_agent_node)
workflow.add_node("medical_rag", medical_rag_node)
workflow.add_node("appointment_booker", appointment_booker_node)

# Entry point
workflow.set_entry_point("supervisor")

# Supervisor routes conditionally to any node or END
workflow.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "triage_router": "triage_router",
        "conversation_agent": "conversation_agent",
        "remedy_agent": "remedy_agent",
        "medical_rag": "medical_rag",
        "appointment_booker": "appointment_booker",
        "finish": END,
    },
)

# All nodes report back to supervisor
workflow.add_edge("triage_router", "supervisor")
workflow.add_edge("conversation_agent", "supervisor")
workflow.add_edge("remedy_agent", "supervisor")
workflow.add_edge("medical_rag", "supervisor")
workflow.add_edge("appointment_booker", "supervisor")

graph = workflow.compile()


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


def _trim_recent_history(history: list[dict], max_turns: int = MAX_RECENT_TURNS) -> tuple[list[dict], list[dict]]:
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
    return f"""
You are compressing hospital chat memory for a follow-up medical assistant.

Keep only clinically useful and conversationally important facts.
Preserve symptoms, timing, severity, triggers, booked appointments, department hints,
and any decisions already made.

Existing summary:
{existing_summary or "None yet."}

New conversation to fold in:
{overflow_text or "None."}

Return a concise summary in plain text, with no bullet points unless they clearly help.
""".strip()


def compact_hybrid_memory(state: GraphState) -> GraphState:
    current_state = dict(state)
    history = _history_to_turns(
        current_state.get("recent_history") or current_state.get("conversation_history")
    )
    recent_history, overflow = _trim_recent_history(history)
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
    current_state["conversation_history"] = list(recent_history)
    current_state["chat_summary"] = summary or ""
    return current_state


def initialise_hybrid_memory(state: GraphState) -> GraphState:
    current_state = dict(state)
    history = _history_to_turns(
        current_state.get("recent_history") or current_state.get("conversation_history")
    )
    current_state["recent_history"] = history
    current_state["conversation_history"] = list(history)
    current_state["chat_summary"] = current_state.get("chat_summary") or ""
    return current_state


def run_patient_chat(
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

    result = graph.invoke(current_state)
    return compact_hybrid_memory(result)
