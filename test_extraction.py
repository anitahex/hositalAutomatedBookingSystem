from app.agents import triage_router


def test_triage_router_extracts_intent_and_symptoms(monkeypatch):
    def fake_generate_text(*args, **kwargs) -> str:
        return """
        {
            "intent": "triage_symptoms",
            "symptoms": ["dizziness", "chest tightness"],
            "severity": "severe"
        }
        """

    monkeypatch.setattr(triage_router, "generate_text", fake_generate_text)

    state = triage_router.triage_router_node(
        {"user_input": "I woke up feeling super dizzy and my chest is tight."}
    )

    assert state["intent"] == "triage_symptoms"
    assert state["symptoms"] == ["dizziness", "chest tightness"]
    assert state["severity"] == "severe"
    assert "final_response" not in state


def test_triage_router_uses_llm_for_body_part_pain_and_urgency(monkeypatch):
    def fake_generate_text(*args, **kwargs) -> str:
        return """
        {
            "intent": "triage_symptoms",
            "symptoms": ["leg pain"],
            "severity": "severe"
        }
        """

    monkeypatch.setattr(triage_router, "generate_text", fake_generate_text)

    state = triage_router.triage_router_node({"user_input": "severe leg pain"})

    assert state["intent"] == "triage_symptoms"
    assert state["symptoms"] == ["leg pain"]
    assert state["severity"] == "severe"


def test_triage_router_clarifies_on_bad_llm_output(monkeypatch):
    monkeypatch.setattr(triage_router, "generate_text", lambda *args, **kwargs: "not json")

    state = triage_router.triage_router_node({"user_input": "severe leg pain"})

    assert state["intent"] == "unclear"
    assert state["symptoms"] == []
    assert state["severity"] == "mild"
    assert "could not reliably understand" in state["final_response"].lower()


def test_triage_router_returns_clarification_when_llm_and_fast_extract_fail(monkeypatch):
    monkeypatch.setattr(triage_router, "generate_text", lambda *args, **kwargs: "not json")

    state = triage_router.triage_router_node({"user_input": "help"})

    assert state["intent"] == "unclear"
    assert state["symptoms"] == []
    assert state["severity"] == "mild"
    assert "could not reliably understand" in state["final_response"]
