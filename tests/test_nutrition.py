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

# A v2 entry also carries real dishes for every region and diet, swaps, habits and a plain
# sentence for the patient; the rules tested here are the same for every part.
MEALS = {
    region: {
        "veg": [{"meal": "breakfast", "dish": "Ragi dosa with coconut chutney"},
                {"meal": "dinner", "dish": "Mushroom masala with roti"}],
        "non_veg": [{"meal": "breakfast", "dish": "Egg bhurji with whole-wheat roti"},
                    {"meal": "lunch", "dish": "Fish curry with rice"}],
    }
    for region in ("north", "south", "east", "west")
}
V2 = {
    "why": "Vitamin D helps your bones and muscles make good use of calcium.",
    "meals": MEALS,
    "swaps": [{"instead_of": "white bread", "try": "whole-wheat roti"}],
    "habits": ["Sit in the morning sun on the balcony with your tea."],
}

GOOD = {
    "nutrient_focus": "Vitamin D, with calcium to use it well.",
    "veg_foods": ["Fortified milk", "Curd", "Paneer", "Sun-dried mushrooms", "Ragi"],
    "non_veg_foods": ["Salmon", "Sardines", "Egg yolk", "Mackerel"],
    "limit": ["Cola drinks"],
    "note": "Pair with morning sunlight where possible.",
    **V2,
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



# ---- v2: real dishes for every region, swaps, habits, a plain sentence for the patient ----

import copy  # noqa: E402

from app.services.nutrition import focus_label, focus_labels  # noqa: E402


def _meals_with(region="south", diet="veg", dishes=None):
    meals = copy.deepcopy(MEALS)
    meals[region][diet] = dishes
    return meals


def test_a_v2_entry_keeps_its_dishes_swaps_habits_and_why():
    entry, reason = check_entry(GOOD)
    assert reason is None
    assert entry["why"] == GOOD["why"]
    assert entry["meals"]["east"]["veg"][0] == {"meal": "breakfast", "dish": "Ragi dosa with coconut chutney"}
    assert entry["swaps"] == [{"instead_of": "white bread", "try": "whole-wheat roti"}]
    assert entry["habits"] == GOOD["habits"]


@pytest.mark.parametrize("dish", ["Egg bhurji with roti", "Chicken tikka with salad", "Fish curry with rice"])
def test_a_vegetarian_dish_never_carries_meat_fish_or_egg(dish):
    entry, reason = check_entry(_with(meals=_meals_with(dishes=[
        {"meal": "breakfast", "dish": "Poha with peanuts"}, {"meal": "lunch", "dish": dish}])))
    assert entry is None and "vegetarian" in reason and dish in reason


@pytest.mark.parametrize("field, value", [
    ("meals", "dish"),
    ("habits", ["Walk for 30 minutes after dinner."]),
    ("swaps", [{"instead_of": "2 rotis", "try": "a bowl of salad"}]),
    ("why", "Aim for 600 IU of Vitamin D every day."),
])
def test_no_digits_in_dishes_swaps_habits_or_the_why(field, value):
    if value == "dish":
        value = _meals_with(dishes=[{"meal": "breakfast", "dish": "2 idlis with sambar"},
                                    {"meal": "lunch", "dish": "Sambar rice"}])
    entry, reason = check_entry(_with(**{field: value}))
    assert entry is None and "number" in reason


def test_household_words_and_nutrient_names_are_fine():
    entry, reason = check_entry(_with(
        why="Omega-3s and Vitamin B12 keep your nerves and heart healthy.",
        habits=["Have a katori of dal with lunch, and fish twice a week."]))
    assert reason is None, reason


def test_supplements_are_not_food_anywhere():
    entry, reason = check_entry(_with(habits=["Take a vitamin D tablet with breakfast."]))
    assert entry is None and "supplements" in reason


@pytest.mark.parametrize("dish, ok", [("Spinach", False), ("Paneer", False), ("Poha", True), ("Khichdi", True)])
def test_a_dish_is_a_dish_not_a_bare_ingredient(dish, ok):
    entry, reason = check_entry(_with(meals=_meals_with(dishes=[
        {"meal": "breakfast", "dish": dish}, {"meal": "dinner", "dish": "Palak dal with rice"}])))
    assert (entry is not None) is ok, reason
    if not ok:
        assert "ingredient" in reason


@pytest.mark.parametrize("dish", ["Chole bhature", "Chicken curry with parotta", "Aloo pakora with chutney",
                                  "Poori bhaji", "Gajar halwa"])
def test_deep_fried_refined_or_sweet_dishes_fail(dish):
    entry, reason = check_entry(_with(meals=_meals_with(dishes=[
        {"meal": "breakfast", "dish": dish}, {"meal": "dinner", "dish": "Palak dal with rice"}])))
    assert entry is None and "deep-fried" in reason


def test_a_food_list_that_is_mostly_seeds_fails():
    entry, reason = check_entry(_with(veg_foods=["Flaxseeds", "Chia seeds", "Pumpkin seeds", "Curd"]))
    assert entry is None and "seeds" in reason
    assert check_entry(_with(veg_foods=["Flaxseeds", "Chia seeds", "Curd"]))[1] is None


def test_every_region_and_diet_needs_real_dishes():
    one = _meals_with(region="west", diet="non_veg", dishes=[{"meal": "lunch", "dish": "Fish curry with rice"}])
    assert "at least" in check_entry(_with(meals=one))[1]
    missing = copy.deepcopy(MEALS)
    del missing["east"]
    assert "east" in check_entry(_with(meals=missing))[1]
    brunch = _meals_with(dishes=[{"meal": "brunch", "dish": "Poha with peanuts"},
                                 {"meal": "dinner", "dish": "Palak dal with rice"}])
    assert "breakfast, lunch, snack, dinner" in check_entry(_with(meals=brunch))[1]


def test_a_swap_must_change_something():
    entry, reason = check_entry(_with(swaps=[{"instead_of": "White rice", "try": "white rice"}]))
    assert entry is None and "swap" in reason


@pytest.mark.parametrize("why", ["", "   ", "Vitamin D matters. " * 15])
def test_the_why_is_one_short_sentence_and_never_missing(why):
    """The patient's handout opens each theme with it; a v2 entry without it is incomplete."""
    entry, reason = check_entry(_with(why=why))
    assert entry is None and "why" in reason


def test_advice_true_of_every_finding_is_left_out_and_the_rest_kept():
    """Live v2 output, after the prompt said not to: the textbook lines go, the entry stays."""
    entry, reason = check_entry(_with(habits=[
        "Include a variety of colorful fruits and vegetables in your meals to boost vitamin intake.",
        "Opt for whole grains over refined grains to support overall health.",
        "Try to have a balanced meal every few hours to maintain energy levels.",
        "Have your tea or coffee between meals, not with them, to help iron absorption.",
    ]))
    assert reason is None
    assert entry["habits"] == ["Have your tea or coffee between meals, not with them, to help iron absorption."]


def test_specific_habits_are_kept():
    habits = ["Spend some time in the morning sun to help your body produce Vitamin D.",
              "Use turmeric and ginger in your cooking for their anti-inflammatory properties.",
              "Opt for steaming, grilling, or roasting instead of frying."]
    assert check_entry(_with(habits=habits))[0]["habits"] == habits


def test_a_habit_is_short():
    long_habit = "Sit in the morning sun on the balcony with your tea, " * 4
    entry, reason = check_entry(_with(habits=[long_habit]))
    assert entry is None and "habit" in reason


def test_the_retry_reason_quotes_what_had_a_digit():
    """The model is told exactly which text broke the rule, so its one retry can fix it."""
    _, reason = check_entry(_with(habits=["Eat 3 meals a day."]))
    assert '"Eat 3 meals a day."' in reason


# ---- conflicts reach the dishes and the swaps ----

def _item(**fields):
    return {"veg_foods": ["Curd"], "non_veg_foods": ["Eggs"], "limit": [], "meals": copy.deepcopy(MEALS),
            "swaps": [], **fields}


def test_a_kidney_result_takes_high_potassium_dishes_and_swaps_out():
    item = _item(meals=_meals_with(region="north", dishes=[
        {"meal": "lunch", "dish": "Palak paneer with roti"}, {"meal": "dinner", "dish": "Lauki chana dal with rice"}]),
        swaps=[{"instead_of": "biscuits", "try": "a banana"}, {"instead_of": "white bread", "try": "whole-wheat roti"}])
    [cleaned], cautions = apply_conflicts([item], {("Creatinine", "high")})
    assert [m["dish"] for m in cleaned["meals"]["north"]["veg"]] == ["Lauki chana dal with rice"]
    assert cleaned["swaps"] == [{"instead_of": "white bread", "try": "whole-wheat roti"}]
    assert CAUTION_KIDNEY in cautions


def test_high_sugar_takes_sweet_dishes_out():
    item = _item(meals=_meals_with(region="west", dishes=[
        {"meal": "snack", "dish": "Dates and jaggery laddoo"}, {"meal": "lunch", "dish": "Bajra roti with methi"}]))
    [cleaned], _ = apply_conflicts([item], {("HbA1c", "high")})
    assert [m["dish"] for m in cleaned["meals"]["west"]["veg"]] == ["Bajra roti with methi"]


def test_high_uric_acid_takes_purine_rich_non_veg_dishes_out_only():
    meals = copy.deepcopy(MEALS)
    meals["east"]["non_veg"] = [{"meal": "lunch", "dish": "Prawn malai curry with rice"},
                                {"meal": "dinner", "dish": "Chicken stew with rice"}]
    [cleaned], cautions = apply_conflicts([_item(meals=meals)], {("Uric Acid", "high")})
    assert [m["dish"] for m in cleaned["meals"]["east"]["non_veg"]] == ["Chicken stew with rice"]
    assert cleaned["meals"]["east"]["veg"] == MEALS["east"]["veg"]
    assert CAUTION_URIC_ACID in cautions


# ---- the heading: what the guidance is for ----

@pytest.mark.parametrize("key, label", [
    (("finding", "Vitamin D", "low"), "Low Vitamin D"),
    (("finding", "hs-CRP", "high"), "High hs-CRP"),
    (("finding", "Blood lipids", "abnormal"), "Abnormal cholesterol & lipids"),
    (("finding", "Kidney function", "abnormal"), "Abnormal kidney function"),
    (("symptom", "joint or back pain", "present"), "Joint or back pain"),
])
def test_each_topic_is_named_as_a_doctor_would(key, label):
    assert focus_label(*key) == label


def test_findings_come_before_symptoms_in_the_pages_theme_order():
    keys = [("symptom", "fatigue", "present"), ("finding", "Vitamin D", "low"),
            ("finding", "hs-CRP", "high"), ("finding", "Blood lipids", "abnormal")]
    assert focus_labels(keys) == ["High hs-CRP", "Abnormal cholesterol & lipids", "Low Vitamin D", "Fatigue"]
