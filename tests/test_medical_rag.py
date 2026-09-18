from app.agents import medical_rag
from app.services.rag import DepartmentMatch


def test_medical_rag_asks_clarifying_question_on_low_confidence(monkeypatch):
    monkeypatch.setattr(
        medical_rag,
        "match_department_details",
        lambda *args, **kwargs: DepartmentMatch(
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
    assert "How long have you been feeling this way?" in state["final_response"]


def test_medical_rag_sets_department_on_confident_match(monkeypatch):
    monkeypatch.setattr(
        medical_rag,
        "match_department_details",
        lambda *args, **kwargs: DepartmentMatch(
            department="Dermatology",
            confidence=0.8,
            source="vector_rerank",
        ),
    )

    result = medical_rag.medical_rag_node({"symptoms": ["rash"]})

    assert result["target_department"] == "Dermatology"
    assert result["department_match_source"] == "vector_rerank"


def test_medical_rag_avoids_repeating_clarification_topics(monkeypatch):
    monkeypatch.setattr(
        medical_rag,
        "match_department_details",
        lambda *args, **kwargs: DepartmentMatch(
            department=None,
            confidence=0.4,
            source="vector_rerank",
            needs_clarification=True,
            reason="low confidence",
        ),
    )

    result = medical_rag.medical_rag_node(
        {
            "symptoms": ["stomach pain"],
            "questions_asked": [
                "How long have you been feeling this way?",
                "Have you noticed any nausea, vomiting, fever, or blood in the stool?",
            ],
            "collected_info": {"duration": "since morning"},
        }
    )

    assert "nausea" not in result["final_response"].lower()
    assert "how long" not in result["final_response"].lower()
    assert "exact area of your body" in result["final_response"]


def test_medical_rag_surfaces_multiple_departments_for_multi_symptoms(monkeypatch):
    monkeypatch.setattr(
        medical_rag,
        "match_department_details",
        lambda *args, **kwargs: DepartmentMatch(
            department=None,
            confidence=0.78,
            source="heuristic_multi",
            needs_clarification=True,
            reason="Symptoms span more than one specialty.",
            candidate_departments=[
                {"department": "Gastroenterology", "matched_terms": ["stomach pain"], "confidence": 0.82},
                {"department": "Dermatology", "matched_terms": ["rash"], "confidence": 0.72},
            ],
        ),
    )

    state = medical_rag.medical_rag_node(
        {
            "intent": "direct_booking",
            "symptoms": ["stomach pain", "rash"],
            "user_input": "I want a doctor",
            "questions_asked": [],
        }
    )

    assert state["awaiting"] == "department_selection"
    assert state["candidate_departments"][0]["department"] == "Gastroenterology"
    assert "more than one specialty" in state["final_response"]
