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


def test_keyword_rerank_can_choose_specialist_over_weak_general(monkeypatch):
    monkeypatch.setattr(rag, "embed_query", lambda _: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        rag,
        "search_clinical_knowledge",
        lambda query_vector, limit: [
            FakeMatch("General Physician", score=0.51),
            FakeMatch("Dermatology", score=0.47),
        ],
    )

    match = rag.match_department_details(["skin rash"])

    assert match.department == "Dermatology"
    assert match.needs_clarification is False
