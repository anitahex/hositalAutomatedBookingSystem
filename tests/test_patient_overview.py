"""The at-a-glance card's grounding rules.

Pure — no database, no model.

The design is "code extracts, the model only phrases". These tests cover the half that
makes that claim true: the check that runs AFTER phrasing. Without it, "the model may only
phrase the facts" is a prompt instruction, which is a hope, not a guarantee.

A failure here is never repaired. The card falls back to the plain structured list — drier
to read, completely faithful. That is the right way round: the prose is a convenience, the
facts are the point.
"""
from __future__ import annotations

import pytest

from app.services.patient_overview import (
    LABEL_PATIENT_REPORTS,
    LABEL_REPORTED_UNVERIFIED,
    MAX_OVERVIEW_LINES,
    structured_lines,
    verify_phrasing,
)

FACTS = [
    {"id": "f1", "kind": "concern", "text": "Anxiety and poor sleep",
     "label": LABEL_PATIENT_REPORTS, "source_type": "patient_profile", "source_id": None},
    {"id": "f2", "kind": "medication", "text": "Amlodipine 5 mg once daily",
     "label": None, "source_type": "note", "source_id": "c1"},
    {"id": "f3", "kind": "abnormal", "text": "Vitamin D low at 13.8 ng/mL (2026-09-20)",
     "label": None, "source_type": "document", "source_id": "d1"},
]


def _line(text, *ids):
    return {"text": text, "fact_ids": list(ids)}


# ---- the phrasing is accepted when it is faithful ----

def test_a_faithful_phrasing_is_accepted():
    ok, reason = verify_phrasing(
        [
            _line("Reports anxiety and poor sleep.", "f1"),
            _line("On amlodipine 5 mg once daily.", "f2"),
            _line("Vitamin D low at 13.8 ng/mL.", "f3"),
        ],
        FACTS,
    )
    assert ok, reason


def test_several_facts_may_be_combined_into_one_line():
    """Combining is the point of phrasing. It is only dropping that is forbidden."""
    ok, reason = verify_phrasing(
        [
            _line("Reports anxiety and poor sleep; on amlodipine 5 mg daily.", "f1", "f2"),
            _line("Vitamin D low at 13.8 ng/mL.", "f3"),
        ],
        FACTS,
    )
    assert ok, reason


def test_a_line_may_omit_numbers_it_does_not_need():
    """The check is one-directional: numbers in the PROSE must exist in the facts. A
    summary is allowed to leave a value out."""
    ok, _ = verify_phrasing(
        [_line("Reports anxiety.", "f1"), _line("On amlodipine.", "f2"),
         _line("Vitamin D is low.", "f3")],
        FACTS,
    )
    assert ok


# ---- and rejected when it is not ----

def test_a_dropped_fact_fails_the_whole_phrasing():
    """This is how an overview silently loses a medication or an abnormal result. Treated
    as a failure of the phrasing, not of one line, because a summary that has dropped a
    fact is one whose other lines cannot be trusted either."""
    ok, reason = verify_phrasing(
        [_line("Reports anxiety and poor sleep.", "f1"), _line("On amlodipine.", "f2")],
        FACTS,
    )
    assert not ok
    assert "dropped" in reason


def test_an_invented_number_fails():
    """The model was given 13.8 and wrote 38."""
    ok, reason = verify_phrasing(
        [_line("Reports anxiety.", "f1"), _line("On amlodipine 5 mg.", "f2"),
         _line("Vitamin D low at 38 ng/mL.", "f3")],
        FACTS,
    )
    assert not ok
    assert "number" in reason


def test_a_number_borrowed_from_a_different_fact_fails():
    """5 exists — in the amlodipine dose, not in the Vitamin D result. Citing f3 and
    stating 5 is a claim the cited fact does not support."""
    ok, _ = verify_phrasing(
        [_line("Reports anxiety.", "f1"), _line("On amlodipine 5 mg.", "f2"),
         _line("Vitamin D low at 5 ng/mL.", "f3")],
        FACTS,
    )
    assert not ok


def test_citing_a_fact_that_was_never_supplied_fails():
    """A citation to something the model was not given is an invention with a footnote."""
    ok, reason = verify_phrasing(
        [_line("Reports anxiety.", "f1"), _line("On amlodipine.", "f2"),
         _line("Vitamin D low.", "f3"), _line("Penicillin allergy.", "f9")],
        FACTS,
    )
    assert not ok
    assert "unknown" in reason


def test_a_line_citing_nothing_fails():
    """Every line must be traceable. An uncited line is prose with no provenance, which is
    exactly what this design exists to prevent."""
    ok, _ = verify_phrasing(
        [_line("Reports anxiety.", "f1"), _line("On amlodipine.", "f2"),
         _line("Vitamin D low.", "f3"), {"text": "Doing well overall.", "fact_ids": []}],
        FACTS,
    )
    assert not ok


def test_a_card_longer_than_the_limit_fails():
    lines = [_line(f"Line {n}", "f1") for n in range(MAX_OVERVIEW_LINES + 1)]
    ok, reason = verify_phrasing(lines, FACTS)
    assert not ok
    assert "lines" in reason


@pytest.mark.parametrize("bad", [None, [], "text", [None], [{"text": "x"}], [{"fact_ids": ["f1"]}]])
def test_malformed_model_output_never_passes(bad):
    ok, _ = verify_phrasing(bad, FACTS)
    assert not ok


# ---- the fallback ----

def test_the_fallback_keeps_every_fact_and_its_label():
    """When phrasing cannot be trusted this is what a doctor reads, so it must lose
    nothing — least of all the labels that say how much a line can be relied on."""
    lines = structured_lines(FACTS)
    flattened = [item for line in lines for item in line["items"]]

    assert {item["fact_id"] for item in flattened} == {"f1", "f2", "f3"}
    assert any(item["label"] == LABEL_PATIENT_REPORTS for item in flattened)


def test_the_fallback_keeps_the_source_of_every_line():
    for line in structured_lines(FACTS):
        for item in line["items"]:
            assert "source_type" in item


def test_an_unverified_medication_is_labelled_not_hidden():
    """A drug the patient is actually taking matters even when this hospital did not
    prescribe it. Hiding it would be the more dangerous choice; presenting it as ours
    would be the other one."""
    facts = FACTS + [{
        "id": "f4", "kind": "medication", "text": "Metformin 500 mg twice daily",
        "label": LABEL_REPORTED_UNVERIFIED, "source_type": "document", "source_id": "d2",
    }]
    medications = [
        item for line in structured_lines(facts) if line["heading"] == "Medications"
        for item in line["items"]
    ]

    unverified = [item for item in medications if item["label"] == LABEL_REPORTED_UNVERIFIED]
    assert len(unverified) == 1
    assert "Metformin" in unverified[0]["text"]


def test_an_empty_record_produces_an_empty_card_not_an_invented_one():
    assert structured_lines([]) == []
    ok, _ = verify_phrasing([_line("Nothing of note.", "f1")], [])
    assert not ok
