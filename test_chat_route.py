from app.api.routes import chat as chat_route


def test_chat_route_respects_explicit_empty_conversation_history(monkeypatch):
    def fail_if_loaded(patient_id):
        raise AssertionError("Saved chat history should not load for a reset chat.")

    def fake_run_patient_chat(user_input, patient_id=None, state=None):
        assert state["conversation_history"] == []
        return {
            "conversation_history": [{"role": "patient", "text": user_input}],
            "symptoms": ["chest pain"],
            "final_response": "Chest pain response",
        }

    monkeypatch.setattr(chat_route, "load_recent_chat_history", fail_if_loaded)
    monkeypatch.setattr(chat_route, "active_bookings_for_patient", lambda patient_id, limit=5: [])
    monkeypatch.setattr(chat_route, "append_chat_messages", lambda patient_id, messages: None)
    monkeypatch.setattr(chat_route, "run_patient_chat", fake_run_patient_chat)

    response = chat_route.chat(
        chat_route.ChatRequest(message="chest pain", state={"conversation_history": []}),
        user={"patient_id": "patient-1", "name": "Pranjal"},
    )

    assert response["response"] == "Chest pain response"
    assert response["state"]["symptoms"] == ["chest pain"]
