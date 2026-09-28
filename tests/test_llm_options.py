"""agenerate_text's per-call budget and its opt-out from the canned fallback."""
from __future__ import annotations

import asyncio

import pytest

from app.inference import llm


def _patch(monkeypatch, behaviour):
    seen = {}

    async def fake_completion(client, **kwargs):
        seen.update(kwargs)
        return behaviour()

    monkeypatch.setattr(llm, "_async_client", object())
    monkeypatch.setattr(llm, "_achat_completion", fake_completion)
    return seen


def test_the_shared_cap_applies_unless_a_caller_asks_for_more(monkeypatch):
    seen = _patch(monkeypatch, lambda: "ok")
    asyncio.run(llm.agenerate_text("s", "u"))
    assert seen["max_tokens"] == llm.MAX_TOKENS
    asyncio.run(llm.agenerate_text("s", "u", max_tokens=8000))
    assert seen["max_tokens"] == 8000


def test_a_failure_still_falls_back_by_default(monkeypatch):
    def boom():
        raise TimeoutError("slow")
    _patch(monkeypatch, boom)
    assert isinstance(asyncio.run(llm.agenerate_text("s", "u")), str)


def test_a_caller_can_have_the_failure_raised_instead(monkeypatch):
    def boom():
        raise TimeoutError("slow")
    _patch(monkeypatch, boom)
    with pytest.raises(TimeoutError):
        asyncio.run(llm.agenerate_text("s", "u", fallback=False))
