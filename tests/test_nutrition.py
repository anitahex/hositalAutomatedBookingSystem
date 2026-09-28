"""The AI nutritionist's rules, all of which are code, not the model.

Pure — no database, no model. What is checked here is what makes model-written guidance
safe to show: the vegetarian list really is vegetarian, it is food and not supplements or
doses, it carries no invented numbers, symptoms are read without their negations, and one
result's guidance never recommends what another of the patient's results rules out.
"""
from __future__ import annotations

import pytest

from app.services.nutrition import (
    CAUTION_KIDNEY,
    CAUTION_SUGAR,
    CAUTION_URIC_ACID,
    DIRECTION_ABNORMAL,
    _term_for,
    apply_conflicts,
    check_entry,
    describe_term,
    symptoms_in,
)

GOOD = {
    "nutrient_focus": "Vitamin D, with calcium to use it well.",
    "veg_foods": ["Fortified milk", "Curd", "Paneer", "Sun-dried mushrooms", "Ragi"],
    "non_veg_foods": ["Salmon", "Sardines", "Egg yolk", "Mackerel"],
    "limit": ["Cola drinks"],
    "note": "Pair with morning sunlight where possible.",
}


def _with(**changes):
    return {**GOOD, **changes}


# ---- check_entry ----

def test_a_good_entry_passes_unchanged():
    entry, reason = check_entry(GOOD)
    assert reason is None
    assert entry["veg_foods"] == GOOD["veg_foods"]


@pytest.mark.parametrize("food", ["Boiled eggs", "Egg", "Chicken soup", "Fish curry", "Prawns",
                                  "Mutton keema", "Cod liver oil", "Goat liver", "Kidney"])
def test_the_vegetarian_list_never_carries_meat_fish_or_egg(food):
    entry, reason = check_entry(_with(veg_foods=["Curd", food]))
    assert entry is None and "vegetarian" in reason


@pytest.mark.parametrize("food", ["Eggplant", "Kidney beans", "Rajma (kidney beans)", "Brinjal"])
def test_vegetables_that_look_like_non_veg_words_are_allowed(food):
    entry, reason = check_entry(_with(veg_foods=[food]))
    assert reason is None, reason


@pytest.mark.parametrize("field, value", [
    ("veg_foods", ["2 glasses of milk"]),
    ("nutrient_focus", "Aim for 600 IU of Vitamin D."),
    ("note", "Eat 3 times a day."),
    ("limit", ["More than 1 cup of tea"]),
])
def test_no_numbers_anywhere(field, value):
    entry, reason = check_entry(_with(**{field: value}))
    assert entry is None and "number" in reason


@pytest.mark.parametrize("field, value", [
    ("veg_foods", ["Vitamin D supplement"]),
    ("non_veg_foods", ["Fish oil capsules"]),
    ("note", "Ask about a multivitamin tablet."),
    ("nutrient_focus", "Vitamin B12 injection may help."),
])
def test_food_only_never_supplements_or_medicines(field, value):
    entry, reason = check_entry(_with(**{field: value}))
    assert entry is None


def test_lists_are_bounded_and_deduplicated():
    entry, _ = check_entry(_with(veg_foods=[f"Food {c}" for c in "ABCDEFGHIJ"] + ["Food A"]))
    assert len(entry["veg_foods"]) == 8
    entry, _ = check_entry(_with(veg_foods=["Curd", "curd", " Curd. "]))
    assert entry["veg_foods"] == ["Curd"]


@pytest.mark.parametrize("bad", [
    None, "text", [], _with(veg_foods="milk"), _with(veg_foods=[1, 2]),
    _with(nutrient_focus=""), _with(veg_foods=[], non_veg_foods=[]),
    _with(veg_foods=["A very long description of a meal that is really a sentence, not a food name"]),
])
def test_malformed_entries_are_rejected(bad):
    entry, reason = check_entry(bad)
    assert entry is None and reason


# ---- symptoms from the booking note ----

def test_diet_relevant_symptoms_are_found():
    note = "**Symptoms:** lower back pain for 3 months, constipation, feeling tired."
    assert symptoms_in(note) == ["constipation", "fatigue", "joint or back pain"]


@pytest.mark.parametrize("note", [
    "No nausea or vomiting.",
    "Denies constipation.",
    "Patient reports no acidity.",
    "Without bloating.",
])
def test_a_negated_symptom_does_not_count(note):
    assert symptoms_in(note) == []


def test_a_symptom_without_a_dietary_angle_gets_nothing():
    assert symptoms_in("Fracture of the left wrist after a fall; rash on arm.") == []


def test_gastric_is_not_gas():
    assert "bloating" not in symptoms_in("History of gastric surgery.")


# ---- grouping and what the model is told ----

def test_lipid_results_share_one_piece_of_guidance():
    terms = {_term_for(name, flag) for name, flag in [
        ("Total Cholesterol", "high"), ("Triglycerides", "high"), ("HDL Cholesterol", "low"),
        ("LDL Cholesterol", "high"), ("Total Cholesterol HDL Ratio", "high"),
    ]}
    assert terms == {("Blood lipids", DIRECTION_ABNORMAL)}
    assert _term_for("Vitamin D", "low") == ("Vitamin D", "low")


def test_the_model_is_told_the_term_and_nothing_about_a_patient():
    text = describe_term("finding", "Vitamin D", "low")
    assert text == "Lab finding: Vitamin D is low. Food guidance for it."
    assert not any(ch.isdigit() for ch in text)


# ---- conflicts between results ----

ITEM = {"term": "Vitamin D", "veg_foods": ["Banana", "Spinach", "Curd", "Soy chunks (protein)", "Orange juice"],
        "non_veg_foods": ["Mutton liver", "Prawns", "Eggs", "Chicken"], "limit": []}


def test_kidney_results_remove_high_potassium_and_high_protein_foods():
    [item], cautions = apply_conflicts([ITEM], {("Creatinine", "high")})
    # Orange juice goes too: orange is high in potassium.
    assert item["veg_foods"] == ["Curd"]
    assert item["non_veg_foods"] == ITEM["non_veg_foods"]
    assert cautions == [CAUTION_KIDNEY]


def test_high_uric_acid_removes_purine_rich_non_veg_only():
    [item], cautions = apply_conflicts([ITEM], {("Uric Acid", "high")})
    assert item["non_veg_foods"] == ["Eggs", "Chicken"]
    assert item["veg_foods"] == ITEM["veg_foods"]
    assert cautions == [CAUTION_URIC_ACID]


def test_high_blood_sugar_removes_juices_and_sweets():
    [item], cautions = apply_conflicts([ITEM], {("HbA1c", "high")})
    assert "Orange juice" not in item["veg_foods"]
    assert cautions == [CAUTION_SUGAR]


def test_no_conflict_leaves_the_guidance_alone():
    [item], cautions = apply_conflicts([ITEM], {("Vitamin D", "low")})
    assert item == ITEM and cautions == []


def test_the_same_results_always_give_the_same_output():
    flagged = {("Creatinine", "high"), ("Uric Acid", "high"), ("HbA1c", "high")}
    assert apply_conflicts([ITEM], flagged) == apply_conflicts([ITEM], set(flagged))


@pytest.mark.parametrize("text", ["Vitamin B12", "Omega-3 fats", "omega 3", "Vitamin D3", "B6 and folate"])
def test_nutrient_names_with_digits_are_names_not_numbers(text):
    """The first real run rejected every entry mentioning B12 or omega-3 as "a number"."""
    entry, reason = check_entry(_with(nutrient_focus=f"{text} for energy.", veg_foods=["Curd", f"{text}-rich seeds"]))
    assert reason is None, reason


@pytest.mark.parametrize("text", ["B12 of 200", "3 servings of omega-3 fish", "Vitamin D3 1000"])
def test_a_real_amount_next_to_a_nutrient_name_still_fails(text):
    entry, reason = check_entry(_with(note=text))
    assert entry is None and "number" in reason
