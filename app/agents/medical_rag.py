from app.agents.state import GraphState
from app.services.rag import match_department_details


def medical_rag_node(state: GraphState):
    symptoms = state.get("symptoms") or []
    match = match_department_details(symptoms)
    if match.needs_clarification or not match.department:
        symptom_text = ", ".join(symptoms) if symptoms else "your symptoms"
        return {
            "awaiting": "conversation",
            "target_department": None,
            "final_response": (
                f"I could not confidently match {symptom_text} to the right department yet. "
                "Could you describe the main symptom, exact body area, and any trigger "
                "such as allergy, injury, fever, or sudden onset?"
            ),
        }

    department = match.department
    return {"target_department": department}
