from app.agents import remedy_agent


def test_remedy_agent_uses_generic_clinical_safety_fallback(monkeypatch):
    monkeypatch.setattr(remedy_agent, "generate_text", lambda *args, **kwargs: "not json")

    state = remedy_agent.remedy_agent_node(
        {
            "symptoms": ["rash"],
            "severity": "severe",
            "collected_info": {"onset": "sudden"},
            "conversation_history": [],
        }
    )

    assert state["awaiting"] == "remedy_check"
    assert "trouble generating tailored care advice" in state["final_response"]
    assert "seek medical care" in state["final_response"]


def test_remedy_agent_uses_llm_follow_up_classification(monkeypatch):
    def fake_generate_text(*args, **kwargs) -> str:
        return """
        {
            "patient_status": "persisting_or_worsening",
            "reason": "Patient says symptoms are not improving and wants doctor help."
        }
        """

    monkeypatch.setattr(remedy_agent, "generate_text", fake_generate_text)

    state = remedy_agent.remedy_agent_node(
        {
            "awaiting": "remedy_check",
            "user_input": "still not better, i want to see a doctor",
            "conversation_history": [],
        }
    )

    assert state["awaiting"] is None
    assert state["persisting"] is True
    assert "final_response" not in state
