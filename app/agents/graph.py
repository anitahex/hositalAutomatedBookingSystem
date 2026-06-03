from langgraph.graph import END, StateGraph

from app.agents.appointment_booker import appointment_booker_node
from app.agents.conversation_agent import conversation_agent_node
from app.agents.medical_rag import medical_rag_node
from app.agents.remedy_agent import remedy_agent_node
from app.agents.state import GraphState
from app.agents.supervisor import route_from_supervisor, supervisor_node
from app.agents.triage_router import triage_router_node


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


def run_patient_chat(
    user_input: str,
    patient_id: str | None = None,
    state: GraphState | None = None,
):
    """
    Call this on every user message, passing the previous state back in.
    The state carries the full conversation history so context is never lost.
    """
    current_state = dict(state or {})
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

    return graph.invoke(current_state)
