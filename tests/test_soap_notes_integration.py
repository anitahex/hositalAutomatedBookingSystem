"""Integration coverage for Phase 3 Part 2 (SOAP note generation, edit, sign, addendum)
against a real database. The LLM call inside the subgraph is mocked — this file proves
the service-layer contract (status transitions, ownership scoping, signed-note
immutability enforced here and not just in the UI), not model output quality.

Skips (not fails) if no database is reachable.
"""
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


def _seed_soap_note(doctor_id, consultation_id, status="draft", patient_id="patient-x"):
    with connect_db() as conn:
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO soap_notes (consultation_id, doctor_id, patient_id, subjective, status)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (consultation_id, doctor_id, patient_id, "pre-existing text", status),
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


def test_generate_creates_draft_note_with_citations(monkeypatch):
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Generate Note")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [
            ("patient", 0, 1000, "I have a headache."),
        ])
        _mock_llm(monkeypatch, _canned_note())

        note = asyncio.run(generate_soap_note(consult["id"], doctor_id))

        assert note["status"] == "draft"
        assert note["subjective"] == "Patient reports headache."
        assert note["source_transcript_type"] == "batch"
        for field in ("subjective", "objective", "assessment", "plan"):
            assert note["field_citations"][field]

        fetched = get_soap_note(consult["id"], doctor_id)
        assert fetched["id"] == note["id"]
        assert fetched["source_transcript_type"] == "batch"
    finally:
        _cleanup([doctor_id])


def test_generate_records_live_fallback_transcript_source(monkeypatch):
    """A live_fallback consult (batch re-transcription failed, only the raw streaming
    transcript is available) must be visible to the doctor reviewing the generated note
    — this is lower-confidence, never proofread by the batch pass."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Live Fallback Note")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        record_consent(consult["id"], doctor_id, account_id="00000000-0000-0000-0000-000000000001")
        begin_recording(consult["id"], doctor_id, sample_rate=48000)

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO transcript_segments
                       (consultation_id, speaker, start_ms, end_ms, text, is_final)
                       VALUES (%s, 'doctor', 0, 1000, 'live only line', FALSE)""",
                    (consult["id"],),
                )
                cur.execute(
                    """UPDATE consultations
                       SET status = 'transcript_ready', transcript_source = 'live_fallback'
                       WHERE id = %s""",
                    (consult["id"],),
                )
            conn.commit()

        _mock_llm(monkeypatch, _canned_note())
        note = asyncio.run(generate_soap_note(consult["id"], doctor_id))

        assert note["source_transcript_type"] == "live_fallback"
        assert get_soap_note(consult["id"], doctor_id)["source_transcript_type"] == "live_fallback"
    finally:
        _cleanup([doctor_id])


def test_generate_rejects_when_transcript_not_ready(monkeypatch):
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Not Ready")
                booking_id = _make_booking(cur, doctor_id)
            conn.commit()

        consult = start_consult(doctor_id=doctor_id, booking_id=booking_id)
        _mock_llm(monkeypatch, _canned_note())

        with pytest.raises(ValueError):
            asyncio.run(generate_soap_note(consult["id"], doctor_id))
    finally:
        _cleanup([doctor_id])


def test_generate_silently_replaces_existing_draft(monkeypatch):
    """Decision (Part 2): a stale OR draft note is silently replaced at the service
    layer — any 'are you sure' confirmation is a UI-layer concern (Part 3), shown before
    this endpoint is ever called, not enforced here."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Replace Draft")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _seed_soap_note(doctor_id, consult["id"], status="draft")

        _mock_llm(monkeypatch, _canned_note(suffix=" v2"))
        note = asyncio.run(generate_soap_note(consult["id"], doctor_id))

        assert note["status"] == "draft"
        assert note["subjective"] == "Patient reports headache. v2"
    finally:
        _cleanup([doctor_id])


def test_generate_silently_replaces_stale_note(monkeypatch):
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Replace Stale")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _seed_soap_note(doctor_id, consult["id"], status="stale")

        _mock_llm(monkeypatch, _canned_note(suffix=" v2"))
        note = asyncio.run(generate_soap_note(consult["id"], doctor_id))

        assert note["status"] == "draft"
        assert note["subjective"] == "Patient reports headache. v2"
    finally:
        _cleanup([doctor_id])


def test_generate_rejected_once_signed_and_note_left_untouched(monkeypatch):
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Signed Blocks Generate")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _seed_soap_note(doctor_id, consult["id"], status="signed")

        _mock_llm(monkeypatch, _canned_note(suffix=" v2"))
        with pytest.raises(PermissionError):
            asyncio.run(generate_soap_note(consult["id"], doctor_id))

        fetched = get_soap_note(consult["id"], doctor_id)
        assert fetched["status"] == "signed"
        assert fetched["subjective"] == "pre-existing text"
    finally:
        _cleanup([doctor_id])


def test_update_soap_note_edits_fields_while_draft(monkeypatch):
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Edit Draft")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _mock_llm(monkeypatch, _canned_note())
        asyncio.run(generate_soap_note(consult["id"], doctor_id))

        note = update_soap_note(consult["id"], doctor_id, {"subjective": "doctor-edited text"})

        assert note["subjective"] == "doctor-edited text"
        assert note["edited_at"] is not None
        assert note["status"] == "draft"
    finally:
        _cleanup([doctor_id])


def test_update_soap_note_rejected_at_service_layer_once_signed():
    """Explicit security requirement: a PATCH attempt after signing must be rejected by
    the service layer itself, not merely discouraged by the UI."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Edit Signed Blocked")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _seed_soap_note(doctor_id, consult["id"], status="signed")

        with pytest.raises(PermissionError):
            update_soap_note(consult["id"], doctor_id, {"subjective": "should not stick"})

        fetched = get_soap_note(consult["id"], doctor_id)
        assert fetched["subjective"] == "pre-existing text"
    finally:
        _cleanup([doctor_id])


def test_sign_soap_note_transitions_status_and_sets_signed_by(monkeypatch):
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Sign Note")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _mock_llm(monkeypatch, _canned_note())
        asyncio.run(generate_soap_note(consult["id"], doctor_id))

        note = sign_soap_note(consult["id"], doctor_id)

        assert note["status"] == "signed"
        assert note["signed_by"] == doctor_id
        assert note["signed_at"] is not None
    finally:
        _cleanup([doctor_id])


def test_sign_soap_note_rejected_when_already_signed():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Double Sign")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _seed_soap_note(doctor_id, consult["id"], status="signed")

        with pytest.raises(PermissionError):
            sign_soap_note(consult["id"], doctor_id)
    finally:
        _cleanup([doctor_id])


def test_sign_soap_note_rejected_when_stale():
    """Staleness must be resolved (regenerate or edit) before a note can be signed —
    signing a stale note would immortalize a note that may cite now-corrected-away
    speaker attributions."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Sign Stale Blocked")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _seed_soap_note(doctor_id, consult["id"], status="stale")

        with pytest.raises(PermissionError):
            sign_soap_note(consult["id"], doctor_id)

        assert get_soap_note(consult["id"], doctor_id)["status"] == "stale"
    finally:
        _cleanup([doctor_id])


def test_addendum_rejected_before_signed_and_allowed_after():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Addendum Flow")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _seed_soap_note(doctor_id, consult["id"], status="draft")

        with pytest.raises(PermissionError):
            add_addendum(consult["id"], doctor_id, "too early")

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE soap_notes SET status = 'signed' WHERE consultation_id = %s", (consult["id"],))
            conn.commit()

        note = add_addendum(consult["id"], doctor_id, "Follow-up: patient improved.")
        assert note["status"] == "signed"
        assert note["addenda"][-1]["content"] == "Follow-up: patient improved."
        assert note["addenda"][-1]["added_by"] == doctor_id
        # The signed fields themselves are untouched by an addendum.
        assert note["subjective"] == "pre-existing text"
    finally:
        _cleanup([doctor_id])


def test_addendum_rejects_empty_content():
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Empty Addendum")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_id, [("patient", 0, 1000, "line one")])
        _seed_soap_note(doctor_id, consult["id"], status="signed")

        with pytest.raises(ValueError):
            add_addendum(consult["id"], doctor_id, "   ")
    finally:
        _cleanup([doctor_id])


def test_doctor_cannot_generate_sign_or_edit_another_doctors_consult(monkeypatch):
    """Explicit security requirement: a doctor can only generate/edit/sign a note for a
    consultation they own."""
    _skip_if_no_database()

    doctor_a = doctor_b = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_a = _make_doctor(cur, "Dr. A Owns Consult")
                doctor_b = _make_doctor(cur, "Dr. B Intruder")
            conn.commit()

        consult = _seed_consult_with_final_segments(doctor_a, [("patient", 0, 1000, "line one")])
        _mock_llm(monkeypatch, _canned_note())

        with pytest.raises(ValueError):
            asyncio.run(generate_soap_note(consult["id"], doctor_b))

        asyncio.run(generate_soap_note(consult["id"], doctor_a))

        with pytest.raises(ValueError):
            update_soap_note(consult["id"], doctor_b, {"subjective": "hijacked"})
        with pytest.raises(ValueError):
            sign_soap_note(consult["id"], doctor_b)

        # A GET for the intruding doctor returns nothing (not even a 403 that would
        # confirm a note exists) — ownership is checked before any note lookup.
        assert get_soap_note(consult["id"], doctor_b) is None
        assert get_soap_note(consult["id"], doctor_a)["subjective"] == "Patient reports headache."
    finally:
        _cleanup([doctor_a, doctor_b])
