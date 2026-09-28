"""Who may read what on the cross-doctor timeline.

Pure — no database, no model. The SQL is covered in
test_patient_timeline_integration.py.

These are disclosure rules, not formatting rules. The timeline is the feature that widened
what a doctor can see from "my own signed notes" to "this hospital's whole history for
this patient", so every rule about what is withheld is a safety test and none may be
relaxed to make a screen look fuller.
"""
from __future__ import annotations

import pytest

from app.services.patient_timeline import (
    RESTRICTED_NOTE_LABEL,
    SENSITIVE_DEPARTMENTS,
    is_sensitive_department,
    may_read_note,
)


# ---- which specialties are sensitive ----

def test_psychiatry_is_sensitive_by_default():
    """The agreed default. Mental-health notes are the usual exception to "treating
    doctors see everything"."""
    assert is_sensitive_department("Psychiatry")
    assert "psychiatry" in SENSITIVE_DEPARTMENTS


@pytest.mark.parametrize(
    "department", ["Cardiology", "Nephrology", "General Physician", "Orthopedics"]
)
def test_an_ordinary_specialty_is_not_sensitive(department):
    assert not is_sensitive_department(department)


@pytest.mark.parametrize("spelling", ["psychiatry", "PSYCHIATRY", "  Psychiatry  ", "PsYcHiAtRy"])
def test_the_match_is_case_and_whitespace_insensitive(spelling):
    """department is free text on the doctors table. A restriction that could be bypassed
    by capitalisation would not be a restriction."""
    assert is_sensitive_department(spelling)


@pytest.mark.parametrize("value", [None, "", "   "])
def test_an_unknown_department_is_not_treated_as_sensitive(value):
    """Fails open deliberately, and only here. Treating "no department recorded" as
    sensitive would withhold ordinary notes across the hospital on a data-quality problem;
    the restriction exists for a named specialty, not for missing data."""
    assert not is_sensitive_department(value)


# ---- who may read a sensitive note ----

def test_a_doctor_outside_the_specialty_may_not_read_its_notes():
    assert not may_read_note("Cardiology", "Psychiatry")


def test_a_doctor_inside_the_specialty_reads_them_normally():
    """The restriction is about disclosure ACROSS specialties. It must not make psychiatry
    notes unreadable to psychiatrists."""
    assert may_read_note("Psychiatry", "Psychiatry")
    assert may_read_note("  psychiatry ", "Psychiatry")


def test_ordinary_notes_are_readable_by_anyone_treating_the_patient():
    """Past the treating-relationship gate, an ordinary encounter is fully visible — that
    was the decision, and withholding it would be the clinical risk."""
    assert may_read_note("Cardiology", "Nephrology")
    assert may_read_note("Nephrology", "Nephrology")
    assert may_read_note(None, "Cardiology")


def test_a_viewer_with_no_department_cannot_read_a_sensitive_note():
    """Fails CLOSED here, unlike an unknown encounter department. An unknown viewer must
    not inherit access to a restricted specialty."""
    for viewer in (None, "", "   "):
        assert not may_read_note(viewer, "Psychiatry")


# ---- what a withheld note says ----

def test_a_restricted_note_says_it_is_restricted():
    """It must never render as an empty or missing note. "Nothing was written" and
    "something exists and you may not see it" are different facts, and a doctor acting on
    the first when the second is true is the whole hazard."""
    assert "Restricted" in RESTRICTED_NOTE_LABEL
    assert RESTRICTED_NOTE_LABEL.strip()
