"""The AI nutritionist, organised: themes, the foods that help most, what to go easy on, a
sample day, and which themes a doctor has discussed with the patient.

Built ON the checked guidance (app/services/nutrition.py), never beside it. Every food shown
here is one that passed nutrition.check_entry for one of the patient's own results or
symptoms, and this module only groups, counts and arranges those foods — no model call, no
new food, no number. The same guidance always produces the same page.

  - THEMES: each result or symptom belongs to one theme by a code-owned map ("Vitamin D" is
    Vitamins & blood, "Blood lipids" is Heart & cholesterol). A theme carries the exact
    results behind it — value, flag, document — and the union of its foods.
  - FOODS THAT HELP MOST: ranked by how many of the patient's results and symptoms each food
    appears for. A count, not a judgement.
  - GO EASY ON: the foods to limit, with how many themes each came from.
  - SAMPLE DAY: morning, lunch, evening, dinner, filled only from the ranked foods by a
    code-owned food category ("oats" is a breakfast base, "dal" a main). A food with no
    known category is not placed rather than placed wrongly.
  - DISCUSSED: a doctor marks a theme discussed; it is shown at the next visit, with who and
    when, and audited.
"""
from __future__ import annotations

import json
import logging
import re

from app.db.connection import connect_db
from app.db.schema_once import once_per_process

logger = logging.getLogger(__name__)

DIETS = ("veg", "non_veg")
_DIET_KEY = {"veg": "veg_foods", "non_veg": "non_veg_foods"}

# ---- themes ----

# Order is the order shown. Each theme: id, title, one-line blurb.
THEMES = [
    ("inflammation", "Inflammation & pain", "Anti-inflammatory foods and omega-3 fats."),
    ("heart", "Heart & cholesterol", "Healthy fats and fibre, less saturated fat."),
    ("sugar", "Blood sugar", "Slow carbohydrates and fibre, fewer sugars."),
    ("vitamins", "Vitamins & blood", "Foods rich in the vitamins and minerals that are low."),
    ("stress", "Stress & hormones", "Regular meals and foods that support steady energy and sleep."),
    ("kidney", "Kidney", "Kidney-friendly choices, agreed with a renal dietitian."),
    ("liver", "Liver", "Light, low-fat meals that are easy on the liver."),
    ("digestion", "Digestion", "Gentle, fibre-balanced foods for the gut."),
    ("weight", "Weight", "Filling, lower-calorie foods."),
    ("other", "Other results", "Guidance for the remaining results."),
]
THEME_TITLES = {theme_id: title for theme_id, title, _ in THEMES}
_THEME_ORDER = {theme_id: index for index, (theme_id, _, _) in enumerate(THEMES)}

_TERM_THEMES = {
    "hs-CRP": "inflammation", "ESR": "inflammation", "CRP": "inflammation",
    "joint or back pain": "inflammation", "muscle cramps": "inflammation",
    "Blood lipids": "heart",
    "Blood sugar": "sugar",
    "Vitamin D": "vitamins", "Vitamin B12": "vitamins", "Folate": "vitamins", "Ferritin": "vitamins",
    "Haemoglobin": "vitamins", "Red Cell Distribution Width": "vitamins", "Magnesium": "vitamins",
    "Calcium": "vitamins", "Iron": "vitamins", "fatigue": "vitamins", "hair fall": "vitamins",
    "Cortisol (morning)": "stress", "TSH": "stress", "Free T3": "stress", "Free T4": "stress",
    "poor sleep": "stress",
    "Kidney function": "kidney", "Uric Acid": "kidney", "Potassium": "kidney",
    "Liver enzymes": "liver",
    "constipation": "digestion", "acidity or heartburn": "digestion", "bloating": "digestion",
    "diarrhoea": "digestion", "nausea": "digestion", "poor appetite": "digestion",
    "weight gain": "weight",
}


def theme_for(term: str) -> str:
    return _TERM_THEMES.get(term, "other")


# "Excessive alcohol" and "alcohol" are one thing to go easy on. Only these qualifiers are
# dropped: "high-potassium fruit" or "processed meat" say something the bare word does not.
_QUALIFIERS = re.compile(r"^(?:excessive|excess|too much|too many)\s+")


def food_key(food: str) -> str:
    """One key for spellings of the same food: case, a bracketed aside, a plural 's', and an
    "excessive"/"too much" in front."""
    key = re.sub(r"\([^)]*\)", "", str(food or "")).strip().lower()
    key = _QUALIFIERS.sub("", " ".join(key.split()))
    if len(key) > 3 and key.endswith("s") and not key.endswith("ss"):
        key = key[:-1]
    return key


def _distinct_tips(notes) -> list[str]:
    """Each tip once. Guidance for related results often carries the same tip, worded the
    same or nearly ("Include turmeric and ginger in cooking for their anti-inflammatory
    properties" / "... for anti-inflammatory benefits"): same first five words, same tip."""
    kept, seen = [], set()
    for note in notes:
        text = " ".join(str(note or "").split())
        if not text:
            continue
        key = " ".join(re.findall(r"[a-z0-9]+", text.lower())[:5])
        if key in seen:
            continue
        seen.add(key)
        kept.append(text)
    return kept


def _rank(foods_per_item: list[list[str]]) -> list[dict]:
    """Foods by how many items list them, most first; ties in first-seen order."""
    counts: dict[str, int] = {}
    shown: dict[str, str] = {}
    order: list[str] = []
    for foods in foods_per_item:
        for key in dict.fromkeys(food_key(food) for food in foods if food):
            counts[key] = counts.get(key, 0) + 1
    for foods in foods_per_item:
        for food in foods:
            key = food_key(food)
            if not key:
                continue
            if key not in shown:
                order.append(key)
            # The plainest spelling is shown: "alcohol", not "excessive alcohol".
            if key not in shown or len(food) < len(shown[key]):
                shown[key] = food
    ranked = sorted(order, key=lambda key: (-counts[key], order.index(key)))
    return [{"food": shown[key], "count": counts[key]} for key in ranked]


# ---- the sample day ----

# Code-owned food categories. A food is placed by the first category whose words it
# contains; unknown foods are not placed.
_CATEGORIES = {
    "breakfast": ("oats", "ragi", "poha", "upma", "idli", "dosa", "dalia", "daliya", "porridge",
                  "muesli", "whole wheat bread", "multigrain bread", "millet", "bajra", "jowar",
                  "quinoa", "besan chilla", "sprouts"),
    "main": ("dal", "lentil", "rajma", "chana", "chickpea", "moong", "masoor", "brown rice",
             "roti", "chapati", "khichdi", "beans", "legume", "barley"),
    "vegetable": ("spinach", "palak", "broccoli", "carrot", "beetroot", "methi", "fenugreek leaves",
                  "cabbage", "cauliflower", "peas", "gourd", "pumpkin", "okra", "bhindi",
                  "mushroom", "tomato", "cucumber", "leafy", "greens", "drumstick", "capsicum",
                  "bell pepper", "sweet potato", "kale", "lettuce", "brinjal", "eggplant", "salad"),
    "protein_veg": ("paneer", "tofu", "curd", "yogurt", "yoghurt", "dahi", "soy", "milk",
                    "buttermilk", "chaas", "cheese"),
    "protein_non_veg": ("chicken", "fish", "salmon", "sardine", "mackerel", "tuna", "rohu",
                        "egg", "prawn", "turkey"),
    "fruit": ("amla", "orange", "guava", "papaya", "banana", "apple", "berries", "berry",
              "pomegranate", "kiwi", "lemon", "watermelon", "mango", "pear", "grape", "fig",
              "avocado", "citrus"),
    "nuts": ("almond", "walnut", "flaxseed", "chia", "pumpkin seed", "sunflower seed", "sesame",
             "peanut", "cashew", "pistachio", "seeds", "nuts"),
    "drink": ("green tea", "herbal tea", "ginger tea", "coconut water", "lemon water", "turmeric milk"),
    "spice": ("turmeric", "ginger", "garlic", "cinnamon", "jeera", "cumin", "ajwain", "fennel"),
}


def food_category(food: str) -> str | None:
    """The food's category, or None. The longest matching phrase wins, so "pumpkin seeds"
    is a seed (not the vegetable "pumpkin") and "sweet potato" a vegetable. Matched on the
    name as written, lower-cased: food_key's plural-stripping is for counting, and "oat"
    would miss "oats"."""
    name = " " + " ".join(re.sub(r"\([^)]*\)", "", str(food or "")).lower().split()) + " "
    best, best_length = None, 0
    for category, words in _CATEGORIES.items():
        for word in words:
            if f" {word}" in name and len(word) > best_length:
                best, best_length = category, len(word)
    return best


# Each meal: (id, label, [(category, how many)]).
_MEALS = [
    ("morning", "Morning", [("breakfast", 1), ("nuts", 2), ("fruit", 1)]),
    ("lunch", "Lunch", [("main", 1), ("vegetable", 2), ("protein", 1)]),
    ("evening", "Evening", [("drink", 1), ("fruit", 1), ("nuts", 1)]),
    ("dinner", "Dinner", [("protein", 1), ("vegetable", 2), ("spice", 1)]),
]


def sample_day(ranked: list[dict], diet: str, themes_by_food: dict[str, list[str]]) -> list[dict]:
    """Meals filled from the ranked foods, most helpful first, each food used once."""
    by_category: dict[str, list[str]] = {}
    for entry in ranked:
        category = food_category(entry["food"])
        if category == "protein_non_veg" and diet == "veg":
            continue  # the veg lists hold none, but a sample day must never place one
        if category in ("protein_veg", "protein_non_veg"):
            category = "protein"
        if category:
            by_category.setdefault(category, []).append(entry["food"])
    used: set[str] = set()
    meals = []
    for meal_id, label, slots in _MEALS:
        foods = []
        for category, count in slots:
            placed = 0
            for food in by_category.get(category, []):
                if placed >= count:
                    break
                if food_key(food) in used:
                    continue
                foods.append(food)
                used.add(food_key(food))
                placed += 1
        if foods:
            helps = sorted({
                title for food in foods for title in themes_by_food.get(food_key(food), [])
            }, key=lambda title: next((i for i, (_, t, _) in enumerate(THEMES) if t == title), 99))
            meals.append({"meal": meal_id, "label": label, "foods": foods, "helps": helps})
    return meals


def organize(guidance: dict, discussions: dict | None = None) -> dict:
    """The organised page for the checked guidance. Pure: same guidance, same page."""
    items = guidance.get("items") or []
    discussions = discussions or {}

    grouped: dict[str, list[dict]] = {}
    for item in items:
        grouped.setdefault(theme_for(item["term"]), []).append(item)

    themes = []
    for theme_id in sorted(grouped, key=lambda t: _THEME_ORDER[t]):
        theme_items = grouped[theme_id]
        results = [b for item in theme_items for b in item.get("because") or [] if not b.get("symptom")]
        symptoms = [b["symptom"] for item in theme_items for b in item.get("because") or [] if b.get("symptom")]
        themes.append({
            "id": theme_id,
            "title": THEME_TITLES[theme_id],
            "blurb": next(blurb for tid, _, blurb in THEMES if tid == theme_id),
            "results": results,
            "symptoms": symptoms,
            "symptom_sources": {
                b["symptom"]: b.get("source") or "booking note"
                for item in theme_items for b in item.get("because") or [] if b.get("symptom")
            },
            "terms": [item["term"] for item in theme_items],
            "foods": {diet: [e["food"] for e in _rank([item.get(_DIET_KEY[diet]) or [] for item in theme_items])]
                      for diet in DIETS},
            "go_easy": [e["food"] for e in _rank([item.get("limit") or [] for item in theme_items])],
            "tips": _distinct_tips(item.get("note") for item in theme_items),
            "discussed": discussions.get(theme_id),
        })

    themes_by_food: dict[str, dict[str, list[str]]] = {diet: {} for diet in DIETS}
    for theme in themes:
        for diet in DIETS:
            for food in theme["foods"][diet]:
                themes_by_food[diet].setdefault(food_key(food), []).append(theme["title"])

    top_foods = {diet: _rank([item.get(_DIET_KEY[diet]) or [] for item in items]) for diet in DIETS}
    go_easy_counts: dict[str, dict] = {}
    for theme in themes:
        for food in theme["go_easy"]:
            entry = go_easy_counts.setdefault(food_key(food), {"food": food, "themes": 0})
            entry["themes"] += 1
            if len(food) < len(entry["food"]):
                entry["food"] = food
    go_easy = sorted(go_easy_counts.values(), key=lambda e: -e["themes"])

    return {
        "themes": themes,
        "top_foods": top_foods,
        "go_easy": go_easy,
        "sample_day": {diet: sample_day(top_foods[diet], diet, themes_by_food[diet]) for diet in DIETS},
        "counts": {
            "results": sum(len(t["results"]) for t in themes),
            "symptoms": sum(len(t["symptoms"]) for t in themes),
            "themes": len(themes),
        },
    }


# ---- which themes have been discussed ----

@once_per_process
def ensure_discussion_schema(conn) -> None:
    """Also created by migration 0032; here too because production's database is stamped
    rather than migrated, and IF NOT EXISTS makes the two safe together."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS nutrition_discussions (
                id BIGSERIAL PRIMARY KEY,
                patient_id TEXT NOT NULL,
                theme TEXT NOT NULL,
                doctor_id UUID NOT NULL,
                booking_id UUID,
                discussed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_nutrition_discussions_patient
                ON nutrition_discussions (patient_id, theme, discussed_at DESC);
            """
        )
    conn.commit()


def _audit(cur, doctor_id: str, action: str, metadata: dict) -> None:
    cur.execute(
        """INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata)
           VALUES (NULL, %s, %s, %s::jsonb)""",
        (doctor_id, action, json.dumps(metadata)),
    )


def discussions_for(patient_id: str, viewer_doctor_id: str | None, viewer_department: str | None) -> dict:
    """{theme: {name, department, at, is_me, booking_id}} — the latest discussion of each
    theme. A doctor in a restricted specialty is not named outside it, as for reviews."""
    from app.services.document_reviews import RESTRICTED_REVIEWER
    from app.services.patient_timeline import may_read_note

    with connect_db() as conn:
        ensure_discussion_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (nd.theme) nd.theme, nd.doctor_id, d.name, d.department,
                       nd.discussed_at, nd.booking_id
                FROM nutrition_discussions nd
                LEFT JOIN doctors d ON d.doctor_id = nd.doctor_id
                WHERE nd.patient_id = %s
                ORDER BY nd.theme, nd.discussed_at DESC
                """,
                (patient_id,),
            )
            rows = cur.fetchall()
        conn.commit()
    result = {}
    for theme, doctor_id, name, department, discussed_at, booking_id in rows:
        is_me = str(doctor_id) == str(viewer_doctor_id)
        who = ({"name": name, "department": department}
               if is_me or may_read_note(viewer_department, department) else dict(RESTRICTED_REVIEWER))
        result[theme] = {**who, "is_me": is_me, "at": discussed_at.isoformat() if discussed_at else None,
                         "booking_id": str(booking_id) if booking_id else None}
    return result


def mark_discussed(doctor_id: str, patient_id: str, theme: str, booking_id: str | None, discussed: bool) -> None:
    """Records (or, for the doctor's own mark on this visit, withdraws) a discussion.

    Withdrawing removes only this doctor's mark for this booking: a colleague's record of
    their own conversation is theirs.
    """
    if theme not in THEME_TITLES:
        raise ValueError("Unknown theme.")
    from app.services.consults import ensure_consult_schema

    with connect_db() as conn:
        ensure_discussion_schema(conn)
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            if discussed:
                cur.execute(
                    "INSERT INTO nutrition_discussions (patient_id, theme, doctor_id, booking_id) VALUES (%s, %s, %s, %s)",
                    (patient_id, theme, doctor_id, booking_id),
                )
                _audit(cur, doctor_id, "nutrition_theme_discussed",
                       {"patient_id": patient_id, "theme": theme, "theme_title": THEME_TITLES[theme],
                        "booking_id": booking_id})
            else:
                cur.execute(
                    """DELETE FROM nutrition_discussions
                       WHERE patient_id = %s AND theme = %s AND doctor_id = %s
                         AND booking_id IS NOT DISTINCT FROM %s""",
                    (patient_id, theme, doctor_id, booking_id),
                )
                if cur.rowcount:
                    _audit(cur, doctor_id, "nutrition_theme_discussion_withdrawn",
                           {"patient_id": patient_id, "theme": theme, "theme_title": THEME_TITLES[theme],
                            "booking_id": booking_id})
        conn.commit()


# ---- handouts: what the patient takes home, kept in their account ----

HANDOUT_NOTE = (
    "These are food suggestions to talk over with your doctor, not a diet prescription. "
    "Please check with your doctor before making big changes, especially if you have kidney, "
    "liver or heart problems, or are pregnant."
)


@once_per_process
def ensure_handout_schema(conn) -> None:
    """Also created by migration 0033; here too for production's stamped database."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS nutrition_handouts (
                id BIGSERIAL PRIMARY KEY,
                patient_id TEXT NOT NULL,
                doctor_id UUID NOT NULL,
                booking_id UUID,
                document_id TEXT,
                diet TEXT NOT NULL,
                content JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_nutrition_handouts_patient
                ON nutrition_handouts (patient_id, created_at DESC);
            """
        )
    conn.commit()


def build_handout(plan: dict, diet: str) -> dict:
    """The patient's copy of the page, in the diet the doctor chose.

    Built from the organised plan, never from free text: theme titles and blurbs written in
    this module, and foods, limits and tips that passed nutrition.check_entry. No values, no
    document names, no doses — the patient takes it home.
    """
    diet = diet if diet in DIETS else "veg"
    return {
        "diet": diet,
        "themes": [
            {
                "title": theme["title"],
                "blurb": theme["blurb"],
                "foods": list(theme["foods"][diet]),
                "go_easy": list(theme["go_easy"]),
                "tips": list(theme["tips"]),
            }
            for theme in plan.get("themes") or []
        ],
        "sample_day": [
            {"label": meal["label"], "foods": list(meal["foods"])}
            for meal in (plan.get("sample_day") or {}).get(diet, [])
        ],
        "note": HANDOUT_NOTE,
    }


def save_handout(doctor_id: str, patient_id: str, booking_id: str | None, document_id: str | None,
                 content: dict) -> int:
    """Keeps the handout in the patient's account, and audits that it was given."""
    from app.services.consults import ensure_consult_schema

    with connect_db() as conn:
        ensure_handout_schema(conn)
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO nutrition_handouts (patient_id, doctor_id, booking_id, document_id, diet, content)
                   VALUES (%s, %s, %s, %s, %s, %s::jsonb) RETURNING id""",
                (patient_id, doctor_id, booking_id, document_id, content["diet"], json.dumps(content)),
            )
            handout_id = cur.fetchone()[0]
            _audit(cur, doctor_id, "nutrition_handout_created", {
                "patient_id": patient_id, "booking_id": booking_id, "document_id": document_id,
                "diet": content["diet"], "handout_id": handout_id,
                "themes": [theme["title"] for theme in content["themes"]],
            })
        conn.commit()
    return int(handout_id)


def handouts_for_patient(patient_id: str, limit: int = 20) -> list[dict]:
    """The patient's handouts, newest first, with the doctor who gave each."""
    with connect_db() as conn:
        ensure_handout_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """SELECT h.id, h.created_at, h.diet, h.content, d.name, d.department
                   FROM nutrition_handouts h
                   LEFT JOIN doctors d ON d.doctor_id = h.doctor_id
                   WHERE h.patient_id = %s
                   ORDER BY h.created_at DESC
                   LIMIT %s""",
                (patient_id, limit),
            )
            rows = cur.fetchall()
        conn.commit()
    return [
        {"id": row[0], "created_at": row[1].isoformat() if row[1] else None, "diet": row[2],
         "content": row[3], "doctor_name": row[4], "department": row[5]}
        for row in rows
    ]
