"""Consult route-level access control and wiring tests (Part 2).

Same convention as test_doctor_appointments.py: call route functions directly (no
TestClient), monkeypatch the service layer, and prove the route only ever passes the
*authenticated* doctor's own doctor_id through — never a client-supplied one.
"""

import asyncio

from fastapi import HTTPException
import pytest

from app.api.routes import consult as consult_route


def _doctor(doctor_id="doctor-1", account_id="account-1", department="Cardiology"):
    return {"doctor_id": doctor_id, "account_id": account_id, "department": department}


# ── POST /start ──────────────────────────────────────────────────────────────

def test_start_route_passes_authenticated_doctor_id_only(monkeypatch):
    seen = {}

    def fake_start_consult(*, doctor_id, booking_id):
        seen["doctor_id"] = doctor_id
        seen["booking_id"] = booking_id
        return {"id": "c1", "status": "not_started"}

    monkeypatch.setattr(consult_route, "start_consult", fake_start_consult)

    request = consult_route.StartConsultRequest(booking_id="b1")
    result = consult_route.start_consult_route(request, doctor=_doctor("doctor-1"))

    assert seen["doctor_id"] == "doctor-1"
    assert seen["booking_id"] == "b1"
    assert result["status"] == "not_started"


def test_start_route_maps_value_error_to_404(monkeypatch):
    monkeypatch.setattr(
        consult_route, "start_consult",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("Booking not found.")),
    )
    request = consult_route.StartConsultRequest(booking_id="missing")
    with pytest.raises(HTTPException) as exc:
        consult_route.start_consult_route(request, doctor=_doctor())
    assert exc.value.status_code == 404


def test_start_route_maps_permission_error_to_409(monkeypatch):
    monkeypatch.setattr(
        consult_route, "start_consult",
        lambda **kwargs: (_ for _ in ()).throw(PermissionError("A consult already exists for this booking.")),
    )
    request = consult_route.StartConsultRequest(booking_id="b1")
    with pytest.raises(HTTPException) as exc:
        consult_route.start_consult_route(request, doctor=_doctor())
    assert exc.value.status_code == 409


# ── POST /{id}/consent ───────────────────────────────────────────────────────

def test_consent_route_passes_authenticated_doctor_and_account_id(monkeypatch):
    seen = {}

    def fake_record_consent(consultation_id, doctor_id, *, account_id):
        seen["consultation_id"] = consultation_id
        seen["doctor_id"] = doctor_id
        seen["account_id"] = account_id
        return {"id": consultation_id, "status": "consented"}

    monkeypatch.setattr(consult_route, "record_consent", fake_record_consent)

    result = consult_route.consent_route("c1", doctor=_doctor("doctor-1", "account-9"))

    assert seen == {"consultation_id": "c1", "doctor_id": "doctor-1", "account_id": "account-9"}
    assert result["status"] == "consented"


def test_consent_route_404_when_consult_not_found(monkeypatch):
    monkeypatch.setattr(
        consult_route, "record_consent",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("Consult not found.")),
    )
    with pytest.raises(HTTPException) as exc:
        consult_route.consent_route("missing", doctor=_doctor())
    assert exc.value.status_code == 404


def test_consent_route_400_on_bad_state_transition(monkeypatch):
    monkeypatch.setattr(
        consult_route, "record_consent",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("Cannot record consent for a consult in status 'ended'.")),
    )
    with pytest.raises(HTTPException) as exc:
        consult_route.consent_route("c1", doctor=_doctor())
    assert exc.value.status_code == 400


# ── POST /{id}/end ───────────────────────────────────────────────────────────

def test_end_route_schedules_retranscription_only_when_transitioned_to_ended(monkeypatch):
    scheduled = {}

    async def fake_retranscribe(consultation_id):
        scheduled["consultation_id"] = consultation_id

    monkeypatch.setattr(consult_route, "end_consult", lambda cid, doctor_id: {"id": cid, "status": "ended"})
    monkeypatch.setattr(consult_route, "run_batch_retranscription", fake_retranscribe)

    async def run():
        result = await consult_route.end_consult_route("c1", doctor=_doctor("doctor-1"))
        await asyncio.sleep(0)  # let the scheduled background task actually execute
        return result

    result = asyncio.run(run())
    assert result["status"] == "ended"
    assert scheduled["consultation_id"] == "c1"


def test_end_route_does_not_reschedule_when_already_ended(monkeypatch):
    """Idempotent end_consult() returns the existing state unchanged when called on an
    already-'transcript_ready' consult — the route must not kick off a second
    re-transcription pass in that case."""
    scheduled = {"called": False}

    async def fake_retranscribe(consultation_id):
        scheduled["called"] = True

    monkeypatch.setattr(
        consult_route, "end_consult",
        lambda cid, doctor_id: {"id": cid, "status": "transcript_ready"},
    )
    monkeypatch.setattr(consult_route, "run_batch_retranscription", fake_retranscribe)

    async def run():
        result = await consult_route.end_consult_route("c1", doctor=_doctor())
        await asyncio.sleep(0)
        return result

    result = asyncio.run(run())
    assert result["status"] == "transcript_ready"
    assert scheduled["called"] is False


def test_end_route_404_when_consult_not_found(monkeypatch):
    monkeypatch.setattr(
        consult_route, "end_consult",
        lambda cid, doctor_id: (_ for _ in ()).throw(ValueError("Consult not found.")),
    )

    async def run():
        return await consult_route.end_consult_route("missing", doctor=_doctor())

    with pytest.raises(HTTPException) as exc:
        asyncio.run(run())
    assert exc.value.status_code == 404


# ── POST /{id}/discard ───────────────────────────────────────────────────────

def test_discard_route_deletes_blob_when_present(monkeypatch):
    deleted = {}

    async def fake_delete_audio(blob_path):
        deleted["blob_path"] = blob_path

    monkeypatch.setattr(
        consult_route, "discard_consult",
        lambda cid, doctor_id: {"row": {"id": cid, "status": "discarded"}, "audio_blob_path": "consult-audio/d1/c1.pcm"},
    )
    monkeypatch.setattr("app.services.audio_storage.delete_audio", fake_delete_audio)

    async def run():
        return await consult_route.discard_consult_route("c1", doctor=_doctor("doctor-1"))

    result = asyncio.run(run())
    assert result["status"] == "discarded"
    assert deleted["blob_path"] == "consult-audio/d1/c1.pcm"


def test_discard_route_skips_blob_delete_when_no_audio(monkeypatch):
    called = {"count": 0}

    async def fake_delete_audio(blob_path):
        called["count"] += 1

    monkeypatch.setattr(
        consult_route, "discard_consult",
        lambda cid, doctor_id: {"row": {"id": cid, "status": "discarded"}, "audio_blob_path": None},
    )
    monkeypatch.setattr("app.services.audio_storage.delete_audio", fake_delete_audio)

    async def run():
        return await consult_route.discard_consult_route("c1", doctor=_doctor())

    asyncio.run(run())
    assert called["count"] == 0


def test_discard_route_404_when_not_found(monkeypatch):
    monkeypatch.setattr(
        consult_route, "discard_consult",
        lambda cid, doctor_id: (_ for _ in ()).throw(ValueError("Consult not found.")),
    )

    async def run():
        return await consult_route.discard_consult_route("missing", doctor=_doctor())

    with pytest.raises(HTTPException) as exc:
        asyncio.run(run())
    assert exc.value.status_code == 404


# ── GET /{id}/transcript ─────────────────────────────────────────────────────

def test_transcript_route_passes_authenticated_doctor_id_only(monkeypatch):
    seen = {}

    def fake_get_transcript(consultation_id, doctor_id):
        seen["consultation_id"] = consultation_id
        seen["doctor_id"] = doctor_id
        return {"status": "transcript_ready", "segments": []}

    monkeypatch.setattr(consult_route, "get_transcript", fake_get_transcript)

    result = consult_route.transcript_route("c1", doctor=_doctor("doctor-1"))

    assert seen == {"consultation_id": "c1", "doctor_id": "doctor-1"}
    assert result["status"] == "transcript_ready"


def test_transcript_route_404_when_owner_mismatch_or_missing(monkeypatch):
    """get_transcript returning None must mean 404 regardless of whether the id is
    garbage or belongs to a different doctor — same 'never disambiguate' principle as
    Part 1's doctor_patient_detail."""
    monkeypatch.setattr(consult_route, "get_transcript", lambda cid, doctor_id: None)
    with pytest.raises(HTTPException) as exc:
        consult_route.transcript_route("someone-elses-consult", doctor=_doctor())
    assert exc.value.status_code == 404


# ── WebSocket auth helper ────────────────────────────────────────────────────

def test_authenticate_doctor_from_token_rejects_missing_token():
    assert consult_route._authenticate_doctor_from_token(None) is None


def test_authenticate_doctor_from_token_rejects_wrong_token_kind(monkeypatch):
    monkeypatch.setattr(
        consult_route, "verify_access_token",
        lambda token: {"role": "doctor", "token_kind": "doctor_mfa_pending", "sub": "d1", "doctor_id": "d1"},
    )
    assert consult_route._authenticate_doctor_from_token("some-token") is None


def test_authenticate_doctor_from_token_rejects_patient_role(monkeypatch):
    monkeypatch.setattr(
        consult_route, "verify_access_token",
        lambda token: {"role": "patient", "token_kind": "doctor_session", "sub": "d1", "doctor_id": "d1"},
    )
    assert consult_route._authenticate_doctor_from_token("some-token") is None


def test_authenticate_doctor_from_token_accepts_valid_doctor_session(monkeypatch):
    monkeypatch.setattr(
        consult_route, "verify_access_token",
        lambda token: {
            "role": "doctor", "token_kind": "doctor_session", "sub": "d1",
            "doctor_id": "d1", "account_id": "a1",
        },
    )
    monkeypatch.setattr(
        consult_route, "get_doctor_profile",
        lambda doctor_id, account_id: {"doctor_id": doctor_id, "account_id": account_id, "department": "Cardiology"},
    )
    profile = consult_route._authenticate_doctor_from_token("some-token")
    assert profile == {"doctor_id": "d1", "account_id": "a1", "department": "Cardiology"}


# ── _should_schedule_retranscription ─────────────────────────────────────────
# Shared by end_consult_route and consult_audio_ws's finally block — covers the
# recovery scenario: a WS handler that was genuinely still hung (not just
# disconnected) finalizes real audio *after* a doctor already manually ended an
# "orphaned" session (or the stale-recording sweep force-ended it) via the plain
# HTTP route, with no real audio yet at that point.

def test_schedules_when_end_consult_just_transitioned_to_ended():
    assert consult_route._should_schedule_retranscription("ended", storage_ref=None) is True


def test_does_not_schedule_when_already_ended_and_no_new_audio():
    """The normal 'nothing to do' case — e.g. a doctor double-clicks End."""
    assert consult_route._should_schedule_retranscription("transcript_ready", storage_ref=None) is False


def test_schedules_when_real_audio_just_became_available_even_if_already_marked_done():
    """The recovery scenario itself: end_consult() was a no-op (status stayed
    'transcript_ready', already force-ended by someone else) but this call just
    finalized a real recording — must still (re-)schedule, or that audio is never
    processed and the transcript stays stuck at its live-only fallback forever."""
    assert consult_route._should_schedule_retranscription("transcript_ready", storage_ref="consult-audio/d1/c1.pcm") is True


def test_schedules_only_once_when_both_conditions_are_true():
    """Just confirms the OR doesn't do anything surprising when both the transition
    AND fresh audio happen together (the common, normal end-of-recording case)."""
    assert consult_route._should_schedule_retranscription("ended", storage_ref="consult-audio/d1/c1.pcm") is True


def test_end_route_passes_no_storage_ref_since_the_http_route_never_finalizes_audio(monkeypatch):
    """end_consult_route has no temp file to finalize (only the WS handler does) — pins
    down that it always calls the shared helper with storage_ref=None."""
    seen = {}
    monkeypatch.setattr(consult_route, "end_consult", lambda cid, doctor_id: {"id": cid, "status": "ended"})

    def fake_should_schedule(status, storage_ref):
        seen["status"] = status
        seen["storage_ref"] = storage_ref
        return True

    monkeypatch.setattr(consult_route, "_should_schedule_retranscription", fake_should_schedule)

    async def fake_retranscribe(cid):
        pass

    monkeypatch.setattr(consult_route, "run_batch_retranscription", fake_retranscribe)

    async def run():
        result = await consult_route.end_consult_route("c1", doctor=_doctor())
        await asyncio.sleep(0)
        return result

    asyncio.run(run())
    assert seen == {"status": "ended", "storage_ref": None}


# ── _parse_sample_rate ───────────────────────────────────────────────────────

def test_parse_sample_rate_accepts_typical_browser_rates():
    assert consult_route._parse_sample_rate("48000") == 48000
    assert consult_route._parse_sample_rate("44100") == 44100
    assert consult_route._parse_sample_rate("16000") == 16000


def test_parse_sample_rate_rejects_non_numeric():
    assert consult_route._parse_sample_rate("not-a-number") is None
    assert consult_route._parse_sample_rate(None) is None
    assert consult_route._parse_sample_rate("") is None


def test_parse_sample_rate_rejects_out_of_range_values():
    """Catches garbage/spoofed values — not a real cross-check against the audio
    itself (see _parse_sample_rate's docstring for that limitation)."""
    assert consult_route._parse_sample_rate("0") is None
    assert consult_route._parse_sample_rate("-16000") is None
    assert consult_route._parse_sample_rate("999999999") is None
    assert consult_route._parse_sample_rate("1") is None


def test_parse_sample_rate_accepts_boundary_values():
    assert consult_route._parse_sample_rate("8000") == 8000
    assert consult_route._parse_sample_rate("192000") == 192000
    assert consult_route._parse_sample_rate("7999") is None
    assert consult_route._parse_sample_rate("192001") is None


# ── POST /{id}/transcript/swap-speakers ──────────────────────────────────────

def test_swap_speakers_route_passes_authenticated_doctor_id_only(monkeypatch):
    seen = {}

    def fake_swap(consultation_id, doctor_id):
        seen["consultation_id"] = consultation_id
        seen["doctor_id"] = doctor_id
        return {"swapped_segments": 4, "note_marked_stale": False}

    monkeypatch.setattr(consult_route, "swap_all_speakers", fake_swap)

    result = consult_route.swap_speakers_route("c1", doctor=_doctor("doctor-1"))

    assert seen == {"consultation_id": "c1", "doctor_id": "doctor-1"}
    assert result == {"swapped_segments": 4, "note_marked_stale": False}


def test_swap_speakers_route_404_when_consult_not_found(monkeypatch):
    monkeypatch.setattr(
        consult_route, "swap_all_speakers",
        lambda cid, doctor_id: (_ for _ in ()).throw(ValueError("Consult not found.")),
    )
    with pytest.raises(HTTPException) as exc:
        consult_route.swap_speakers_route("missing", doctor=_doctor())
    assert exc.value.status_code == 404


def test_swap_speakers_route_409_when_note_already_signed(monkeypatch):
    monkeypatch.setattr(
        consult_route, "swap_all_speakers",
        lambda cid, doctor_id: (_ for _ in ()).throw(PermissionError("Cannot correct speaker labels after the SOAP note has been signed.")),
    )
    with pytest.raises(HTTPException) as exc:
        consult_route.swap_speakers_route("c1", doctor=_doctor())
    assert exc.value.status_code == 409


# ── PATCH /{id}/transcript/segments/{segment_id} ─────────────────────────────

def test_correct_segment_route_passes_authenticated_doctor_id_only(monkeypatch):
    seen = {}

    def fake_correct(consultation_id, doctor_id, segment_id, speaker):
        seen["consultation_id"] = consultation_id
        seen["doctor_id"] = doctor_id
        seen["segment_id"] = segment_id
        seen["speaker"] = speaker
        return {"updated": True, "note_marked_stale": True}

    monkeypatch.setattr(consult_route, "correct_segment_speaker", fake_correct)

    request = consult_route.SegmentCorrectionRequest(speaker="patient")
    result = consult_route.correct_segment_route("c1", "seg1", request, doctor=_doctor("doctor-1"))

    assert seen == {"consultation_id": "c1", "doctor_id": "doctor-1", "segment_id": "seg1", "speaker": "patient"}
    assert result == {"updated": True, "note_marked_stale": True}


def test_correct_segment_route_404_when_consult_not_found(monkeypatch):
    monkeypatch.setattr(
        consult_route, "correct_segment_speaker",
        lambda cid, doctor_id, segment_id, speaker: (_ for _ in ()).throw(ValueError("Consult not found.")),
    )
    request = consult_route.SegmentCorrectionRequest(speaker="doctor")
    with pytest.raises(HTTPException) as exc:
        consult_route.correct_segment_route("missing", "seg1", request, doctor=_doctor())
    assert exc.value.status_code == 404


def test_correct_segment_route_404_when_segment_not_found(monkeypatch):
    monkeypatch.setattr(
        consult_route, "correct_segment_speaker",
        lambda cid, doctor_id, segment_id, speaker: (_ for _ in ()).throw(ValueError("Transcript segment not found.")),
    )
    request = consult_route.SegmentCorrectionRequest(speaker="doctor")
    with pytest.raises(HTTPException) as exc:
        consult_route.correct_segment_route("c1", "missing-seg", request, doctor=_doctor())
    assert exc.value.status_code == 404


def test_correct_segment_route_400_on_invalid_speaker(monkeypatch):
    monkeypatch.setattr(
        consult_route, "correct_segment_speaker",
        lambda cid, doctor_id, segment_id, speaker: (_ for _ in ()).throw(ValueError("speaker must be one of ('doctor', 'patient', 'unknown').")),
    )
    request = consult_route.SegmentCorrectionRequest(speaker="bogus")
    with pytest.raises(HTTPException) as exc:
        consult_route.correct_segment_route("c1", "seg1", request, doctor=_doctor())
    assert exc.value.status_code == 400


def test_correct_segment_route_409_when_note_already_signed(monkeypatch):
    monkeypatch.setattr(
        consult_route, "correct_segment_speaker",
        lambda cid, doctor_id, segment_id, speaker: (_ for _ in ()).throw(PermissionError("Cannot correct speaker labels after the SOAP note has been signed.")),
    )
    request = consult_route.SegmentCorrectionRequest(speaker="doctor")
    with pytest.raises(HTTPException) as exc:
        consult_route.correct_segment_route("c1", "seg1", request, doctor=_doctor())
    assert exc.value.status_code == 409


# ── POST /{id}/soap/generate ─────────────────────────────────────────────────

def test_generate_soap_note_route_passes_authenticated_doctor_id_only(monkeypatch):
    seen = {}

    async def fake_generate(consultation_id, doctor_id):
        seen["consultation_id"] = consultation_id
        seen["doctor_id"] = doctor_id
        return {"status": "draft"}

    monkeypatch.setattr(consult_route, "generate_soap_note", fake_generate)

    result = asyncio.run(consult_route.generate_soap_note_route("c1", doctor=_doctor("doctor-1")))

    assert seen == {"consultation_id": "c1", "doctor_id": "doctor-1"}
    assert result["status"] == "draft"


def test_generate_soap_note_route_404_when_consult_not_found(monkeypatch):
    async def fake_generate(consultation_id, doctor_id):
        raise ValueError("Consult not found.")

    monkeypatch.setattr(consult_route, "generate_soap_note", fake_generate)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(consult_route.generate_soap_note_route("missing", doctor=_doctor()))
    assert exc.value.status_code == 404


def test_generate_soap_note_route_400_when_transcript_not_ready(monkeypatch):
    async def fake_generate(consultation_id, doctor_id):
        raise ValueError("Transcript is not ready yet for this consult.")

    monkeypatch.setattr(consult_route, "generate_soap_note", fake_generate)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(consult_route.generate_soap_note_route("c1", doctor=_doctor()))
    assert exc.value.status_code == 400


def test_generate_soap_note_route_409_when_already_signed(monkeypatch):
    async def fake_generate(consultation_id, doctor_id):
        raise PermissionError("This clinical note has already been signed. Add an addendum instead of regenerating.")

    monkeypatch.setattr(consult_route, "generate_soap_note", fake_generate)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(consult_route.generate_soap_note_route("c1", doctor=_doctor()))
    assert exc.value.status_code == 409


def test_generate_soap_note_route_502_on_llm_parse_failure(monkeypatch):
    async def fake_generate(consultation_id, doctor_id):
        raise RuntimeError("Could not generate a structured clinical note from this transcript. Please try again.")

    monkeypatch.setattr(consult_route, "generate_soap_note", fake_generate)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(consult_route.generate_soap_note_route("c1", doctor=_doctor()))
    assert exc.value.status_code == 502


# ── GET /{id}/soap ────────────────────────────────────────────────────────────

def test_get_soap_note_route_passes_authenticated_doctor_id_only(monkeypatch):
    seen = {}

    def fake_get(consultation_id, doctor_id):
        seen["consultation_id"] = consultation_id
        seen["doctor_id"] = doctor_id
        return {"status": "draft"}

    monkeypatch.setattr(consult_route, "get_soap_note", fake_get)

    result = consult_route.get_soap_note_route("c1", doctor=_doctor("doctor-1"))

    assert seen == {"consultation_id": "c1", "doctor_id": "doctor-1"}
    assert result["status"] == "draft"


def test_get_soap_note_route_404_when_no_note(monkeypatch):
    monkeypatch.setattr(consult_route, "get_soap_note", lambda cid, doctor_id: None)

    with pytest.raises(HTTPException) as exc:
        consult_route.get_soap_note_route("c1", doctor=_doctor())
    assert exc.value.status_code == 404


# ── PATCH /{id}/soap ──────────────────────────────────────────────────────────

def test_update_soap_note_route_passes_authenticated_doctor_id_and_fields(monkeypatch):
    seen = {}

    def fake_update(consultation_id, doctor_id, fields):
        seen["consultation_id"] = consultation_id
        seen["doctor_id"] = doctor_id
        seen["fields"] = fields
        return {"status": "draft", "subjective": "edited"}

    monkeypatch.setattr(consult_route, "update_soap_note", fake_update)

    request = consult_route.SoapNoteUpdateRequest(subjective="edited")
    result = consult_route.update_soap_note_route("c1", request, doctor=_doctor("doctor-1"))

    assert seen["consultation_id"] == "c1"
    assert seen["doctor_id"] == "doctor-1"
    assert seen["fields"]["subjective"] == "edited"
    assert result["subjective"] == "edited"


def test_update_soap_note_route_409_when_already_signed(monkeypatch):
    monkeypatch.setattr(
        consult_route, "update_soap_note",
        lambda cid, doctor_id, fields: (_ for _ in ()).throw(
            PermissionError("This clinical note has already been signed and can no longer be edited.")
        ),
    )
    request = consult_route.SoapNoteUpdateRequest(subjective="edited")
    with pytest.raises(HTTPException) as exc:
        consult_route.update_soap_note_route("c1", request, doctor=_doctor())
    assert exc.value.status_code == 409


def test_update_soap_note_route_404_when_no_note_exists(monkeypatch):
    monkeypatch.setattr(
        consult_route, "update_soap_note",
        lambda cid, doctor_id, fields: (_ for _ in ()).throw(ValueError("No clinical note exists yet for this consult.")),
    )
    request = consult_route.SoapNoteUpdateRequest(subjective="edited")
    with pytest.raises(HTTPException) as exc:
        consult_route.update_soap_note_route("c1", request, doctor=_doctor())
    assert exc.value.status_code == 404


# ── POST /{id}/soap/sign ──────────────────────────────────────────────────────

def test_sign_soap_note_route_passes_authenticated_doctor_id_only(monkeypatch):
    seen = {}

    def fake_sign(consultation_id, doctor_id):
        seen["consultation_id"] = consultation_id
        seen["doctor_id"] = doctor_id
        return {"status": "signed"}

    monkeypatch.setattr(consult_route, "sign_soap_note", fake_sign)

    result = consult_route.sign_soap_note_route("c1", doctor=_doctor("doctor-1"))

    assert seen == {"consultation_id": "c1", "doctor_id": "doctor-1"}
    assert result["status"] == "signed"


def test_sign_soap_note_route_409_when_stale(monkeypatch):
    monkeypatch.setattr(
        consult_route, "sign_soap_note",
        lambda cid, doctor_id: (_ for _ in ()).throw(
            PermissionError("This clinical note is stale (transcript labels changed since it was generated). "
                             "Regenerate or edit it before signing.")
        ),
    )
    with pytest.raises(HTTPException) as exc:
        consult_route.sign_soap_note_route("c1", doctor=_doctor())
    assert exc.value.status_code == 409


def test_sign_soap_note_route_404_when_no_note_exists(monkeypatch):
    monkeypatch.setattr(
        consult_route, "sign_soap_note",
        lambda cid, doctor_id: (_ for _ in ()).throw(ValueError("No clinical note exists yet for this consult.")),
    )
    with pytest.raises(HTTPException) as exc:
        consult_route.sign_soap_note_route("c1", doctor=_doctor())
    assert exc.value.status_code == 404


# ── POST /{id}/soap/addendum ──────────────────────────────────────────────────

def test_add_addendum_route_passes_authenticated_doctor_id_and_content(monkeypatch):
    seen = {}

    def fake_add(consultation_id, doctor_id, content):
        seen["consultation_id"] = consultation_id
        seen["doctor_id"] = doctor_id
        seen["content"] = content
        return {"status": "signed", "addenda": [{"content": content}]}

    monkeypatch.setattr(consult_route, "add_addendum", fake_add)

    request = consult_route.AddendumRequest(content="Follow-up note")
    result = consult_route.add_addendum_route("c1", request, doctor=_doctor("doctor-1"))

    assert seen == {"consultation_id": "c1", "doctor_id": "doctor-1", "content": "Follow-up note"}
    assert result["addenda"][0]["content"] == "Follow-up note"


def test_add_addendum_route_409_when_note_not_signed_yet(monkeypatch):
    monkeypatch.setattr(
        consult_route, "add_addendum",
        lambda cid, doctor_id, content: (_ for _ in ()).throw(
            PermissionError("Addenda can only be added to a signed clinical note.")
        ),
    )
    request = consult_route.AddendumRequest(content="Follow-up note")
    with pytest.raises(HTTPException) as exc:
        consult_route.add_addendum_route("c1", request, doctor=_doctor())
    assert exc.value.status_code == 409


def test_add_addendum_route_404_when_no_note_exists(monkeypatch):
    monkeypatch.setattr(
        consult_route, "add_addendum",
        lambda cid, doctor_id, content: (_ for _ in ()).throw(ValueError("No clinical note exists yet for this consult.")),
    )
    request = consult_route.AddendumRequest(content="Follow-up note")
    with pytest.raises(HTTPException) as exc:
        consult_route.add_addendum_route("c1", request, doctor=_doctor())
    assert exc.value.status_code == 404
