from datetime import datetime

from app.agents import appointment_booker
from app.agents import conversation_agent
from app.agents.graph import run_patient_chat
from app.agents.supervisor import continue_current_node, supervisor_node
from app.agents.supervisor import _extract_requested_department
from app.services import appointments as appointments_service


def test_booker_asks_empathetic_symptom_follow_up_before_doctors():
    state = appointment_booker.appointment_booker_node(
        {
            "user_input": "I have chest tightness",
            "symptoms": ["chest tightness"],
            "severity": "severe",
        }
    )

    assert state["awaiting"] is None
    assert state["booking_active"] is False


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
    assert state["collected_info"]["duration"] == "since yesterday"


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


def test_booker_normalizes_misspelled_department_before_lookup(monkeypatch):
    seen = {}

    def fake_available_doctors(department, limit):
        seen["department"] = department
        seen["limit"] = limit
        return [
            {
                "doctor_id": "doc-psy-1",
                "doctor_name": "Dr. Sunita Panday",
                "experience_years": 19,
                "next_available_time": "2026-06-15T09:00:00",
                "available_slot_count": 2,
            }
        ]

    monkeypatch.setattr(
        appointment_booker,
        "available_doctors_for_department",
        fake_available_doctors,
    )

    state = appointment_booker.appointment_booker_node(
        {
            "target_department": "Psychitary",
            "requested_department": "Psychitary",
            "user_input": "book an appointment with psychitary department",
        }
    )

    assert seen["department"] == "Psychiatry"
    assert state["awaiting"] == "doctor_selection"
    assert "Psychiatry" in state["final_response"]
    assert "Dr. Sunita Panday" in state["final_response"]


def test_booker_asks_for_symptoms_instead_of_defaulting_department(monkeypatch):
    calls = []

    def fake_available_doctors_for_department(department, limit):
        calls.append(("department", department, limit))
        return []

    monkeypatch.setattr(
        appointment_booker,
        "available_doctors_for_department",
        fake_available_doctors_for_department,
    )

    state = appointment_booker.appointment_booker_node(
        {
            "user_input": "I have heart burn sensation",
            "symptoms": ["heart burn sensation"],
        }
    )

    assert calls == []
    assert state["awaiting"] is None
    assert state["booking_active"] is False


def test_supervisor_extracts_misspelled_department():
    assert _extract_requested_department("book an appointment with the psychitary department") == "Psychiatry"


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

    assert state["awaiting"] == "report_forwarding_decision"
    assert state["selected_slot_id"] == "slot-1"
    assert state["confirmed_bookings"][0]["slot_id"] == "slot-1"
    assert "Your appointment is booked" in state["final_response"]
    assert "forward your detailed clinical report" in state["final_response"]


def test_classify_booking_menu_reply_bare_digit_skips_llm(monkeypatch):
    def _boom(**kwargs):
        raise AssertionError("generate_text should not be called for a bare digit reply")

    monkeypatch.setattr(appointment_booker, "generate_text", _boom)

    slot_options = [
        {"start_time": f"2026-05-21T{9 + i:02d}:00:00", "end_time": f"2026-05-21T{9 + i:02d}:30:00"}
        for i in range(5)
    ]

    decision = appointment_booker.classify_booking_menu_reply(
        {"user_input": "5", "slot_options": slot_options},
        "slot_selection",
    )

    assert decision.action == "select_option"
    assert decision.selected_value == "5"


def test_classify_booking_menu_reply_out_of_range_digit_falls_back_to_llm(monkeypatch):
    monkeypatch.setattr(
        appointment_booker,
        "generate_text",
        lambda **kwargs: '{"action":"unclear","selected_value":null,"reason":"out of range"}',
    )

    decision = appointment_booker.classify_booking_menu_reply(
        {"user_input": "9", "slot_options": [{"start_time": "2026-05-21T09:00:00", "end_time": "2026-05-21T09:30:00"}]},
        "slot_selection",
    )

    assert decision.action == "unclear"


def test_booker_confirms_booking_from_slot_selection_retry_state(monkeypatch):
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
            "awaiting": "slot_selection_retry_1",
            "user_input": "1",
            "slot_options": [{"slot_id": "slot-1", "start_time": "2026-05-21T09:00:00"}],
            "patient_id": "patient-1",
        }
    )

    assert state["awaiting"] == "report_forwarding_decision"
    assert state["selected_slot_id"] == "slot-1"
    assert state["confirmed_bookings"][0]["slot_id"] == "slot-1"


def test_booker_advances_to_slots_from_doctor_selection_retry_state(monkeypatch):
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
            "awaiting": "doctor_selection_retry_2",
            "user_input": "1",
            "doctor_options": [{"doctor_id": "doc-1", "doctor_name": "Dr. A"}],
        }
    )

    assert state["awaiting"] == "slot_selection"
    assert state["selected_doctor_id"] == "doc-1"


def test_date_options_skip_sunday_and_backfill_window(monkeypatch):
    from datetime import date as real_date

    class FakeDate(real_date):
        @classmethod
        def today(cls):
            return real_date(2026, 9, 7)  # a Monday, so Sep 13 (Sunday) falls in the raw window

    monkeypatch.setattr(appointment_booker, "date", FakeDate)

    options = appointment_booker._date_options()

    assert len(options) == appointment_booker._DATE_OPTION_COUNT
    assert all(real_date.fromisoformat(o["value"]).weekday() != 6 for o in options)


def test_booker_offers_date_picker_on_request_mid_slot_selection():
    from datetime import date

    state = appointment_booker.appointment_booker_node(
        {
            "awaiting": "slot_selection",
            "user_input": "actually, let me pick a different date",
            "slot_options": [{"slot_id": "slot-1", "start_time": "2026-05-21T09:00:00"}],
        }
    )

    assert state["awaiting"] == "date_selection"
    assert state["date_options"]
    assert all(date.fromisoformat(o["value"]).weekday() != 6 for o in state["date_options"])


def test_extract_requested_date_from_text_patterns():
    from datetime import date, timedelta

    extract = appointment_booker._extract_requested_date_from_text
    today = date.today()

    day_month_result = extract("can i book for 11 september ?")
    resolved = date.fromisoformat(day_month_result)
    assert (resolved.month, resolved.day) == (9, 11)
    assert resolved >= today

    assert extract("sept 11 2026") == "2026-09-11"
    assert extract("book for 11/09/2026") == "2026-09-11"
    assert extract("book for 2026-09-11") == "2026-09-11"
    # day > 12 proves DD/MM (not MM/DD) interpretation
    assert extract("book for 15/09/2026") == "2026-09-15"

    assert extract("tomorrow") == (today + timedelta(days=1)).isoformat()
    assert extract("day after tomorrow") == (today + timedelta(days=2)).isoformat()
    assert extract("in 3 days") == (today + timedelta(days=3)).isoformat()
    assert extract("3 days from now") == (today + timedelta(days=3)).isoformat()

    weekday_result = extract("monday")
    assert weekday_result == extract("next monday")
    assert date.fromisoformat(weekday_result).weekday() == 0
    assert date.fromisoformat(weekday_result) > today

    ordinal_result = extract("the 15th")
    assert date.fromisoformat(ordinal_result).day == 15

    assert extract("thanks") is None
    assert extract("I have a fever") is None
    assert extract("1") is None
    assert extract("5") is None


def test_booker_reslots_same_doctor_for_extracted_date(monkeypatch):
    seen = {}

    def fake_slots_on_date(doctor_id, requested_date, limit):
        seen["doctor_id"] = doctor_id
        seen["requested_date"] = requested_date
        return [
            {
                "slot_id": "slot-sep-11",
                "start_time": "2026-09-11T09:00:00",
                "end_time": "2026-09-11T09:30:00",
                "doctor_name": "Dr. Amit Vyas",
            }
        ]

    monkeypatch.setattr(appointment_booker, "available_slots_for_doctor_on_date", fake_slots_on_date)

    state = appointment_booker.appointment_booker_node(
        {
            "awaiting": "slot_selection",
            "user_input": "can i book for 11 september ?",
            "selected_doctor_id": "doc-amit",
            "selected_doctor_name": "Dr. Amit Vyas",
            "doctor_options": [{"doctor_id": "doc-amit", "doctor_name": "Dr. Amit Vyas"}],
            "target_department": "Cardiology",
        }
    )

    assert state["awaiting"] == "slot_selection"
    assert seen["doctor_id"] == "doc-amit"
    assert seen["requested_date"] == "2026-09-11"
    assert state["slot_options"][0]["slot_id"] == "slot-sep-11"
    assert "Dr. Amit Vyas" in state["final_response"]


def test_booker_researches_doctors_for_extracted_date_when_none_selected_yet(monkeypatch):
    seen = {}

    def fake_doctors_on_date(department, requested_date, limit):
        seen["department"] = department
        seen["requested_date"] = requested_date
        return [
            {
                "doctor_id": "doc-1",
                "doctor_name": "Dr. A",
                "experience_years": 10,
                "next_available_time": "2026-09-11T09:00:00",
                "available_slot_count": 3,
            },
            {
                "doctor_id": "doc-2",
                "doctor_name": "Dr. B",
                "experience_years": 5,
                "next_available_time": "2026-09-11T10:00:00",
                "available_slot_count": 2,
            },
        ]

    monkeypatch.setattr(appointment_booker, "available_doctors_for_department_on_date", fake_doctors_on_date)

    state = appointment_booker.appointment_booker_node(
        {
            "awaiting": "doctor_selection",
            "user_input": "can i book for 11 september ?",
            "target_department": "Cardiology",
            "doctor_options": [{"doctor_id": "doc-old", "doctor_name": "Dr. Old"}],
        }
    )

    assert state["awaiting"] == "doctor_selection"
    assert seen["department"] == "Cardiology"
    assert seen["requested_date"] == "2026-09-11"
    assert "2026-09-11" in state["final_response"]


def test_booker_rejects_extracted_sunday_date_with_picker():
    from datetime import date, timedelta

    today = date.today()
    days_to_sunday = (6 - today.weekday()) % 7
    days_to_sunday = days_to_sunday or 7
    sunday = today + timedelta(days=days_to_sunday)

    state = appointment_booker.appointment_booker_node(
        {
            "awaiting": "slot_selection",
            "user_input": f"can i book for {sunday.day} {sunday.strftime('%B').lower()} ?",
            "selected_doctor_id": "doc-amit",
            "selected_doctor_name": "Dr. Amit Vyas",
            "doctor_options": [{"doctor_id": "doc-amit", "doctor_name": "Dr. Amit Vyas"}],
        }
    )

    assert state["awaiting"] == "date_selection"
    assert "closed on Sundays" in state["final_response"]
    assert all(date.fromisoformat(o["value"]).weekday() != 6 for o in state["date_options"])


def test_booker_books_selected_slot_in_localized_language_without_catalog_key_error(monkeypatch):
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
        lambda slot_id, patient_id, booking_note=None: {
            "slot_id": slot_id,
            "doctor_name": "Dr. A",
            "department": "Cardiology",
            "start_time": "2026-05-21T09:00:00",
        },
    )
    monkeypatch.setattr(appointment_booker, "generate_text", lambda **kwargs: kwargs["user_prompt"])

    state = appointment_booker.appointment_booker_node(
        {
            "active_language": "de",
            "preferred_language": "de",
            "awaiting": "slot_selection",
            "user_input": "1",
            "slot_options": [
                {"slot_id": "slot-3", "start_time": "2026-05-21T09:00:00"},
            ],
            "patient_id": "patient-1",
        }
    )

    assert state["awaiting"] == "report_forwarding_decision"
    assert state["confirmed_booking"]["doctor"] == "Dr. A"
    assert "Dr. A" in state["final_response"]


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


def test_supervisor_answers_clinical_note_query_from_saved_booking():
    state = supervisor_node(
        {
            "user_input": "what symptoms were forwarded to my doctor?",
            "confirmed_booking": {
                "booking_id": "booking-1",
                "doctor": "Dr. Neetu Ramrakhiani",
                "department": "Neurology",
                "time": "2026-06-18T10:30:00",
                "booking_note": "Reported symptoms: lower back pain, exhaustion; Duration: since last month",
            },
            "patient_profile": {"name": "Anit", "age": 26},
        }
    )

    assert state["next_agent"] == "finish"
    assert "clinical note" in state["final_response"].lower()
    assert "lower back pain" in state["final_response"]
    assert "Neetu Ramrakhiani" in state["final_response"]


def test_report_consent_updates_the_booking_named_by_prompt(monkeypatch):
    target = {
        "booking_id": "booking-smriti-9am",
        "doctor": "Dr. Smriti Naswa",
        "department": "Dermatology",
        "time": "2026-09-03T09:00:00",
    }
    later_booking = {
        "booking_id": "booking-smriti-1030am",
        "doctor": "Dr. Smriti Naswa",
        "department": "Dermatology",
        "time": "2026-09-03T10:30:00",
    }
    monkeypatch.setattr(
        "app.agents.supervisor.update_booking_note",
        lambda booking_id, patient_id, booking_note: {**target, "booking_note": booking_note}
        if booking_id == target["booking_id"]
        else None,
    )

    result = continue_current_node(
        {
            "awaiting": "report_forwarding_decision",
            "user_input": "yes",
            "patient_id": "patient-1",
            "report_forwarding_booking_id": target["booking_id"],
            "upcoming_bookings": [later_booking, target],
            "pre_checkup_summary": "Chief Complaint: headache",
        }
    )

    assert result["note_forwarded"] is True
    assert result["upcoming_bookings"][1]["booking_id"] == target["booking_id"]
    assert result["upcoming_bookings"][1]["booking_note"] == "Chief Complaint: headache"
    assert "Dr. Smriti Naswa" in result["final_response"]


def test_supervisor_routes_billing_request_away_from_intake():
    state = supervisor_node(
        {
            "awaiting": "conversation",
            "user_input": "I want to ask about billing and payment",
            "symptoms": ["stomach pain"],
            "patient_profile": {"name": "Anit", "age": 26},
        }
    )

    assert state["next_agent"] == "conversation_agent"


def test_supervisor_routes_add_symptoms_request_to_note_forwarding():
    state = supervisor_node(
        {
            "awaiting": "conversation",
            "user_input": "please add these symptoms",
            "symptoms": ["nail pain", "discoloration"],
            "confirmed_booking": {
                "booking_id": "booking-1",
                "doctor": "Dr. Neetu Ramrakhiani",
                "department": "Dermatology",
                "time": "2026-06-22T10:30:00",
            },
            "patient_profile": {"name": "Anit", "age": 26},
        }
    )

    assert state["next_agent"] == "conversation_agent"


def test_supervisor_routes_new_symptom_pivot_back_to_triage():
    state = supervisor_node(
        {
            "awaiting": "remedy_check",
            "user_input": "actually now I have fever and vomiting",
            "remedy_given": True,
            "symptoms": ["stomach upset"],
            "patient_profile": {"name": "Anit", "age": 26},
        }
    )

    assert state["next_agent"] == "triage_router"
    assert state["awaiting"] is None
    assert state["intent"] is None
    assert state["doctor_options"] == []
    assert state["slot_options"] == []


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


def test_supervisor_keeps_symptom_only_message_in_medical_flow():
    state = supervisor_node(
        {
            "user_input": "i have heart burn sensation",
            "symptoms": ["heart burn sensation"],
            "severity": "moderate",
        }
    )

    assert state["next_agent"] == "triage_router"
    assert state.get("intent") is None
    assert state.get("requested_department") is None


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

    # Comfortably beyond the booking window even after Sundays are skipped and the
    # window backfills to still offer a full set of options (see _date_options).
    state = appointment_booker.appointment_booker_node(
        {
            "target_department": "Neurology",
            "requested_date": (date.today() + timedelta(days=20)).isoformat(),
            "intent": "direct_booking",
            "user_input": "book after 20 days",
        }
    )

    assert state["awaiting"] == "date_selection"
    assert len(state["date_options"]) == 8
    assert "closed on Sundays" in state["final_response"]


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


def test_booker_prompts_for_department_when_multiple_candidates_exist():
    state = appointment_booker.appointment_booker_node(
        {
            "candidate_departments": [
                {"department": "Gastroenterology", "matched_terms": ["stomach pain"]},
                {"department": "Dermatology", "matched_terms": ["rash"]},
            ],
            "user_input": "",
        }
    )

    assert state["awaiting"] == "department_selection"
    assert "Gastroenterology" in state["final_response"]
    assert "Dermatology" in state["final_response"]


def test_booker_selects_department_candidate_before_doctors(monkeypatch):
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
            "awaiting": "department_selection",
            "candidate_departments": [
                {"department": "Gastroenterology", "matched_terms": ["stomach pain"]},
                {"department": "Dermatology", "matched_terms": ["rash"]},
            ],
            "user_input": "1",
        }
    )

    assert state["awaiting"] == "doctor_selection"
    assert state["requested_department"] == "Gastroenterology"


def test_reschedule_patient_booking_handles_booking_row_shape(monkeypatch):
    class FakeCursor:
        def __init__(self):
            self.last_query = ""

        def execute(self, query, params=None):
            self.last_query = query

        def fetchone(self):
            if "FROM appointment_slots s" in self.last_query:
                return ("slot-new", "doctor-new", "Dr. B", "Cardiology", datetime(2026, 5, 22, 10, 0, 0), datetime(2026, 5, 22, 10, 30, 0))
            return None

    class FakeConn:
        def __init__(self):
            self.cursor_obj = FakeCursor()

        def cursor(self):
            class CursorContext:
                def __enter__(inner_self):
                    return self.cursor_obj

                def __exit__(inner_self, exc_type, exc, tb):
                    return False

            return CursorContext()

        def commit(self):
            pass

        def rollback(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(appointments_service, "ensure_booking_schema", lambda conn: None)
    monkeypatch.setattr(
        appointments_service,
        "_modifiable_booking",
        lambda cur, booking_id, patient_id: (
            "booking-1",
            "slot-old",
            "doctor-old",
            "Dr. A",
            "Cardiology",
            "note",
            datetime(2026, 5, 21, 9, 0, 0),
            datetime(2026, 5, 21, 9, 30, 0),
        ),
    )
    monkeypatch.setattr(appointments_service, "connect_db", lambda: FakeConn())

    booking = appointments_service.reschedule_patient_booking(
        booking_id="booking-1",
        patient_id="patient-1",
        new_slot_id="slot-new",
    )

    assert booking["booking_id"] == "booking-1"
    assert booking["slot_id"] == "slot-new"
    assert booking["doctor"] == "Dr. B"
    assert booking["booking_note"] == "note"


def test_book_selected_slot_returns_compatibility_fields(monkeypatch):
    class FakeCursor:
        def __init__(self):
            self.last_query = ""

        def execute(self, query, params=None):
            self.last_query = query

        def fetchone(self):
            if "SELECT booking_id" in self.last_query:
                return ("booking-1",)
            if "FROM appointment_slots s" in self.last_query:
                return (
                    "Dr. A",
                    "Neurology",
                    datetime(2026, 5, 21, 9, 0, 0),
                    datetime(2026, 5, 21, 9, 30, 0),
                    "slot-1",
                    "doctor-1",
                )
            return None

    class FakeConn:
        def __init__(self):
            self.cursor_obj = FakeCursor()

        def cursor(self):
            class CursorContext:
                def __enter__(inner_self):
                    return self.cursor_obj

                def __exit__(inner_self, exc_type, exc, tb):
                    return False

            return CursorContext()

        def commit(self):
            pass

        def rollback(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(appointments_service, "ensure_booking_schema", lambda conn: None)
    monkeypatch.setattr(appointments_service, "connect_db", lambda: FakeConn())

    booking = appointments_service.book_selected_slot(slot_id="slot-1", patient_id="patient-1")

    assert booking["doctor"] == "Dr. A"
    assert booking["doctor_name"] == "Dr. A"
    assert booking["department"] == "Neurology"
    assert booking["time"] == "2026-05-21T09:00:00"
    assert booking["start_time"] == datetime(2026, 5, 21, 9, 0, 0)


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

    assert state["awaiting"] == "conversation"
    assert state["final_response"]


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
