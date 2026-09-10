"""End-to-end coverage for the consult audio WebSocket handler
(`consult_audio_ws` in app/api/routes/consult.py) — the highest-priority gap identified
in FULL_SYSTEM_AUDIT.md: no existing test drove this handler at all before this file.

Same conventions as the rest of this repo's consult test suite:
- Route-level tests (the majority of this file) call the route coroutine directly (no
  TestClient/real network) and monkeypatch the service layer — see test_consult_routes.py.
  Since `consult_audio_ws` takes a real `fastapi.WebSocket` and talks to Deepgram via
  `websockets.connect`, this file builds two minimal test doubles instead of a full ASGI
  client: a `FakeClientWebSocket` that implements only the WebSocket methods the handler
  actually calls (query_params.get / accept / receive / send_json / send_bytes /
  send_text / close), and a `FakeDeepgramWS` + `FakeDeepgramConnect` pair that stand in
  for `websockets.connect(...)` used as `async with ... as deepgram_ws`, monkeypatched
  onto the `websockets` module directly (consult.py does `import websockets` then calls
  `websockets.connect(...)`, so patching `consult_route.websockets.connect` is exactly
  the module-level `websockets.connect`).
- One DB-backed "integration" test (zero-segment batch retranscription) follows the
  connect_db()-and-skip-cleanly pattern from test_consult_integration.py.

Deepgram message shapes reused from test_consult_parsing.py's understanding of the
Results event shape (parse_deepgram_streaming_result), but this file monkeypatches
parse_deepgram_streaming_result directly for the WS-level tests rather than re-deriving
real Deepgram JSON, since test_consult_parsing.py already pins that parsing logic
thoroughly — duplicating it here would just be redundant.
"""
from __future__ import annotations

import asyncio
import io
import json

import pytest
from websockets.exceptions import ConnectionClosedError

from app.api.routes import consult as consult_route
from app.db.connection import connect_db
from app.services import consults as consults_module
from app.services.consults import (
    begin_recording,
    get_transcript,
    record_consent,
    run_batch_retranscription,
    start_consult,
)


def _doctor(doctor_id="doctor-1", account_id="account-1", department="Cardiology"):
    return {"doctor_id": doctor_id, "account_id": account_id, "department": department}


# ── Test doubles ─────────────────────────────────────────────────────────────

class FakeClientWebSocket:
    """Implements only the subset of fastapi.WebSocket that consult_audio_ws actually
    calls: query_params.get(), accept(), receive() (returning raw ASGI-style message
    dicts, matching exactly what the handler pattern-matches on:
    {"type": "websocket.disconnect"} / {"bytes": ...} / {"text": "__stop__"}),
    send_json/send_bytes/send_text, and close(code=...)."""

    def __init__(self, query_params=None, incoming=None):
        self.query_params = query_params or {}
        self._incoming = list(incoming or [])
        self.accepted = False
        self.sent_json = []
        self.sent_bytes = []
        self.sent_text = []
        self.close_calls = []

    async def accept(self):
        self.accepted = True

    async def receive(self):
        # Once the queued script runs out, behave like a client that has gone away —
        # keeps relay_audio() from spinning forever if a test forgets to queue an
        # explicit terminal message.
        if not self._incoming:
            return {"type": "websocket.disconnect"}
        return self._incoming.pop(0)

    async def send_json(self, data):
        self.sent_json.append(data)

    async def send_bytes(self, data):
        self.sent_bytes.append(data)

    async def send_text(self, data):
        self.sent_text.append(data)

    async def close(self, code=1000):
        self.close_calls.append(code)


class FakeDeepgramWS:
    """Fakes the Deepgram streaming connection object relay_audio()/relay_results() use
    (`.send(bytes)` and `async for payload in deepgram_ws`).

    Modeled as request/response over an asyncio.Queue rather than a pre-baked list: each
    non-empty `send()` (an audio frame relay_audio forwards) can produce zero or more
    queued response payloads via `respond_to_frame`, and relay_results() consumes them via
    `async for`. This mirrors the real send-audio/receive-transcript interleaving closely
    enough to be deterministic under asyncio's single-threaded scheduler (neither of these
    fakes' awaited calls ever truly suspend before all queued items exist, so there is no
    race between relay_audio finishing and relay_results draining the queue).

    An empty-bytes send (`b""`) is relay_audio's own "I'm done sending" signal (both on a
    clean disconnect and on an explicit `__stop__`); this fake treats it as the cue to end
    the results iterator too, standing in for Deepgram closing the socket shortly after.

    `raise_on_iter`, if set, is raised from the very first `__anext__()` call instead —
    used to simulate a Deepgram-side connection failure mid-stream.
    """

    def __init__(self, respond_to_frame=None, raise_on_iter=None):
        self._queue: asyncio.Queue = asyncio.Queue()
        self.sent: list[bytes] = []
        self._respond_to_frame = respond_to_frame
        self._raise_on_iter = raise_on_iter

    async def send(self, data):
        self.sent.append(data)
        if data == b"":
            await self._queue.put(None)
            return
        if self._respond_to_frame:
            result = self._respond_to_frame(data)
            if result is not None:
                await self._queue.put(json.dumps(result))

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._raise_on_iter is not None:
            raise self._raise_on_iter
        item = await self._queue.get()
        if item is None:
            raise StopAsyncIteration
        return item


class FakeDeepgramConnect:
    """Stands in for the object `websockets.connect(...)` returns, used exactly as
    `async with websockets.connect(...) as deepgram_ws:` — only needs to be an async
    context manager, not also awaitable (consult.py never awaits it directly)."""

    def __init__(self, ws):
        self._ws = ws

    async def __aenter__(self):
        return self._ws

    async def __aexit__(self, exc_type, exc, tb):
        return False


# ── Shared mock wiring ──────────────────────────────────────────────────────

def _wire_auth_and_consult(monkeypatch, *, doctor=None, consult_status="consented", dg_key="fake-dg-key"):
    """Wires the pieces every test needs regardless of what it's specifically probing:
    a valid access token, a doctor profile lookup, an owned consult in the given status,
    and a configured Deepgram key (empty string reproduces the "not configured" branch,
    which no test here needs, so the default is a non-empty fake key)."""
    doctor = doctor or _doctor()
    monkeypatch.setattr(consult_route, "DEEPGRAM_API_KEY", dg_key)
    monkeypatch.setattr(
        consult_route, "verify_access_token",
        lambda token: {
            "role": "doctor", "token_kind": "doctor_session",
            "sub": doctor["doctor_id"], "doctor_id": doctor["doctor_id"],
            "account_id": doctor["account_id"],
        },
    )
    monkeypatch.setattr(consult_route, "get_doctor_profile", lambda doctor_id, account_id: dict(doctor))
    monkeypatch.setattr(
        consult_route, "get_consult_owned",
        lambda cid, doctor_id: {"id": cid, "status": consult_status},
    )
    return doctor


def _wire_recording_plumbing(monkeypatch, *, temp_handle=None, finalize_storage_ref="consult-audio/doctor-1/c1.pcm"):
    """Wires begin_recording/list_keyterms/build_url/open_tempfile/finalize/set_blob/
    end_consult/run_batch_retranscription to no-DB fakes that just record what they were
    called with, so route-level tests never touch Postgres or the filesystem."""
    calls = {}

    def fake_begin_recording(cid, doctor_id, *, sample_rate=None):
        calls["begin_recording"] = {"consultation_id": cid, "doctor_id": doctor_id, "sample_rate": sample_rate}
        return {"id": cid, "status": "recording"}

    monkeypatch.setattr(consult_route, "begin_recording", fake_begin_recording)
    monkeypatch.setattr(consult_route, "list_keyterms_for_department", lambda dept: [])
    monkeypatch.setattr(
        consult_route, "build_deepgram_streaming_url",
        lambda *, sample_rate, keyterms: "wss://fake-deepgram/listen",
    )

    handle = temp_handle if temp_handle is not None else io.BytesIO()
    monkeypatch.setattr(consult_route, "open_recording_tempfile", lambda: (handle, "fake-temp-path.pcm"))

    async def fake_finalize(temp_path, *, doctor_id, consultation_id):
        calls["finalize_recording"] = {
            "temp_path": temp_path, "doctor_id": doctor_id, "consultation_id": consultation_id,
        }
        return finalize_storage_ref

    monkeypatch.setattr(consult_route, "finalize_recording", fake_finalize)

    def fake_set_audio_blob_path(cid, path):
        calls["set_audio_blob_path"] = {"consultation_id": cid, "path": path}

    monkeypatch.setattr(consult_route, "set_audio_blob_path", fake_set_audio_blob_path)

    def fake_end_consult(cid, doctor_id):
        calls["end_consult"] = {"consultation_id": cid, "doctor_id": doctor_id}
        return {"id": cid, "status": "ended"}

    monkeypatch.setattr(consult_route, "end_consult", fake_end_consult)

    async def fake_retranscribe(cid):
        calls["run_batch_retranscription"] = cid

    monkeypatch.setattr(consult_route, "run_batch_retranscription", fake_retranscribe)

    return calls


async def _run_ws_and_flush(ws, consultation_id):
    """Runs the handler, then yields once so the fire-and-forget
    asyncio.create_task(run_batch_retranscription(...)) scheduled in the handler's
    finally block actually gets a turn to execute before the test asserts on it."""
    await asyncio.wait_for(consult_route.consult_audio_ws(ws, consultation_id), timeout=5)
    await asyncio.sleep(0)


# ── Happy path ───────────────────────────────────────────────────────────────

def test_consult_audio_ws_happy_path_streams_persists_and_finalizes(monkeypatch):
    """Connect -> authenticate -> stream two fake audio frames -> fake Deepgram returns
    an interim transcript result per frame -> each gets persisted via
    append_transcript_segment -> client disconnects cleanly -> recording is finalized,
    audio_blob_path is set, the consult is ended, and re-transcription is scheduled."""
    doctor = _wire_auth_and_consult(monkeypatch)
    calls = _wire_recording_plumbing(monkeypatch)

    persisted = []

    def fake_append_transcript_segment(cid, **segment):
        persisted.append((cid, segment))

    monkeypatch.setattr(consult_route, "append_transcript_segment", fake_append_transcript_segment)

    def fake_parse(data):
        if data.get("type") != "Results":
            return None
        return {
            "speaker": "doctor", "start_ms": 0, "end_ms": 1000,
            "text": data["_label"], "confidence": 0.9, "is_final": False,
        }

    monkeypatch.setattr(consult_route, "parse_deepgram_streaming_result", fake_parse)

    def respond_to_frame(data):
        return {"type": "Results", "_label": f"transcript for {data.decode()}"}

    fake_dg_ws = FakeDeepgramWS(respond_to_frame=respond_to_frame)
    monkeypatch.setattr(consult_route.websockets, "connect", lambda *a, **k: FakeDeepgramConnect(fake_dg_ws))

    incoming = [
        {"type": "websocket.receive", "bytes": b"frame-1"},
        {"type": "websocket.receive", "bytes": b"frame-2"},
        {"type": "websocket.disconnect"},
    ]
    ws = FakeClientWebSocket(query_params={"token": "tok", "sample_rate": "48000"}, incoming=incoming)

    asyncio.run(_run_ws_and_flush(ws, "c1"))

    assert ws.accepted is True
    assert calls["begin_recording"] == {"consultation_id": "c1", "doctor_id": "doctor-1", "sample_rate": 48000}

    assert len(persisted) == 2
    assert {seg["text"] for _, seg in persisted} == {
        "transcript for frame-1", "transcript for frame-2",
    }
    assert all(cid == "c1" for cid, _ in persisted)

    # Both interim results were relayed back to the client as raw text too.
    assert len(ws.sent_text) == 2

    # Clean disconnect -> relay_audio sends an empty frame to Deepgram, never an error.
    assert b"" in fake_dg_ws.sent
    assert ws.sent_json == []

    assert calls["finalize_recording"] == {
        "temp_path": "fake-temp-path.pcm", "doctor_id": "doctor-1", "consultation_id": "c1",
    }
    assert calls["set_audio_blob_path"] == {"consultation_id": "c1", "path": "consult-audio/doctor-1/c1.pcm"}
    assert calls["end_consult"] == {"consultation_id": "c1", "doctor_id": "doctor-1"}
    # end_consult transitioned to 'ended' -> _should_schedule_retranscription is True.
    assert calls["run_batch_retranscription"] == "c1"

    assert ws.close_calls == [1000]


# ── Recording size/duration cap (FULL_SYSTEM_AUDIT.md P1 #9) ────────────────

def test_consult_audio_ws_stops_recording_once_byte_cap_is_reached(monkeypatch):
    """Previously there was no cap on live recording size/duration at all — the only
    backstop was a periodic background sweep that changes a DB status but never closes
    the live socket. Confirms the WS handler itself now stops the recording once the
    configured byte cap is hit: an error is sent to the client, Deepgram is told the
    stream ended, and the partial recording still finalizes normally rather than being
    lost or crashing the handler."""
    _wire_auth_and_consult(monkeypatch)
    calls = _wire_recording_plumbing(monkeypatch)
    monkeypatch.setattr(consult_route, "append_transcript_segment", lambda *a, **k: None)
    monkeypatch.setattr(consult_route, "parse_deepgram_streaming_result", lambda data: None)
    monkeypatch.setattr(consult_route, "CONSULT_MAX_RECORDING_BYTES", 10)  # tiny — one frame exceeds it

    fake_dg_ws = FakeDeepgramWS()
    monkeypatch.setattr(consult_route.websockets, "connect", lambda *a, **k: FakeDeepgramConnect(fake_dg_ws))

    incoming = [
        {"type": "websocket.receive", "bytes": b"0123456789ABCDEF"},  # 16 bytes > cap of 10
        {"type": "websocket.receive", "bytes": b"should never be reached"},
        {"type": "websocket.disconnect"},
    ]
    ws = FakeClientWebSocket(query_params={"token": "tok", "sample_rate": "48000"}, incoming=incoming)

    asyncio.run(_run_ws_and_flush(ws, "c1"))

    assert any("maximum allowed size or duration" in msg.get("message", "") for msg in ws.sent_json)
    # Deepgram was told the stream ended (empty-bytes terminal frame), same as a clean stop.
    assert b"" in fake_dg_ws.sent
    # The second queued frame was never sent — the loop broke immediately after the cap.
    assert b"should never be reached" not in fake_dg_ws.sent
    # The partial recording still finalizes normally, it isn't lost or left dangling.
    assert calls["finalize_recording"]["consultation_id"] == "c1"
    assert calls["end_consult"] == {"consultation_id": "c1", "doctor_id": "doctor-1"}


def test_consult_audio_ws_stops_recording_once_duration_cap_is_reached(monkeypatch):
    """Same mechanism, the other trigger: CONSULT_MAX_RECORDING_HOURS elapsed, not bytes.
    Setting it to 0 means any elapsed wall-clock time after the first frame exceeds it."""
    _wire_auth_and_consult(monkeypatch)
    calls = _wire_recording_plumbing(monkeypatch)
    monkeypatch.setattr(consult_route, "append_transcript_segment", lambda *a, **k: None)
    monkeypatch.setattr(consult_route, "parse_deepgram_streaming_result", lambda data: None)
    monkeypatch.setattr(consult_route, "CONSULT_MAX_RECORDING_HOURS", 0.0)

    fake_dg_ws = FakeDeepgramWS()
    monkeypatch.setattr(consult_route.websockets, "connect", lambda *a, **k: FakeDeepgramConnect(fake_dg_ws))

    incoming = [
        {"type": "websocket.receive", "bytes": b"frame-1"},
        {"type": "websocket.receive", "bytes": b"should never be reached"},
        {"type": "websocket.disconnect"},
    ]
    ws = FakeClientWebSocket(query_params={"token": "tok", "sample_rate": "48000"}, incoming=incoming)

    asyncio.run(_run_ws_and_flush(ws, "c1"))

    assert any("maximum allowed size or duration" in msg.get("message", "") for msg in ws.sent_json)
    assert b"should never be reached" not in fake_dg_ws.sent
    assert calls["finalize_recording"]["consultation_id"] == "c1"


# ── Mid-stream Deepgram disconnect ──────────────────────────────────────────

def test_consult_audio_ws_mid_stream_deepgram_disconnect_is_silently_swallowed_today(monkeypatch):
    """Pins CURRENT actual behavior after reading the handler's except-block handling
    directly: `except ConnectionClosed: pass` sits ABOVE the generic
    `except Exception as exc: await websocket.send_json({"type": "error", ...})` branch,
    so when the Deepgram connection drops mid-stream (relay_results' `async for payload in
    deepgram_ws` raises ConnectionClosed/ConnectionClosedError), the handler does NOT
    notify the client at all — no error message is ever sent, the socket is just closed
    with the ordinary code (1000) in the finally block, exactly as if the session had
    ended normally. This looks like a UX gap (a doctor watching the recording UI would see
    it just... stop, with no indication anything went wrong) but this test only pins what
    the code does today; it does not assert what it *should* do.

    The finally block still runs regardless (finalize/end/schedule-retranscription), which
    this test also confirms — the silence is specifically about client notification, not
    about skipping cleanup."""
    _wire_auth_and_consult(monkeypatch)
    calls = _wire_recording_plumbing(monkeypatch)
    monkeypatch.setattr(consult_route, "append_transcript_segment", lambda cid, **seg: None)
    monkeypatch.setattr(consult_route, "parse_deepgram_streaming_result", lambda data: None)

    fake_dg_ws = FakeDeepgramWS(raise_on_iter=ConnectionClosedError(None, None))
    monkeypatch.setattr(consult_route.websockets, "connect", lambda *a, **k: FakeDeepgramConnect(fake_dg_ws))

    incoming = [
        {"type": "websocket.receive", "bytes": b"frame-1"},
        {"type": "websocket.disconnect"},
    ]
    ws = FakeClientWebSocket(query_params={"token": "tok", "sample_rate": "48000"}, incoming=incoming)

    asyncio.run(_run_ws_and_flush(ws, "c1"))

    # No error was ever surfaced to the client — this is the behavior being pinned.
    assert ws.sent_json == []
    assert ws.close_calls == [1000]

    # Cleanup still ran to completion despite the silent swallow.
    assert calls["finalize_recording"]["consultation_id"] == "c1"
    assert calls["end_consult"] == {"consultation_id": "c1", "doctor_id": "doctor-1"}
    assert calls["run_batch_retranscription"] == "c1"


# ── Auth rejection ───────────────────────────────────────────────────────────

def test_consult_audio_ws_rejects_deactivated_doctor_at_connect(monkeypatch):
    """_authenticate_doctor_from_token delegates to get_doctor_profile, which (per
    app/services/doctor_auth.py: `if not row or not row[8] or not row[4]: return None`,
    row[8]=account.is_active, row[4]=doctor.is_active) returns None for a deactivated
    doctor OR deactivated account. Confirms the WS handler treats that identically to a
    missing/invalid token: an error message, close(code=1008), and it never reaches
    begin_recording (i.e. never opens the Deepgram connection or starts a recording for
    a doctor who shouldn't be authenticated at all)."""
    monkeypatch.setattr(consult_route, "DEEPGRAM_API_KEY", "fake-dg-key")
    monkeypatch.setattr(
        consult_route, "verify_access_token",
        lambda token: {
            "role": "doctor", "token_kind": "doctor_session",
            "sub": "doctor-1", "doctor_id": "doctor-1", "account_id": "account-1",
        },
    )
    # Deactivated doctor/account -> get_doctor_profile returns None.
    monkeypatch.setattr(consult_route, "get_doctor_profile", lambda doctor_id, account_id: None)

    begin_recording_called = {"value": False}
    monkeypatch.setattr(
        consult_route, "begin_recording",
        lambda *a, **k: begin_recording_called.__setitem__("value", True),
    )

    ws = FakeClientWebSocket(query_params={"token": "some-token"}, incoming=[])
    asyncio.run(consult_route.consult_audio_ws(ws, "c1"))

    assert ws.accepted is True
    assert ws.sent_json == [{"type": "error", "message": "Doctor authentication is required."}]
    assert ws.close_calls == [1008]
    assert begin_recording_called["value"] is False


# ── Sample-rate boundary validation ─────────────────────────────────────────

def test_consult_audio_ws_rejects_sample_rate_just_below_valid_range(monkeypatch):
    """_parse_sample_rate's accepted range is [8000, 192000] (see its own docstring:
    8kHz telephone-quality through 192kHz professional audio). 7999 is one below the
    floor -> the WS handler must reject at connect time before ever calling
    begin_recording or opening the Deepgram connection."""
    _wire_auth_and_consult(monkeypatch)
    begin_recording_called = {"value": False}
    monkeypatch.setattr(
        consult_route, "begin_recording",
        lambda *a, **k: begin_recording_called.__setitem__("value", True),
    )

    ws = FakeClientWebSocket(query_params={"token": "tok", "sample_rate": "7999"}, incoming=[])
    asyncio.run(consult_route.consult_audio_ws(ws, "c1"))

    assert ws.sent_json == [{"type": "error", "message": "Invalid sample_rate."}]
    assert ws.close_calls == [1008]
    assert begin_recording_called["value"] is False


def test_consult_audio_ws_rejects_sample_rate_just_above_valid_range(monkeypatch):
    """192001 is one above the ceiling -> same rejection as just below the floor."""
    _wire_auth_and_consult(monkeypatch)
    begin_recording_called = {"value": False}
    monkeypatch.setattr(
        consult_route, "begin_recording",
        lambda *a, **k: begin_recording_called.__setitem__("value", True),
    )

    ws = FakeClientWebSocket(query_params={"token": "tok", "sample_rate": "192001"}, incoming=[])
    asyncio.run(consult_route.consult_audio_ws(ws, "c1"))

    assert ws.sent_json == [{"type": "error", "message": "Invalid sample_rate."}]
    assert ws.close_calls == [1008]
    assert begin_recording_called["value"] is False


def test_consult_audio_ws_accepts_sample_rate_at_lower_boundary(monkeypatch):
    """8000 (the floor, inclusive) must be accepted and passed through to
    begin_recording as an int, not rejected."""
    _wire_auth_and_consult(monkeypatch)
    calls = _wire_recording_plumbing(monkeypatch)
    monkeypatch.setattr(consult_route, "append_transcript_segment", lambda cid, **seg: None)

    fake_dg_ws = FakeDeepgramWS()
    monkeypatch.setattr(consult_route.websockets, "connect", lambda *a, **k: FakeDeepgramConnect(fake_dg_ws))

    ws = FakeClientWebSocket(query_params={"token": "tok", "sample_rate": "8000"}, incoming=[])
    asyncio.run(_run_ws_and_flush(ws, "c1"))

    assert calls["begin_recording"]["sample_rate"] == 8000
    assert ws.sent_json == []  # never hit the "Invalid sample_rate." branch


def test_consult_audio_ws_accepts_sample_rate_at_upper_boundary(monkeypatch):
    """192000 (the ceiling, inclusive) must likewise be accepted."""
    _wire_auth_and_consult(monkeypatch)
    calls = _wire_recording_plumbing(monkeypatch)
    monkeypatch.setattr(consult_route, "append_transcript_segment", lambda cid, **seg: None)

    fake_dg_ws = FakeDeepgramWS()
    monkeypatch.setattr(consult_route.websockets, "connect", lambda *a, **k: FakeDeepgramConnect(fake_dg_ws))

    ws = FakeClientWebSocket(query_params={"token": "tok", "sample_rate": "192000"}, incoming=[])
    asyncio.run(_run_ws_and_flush(ws, "c1"))

    assert calls["begin_recording"]["sample_rate"] == 192000
    assert ws.sent_json == []


# ── Empty/silent audio -> live_fallback (DB-backed) ─────────────────────────

def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _make_doctor(cur, name):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
        (name, "Testing", 1),
    )
    return str(cur.fetchone()[0])


def _make_booking(cur, doctor_id, patient_id="patient-x", offset_hours=1):
    from datetime import datetime, timedelta

    start_time = datetime.now() + timedelta(hours=offset_hours)
    end_time = start_time + timedelta(minutes=30)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked)
           VALUES (%s, %s, %s, TRUE) RETURNING slot_id""",
        (doctor_id, start_time, end_time),
    )
    slot_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, 'booked') RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start_time, end_time),
    )
    return str(cur.fetchone()[0])


def _cleanup(doctor_ids):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for doctor_id in doctor_ids:
                if doctor_id:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        conn.commit()


def test_run_batch_retranscription_falls_back_when_batch_returns_zero_segments(monkeypatch):
    """Empty/silent audio: a real Deepgram prerecorded response for silence/near-silence
    is well-formed but carries zero words, so _parse_prerecorded_segments legitimately
    returns []. Reading _run_batch_retranscription_locked directly confirms the current,
    explicit handling: `if not segments: raise RuntimeError("Batch re-transcription
    returned no segments.")`, caught by the same except block as every other failure mode
    and turned into the live_fallback path (status='transcript_ready',
    transcript_source='live_fallback', transcript_fallback_error=<message>) — NOT left
    stuck at 'transcribing' forever. Since no audio was ever live-streamed in this
    scenario either, the resulting "fallback" transcript is legitimately empty too."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Silent Audio")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id, sample_rate=48000)
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE consultations SET audio_blob_path = %s WHERE id = %s",
                    (f"consult-audio/{doctor_id}/{consult['id']}.pcm", consult["id"]),
                )
            conn.commit()

        async def fake_download_audio(path):
            return b"near-silent-audio-bytes"

        async def fake_transcribe(audio_bytes, *, department, sample_rate):
            return []  # Deepgram found nothing worth transcribing

        monkeypatch.setattr("app.services.audio_storage.download_audio", fake_download_audio)
        monkeypatch.setattr(consults_module, "_deepgram_prerecorded_transcribe", fake_transcribe)

        asyncio.run(run_batch_retranscription(consult["id"]))

        transcript = get_transcript(consult["id"], doctor_id)
        assert transcript["status"] == "transcript_ready"
        assert transcript["transcript_source"] == "live_fallback"
        assert "no segments" in transcript["transcript_fallback_error"].lower()
        assert transcript["segments"] == []
    finally:
        _cleanup([doctor_id])
