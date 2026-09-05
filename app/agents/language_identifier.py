from app.agents.state import GraphState
from app.services.language import apply_language_turn


def language_identification_node(state: GraphState):
    updates = apply_language_turn(dict(state), state.get("user_input") or "")
    if updates.get("language_control_response"):
        history = list(state.get("conversation_history") or state.get("messages") or [])
        history.append({"role": "assistant", "text": updates["language_control_response"]})
        updates.update({"conversation_history": history, "messages": history[-6:],
                        "final_response": updates["language_control_response"], "next_agent": "finish",
                        "supervisor_checked_input": True})
    return updates
