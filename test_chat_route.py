import pytest
from fastapi import HTTPException

from app.api.routes import appointments as appointments_route
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
    monkeypatch.setattr(chat_route, "load_chat_session_memory", lambda **kwargs: "")
    monkeypatch.setattr(chat_route, "active_bookings_for_patient", lambda patient_id, limit=5: [])
    monkeypatch.setattr(
        chat_route,
        "append_chat_messages",
        lambda patient_id, messages, chat_session_id=None: None,
    )
    monkeypatch.setattr(chat_route, "persist_chat_session_memory", lambda **kwargs: None)
    monkeypatch.setattr(chat_route, "run_patient_chat", fake_run_patient_chat)

    response = chat_route.chat(
        chat_route.ChatRequest(message="chest pain", state={"conversation_history": []}),
        user={"patient_id": "patient-1", "name": "Pranjal"},
    )

    assert response["response"] == "Chest pain response"
    assert response["state"]["symptoms"] == ["chest pain"]


def test_upcoming_bookings_are_scoped_to_logged_in_user(monkeypatch):
    calls = []

    def fake_upcoming(patient_id, limit):
        calls.append((patient_id, limit))
        return [{"booking_id": "booking-1", "doctor": "Dr. A"}]

    monkeypatch.setattr(appointments_route, "upcoming_bookings_for_patient", fake_upcoming)

    response = appointments_route.upcoming_bookings(
        user={"patient_id": "patient-1"},
    )

    assert calls == [("patient-1", 30)]
    assert response["bookings"][0]["booking_id"] == "booking-1"


def test_previous_bookings_are_scoped_to_logged_in_user(monkeypatch):
    calls = []

    def fake_previous(patient_id, limit):
        calls.append((patient_id, limit))
        return [{"booking_id": "booking-old", "status": "completed"}]

    monkeypatch.setattr(appointments_route, "previous_bookings_for_patient", fake_previous)

    response = appointments_route.previous_bookings(
        user={"patient_id": "patient-2"},
    )

    assert calls == [("patient-2", 30)]
    assert response["bookings"][0]["status"] == "completed"


def test_cancel_booking_rejects_unmodifiable_booking(monkeypatch):
    monkeypatch.setattr(
        appointments_route,
        "cancel_patient_booking",
        lambda booking_id, patient_id: None,
    )

    with pytest.raises(HTTPException) as exc:
        appointments_route.cancel_upcoming_booking(
            "booking-1",
            user={"patient_id": "patient-1"},
        )

    assert exc.value.status_code == 400
    assert "24 hours" in exc.value.detail


def test_reschedule_options_are_scoped_to_logged_in_user(monkeypatch):
    calls = []

    def fake_options(booking_id, patient_id, requested_date, limit):
        calls.append((booking_id, patient_id, requested_date, limit))
        return [{"slot_id": "slot-1"}]

    monkeypatch.setattr(appointments_route, "reschedule_options_for_booking", fake_options)

    response = appointments_route.reschedule_options(
        "booking-1",
        date="2026-06-05",
        user={"patient_id": "patient-1"},
    )

    assert calls == [("booking-1", "patient-1", "2026-06-05", 10)]
    assert response["slots"][0]["slot_id"] == "slot-1"


def test_reschedule_booking_rejects_unavailable_or_locked_slot(monkeypatch):
    monkeypatch.setattr(
        appointments_route,
        "reschedule_patient_booking",
        lambda booking_id, patient_id, new_slot_id: None,
    )

    with pytest.raises(HTTPException) as exc:
        appointments_route.reschedule_booking(
            "booking-1",
            appointments_route.RescheduleRequest(slot_id="slot-2"),
            user={"patient_id": "patient-1"},
        )

    assert exc.value.status_code == 400
    assert "24 hours" in exc.value.detail


def test_chat_history_is_scoped_to_logged_in_user(monkeypatch):
    calls = []
    session_calls = []

    def fake_history(patient_id, limit):
        calls.append((patient_id, limit))
        return [{"role": "patient", "text": "hello"}]

    def fake_sessions(patient_id, limit):
        session_calls.append((patient_id, limit))
        return [
            {
                "chat_session_id": "session-1",
                "date": "2026-06-08",
                "messages": [{"role": "patient", "text": "hello"}],
            }
        ]

    monkeypatch.setattr(chat_route, "load_chat_history_with_timestamps", fake_history)
    monkeypatch.setattr(chat_route, "load_chat_sessions_with_messages", fake_sessions)

    response = chat_route.chat_history(user={"patient_id": "patient-1"})

    assert session_calls == [("patient-1", 100)]
    assert calls == [("patient-1", 100)]
    assert response["sessions"][0]["chat_session_id"] == "session-1"
    assert response["messages"][0]["text"] == "hello"


def test_chat_route_saves_messages_with_session_id(monkeypatch):
    saved = []

    def fake_run_patient_chat(user_input, patient_id=None, state=None):
        return {
            "chat_session_id": state["chat_session_id"],
            "final_response": "Hello there",
        }

    def fake_append(patient_id, messages, chat_session_id=None):
        saved.append((patient_id, messages, chat_session_id))

    monkeypatch.setattr(chat_route, "load_recent_chat_history", lambda patient_id: [])
    monkeypatch.setattr(chat_route, "load_chat_session_memory", lambda **kwargs: "")
    monkeypatch.setattr(chat_route, "active_bookings_for_patient", lambda patient_id, limit=5: [])
    monkeypatch.setattr(chat_route, "append_chat_messages", fake_append)
    monkeypatch.setattr(chat_route, "persist_llm_usage_records", lambda **kwargs: {})
    monkeypatch.setattr(chat_route, "persist_chat_session_memory", lambda **kwargs: None)
    monkeypatch.setattr(chat_route, "run_patient_chat", fake_run_patient_chat)

    response = chat_route.chat(
        chat_route.ChatRequest(
            message="hello",
            state={"chat_session_id": "11111111-1111-1111-1111-111111111111"},
        ),
        user={"patient_id": "patient-1", "name": "Pranjal"},
    )

    assert response["state"]["chat_session_id"] == "11111111-1111-1111-1111-111111111111"
    assert saved[0][0] == "patient-1"
    assert saved[0][2] == "11111111-1111-1111-1111-111111111111"
