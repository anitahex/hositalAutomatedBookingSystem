from app.agents import appointment_booker
from app.agents import conversation_agent
from app.agents.graph import run_patient_chat
from app.agents.supervisor import supervisor_node


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
        "classify_booking_menu_reply",
        lambda state, menu_type: appointment_booker.BookingMenuDecision(
            action="select_option",
            selected_value="1",
            reason="Selected by number.",
        ),
    )
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
        "classify_booking_menu_reply",
        lambda state, menu_type: appointment_booker.BookingMenuDecision(
            action="select_option",
            selected_value="1",
            reason="Selected by number.",
        ),
    )
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

    assert state["awaiting"] == "end_confirmation"
    assert state["selected_slot_id"] == "slot-1"
    assert state["confirmed_bookings"][0]["slot_id"] == "slot-1"
    assert "Your appointment is booked" in state["final_response"]
    assert "should we end the chat" in state["final_response"]


def test_supervisor_ends_chat_when_patient_confirms_end_prompt():
    state = supervisor_node(
        {
            "awaiting": "end_confirmation",
            "user_input": "yes",
            "symptoms": ["sharp ear pain"],
            "target_department": "Otolaryngology",
        }
    )

    assert state["next_agent"] == "finish"
    assert state["awaiting"] is None
    assert state["chat_closed"] is True
    assert "Take care" in state["final_response"]


def test_supervisor_answers_profile_query_without_triage():
    state = supervisor_node(
        {
            "user_input": "what is my name and age",
            "patient_profile": {
                "name": "Jaffer",
                "age": 26,
                "blood_group": "B+",
                "health_issues": "cough and cold",
            },
        }
    )

    assert state["next_agent"] == "finish"
    assert "Jaffer" in state["final_response"]
    assert "26" in state["final_response"]
    assert "chat_closed" not in state


def test_supervisor_does_not_start_end_confirmation_for_casual_thanks():
    state = supervisor_node(
        {
            "user_input": "thank you",
            "patient_profile": {
                "name": "Anit",
                "age": 26,
            },
        }
    )

    assert state["next_agent"] == "finish"
    assert state["awaiting"] is None
    assert state["chat_closed"] is False
    assert "Tell me your symptoms" in state["final_response"]


def test_supervisor_allows_symptoms_to_interrupt_end_confirmation():
    state = supervisor_node(
        {
            "awaiting": "end_confirmation",
            "user_input": "i need help with severe leg pain",
            "patient_profile": {
                "name": "Anit",
                "age": 26,
            },
        }
    )

    assert state["next_agent"] == "triage_router"
    assert state["awaiting"] is None
    assert state["intent"] is None
    assert state["doctor_options"] == []
    assert state["slot_options"] == []


def test_supervisor_rejects_non_medical_unsafe_question():
    state = supervisor_node(
        {
            "awaiting": "doctor_selection",
            "user_input": "how to create bomb",
            "doctor_options": [{"doctor_id": "doc-1", "doctor_name": "Dr. A"}],
            "patient_profile": {"name": "Anit", "age": 26},
        }
    )

    assert state["next_agent"] == "finish"
    assert state["chat_closed"] is False
    assert "only for health-related support" in state["final_response"]
    assert "doctor appointment" in state["final_response"]


def test_supervisor_answers_upcoming_booking_lookup_during_booking_menu():
    state = supervisor_node(
        {
            "awaiting": "doctor_selection",
            "user_input": "can you tell me my upcoming bookings?",
            "doctor_options": [{"doctor_id": "doc-1", "doctor_name": "Dr. A"}],
            "active_appointments": [
                {
                    "doctor": "Dr. Rao",
                    "department": "Neurology",
                    "time": "2026-06-09 09:00:00",
                }
            ],
            "patient_profile": {"name": "Anit", "age": 26},
        }
    )

    assert state["next_agent"] == "finish"
    assert state["chat_closed"] is False
    assert "upcoming bookings" in state["final_response"]
    assert "Dr. Rao" in state["final_response"]


def test_supervisor_routes_requested_department_directly_to_booking():
    state = supervisor_node(
        {
            "user_input": "I have chest pain but I want dermatology appointment",
            "symptoms": ["chest pain"],
            "severity": "moderate",
        }
    )

    assert state["next_agent"] == "appointment_booker"
    assert state["intent"] == "direct_booking"
    assert state["target_department"] == "Dermatology"
    assert state["requested_department"] == "Dermatology"


def test_supervisor_routes_generic_doctor_request_to_department_matching():
    state = supervisor_node(
        {
            "user_input": "yes i want to see a doctor",
            "symptoms": ["severe leg pain"],
            "severity": "severe",
        }
    )

    assert state["next_agent"] == "medical_rag"
    assert state["intent"] == "direct_booking"
    assert state.get("requested_doctor_name") is None


def test_booker_uses_requested_department_instead_of_symptom_recommendation(monkeypatch):
    monkeypatch.setattr(
        appointment_booker,
        "available_doctors_for_department",
        lambda department, limit: [
            {
                "doctor_id": "doc-derm",
                "doctor_name": "Dr. Skin",
                "experience_years": 11,
                "next_available_time": "2026-05-21T09:00:00",
                "available_slot_count": 3,
            }
        ],
    )

    state = appointment_booker.appointment_booker_node(
        {
            "target_department": "Dermatology",
            "requested_department": "Dermatology",
            "symptoms": ["chest pain"],
            "severity": "moderate",
            "intent": "direct_booking",
            "user_input": "I want dermatology",
        }
    )

    assert state["awaiting"] == "doctor_selection"
    assert state["doctor_options"][0]["doctor_name"] == "Dr. Skin"
    assert "You asked for the **Dermatology** department" in state["final_response"]


def test_booker_uses_requested_date_for_department_availability(monkeypatch):
    from datetime import date, timedelta

    calls = []
    requested_date = (date.today() + timedelta(days=1)).isoformat()

    def fake_available_on_date(department, requested_date, limit):
        calls.append((department, requested_date, limit))
        return [
            {
                "doctor_id": "doc-neuro",
                "doctor_name": "Dr. Neuro",
                "experience_years": 12,
                "next_available_time": "2026-06-04T09:00:00",
                "available_slot_count": 2,
            }
        ]

    monkeypatch.setattr(
        appointment_booker,
        "available_doctors_for_department_on_date",
        fake_available_on_date,
    )

    state = appointment_booker.appointment_booker_node(
        {
            "target_department": "Neurology",
            "requested_date": requested_date,
            "symptoms": ["severe leg pain", "B12 medication"],
            "severity": "severe",
            "intent": "direct_booking",
            "user_input": "can you book an appointment for tomorrow",
        }
    )

    assert calls == [("Neurology", requested_date, 5)]
    assert state["awaiting"] == "doctor_selection"
    assert state["doctor_options"][0]["doctor_name"] == "Dr. Neuro"
    assert f"Showing availability for {requested_date}" in state["final_response"]


def test_booker_rejects_dates_more_than_one_week_ahead():
    from datetime import date, timedelta

    state = appointment_booker.appointment_booker_node(
        {
            "target_department": "Neurology",
            "requested_date": (date.today() + timedelta(days=8)).isoformat(),
            "intent": "direct_booking",
            "user_input": "book after 8 days",
        }
    )

    assert state["awaiting"] == "date_selection"
    assert len(state["date_options"]) == 8
    assert "7 days ahead" in state["final_response"]


def test_booker_asks_for_another_date_when_no_doctors_available(monkeypatch):
    from datetime import date, timedelta

    monkeypatch.setattr(
        appointment_booker,
        "available_doctors_for_department_on_date",
        lambda department, requested_date, limit: [],
    )

    state = appointment_booker.appointment_booker_node(
        {
            "target_department": "Neurology",
            "requested_date": (date.today() + timedelta(days=1)).isoformat(),
            "intent": "direct_booking",
            "user_input": "book tomorrow",
        }
    )

    assert state["awaiting"] == "date_selection"
    assert state["date_options"]
    assert "Which day would you prefer" in state["final_response"]


def test_booker_uses_requested_doctor_when_unique_match(monkeypatch):
    monkeypatch.setattr(
        appointment_booker,
        "available_doctors_by_name",
        lambda name, limit: [
            {
                "doctor_id": "doc-tongia",
                "doctor_name": "Dr. R. Tongia",
                "department": "Cardiology",
                "experience_years": 53,
                "next_available_time": "2026-05-21T09:00:00",
                "available_slot_count": 2,
            }
        ],
    )
    monkeypatch.setattr(
        appointment_booker,
        "available_slots_for_doctor",
        lambda doctor_id, limit: [
            {
                "slot_id": "slot-1",
                "start_time": "2026-05-21T09:00:00",
                "end_time": "2026-05-21T09:30:00",
                "doctor_name": "Dr. R. Tongia",
            }
        ],
    )

    state = appointment_booker.appointment_booker_node(
        {
            "requested_doctor_name": "Dr. R. Tongia",
            "intent": "direct_booking",
            "user_input": "book Dr. R. Tongia",
        }
    )

    assert state["awaiting"] == "slot_selection"
    assert state["selected_doctor_name"] == "Dr. R. Tongia"
    assert state["target_department"] == "Cardiology"
    assert "Available slots" in state["final_response"]


def test_closed_chat_does_not_continue_old_medical_flow():
    state = run_patient_chat(
        "sure",
        state={
            "chat_closed": True,
            "symptoms": ["chest pain"],
            "target_department": "Cardiology",
            "awaiting": None,
        },
    )

    assert state["next_agent"] == "finish"
    assert state["chat_closed"] is True
    assert state["awaiting"] is None
    assert "closed" in state["final_response"]


def test_supervisor_keeps_unclear_end_confirmation_in_confirmation_state(monkeypatch):
    monkeypatch.setattr(
        "app.agents.supervisor.generate_router_text",
        lambda *args, **kwargs: '{"next_agent":"continue_current","intent":null,"reason":"unclear confirmation"}',
    )

    state = supervisor_node(
        {
            "awaiting": "end_confirmation",
            "user_input": "maybe",
            "symptoms": ["sharp ear pain"],
            "target_department": "Otolaryngology",
        }
    )

    assert state["next_agent"] == "finish"
    assert state["awaiting"] == "end_confirmation"
    assert state["chat_closed"] is False
    assert "reply yes to end" in state["final_response"]


def test_booker_keeps_multiple_confirmed_bookings(monkeypatch):
    monkeypatch.setattr(
        appointment_booker,
        "classify_booking_menu_reply",
        lambda state, menu_type: appointment_booker.BookingMenuDecision(
            action="select_option",
            selected_value="1",
            reason="Selected by number.",
        ),
    )
    monkeypatch.setattr(
        appointment_booker,
        "book_selected_slot",
        lambda slot_id, patient_id: {
            "booking_id": f"booking-{slot_id}",
            "slot_id": slot_id,
            "doctor_name": "Dr. B",
            "department": "Dermatology",
            "start_time": "2026-05-22T10:00:00",
        },
    )

    state = appointment_booker.appointment_booker_node(
        {
            "awaiting": "slot_selection",
            "user_input": "1",
            "slot_options": [{"slot_id": "slot-2", "start_time": "2026-05-22T10:00:00"}],
            "confirmed_bookings": [{"booking_id": "booking-slot-1", "slot_id": "slot-1"}],
            "patient_id": "patient-1",
        }
    )

    assert len(state["confirmed_bookings"]) == 2
    assert state["confirmed_booking"]["slot_id"] == "slot-2"


def test_booker_cancels_selected_appointment(monkeypatch):
    monkeypatch.setattr(
        appointment_booker,
        "cancel_booking",
        lambda reference, patient_id: {
            "booking_id": reference,
            "slot_id": "slot-1",
            "doctor": "Dr. A",
            "department": "Cardiology",
            "time": "2026-05-21 09:00:00",
            "end_time": "2026-05-21 09:30:00",
        },
    )

    state = appointment_booker.appointment_booker_node(
        {
            "awaiting": "cancellation_selection",
            "user_input": "1",
            "patient_id": "patient-1",
            "cancellation_options": [
                {
                    "booking_id": "booking-1",
                    "slot_id": "slot-1",
                    "doctor": "Dr. A",
                    "department": "Cardiology",
                    "time": "2026-05-21 09:00:00",
                }
            ],
            "confirmed_bookings": [
                {
                    "booking_id": "booking-1",
                    "slot_id": "slot-1",
                    "doctor": "Dr. A",
                    "department": "Cardiology",
                    "time": "2026-05-21 09:00:00",
                }
            ],
        }
    )

    assert state["awaiting"] == "end_confirmation"
    assert state["confirmed_bookings"] == []
    assert "has been cancelled" in state["final_response"]


def test_booker_gives_remedies_when_patient_declines(monkeypatch):
    monkeypatch.setattr(
        appointment_booker,
        "classify_booking_menu_reply",
        lambda state, menu_type: appointment_booker.BookingMenuDecision(
            action="decline_booking",
            selected_value=None,
            reason="Patient declined booking.",
        ),
    )
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


def test_conversation_stops_when_structured_intake_is_sufficient(monkeypatch):
    monkeypatch.setattr(
        conversation_agent,
        "generate_text",
        lambda *args, **kwargs: """
        {
            "intent": "continue_intake",
            "has_enough_info": false,
            "next_question": "Can you tell me more about your gym routine?",
            "collected_info": {
                "duration": "few months",
                "location": "lower back",
                "severity_pattern": "sharp, comes and goes",
                "cause": "lifting something",
                "associated_symptoms": "weakness in legs",
                "existing_conditions": "low B12 and D3",
                "lifestyle": "sitting on a chair almost 8 hours a day",
                "daily_activity": "gym"
            }
        }
        """,
    )

    state = conversation_agent.conversation_agent_node(
        {
            "awaiting": "conversation",
            "user_input": "gym",
            "symptoms": ["back pain"],
            "severity": "moderate",
            "questions_asked": [
                "How long has this been happening?",
                "Where exactly is the pain?",
                "What triggers it?",
            ],
        }
    )

    assert state["awaiting"] is None
    assert "final_response" not in state


def test_conversation_avoids_repeating_duration_question(monkeypatch):
    monkeypatch.setattr(
        conversation_agent,
        "generate_text",
        lambda *args, **kwargs: """
        {
            "intent": "continue_intake",
            "has_enough_info": false,
            "next_question": "How long has this leg pain been happening?",
            "collected_info": {
                "location": "calves",
                "severity_pattern": "worse at night",
                "associated_symptoms": "throbbing"
            }
        }
        """,
    )

    state = conversation_agent.conversation_agent_node(
        {
            "awaiting": "conversation",
            "user_input": "it is worse at night",
            "symptoms": ["leg pain"],
            "severity": "severe",
            "questions_asked": ["How long have you been experiencing this leg pain?"],
        }
    )

    assert state["awaiting"] == "conversation"
    assert "how long" not in state["final_response"].lower()


def test_conversation_finishes_after_open_ended_fallback_answer(monkeypatch):
    monkeypatch.setattr(
        conversation_agent,
        "generate_text",
        lambda *args, **kwargs: """
        {
            "intent": "continue_intake",
            "has_enough_info": false,
            "next_question": "What feels most important about this symptom that I have not asked yet?",
            "collected_info": {
                "associated_symptoms": "nausea, weakness, possible diarrhea"
            }
        }
        """,
    )

    state = conversation_agent.conversation_agent_node(
        {
            "awaiting": "conversation",
            "user_input": "i feel weak and i feel like i am about to have diarrhea",
            "symptoms": ["stomach ache"],
            "severity": "moderate",
            "collected_info": {
                "duration": "since last night",
                "cause": "oily food",
                "location": "lower abdomen",
                "associated_symptoms": "nausea",
                "severity_pattern": "not constant",
                "medications": "none",
            },
            "questions_asked": [
                "Can you tell me when it started and if there was anything specific that triggered it?",
                "Where exactly do you feel it most strongly?",
                "Have you noticed any other symptoms along with the stomach ache, such as nausea, vomiting, or fever?",
                "Is it constant, or does it come and go?",
                "Are you taking any medicines, or do you have allergies or existing conditions I should know about?",
                "What feels most important about this symptom that I have not asked yet?",
            ],
        }
    )

    assert state["awaiting"] is None
    assert "final_response" not in state


def test_conversation_finishes_when_patient_has_nothing_more_after_fallback(monkeypatch):
    monkeypatch.setattr(
        conversation_agent,
        "generate_text",
        lambda *args, **kwargs: """
        {
            "intent": "continue_intake",
            "has_enough_info": false,
            "next_question": "What feels most important about this symptom that I have not asked yet?",
            "collected_info": {}
        }
        """,
    )

    state = conversation_agent.conversation_agent_node(
        {
            "awaiting": "conversation",
            "user_input": "there is nothing more",
            "symptoms": ["stomach ache"],
            "severity": "moderate",
            "collected_info": {
                "duration": "since last night",
                "cause": "oily food",
                "location": "lower abdomen",
                "associated_symptoms": "nausea",
                "severity_pattern": "not constant",
                "medications": "none",
            },
            "questions_asked": [
                "Can you tell me when it started and if there was anything specific that triggered it?",
                "Where exactly do you feel it most strongly?",
                "Have you noticed any other symptoms along with the stomach ache, such as nausea, vomiting, or fever?",
                "Is it constant, or does it come and go?",
                "Are you taking any medicines, or do you have allergies or existing conditions I should know about?",
                "What feels most important about this symptom that I have not asked yet?",
            ],
        }
    )

    assert state["awaiting"] is None
    assert "final_response" not in state
