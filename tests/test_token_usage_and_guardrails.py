"""LLM fallback / token-accounting coverage for app/inference/llm.py and
app/services/llm_usage.py.

generate_text/agenerate_text/generate_router_text each gate on a module-level client
(`_sync_client` / `_async_client` in app/inference/llm.py) that is constructed exactly
once, at import time, from OPENAI_API_KEY — `if OPENAI_API_KEY: _sync_client = ...`.
Clearing the env var after import has no effect, so these tests monkeypatch the module
attributes directly, which is the only way to actually exercise the
"no client configured" branch (`if not _sync_client: raise RuntimeError(...)`) that
every generate_*() function catches and falls through to `_local_fallback()` for.

record_llm_usage()'s DB write (persist_token_log) is fire-and-forget: with no running
event loop (the normal case for a plain sync call/test) it spawns a background daemon
thread that does `asyncio.run(...)`, so asserting against the real table from the
calling thread would be racy. Per this repo's stated approach ("monkeypatch the DB layer
if the function is structured to allow that cleanly"), the orchestration test below
monkeypatches llm_usage.persist_token_log itself to assert record_llm_usage() builds and
forwards the right TokenLogRecord. A second, real-DB test then exercises the actual write
path (llm_usage._persist_token_log_sync, the synchronous function persist_token_log runs
under the hood) directly — skipping cleanly if Postgres isn't reachable, matching
test_admin_doctor_management_integration.py's convention.
"""

from __future__ import annotations

import asyncio

import pytest

from app.db.connection import connect_db
import app.inference.llm as llm
import app.services.llm_usage as llm_usage
from app.services.llm_usage import TokenLogRecord, estimate_tokens


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


# ── No client configured → local fallback ────────────────────────────────────

def test_generate_text_falls_back_to_local_when_no_client_configured(monkeypatch):
    monkeypatch.setattr(llm, "_sync_client", None)

    result = llm.generate_text("You are a helpful assistant.", "Hello, how are you?")

    assert isinstance(result, str)
    assert result.strip() != ""


def test_agenerate_text_falls_back_to_local_when_no_client_configured(monkeypatch):
    monkeypatch.setattr(llm, "_async_client", None)

    result = asyncio.run(llm.agenerate_text("You are a helpful assistant.", "Hello, how are you?"))

    assert isinstance(result, str)
    assert result.strip() != ""


def test_generate_router_text_falls_back_to_local_when_no_client_configured(monkeypatch):
    monkeypatch.setattr(llm, "_sync_client", None)

    result = llm.generate_router_text("Triage Router Agent system prompt", "Latest message:\nfever")

    assert isinstance(result, str)
    assert result.strip() != ""
    # falls through to the Triage-Router-specific branch of _local_fallback, not the
    # generic string, proving it actually ran the fallback logic (not just returned "").
    import json
    parsed = json.loads(result)
    assert parsed["intent"] == "unclear"


def test_generate_router_text_reraises_when_raise_on_error_is_set(monkeypatch):
    """The one generate_*_text() knob that does NOT swallow into the local fallback."""
    monkeypatch.setattr(llm, "_sync_client", None)

    with pytest.raises(RuntimeError):
        llm.generate_router_text(
            "some system prompt", "some user prompt", raise_on_error=True,
        )


def test_local_fallback_never_raises_and_is_non_empty_for_an_unmatched_prompt():
    result = llm._local_fallback("Some arbitrary system prompt with no special markers.", "Hi there")
    assert isinstance(result, str)
    assert result.strip() != ""


# ── _completion_options() includes the configured max_tokens ────────────────

def test_completion_options_includes_max_completion_tokens_and_temperature():
    options = llm._completion_options("gpt-4o", max_tokens=llm.MAX_TOKENS, temperature=0.1)

    assert options["max_completion_tokens"] == llm.MAX_TOKENS
    assert options["temperature"] == 0.1
    assert "stream" not in options


def test_completion_options_includes_router_max_tokens_for_router_call():
    options = llm._completion_options("gpt-4o", max_tokens=llm.ROUTER_MAX_TOKENS, temperature=0)
    assert options["max_completion_tokens"] == llm.ROUTER_MAX_TOKENS


def test_completion_options_omits_temperature_for_gpt5_reasoning_models():
    """gpt-5* reasoning models reject a custom temperature — _completion_options must
    drop it rather than send the API default-incompatible value."""
    options = llm._completion_options("gpt-5.6-mini", max_tokens=llm.SUMMARY_MAX_TOKENS, temperature=0.1)
    assert options["max_completion_tokens"] == llm.SUMMARY_MAX_TOKENS
    assert "temperature" not in options


def test_completion_options_sets_stream_flag_when_requested():
    options = llm._completion_options("gpt-4o", max_tokens=llm.MAX_TOKENS, temperature=0.1, stream=True)
    assert options["stream"] is True


# ── record_llm_usage: orchestration (monkeypatched DB layer) ────────────────

def test_record_llm_usage_persists_expected_fields(monkeypatch):
    captured = {}

    def fake_persist_token_log(record: TokenLogRecord):
        captured["record"] = record

    monkeypatch.setattr(llm_usage, "persist_token_log", fake_persist_token_log)

    llm_usage.record_llm_usage(
        model="gpt-4o",
        call_type="generation",
        prompt="hi",
        completion="hello there",
        response=None,
        node_name="test_node",
        session_id="session-123",
        patient_id="patient-456",
        status="SUCCESS",
        latency_ms=42,
    )

    record = captured["record"]
    assert isinstance(record, TokenLogRecord)
    assert record.session_id == "session-123"
    assert record.patient_id == "patient-456"
    assert record.node_name == "test_node"
    assert record.model_name == "gpt-4o"
    assert record.input_tokens == estimate_tokens("hi")
    assert record.output_tokens == estimate_tokens("hello there")
    assert record.status == "SUCCESS"
    assert record.latency_ms == 42


def test_record_llm_usage_skips_persistence_when_session_or_patient_missing(monkeypatch):
    """persist_token_log is only reachable when both session_id and patient_id are
    truthy — an anonymous/unauthenticated call (patient_id=None) must not attempt it."""
    called = {"count": 0}

    def fake_persist_token_log(record: TokenLogRecord):
        called["count"] += 1

    monkeypatch.setattr(llm_usage, "persist_token_log", fake_persist_token_log)

    llm_usage.record_llm_usage(
        model="gpt-4o", call_type="generation", prompt="hi", completion="hello",
        session_id=None, patient_id=None,
    )

    assert called["count"] == 0


def test_record_llm_usage_appends_to_active_collector_when_present(monkeypatch):
    """The in-memory usage_records list (used by /chat's token_usage summary) is
    populated regardless of whether the DB persistence path fires."""
    monkeypatch.setattr(llm_usage, "persist_token_log", lambda record: None)

    with llm_usage.collect_llm_usage() as records:
        llm_usage.record_llm_usage(
            model="gpt-4o", call_type="generation", prompt="hi", completion="hello",
            session_id=None, patient_id=None,
        )
        assert len(records) == 1
        assert records[0]["model"] == "gpt-4o"
        assert records[0]["prompt_tokens"] == estimate_tokens("hi")
        assert records[0]["completion_tokens"] == estimate_tokens("hello")


# ── record_llm_usage: real DB write path ─────────────────────────────────────

def test_persist_token_log_sync_writes_expected_row_to_a_real_database():
    """Exercises the actual synchronous DB write that record_llm_usage()'s
    persist_token_log() eventually runs (via a background thread/task) — called
    directly here so the test is deterministic instead of racing a spawned thread."""
    _skip_if_no_database()

    record = TokenLogRecord(
        session_id="test-session-token-usage-e2e",
        patient_id="test-patient-token-usage-e2e",
        node_name="test_node",
        model_name="gpt-4o",
        input_tokens=11,
        output_tokens=7,
        status="SUCCESS",
        latency_ms=99,
    )

    try:
        llm_usage._persist_token_log_sync(record)

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT patient_id, node_name, model_name, input_tokens,
                              output_tokens, status, latency_ms
                       FROM token_logs WHERE session_id = %s""",
                    (record.session_id,),
                )
                row = cur.fetchone()

        assert row is not None
        patient_id, node_name, model_name, input_tokens, output_tokens, status, latency_ms = row
        assert patient_id == "test-patient-token-usage-e2e"
        assert node_name == "test_node"
        assert model_name == "gpt-4o"
        assert input_tokens == 11
        assert output_tokens == 7
        assert status == "SUCCESS"
        assert latency_ms == 99
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM token_logs WHERE session_id = %s", (record.session_id,))
            conn.commit()
