import asyncio

from app.agents import triage_router
from app.agents.intake_utils import extract_local_intake_info, looks_like_intake_wrapup


def test_triage_router_extracts_intent_and_symptoms(monkeypatch):
    async def fake_agenerate_text(*args, **kwargs) -> str:
        return '{"intent":"triage_symptoms","symptoms":["dizziness","chest tightness"],"severity":"severe"}'

    monkeypatch.setattr(triage_router, "agenerate_text", fake_agenerate_text)

    state = asyncio.run(
        triage_router.triage_router_node(
            {"user_input": "I woke up feeling super dizzy and my chest is tight."}
        )
    )

    assert state["intent"] == "triage_symptoms"
    assert state["symptoms"] == ["dizziness", "chest tightness"]
    assert state["severity"] == "severe"
    assert "final_response" not in state


def test_triage_router_uses_llm_for_body_part_pain_and_urgency(monkeypatch):
    async def fake_agenerate_text(*args, **kwargs) -> str:
        return '{"intent":"triage_symptoms","symptoms":["leg pain"],"severity":"severe"}'

    monkeypatch.setattr(triage_router, "agenerate_text", fake_agenerate_text)

    state = asyncio.run(
        triage_router.triage_router_node({"user_input": "severe leg pain"})
    )

    assert state["intent"] == "triage_symptoms"
    assert state["symptoms"] == ["leg pain"]
    assert state["severity"] == "severe"


def test_triage_router_clarifies_on_bad_llm_output(monkeypatch):
    async def fake_agenerate_text(*args, **kwargs) -> str:
        return "not json"

    monkeypatch.setattr(triage_router, "agenerate_text", fake_agenerate_text)

    state = asyncio.run(
        triage_router.triage_router_node({"user_input": "severe leg pain"})
    )

    assert state["intent"] == "unclear"
    assert state["symptoms"] == []
    assert state["severity"] == "mild"
    assert "could not reliably understand" in state["final_response"].lower()


def test_triage_router_returns_clarification_when_llm_and_fast_extract_fail(monkeypatch):
    async def fake_agenerate_text(*args, **kwargs) -> str:
        return "not json"

    monkeypatch.setattr(triage_router, "agenerate_text", fake_agenerate_text)

    state = asyncio.run(
        triage_router.triage_router_node({"user_input": "help"})
    )

    assert state["intent"] == "unclear"
    assert state["symptoms"] == []
    assert state["severity"] == "mild"
    assert "could not reliably understand" in state["final_response"]


def test_extract_local_intake_info_handles_common_duration_and_trigger_phrases():
    info = extract_local_intake_info(
        "i havent slept properly since last night, on and off for 3-4 months, overthinking a lot lately which triggers anxiety"
    )

    assert info["duration"] == "since last night"
    assert info["cause"] == "stress or anxiety"
    assert info["pattern"] == "sleep disturbance"


def test_looks_like_intake_wrapup_flags_summary_phrases():
    assert looks_like_intake_wrapup("i have mentioned everything that is all")
    assert looks_like_intake_wrapup("i have summarise everything up")
