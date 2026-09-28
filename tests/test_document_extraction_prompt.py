"""The document prompts — what we ask the model to read, and what we let it recommend.

Prompt-content checks, in the same spirit as
test_document_upload_e2e.py::test_stream_format_prompt_allows_best_effort_reading_of_unclear_handwriting.
They do not prove the model complies; they prove we asked, which is the part that
regressed silently before.

Motivating incident: a blood report carried "Referred by Dr. Sunita Panday, Psychiatry",
and in 3,914 characters of generated analysis the words "Panday", "Referr" and
"Psychiatr" appeared ZERO times. No template had a Referred By field and the extraction
schema had no slot for one, so the strongest routing signal on the page was discarded
before any routing code ran.
"""
from __future__ import annotations

import pytest

from app.inference.azure_client import (
    _EXTRACTION_SYSTEM,
    _STREAM_FORMAT_SYSTEM,
    build_stream_format_system_prompt,
)


# ---- extraction schema ----

@pytest.mark.parametrize(
    "field",
    ["referring_doctor", "referring_department", "clinical_history", "body_region"],
)
def test_extraction_schema_asks_for_the_routing_fields(field):
    assert field in _EXTRACTION_SYSTEM


def test_extraction_prompt_tells_the_model_to_read_the_letterhead():
    """The schema field alone was not enough — the prompt is results-oriented, so the
    model never looked at the header where the referral is printed."""
    prompt = _EXTRACTION_SYSTEM
    assert "LETTERHEAD" in prompt or "letterhead" in prompt
    assert "Referred By" in prompt
    assert "Referring Physician" in prompt


def test_extraction_prompt_forbids_inferring_a_referral_from_the_findings():
    """A referral is something printed on the page. Inferring one from lab values would
    manufacture the very signal we rank most highly."""
    assert "Never infer referring_department" in _EXTRACTION_SYSTEM


def test_extraction_prompt_keeps_clinical_history_distinct_from_the_results():
    assert "Do not summarise the results into it" in _EXTRACTION_SYSTEM


@pytest.mark.parametrize("doc_type", ["ecg_report", "ultrasound_report"])
def test_document_taxonomy_covers_the_types_patients_actually_upload(doc_type):
    """ECG and ultrasound were missing from the taxonomy entirely, so both collapsed to
    'other' and lost their type-specific routing."""
    assert doc_type in _EXTRACTION_SYSTEM


def test_extraction_prompt_still_forbids_inventing_values():
    """Pre-existing guarantee — the new fields must not have diluted it."""
    assert "Do NOT invent or estimate any value" in _EXTRACTION_SYSTEM


# ---- the visible analysis ----

def test_stream_prompt_asks_for_referred_by_on_every_document_type():
    """Prescription, lab and imaging templates each need it — a referral can appear on
    any of them."""
    assert _STREAM_FORMAT_SYSTEM.count("**Referred By:**") >= 3


def test_stream_prompt_forbids_recommending_a_service_that_produced_the_report():
    prompt = _STREAM_FORMAT_SYSTEM
    assert "NEVER name Radiology, Pathology" in prompt
    assert "do not treat the patient" in prompt


def test_stream_prompt_is_unchanged_when_no_department_list_is_injected():
    """The unconstrained path must be provably identical, so callers that do not pass a
    list are unaffected."""
    assert build_stream_format_system_prompt() == _STREAM_FORMAT_SYSTEM
    assert build_stream_format_system_prompt(None) == _STREAM_FORMAT_SYSTEM
    assert build_stream_format_system_prompt([]) == _STREAM_FORMAT_SYSTEM


def test_injected_departments_are_the_only_ones_offered():
    prompt = build_stream_format_system_prompt(["Cardiology", "Psychiatry"])
    assert "Cardiology" in prompt
    assert "Psychiatry" in prompt
    assert "Endocrinology" not in prompt
    assert "Gastroenterology" not in prompt


def test_the_department_list_is_injected_not_hard_coded_in_the_prompt():
    """If the names were written into the template they would drift from the doctors
    table, which is how a recommendation for a department with no doctors happens."""
    for department in ["Cardiology", "Psychiatry", "Endocrinology", "Nephrology"]:
        assert department not in _STREAM_FORMAT_SYSTEM


def test_injected_prompt_still_carries_the_pre_existing_handwriting_instruction():
    """test_document_upload_e2e.py asserts this on the base constant; it must survive the
    builder too."""
    prompt = build_stream_format_system_prompt(["Cardiology"])
    assert "best-effort" in prompt or "(?)" in prompt


def test_a_blank_department_name_is_not_offered_to_the_model():
    prompt = build_stream_format_system_prompt(["Cardiology", "  ", ""])
    assert "Cardiology" in prompt
    assert "|  |" not in prompt
