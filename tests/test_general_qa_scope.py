"""Regression coverage for general_qa_node's strict scope (symptoms/health or this
app's booking features only — hospital policy/administrative questions and anything
else redirected too, per explicit user decision). Reproduces the exact demo-transcript
failure: general_qa previously answered any question (travel directions, weather,
politics) because its prompt never actually told it to refuse anything.

Same convention as test_extraction.py: monkeypatch the LLM call, call the node
function directly, no real network access.
"""
from app.agents import supervisor
from app.agents.supervisor import _GENERAL_QA_OUT_OF_SCOPE_RESPONSE, general_qa_node


def _state(user_input: str) -> dict:
    return {"user_input": user_input, "messages": [], "conversation_history": []}


def test_out_of_scope_travel_question_gets_fixed_redirect_not_real_travel_advice(monkeypatch):
    # Simulates the model trying to be "helpful" anyway despite the strict prompt —
    # the fix must discard this text entirely, not just hope the prompt is obeyed.
    monkeypatch.setattr(
        supervisor, "generate_text",
        lambda *a, **k: '{"in_scope": false, "answer": "You can fly from Hyderabad to Jaipur via..."}',
    )
    state = general_qa_node(_state("how can i travel to hyd to jaipur"))
    assert state["final_response"] == _GENERAL_QA_OUT_OF_SCOPE_RESPONSE
    assert "fly" not in state["final_response"]


def test_out_of_scope_politics_question_gets_fixed_redirect(monkeypatch):
    monkeypatch.setattr(
        supervisor, "generate_text",
        lambda *a, **k: '{"in_scope": false, "answer": ""}',
    )
    state = general_qa_node(_state("who is the prime minister of india"))
    assert state["final_response"] == _GENERAL_QA_OUT_OF_SCOPE_RESPONSE


def test_hospital_policy_question_is_also_redirected_per_explicit_scope_decision(monkeypatch):
    monkeypatch.setattr(
        supervisor, "generate_text",
        lambda *a, **k: '{"in_scope": false, "answer": ""}',
    )
    state = general_qa_node(_state("what are your visiting hours"))
    assert state["final_response"] == _GENERAL_QA_OUT_OF_SCOPE_RESPONSE


def test_genuine_symptom_question_gets_the_real_answer_through(monkeypatch):
    monkeypatch.setattr(
        supervisor, "generate_text",
        lambda *a, **k: '{"in_scope": true, "answer": "A mild fever with no other symptoms is usually not urgent, but monitor your temperature."}',
    )
    state = general_qa_node(_state("is a mild fever dangerous"))
    assert "monitor your temperature" in state["final_response"]


def test_booking_feature_question_gets_the_real_answer_through(monkeypatch):
    monkeypatch.setattr(
        supervisor, "generate_text",
        lambda *a, **k: '{"in_scope": true, "answer": "You can cancel from your upcoming appointments list, up to 24 hours before your visit."}',
    )
    state = general_qa_node(_state("how do i cancel my appointment"))
    assert "cancel" in state["final_response"].lower()


def test_ambiguous_temperature_question_still_gets_a_clarifying_question_not_a_flat_refusal(monkeypatch):
    monkeypatch.setattr(
        supervisor, "generate_text",
        lambda *a, **k: '{"in_scope": true, "answer": "Are you asking about your own body temperature, or the weather today?"}',
    )
    state = general_qa_node(_state("what is the temperature today"))
    assert state["final_response"] != _GENERAL_QA_OUT_OF_SCOPE_RESPONSE
    assert "body temperature" in state["final_response"]


def test_malformed_llm_output_falls_back_to_fixed_redirect(monkeypatch):
    monkeypatch.setattr(supervisor, "generate_text", lambda *a, **k: "not valid json at all")
    state = general_qa_node(_state("anything"))
    assert state["final_response"] == _GENERAL_QA_OUT_OF_SCOPE_RESPONSE


def test_in_scope_true_but_blank_answer_still_falls_back_to_fixed_redirect(monkeypatch):
    """Defense in depth: even if the model says in_scope=true but leaves answer empty
    (a malformed/inconsistent response), don't show a blank message to the patient."""
    monkeypatch.setattr(
        supervisor, "generate_text",
        lambda *a, **k: '{"in_scope": true, "answer": ""}',
    )
    state = general_qa_node(_state("anything"))
    assert state["final_response"] == _GENERAL_QA_OUT_OF_SCOPE_RESPONSE
