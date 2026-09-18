"""New end-to-end / service-layer tests for SOAP note generation, editing, signing and
addenda (app/services/soap_notes.py), covering gaps NOT already exercised by
test_soap_notes_integration.py — that file was read in full first; it already covers
generate/update/sign/addendum status transitions and ownership scoping individually
against seeded fixtures. This file adds:

- A single continuous generate -> edit -> sign happy path via direct service calls
  (the existing file tests each transition in isolation, never chained end-to-end).
- The exact precondition that blocks signing a note with no real transcript content:
  confirmed by reading generate_soap_note/sign_soap_note directly that sign_soap_note
  itself only ever re-checks `status == 'draft'` — it never looks at the transcript
  again. The real guarantee lives entirely in generate_soap_note, which is the only
  function that ever creates a 'draft' row, and explicitly raises ValueError when the
  fetched segments list is empty. The existing test_generate_rejects_when_transcript_not_ready
  only covers the *wrong status* case; this file adds the distinct *right status
  (transcript_ready), zero segments* edge case.
- Addendum-after-sign exercised through a real generate->sign pipeline (not a seeded
  soap_notes row), confirming add_addendum succeeds while a direct field edit is
  rejected, on a note the service layer actually produced itself.
- A characterization test for FULL_SYSTEM_AUDIT.md finding #124 ("A SOAP note can be
  signed completely blank") — verified for real against a live database below, not
  assumed from reading the code alone.

Same convention as test_soap_notes_integration.py: hits a real Postgres via connect_db()
and skips cleanly if unreachable.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.consults import begin_recording, record_consent, start_consult
from app.services.soap_notes import (
    add_addendum,
    ensure_soap_schema,
    generate_soap_note,
    get_soap_note,
    sign_soap_note,
    update_soap_note,
)


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


def _seed_consult_with_final_segments(doctor_id, segments, patient_id="patient-x"):
    with connect_db() as conn:
        with conn.cursor() as cur:
            booking_id = _make_booking(cur, doctor_id, patient_id=patient_id)
        conn.commit()

    consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
    record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
    begin_recording(consult["id"], doctor_id, sample_rate=48000)

    with connect_db() as conn:
        with conn.cursor() as cur:
            for speaker, start_ms, end_ms, text in segments:
                cur.execute(
                    """INSERT INTO transcript_segments
                       (consultation_id, speaker, start_ms, end_ms, text, is_final)
                       VALUES (%s, %s, %s, %s, %s, TRUE)""",
                    (consult["id"], speaker, start_ms, end_ms, text),
                )
            cur.execute(
                "UPDATE consultations SET status = 'transcript_ready', transcript_source = 'batch' WHERE id = %s",
                (consult["id"],),
            )
        conn.commit()

    return consult


def _seed_blank_soap_note(doctor_id, consultation_id, status="draft", patient_id="patient-x"):
    """Directly inserts a soap_notes row with all four content fields as empty strings —
    bypasses generate_soap_note/the LLM entirely, since we're pinning sign_soap_note's own
    behavior in isolation, not the (already-mocked-elsewhere) generation pipeline."""
    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO soap_notes
                   (consultation_id, doctor_id, patient_id, subjective, objective, assessment, plan, status)
                   VALUES (%s, %s, %s, '', '', '', '', %s) RETURNING id""",
                (consultation_id, doctor_id, patient_id, status),
            )
            note_id = str(cur.fetchone()[0])
        conn.commit()
    return note_id


def _cleanup(doctor_ids):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for doctor_id in doctor_ids:
                if doctor_id:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        conn.commit()


def _canned_note(subjective="Patient reports headache.", suffix=""):
    return {
        "subjective": subjective + suffix,
        "objective": "BP 120/80." + suffix,
        "assessment": "Tension headache." + suffix,
        "plan": "Rest and hydrate." + suffix,
        "field_citations": {"subjective": ["s1"], "objective": ["s1"], "assessment": ["s1"], "plan": ["s1"]},
        "confidence_flags": {"subjective": False, "objective": False, "assessment": False, "plan": False},
    }


def _mock_llm(monkeypatch, payload):
    async def fake_agenerate_soap_note(consultation_id, patient_id, segments):
        return payload

    import app.agents.consult_documentation_graph as docgraph
    monkeypatch.setattr(docgraph, "agenerate_soap_note", fake_agenerate_soap_note)


# ── Full generate -> edit -> sign happy path ────────────────────────────────

def test_generate_edit_sign_full_happy_path_via_direct_service_calls(monkeypatch):
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Full Flow")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [
            ("patient", 0, 1000, "I have had a headache for two days."),
            ("doctor", 1000, 3000, "Any nausea or visual changes?"),
        ])
        _mock_llm(monkeypatch, _canned_note())

        generated = asyncio.run(generate_soap_note(consult["id"], doctor_id))
        assert generated["status"] == "draft"
        assert generated["signed_at"] is None
        assert generated["subjective"] == "Patient reports headache."

        edited = update_soap_note(consult["id"], doctor_id, {
            "assessment": "Tension-type headache, no red flags.",
        })
        assert edited["status"] == "draft"
        assert edited["assessment"] == "Tension-type headache, no red flags."
        assert edited["edited_at"] is not None
        # Fields not touched by the edit must survive untouched.
        assert edited["subjective"] == "Patient reports headache."

        signed = sign_soap_note(consult["id"], doctor_id)
        assert signed["status"] == "signed"
        assert signed["signed_by"] == doctor_id
        assert signed["signed_at"] is not None
        assert signed["assessment"] == "Tension-type headache, no red flags."

        # The pipeline ends in the same immutability guarantee already unit-tested
        # against a seeded note in test_soap_notes_integration.py — confirming it holds
        # end-to-end, not just against a hand-inserted fixture.
        with pytest.raises(PermissionError):
            update_soap_note(consult["id"], doctor_id, {"plan": "should not stick"})

        fetched = get_soap_note(consult["id"], doctor_id)
        assert fetched["status"] == "signed"
        assert fetched["plan"] == "Rest and hydrate."
    finally:
        _cleanup([doctor_id])


# ── Signing requires real transcript content ────────────────────────────────

def test_generate_soap_note_rejected_when_transcript_ready_but_zero_segments_exist():
    """A note can never be signed without transcript content, because it can never even
    be *created* without it: generate_soap_note fetches segments via get_transcript() and
    raises ValueError("There is no transcript to generate a note from.") when that list is
    empty — even when consult['status'] == 'transcript_ready' (the status check alone
    passes; it's the actual segment count that blocks it here). This is the distinct edge
    case from test_generate_rejects_when_transcript_not_ready (which covers status !=
    'transcript_ready'): a consult that legitimately reached transcript_ready with no
    transcribable content at all, e.g. a live_fallback pass that itself produced zero
    segments (see test_run_batch_retranscription_falls_back_when_batch_returns_zero_segments
    in test_consult_audio_ws_e2e.py)."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Zero Segments")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id, sample_rate=48000)

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE consultations SET status = 'transcript_ready', transcript_source = 'batch' WHERE id = %s",
                    (consult["id"],),
                )
            conn.commit()

        with pytest.raises(ValueError, match="no transcript"):
            asyncio.run(generate_soap_note(consult["id"], doctor_id))

        # No note was ever created, so there's nothing a doctor could sign.
        assert get_soap_note(consult["id"], doctor_id) is None
    finally:
        _cleanup([doctor_id])


# ── Addendum-after-sign via a real generate->sign pipeline ──────────────────

def test_addendum_succeeds_after_real_generate_and_sign_flow_while_direct_edit_still_rejected(monkeypatch):
    """Differs from test_addendum_rejected_before_signed_and_allowed_after in
    test_soap_notes_integration.py, which seeds a soap_notes row directly via raw SQL:
    this exercises the actual generate_soap_note -> sign_soap_note pipeline first, so the
    note being amended is one the service layer produced and signed itself end-to-end,
    then confirms add_addendum is exposed correctly (succeeds, is appended, is visible on
    the next GET) while update_soap_note is still rejected for direct field edits."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Real Addendum Flow")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _mock_llm(monkeypatch, _canned_note())
        asyncio.run(generate_soap_note(consult["id"], doctor_id))
        sign_soap_note(consult["id"], doctor_id)

        note = add_addendum(consult["id"], doctor_id, "Patient called back, symptoms resolved.")
        assert note["status"] == "signed"
        assert note["addenda"][-1]["content"] == "Patient called back, symptoms resolved."
        assert note["addenda"][-1]["added_by"] == doctor_id
        # The originally-signed fields are untouched by the addendum.
        assert note["subjective"] == "Patient reports headache."

        # Addendum is visible on a fresh GET too, not just the mutating call's return value.
        fetched = get_soap_note(consult["id"], doctor_id)
        assert len(fetched["addenda"]) == 1

        with pytest.raises(PermissionError):
            update_soap_note(consult["id"], doctor_id, {"subjective": "direct edit after sign"})
    finally:
        _cleanup([doctor_id])


# ── Characterization test: blank-note signing (FULL_SYSTEM_AUDIT.md #124) ──

# CHARACTERIZATION TEST — this pins TODAY's actual (buggy) behavior, it does not assert
# desired behavior. Confirmed both by direct reading of sign_soap_note
# (app/services/soap_notes.py:338-378 — its UPDATE's WHERE clause only ever checks
# `status = 'draft'`, with no check that subjective/objective/assessment/plan contain any
# text) AND empirically by actually running this test against a real database (see the
# task report — do not trust the source-reading alone). This matches
# FULL_SYSTEM_AUDIT.md's documented finding #124: "A SOAP note can be signed completely
# blank." If that gap is ever fixed (e.g. sign_soap_note starts rejecting all-blank
# content), THIS TEST MUST BE INVERTED to assert a ValueError/PermissionError is raised
# instead of asserting success.
def test_sign_soap_note_currently_allows_blank_content_characterization():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Blank Note Sign")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _seed_blank_soap_note(doctor_id, consult["id"], status="draft")

        note = sign_soap_note(consult["id"], doctor_id)

        assert note["status"] == "signed"
        assert note["subjective"] == ""
        assert note["objective"] == ""
        assert note["assessment"] == ""
        assert note["plan"] == ""
        assert note["signed_at"] is not None
        assert note["signed_by"] == doctor_id
    finally:
        _cleanup([doctor_id])
