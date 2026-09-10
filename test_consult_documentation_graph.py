"""SOAP note generation subgraph tests (Phase 3, Part 2) — mocked LLM only, no DB.

Mirrors this repo's existing convention (see test_consult_routes.py) for testing async
code without pytest-asyncio (not installed in this project): drive the coroutine with a
plain asyncio.run() wrapper inside an otherwise-sync test function.
"""
import asyncio
import json

import pytest

from app.agents import consult_documentation_graph as docgraph


def _segments():
    return [
        {"id": "s1", "speaker": "patient", "text": "I have had a headache for 2 days."},
        {"id": "s2", "speaker": "doctor", "text": "Your blood pressure is 120 over 80. Sounds like a tension headache."},
    ]


def _mock_llm(monkeypatch, payload: dict):
    async def fake_agenerate_text(**kwargs):
        return json.dumps(payload)

    monkeypatch.setattr(docgraph, "agenerate_text", fake_agenerate_text)


def _generate(segments=None):
    return asyncio.run(docgraph.agenerate_soap_note("c1", "p1", segments if segments is not None else _segments()))


# ── transcript_segmenter_node ─────────────────────────────────────────────────

def test_transcript_segmenter_preserves_segment_ids_and_speaker_labels():
    result = docgraph.transcript_segmenter_node({"segments": _segments()})
    text = result["transcript_text"]
    assert "[s1] Patient: I have had a headache for 2 days." in text
    assert "[s2] Doctor: Your blood pressure is 120 over 80. Sounds like a tension headache." in text


def test_transcript_segmenter_skips_segments_without_an_id():
    segments = _segments() + [{"speaker": "doctor", "text": "no id here"}]
    result = docgraph.transcript_segmenter_node({"segments": segments})
    assert "no id here" not in result["transcript_text"]


# ── soap_extractor_node + confidence_validator_node (via agenerate_soap_note) ───

def test_every_field_gets_a_citation_when_the_model_cites_correctly(monkeypatch):
    _mock_llm(monkeypatch, {
        "subjective": {"text": "Headache for 2 days.", "citations": ["s1"], "confident": True},
        "objective": {"text": "BP 120/80.", "citations": ["s2"], "confident": True},
        "assessment": {"text": "Tension headache.", "citations": ["s2"], "confident": True},
        "plan": {"text": "Rest and hydrate.", "citations": ["s1", "s2"], "confident": True},
    })

    result = _generate()

    for field in ("subjective", "objective", "assessment", "plan"):
        assert result["field_citations"][field], f"{field} has no citations"
        assert result["confidence_flags"][field] is False


def test_citation_to_a_nonexistent_segment_id_is_dropped_and_flags_not_confident(monkeypatch):
    """The model claims confident=True but cites a segment id that isn't in this
    transcript at all — the validator must not let that field reach the doctor looking
    as trustworthy as a properly-cited one."""
    _mock_llm(monkeypatch, {
        "subjective": {"text": "Headache for 2 days.", "citations": ["s1"], "confident": True},
        "objective": {"text": "BP 120/80.", "citations": ["s2"], "confident": True},
        "assessment": {"text": "Tension headache.", "citations": ["s2"], "confident": True},
        "plan": {"text": "Rest and hydrate.", "citations": ["does-not-exist"], "confident": True},
    })

    result = _generate()

    assert result["field_citations"]["plan"] == []
    assert result["confidence_flags"]["plan"] is True


def test_model_reported_low_confidence_is_preserved(monkeypatch):
    _mock_llm(monkeypatch, {
        "subjective": {"text": "Headache for 2 days.", "citations": ["s1"], "confident": True},
        "objective": {"text": "BP 120/80.", "citations": ["s2"], "confident": True},
        "assessment": {"text": "Possibly a tension headache, unclear.", "citations": ["s2"], "confident": False},
        "plan": {"text": "Rest and hydrate.", "citations": ["s1"], "confident": True},
    })

    result = _generate()

    assert result["confidence_flags"]["assessment"] is True
    assert result["field_citations"]["assessment"] == ["s2"]  # citation kept, only confidence is flagged


def test_empty_field_with_no_citations_is_not_flagged(monkeypatch):
    """A genuinely empty section (nothing in the transcript to fill it) is valid and
    should not be penalized just for having zero citations."""
    _mock_llm(monkeypatch, {
        "subjective": {"text": "Headache for 2 days.", "citations": ["s1"], "confident": True},
        "objective": {"text": "BP 120/80.", "citations": ["s2"], "confident": True},
        "assessment": {"text": "", "citations": [], "confident": True},
        "plan": {"text": "", "citations": [], "confident": True},
    })

    result = _generate()

    assert result["confidence_flags"]["assessment"] is False
    assert result["confidence_flags"]["plan"] is False


def test_malformed_llm_output_raises_runtime_error(monkeypatch):
    async def fake_agenerate_text(**kwargs):
        return "not valid json at all"

    monkeypatch.setattr(docgraph, "agenerate_text", fake_agenerate_text)

    with pytest.raises(RuntimeError):
        _generate()


def test_markdown_fenced_json_is_still_parsed(monkeypatch):
    payload = {
        "subjective": {"text": "Headache for 2 days.", "citations": ["s1"], "confident": True},
        "objective": {"text": "BP 120/80.", "citations": ["s2"], "confident": True},
        "assessment": {"text": "Tension headache.", "citations": ["s2"], "confident": True},
        "plan": {"text": "Rest and hydrate.", "citations": ["s1"], "confident": True},
    }

    async def fake_agenerate_text(**kwargs):
        return f"```json\n{json.dumps(payload)}\n```"

    monkeypatch.setattr(docgraph, "agenerate_text", fake_agenerate_text)

    result = _generate()
    assert result["subjective"] == "Headache for 2 days."
