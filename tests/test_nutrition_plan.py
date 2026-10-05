"""The AI nutritionist, organised: themes, foods that help most, go easy on, a sample day,
and which themes were discussed.

The page only groups and counts foods the checked guidance already holds, so the rules are:
nothing appears that no item listed, the vegetarian page never shows meat, fish or egg, the
same guidance always makes the same page, and a discussion is shown with who and when.
"""
from __future__ import annotations

import uuid

import pytest

from app.services import nutrition_plan as np_


def _item(term, veg, non_veg, limit=(), note="", kind="finding", because=None):
    return {
        "kind": kind, "term": term, "direction": "low",
        "veg_foods": list(veg), "non_veg_foods": list(non_veg), "limit": list(limit), "note": note,
        "because": because if because is not None else [{
            "canonical_name": term, "printed_name": term, "value_text": "13.8 ng/mL", "flag": "low",
            "clinical_date": "2026-09-20", "page_no": 2, "document_id": "d1", "document_type": "blood_report"}],
    }


GUIDANCE = {"items": [
    _item("Vitamin D", ["paneer", "mushrooms", "milk", "almonds"], ["salmon", "eggs", "almonds"],
          limit=["fried foods"], note="Sit in the morning sun."),
    _item("Vitamin B12", ["curd", "paneer", "almonds"], ["eggs", "chicken", "curd"], limit=["alcohol"]),
    _item("ESR", ["turmeric", "Almonds", "spinach", "oats"], ["sardines", "turmeric", "spinach"],
          limit=["fried foods", "sugary drinks"]),
    _item("joint or back pain", ["turmeric", "ginger", "walnuts"], ["salmon", "turmeric"], kind="symptom",
          because=[{"symptom": "joint or back pain"}]),
]}


# ---- themes ----

def test_each_result_and_symptom_lands_in_its_theme():
    themes = {t["id"]: t for t in np_.organize(GUIDANCE)["themes"]}
    assert set(themes) == {"inflammation", "vitamins"}
    assert themes["vitamins"]["terms"] == ["Vitamin D", "Vitamin B12"]
    assert themes["inflammation"]["terms"] == ["ESR", "joint or back pain"]
    assert themes["inflammation"]["symptoms"] == ["joint or back pain"]
    assert [r["canonical_name"] for r in themes["inflammation"]["results"]] == ["ESR"]


def test_themes_come_in_a_fixed_order():
    ids = [t["id"] for t in np_.organize(GUIDANCE)["themes"]]
    assert ids == ["inflammation", "vitamins"]


def test_an_unknown_term_goes_to_other_results():
    assert np_.theme_for("Serum Zinc") == "other"


def test_a_theme_keeps_the_evidence_and_the_tips():
    vitamins = next(t for t in np_.organize(GUIDANCE)["themes"] if t["id"] == "vitamins")
    assert vitamins["results"][0]["value_text"] == "13.8 ng/mL"
    assert vitamins["tips"] == ["Sit in the morning sun."]
    assert vitamins["go_easy"] == ["Fried foods", "Alcohol"]


# ---- foods that help most ----

def test_foods_are_ranked_by_how_many_findings_list_them():
    top = np_.organize(GUIDANCE)["top_foods"]["veg"]
    assert (top[0]["food"], top[0]["count"]) == ("Almonds", 3)  # "Almonds" counted with "almonds"
    assert ("Turmeric", 2) in [(e["food"], e["count"]) for e in top]


def test_nothing_is_ranked_that_no_item_listed():
    listed = {np_.food_key(f) for item in GUIDANCE["items"] for f in item["veg_foods"]}
    assert {np_.food_key(e["food"]) for e in np_.organize(GUIDANCE)["top_foods"]["veg"]} <= listed


def test_go_easy_counts_the_themes_a_food_comes_from():
    easy = {e["food"]: e["themes"] for e in np_.organize(GUIDANCE)["go_easy"]}
    assert easy["Fried foods"] == 2 and easy["Alcohol"] == 1


# ---- the sample day ----

@pytest.mark.parametrize("food, category", [
    ("oats", "breakfast"), ("pumpkin seeds", "nuts"), ("pumpkin", "vegetable"),
    ("sweet potato", "vegetable"), ("Paneer (low-fat)", "protein_veg"), ("eggs", "protein_non_veg"),
    ("green tea", "drink"), ("amaranth leaves", None),
])
def test_food_categories(food, category):
    assert np_.food_category(food) == category


def test_the_sample_day_uses_only_foods_on_the_page_each_once():
    plan = np_.organize(GUIDANCE)
    for diet in np_.DIETS:
        listed = {np_.food_key(e["food"]) for e in plan["top_foods"][diet]}
        placed = [np_.food_key(f) for meal in plan["sample_day"][diet] for f in meal["foods"]]
        assert set(placed) <= listed
        assert len(placed) == len(set(placed))


def test_the_vegetarian_day_never_places_meat_fish_or_egg():
    from app.services.nutrition import _NON_VEG

    guidance = {"items": [_item("Vitamin D", ["paneer", "oats", "eggs"], ["eggs", "chicken"])]}
    for meal in np_.organize(guidance)["sample_day"]["veg"]:
        assert not any(_NON_VEG.search(food) for food in meal["foods"])


def test_a_meal_says_which_themes_its_foods_help():
    plan = np_.organize(GUIDANCE)
    morning = next(m for m in plan["sample_day"]["veg"] if m["meal"] == "morning")
    assert "Oats" in morning["foods"]
    assert "Inflammation & pain" in morning["helps"]


def test_the_same_guidance_makes_the_same_page():
    assert np_.organize(GUIDANCE) == np_.organize(GUIDANCE)


def test_discussions_are_attached_to_their_theme():
    discussed = {"vitamins": {"name": "Dr. A", "at": "2026-09-29T10:00:00", "is_me": False}}
    themes = {t["id"]: t for t in np_.organize(GUIDANCE, discussed)["themes"]}
    assert themes["vitamins"]["discussed"]["name"] == "Dr. A"
    assert themes["inflammation"]["discussed"] is None


# ---- discussions and handouts, against a real database ----

def _skip_if_no_database():
    from app.db.connection import connect_db

    try:
        with connect_db() as conn:
            np_.ensure_discussion_schema(conn)
            np_.ensure_handout_schema(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM nutrition_discussions LIMIT 0")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


@pytest.fixture
def people():
    _skip_if_no_database()
    from app.db.connection import connect_db

    ids = {"patient": f"nutri-{uuid.uuid4().hex[:8]}", "ortho": str(uuid.uuid4()), "psych": str(uuid.uuid4())}
    with connect_db() as conn:
        with conn.cursor() as cur:
            for key, name, department in (("ortho", "Dr. Nutri Ortho", "Orthopedics"),
                                          ("psych", "Dr. Nutri Psych", "Psychiatry")):
                cur.execute("INSERT INTO doctors (doctor_id, name, department, experience_years, is_active) "
                            "VALUES (%s, %s, %s, 5, TRUE)", (ids[key], name, department))
        conn.commit()
    try:
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM nutrition_discussions WHERE patient_id = %s", (ids["patient"],))
                cur.execute("DELETE FROM nutrition_handouts WHERE patient_id = %s", (ids["patient"],))
                cur.execute("DELETE FROM consult_audit_log WHERE metadata->>'patient_id' = %s", (ids["patient"],))
                cur.execute("DELETE FROM doctors WHERE doctor_id = ANY(%s::uuid[])", ([ids["ortho"], ids["psych"]],))
            conn.commit()


def _audit_actions(patient_id):
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT action_type, metadata FROM consult_audit_log WHERE metadata->>'patient_id' = %s "
                        "ORDER BY created_at", (patient_id,))
            rows = cur.fetchall()
        conn.commit()
    return rows


def test_a_discussion_is_shown_with_who_and_when_and_audited(people):
    np_.mark_discussed(people["ortho"], people["patient"], "vitamins", None, True)
    seen_by_other = np_.discussions_for(people["patient"], str(uuid.uuid4()), "Orthopedics")
    assert seen_by_other["vitamins"]["name"] == "Dr. Nutri Ortho"
    assert seen_by_other["vitamins"]["is_me"] is False and seen_by_other["vitamins"]["at"]
    assert np_.discussions_for(people["patient"], people["ortho"], "Orthopedics")["vitamins"]["is_me"] is True
    [(action, metadata)] = _audit_actions(people["patient"])
    assert action == "nutrition_theme_discussed" and metadata["theme_title"] == "Vitamins & blood"


def test_a_doctor_can_withdraw_only_their_own_mark(people):
    np_.mark_discussed(people["ortho"], people["patient"], "vitamins", None, True)
    np_.mark_discussed(people["psych"], people["patient"], "vitamins", None, False)  # not theirs: no-op
    assert "vitamins" in np_.discussions_for(people["patient"], people["psych"], "Psychiatry")
    np_.mark_discussed(people["ortho"], people["patient"], "vitamins", None, False)
    assert np_.discussions_for(people["patient"], people["ortho"], "Orthopedics") == {}
    assert [a for a, _ in _audit_actions(people["patient"])] == [
        "nutrition_theme_discussed", "nutrition_theme_discussion_withdrawn"]


def test_a_discusser_in_a_restricted_specialty_is_not_named_outside_it(people):
    np_.mark_discussed(people["psych"], people["patient"], "stress", None, True)
    seen = np_.discussions_for(people["patient"], people["ortho"], "Orthopedics")["stress"]
    assert seen["name"] != "Dr. Nutri Psych" and seen["department"] == "restricted specialty"


def test_an_unknown_theme_is_refused(people):
    with pytest.raises(ValueError):
        np_.mark_discussed(people["ortho"], people["patient"], "not-a-theme", None, True)


def test_a_handout_is_recorded_with_what_it_covered(people):
    content = np_.build_handout(np_.organize(GUIDANCE), "non_veg")
    np_.save_handout(people["ortho"], people["patient"], None, None, content)
    [(action, metadata)] = _audit_actions(people["patient"])
    assert action == "nutrition_handout_created"
    assert metadata["diet"] == "non_veg"
    assert metadata["themes"] == ["Inflammation & pain", "Vitamins & blood"]


def test_nutrition_actions_appear_in_the_doctors_audit_log(people):
    from app.services.doctor_ai_activity import get_activity_log

    np_.mark_discussed(people["ortho"], people["patient"], "vitamins", None, True)
    np_.save_handout(people["ortho"], people["patient"], None, None, np_.build_handout(np_.organize(GUIDANCE), "veg"))
    events = get_activity_log(people["ortho"])["events"]
    labels = [e["label"] for e in events[:2]]
    assert labels == ["You shared a food handout with the patient", "You discussed a nutrition topic"]
    assert events[1]["detail"] == {"theme_title": "Vitamins & blood"}


# ---- found in the live page ----

def test_a_qualified_food_is_the_same_food_shown_plainly():
    """Live page: "alcohol" and "excessive alcohol" listed as two things to go easy on."""
    guidance = {"items": [
        _item("Vitamin D", [], [], limit=["excessive alcohol", "fried foods"]),
        _item("ESR", [], [], limit=["alcohol"]),
        _item("Blood lipids", [], [], limit=["too much caffeine"]),
    ]}
    easy = {e["food"]: e["themes"] for e in np_.organize(guidance)["go_easy"]}
    assert easy["Alcohol"] == 2 and "Excessive alcohol" not in easy
    assert "Too much caffeine" in easy  # one spelling only: shown as written


def test_a_qualifier_that_changes_the_meaning_is_kept():
    assert np_.food_key("processed meats") != np_.food_key("meats")
    assert np_.food_key("excessive alcohol") == np_.food_key("alcohol")


def test_the_same_tip_from_related_findings_is_shown_once():
    """Live page: three findings in one theme each carried "Include turmeric and ginger..."."""
    guidance = {"items": [
        _item("ESR", ["turmeric"], ["turmeric"], note="Include turmeric and ginger in cooking for their anti-inflammatory properties."),
        _item("hs-CRP", ["ginger"], ["ginger"], note="Include turmeric and ginger in cooking for anti-inflammatory benefits."),
        _item("joint or back pain", ["walnuts"], ["salmon"], kind="symptom", because=[{"symptom": "joint or back pain"}],
              note="Stay active with gentle stretching."),
    ]}
    [theme] = np_.organize(guidance)["themes"]
    assert theme["tips"] == ["Include turmeric and ginger in cooking for their anti-inflammatory properties.",
                             "Stay active with gentle stretching."]


def test_a_tip_reworded_from_its_first_word_is_still_shown_once():
    """Live v2 page: "Add turmeric and ginger to your dishes..." and "Use turmeric and ginger in
    cooking..." both showed; they start differently but say the same thing."""
    assert np_._distinct_tips([
        "Add turmeric and ginger to your dishes for their anti-inflammatory properties.",
        "Use turmeric and ginger in cooking for their anti-inflammatory properties.",
    ]) == ["Add turmeric and ginger to your dishes for their anti-inflammatory properties."]


def test_a_tip_that_starts_the_same_and_ends_differently_is_shown_once():
    """Few words in common once filler is gone, but plainly the same advice."""
    assert np_._distinct_tips(["Stay hydrated with water throughout the day.",
                               "Stay hydrated with water and herbal teas."]) == [
        "Stay hydrated with water throughout the day."]


def test_different_tips_about_the_same_nutrient_all_stay():
    tips = ["Include a source of vitamin C with meals to enhance iron absorption.",
            "Have your tea between meals, not with them, to improve iron absorption.",
            "Cook in iron utensils to increase iron content in food.",
            "Spend some time in sunlight daily to help your body make Vitamin D.",
            "Sit in the morning sun on the balcony with your tea."]
    assert np_._distinct_tips(tips) == tips



# ---- v2: a day of real dishes per region, easy swaps, why it matters, habits ----

def _meals(prefix, regions=("north", "south", "east", "west")):
    """Distinct dishes per region and diet, named after their topic so the day can be traced."""
    return {region: {
        "veg": [{"meal": slot, "dish": f"{prefix} {region} veg {slot}"} for slot in ("breakfast", "lunch", "snack", "dinner")],
        "non_veg": [{"meal": slot, "dish": f"{prefix} {region} nonveg {slot}"} for slot in ("breakfast", "lunch", "snack", "dinner")],
    } for region in regions}


def _v2_item(term, prefix, *, kind="finding", why="", swaps=(), habits=(), meals=None):
    item = _item(term, ["curd"], ["eggs"], kind=kind,
                 because=[{"symptom": term}] if kind == "symptom" else None)
    return {**item, "why": why, "swaps": list(swaps), "habits": list(habits),
            "meals": meals if meals is not None else _meals(prefix)}


V2_GUIDANCE = {"items": [
    _v2_item("Vitamin D", "VitD", why="Vitamin D helps your bones use calcium.",
             swaps=[{"instead_of": "white bread", "try": "whole-wheat roti"}],
             habits=["Sit in the morning sun with your tea."]),
    _v2_item("ESR", "ESR", why="Calmer inflammation helps you feel better.",
             swaps=[{"instead_of": "White bread", "try": "multigrain roti"},
                    {"instead_of": "fried namkeen", "try": "roasted chana"}],
             habits=["Cook with turmeric and ginger."]),
    _v2_item("joint or back pain", "Joint", kind="symptom"),
]}


def test_a_day_takes_one_dish_per_meal_from_several_themes():
    day = np_.organize(V2_GUIDANCE)["sample_days"]["south"]["veg"]
    assert [meal["meal"] for meal in day] == ["breakfast", "lunch", "snack", "dinner"]
    # Inflammation & pain (ESR, joint pain) comes before Vitamins in the page's theme order;
    # each meal starts one topic further along, so three topics contribute.
    assert [meal["dish"] for meal in day] == ["ESR south veg breakfast", "Joint south veg lunch",
                                              "VitD south veg snack", "ESR south veg dinner"]
    assert day[2]["helps"] == ["Vitamins & blood"] and all(meal["region"] == "south" for meal in day)


def test_each_region_gets_its_own_dishes_and_all_india_mixes_them():
    days = np_.organize(V2_GUIDANCE)["sample_days"]
    assert set(days) == {"all", "north", "south", "east", "west"}
    assert all(" east " in meal["dish"] for meal in days["east"]["non_veg"])
    assert [meal["region"] for meal in days["all"]["veg"]] == ["north", "south", "east", "west"]


def test_a_vegetarian_day_never_carries_a_non_vegetarian_dish():
    """The entry check forbids it; the day checks again, in case anything ever slips."""
    meals = _meals("Bad")
    meals["north"]["veg"][0] = {"meal": "breakfast", "dish": "Egg bhurji with roti"}
    plan = np_.organize({"items": [_v2_item("Vitamin D", "Bad", meals=meals)]})
    dishes = [meal["dish"] for meal in plan["sample_days"]["north"]["veg"]]
    assert "Egg bhurji with roti" not in dishes and len(dishes) == 3


def test_the_same_guidance_makes_the_same_day():
    assert np_.organize(V2_GUIDANCE)["sample_days"] == np_.organize(V2_GUIDANCE)["sample_days"]


def test_swaps_are_listed_once_with_their_theme():
    for diet in ("veg", "non_veg"):
        swaps = np_.organize(V2_GUIDANCE)["swaps"][diet]
        # "White bread" from two topics is one swap: the first theme's wording.
        assert [s["instead_of"] for s in swaps] == ["White bread", "fried namkeen"]
        assert swaps[0] == {"instead_of": "White bread", "try": "multigrain roti", "theme": "Inflammation & pain"}


EGG_SWAPS = [{"instead_of": "plain dosa", "try": "egg dosa"},
             {"instead_of": "mutton curry", "try": "rajma with brown rice"},
             {"instead_of": "tea with biscuits", "try": "a glass of buttermilk with roasted chana"}]


def test_a_vegetarian_is_never_offered_a_swap_with_meat_fish_or_egg():
    """Live: low B12 guidance offered "plain dosa → egg dosa" to every patient. Swaps are
    written for both diets at once, so the vegetarian list is filtered — page, theme, handout."""
    plan = np_.organize({"items": [_v2_item("Vitamin B12", "B12", swaps=EGG_SWAPS)]})
    [theme] = plan["themes"]
    assert theme["swaps"]["veg"] == [EGG_SWAPS[2]]
    assert theme["swaps"]["non_veg"] == EGG_SWAPS
    assert [s["try"] for s in plan["swaps"]["veg"]] == ["a glass of buttermilk with roasted chana"]
    assert len(plan["swaps"]["non_veg"]) == 3
    assert np_.build_handout(plan, "veg", "all")["themes"][0]["swaps"] == [EGG_SWAPS[2]]
    assert np_.build_handout(plan, "non_veg", "all")["themes"][0]["swaps"] == EGG_SWAPS


def test_a_theme_keeps_a_few_swaps_taking_one_from_each_topic_in_turn():
    """Live: three topics in one theme brought eleven swaps to the patient's handout."""
    def swaps(prefix):
        return [{"instead_of": f"{prefix} plain {n}", "try": f"{prefix} better {n}"} for n in ("one", "two", "three")]
    guidance = {"items": [_v2_item("Vitamin D", "D", swaps=swaps("D")),
                          _v2_item("Vitamin B12", "B", swaps=swaps("B")),
                          _v2_item("Red Cell Distribution Width", "R", swaps=swaps("R"))]}
    [theme] = np_.organize(guidance)["themes"]
    assert [s["instead_of"] for s in theme["swaps"]["veg"]] == ["D plain one", "B plain one", "R plain one", "D plain two"]


def test_a_theme_shows_a_swap_once_however_many_of_its_topics_suggest_it():
    """The theme panel and the patient's handout list the theme's own swaps, not the page's."""
    guidance = {"items": [
        _v2_item("ESR", "ESR", swaps=[{"instead_of": "white rice", "try": "brown rice"}]),
        _v2_item("hs-CRP", "CRP", swaps=[{"instead_of": "White rice", "try": "red rice"},
                                         {"instead_of": "sweet tea", "try": "masala chaas"}]),
    ]}
    [theme] = np_.organize(guidance)["themes"]
    assert theme["swaps"]["veg"] == [{"instead_of": "white rice", "try": "brown rice"},
                                     {"instead_of": "sweet tea", "try": "masala chaas"}]


def test_a_dish_is_eaten_once_in_a_day():
    meals = _meals("X", regions=("north", "east", "west"))
    meals["south"] = {"veg": [{"meal": "lunch", "dish": "Moong dal khichdi"},
                              {"meal": "dinner", "dish": "Moong dal khichdi"},
                              {"meal": "dinner", "dish": "Palak paneer with phulka"}],
                      "non_veg": []}
    plan = np_.organize({"items": [_v2_item("Vitamin D", "X", meals=meals)]})
    assert [meal["dish"] for meal in plan["sample_days"]["south"]["veg"]] == [
        "Moong dal khichdi", "Palak paneer with phulka"]


def test_the_same_dish_with_different_sides_is_still_eaten_once():
    """Live: "Rajma with brown rice and a squeeze of lemon" for lunch, "Rajma with brown rice"
    for dinner; "Egg bhurji with whole-wheat toast" for breakfast and "... with roti" for dinner."""
    meals = _meals("X", regions=("south", "east", "west"))
    meals["north"] = {
        "veg": [{"meal": "lunch", "dish": "Rajma with brown rice and a squeeze of lemon"},
                {"meal": "dinner", "dish": "Rajma with brown rice"},
                {"meal": "dinner", "dish": "Palak paneer with whole-wheat roti"}],
        "non_veg": [{"meal": "breakfast", "dish": "Egg bhurji with whole-wheat toast"},
                    {"meal": "dinner", "dish": "Egg bhurji with whole-wheat roti"},
                    {"meal": "dinner", "dish": "Fish curry with brown rice"}],
    }
    plan = np_.organize({"items": [_v2_item("Vitamin D", "X", meals=meals)]})
    days = plan["sample_days"]["north"]
    assert [meal["dish"] for meal in days["veg"]] == ["Rajma with brown rice and a squeeze of lemon",
                                                      "Palak paneer with whole-wheat roti"]
    assert [meal["dish"] for meal in days["non_veg"]] == ["Egg bhurji with whole-wheat toast",
                                                          "Fish curry with brown rice"]


def test_different_dishes_that_start_alike_are_both_kept():
    assert np_._dish_key("A handful of roasted almonds") != np_._dish_key("A handful of walnuts")
    assert np_._dish_key("Fish curry with rice") != np_._dish_key("Fish tikka with salad")


def test_a_theme_says_why_it_matters_and_keeps_its_habits():
    themes = {t["title"]: t for t in np_.organize(V2_GUIDANCE)["themes"]}
    assert themes["Vitamins & blood"]["why"] == ["Vitamin D helps your bones use calcium."]
    assert themes["Vitamins & blood"]["tips"] == ["Sit in the morning sun with your tea."]
    assert themes["Inflammation & pain"]["swaps"]["veg"][1] == {"instead_of": "fried namkeen", "try": "roasted chana"}


def test_guidance_written_before_v2_still_makes_the_older_day():
    plan = np_.organize(GUIDANCE)
    assert plan["sample_days"]["all"]["veg"] == [] and plan["sample_day"]["veg"]
    handout = np_.build_handout(plan, "veg", "south")
    assert handout["sample_day"] and all(meal["dish"] is None for meal in handout["sample_day"])


def test_the_handout_follows_the_region_and_diet_the_doctor_chose():
    plan = np_.organize(V2_GUIDANCE)
    handout = np_.build_handout(plan, "non_veg", "east")
    assert handout["region"] == "east" and handout["region_label"] == "East Indian"
    assert [meal["dish"] for meal in handout["sample_day"]] == [m["dish"] for m in plan["sample_days"]["east"]["non_veg"]]
    vitamins = next(t for t in handout["themes"] if t["title"] == "Vitamins & blood")
    assert vitamins["why"] == ["Vitamin D helps your bones use calcium."]
    assert vitamins["swaps"] == [{"instead_of": "white bread", "try": "whole-wheat roti"}]
    # No values or documents reach the patient.
    assert "13.8" not in str(handout) and "d1" not in str(handout)
    assert np_.build_handout(plan, "veg", "atlantis")["region"] == "all"


def test_seeds_never_crowd_out_everyday_food():
    """Each topic may name two seeds; nine topics each naming flax and chia made a "foods that
    help most" list of seeds — the textbook list the client asked to be rid of."""
    items = [_item(term, ["Flaxseeds", "Chia seeds", "curd"], ["eggs"]) for term in ("Vitamin D", "ESR", "Vitamin B12")]
    items.append(_item("hs-CRP", ["Pumpkin seeds", "Sunflower seeds", "paneer"], ["eggs"]))
    plan = np_.organize({"items": items})
    good = plan["good_to_include"]["veg"]
    assert sum("seed" in food.lower() for food in good) == 2
    assert "Curd" in good and "Paneer" in good
    inflammation = next(t for t in plan["themes"] if t["title"] == "Inflammation & pain")
    assert sum("seed" in food.lower() for food in inflammation["foods"]["veg"]) == 2

def test_foods_from_several_topics_read_as_one_list():
    """Live page: "almonds" and "amla" among "Walnuts" and "Paneer"; "sugary snacks" above
    "Fried foods". Each topic capitalises its own way; the page shows one way."""
    guidance = {"items": [
        _item("Vitamin D", ["almonds", "omega-3 rich fish"], [], limit=["sugary snacks"]),
        _item("ESR", ["Walnuts", "Vitamin D-fortified milk"], [], limit=["Fried foods"]),
    ]}
    plan = np_.organize(guidance)
    foods = [e["food"] for e in plan["top_foods"]["veg"]]
    assert foods == ["Almonds", "Omega-3 rich fish", "Walnuts", "Vitamin D-fortified milk"]
    assert {e["food"] for e in plan["go_easy"]} == {"Sugary snacks", "Fried foods"}
    # The handout reads the same.
    handout_foods = [food for theme in np_.build_handout(plan, "veg")["themes"] for food in theme["foods"]]
    assert all(food[:1].isupper() for food in handout_foods)
