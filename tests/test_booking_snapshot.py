"""Reading the pre-visit context out of agent state.

Pure — no database, no model. The SQL side is covered in
test_booking_snapshot_integration.py.

What these protect: the moment a booking commits, the conversation behind it stops being
recoverable. Everything below is about extracting the right thing from state while it
still exists, and about never quietly turning a disagreement into agreement.
"""
from __future__ import annotations

import uuid

import pytest

from app.services.booking_context import SnapshotContext, context_from_state


def test_the_assistants_suggestion_and_the_patients_choice_are_both_kept():
    """The case this feature exists for: the assistant proposed Endocrinology off a
    cortisol result and the patient insisted on Psychiatry. The doctor must see both."""
    context = context_from_state(
        {
            "suggested_department": "Endocrinology",
            "department_match_source": "document_findings",
            "department_match_reason": "raised morning cortisol on the blood report",
        },
        chosen_department="Psychiatry",
    )

    assert context.suggested_department == "Endocrinology"
    assert context.chosen_department == "Psychiatry"
    assert context.department_match_reason == "raised morning cortisol on the blood report"


def test_an_absent_suggestion_is_not_backfilled_from_the_choice():
    """"The assistant had no opinion" and "the assistant agreed" are different facts.
    Defaulting one field from the other would make the disagreement the doctor most needs
    to see indistinguishable from agreement."""
    context = context_from_state({}, chosen_department="Cardiology")

    assert context.suggested_department is None
    assert context.chosen_department == "Cardiology"


def test_an_absent_choice_is_not_backfilled_from_the_suggestion():
    context = context_from_state({"suggested_department": "Cardiology"}, chosen_department=None)

    assert context.suggested_department == "Cardiology"
    assert context.chosen_department is None


# ---- the session id ----

def test_either_session_key_is_accepted():
    """chat.py keeps session_id and chat_session_id in step, and different call sites read
    different ones."""
    session = str(uuid.uuid4())

    assert context_from_state({"chat_session_id": session}).chat_session_id == session
    assert context_from_state({"session_id": session}).chat_session_id == session


def test_chat_session_id_wins_when_both_are_present():
    primary, secondary = str(uuid.uuid4()), str(uuid.uuid4())
    context = context_from_state({"chat_session_id": primary, "session_id": secondary})
    assert context.chat_session_id == primary


@pytest.mark.parametrize("bad", ["", "   ", "not-a-uuid", "12345", None, 42, [], {}])
def test_a_malformed_session_id_is_dropped_rather_than_failing_the_booking(bad):
    """Losing the transcript link is bad. Losing the appointment is worse — a patient who
    does not get seen because a session id was malformed is not an acceptable trade."""
    assert context_from_state({"chat_session_id": bad}).chat_session_id is None


# ---- hygiene ----

def test_blank_and_whitespace_fields_become_none_not_empty_strings():
    """An empty string renders as a present-but-blank field on the doctor's screen, which
    reads as "the assistant suggested nothing in particular" rather than "no suggestion
    was recorded"."""
    context = context_from_state(
        {"suggested_department": "   ", "department_match_reason": ""},
        chosen_department="  Neurology  ",
    )

    assert context.suggested_department is None
    assert context.department_match_reason is None
    assert context.chosen_department == "Neurology"


def test_no_state_at_all_is_handled():
    """The REST booking route has no conversation. That is a real case, not a bug."""
    for empty in (None, {}):
        context = context_from_state(empty)
        assert isinstance(context, SnapshotContext)
        assert context.chat_session_id is None


def test_the_context_is_immutable_once_built():
    """It is copied straight into an immutable database row; letting it be edited between
    construction and write would reintroduce exactly the mutability the snapshot exists to
    prevent."""
    context = context_from_state({"suggested_department": "Cardiology"})

    with pytest.raises(Exception):
        context.suggested_department = "Neurology"  # type: ignore[misc]
