"""Department validation against the real doctors table.

test_department_validation.py pins the same properties with the department list pinned to
a constant. This file is the one that would catch the list drifting from reality — a
department renamed, a doctor deactivated, or a new alias pointing at something nobody
staffs.

Skips (not fails) if no database is reachable.
"""
from __future__ import annotations

import pytest

from app.db.connection import connect_db
from app.services.appointments import (
    CANONICAL_DEPARTMENTS,
    DEPARTMENT_ALIASES,
    NEVER_ROUTE_TO_DEPARTMENTS,
    available_departments,
    match_department,
    routable_departments,
)
from app.services.department_resolver import BODY_REGION_DEPARTMENTS


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _departments_with_doctors() -> set[str]:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT department FROM doctors "
                "WHERE COALESCE(is_active, TRUE) AND department IS NOT NULL"
            )
            return {row[0] for row in cur.fetchall() if row and row[0]}


def test_routable_departments_matches_the_doctors_table():
    _skip_if_no_database()
    assert set(routable_departments()) == _departments_with_doctors()


def test_routable_departments_is_not_gated_on_slot_availability():
    """available_departments() only lists departments with a free slot in the next seven
    days. Validating against it would make Psychiatry — one doctor — vanish in any week
    she is fully booked, and a patient asking for a psychiatrist would be told the
    hospital has no such department."""
    _skip_if_no_database()

    routable = set(routable_departments())
    bookable = {
        row["department"] if isinstance(row, dict) else row[0]
        for row in (available_departments() or [])
    }
    assert bookable <= routable, "slot availability must never widen the valid set"


def test_every_alias_resolves_to_a_department_that_has_doctors():
    """The guard against the whole class of bug: an alias pointing at a department nobody
    staffs sends the patient to an empty list."""
    _skip_if_no_database()

    staffed = _departments_with_doctors()
    unstaffed = {
        alias: target for alias, target in DEPARTMENT_ALIASES.items()
        if target not in staffed
    }
    assert not unstaffed, f"aliases resolve to departments with no doctors: {unstaffed}"


def test_every_body_region_maps_to_a_department_that_has_doctors():
    _skip_if_no_database()

    staffed = _departments_with_doctors()
    unstaffed = {
        region: target for region, target in BODY_REGION_DEPARTMENTS.items()
        if target not in staffed
    }
    assert not unstaffed, f"body regions map to departments with no doctors: {unstaffed}"


def test_no_producing_service_is_ever_routable():
    """Radiology, Pathology and the lab produce documents; they do not treat patients."""
    _skip_if_no_database()

    for department in routable_departments():
        assert " ".join(department.lower().split()) not in NEVER_ROUTE_TO_DEPARTMENTS


def test_the_canonical_list_has_not_drifted_from_the_database():
    """Not a hard equality: the DB is the source of truth and may legitimately gain a
    department. This catches the reverse — a canonical name nobody staffs, which is what
    lets a fabricated department look plausible."""
    _skip_if_no_database()

    staffed = _departments_with_doctors()
    missing = [d for d in CANONICAL_DEPARTMENTS if d not in staffed]
    assert not missing, f"canonical departments with no active doctors: {missing}"


def test_a_psychiatry_request_resolves_to_a_department_with_a_bookable_doctor():
    """The incident, end to end against real data: the patient asked for a psychiatrist
    four times and was offered Endocrinology."""
    _skip_if_no_database()

    routable = routable_departments()
    for phrasing in ["psychiatrist", "can i see a psychiatrist?", "can i see a phyciatrist ?"]:
        assert match_department(phrasing, routable) == "Psychiatry", phrasing
    assert "Psychiatry" in _departments_with_doctors()
