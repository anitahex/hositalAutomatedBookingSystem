"""The overview card against a real database.

The pure grounding rules are in test_patient_overview.py. These cover what only SQL can
prove, and the first of them is the one that matters most: the card must not quietly undo
the restriction the timeline enforces one panel below it.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services import patient_overview as overview_module
from app.services.patient_overview import (
    LABEL_PATIENT_REPORTS,
    gather_facts,
    get_overview,
    latest_source_change,
)


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _doctor(cur, name, department):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, %s, 1, TRUE) RETURNING doctor_id""",
        (name, department),
    )
    return str(cur.fetchone()[0])


def _patient(cur, email, health_issues=None):
    cur.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id", (email,)
    )
    user_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email,
                                         blood_group, health_issues)
           VALUES (%s, %s, 30, '9999999999', 'Test', %s, 'O+', %s)""",
        (user_id, f"Patient {email}", email, health_issues),
    )
    return user_id


def _signed_note(cur, doctor_id, patient_id, assessment, *, days_ago=1):
    start = datetime.now() - timedelta(days=days_ago)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
           VALUES (%s, %s, %s, TRUE, %s) RETURNING slot_id""",
        (doctor_id, start, start + timedelta(minutes=30), patient_id),
    )
    slot_id = cur.fetchone()[0]
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, 'completed') RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start, start + timedelta(minutes=30)),
    )
    booking_id = cur.fetchone()[0]
    cur.execute(
        """INSERT INTO consultations (booking_id, doctor_id, patient_id, status)
           VALUES (%s, %s, %s, 'transcript_ready') RETURNING id""",
        (booking_id, doctor_id, patient_id),
    )
    consult_id = cur.fetchone()[0]
    cur.execute(
        """INSERT INTO soap_notes (consultation_id, doctor_id, patient_id, assessment, plan,
                                   status, generated_at, signed_at)
           VALUES (%s, %s, %s, %s, 'Plan', 'signed', NOW(), NOW())""",
        (consult_id, doctor_id, patient_id, assessment),
    )
    return str(consult_id)


@pytest.fixture
def world():
    _skip_if_no_database()
    ids = {}
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                ids["patient"] = _patient(
                    cur, f"ov-{uuid.uuid4().hex[:8]}@example.com",
                    health_issues="Vitamin B12 deficiency. Occasional anxiety.",
                )
                ids["cardio"] = _doctor(cur, "Dr. Cardio", "Cardiology")
                ids["psych"] = _doctor(cur, "Dr. Psych", "Psychiatry")
                _signed_note(cur, ids["cardio"], ids["patient"],
                             "Atrial fibrillation, rate controlled.", days_ago=2)
                _signed_note(cur, ids["psych"], ids["patient"],
                             "Generalised anxiety disorder.", days_ago=5)
            conn.commit()
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM patient_overviews WHERE patient_id = %s", (ids.get("patient"),))
                for key in ("cardio", "psych"):
                    if ids.get(key):
                        cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (ids[key],))
                if ids.get("patient"):
                    cur.execute("DELETE FROM users WHERE user_id = %s", (ids["patient"],))
            conn.commit()


# ---- the restriction must hold here too ----

def test_a_sensitive_specialtys_diagnosis_is_not_in_another_doctors_card(world):
    """The card sits directly above the timeline that withholds this. If it appeared here
    the restriction would be undone by the summary, which is the worse failure: a doctor
    reads the card and never scrolls."""
    facts = gather_facts(world["cardio"], world["patient"], "Cardiology")

    assert "Generalised anxiety disorder" not in str(facts)
    assert "Atrial fibrillation" in str(facts)


def test_the_specialtys_own_doctor_still_sees_it(world):
    facts = gather_facts(world["psych"], world["patient"], "Psychiatry")
    assert "Generalised anxiety disorder" in str(facts)


def test_the_cache_is_keyed_by_viewing_department(world):
    """The most dangerous caching bug available here: one department's card served to
    another would look like a performance win and silently leak a restricted diagnosis."""
    async def build():
        # Phrasing is irrelevant to this test and costs a model call; force the
        # structured path so it exercises caching only.
        async def no_phrasing(**kwargs):
            raise RuntimeError("no model in tests")

        import app.inference.azure_client as azure
        original = azure.gpt4o_overview_phrasing
        azure.gpt4o_overview_phrasing = no_phrasing
        try:
            cardio = await get_overview(world["cardio"], world["patient"], "Cardiology")
            psych = await get_overview(world["psych"], world["patient"], "Psychiatry")
            return cardio, psych
        finally:
            azure.gpt4o_overview_phrasing = original

    cardio, psych = asyncio.run(build())

    assert "Generalised anxiety disorder" not in str(cardio["lines"])
    assert "Generalised anxiety disorder" in str(psych["lines"])


# ---- labels ----

def test_the_patients_own_words_are_labelled_as_such(world):
    """health_issues is unvalidated free text. It may be shown, never promoted into a
    diagnosis."""
    facts = gather_facts(world["cardio"], world["patient"], "Cardiology")
    concerns = [f for f in facts if f["kind"] == "concern"]

    assert concerns
    assert all(f["label"] == LABEL_PATIENT_REPORTS for f in concerns)


def test_an_unsigned_draft_is_not_a_diagnosis(world):
    """Only signed notes become diagnoses on the card."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            consult = _signed_note(cur, world["cardio"], world["patient"],
                                   "Draft only assessment.", days_ago=3)
            cur.execute(
                "UPDATE soap_notes SET status = 'draft', signed_at = NULL WHERE consultation_id = %s",
                (consult,),
            )
        conn.commit()

    facts = gather_facts(world["cardio"], world["patient"], "Cardiology")
    assert "Draft only assessment" not in str(facts)


# ---- the cache is self-correcting ----

def test_the_cache_rebuilds_when_the_record_changes(world):
    """Staleness is decided by comparing recorded inputs against current ones, not by
    trusting every writer to call invalidate(). A new signed note must appear without any
    writer knowing the cache exists."""
    async def build():
        async def no_phrasing(**kwargs):
            raise RuntimeError("no model in tests")

        import app.inference.azure_client as azure
        original = azure.gpt4o_overview_phrasing
        azure.gpt4o_overview_phrasing = no_phrasing
        try:
            first = await get_overview(world["cardio"], world["patient"], "Cardiology")
            with connect_db() as conn:
                with conn.cursor() as cur:
                    _signed_note(cur, world["cardio"], world["patient"],
                                 "New finding: hypertension.", days_ago=0)
                conn.commit()
            second = await get_overview(world["cardio"], world["patient"], "Cardiology")
            return first, second
        finally:
            azure.gpt4o_overview_phrasing = original

    first, second = asyncio.run(build())

    assert first["cached"] is False
    assert second["cached"] is False, "the cache did not notice a new signed note"
    assert "hypertension" in str(second["lines"]).lower()


def test_an_unchanged_record_is_served_from_cache(world):
    async def build():
        async def no_phrasing(**kwargs):
            raise RuntimeError("no model in tests")

        import app.inference.azure_client as azure
        original = azure.gpt4o_overview_phrasing
        azure.gpt4o_overview_phrasing = no_phrasing
        try:
            await get_overview(world["cardio"], world["patient"], "Cardiology")
            return await get_overview(world["cardio"], world["patient"], "Cardiology")
        finally:
            azure.gpt4o_overview_phrasing = original

    assert asyncio.run(build())["cached"] is True


def test_a_model_failure_still_returns_the_facts(world):
    """A doctor must get the record even when nothing can phrase it. The card degrades to
    the structured list; it never becomes an error."""
    async def build():
        async def broken(**kwargs):
            raise RuntimeError("model unavailable")

        import app.inference.azure_client as azure
        original = azure.gpt4o_overview_phrasing
        azure.gpt4o_overview_phrasing = broken
        try:
            return await get_overview(world["cardio"], world["patient"], "Cardiology")
        finally:
            azure.gpt4o_overview_phrasing = original

    result = asyncio.run(build())

    assert result["mode"] == "structured"
    assert result["lines"], "the facts were lost along with the phrasing"
    assert result["reason"]


def test_latest_source_change_moves_when_a_note_is_signed(world):
    before = latest_source_change(world["patient"])
    with connect_db() as conn:
        with conn.cursor() as cur:
            _signed_note(cur, world["cardio"], world["patient"], "Another finding.", days_ago=0)
        conn.commit()

    assert latest_source_change(world["patient"]) >= before
