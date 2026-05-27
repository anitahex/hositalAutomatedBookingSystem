from app.agents import remedy_agent


def test_remedy_agent_fallback_is_specific_for_rash(monkeypatch):
    monkeypatch.setattr(remedy_agent, "generate_text", lambda _: "not json")

    state = remedy_agent.remedy_agent_node(
        {
            "symptoms": ["rash"],
            "severity": "severe",
            "collected_info": {"onset": "sudden"},
            "conversation_history": [],
        }
    )

    assert state["awaiting"] == "remedy_check"
    assert "skin rash" in state["final_response"]
    assert "cool compress" in state["final_response"]


def test_remedy_agent_treats_not_better_as_persisting():
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
