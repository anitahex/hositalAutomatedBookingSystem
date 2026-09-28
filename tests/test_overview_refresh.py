"""The at-a-glance card is rebuilt in the background when its inputs change.

Before this, the first doctor to open a patient after a note was signed, a prescription
approved or a document processed waited ~4s for the model to phrase the card. Now the
change schedules the rebuild, off the request path.

What must hold:
  - only departments that already have a card are rebuilt (no model call for a department
    whose doctors never open this patient)
  - signing and approving schedule it; the clinical action never waits for it and can
    never fail because of it
"""
from __future__ import annotations

import asyncio
import threading
import uuid

import pytest

from app.api.routes import consult as consult_route
from app.db.connection import connect_db
from app.services import patient_overview as po


def _doctor():
    return {"doctor_id": "doctor-1", "account_id": "account-1", "name": "Dr. Test", "department": "Neurology"}


# ---- scheduling from the routes ----

def test_signing_schedules_a_rebuild(monkeypatch):
    seen = []
    monkeypatch.setattr(consult_route, "sign_soap_note", lambda consultation_id, doctor_id: {"status": "signed"})
    monkeypatch.setattr(consult_route, "schedule_overview_refresh", lambda **kw: seen.append(kw))

    consult_route.sign_soap_note_route("c-1", doctor=_doctor())

    assert seen == [{"consultation_id": "c-1"}]


def test_approving_schedules_a_rebuild(monkeypatch):
    seen = []
    monkeypatch.setattr(consult_route, "approve_clinical_item", lambda *a: {"status": "approved"})
    monkeypatch.setattr(consult_route, "schedule_overview_refresh", lambda **kw: seen.append(kw))

    result = consult_route.approve_clinical_item_route("c-2", "prescription", doctor=_doctor())

    assert result == {"status": "approved"}
    assert seen == [{"consultation_id": "c-2"}]


def test_a_refused_signature_schedules_nothing(monkeypatch):
    """Nothing changed on the record, so there is nothing to rebuild."""
    from fastapi import HTTPException

    def refuse(*args):
        raise PermissionError("Note is not in a signable state.")

    seen = []
    monkeypatch.setattr(consult_route, "sign_soap_note", refuse)
    monkeypatch.setattr(consult_route, "schedule_overview_refresh", lambda **kw: seen.append(kw))

    with pytest.raises(HTTPException):
        consult_route.sign_soap_note_route("c-3", doctor=_doctor())
    assert seen == []


def test_scheduling_returns_immediately_and_never_raises(monkeypatch):
    """The sign request must not wait on a model call, nor fail because the rebuild did."""
    started = threading.Event()

    async def slow_and_broken(patient_id):
        started.set()
        await asyncio.sleep(0.5)
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(po, "refresh_cached_overviews", slow_and_broken)

    po.schedule_overview_refresh(patient_id="p-1")   # returns before the work runs
    assert started.wait(2), "the rebuild never ran"


def test_nothing_to_schedule_without_a_patient_or_consult():
    po.schedule_overview_refresh()   # no thread, no error


# ---- which cards are rebuilt ----

def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def test_only_departments_with_a_card_are_rebuilt(monkeypatch):
    _skip_if_no_database()
    patient = f"refresh-{uuid.uuid4()}"
    rebuilt = []

    async def fake_overview(doctor_id, patient_id, department):
        rebuilt.append(department)
        return {}

    monkeypatch.setattr(po, "get_overview", fake_overview)
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                for department in ("Cardiology", "Psychiatry"):
                    cur.execute(
                        """INSERT INTO patient_overviews (patient_id, viewer_department, lines, facts,
                                                          mode, reason, prompt_version, source_changed_at)
                           VALUES (%s, %s, '[]', '[]', 'structured', '', %s, NOW())""",
                        (patient, department, po.OVERVIEW_PROMPT_VERSION),
                    )
            conn.commit()

        count = asyncio.run(po.refresh_cached_overviews(patient))

        assert count == 2
        assert sorted(rebuilt) == ["Cardiology", "Psychiatry"]
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM patient_overviews WHERE patient_id = %s", (patient,))
            conn.commit()


def test_a_patient_with_no_cards_costs_nothing(monkeypatch):
    _skip_if_no_database()
    calls = []

    async def fake_overview(*args):
        calls.append(args)
        return {}

    monkeypatch.setattr(po, "get_overview", fake_overview)
    assert asyncio.run(po.refresh_cached_overviews(f"nobody-{uuid.uuid4()}")) == 0
    assert calls == []
