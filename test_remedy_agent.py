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


def test_remedy_agent_forwards_note_to_upcoming_booking(monkeypatch):
    monkeypatch.setattr(
        remedy_agent,
        "generate_text",
        lambda *args, **kwargs: """
        {
            "patient_status": "agrees_to_forward_note",
            "reason": "Patient agreed to share the symptom update."
        }
        """,
    )

    forwarded = {}

    def fake_update_booking_note(booking_id, patient_id, booking_note):
        forwarded["booking_id"] = booking_id
        forwarded["patient_id"] = patient_id
        forwarded["booking_note"] = booking_note
        return {
            "booking_id": booking_id,
            "slot_id": "slot-1",
            "doctor": "Dr. Neetu Ramrakhiani",
            "department": "Neurology",
            "booking_note": booking_note,
            "time": "2026-06-18T10:30:00",
            "end_time": "2026-06-18T11:00:00",
            "status": "booked",
            "can_modify": True,
        }

    monkeypatch.setattr(remedy_agent, "update_booking_note", fake_update_booking_note)

    state = remedy_agent.remedy_agent_node(
        {
            "awaiting": "remedy_check",
            "user_input": "yes please do",
            "patient_id": "patient-1",
            "symptoms": ["lower back pain", "exhaustion"],
            "symptom_duration": "Since last month",
            "collected_info": {"location": "lower back", "associated_symptoms": "insomnia"},
            "confirmed_booking": {
                "booking_id": "booking-1",
                "slot_id": "slot-1",
                "doctor": "Dr. Neetu Ramrakhiani",
                "department": "Neurology",
                "time": "2026-06-18T10:30:00",
            },
            "conversation_history": [],
        }
    )

    assert forwarded["booking_id"] == "booking-1"
    assert "lower back pain" in forwarded["booking_note"]
    assert state["note_forwarded"] is True
    assert state["confirmed_booking"]["booking_note"] == forwarded["booking_note"]
    assert "forwarded these symptoms as a clinical note" in state["final_response"]


def test_remedy_agent_detects_simple_yes_to_forward_note_without_llm(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("LLM classification should not be needed for a clear yes/no reply.")

    forwarded = {}

    monkeypatch.setattr(remedy_agent, "generate_text", fail_if_called)

    def fake_update_booking_note(booking_id, patient_id, booking_note):
        forwarded["booking_note"] = booking_note
        return {
            "booking_id": booking_id,
            "slot_id": "slot-1",
            "doctor": "Dr. Neetu Ramrakhiani",
            "department": "Neurology",
            "booking_note": booking_note,
            "time": "2026-06-18T10:30:00",
            "end_time": "2026-06-18T11:00:00",
            "status": "booked",
            "can_modify": True,
        }

    monkeypatch.setattr(remedy_agent, "update_booking_note", fake_update_booking_note)

    state = remedy_agent.remedy_agent_node(
        {
            "awaiting": "remedy_check",
            "user_input": "yes please do",
            "patient_id": "patient-1",
            "symptoms": ["lower back pain"],
            "confirmed_booking": {
                "booking_id": "booking-1",
                "slot_id": "slot-1",
                "doctor": "Dr. Neetu Ramrakhiani",
                "department": "Neurology",
                "time": "2026-06-18T10:30:00",
            },
            "conversation_history": [],
        }
    )

    assert forwarded["booking_note"]
    assert state["note_forwarded"] is True
    assert "clinical note" in state["final_response"].lower()
