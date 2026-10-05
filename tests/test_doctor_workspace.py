"""Unit tests for app/services/doctor_workspace.py — the pure read-model logic behind the
AI doctor workspace (ranking, lane grouping, verification progress, activity headline,
patient-brief source selection, Insert-from-plan parsing).

No database and no model call: every function under test is deterministic over rows the
caller has already fetched and already authorized, which is exactly why this file can
assert the awkward cases exhaustively.

Two tests here are safety tests rather than behaviour tests, and must not be relaxed:
  - test_an_unsigned_draft_is_never_compiled_into_a_brief (plan §5: AI output never
    reaches the record or a doctor's summary without a signature)
  - test_insert_from_plan_copies_verbatim_and_validates_nothing (plan §5: AI never
    generates dosing, interaction or formulary advice)
"""
from __future__ import annotations

from app.services.doctor_workspace import (
    BULK_DRAFT_MAX_ITEMS,
    LANE_NEEDS_ATTENTION,
    LANE_NOT_DRAFTED,
    LANE_QUICK_REVIEW,
    LANES,
    SOAP_SECTIONS,
    explain_item_status,
    extract_plan_medication_lines,
    flag_weight,
    group_into_lanes,
    lane_for_item,
    rank_pending_items,
    summarize_activity,
    verification_progress,
)


def _item(consultation_id="c1", **overrides) -> dict:
    """A pending-queue row in exactly the shape soap_notes._review_row_to_dict produces."""
    base = {
        "consultation_id": consultation_id,
        "item_type": "draft",
        "appointment_start": "2026-09-21T13:00:00",
        "is_stale": False,
        "is_edited": False,
        "low_quality_transcript": False,
        "low_confidence_fields": 0,
    }
    base.update(overrides)
    return base


# ---- Ranking (plan §4.2) ----

def test_blocked_items_rank_above_everything_else():
    blocked = _item("blocked", is_stale=True, appointment_start="2026-09-22T09:00:00")
    heavily_flagged = _item("flagged", low_confidence_fields=4, appointment_start="2026-01-01T09:00:00")

    ranked = rank_pending_items([heavily_flagged, blocked])

    # Blocked wins even though the other item is older AND more flagged: a stale note
    # cannot be signed at all until it is regenerated.
    assert [i["consultation_id"] for i in ranked] == ["blocked", "flagged"]


def test_more_flags_rank_above_fewer_among_drafts():
    ranked = rank_pending_items([
        _item("one_flag", low_confidence_fields=1),
        _item("three_flags", low_confidence_fields=3),
        _item("no_flags", low_confidence_fields=0),
    ])
    assert [i["consultation_id"] for i in ranked] == ["three_flags", "one_flag", "no_flags"]


def test_a_lower_quality_transcript_counts_toward_the_flag_weight():
    # Documents the weighting rule: a weak transcript outranks a single flagged field,
    # because it casts doubt over every section at once rather than just one.
    assert flag_weight(_item(low_quality_transcript=True)) > flag_weight(_item(low_confidence_fields=1))
    assert flag_weight(_item(low_quality_transcript=True)) < flag_weight(_item(low_confidence_fields=3))


def test_oldest_waits_first_when_flags_are_equal():
    ranked = rank_pending_items([
        _item("newer", appointment_start="2026-09-22T09:00:00"),
        _item("older", appointment_start="2026-09-20T09:00:00"),
    ])
    assert [i["consultation_id"] for i in ranked] == ["older", "newer"]


def test_undrafted_transcripts_rank_last_among_equals():
    ranked = rank_pending_items([
        _item("undrafted", item_type="not_generated"),
        _item("drafted", item_type="draft"),
    ])
    assert [i["consultation_id"] for i in ranked] == ["drafted", "undrafted"]


def test_ranking_is_a_total_order_and_does_not_reshuffle():
    """Two items identical on every ranking signal must still come back in a stable,
    repeatable order — a 'prioritised' list that reorders itself between loads is worse
    than an unsorted one."""
    a, b = _item("aaa"), _item("bbb")
    assert rank_pending_items([a, b]) == rank_pending_items([b, a])
    assert [i["consultation_id"] for i in rank_pending_items([b, a])] == ["aaa", "bbb"]


def test_ranking_does_not_mutate_its_input():
    items = [_item("second", appointment_start="2026-09-22T09:00:00"), _item("first")]
    original = list(items)
    rank_pending_items(items)
    assert items == original


def test_ranking_tolerates_missing_and_malformed_fields():
    # A malformed row must never break the whole queue — same rationale as
    # soap_notes._low_confidence_count tolerating a non-dict.
    ranked = rank_pending_items([
        {"consultation_id": "sparse"},
        _item("normal"),
        {"consultation_id": "bad_flags", "low_confidence_fields": "three"},
        {"consultation_id": "negative", "low_confidence_fields": -5},
    ])
    assert len(ranked) == 4
    assert flag_weight({"low_confidence_fields": "three"}) == 0
    assert flag_weight({"low_confidence_fields": -5}) == 0


def test_an_item_with_no_appointment_time_sorts_last_rather_than_raising():
    ranked = rank_pending_items([
        {"consultation_id": "undated", "appointment_start": None},
        _item("dated", appointment_start="2026-09-20T09:00:00"),
    ])
    assert [i["consultation_id"] for i in ranked] == ["dated", "undated"]


def test_ranking_an_empty_queue_returns_empty():
    assert rank_pending_items([]) == []


# ---- Lanes (plan §4.5) ----

def test_blocked_and_low_quality_items_go_to_needs_attention():
    assert lane_for_item(_item(is_stale=True)) == LANE_NEEDS_ATTENTION
    assert lane_for_item(_item(low_quality_transcript=True)) == LANE_NEEDS_ATTENTION


def test_a_plain_draft_is_a_quick_review():
    assert lane_for_item(_item()) == LANE_QUICK_REVIEW


def test_an_undrafted_transcript_is_not_drafted_yet():
    assert lane_for_item(_item(item_type="not_generated")) == LANE_NOT_DRAFTED


def test_an_item_qualifying_for_two_lanes_lands_in_the_more_serious_one():
    """A blocked item that also has no note is 'needs attention', not 'not drafted' —
    otherwise the most serious item in the queue would be filed under the calmest lane."""
    both = _item(is_stale=True, item_type="not_generated")
    assert lane_for_item(both) == LANE_NEEDS_ATTENTION


def test_grouping_always_returns_all_three_lanes_even_when_empty():
    lanes = group_into_lanes([])
    assert set(lanes) == set(LANES)
    assert all(rows == [] for rows in lanes.values())


def test_each_item_lands_in_exactly_one_lane():
    items = [
        _item("a", is_stale=True),
        _item("b", low_quality_transcript=True),
        _item("c"),
        _item("d", item_type="not_generated"),
    ]
    lanes = group_into_lanes(items)
    placed = [i["consultation_id"] for rows in lanes.values() for i in rows]
    assert sorted(placed) == ["a", "b", "c", "d"]
    assert len(placed) == len(set(placed))


def test_lanes_are_internally_ranked():
    lanes = group_into_lanes([
        _item("light", low_confidence_fields=1),
        _item("heavy", low_confidence_fields=3),
    ])
    assert [i["consultation_id"] for i in lanes[LANE_QUICK_REVIEW]] == ["heavy", "light"]


# ---- Status explanation (plan §4.5) ----

def test_explanation_leads_with_the_blocking_reason():
    assert "regenerate" in explain_item_status(_item(is_stale=True)).lower()


def test_explanation_covers_every_pending_state():
    assert "ready to draft" in explain_item_status(_item(item_type="not_generated")).lower()
    assert "lower-quality" in explain_item_status(_item(low_quality_transcript=True)).lower()
    assert "1 section flagged" in explain_item_status(_item(low_confidence_fields=1))
    assert "2 sections flagged" in explain_item_status(_item(low_confidence_fields=2))
    assert "edits in progress" in explain_item_status(_item(is_edited=True)).lower()
    assert "cited" in explain_item_status(_item()).lower()


def test_explanation_never_describes_the_patient_or_anything_clinical():
    """These strings sit on a dashboard card. They describe the state of the
    DOCUMENTATION, never the person or their condition."""
    for item in [_item(is_stale=True), _item(low_confidence_fields=2), _item(item_type="not_generated")]:
        text = explain_item_status(item).lower()
        for forbidden in ("patient", "diagnos", "urgent", "severe", "critical", "risk"):
            assert forbidden not in text


# ---- Verification progress (plan §4.6) ----

def test_progress_counts_from_zero_to_four():
    assert verification_progress([])["verified_count"] == 0
    assert verification_progress([])["percent"] == 0
    assert verification_progress(["subjective"])["verified_count"] == 1
    full = verification_progress(list(SOAP_SECTIONS))
    assert full["verified_count"] == 4
    assert full["percent"] == 100
    assert full["complete"] is True


def test_progress_cannot_exceed_four_however_the_rows_look():
    """A duplicate or unknown section recorded against a note must never push the bar
    past 100%."""
    progress = verification_progress(
        ["subjective", "subjective", "objective", "not_a_section", "", None]
    )
    assert progress["verified_count"] == 2
    assert progress["percent"] == 50
    assert progress["complete"] is False


def test_unresolved_flags_are_reported_for_the_sign_warning():
    note = {"confidence_flags": {"subjective": True, "plan": True, "objective": False}}
    progress = verification_progress(["subjective"], note)
    # 'subjective' was flagged but the doctor has now verified it, so only 'plan' remains.
    assert progress["unresolved_flagged_sections"] == ["plan"]


def test_unresolved_flags_tolerate_a_malformed_flags_value():
    assert verification_progress([], {"confidence_flags": "nonsense"})["unresolved_flagged_sections"] == []
    assert verification_progress([], {})["unresolved_flagged_sections"] == []
    assert verification_progress([], None)["unresolved_flagged_sections"] == []


# ---- Activity headline (plan §4.1) ----

def test_headline_reports_what_actually_happened():
    headline = summarize_activity(
        {"notes_drafted": 3, "documents_summarized": 2, "awaiting_signature": 4}
    )
    assert "3 notes drafted" in headline
    assert "2 documents summarised" in headline
    assert "4 items wait on your sign-off" in headline


def test_headline_is_honest_when_nothing_happened():
    """It must not claim activity that did not occur — the demo's cheerful copy is not a
    default to fall back on."""
    assert summarize_activity({}) == "No new AI activity since you were last here."
    quiet = summarize_activity({"notes_drafted": 0, "documents_summarized": 0, "awaiting_signature": 2})
    assert "No new AI activity" in quiet
    assert "2 items" in quiet


def test_headline_uses_singular_forms_correctly():
    headline = summarize_activity(
        {"notes_drafted": 1, "documents_summarized": 1, "awaiting_signature": 1}
    )
    assert "1 note drafted" in headline
    assert "1 document summarised" in headline
    assert "1 item waits" in headline or "1 item wait" in headline


def test_headline_says_so_when_nothing_awaits_signature():
    assert "Nothing is waiting" in summarize_activity({"notes_drafted": 2, "awaiting_signature": 0})


# ---- Insert from plan (plan §4.10) ----

def test_extracts_list_style_medication_lines():
    plan = """Medications:
- Amlodipine 5 mg once daily
- Atorvastatin 20 mg at night
Review in six weeks.
"""
    assert extract_plan_medication_lines(plan) == [
        "Amlodipine 5 mg once daily",
        "Atorvastatin 20 mg at night",
    ]


def test_extracts_unmarked_lines_that_carry_a_dose():
    assert extract_plan_medication_lines("Metformin 500mg BD") == ["Metformin 500mg BD"]


def test_headings_and_prose_are_not_treated_as_medications():
    plan = """Plan:
Medications
Continue lifestyle advice and follow up in clinic.
1. Ramipril 2.5 mg daily
"""
    assert extract_plan_medication_lines(plan) == ["Ramipril 2.5 mg daily"]


def test_insert_from_plan_copies_verbatim_and_validates_nothing():
    """SAFETY (plan §5). This is a copy, not a suggestion. A line the doctor signed with an
    implausible dose comes back EXACTLY as written — unaltered, uncorrected, unflagged.
    Anything else would be this application generating dosing advice, which it must never
    do, and would also silently rewrite a signed clinical record."""
    plan = "- Amlodipine 500000 mg twice daily"
    out = extract_plan_medication_lines(plan)
    assert out == ["Amlodipine 500000 mg twice daily"]
    # No warning, no correction, no annotation, no extra lines invented.
    assert len(out) == 1


def test_duplicate_lines_are_copied_once():
    plan = "- Amlodipine 5 mg daily\n- amlodipine 5 MG daily\n"
    assert extract_plan_medication_lines(plan) == ["Amlodipine 5 mg daily"]


def test_extraction_is_bounded():
    plan = "\n".join(f"- Drug{i} {i} mg daily" for i in range(100))
    assert len(extract_plan_medication_lines(plan)) == 20
    assert len(extract_plan_medication_lines(plan, limit=5)) == 5


def test_extraction_handles_empty_and_malformed_input():
    assert extract_plan_medication_lines(None) == []
    assert extract_plan_medication_lines("") == []
    assert extract_plan_medication_lines("   \n\n  ") == []
    assert extract_plan_medication_lines(12345) == []
    assert extract_plan_medication_lines("Follow up in six weeks.") == []


def test_a_bare_bullet_produces_no_line():
    assert extract_plan_medication_lines("- \n-\n") == []


def test_bulk_draft_is_capped():
    """The cap is the whole point of the constant — an uncapped bulk draft is N LLM calls
    triggered by one click."""
    assert isinstance(BULK_DRAFT_MAX_ITEMS, int)
    assert 0 < BULK_DRAFT_MAX_ITEMS <= 25


# ---- Insert from plan: medicines AND the tests or reports the plan advises ----

from app.services.doctor_workspace import extract_plan_items  # noqa: E402


def test_tests_and_reports_are_copied_under_their_own_list():
    """The prescription used to receive only medication lines: a plan that advised an MRI
    or blood tests lost them."""
    plan = """- Tab Gabapentin NT 400/10 BD x 15 days
- Cap Rabeprazole 20 mg OD
- Serum Vitamin B12 and Vitamin D levels
- MRI lumbar spine if pain persists
Physiotherapy for back strengthening.
"""
    items = extract_plan_items(plan)
    # Unmarked prose with no dose and no test ("Physiotherapy ...") stays in the plan.
    assert items["medications"] == ["Tab Gabapentin NT 400/10 BD x 15 days", "Cap Rabeprazole 20 mg OD"]
    assert items["tests"] == ["Serum Vitamin B12 and Vitamin D levels", "MRI lumbar spine if pain persists"]


def test_prose_plans_are_read_sentence_by_sentence():
    plan = ("Continue sumatriptan 50 mg as needed. Recheck blood pressure in two weeks. "
            "Advised CBC, LFT and lipid profile. Bring previous reports at the next visit.")
    items = extract_plan_items(plan)
    assert items["medications"] == ["Continue sumatriptan 50 mg as needed."]
    assert items["tests"] == ["Advised CBC, LFT and lipid profile.", "Bring previous reports at the next visit."]


def test_a_dose_makes_it_a_medicine_even_when_it_names_a_test_word():
    items = extract_plan_items("- Vitamin D3 60000 IU weekly\n- Serum vitamin D level after 8 weeks")
    assert items["medications"] == ["Vitamin D3 60000 IU weekly"]
    assert items["tests"] == ["Serum vitamin D level after 8 weeks"]


def test_tests_are_copied_verbatim_and_bounded():
    plan = "\n".join(f"- X-ray view {i}" for i in range(40))
    items = extract_plan_items(plan, limit=5)
    assert items["tests"] == [f"X-ray view {i}" for i in range(5)]
    assert extract_plan_items("- MRI  brain  with contrast")["tests"] == ["MRI  brain  with contrast"]


def test_words_that_merely_contain_a_test_name_do_not_count():
    """Whole words only: "act", "fact", "echoing" are not tests."""
    assert extract_plan_items("Act on the advice given. The fact is noted.")["tests"] == []


def test_a_follow_up_that_mentions_a_test_is_not_a_test():
    """Seen on the server: the follow-up sentence was copied under "Tests / reports advised"
    because it mentions the MRI it follows."""
    plan = ("Order MRI of the lumbosacral spine to identify cause. "
            "Follow-up in neurology clinic after MRI or sooner if symptoms worsen.")
    assert extract_plan_items(plan) == {
        "medications": [], "tests": ["Order MRI of the lumbosacral spine to identify cause."]}


def test_follow_up_review_and_referral_lines_are_neither_list():
    plan = """- Review with MRI report in 2 weeks
- Follow up twice weekly for dressing
- Refer to neurology for nerve conduction study
- Return if fever persists; continue paracetamol 500 mg SOS
Review in two weeks. See me again after the reports."""
    items = extract_plan_items(plan)
    # A strength still makes it a medicine, even inside a follow-up line.
    assert items["medications"] == ["Return if fever persists; continue paracetamol 500 mg SOS"]
    assert items["tests"] == []


def test_prose_that_only_mentions_a_test_is_not_an_order():
    plan = ("Discussed the MRI findings with the patient. Explained the report. "
            "MRI lumbar spine. The ECG is pending. Repeat lipid profile after 6 weeks.")
    assert extract_plan_items(plan)["tests"] == [
        "MRI lumbar spine.", "The ECG is pending.", "Repeat lipid profile after 6 weeks."]


def test_a_listed_test_needs_no_ordering_word():
    assert extract_plan_items("- Fasting lipid profile and HbA1c\n- ECG")["tests"] == [
        "Fasting lipid profile and HbA1c", "ECG"]


def test_plan_items_handle_empty_input():
    assert extract_plan_items(None) == {"medications": [], "tests": []}
    assert extract_plan_items("Follow up in six weeks.") == {"medications": [], "tests": []}
