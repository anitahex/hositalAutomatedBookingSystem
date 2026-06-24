from app.agents.state import GraphState
from app.agents.intake_utils import next_missing_intake_question
from app.services.rag import match_department_details


def _format_department_candidates(candidates: list[dict] | None) -> str:
    if not candidates:
        return ""
    parts = []
    for candidate in candidates[:3]:
        department = candidate.get("department") or "Unknown department"
        matched_terms = candidate.get("matched_terms") or []
        symptom_hint = ", ".join(str(term) for term in matched_terms[:2] if term)
        if symptom_hint:
            parts.append(f"{department} for {symptom_hint}")
        else:
            parts.append(str(department))
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def medical_rag_node(state: GraphState):
    symptoms = state.get("symptoms") or []
    collected_info = state.get("collected_data") or state.get("collected_info") or {}
    existing_questions = list(state.get("questions_asked") or [])
    match = match_department_details(
        symptoms,
        collected_info,
        chat_history=state.get("conversation_history"),
        chat_summary=state.get("chat_summary"),
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    candidate_departments = list(match.candidate_departments or [])
    if len(candidate_departments) >= 2 and (match.needs_clarification or not match.department):
        department_text = _format_department_candidates(candidate_departments)
        awaiting_state = "department_selection" if (state.get("active_intent") or state.get("intent")) == "direct_booking" else "conversation"
        response = (
            f"I can see this may involve more than one specialty, including {department_text}. "
            "I do not want to collapse separate problems into one chat path. "
            "Tell me whether these symptoms belong to one issue or if you want help booking them separately, and I will keep this in the same conversation."
        )
        history = list(state.get("conversation_history") or [])
        history.append({"role": "assistant", "text": response})
        return {
            "awaiting": awaiting_state,
            "active_intent": state.get("active_intent") or state.get("intent") or "direct_booking",
            "intent": state.get("active_intent") or state.get("intent") or "direct_booking",
            "target_department": None,
            "candidate_departments": candidate_departments,
            "department_match_source": match.source,
            "department_match_confidence": match.confidence,
            "department_match_reason": match.reason,
            "retrieval_attempted": match.retrieval_attempted,
            "retrieval_confidence": match.retrieval_confidence,
            "conversation_history": history,
            "messages": history[-6:],
            "questions_asked": existing_questions + [response],
            "final_response": response,
        }

    if match.needs_clarification or not match.department:
        symptom_text = ", ".join(symptoms) if symptoms else "your symptoms"
        history = list(state.get("conversation_history") or [])
        response = (
            f"I could not confidently match {symptom_text} to the right department yet. "
            f"{next_missing_intake_question(collected_info, existing_questions, 'Could you describe what feels most important about this symptom?')}"
        )
        history.append({"role": "assistant", "text": response})
        return {
            "awaiting": "conversation",
            "target_department": None,
            "department_match_source": match.source,
            "department_match_confidence": match.confidence,
            "department_match_reason": match.reason,
            "retrieval_attempted": match.retrieval_attempted,
            "retrieval_confidence": match.retrieval_confidence,
            "conversation_history": history,
            "messages": history[-6:],
            "questions_asked": existing_questions + [response],
            "final_response": response,
        }

    department = match.department
    return {
        "target_department": department,
        "candidate_departments": candidate_departments or [
            {
                "department": department,
                "confidence": match.confidence,
                "matched_terms": [],
                "reason": match.reason,
            }
        ],
        "department_match_source": match.source,
        "department_match_confidence": match.confidence,
        "department_match_reason": match.reason,
        "retrieval_attempted": match.retrieval_attempted,
        "retrieval_confidence": match.retrieval_confidence,
    }
