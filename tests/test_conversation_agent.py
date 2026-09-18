from app.agents import conversation_agent


def test_conversation_agent_avoids_repeating_a_previously_asked_topic(monkeypatch):
    def fake_generate_text(*args, **kwargs) -> str:
        return """
        {
            "intent": "continue_intake",
            "has_enough_info": false,
            "next_question": "Have you noticed any nausea, vomiting, fever, or blood in the stool?",
            "collected_info": {}
        }
        """

    monkeypatch.setattr(conversation_agent, "generate_text", fake_generate_text)

    state = {
        "awaiting": "conversation",
        "intent": "triage_symptoms",
        "symptoms": ["loose motion", "stomach pain"],
        "questions_asked": [
            "When did this start?",
            "Have you noticed any nausea, vomiting, fever, or blood in the stool?",
        ],
        "conversation_history": [
            {"role": "assistant", "text": "When did this start?"},
            {"role": "patient", "text": "since morning"},
            {"role": "assistant", "text": "Have you noticed any nausea, vomiting, fever, or blood in the stool?"},
            {"role": "patient", "text": "no"},
        ],
        "collected_info": {},
        "greeted": True,
    }

    result = conversation_agent.conversation_agent_node(state)

    assert "nausea" not in result["final_response"].lower()
    assert "vomiting" not in result["final_response"].lower()
    assert "exact area of your body" in result["final_response"]
    assert result["awaiting"] == "conversation"


def test_conversation_agent_recovers_from_malformed_llm_output(monkeypatch):
    monkeypatch.setattr(conversation_agent, "generate_text", lambda *args, **kwargs: "```json\nnot valid json\n```")

    state = {
        "awaiting": "conversation",
        "intent": "triage_symptoms",
        "symptoms": ["loose motion", "stomach pain"],
        "questions_asked": [
            "How long have you been feeling this way?",
            "Have you noticed any nausea, vomiting, fever, or blood in the stool?",
        ],
        "conversation_history": [
            {"role": "assistant", "text": "How long have you been feeling this way?"},
            {"role": "patient", "text": "since morning"},
            {"role": "assistant", "text": "Have you noticed any nausea, vomiting, fever, or blood in the stool?"},
            {"role": "patient", "text": "no"},
        ],
        "collected_info": {"duration": "since morning"},
        "greeted": True,
    }

    result = conversation_agent.conversation_agent_node(state)

    assert result["final_response"] != "Could you tell me a little more about what you are feeling and when it started?"
    assert "exact area of your body" in result["final_response"]
    assert result["awaiting"] == "conversation"


def test_conversation_agent_stops_when_patient_says_they_have_shared_everything(monkeypatch):
    monkeypatch.setattr(
        conversation_agent,
        "generate_text",
        lambda *args, **kwargs: """
        {
            "intent": "continue_intake",
            "has_enough_info": false,
            "next_question": "Have you noticed any changes in appetite?",
            "collected_info": {}
        }
        """,
    )

    state = {
        "awaiting": "conversation",
        "intent": "triage_symptoms",
        "symptoms": ["feeling exhausted", "anxiety"],
        "questions_asked": ["How long have you been feeling this way?"],
        "conversation_history": [
            {"role": "assistant", "text": "How long have you been feeling this way?"},
            {"role": "patient", "text": "since last night"},
        ],
        "collected_info": {"duration": "since last night"},
        "greeted": True,
        "user_input": "i have mentioned everything that is all",
    }

    result = conversation_agent.conversation_agent_node(state)

    assert result["awaiting"] is None
    assert result["remedy_requested"] is True
    assert "next_question" not in result
