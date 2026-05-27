from app.agents import appointment_booker


def test_booker_asks_empathetic_symptom_follow_up_before_doctors():
    state = appointment_booker.appointment_booker_node(
        {
            "user_input": "I have chest tightness",
            "symptoms": ["chest tightness"],
            "severity": "severe",
        }
    )

    assert state["awaiting"] == "symptom_follow_up"
    assert "I noted: chest tightness" in state["final_response"]
    assert "since when" in state["final_response"]


def test_booker_captures_symptom_follow_up_answer():
    state = appointment_booker.appointment_booker_node(
        {
            "awaiting": "symptom_follow_up",
            "user_input": "Since yesterday and it is getting worse",
        }
    )

    assert state["awaiting"] is None
    assert state["follow_up_answer"] == "Since yesterday and it is getting worse"
    assert state["symptom_duration"] == "Since yesterday and it is getting worse"


def test_booker_recommends_doctors_and_asks_for_preference(monkeypatch):
    monkeypatch.setattr(
        appointment_booker,
        "available_doctors_for_department",
        lambda department, limit: [
            {
                "doctor_id": "doc-1",
                "doctor_name": "Dr. A",
                "experience_years": 10,
                "next_available_time": "2026-05-21T09:00:00",
                "available_slot_count": 3,
            }
        ],
    )

    state = appointment_booker.appointment_booker_node(
        {
            "target_department": "Cardiology",
            "severity": "severe",
            "follow_up_answer": "Since yesterday and worsening",
            "user_input": "chest pain",
        }
    )

    assert state["awaiting"] == "doctor_selection"
    assert state["doctor_options"][0]["doctor_name"] == "Dr. A"
    assert "Please reply with the doctor number" in state["final_response"]


def test_booker_shows_slots_after_doctor_selection(monkeypatch):
    monkeypatch.setattr(
        appointment_booker,
        "available_slots_for_doctor",
        lambda doctor_id, limit: [
            {
                "slot_id": "slot-1",
                "start_time": "2026-05-21T09:00:00",
                "end_time": "2026-05-21T09:30:00",
                "doctor_name": "Dr. A",
            }
        ],
    )

    state = appointment_booker.appointment_booker_node(
        {
            "awaiting": "doctor_selection",
            "user_input": "1",
            "doctor_options": [{"doctor_id": "doc-1", "doctor_name": "Dr. A"}],
        }
    )

    assert state["awaiting"] == "slot_selection"
    assert state["selected_doctor_id"] == "doc-1"
    assert state["slot_options"][0]["slot_id"] == "slot-1"


def test_booker_books_selected_slot(monkeypatch):
    monkeypatch.setattr(
        appointment_booker,
        "book_selected_slot",
        lambda slot_id, patient_id: {
            "slot_id": slot_id,
            "doctor_name": "Dr. A",
            "department": "Cardiology",
            "start_time": "2026-05-21T09:00:00",
        },
    )

    state = appointment_booker.appointment_booker_node(
        {
            "awaiting": "slot_selection",
            "user_input": "1",
            "slot_options": [{"slot_id": "slot-1", "start_time": "2026-05-21T09:00:00"}],
            "patient_id": "patient-1",
        }
    )

    assert state["awaiting"] is None
    assert state["selected_slot_id"] == "slot-1"
    assert "Your appointment is booked" in state["final_response"]


def test_booker_gives_remedies_when_patient_declines():
    state = appointment_booker.appointment_booker_node(
        {
            "awaiting": "slot_selection",
            "user_input": "no",
            "target_department": "Cardiology",
            "severity": "severe",
        }
    )

    assert state["awaiting"] is None
    assert "No appointment has been booked" in state["final_response"]
    assert "please see a Cardiology doctor" in state["final_response"]
