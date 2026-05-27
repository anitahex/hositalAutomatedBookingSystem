from app.agents import medical_rag
from app.services.rag import DepartmentMatch


def test_medical_rag_asks_clarifying_question_on_low_confidence(monkeypatch):
    monkeypatch.setattr(
        medical_rag,
        "match_department_details",
        lambda symptoms: DepartmentMatch(
            department=None,
            confidence=0.51,
            source="vector_rerank",
            needs_clarification=True,
            reason="low confidence",
        ),
    )

    state = medical_rag.medical_rag_node({"symptoms": ["unusual discomfort"]})

    assert state["awaiting"] == "conversation"
    assert state["target_department"] is None
    assert "could not confidently match" in state["final_response"]


def test_medical_rag_sets_department_on_confident_match(monkeypatch):
    monkeypatch.setattr(
        medical_rag,
        "match_department_details",
        lambda symptoms: DepartmentMatch(
            department="Dermatology",
            confidence=0.8,
            source="vector_rerank",
        ),
    )

    assert medical_rag.medical_rag_node({"symptoms": ["rash"]}) == {
        "target_department": "Dermatology"
    }
