"""The conversation after a document upload.

Same convention as test_booking_flow.py: call the functions directly with plain state
dicts, no LLM, no network. Nothing here needs mocking because the questions are templated
rather than generated — which is the point of the design.

The behaviour being protected: uploading a document used to set
active_intent="direct_booking" and a target_department in one assignment and return
before the graph ran. No question could be asked, and the guessed department became the
patient's own "request" and could not be talked out of. A patient asking for a psychiatrist
was answered with the original guess four times running.
"""
from __future__ import annotations

import pytest

from app.agents import document_followup as followup
from app.agents import supervisor
from app.agents.document_followup import (
    AWAITING_DOCUMENT_FOLLOW_UP,
    MAX_DOCUMENT_FOLLOW_UP_QUESTIONS,
    TOPIC_DURATION,
    TOPIC_REFERRAL,
    TOPIC_SYMPTOMS,
    budget_exhausted,
    next_question,
    register_question,
    reports_no_symptoms,
    wants_to_only_store,
)

REAL_DEPARTMENTS = [
    "General Physician", "Gastroenterology", "Cardiology", "Neurology",
    "Orthopedics", "Oncology", "Pulmonology", "Psychiatry", "Nephrology",
    "Endocrinology", "Hematology", "Dermatology",
]


@pytest.fixture(autouse=True)
def _no_database(monkeypatch):
    """Keep these pure — the resolver reads the department list from the DB."""
    from app.services import appointments as appointments_service

    monkeypatch.setattr(
        appointments_service, "routable_departments", lambda *a, **k: list(REAL_DEPARTMENTS)
    )
    # The model that words the later questions is unavailable here, so every question comes
    # from the templates — the floor the flow must keep when the model is down.
    def _no_model(*args, **kwargs):
        raise RuntimeError("no model in unit tests")

    monkeypatch.setattr(followup, "_ask_model", _no_model)


def _referral_document(**overrides):
    """The document from the real incident."""
    document = {
        "file_name": "blood-report.pdf",
        "document_type": "blood_report",
        "department": "Endocrinology",
        "referring_doctor": "Sunita Panday",
        "referring_department": "Psychiatry",
        "clinical_history": "anxiety for the past few days and unable to sleep",
    }
    document.update(overrides)
    return document


def _state(**overrides):
    state = {
        "awaiting": AWAITING_DOCUMENT_FOLLOW_UP,
        "analyzed_documents": [_referral_document()],
        "document_topics_asked": [],
        "questions_asked": [],
        "user_input": "",
    }
    state.update(overrides)
    return state


# ---- which question comes first ----

def test_the_referral_is_the_first_thing_asked_about():
    """The decisive question. A patient who abandons the flow after one answer has still
    answered the one that resolves the whole case."""
    topic, question = next_question(_state())
    assert topic == TOPIC_REFERRAL
    assert "Panday" in question
    assert "Psychiatry" in question


def test_a_document_with_no_referral_asks_about_symptoms_instead():
    """The budget is re-spent rather than wasted asking about a referral that is not
    there — most documents have none."""
    state = _state(analyzed_documents=[_referral_document(
        referring_department=None, referring_doctor=None, clinical_history=None
    )])
    topic, question = next_question(state)
    assert topic == TOPIC_SYMPTOMS
    assert "symptoms" in question.lower()


def test_a_stated_clinical_history_is_confirmed_rather_than_re_asked():
    """The document already says why the test was ordered; asking "any symptoms?" as if
    we had not read it wastes the turn."""
    state = _state(document_topics_asked=[TOPIC_REFERRAL])
    topic, question = next_question(state)
    assert topic == TOPIC_SYMPTOMS
    assert "unable to sleep" in question
    assert "still the main problem" in question


def test_duration_is_only_asked_once_something_is_known_to_be_wrong():
    no_symptoms = _state(
        analyzed_documents=[_referral_document(clinical_history=None, referring_department=None)],
        document_topics_asked=[TOPIC_SYMPTOMS],
        symptoms=[],
    )
    assert next_question(no_symptoms) is None

    with_symptoms = _state(
        document_topics_asked=[TOPIC_REFERRAL, TOPIC_SYMPTOMS],
        symptoms=["anxiety"],
    )
    assert next_question(with_symptoms)[0] == TOPIC_DURATION


def test_a_topic_is_never_asked_twice():
    state = _state(document_topics_asked=[TOPIC_REFERRAL, TOPIC_SYMPTOMS, TOPIC_DURATION],
                   symptoms=["anxiety"])
    assert next_question(state) is None


# ---- the budget ----

def test_the_budget_is_a_ceiling_of_three_to_four_questions():
    assert 3 <= MAX_DOCUMENT_FOLLOW_UP_QUESTIONS <= 4


def test_the_budget_counts_topics_not_prose():
    """questions_asked holds whole sentences and other nodes push non-questions into it,
    so counting it would exhaust the budget without having asked anything."""
    state = _state(questions_asked=["a", "b", "c", "d", "e", "f"], document_topics_asked=[])
    assert not budget_exhausted(state)


def test_the_budget_stops_the_questions():
    state = _state(document_topics_asked=["a", "b", "c", "d"])
    assert budget_exhausted(state)


def test_registering_a_question_records_both_the_topic_and_the_prose():
    delta = register_question(_state(), TOPIC_REFERRAL, "Is this a follow-up?")
    assert delta["document_topics_asked"] == [TOPIC_REFERRAL]
    assert delta["questions_asked"] == ["Is this a follow-up?"]


# ---- skip-ahead ----

@pytest.mark.parametrize(
    "text",
    ["just store it", "no appointment please", "just save it for my records",
     "don't book anything", "I just keep it for reference"],
)
def test_a_patient_who_only_wants_the_document_filed_is_not_pushed_into_booking(text):
    assert wants_to_only_store(text)


@pytest.mark.parametrize(
    "text", ["I want to book", "can i see a doctor", "yes please", "psychiatrist"]
)
def test_a_booking_request_is_not_mistaken_for_just_store_it(text):
    assert not wants_to_only_store(text)


@pytest.mark.parametrize(
    "text",
    ["no symptoms", "feeling fine", "this is just a routine check", "nothing right now"],
)
def test_no_symptoms_is_recognised(text):
    assert reports_no_symptoms(text)


# ---- the supervisor turn ----

def test_naming_a_department_skips_the_remaining_questions():
    """The failure this whole slice exists to fix: an explicit request must be honoured
    immediately, not answered with the document's guess."""
    result = supervisor._handle_document_follow_up(
        _state(), "can i see a psychiatrist?"
    )
    assert result["next_agent"] == "appointment_booker"
    assert result["requested_department"] == "Psychiatry"
    assert result["awaiting"] is None


def test_a_misspelled_department_also_skips_ahead():
    result = supervisor._handle_document_follow_up(_state(), "can i see a phyciatrist ?")
    assert result["requested_department"] == "Psychiatry"


def test_just_store_it_ends_the_conversation_without_booking():
    result = supervisor._handle_document_follow_up(_state(), "just store it for my records")
    assert result["next_agent"] == "finish"
    assert result["awaiting"] is None
    assert "won't book" in result["final_response"]


def test_an_ordinary_reply_asks_the_next_question_and_keeps_waiting():
    result = supervisor._handle_document_follow_up(_state(), "ok")
    assert result["next_agent"] == "finish"
    assert result["awaiting"] == AWAITING_DOCUMENT_FOLLOW_UP
    assert result["active_intent"] == "document_review"
    assert "Panday" in result["final_response"]
    assert result["document_topics_asked"] == [TOPIC_REFERRAL]


def test_the_upload_turn_no_longer_forces_a_booking_intent():
    """document_review, not direct_booking. The old value made every later turn behave as
    though the patient had asked to be booked into the guessed department."""
    result = supervisor._handle_document_follow_up(_state(), "ok")
    assert result["intent"] == "document_review"
    assert result["active_intent"] == "document_review"
    assert "target_department" not in result


def test_when_the_budget_runs_out_the_patient_is_asked_to_choose_not_booked_silently():
    """Endocrinology from the findings and Psychiatry from the referral both apply, so the
    patient decides — the resolver returns "ask" and both are offered. The summary comes
    first (checkup_report), and it ends with that choice rather than a booking."""
    state = _state(document_topics_asked=["a", "b", "c", "d"])
    result = supervisor._handle_document_follow_up(state, "yes")
    assert result["next_agent"] == "checkup_report"
    offered = {c["department"] for c in result.get("candidate_departments", [])}
    assert {"Psychiatry", "Endocrinology"} <= offered
    assert result.get("target_department") is None


def test_the_follow_up_state_is_routed_in_both_supervisor_tables():
    """A new awaiting value needs an entry in the heuristic router AND the post-node
    fallback. The old awaiting="user_input" was written by five document paths and
    consumed by neither, which is why it was inert."""
    import inspect

    heuristic = inspect.getsource(supervisor._heuristic_supervisor_route)
    fallback = inspect.getsource(supervisor._fallback_route_after_node)
    assert "AWAITING_DOCUMENT_FOLLOW_UP" in heuristic
    assert "AWAITING_DOCUMENT_FOLLOW_UP" in fallback


def test_a_document_with_nothing_useful_does_not_crash_or_invent_a_department():
    state = _state(analyzed_documents=[{"document_type": "other"}], document_topics_asked=["a", "b", "c", "d"])
    result = supervisor._handle_document_follow_up(state, "ok")
    assert result["next_agent"] == "checkup_report"
    assert result.get("target_department") in (None, "General Physician")


def test_no_document_at_all_is_handled():
    state = _state(analyzed_documents=[])
    assert followup.latest_document(state) == {}
    result = supervisor._handle_document_follow_up(state, "ok")
    assert result["next_agent"] in {"finish", "checkup_report"}
