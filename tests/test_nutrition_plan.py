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
    assert vitamins["go_easy"] == ["fried foods", "alcohol"]


# ---- foods that help most ----

def test_foods_are_ranked_by_how_many_findings_list_them():
    top = np_.organize(GUIDANCE)["top_foods"]["veg"]
    assert (top[0]["food"], top[0]["count"]) == ("almonds", 3)  # "Almonds" counted with "almonds"
    assert ("turmeric", 2) in [(e["food"], e["count"]) for e in top]


def test_nothing_is_ranked_that_no_item_listed():
    listed = {np_.food_key(f) for item in GUIDANCE["items"] for f in item["veg_foods"]}
    assert {np_.food_key(e["food"]) for e in np_.organize(GUIDANCE)["top_foods"]["veg"]} <= listed


def test_go_easy_counts_the_themes_a_food_comes_from():
    easy = {e["food"]: e["themes"] for e in np_.organize(GUIDANCE)["go_easy"]}
    assert easy["fried foods"] == 2 and easy["alcohol"] == 1


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
    assert "oats" in morning["foods"]
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
    assert labels == ["You created a nutrition handout", "You discussed a nutrition topic"]
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
    assert easy["alcohol"] == 2 and "excessive alcohol" not in easy
    assert "too much caffeine" in easy  # one spelling only: shown as written


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
