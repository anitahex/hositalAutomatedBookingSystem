from app.services import rag


class FakeMatch:
    def __init__(self, department: str | None, score: float = 0.9, chunk_text: str = ""):
        self.payload = {"department": department, "chunk_text": chunk_text} if department is not None else {}
        self.score = score


def test_match_department_corrects_general_physician_for_skin_rash(monkeypatch):
    monkeypatch.setattr(rag, "embed_query", lambda _: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        rag,
        "search_clinical_knowledge",
        lambda query_vector, limit: [FakeMatch("General Physician")],
    )
    monkeypatch.setattr(
        rag,
        "generate_text",
        lambda _: """
        {
            "department": "Dermatology",
            "confidence": 0.9,
            "needs_clarification": false,
            "reason": "The symptom needs skin-specialist routing."
        }
        """,
    )

    assert rag.match_department(["rash"]) == "Dermatology"


def test_match_department_uses_vector_specialist_when_available(monkeypatch):
    monkeypatch.setattr(rag, "embed_query", lambda _: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        rag,
        "search_clinical_knowledge",
        lambda query_vector, limit: [FakeMatch("Dermatology")],
    )

    assert rag.match_department(["rash"]) == "Dermatology"


def test_low_confidence_general_physician_needs_clarification(monkeypatch):
    monkeypatch.setattr(rag, "embed_query", lambda _: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        rag,
        "search_clinical_knowledge",
        lambda query_vector, limit: [FakeMatch("General Physician", score=0.51)],
    )

    match = rag.match_department_details(["unusual discomfort"])

    assert match.department is None
    assert match.needs_clarification is True


def test_llm_context_decision_can_choose_specialist_over_weak_general(monkeypatch):
    monkeypatch.setattr(rag, "embed_query", lambda _: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        rag,
        "search_clinical_knowledge",
        lambda query_vector, limit: [
            FakeMatch("General Physician", score=0.51),
            FakeMatch("Dermatology", score=0.47),
        ],
    )
    monkeypatch.setattr(
        rag,
        "generate_text",
        lambda _: """
        {
            "department": "Dermatology",
            "confidence": 0.86,
            "needs_clarification": false,
            "reason": "The retrieved context and symptom point to dermatology."
        }
        """,
    )

    match = rag.match_department_details(["skin rash"])

    assert match.department == "Dermatology"
    assert match.needs_clarification is False


def test_back_pain_context_routes_to_orthopedics_when_vector_is_weak(monkeypatch):
    monkeypatch.setattr(rag, "embed_query", lambda _: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        rag,
        "search_clinical_knowledge",
        lambda query_vector, limit: [FakeMatch("General Physician", score=0.2)],
    )
    monkeypatch.setattr(
        rag,
        "generate_text",
        lambda _: """
        {
            "department": null,
            "confidence": 0,
            "needs_clarification": true,
            "reason": "The language model was unavailable."
        }
        """,
    )

    match = rag.match_department_details(
        ["back pain"],
        {
            "duration": "few months",
            "location": "lower back",
            "severity_pattern": "sharp, comes and goes",
            "cause": "lifting something",
            "associated_symptoms": "weakness in legs",
            "existing_conditions": "low B12 and D3",
            "lifestyle": "sitting on a chair almost 8 hours a day",
            "daily_activity": "gym",
        },
    )

    assert match.department == "Orthopedics"
    assert match.needs_clarification is False
