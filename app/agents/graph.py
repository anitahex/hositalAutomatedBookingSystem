import asyncio

from langgraph.graph import END, StateGraph

from app.agents.appointment_booker import appointment_booker_node
from app.agents.conversation_agent import conversation_agent_node
from app.agents.document_analyzer import document_analyzer_node
from app.agents.supervisor import continue_current_node
from app.agents.supervisor import general_qa_node
from app.agents.medical_rag import medical_rag_node
from app.agents.remedy_agent import remedy_agent_node
from app.agents.state import GraphState
from app.agents.supervisor import route_from_supervisor, supervisor_node
from app.agents.triage_router import triage_router_node
from app.inference.llm import summarize_chat_history
from app.services.memory_policy import get_memory_policy
from app.services.checkpoint_store import SQLiteCheckpointer


MEMORY_POLICY = get_memory_policy("memory_compactor")


workflow = StateGraph(GraphState)

# Register all nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("triage_router", triage_router_node)
workflow.add_node("conversation_agent", conversation_agent_node)
workflow.add_node("remedy_agent", remedy_agent_node)
workflow.add_node("medical_rag", medical_rag_node)
workflow.add_node("general_qa", general_qa_node)
workflow.add_node("appointment_booker", appointment_booker_node)
workflow.add_node("appointment_resolver", appointment_booker_node)
workflow.add_node("continue_current", continue_current_node)
workflow.add_node("document_analyzer", document_analyzer_node)

# Entry point
workflow.set_entry_point("supervisor")

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

    thread_id = str(current_state.get("session_id") or current_state.get("chat_session_id") or patient_id or "default-session")
    result = await graph.ainvoke(
        current_state,
        config={"configurable": {"thread_id": thread_id}},
    )
    return compact_hybrid_memory(result)


def run_patient_chat(
    user_input: str,
    patient_id: str | None = None,
    state: GraphState | None = None,
):
    return asyncio.run(arun_patient_chat(user_input=user_input, patient_id=patient_id, state=state))
