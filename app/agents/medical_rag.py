from app.agents.state import GraphState
from app.services.rag import match_department_details


def medical_rag_node(state: GraphState):
    symptoms = state.get("symptoms") or []
    collected_info = state.get("collected_info") or {}
    try:
        match = match_department_details(symptoms, collected_info)
    except TypeError:
        match = match_department_details(symptoms)
    if match.needs_clarification or not match.department:
        symptom_text = ", ".join(symptoms) if symptoms else "your symptoms"
        response = (
            f"I could not confidently match {symptom_text} to the right department yet. "
            "Could you describe the main symptom, exact body area, and any trigger "
            "such as allergy, injury, fever, or sudden onset?"
        )
        history = list(state.get("conversation_history") or [])
        questions_asked = list(state.get("questions_asked") or [])
        history.append({"role": "assistant", "text": response})
        return {
            "awaiting": "conversation",
            "target_department": None,
            "conversation_history": history,
            "questions_asked": questions_asked + [response],
            "final_response": response,
        }

    department = match.department
    return {"target_department": department}
