"""End-to-end coverage for the conversational (LangGraph agent) booking flow.

"End-to-end" here means full-stack-through-the-service-layer, matching this repo's
existing convention (see test_booking_flow.py): nodes are invoked directly rather than
through a browser, and the service layer is either monkeypatched (pure agent-logic
tests) or hit against a real Postgres database (DB-backed tests, which skip cleanly —
not fail — if no database is reachable, same pattern as test_consult_integration.py and
test_booking_schema_integration.py).

Covers:
- Full happy path: intake (respecting MAX_INTAKE_QUESTIONS=6) -> doctor selection ->
  slot selection -> booking confirmed.
- The intake gate: booking/next-question flow cannot skip ahead of the question count.
- MAX_IRRELEVANT_STREAK=2: two consecutive off-topic replies advance to the next
  scripted question instead of looping forever.
- Zero-available-doctors path (both the requested department AND the "General
  Physician" fallback have no doctors): re-prompts for a date instead of crashing.
- Cancel and reschedule via chat, including the exact 24-hour cutoff boundary
  (`b.start_time > NOW() + INTERVAL '24 hours'` in app/services/appointments.py).
"""

from datetime import datetime, timedelta

import pytest

from app.agents import appointment_booker
from app.agents import conversation_agent
from app.agents import supervisor
from app.db.connection import connect_db
from app.services import appointments as appointments_service


# ── DB availability helper (same pattern as test_consult_integration.py) ────────

def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _make_doctor(cur, name, department="Testing"):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
        (name, department, 5),
    )
    return str(cur.fetchone()[0])


def _make_slot(cur, doctor_id, offset):
    """offset is a timedelta from now for the slot's start_time."""
    start_time = datetime.now() + offset
    end_time = start_time + timedelta(minutes=30)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
           VALUES (%s, %s, %s, FALSE) RETURNING slot_id""",
        (doctor_id, start_time, end_time),
    )
    return str(cur.fetchone()[0])


def _cleanup(doctor_ids):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for doctor_id in doctor_ids:
                if doctor_id:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        conn.commit()


# ── Full happy path: intake -> doctor selection -> slot selection -> booked ────

def test_full_chat_booking_happy_path_respects_max_intake_questions(monkeypatch):
    """Drives conversation_agent_node through exactly MAX_INTAKE_QUESTIONS=6 scripted
    questions (as test_conversation_stops_when_structured_intake_is_sufficient and
    friends in test_booking_flow.py already do individually), then chains straight into
    appointment_booker_node's doctor-selection -> slot-selection -> booking-confirmed
    sequence exactly as test_booker_shows_slots_after_doctor_selection /
    test_booker_books_selected_slot already exercise it, to prove the two halves
    actually compose into one continuous flow."""

    topics_in_order = [
        ("How long have you had this pain?", {"duration": "3 days"}),
        ("Where exactly is the pain located?", {"location": "lower back"}),
        ("Is it constant or does it come and go?", {"severity_pattern": "constant"}),
        ("Did anything trigger it, like lifting something?", {"cause": "lifting a heavy box"}),
        ("Any other symptoms, like numbness or weakness?", {"associated_symptoms": "mild numbness"}),
        ("Are you taking any medication for it?", {"medications": "ibuprofen"}),
    ]

    state = {
        "awaiting": "conversation",
        "symptoms": ["back pain"],
        "severity": "moderate",
        "questions_asked": [],
        "collected_data": {},
        "collected_info": {},
    }

    for index, (next_question, collected_info) in enumerate(topics_in_order):
        def fake_generate_text(*args, __q=next_question, __info=collected_info, **kwargs):
            import json as _json
            return _json.dumps(
                {
                    "intent": "continue_intake",
                    "has_enough_info": False,
                    "next_question": __q,
                    "collected_info": __info,
                }
            )

        monkeypatch.setattr(conversation_agent, "generate_text", fake_generate_text)
        state["user_input"] = "some clinical answer"
        state = {**state, **conversation_agent.conversation_agent_node(state)}

        # The gate must still be open: exactly `index + 1` questions have been asked
        # and the flow is still awaiting more intake, never jumping ahead to booking.
        assert len(state["questions_asked"]) == index + 1
        assert state["awaiting"] == "conversation"

    assert len(state["questions_asked"]) == conversation_agent.MAX_INTAKE_QUESTIONS

    # The 7th turn hits the fast-path in conversation_agent_node: once
    # MAX_INTAKE_QUESTIONS have been asked, intake is force-completed without another
    # LLM call (see the "FAST-PATH" branch at the top of conversation_agent_node).
    def _boom(*args, **kwargs):
        raise AssertionError("generate_text should not be called once the question cap is hit")

    monkeypatch.setattr(conversation_agent, "generate_text", _boom)
    state["user_input"] = "it has been getting worse honestly"
    state = {**state, **conversation_agent.conversation_agent_node(state)}

    assert state["awaiting"] is None
    assert state["intake_complete"] is True
    assert len(state["questions_asked"]) == conversation_agent.MAX_INTAKE_QUESTIONS

    # Triage produced a target department (triage_router.py's job — simulated here
    # since only conversation_agent/appointment_booker/supervisor are under test).
    state["target_department"] = "Orthopedics"
    state["intent"] = "triage_symptoms"
    state["active_intent"] = "triage_symptoms"

    # Doctor selection.
    monkeypatch.setattr(
        appointment_booker,
        "available_doctors_for_department",
        lambda department, limit: [
            {
                "doctor_id": "doc-ortho-1",
                "doctor_name": "Dr. Spine",
                "experience_years": 12,
                "next_available_time": "2026-09-11T09:00:00",
                "available_slot_count": 3,
            }
        ],
    )
    state["user_input"] = "book an appointment"
    state = {**state, **appointment_booker.appointment_booker_node(state)}
    assert state["awaiting"] == "doctor_selection"
    assert state["doctor_options"][0]["doctor_name"] == "Dr. Spine"

    # Slot selection.
    monkeypatch.setattr(
        appointment_booker,
        "classify_booking_menu_reply",
        lambda state, menu_type: appointment_booker.BookingMenuDecision(
            action="select_option", selected_value="1", reason="picked by number",
        ),
    )
    monkeypatch.setattr(
        appointment_booker,
        "available_slots_for_doctor",
        lambda doctor_id, limit: [
            {
                "slot_id": "slot-ortho-1",
                "start_time": "2026-09-11T09:00:00",
                "end_time": "2026-09-11T09:30:00",
                "doctor_name": "Dr. Spine",
            }
        ],
    )
    state["user_input"] = "1"
    state = {**state, **appointment_booker.appointment_booker_node(state)}
    assert state["awaiting"] == "slot_selection"
    assert state["selected_doctor_id"] == "doc-ortho-1"

    # Booking confirmed.
    monkeypatch.setattr(
        appointment_booker,
        "book_selected_slot",
        lambda slot_id, patient_id, booking_note=None: {
            "slot_id": slot_id,
            "booking_id": "booking-ortho-1",
            "doctor_name": "Dr. Spine",
            "department": "Orthopedics",
            "start_time": "2026-09-11T09:00:00",
        },
    )
    state["patient_id"] = "patient-e2e-1"
    state["user_input"] = "1"
    state = {**state, **appointment_booker.appointment_booker_node(state)}

    assert state["awaiting"] == "report_forwarding_decision"
    assert state["confirmed_booking"]["slot_id"] == "slot-ortho-1"
    assert state["confirmed_booking"]["booking_id"] == "booking-ortho-1"
    assert "Your appointment is booked" in state["final_response"]


# ── Intake gate ──────────────────────────────────────────────────────────────

def test_supervisor_keeps_patient_in_intake_before_five_questions_even_if_they_ask_to_book():
    """_heuristic_supervisor_route's `awaiting == "conversation"` branch only lets the
    patient leave intake for an explicit remedy/doctor request once 5 questions have
    been asked (see supervisor.py: `if len(questions_asked) < 5: ... return
    _route("conversation_agent")`). Below that count, even a message that sounds like a
    booking request must stay routed to conversation_agent — the gate is enforced by
    question count, not just by intent."""
    state = supervisor.supervisor_node(
        {
            "awaiting": "conversation",
            "user_input": "can we just skip ahead",
            "symptoms": ["back pain"],
            "questions_asked": ["Q1", "Q2"],
            "patient_profile": {"name": "Anit", "age": 26},
        }
    )
    assert state["next_agent"] == "conversation_agent"


def test_appointment_booker_will_not_show_doctors_without_any_intake_context():
    """appointment_booker_node's own gate: with symptoms present but no follow-up
    answer, no conversational context (duration/cause/trigger/onset), and no
    direct_booking override, it must ask a symptom follow-up question rather than
    reach ask_preferred_doctor and show doctors directly — booking cannot be reached by
    skipping straight past intake."""
    state = appointment_booker.appointment_booker_node(
        {
            "user_input": "back pain",
            "symptoms": ["back pain"],
            "target_department": "Orthopedics",
        }
    )
    assert state["awaiting"] == "symptom_follow_up"
    assert state["booking_active"] is False
    assert "doctor_options" not in state or not state["doctor_options"]


def test_conversation_intake_complete_requires_exact_question_count():
    """Pin down _conversation_intake_complete's actual gate condition directly: it must
    return False below MAX_INTAKE_QUESTIONS regardless of how much info is collected,
    and True once the count is reached."""
    rich_collected = {
        "duration": "3 days", "location": "back", "severity_pattern": "constant",
        "cause": "lifting", "associated_symptoms": "numbness", "medications": "none",
    }
    assert conversation_agent._conversation_intake_complete(rich_collected, ["q"] * 5) is False
    assert conversation_agent._conversation_intake_complete(rich_collected, ["q"] * 6) is True
    assert conversation_agent._conversation_intake_complete({}, ["q"] * 6) is True


# ── Irrelevant-answer streak (MAX_IRRELEVANT_STREAK=2) ──────────────────────────

def test_irrelevant_answer_streak_advances_to_next_question_instead_of_looping(monkeypatch):
    assert conversation_agent.MAX_IRRELEVANT_STREAK == 2

    def fake_generate_text(*args, **kwargs):
        import json as _json
        return _json.dumps(
            {
                "intent": "continue_intake",
                "reply_addresses_question": False,
                "has_enough_info": False,
                "next_question": "Can you tell me more about the pain?",
                "collected_info": {},
            }
        )

    monkeypatch.setattr(conversation_agent, "generate_text", fake_generate_text)

    base_state = {
        "awaiting": "conversation",
        "symptoms": ["back pain"],
        "questions_asked": ["How long has this been going on?"],
        "collected_data": {},
        "collected_info": {},
        "irrelevant_reply_streak": 0,
    }

    # First off-topic reply: streak becomes 1, still below MAX_IRRELEVANT_STREAK(2) ->
    # re-prompt the SAME question, do not consume a scripted question slot.
    base_state["user_input"] = "lol what"
    first = conversation_agent.conversation_agent_node(base_state)
    assert first["irrelevant_reply_streak"] == 1
    assert first["awaiting"] == "conversation"
    assert len(first["questions_asked"]) == 1  # unchanged — no new question consumed

    # Second consecutive off-topic reply: streak hits MAX_IRRELEVANT_STREAK(2) -> the
    # safety valve fires and the flow advances to the next scripted question rather
    # than asking the same one a third time.
    second_state = {**base_state, **first}
    second_state["user_input"] = "haha ok"
    second = conversation_agent.conversation_agent_node(second_state)

    assert second["irrelevant_reply_streak"] == 0  # reset after the safety valve fires
    assert second["awaiting"] == "conversation"  # flow continues, does not get stuck
    assert len(second["questions_asked"]) == 2  # advanced to a NEW question


# ── Zero-available-doctors path ─────────────────────────────────────────────────

def test_no_doctors_in_department_or_general_physician_fallback_reprompts_for_date(monkeypatch):
    """Per ask_preferred_doctor in appointment_booker.py: when the requested department
    has no available doctors, it tries the "General Physician" fallback; when THAT is
    also empty, it must return the date-selection prompt (via _date_selection_response)
    rather than raise or dead-end. This is the actual current behavior — it does not
    crash and does not silently show an empty doctor list."""
    monkeypatch.setattr(
        appointment_booker,
        "available_doctors_for_department",
        lambda department, limit: [],  # empty for every department, including the GP fallback
    )

    state = appointment_booker.appointment_booker_node(
        {
            "target_department": "Cardiology",
            "requested_department": "Cardiology",
            "intent": "direct_booking",
            "user_input": "book a cardiology appointment",
        }
    )

    assert state["awaiting"] == "date_selection"
    assert state["date_options"]
    assert state["doctor_options"] == []
    assert "General Physician" in state["final_response"]
    assert "could not find" in state["final_response"].lower()


# ── Cancel / reschedule via chat, with the exact 24h cutoff ─────────────────────
#
# app/services/appointments.py's cancel_booking() (and _modifiable_booking(), used by
# reschedule_patient_booking) gate strictly on `b.start_time > NOW() + INTERVAL '24
# hours'`. That is a strict inequality: a booking exactly 24h out at insert time will,
# by the time the query actually runs (a small but nonzero delay later), have already
# drifted to just UNDER 24h away and therefore fail the same as "just under" — that is
# the real, deterministic behavior of this boundary, not a hypothetical.

_JUST_UNDER_24H = timedelta(hours=24) - timedelta(minutes=2)
_EXACTLY_24H = timedelta(hours=24)
_JUST_OVER_24H = timedelta(hours=24) + timedelta(minutes=2)


@pytest.mark.parametrize(
    "offset,expect_cancelled",
    [
        (_JUST_OVER_24H, True),
        (_EXACTLY_24H, False),
        (_JUST_UNDER_24H, False),
    ],
    ids=["just_over_24h", "exactly_24h", "just_under_24h"],
)
def test_chat_cancel_respects_24_hour_cutoff_boundary(offset, expect_cancelled):
    _skip_if_no_database()

    doctor_id = None
    patient_id = "patient-cancel-boundary"
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Cancel Boundary")
                slot_id = _make_slot(cur, doctor_id, offset)
                start_time = datetime.now() + offset
                end_time = start_time + timedelta(minutes=30)
                cur.execute(
                    """INSERT INTO appointment_bookings
                       (slot_id, doctor_id, patient_id, start_time, end_time, status)
                       VALUES (%s, %s, %s, %s, %s, 'booked') RETURNING booking_id""",
                    (slot_id, doctor_id, patient_id, start_time, end_time),
                )
                booking_id = str(cur.fetchone()[0])
                cur.execute(
                    "UPDATE appointment_slots SET is_booked = TRUE, booked_by_patient_id = %s WHERE slot_id = %s",
                    (patient_id, slot_id),
                )
            conn.commit()

        # Drive it through the actual chat-path function (unmocked — hits the real
        # cancel_booking() service call, which is what enforces the boundary).
        state = appointment_booker.cancel_selected_appointment(
            {
                "user_input": "1",
                "patient_id": patient_id,
                "cancellation_options": [{"booking_id": booking_id, "doctor": "Dr. Cancel Boundary"}],
                "upcoming_bookings": [],
            }
        )

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT status FROM appointment_bookings WHERE booking_id::text = %s", (booking_id,))
                status = cur.fetchone()[0]

        if expect_cancelled:
            assert status == "cancelled"
            assert "cancelled" in state["final_response"].lower()
            assert state["awaiting"] == "end_confirmation"
        else:
            assert status == "booked"
            assert "could not find" in state["final_response"].lower()
            assert state["awaiting"] == "cancellation_selection"
    finally:
        _cleanup([doctor_id])


def test_chat_reschedule_date_step_blocks_when_booking_is_just_under_24h_away():
    _skip_if_no_database()

    doctor_id = None
    patient_id = "patient-resched-under"
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Reschedule Under")
                slot_id = _make_slot(cur, doctor_id, _JUST_UNDER_24H)
                start_time = datetime.now() + _JUST_UNDER_24H
                end_time = start_time + timedelta(minutes=30)
                cur.execute(
                    """INSERT INTO appointment_bookings
                       (slot_id, doctor_id, patient_id, start_time, end_time, status)
                       VALUES (%s, %s, %s, %s, %s, 'booked') RETURNING booking_id""",
                    (slot_id, doctor_id, patient_id, start_time, end_time),
                )
                booking_id = str(cur.fetchone()[0])
                cur.execute(
                    "UPDATE appointment_slots SET is_booked = TRUE, booked_by_patient_id = %s WHERE slot_id = %s",
                    (patient_id, slot_id),
                )
            conn.commit()

        # can_modify comes from the real upcoming_bookings_for_patient() query, exactly
        # as the chat flow would have populated reschedule_options.
        bookings = appointments_service.upcoming_bookings_for_patient(patient_id)
        assert bookings[0]["can_modify"] is False

        result = appointment_booker.ask_reschedule_date(
            {
                "user_input": booking_id,
                "patient_id": patient_id,
                "reschedule_options": bookings,
            }
        )

        assert result["awaiting"] is None
        assert "cannot be changed" in result["final_response"].lower()
    finally:
        _cleanup([doctor_id])


def test_chat_reschedule_date_step_allows_and_reschedule_succeeds_when_just_over_24h_away():
    _skip_if_no_database()

    doctor_id = None
    patient_id = "patient-resched-over"
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Reschedule Over")
                original_slot_id = _make_slot(cur, doctor_id, _JUST_OVER_24H)
                start_time = datetime.now() + _JUST_OVER_24H
                end_time = start_time + timedelta(minutes=30)
                cur.execute(
                    """INSERT INTO appointment_bookings
                       (slot_id, doctor_id, patient_id, start_time, end_time, status)
                       VALUES (%s, %s, %s, %s, %s, 'booked') RETURNING booking_id""",
                    (original_slot_id, doctor_id, patient_id, start_time, end_time),
                )
                booking_id = str(cur.fetchone()[0])
                cur.execute(
                    "UPDATE appointment_slots SET is_booked = TRUE, booked_by_patient_id = %s WHERE slot_id = %s",
                    (patient_id, original_slot_id),
                )
                # A second, open slot with the same doctor further out, to reschedule into.
                new_slot_id = _make_slot(cur, doctor_id, _JUST_OVER_24H + timedelta(days=1))
            conn.commit()

        bookings = appointments_service.upcoming_bookings_for_patient(patient_id)
        assert bookings[0]["can_modify"] is True

        # Step 1: ask_reschedule_date must allow proceeding (not blocked).
        gate = appointment_booker.ask_reschedule_date(
            {
                "user_input": booking_id,
                "patient_id": patient_id,
                "reschedule_options": bookings,
            }
        )
        assert gate["awaiting"] == "reschedule_date_selection"
        assert gate["date_options"] if "date_options" in gate else gate["reschedule_date_options"]

        # Step 2: apply the reschedule directly to the known-open new_slot_id (mirrors
        # what apply_reschedule_slot does once the patient picks a slot number).
        result = appointment_booker.apply_reschedule_slot(
            {
                "user_input": "1",
                "patient_id": patient_id,
                "selected_booking_id": booking_id,
                "reschedule_slot_options": [{"slot_id": new_slot_id, "start_time": (datetime.now() + _JUST_OVER_24H + timedelta(days=1)).isoformat()}],
            }
        )

        assert result["awaiting"] == "end_confirmation"
        assert result["confirmed_booking"]["slot_id"] == new_slot_id
        assert "updated" in result["final_response"].lower()

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT slot_id, status FROM appointment_bookings WHERE booking_id::text = %s", (booking_id,))
                row = cur.fetchone()
                assert str(row[0]) == new_slot_id
                assert row[1] == "booked"
    finally:
        _cleanup([doctor_id])
