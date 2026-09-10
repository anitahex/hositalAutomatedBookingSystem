"""Regression tests for bugs traced from a real demo-conversation transcript
(see FULL_SYSTEM_AUDIT.md and the fix plan): a car "leaking fuel" getting
classified as a medical symptom, a crisis-sounding message trapping the
conversation for several turns regardless of topic, a misclassified fact
leaking into unrelated general_qa answers, and an uploaded document not
being referenced in a later follow-up question.

Same convention as test_extraction.py / test_booking_flow.py: call node
functions directly with monkeypatched LLM calls, no real network access.
"""
import asyncio

from app.agents import document_analyzer, supervisor, triage_router
from app.agents.intake_utils import looks_like_crisis_or_harm, looks_like_general_knowledge_question
from app.agents.conversation_agent import should_stream_intake


# ── Bug 1: non-medical "symptom" misclassification ───────────────────────────

def test_triage_router_drops_non_medical_symptom_from_llm_misclassification(monkeypatch):
    async def fake_agenerate_text(*args, **kwargs) -> str:
        # Simulate the LLM incorrectly treating a car fuel leak as a symptom.
        return '{"intent":"triage_symptoms","symptoms":["fuel leak"],"severity":"mild"}'

    monkeypatch.setattr(triage_router, "agenerate_text", fake_agenerate_text)

    state = asyncio.run(
        triage_router.triage_router_node(
            {"user_input": "i have a car and its leakimg fuel what should i do"}
        )
    )

    assert state["intent"] == "unclear"
    assert state["symptoms"] == []
    assert "medical symptom" in state["final_response"].lower()


def test_triage_router_keeps_genuine_symptoms_alongside_a_bad_one(monkeypatch):
    async def fake_agenerate_text(*args, **kwargs) -> str:
        return '{"intent":"triage_symptoms","symptoms":["chest pain","fuel leak"],"severity":"severe"}'

    monkeypatch.setattr(triage_router, "agenerate_text", fake_agenerate_text)

    state = asyncio.run(
        triage_router.triage_router_node({"user_input": "chest pain, also my car is leaking fuel"})
    )

    assert state["symptoms"] == ["chest pain"]
    assert state["intent"] == "triage_symptoms"


# ── Bug 2a: crisis/self-harm detection ────────────────────────────────────────

def test_looks_like_crisis_or_harm_detects_transcript_phrases():
    assert looks_like_crisis_or_harm("can i murder a doctor")
    assert looks_like_crisis_or_harm("i want to murder someone")
    assert looks_like_crisis_or_harm("I want to kill myself")
    assert looks_like_crisis_or_harm("thinking about suicide")


def test_looks_like_crisis_or_harm_does_not_misfire_on_pain_hyperbole():
    # "this headache is killing me" is common hyperbole, not a crisis statement —
    # deliberately not caught by a bare "kill" the way _looks_like_unsafe_non_medical is.
    assert not looks_like_crisis_or_harm("this headache is absolutely killing me")
    assert not looks_like_crisis_or_harm("my back pain is killing me today")


def test_heuristic_supervisor_route_returns_fixed_crisis_response_and_resets_awaiting():
    state = {
        "user_input": "i want to murder someone",
        "awaiting": "conversation",
        "questions_asked": ["How long have you been feeling this way?"],
    }
    route = supervisor._heuristic_supervisor_route(state)

    assert route is not None
    assert route["next_agent"] == "finish"
    assert route["awaiting"] is None  # not "conversation" — next turn routes fresh
    assert "1800-599-0019" in route["final_response"] or "112" in route["final_response"]


# ── Bug 2b: off-topic questions no longer trapped by the intake fast-path ────

def test_looks_like_general_knowledge_question_catches_transcript_examples():
    for text in (
        "hows the weather in hyd today",
        "who is the prime minister of india",
        "write me a python code",
        "what is the fastest way to reach to delhi",
    ):
        assert looks_like_general_knowledge_question(text), text


def test_looks_like_general_knowledge_question_does_not_flag_real_answers():
    for text in ("since yesterday", "mild, about a 4 out of 10", "no fever", "3 days"):
        assert not looks_like_general_knowledge_question(text), text


def test_should_stream_intake_false_for_off_topic_question_mid_intake():
    state = {
        "questions_asked": ["How long have you been feeling this way?"],
        "user_input": "hows the weather in hyd today",
        "collected_data": {},
    }
    assert should_stream_intake(state) is False


def test_heuristic_supervisor_route_does_not_trap_off_topic_question_in_conversation_state():
    state = {
        "user_input": "hows the weather in hyd today",
        "awaiting": "conversation",
        "questions_asked": ["How long have you been feeling this way?"],
    }
    route = supervisor._heuristic_supervisor_route(state)
    # Falls through (None) instead of forcing conversation_agent again — the caller
    # then defers to the LLM supervisor decision, which can route to general_qa.
    assert route is None


# ── Bug 3: stale facts no longer leak into general_qa ────────────────────────

def test_state_summary_omits_known_facts_for_general_qa():
    state = {
        "active_intent": "triage_symptoms",
        "symptoms": ["fuel leak"],
        "collected_facts": {"cause": "fuel leak"},
    }
    with_facts = supervisor._state_summary(state)
    without_facts = supervisor._state_summary(state, include_facts=False)

    assert "fuel leak" in with_facts
    assert "fuel leak" not in without_facts
    assert "Not applicable" in without_facts


def test_state_summary_includes_analyzed_documents():
    state = {
        "analyzed_documents": [
            {"document_type": "prescription", "file_name": "rx.jpg", "summary": "Amoxicillin 500mg twice daily"},
        ],
    }
    summary = supervisor._state_summary(state)
    assert "prescription" in summary
    assert "Amoxicillin" in summary


# ── Bug 4: a follow-up question about an uploaded document gets answered ─────

def test_document_analyzer_falls_back_to_session_summary_when_catalog_is_empty(monkeypatch):
    async def fake_catalog_retrieval(state):
        return None  # simulates: background ingestion not finished yet / no consent

    async def fake_agenerate_text(*args, **kwargs) -> str:
        return "Your prescription lists Amoxicillin 500mg, twice daily for 5 days."

    monkeypatch.setattr(document_analyzer, "_catalog_retrieval_response", fake_catalog_retrieval)
    monkeypatch.setattr("app.inference.llm.agenerate_text", fake_agenerate_text)

    state = {
        "user_input": "what does my prescription say",
        "analyzed_documents": [
            {"document_type": "prescription", "file_name": "rx.jpg", "summary": "Amoxicillin 500mg twice daily"},
        ],
        "conversation_history": [],
    }
    result = asyncio.run(document_analyzer.document_analyzer_node(state))

    assert "Amoxicillin" in result["final_response"]
    assert "I don't see any previously uploaded" not in result["final_response"]


def test_document_analyzer_still_shows_no_document_message_when_nothing_was_ever_uploaded(monkeypatch):
    async def fake_catalog_retrieval(state):
        return None

    monkeypatch.setattr(document_analyzer, "_catalog_retrieval_response", fake_catalog_retrieval)

    state = {"user_input": "what does my prescription say", "analyzed_documents": [], "conversation_history": []}
    result = asyncio.run(document_analyzer.document_analyzer_node(state))

    assert "I don't see any previously uploaded" in result["final_response"]
