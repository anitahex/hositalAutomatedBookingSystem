"""Department routing — pure logic only, no DB and no LLM.

Same convention as test_booking_flow.py / test_mobile_number_normalization.py: call the
functions directly with plain values, parametrize the value tables, no network access.
tests/test_department_resolver_integration.py covers the one thing that needs a real
database — that every department this module can emit actually has doctors.

Several tests here are SAFETY tests rather than behaviour tests and must not be relaxed:

  - test_the_real_incident_* — the transcript that motivated this module. A patient with a
    Psychiatry referral and anxiety/insomnia was offered Endocrinology four times. The
    resolver must never silently resolve Endocrinology on that input.
  - test_*_never_fabricates_* — an unmatched string must produce no department at all,
    never a department named after the patient's typo.
  - test_*_never_routes_to_a_producing_service — you do not follow up with the radiologist
    who read your scan or the lab that ran your blood.
"""
from __future__ import annotations

import pytest

from app.services.appointments import match_department, match_department_scored
from app.services.department_resolver import (
    DEFAULT_DEPARTMENT,
    DepartmentSignal,
    body_region_department,
    resolve_department,
    signal_from_text,
    signals_from_document,
)

REAL_DEPARTMENTS = [
    "General Physician", "Gastroenterology", "Cardiology", "Neurology",
    "Orthopedics", "Oncology", "Pulmonology", "Psychiatry", "Nephrology",
    "Endocrinology", "Hematology", "Dermatology",
]


def _signal(department, source, confidence=1.0, reason="r"):
    return DepartmentSignal(department=department, source=source,
                            confidence=confidence, reason=reason)


# ---- free-text matching ----

@pytest.mark.parametrize(
    "text,expected",
    [
        ("Psychiatry", "Psychiatry"),            # canonical
        ("psychiatrist", "Psychiatry"),          # practitioner form
        ("psychitary department", "Psychiatry"), # the spelling in the existing suite
        ("phyciatrist", "Psychiatry"),           # the patient's actual typo
        ("psycologist", "Psychiatry"),
        ("mental health", "Psychiatry"),
        ("cardiologist", "Cardiology"),
        ("heart", "Cardiology"),
        ("can i see a psychiatrist?", "Psychiatry"),   # whole sentence
        ("can i see a phyciatrist ?", "Psychiatry"),   # whole sentence, misspelled
    ],
)
def test_strict_matching_resolves_the_words_patients_actually_use(text, expected):
    assert match_department(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "nonsense wxyz", "", None, "the", "please help me",
        "radiology", "pathology", "laboratory",
    ],
)
def test_strict_matching_never_fabricates_a_department(text):
    """The bug this replaces title-cased unmatched input and returned it as real
    ("physcologist" -> 'Physcologist'). Nothing may come back but None."""
    assert match_department(text) is None


@pytest.mark.parametrize("text", ["radiology", "pathology", "laboratory", "mri radiology report"])
def test_a_producing_service_is_rejected_as_input_not_fuzzy_matched(text):
    """Checking only the RESULT let "radiology" fuzzy-match to Cardiology at 0.84 and
    "pathology" to Psychiatry at 0.74 — plausible scores for departments the patient never
    mentioned."""
    department, score = match_department_scored(text)
    assert department is None
    assert score == 0.0


@pytest.mark.parametrize("text", ["physcologist", "physiatrist", "physcitarist"])
def test_a_typo_level_match_is_offered_but_never_acted_on(text):
    """"physiatrist" (physical medicine) is one edit from "psychiatrist" (mental health).
    Scoring keeps it as something to ASK about; strict matching refuses to act on it."""
    department, score = match_department_scored(text)
    assert department == "Psychiatry"
    assert 0 < score < 1.0
    assert match_department(text) is None


@pytest.mark.parametrize(
    "text,expected",
    [("nephrologist", "Nephrology"), ("neurologist", "Neurology")],
)
def test_nephrologist_is_not_fuzzy_matched_to_neurology(text, expected):
    """Kidneys, not the brain. Before the practitioner aliases existed, "nephrologist"
    fuzzy-matched the pre-existing "neurologist" alias at 0.87 — beating "nephrology" at
    0.818 — and routed to Neurology. A live clinical mis-routing, fixed by matching the
    practitioner word exactly before any fuzzy pass runs."""
    assert match_department(text) == expected


def test_matching_can_be_constrained_to_departments_this_hospital_actually_has():
    assert match_department("cardiologist", REAL_DEPARTMENTS) == "Cardiology"
    assert match_department("cardiologist", ["Psychiatry"]) is None


# ---- the real incident ----

def _real_incident_document():
    """The blood report from the transcript: referred by a psychiatrist, anxiety and
    insomnia in the history, raised cortisol in the findings."""
    return {
        "document_type": "blood_report",
        "referring_doctor": "Dr. Sunita Panday",
        "referring_department": "Psychiatry",
        "clinical_history": "anxiety for the past few days and unable to sleep",
        "recommended_department": "Endocrinology",
        "overall_impression": "Raised morning cortisol, low vitamin D and B12.",
    }


def test_the_real_incident_asks_instead_of_silently_choosing_endocrinology():
    """THE regression test for this module. Endocrinology is a legitimate reading of the
    cortisol result — but so is the Psychiatry referral, and the patient must be the one
    who decides between them."""
    signals = signals_from_document(_real_incident_document(), REAL_DEPARTMENTS)
    result = resolve_department(signals, REAL_DEPARTMENTS)

    assert result.decision == "ask"
    assert result.department is None, "must not silently resolve a department"
    offered = {c["department"] for c in result.candidates}
    assert "Psychiatry" in offered, "the referral was ignored entirely in the original bug"
    assert "Endocrinology" in offered, "the cortisol finding must not be hidden either"


def test_the_real_incident_ranks_the_referral_above_the_findings():
    signals = signals_from_document(_real_incident_document(), REAL_DEPARTMENTS)
    result = resolve_department(signals, REAL_DEPARTMENTS)
    assert result.candidates[0]["department"] == "Psychiatry"
    assert result.candidates[0]["source"] == "referral"


def test_an_explicit_request_outranks_everything_on_the_document():
    """The patient asking for a psychiatrist must win outright — that request was
    swallowed four times in the original transcript."""
    signals = signals_from_document(_real_incident_document(), REAL_DEPARTMENTS)
    signals.append(_signal("Psychiatry", "explicit_request"))
    result = resolve_department(signals, REAL_DEPARTMENTS)

    assert result.decision == "resolved"
    assert result.department == "Psychiatry"


# ---- per document type ----

def test_a_lab_report_never_routes_to_pathology():
    signals = signals_from_document(
        {"document_type": "blood_report", "recommended_department": "Pathology"},
        REAL_DEPARTMENTS,
    )
    assert all(s.department != "Pathology" for s in signals)
    assert resolve_department(signals, REAL_DEPARTMENTS).department != "Pathology"


def test_a_scan_never_routes_to_radiology_and_uses_the_body_region_instead():
    """An MRI with no referring doctor. Radiology produced the report; Orthopedics treats
    the spine."""
    signals = signals_from_document(
        {"document_type": "mri_report", "recommended_department": "Radiology",
         "body_region": "Lumbar spine"},
        REAL_DEPARTMENTS,
    )
    result = resolve_department(signals, REAL_DEPARTMENTS)
    assert result.department == "Orthopedics"
    assert all(c["department"] != "Radiology" for c in result.candidates)


@pytest.mark.parametrize(
    "region,expected",
    [
        ("Lumbar spine", "Orthopedics"), ("left knee", "Orthopedics"),
        ("Brain", "Neurology"), ("chest", "Pulmonology"),
        ("cardiac", "Cardiology"), ("abdomen", "Gastroenterology"),
        ("renal", "Nephrology"), ("no idea", None),
    ],
)
def test_body_region_maps_to_the_department_that_treats_it(region, expected):
    assert body_region_department(region)[0] == expected


def test_an_external_prescription_maps_to_our_closest_department_and_confirms():
    """The prescriber is at another hospital and is not in our doctors table, so this can
    never book them — it proposes the matching department and asks."""
    signals = signals_from_document(
        {"document_type": "prescription", "prescriber_specialty": "Psychiatrist",
         "clinical_history": "follow-up for anxiety"},
        REAL_DEPARTMENTS,
    )
    result = resolve_department(signals, REAL_DEPARTMENTS)
    assert "Psychiatry" in {c["department"] for c in result.candidates}
    assert result.department != "Dr. Sunita Panday"


def test_an_ecg_report_routes_to_cardiology_not_to_a_producing_service():
    signals = signals_from_document(
        {"document_type": "ecg_report", "recommended_department": "Cardiology"},
        REAL_DEPARTMENTS,
    )
    assert resolve_department(signals, REAL_DEPARTMENTS).department == "Cardiology"


# ---- resolution rules ----

def test_agreeing_signals_resolve_without_asking():
    result = resolve_department(
        [_signal("Cardiology", "referral"), _signal("Cardiology", "findings")],
        REAL_DEPARTMENTS,
    )
    assert result.decision == "resolved"
    assert result.department == "Cardiology"


def test_disagreeing_signals_always_ask_and_show_both():
    result = resolve_department(
        [_signal("Psychiatry", "referral"), _signal("Endocrinology", "findings")],
        REAL_DEPARTMENTS,
    )
    assert result.decision == "ask"
    assert result.department is None
    assert len(result.candidates) == 2


def test_a_department_we_do_not_have_is_dropped_entirely():
    result = resolve_department([_signal("Psychology", "referral")], REAL_DEPARTMENTS)
    assert result.decision == "none"
    assert result.department is None


def test_no_signals_at_all_is_handled_not_crashed():
    for empty in ([], None):
        result = resolve_department(empty, REAL_DEPARTMENTS)
        assert result.decision == "none"
        assert result.department is None
    assert signals_from_document(None) == []
    assert signals_from_document({}) == []


def test_candidates_are_shaped_for_the_existing_disambiguation_menu():
    """ask_department_choice already consumes {department, confidence, matched_terms,
    reason}; reusing that shape is why this needs no second menu implementation."""
    result = resolve_department(
        [_signal("Psychiatry", "referral"), _signal("Endocrinology", "findings")],
        REAL_DEPARTMENTS,
    )
    for candidate in result.candidates:
        assert {"department", "confidence", "matched_terms", "reason", "source"} <= set(candidate)


def test_a_weak_single_match_asks_rather_than_assuming_the_typo_was_intended():
    result = resolve_department([_signal("Psychiatry", "findings", confidence=0.75)],
                                REAL_DEPARTMENTS)
    assert result.decision == "ask"


def test_signal_from_text_yields_nothing_for_unmatched_text():
    assert signal_from_text("nonsense wxyz", "symptoms", REAL_DEPARTMENTS) is None
    assert signal_from_text("psychiatrist", "symptoms", REAL_DEPARTMENTS).department == "Psychiatry"


def test_the_default_department_is_one_we_actually_have():
    assert DEFAULT_DEPARTMENT in REAL_DEPARTMENTS
