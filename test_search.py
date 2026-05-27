from types import SimpleNamespace

from app.services import rag


def test_match_department_returns_department_from_qdrant_payload(monkeypatch):
    monkeypatch.setattr(rag, "embed_query", lambda _: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        rag,
        "search_clinical_knowledge",
        lambda query_vector, limit: [
            SimpleNamespace(payload={"department": "Neurology"})
        ],
    )

    department = rag.match_department(
        ["severe headache", "stiff neck", "sudden loss of speech"]
    )

    assert department == "Neurology"


def test_match_department_defaults_to_general_physician_without_symptoms():
    assert rag.match_department([]) == "General Physician"


def test_match_department_defaults_to_general_physician_without_matches(monkeypatch):
    monkeypatch.setattr(rag, "embed_query", lambda _: [0.1, 0.2, 0.3])
    monkeypatch.setattr(rag, "search_clinical_knowledge", lambda query_vector, limit: [])

    assert rag.match_department(["unclear symptom"]) == "General Physician"
