"""Who receives a forwarded clinical report.

This decides which doctor sees a patient's clinical summary. Every test here is a safety
test, and none may be relaxed to make a change pass.

THE INCIDENT. A patient booked Dr. Mihir Thanvi for the 25th, then Dr. Sunita Panday for
the 24th. The assistant asked "forward your report to Dr. Sunita Panday?", the patient
said yes, and the summary was written to Dr. Mihir Thanvi's appointment. Verified in the
database afterwards: Panday's booking_note was empty and Thanvi's held the summary.

TWO INDEPENDENT FAULTS, both needed:

  1. appointment_booker pinned the intended appointment in report_forwarding_booking_id
     specifically to stop this — but the key was not declared in GraphState, and LangGraph
     merges only declared keys, so the pin was silently discarded on every hop. The guard
     had never once worked.
  2. The fallback, _latest_booking, is misnamed. upcoming_bookings is ORDER BY start_time
     ASC and the function reverses it, so it returns the appointment FURTHEST IN THE
     FUTURE, not the most recently booked one.
"""
from __future__ import annotations

import pytest

from app.agents.state import GraphState
from app.agents.supervisor import _latest_booking, _report_forwarding_booking


def _booking(booking_id, doctor, start_time):
    return {"booking_id": booking_id, "doctor": doctor, "doctor_name": doctor,
            "start_time": start_time, "time": start_time}


# Exactly as upcoming_bookings_for_patient returns them: ORDER BY start_time ASC.
# Panday was booked SECOND but is scheduled FIRST.
PANDAY = _booking("panday-booking", "Dr. Sunita Panday", "2026-09-24T11:30:00")
THANVI = _booking("thanvi-booking", "Dr. Mihir Thanvi", "2026-09-25T10:00:00")
BOTH = [PANDAY, THANVI]


# ---- the state key must survive LangGraph ----

def test_the_pinned_booking_id_is_declared_in_the_graph_state():
    """The whole fault. LangGraph drops keys that are not in the schema, so an undeclared
    pin is a guard that silently never runs."""
    assert "report_forwarding_booking_id" in GraphState.__annotations__


def test_intake_complete_is_declared_too():
    """Same class of bug, found by auditing for it: written by conversation_agent, read by
    supervisor routing, never survived the hop."""
    assert "intake_complete" in GraphState.__annotations__


def test_the_pin_survives_a_real_langgraph_hop():
    """Asserts the behaviour, not just the annotation — this is what actually failed."""
    from langgraph.graph import END, StateGraph

    def node(state):
        return {"report_forwarding_booking_id": "panday-booking",
                "awaiting": "report_forwarding_decision"}

    graph = StateGraph(GraphState)
    graph.add_node("n", node)
    graph.set_entry_point("n")
    graph.add_edge("n", END)
    result = graph.compile().invoke({"user_input": "x"})

    assert result.get("report_forwarding_booking_id") == "panday-booking"


# ---- the incident ----

def test_the_report_goes_to_the_doctor_named_in_the_consent_prompt():
    """The patient consented to Dr. Panday. Dr. Panday must be the recipient, even though
    Dr. Thanvi's appointment is further in the future."""
    booking = _report_forwarding_booking({
        "report_forwarding_booking_id": "panday-booking",
        "upcoming_bookings": BOTH,
    })
    assert booking is not None
    assert booking["doctor"] == "Dr. Sunita Panday"


def test_the_recipient_is_never_chosen_by_appointment_order():
    """Without a pin and with two appointments, refusing is the only safe answer. The old
    code returned Dr. Thanvi here — the exact disclosure that occurred."""
    assert _report_forwarding_booking({"upcoming_bookings": BOTH}) is None


def test_latest_booking_returns_the_furthest_future_appointment_not_the_newest():
    """Pins the misnamed behaviour so nobody reintroduces it as a 'safe' fallback.
    Panday was booked second; _latest_booking still returns Thanvi."""
    assert _latest_booking({"upcoming_bookings": BOTH})["doctor"] == "Dr. Mihir Thanvi"


def test_a_pin_that_no_longer_resolves_forwards_to_nobody():
    """A stale pin must not silently fall through to some other appointment."""
    assert _report_forwarding_booking({
        "report_forwarding_booking_id": "a-booking-that-is-gone",
        "upcoming_bookings": BOTH,
    }) is None


# ---- unambiguous cases still work ----

def test_a_single_appointment_needs_no_pin():
    """Refusing here would be pointless caution: there is only one thing it could mean."""
    booking = _report_forwarding_booking({"upcoming_bookings": [PANDAY]})
    assert booking["doctor"] == "Dr. Sunita Panday"


def test_the_same_appointment_listed_twice_is_still_unambiguous():
    booking = _report_forwarding_booking({
        "upcoming_bookings": [PANDAY],
        "confirmed_bookings": [PANDAY],
    })
    assert booking["doctor"] == "Dr. Sunita Panday"


def test_a_lone_confirmed_booking_is_used_when_no_list_exists():
    booking = _report_forwarding_booking({"confirmed_booking": PANDAY})
    assert booking["doctor"] == "Dr. Sunita Panday"


def test_no_appointments_at_all_forwards_to_nobody():
    assert _report_forwarding_booking({}) is None
    assert _report_forwarding_booking({"upcoming_bookings": []}) is None


def test_malformed_booking_entries_do_not_produce_a_recipient():
    assert _report_forwarding_booking({"upcoming_bookings": ["nope", None, {}]}) is None


@pytest.mark.parametrize("pin", ["", "   ", None])
def test_a_blank_pin_is_treated_as_no_pin_not_as_a_match(pin):
    assert _report_forwarding_booking({
        "report_forwarding_booking_id": pin, "upcoming_bookings": BOTH,
    }) is None
