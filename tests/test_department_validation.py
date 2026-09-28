"""Departments that reach a patient must be ones this hospital actually staffs.

Three separate code paths used to invent department names, and none of them checked
against the doctors table:

  - app/api/routes/chat.py::_extract_dept_from_text  (streaming upload)
  - app/agents/document_analyzer.py::_infer_department  (LangGraph document path)
  - app/services/rag.py::DEPARTMENT_SYMPTOM_RULES -> candidate_departments (symptom triage)

Between them they could emit Pathology, Radiology, Ophthalmology, ENT, Gynecology and
Urology — six departments with zero bookable doctors. This file pins the fixes.

Same convention as test_booking_flow.py: call the functions directly, monkeypatch the
department lookup so these stay pure. test_department_resolver_integration.py checks the
same property against real SQL.
"""
from __future__ import annotations

import pytest

from app.agents import appointment_booker
from app.agents import document_analyzer
from app.services import appointments as appointments_service

REAL_DEPARTMENTS = [
    "General Physician", "Gastroenterology", "Cardiology", "Neurology",
    "Orthopedics", "Oncology", "Pulmonology", "Psychiatry", "Nephrology",
    "Endocrinology", "Hematology", "Dermatology",
]

# Every department the old code could emit that does not exist here.
FABRICATED = ["Pathology", "Radiology", "Ophthalmology", "ENT", "Gynecology", "Urology"]

# Captured at import, BEFORE the autouse fixture below replaces it. The fallback test must
# call the real implementation: REAL_DEPARTMENTS is identical to CANONICAL_DEPARTMENTS, so
# asserting against the patched lambda would pass without exercising the fallback at all.
_REAL_ROUTABLE_DEPARTMENTS = appointments_service.routable_departments


@pytest.fixture(autouse=True)
def _fixed_department_list(monkeypatch):
    """Pin the routable list so these tests do not depend on a database."""
    monkeypatch.setattr(
        appointments_service, "routable_departments", lambda *a, **k: list(REAL_DEPARTMENTS)
    )


# ---- document_analyzer: the LangGraph document path ----

@pytest.mark.parametrize(
    "doc_type,impression",
    [
        ("blood_report", "CBC results, haemoglobin 13.1, platelet count normal."),
        ("pathology_report", "Lab result reviewed, wbc and rbc within range."),
    ],
)
def test_a_lab_report_no_longer_routes_to_pathology(doc_type, impression):
    """_DEPT_MAP mapped blood_report -> "Pathology" by design. Pathology ran the test; it
    does not treat the patient, and it has no doctors here."""
    assert document_analyzer._infer_department(doc_type, impression, {}) != "Pathology"


@pytest.mark.parametrize("doc_type", ["mri_report", "ct_report", "xray_report"])
def test_a_scan_no_longer_routes_to_radiology(doc_type):
    result = document_analyzer._infer_department(doc_type, "Imaging study performed.", {})
    assert result != "Radiology"
    assert result in REAL_DEPARTMENTS


def test_an_mri_of_the_spine_routes_to_the_department_that_treats_spines():
    assert document_analyzer._infer_department(
        "mri_report", "MRI lumbar spine shows a disc bulge.", {}
    ) == "Orthopedics"


@pytest.mark.parametrize(
    "impression",
    [
        "Eye pain with blurry vision and retinal changes.",   # was Ophthalmology
        "Sore throat, sinus congestion and hearing loss.",    # was ENT
        "Urinary frequency with a kidney stone and bladder discomfort.",  # was Urology
    ],
)
def test_content_that_used_to_produce_an_unstaffed_department_now_falls_back_safely(impression):
    result = document_analyzer._infer_department("other", impression, {})
    assert result in REAL_DEPARTMENTS, f"{result!r} is not a department we staff"
    assert result not in FABRICATED


def test_infer_department_always_returns_a_real_department_never_none():
    """Two call sites pass this straight on without a None check, so the contract is
    'always a usable department'."""
    for impression in ["", "nothing clinical here at all", "zzzz"]:
        result = document_analyzer._infer_department("other", impression, {})
        assert result in REAL_DEPARTMENTS


def test_the_real_report_now_surfaces_psychiatry_alongside_endocrinology():
    """The incident behind this work. The report mentioned BOTH anxiety/insomnia and
    thyroid/glucose. First-match-wins returned Endocrinology because it sat ten rows above
    Psychiatry in a hand-ordered list, and the mental-health signal was discarded
    silently. Both must now be visible so the patient can be asked."""
    impression = (
        "Raised morning cortisol. Patient reports anxiety and insomnia. "
        "Thyroid and glucose within range."
    )
    candidates = document_analyzer._department_candidates(
        "blood_report", impression, {}, REAL_DEPARTMENTS
    )
    assert "Psychiatry" in candidates
    assert "Endocrinology" in candidates


def test_candidates_never_include_a_department_we_do_not_staff():
    impression = "eye pain, sore throat, urinary frequency, mri imaging, cbc blood report"
    for department in document_analyzer._department_candidates(
        "blood_report", impression, {}, REAL_DEPARTMENTS
    ):
        assert department in REAL_DEPARTMENTS


# ---- the gate: candidates on their way to a patient ----

def _candidate(name):
    return {"department": name, "confidence": 0.9, "matched_terms": [], "reason": "r"}


def test_the_gate_drops_unstaffed_departments_from_a_menu():
    """rag.py's DEPARTMENT_SYMPTOM_RULES contains ENT, Urology and Ophthalmology, so
    "my eye hurts" could put an Ophthalmology option in front of a patient that books
    nothing. Filtering happens where candidates are CONSUMED, so a producer added later
    cannot bypass it."""
    kept = appointment_booker._bookable_candidates(
        [_candidate("Ophthalmology"), _candidate("Cardiology"),
         _candidate("ENT"), _candidate("Psychiatry")]
    )
    assert [c["department"] for c in kept] == ["Cardiology", "Psychiatry"]


def test_the_gate_preserves_order_and_shape():
    original = [_candidate("Psychiatry"), _candidate("Cardiology")]
    kept = appointment_booker._bookable_candidates(original)
    assert kept == original


def test_the_gate_tolerates_malformed_candidate_entries():
    """A malformed row must not take down the booking flow."""
    kept = appointment_booker._bookable_candidates(
        ["not a dict", None, {}, {"department": ""}, _candidate("Cardiology")]
    )
    assert [c["department"] for c in kept] == ["Cardiology"]


def test_a_menu_of_only_unstaffed_departments_falls_through_instead_of_being_shown(monkeypatch):
    """If every candidate is filtered out, the patient must not be shown an empty menu."""
    monkeypatch.setattr(appointment_booker, "ask_preferred_doctor",
                        lambda state: {"fell_through": True})
    result = appointment_booker.ask_department_choice(
        {"candidate_departments": [_candidate("ENT"), _candidate("Urology")]}
    )
    assert result == {"fell_through": True}


def test_a_menu_with_at_least_one_staffed_department_is_still_shown():
    result = appointment_booker.ask_department_choice(
        {"candidate_departments": [_candidate("ENT"), _candidate("Psychiatry")]}
    )
    assert result["awaiting"] == "department_selection"
    assert [c["department"] for c in result["candidate_departments"]] == ["Psychiatry"]


# ---- the validation list itself ----

def test_routable_departments_falls_back_instead_of_returning_nothing(monkeypatch):
    """An empty validation list would reject every department and take booking down with
    it. A database outage must degrade to the static list, not to a hard failure."""
    def _boom():
        raise RuntimeError("database unreachable")

    monkeypatch.setattr(appointments_service, "connect_db", _boom)
    result = _REAL_ROUTABLE_DEPARTMENTS()
    assert result == list(appointments_service.CANONICAL_DEPARTMENTS)
    assert "Psychiatry" in result
