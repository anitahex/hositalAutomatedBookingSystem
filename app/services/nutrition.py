"""The AI nutritionist: food guidance for a doctor to discuss, vegetarian and non-vegetarian.

CONSISTENT BY CONSTRUCTION. Model-written guidance varies from call to call, and two
patients with the same low Vitamin D must not be told different things. So the model never
sees a patient. It writes guidance for ONE term at a time —

    finding  "Vitamin D"                       low
    finding  "Blood lipids"                    abnormal   (cholesterol, triglycerides, ratio)
    symptom  "constipation"                    present

— which is checked by code (check_entry) and stored in nutrition_guidance, keyed by the term
and the prompt version. Every patient with that term then gets that exact stored entry.

WHAT IS PATIENT-SPECIFIC IS WRITTEN BY CODE. Which terms apply (the patient's latest flagged
results and the diet-relevant symptoms in their booking note and in their own words in the
booking chat), the "because" evidence beside
each (value, document, date, page — from the record), and the conflict rules between terms
(kidney results, uric acid, blood sugar) are all decided here, deterministically.

WHAT THE CHECKS GUARANTEE, per entry, before it is stored:
  - the vegetarian list AND the vegetarian dishes hold no meat, fish, seafood or egg
    (lacto-vegetarian: dairy is allowed, as is usual in India)
  - food only: no supplements, tablets, doses or medicines — those are the doctor's call
  - no digits at all, so no amount or value can be invented (portions only in household
    words: "a katori of dal")
  - real food (v2): every region and diet has real dishes, each a dish and not a bare
    ingredient; none deep-fried, refined or a sweet; a food list is not mostly seeds; a
    swap changes something
  - habits true of every finding ("eat a balanced diet") are dropped, not shown
  - bounded lists of short items

WHAT IT IS NOT. A diet prescription. The UI labels it "Food guidance · AI drafted · to
discuss, not a diet prescription", and it is shown to doctors. The patient sees only the
handout a doctor chooses to share (nutrition_plan.build_handout): foods, dishes, swaps and
habits in the diet and cuisine the doctor chose, no values.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

from app.db.connection import connect_db

logger = logging.getLogger(__name__)

# v2: real dishes for each region of India (both diets), easy swaps, everyday habits and a
# plain sentence for the patient — guidance that reads like real life, not an ingredient list.
NUTRITION_PROMPT_VERSION = "nutrition-v2"

NUTRITION_SYSTEM = """You are a clinical nutritionist writing practical food guidance for patients of an Indian
hospital, which their doctor will talk through with them. You write guidance for ONE lab finding or
symptom at a time — never about a particular patient.

Return JSON only, exactly this shape:
{"nutrient_focus": "...", "why": "...",
 "veg_foods": ["..."], "non_veg_foods": ["..."], "limit": ["..."],
 "meals": {"north": {"veg": [{"meal": "breakfast", "dish": "..."}], "non_veg": [{"meal": "...", "dish": "..."}]},
           "south": {...}, "east": {...}, "west": {...}},
 "swaps": [{"instead_of": "...", "try": "..."}],
 "habits": ["..."],
 "note": ""}

What each part is for:
- nutrient_focus: one short sentence for the doctor naming the nutrient(s) or eating pattern
  that matters, e.g. "Vitamin D, with calcium to use it well."
- why: one warm, plain sentence the patient will read about what eating well does for them
  here, e.g. "Vitamin D helps your bones and muscles make good use of calcium." Encouraging,
  never alarming.
- veg_foods / non_veg_foods: up to 8 everyday foods each that help. veg_foods is
  LACTO-VEGETARIAN — plant foods and dairy only, NEVER meat, poultry, fish, seafood or eggs.
  non_veg_foods leads with the animal foods that help most.
- limit: up to 6 foods or habits to go easy on, or [].
- meals: for EACH region of India (north, south, east, west) and EACH diet (veg, non_veg),
  two to four real dishes a family there would cook or order, each tagged "breakfast",
  "lunch", "snack" or "dinner". Name each dish the way people say it, with what it is eaten
  with: "Moong dal chilla with mint chutney", "Ragi dosa with coconut chutney", "Macher jhol
  with rice", "Egg bhurji with whole-wheat roti", "Poha with peanuts and lemon". A portion,
  when it helps, only in household words: "a katori of dal", "a handful of roasted chana",
  "a glass of buttermilk". Veg dishes follow the vegetarian rule above.
- swaps: up to 4 simple switches in everyday Indian eating that bring in what THIS finding
  needs, e.g. for iron {"instead_of": "plain dal-chawal", "try": "palak dal with rice and a
  squeeze of lemon"}; for Vitamin B12 {"instead_of": "black tea with biscuits", "try": "a glass
  of buttermilk with a handful of roasted chana"}; for cholesterol {"instead_of": "ghee-laden
  paratha", "try": "methi thepla with curd"}. Not the same generic swap every finding would
  get ("white rice" to "brown rice", "sugary drinks" to "herbal tea", "refined flour" to
  "whole grains") unless it truly serves this finding.
- habits: up to 3 short, practical habits that fit daily life — when and how to eat, how to
  cook, sunlight — in kind, encouraging words.
- note: "".

Rules:
- SPECIFIC TO THIS FINDING. Every dish, swap and habit should deliver the nutrient or eating
  pattern in nutrient_focus — a dish chosen because it is rich in it, not a generic "healthy"
  meal. Say why through the dish itself ("Rajma with brown rice and a squeeze of lemon" for
  iron, "Mushroom masala with roti" for Vitamin D).
- VARIED. Different dishes in each region and diet; do not repeat one dish across regions.
- HOME-STYLE AND HEALTHY: whole grains, lean preparations, steamed, grilled, roasted or lightly
  cooked. Not deep-fried or refined-flour dishes (no pakora, samosa, puri, bhatura, parotta,
  kachori) and no sweets.
- Habits are specific and practical for this finding (e.g. "Have your tea after meals, not
  with them, so iron is absorbed well"), never general advice: not "eat a balanced diet",
  "eat a variety of foods", "drink plenty of water", "stay active" or "eat mindfully".
- Real food people actually eat: everyday Indian home food first; common urban options
  (oats, salads, smoothies, grilled fish, quinoa, avocado) are fine where they genuinely fit.
  Not a list of seeds and superfoods: at most two seeds in any food list.
- Every dish is a dish, not a single ingredient ("Palak dal with rice", not "spinach").
- Each food and dish is short: a name, not a paragraph.
- FOOD ONLY. No supplements, tablets, capsules, doses, medicines or brand names.
- NO DIGITS anywhere: no amounts, grams, servings, percentages, times or values. Words such as
  "a handful" or "twice a week" are fine.
- Conventional, evidence-based dietary advice for adults. Nothing speculative, no cures promised.
- Do not diagnose, and do not mention the patient.
"""

MAX_FOODS = 8
MAX_LIMIT = 6
MAX_ITEM_CHARS = 60
MAX_FOCUS_CHARS = 180
MAX_NOTE_CHARS = 220
MAX_WHY_CHARS = 200
MAX_DISH_CHARS = 90
MIN_DISHES = 2
MAX_DISHES = 4
MAX_SWAPS = 4
MAX_HABITS = 3
MAX_HABIT_CHARS = 170
MAX_SEEDS_PER_LIST = 2
GENERATION_CONCURRENCY = 4
# v2 entries are larger (dishes for four regions and two diets).
GENERATION_TIMEOUT_SECONDS = 60

REGIONS = ("north", "south", "east", "west")
MEAL_SLOTS = ("breakfast", "lunch", "snack", "dinner")
# "Flaxseeds" is one word: the seed is matched where it ENDS a word, not where one starts.
_SEED = re.compile(r"seeds?\b", re.I)
# Dishes that are no part of food guidance however good the rest of the plate is.
_UNHEALTHY_DISH = re.compile(
    r"\b(deep[\s-]?fried|pakoras?|pakodas?|bhajjis?|bhajiyas?|samosas?|kachoris?|puris?|pooris?|"
    r"bhatur(?:a|as|e)|parottas?|jalebis?|gulab jamuns?|halwa|mithai|cakes?|pastr(?:y|ies)|"
    r"doughnuts?|donuts?|french fries)\b", re.I,
)
# Dishes known by one word. Anything else of one word is an ingredient ("spinach"), not a dish.
SINGLE_WORD_DISHES = frozenset({
    "poha", "upma", "khichdi", "khichri", "idli", "idlis", "dosa", "uttapam", "dalia", "daliya", "pongal",
    "thepla", "theplas", "paratha", "dhokla", "sundal", "raita", "kadhi", "sambar", "rasam", "pesarattu",
    "appam", "puttu", "litti", "chilla", "handvo", "khandvi", "thalipeeth", "bisibelebath", "avial",
    "kosambari", "chaas", "lassi", "dalma", "ghugni", "chhole", "chole", "rajma", "biryani", "pulao",
    "salad", "soup", "smoothie", "porridge", "muesli", "oatmeal", "khakhra", "sprouts", "omelette",
})

KIND_FINDING = "finding"
KIND_SYMPTOM = "symptom"
DIRECTION_ABNORMAL = "abnormal"
DIRECTION_PRESENT = "present"

# ---- the checks ----

# Whole words only: "eggplant" is a vegetable, "kidney beans" are beans.
_NON_VEG = re.compile(
    r"\b(chicken|mutton|lamb|goat|beef|pork|veal|venison|meat|meats|keema|fish|salmon|tuna|"
    r"sardines?|mackerel|hilsa|rohu|catla|pomfret|surmai|bangda|anchov(?:y|ies)|cod|trout|"
    r"herring|basa|tilapia|prawns?|shrimps?|crabs?|lobsters?|oysters?|mussels?|clams?|squid|"
    r"octopus|scallops?|seafood|shellfish|eggs?|egg yolks?|liver|turkey|duck|quail|bacon|ham|"
    r"sausages?|salami|pepperoni|gelatin|gelatine|bone broth|fish oil|cod liver oil|"
    r"kidney(?!\s+beans?))\b",
    re.I,
)
_NOT_FOOD = re.compile(
    r"\b(supplements?|supplementation|tablets?|capsules?|pills?|doses?|dosage|mg|mcg|µg|iu|"
    r"injections?|medications?|medicines?|drugs?|prescri\w*|sachets?|multivitamins?)\b",
    re.I,
)
_DIGIT = re.compile(r"\d")
# Nutrient NAMES that contain a digit are names, not amounts: "Vitamin B12", "omega-3",
# "vitamin D3". The first real run rejected every entry about B12 or omega-3 as "a number".
# Removed before the digit check; any other digit still fails it.
# Plurals too: "Omega-3s help ease inflammation" failed every joint-pain entry as "a number".
_NUTRIENT_NAMES_WITH_DIGITS = re.compile(r"\b(?:b\s?(?:12|6|1|2|3|5|7|9)|d\s?[23]|k\s?[12]|omega[\s-]?(?:3|6|9))s?\b", re.I)


def _clean_list(values, limit: int) -> list[str] | None:
    if values is None:
        return []
    if not isinstance(values, list):
        return None
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            return None
        text = " ".join(value.split()).strip(" .;,")
        if not text:
            continue
        if len(text) > MAX_ITEM_CHARS:
            return None
        key = text.lower()
        if key not in seen:
            seen.add(key)
            out.append(text)
    return out[:limit]


def _clean_meals(raw) -> tuple[dict | None, str | None]:
    """{region: {veg: [...], non_veg: [...]}} of {meal, dish}, or (None, why)."""
    if not isinstance(raw, dict):
        return None, "meals must be an object with north, south, east and west"
    out: dict[str, dict[str, list[dict]]] = {}
    for region in REGIONS:
        diets = raw.get(region)
        if not isinstance(diets, dict):
            return None, f"meals is missing the {region} region"
        out[region] = {}
        for diet in ("veg", "non_veg"):
            dishes = diets.get(diet)
            if not isinstance(dishes, list):
                return None, f"meals.{region}.{diet} must be a list of dishes"
            clean: list[dict] = []
            seen: set[str] = set()
            for item in dishes:
                if not isinstance(item, dict):
                    return None, "each meal must be an object with meal and dish"
                meal = str(item.get("meal") or "").strip().lower()
                dish = " ".join(str(item.get("dish") or "").split()).strip(" .;,")
                if meal not in MEAL_SLOTS:
                    return None, f"each meal must be one of {', '.join(MEAL_SLOTS)}"
                if not dish or len(dish) > MAX_DISH_CHARS:
                    return None, f"each dish must be under {MAX_DISH_CHARS} characters"
                if len(dish.split()) < 2 and dish.lower() not in SINGLE_WORD_DISHES:
                    return None, (f"\"{dish}\" is an ingredient, not a dish; name a dish people eat, "
                                  "such as \"Palak dal with rice\"")
                if dish.lower() not in seen:
                    seen.add(dish.lower())
                    clean.append({"meal": meal, "dish": dish})
            if len(clean) < MIN_DISHES:
                return None, f"give at least {MIN_DISHES} dishes for {region} {diet}"
            out[region][diet] = clean[:MAX_DISHES]
    return out, None


def _clean_swaps(raw) -> tuple[list[dict] | None, str | None]:
    if raw is None:
        return [], None
    if not isinstance(raw, list):
        return None, "swaps must be a list"
    clean, seen = [], set()
    for item in raw:
        if not isinstance(item, dict):
            return None, "each swap must have instead_of and try"
        before = " ".join(str(item.get("instead_of") or "").split()).strip(" .;,")
        after = " ".join(str(item.get("try") or "").split()).strip(" .;,")
        if not before or not after or len(before) > MAX_ITEM_CHARS or len(after) > MAX_ITEM_CHARS:
            return None, f"each swap needs a short instead_of and try, each under {MAX_ITEM_CHARS} characters"
        if before.lower() == after.lower():
            return None, f"a swap must change something (\"{before}\" to itself)"
        if before.lower() not in seen:
            seen.add(before.lower())
            clean.append({"instead_of": before, "try": after})
    return clean[:MAX_SWAPS], None


# Advice true of every finding, which is why it reads like a textbook. The model is told not to
# give it and gives it anyway; it is dropped (not failed — the rest of the entry is good).
_GENERIC_HABIT = re.compile(
    r"\b(balanced (?:diet|meals?)|variety of|plenty of water|drink (?:more |enough )?water|stay hydrated|"
    r"stay active|mindful(?:ly)?|whole grains over refined|overall health)\b", re.I,
)


def _clean_habits(raw) -> tuple[list[str] | None, str | None]:
    if raw is None:
        return [], None
    if not isinstance(raw, list) or not all(isinstance(h, str) for h in raw):
        return None, "habits must be a list of short sentences"
    clean = [" ".join(h.split()) for h in raw if h.strip()]
    if any(len(h) > MAX_HABIT_CHARS for h in clean):
        return None, f"each habit must be under {MAX_HABIT_CHARS} characters"
    specific = [h for h in clean if not _GENERIC_HABIT.search(h)]
    return list(dict.fromkeys(specific))[:MAX_HABITS], None


def check_entry(raw) -> tuple[dict | None, str | None]:
    """(clean entry, None) when it passes every rule, else (None, why it failed).

    Pure. The reason is phrased for the model, which is told it on its one retry.
    """
    if not isinstance(raw, dict):
        return None, "the answer was not a JSON object"
    focus = " ".join(str(raw.get("nutrient_focus") or "").split())
    why = " ".join(str(raw.get("why") or "").split())
    note = " ".join(str(raw.get("note") or "").split())
    veg = _clean_list(raw.get("veg_foods"), MAX_FOODS)
    non_veg = _clean_list(raw.get("non_veg_foods"), MAX_FOODS)
    limit = _clean_list(raw.get("limit"), MAX_LIMIT)
    if veg is None or non_veg is None or limit is None:
        return None, f"every list must be a list of short food names, each under {MAX_ITEM_CHARS} characters"
    if not focus or len(focus) > MAX_FOCUS_CHARS:
        return None, "nutrient_focus must be one short sentence"
    if not why or len(why) > MAX_WHY_CHARS:
        return None, "why must be one short, plain sentence for the patient"
    if len(note) > MAX_NOTE_CHARS:
        return None, "note must be one short sentence"
    if not veg and not non_veg:
        return None, "give at least one food"
    meals, problem = _clean_meals(raw.get("meals"))
    if problem:
        return None, problem
    swaps, problem = _clean_swaps(raw.get("swaps"))
    if problem:
        return None, problem
    habits, problem = _clean_habits(raw.get("habits"))
    if problem:
        return None, problem

    unhealthy = [m["dish"] for region in REGIONS for diet in ("veg", "non_veg")
                 for m in meals[region][diet] if _UNHEALTHY_DISH.search(m["dish"])]
    if unhealthy:
        return None, (f"\"{unhealthy[0]}\" is deep-fried, refined or a sweet; suggest everyday "
                      "home-style dishes — steamed, grilled, roasted or lightly cooked")
    veg_dishes = [m["dish"] for region in REGIONS for m in meals[region]["veg"]]
    offending = [text for text in [*veg, *veg_dishes] if _NON_VEG.search(text)]
    if offending:
        return None, f"the vegetarian food or dishes contained non-vegetarian food ({', '.join(offending)})"
    for name, foods in (("veg_foods", veg), ("non_veg_foods", non_veg)):
        if sum(1 for food in foods if _SEED.search(food)) > MAX_SEEDS_PER_LIST:
            return None, f"{name} is mostly seeds; give everyday foods, with at most {MAX_SEEDS_PER_LIST} seeds"

    all_dishes = [m["dish"] for region in REGIONS for diet in ("veg", "non_veg") for m in meals[region][diet]]
    swap_text = [text for swap in swaps for text in (swap["instead_of"], swap["try"])]
    every_text = [focus, why, note, *veg, *non_veg, *limit, *all_dishes, *swap_text, *habits]
    with_digits = [text for text in every_text if _DIGIT.search(_NUTRIENT_NAMES_WITH_DIGITS.sub(" ", text))]
    if with_digits:
        return None, (f"it contained a number (\"{with_digits[0]}\"); use no digits — household words such as "
                      "\"a katori\" or \"twice a week\" are fine")
    not_food = [text for text in every_text if _NOT_FOOD.search(text)]
    if not_food:
        return None, f"it mentioned supplements, doses or medicines ({not_food[0]}); give food only"

    return {"nutrient_focus": focus, "why": why, "veg_foods": veg, "non_veg_foods": non_veg,
            "limit": limit, "meals": meals, "swaps": swaps, "habits": habits, "note": note}, None


# ---- which terms apply ----

# Results that are read together get ONE piece of guidance, not six overlapping ones.
TERM_GROUPS: dict[str, str] = {
    **{name: "Blood lipids" for name in (
        "Total Cholesterol", "LDL Cholesterol", "HDL Cholesterol", "VLDL Cholesterol",
        "Triglycerides", "Total Cholesterol HDL Ratio", "LDL HDL Ratio",
    )},
    **{name: "Blood sugar" for name in ("Glucose (fasting)", "HbA1c")},
    **{name: "Kidney function" for name in ("Creatinine", "EGFR", "Blood Urea", "Urea", "BUN")},
    **{name: "Liver enzymes" for name in ("SGOT", "SGPT", "ALT", "AST", "Alkaline Phosphatase", "GGT")},
}

# Diet-relevant symptoms, matched in the booking note. Only ones where food advice is
# conventional; a symptom with no dietary angle (a fracture, a rash) gets nothing.
SYMPTOM_VOCABULARY: dict[str, tuple[str, ...]] = {
    "constipation": ("constipation", "constipated", "hard stools"),
    "acidity or heartburn": ("acidity", "heartburn", "acid reflux", "reflux", "gerd", "indigestion"),
    "bloating": ("bloating", "bloated", "flatulence", "gas"),
    "diarrhoea": ("diarrhoea", "diarrhea", "loose stools", "loose motions"),
    "nausea": ("nausea", "nauseous", "vomiting"),
    "fatigue": ("fatigue", "tiredness", "tired", "weakness", "low energy", "exhaustion"),
    "muscle cramps": ("cramps", "cramping", "muscle cramp"),
    "joint or back pain": ("joint pain", "back pain", "knee pain", "lower back pain", "arthritis"),
    "poor sleep": ("insomnia", "poor sleep", "trouble sleeping", "difficulty sleeping"),
    "poor appetite": ("loss of appetite", "poor appetite", "not eating"),
    "weight gain": ("weight gain", "gaining weight", "overweight", "obesity"),
    "hair fall": ("hair fall", "hair loss"),
}
_NEGATION = re.compile(r"\b(no|not|denies|denied|without|never|nil)\b(?:\W+\w+){0,3}\W*$", re.I)


def symptoms_in(text: str | None) -> list[str]:
    """The diet-relevant symptoms a booking note mentions, in vocabulary order.

    A mention just after "no", "denies" or "without" does not count: "no nausea or
    vomiting" is not nausea.
    """
    found: list[str] = []
    lowered = str(text or "").lower()
    for tag, phrases in SYMPTOM_VOCABULARY.items():
        for phrase in phrases:
            for match in re.finditer(rf"\b{re.escape(phrase)}\b", lowered):
                if not _NEGATION.search(lowered[max(0, match.start() - 40):match.start()]):
                    found.append(tag)
                    break
            if tag in found:
                break
    return found


def describe_term(kind: str, term: str, direction: str) -> str:
    """What the model is told. The term and its direction — nothing about any patient."""
    if kind == KIND_SYMPTOM:
        return f"Symptom: {term}. Food guidance that commonly helps."
    if direction == DIRECTION_ABNORMAL:
        return f"Lab finding: {term} outside the reference range. Food guidance for it."
    return f"Lab finding: {term} is {direction}. Food guidance for it."


def _term_for(canonical: str, direction: str) -> tuple[str, str]:
    group = TERM_GROUPS.get(canonical)
    return (group, DIRECTION_ABNORMAL) if group else (canonical, direction)


# ---- conflicts between terms, decided in code ----

_HIGH_POTASSIUM = re.compile(
    r"\b(banana|coconut water|potato(?:es)?|sweet potato(?:es)?|spinach|palak|tomato(?:es)?|"
    r"orange|avocado|dates|raisins|apricots?|kiwi|dried fruits?)\b", re.I,
)
_HIGH_PROTEIN = re.compile(r"\b(protein|whey|soy chunks)\b", re.I)
_HIGH_PURINE = re.compile(
    r"\b(liver|kidney(?!\s+beans?)|organ meats?|mutton|lamb|goat|beef|pork|red meat|shellfish|"
    r"prawns?|shrimps?|crabs?|lobsters?|sardines?|anchov(?:y|ies)|mackerel|herring|mussels?|"
    r"scallops?)\b", re.I,
)
_SUGARY = re.compile(
    r"\b(juices?|honey|jaggery|sugar|sweets?|desserts?|syrup|soft drinks?|dates|raisins|"
    r"dried fruits?)\b", re.I,
)

CAUTION_KIDNEY = ("Kidney results are abnormal — agree any diet change with a renal dietitian. "
                  "High-potassium and high-protein foods have been left out.")
CAUTION_URIC_ACID = "Uric acid is high — organ meats, red meat and shellfish have been left out."
CAUTION_SUGAR = "Blood sugar is high — juices, sweets and dried fruit have been left out."


def apply_conflicts(items: list[dict], flagged: set[tuple[str, str]]) -> tuple[list[dict], list[str]]:
    """Removes foods that one of the patient's OTHER results makes unsuitable.

    `flagged` is the patient's (canonical name, direction) pairs. The same combination of
    results always removes the same foods and shows the same cautions. Pure.
    """
    kidney = bool(flagged & {("Creatinine", "high"), ("EGFR", "low"), ("Potassium", "high"),
                             ("Blood Urea", "high"), ("Urea", "high")})
    uric = ("Uric Acid", "high") in flagged
    sugar = bool(flagged & {("Glucose (fasting)", "high"), ("HbA1c", "high")})

    def keep(food: str, diet: str) -> bool:
        if kidney and (_HIGH_POTASSIUM.search(food) or _HIGH_PROTEIN.search(food)):
            return False
        if uric and diet == "non_veg_foods" and _HIGH_PURINE.search(food):
            return False
        if sugar and _SUGARY.search(food):
            return False
        return True

    cleaned = []
    for item in items:
        item = dict(item)
        for diet in ("veg_foods", "non_veg_foods"):
            item[diet] = [food for food in item.get(diet, []) if keep(food, diet)]
        # The same foods leave the dishes and the swaps: a kidney patient is not told to make
        # palak paneer because a different topic suggested it.
        if item.get("meals"):
            item["meals"] = {
                region: {diet: [m for m in dishes if keep(m["dish"], f"{diet}_foods")]
                         for diet, dishes in diets.items()}
                for region, diets in item["meals"].items()
            }
        if item.get("swaps"):
            item["swaps"] = [swap for swap in item["swaps"] if keep(swap["try"], "non_veg_foods")]
        cleaned.append(item)

    cautions = []
    if kidney:
        cautions.append(CAUTION_KIDNEY)
    if uric:
        cautions.append(CAUTION_URIC_ACID)
    if sugar:
        cautions.append(CAUTION_SUGAR)
    return cleaned, cautions


# ---- storage and generation ----

def _stored_entries(keys: list[tuple[str, str, str]]) -> dict[tuple[str, str, str], dict]:
    if not keys:
        return {}
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT kind, term, direction, entry FROM nutrition_guidance
                   WHERE prompt_version = %s AND (kind, term, direction) IN
                         (SELECT * FROM unnest(%s::text[], %s::text[], %s::text[]))""",
                (NUTRITION_PROMPT_VERSION, [k[0] for k in keys], [k[1] for k in keys], [k[2] for k in keys]),
            )
            rows = cur.fetchall()
        conn.commit()
    return {(row[0], row[1], row[2]): row[3] for row in rows}


def _store_entry(key: tuple[str, str, str], entry: dict, model: str | None) -> None:
    with connect_db() as conn:
        with conn.cursor() as cur:
            # DO NOTHING: if two requests generated the same term at once, the first stored
            # one stands, so every patient keeps getting the same text.
            cur.execute(
                """INSERT INTO nutrition_guidance (kind, term, direction, prompt_version, entry, model)
                   VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                   ON CONFLICT DO NOTHING""",
                (*key, NUTRITION_PROMPT_VERSION, json.dumps(entry), model),
            )
        conn.commit()


# Terms whose guidance failed the checks twice, and when. Nothing failing is ever stored, so
# without this every request for such a patient paid two more model calls and their wait.
_recent_failures: dict[tuple[str, str, str], float] = {}
FAILURE_BACKOFF_SECONDS = 30 * 60


async def _generate(key: tuple[str, str, str]) -> dict | None:
    """One term: generate, check, retry once with the reason, store. None if it never passes."""
    import time

    from app.inference.azure_client import gpt4o_nutrition_entry

    failed_at = _recent_failures.get(key)
    if failed_at and time.monotonic() - failed_at < FAILURE_BACKOFF_SECONDS:
        return None

    kind, term, direction = key
    reason = None
    for _attempt in range(2):
        try:
            generated = await asyncio.wait_for(
                gpt4o_nutrition_entry(kind=kind, term=term, direction=direction, retry_reason=reason),
                timeout=GENERATION_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.warning("nutrition: generation failed for %s: %s", key, exc)
            return None
        entry, reason = check_entry(generated.get("entry"))
        if entry:
            _store_entry(key, entry, generated.get("model"))
            return _stored_entries([key]).get(key, entry)
        logger.warning("nutrition: rejected entry for %s: %s", key, reason)
    # Only a CONTENT failure backs off; a timeout or an outage is retried on the next request.
    _recent_failures[key] = time.monotonic()
    return None


async def entries_for(keys: list[tuple[str, str, str]]) -> dict[tuple[str, str, str], dict]:
    """Stored entries for these terms, generating the missing ones (a few at a time)."""
    keys = list(dict.fromkeys(keys))
    found = _stored_entries(keys)
    missing = [key for key in keys if key not in found]
    if missing:
        gate = asyncio.Semaphore(GENERATION_CONCURRENCY)

        async def one(key):
            async with gate:
                return key, await _generate(key)

        for key, entry in await asyncio.gather(*(one(key) for key in missing)):
            if entry:
                found[key] = entry
    return found


# ---- per patient / per document ----

def _flagged_documents(patient_id: str) -> set[str]:
    """Documents a doctor has reported inaccurate: their results are left out. By the same
    rule the page labels them with (document_reviews.merged_review_states): a report flagged
    on ANY of its uploaded copies is flagged, so guidance never rests on a copy of a report
    the brief and the history show as reported inaccurate."""
    from app.services.document_reviews import STATUS_FLAGGED, merged_review_states
    from app.services.overview_documents import copy_groups

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT document_id FROM document_findings WHERE patient_id = %s", (patient_id,))
            ids = [str(row[0]) for row in cur.fetchall()]
        conn.commit()
    states = merged_review_states(copy_groups(ids), None, None)
    return {document_id for document_id, state in states.items() if state["status"] == STATUS_FLAGGED}


def _latest_flagged_results(patient_id: str, document_id: str | None, excluded: set[str],
                            documents: list[str] | None = None) -> list[dict]:
    """The latest reading of each measurement, where it is flagged low or high. For one
    document when `document_id` is given; among `documents` when that is given (an empty
    list means none, not all); otherwise across the patient's documents — with the same
    latest-reading rule and tie-break as the overview and the history."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT canonical_name, printed_name, value_text, abnormal, clinical_date, page_no,
                       document_id, document_type
                FROM (
                    SELECT DISTINCT ON (df.canonical_name)
                           df.canonical_name, df.printed_name, df.value_text, df.abnormal,
                           df.clinical_date, df.page_no, df.document_id, dc.document_type
                    FROM document_findings df
                    JOIN document_catalog dc ON dc.document_id = df.document_id
                    WHERE df.patient_id = %(patient)s AND df.canonical_name IS NOT NULL
                      AND dc.ingestion_status = 'complete'
                      AND (%(document)s::text IS NULL OR df.document_id = %(document)s)
                      AND (NOT %(scoped)s OR df.document_id = ANY(%(documents)s))
                      AND NOT (df.document_id = ANY(%(excluded)s))
                    ORDER BY df.canonical_name, df.clinical_date DESC NULLS LAST,
                             (df.abnormal = 'unknown'), df.created_at DESC
                ) latest
                WHERE abnormal IN ('low', 'high')
                ORDER BY canonical_name
                """,
                {"patient": patient_id, "document": document_id, "excluded": sorted(excluded),
                 "scoped": documents is not None, "documents": sorted(documents or [])},
            )
            rows = cur.fetchall()
        conn.commit()
    return [
        {"canonical_name": r[0], "printed_name": r[1], "value_text": r[2], "flag": r[3],
         "clinical_date": r[4].isoformat() if r[4] else None, "page_no": r[5],
         "document_id": r[6], "document_type": r[7]}
        for r in rows
    ]


def guidance_items(results: list[dict], symptoms: list[str],
                   symptom_sources: dict[str, str] | None = None) -> dict[tuple[str, str, str], dict]:
    """The topics guidance is given for, each with its evidence — chosen by code, no model.

    build_guidance writes guidance for exactly these; the heading names exactly these
    (focus_labels), so the heading and what opens beneath it cannot disagree.
    `symptom_sources` says where each symptom was found ("booking note", "booking chat").
    """
    items: dict[tuple[str, str, str], dict] = {}
    for result in results:
        term, direction = _term_for(result["canonical_name"], result["flag"])
        key = (KIND_FINDING, term, direction)
        items.setdefault(key, {"kind": KIND_FINDING, "term": term, "direction": direction, "because": []})
        items[key]["because"].append(result)
    for symptom in symptoms:
        key = (KIND_SYMPTOM, symptom, DIRECTION_PRESENT)
        source = (symptom_sources or {}).get(symptom, "booking note")
        items.setdefault(key, {"kind": KIND_SYMPTOM, "term": symptom, "direction": DIRECTION_PRESENT,
                               "because": [{"symptom": symptom, "source": source}]})
    return items


# Grouped topics, as a doctor would name them in a heading.
_GROUP_LABELS = {
    "Blood lipids": "cholesterol & lipids", "Blood sugar": "blood sugar",
    "Kidney function": "kidney function", "Liver enzymes": "liver enzymes",
}


def focus_label(kind: str, term: str, direction: str) -> str:
    """"Low Vitamin D", "Abnormal cholesterol & lipids", "Joint or back pain"."""
    if kind == KIND_SYMPTOM:
        return term[:1].upper() + term[1:]
    if direction == DIRECTION_ABNORMAL:
        return f"Abnormal {_GROUP_LABELS.get(term, term)}"
    return f"{direction.capitalize()} {term}"


def focus_labels(items) -> list[str]:
    """What the guidance is for, most relevant first: results in the page's theme order, then
    symptoms. `items` is guidance_items' result (or its keys)."""
    from app.services.nutrition_plan import _THEME_ORDER, theme_for

    keys = list(items)
    ordered = sorted(
        enumerate(keys),
        key=lambda pair: (pair[1][0] == KIND_SYMPTOM, _THEME_ORDER.get(theme_for(pair[1][1]), 99), pair[0]),
    )
    return [focus_label(*key) for _, key in ordered]


async def build_guidance(results: list[dict], symptoms: list[str],
                         symptom_sources: dict[str, str] | None = None) -> dict:
    """Items for these results and symptoms: stored guidance plus the evidence behind it.

    `symptom_sources` says where each symptom was found ("booking note", "booking chat");
    shown beside it so the doctor can see what the suggestion rests on.
    """
    items = guidance_items(results, symptoms, symptom_sources)
    entries = await entries_for(list(items))
    ready, unavailable = [], []
    for key, item in items.items():
        entry = entries.get(key)
        if entry:
            ready.append({**item, **entry})
        else:
            unavailable.append(item["term"])

    flagged = {(r["canonical_name"], r["flag"]) for r in results}
    ready, cautions = apply_conflicts(ready, flagged)
    return {
        "focus": focus_labels(items),
        "items": ready,
        "cautions": cautions,
        "unavailable": unavailable,
        "prompt_version": NUTRITION_PROMPT_VERSION,
    }


def _audit(doctor_id: str, metadata: dict) -> None:
    from app.services.consults import ensure_consult_schema

    try:
        with connect_db() as conn:
            ensure_consult_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata)
                       VALUES (NULL, %s, 'nutrition_guidance_viewed', %s::jsonb)""",
                    (doctor_id, json.dumps(metadata)),
                )
            conn.commit()
    except Exception as exc:
        logger.error("nutrition: could not audit view by doctor=%s: %s", doctor_id, exc)


def _booking_chat_patient_text(patient_id: str, booking_id: str) -> str:
    """What the patient wrote in the conversation that made this booking — their messages
    only, inside the window the booking pinned (booking_context), never the assistant's
    replies, which would put the model's own words back in as symptoms."""
    from app.services.booking_context import get_snapshot

    snapshot = get_snapshot(booking_id)
    if not snapshot or not snapshot.get("chat_session_id") or not snapshot.get("transcript_to_at"):
        return ""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT text FROM chat_messages
                   WHERE patient_id = %s AND chat_session_id::text = %s AND role = 'patient'
                     AND created_at BETWEEN %s::timestamp AND %s::timestamp
                   ORDER BY created_at""",
                (patient_id, snapshot["chat_session_id"], snapshot["transcript_from_at"],
                 snapshot["transcript_to_at"]),
            )
            rows = cur.fetchall()
        conn.commit()
    return "\n".join(str(row[0] or "") for row in rows)


def _scope_bookings(doctor_id, booking_id) -> tuple[str, list[tuple[str, object, str | None]]] | None:
    """(patient_id, [(booking_id, start_time, booking_note)]) for the visit's food guidance:
    THIS booking first, then the same doctor's earlier appointments with the patient, newest
    first — the visits the brief lists as "Your previous visits", with the same bound. None
    when the booking is not this doctor's."""
    from app.services.visit_brief import CANCELLED, MAX_PREVIOUS_VISITS

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT patient_id, start_time, booking_note FROM appointment_bookings WHERE booking_id = %s AND doctor_id = %s",
                (booking_id, doctor_id),
            )
            row = cur.fetchone()
            if not row:
                conn.commit()
                return None
            patient_id, start_time, booking_note = row
            cur.execute(
                """SELECT booking_id::text, start_time, booking_note FROM appointment_bookings
                   WHERE doctor_id = %s AND patient_id = %s AND booking_id <> %s
                     AND start_time < %s AND status <> %s
                   ORDER BY start_time DESC
                   LIMIT %s""",
                (doctor_id, patient_id, booking_id, start_time, CANCELLED, MAX_PREVIOUS_VISITS),
            )
            earlier = cur.fetchall()
        conn.commit()
    return patient_id, [(str(booking_id), start_time, booking_note), *earlier]


def _documents_of_bookings(patient_id: str, booking_ids: list[str]) -> list[str]:
    """The documents brought to these bookings, by the history's own rule
    (patient_timeline._ENCOUNTER_DOCUMENTS), so guidance and history agree on what belongs
    to a visit."""
    from app.services.patient_timeline import _ENCOUNTER_DOCUMENTS

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""WITH encounter_documents AS ({_ENCOUNTER_DOCUMENTS})
                    SELECT DISTINCT document_id::text FROM encounter_documents
                    WHERE booking_id::text = ANY(%(bookings)s)""",
                {"patient_id": patient_id, "bookings": booking_ids},
            )
            documents = [row[0] for row in cur.fetchall()]
        conn.commit()
    return documents


def _appointment_inputs(doctor_id: str, booking_id: str):
    """(patient_id, booking_id, excluded documents, flagged results, symptom sources,
    earlier visits counted) for a visit. The booking's own doctor only. Raises
    PermissionError otherwise.

    What it rests on is what the patient has brought to THIS doctor: the documents and the
    booking note and chat of this appointment and of their earlier appointments with them.
    It used to read every document from every doctor, so a colleague's patient's reports
    shaped this doctor's food guidance.
    """
    from app.services.visit_brief import _uuid_or_none

    safe_booking, safe_doctor = _uuid_or_none(booking_id), _uuid_or_none(doctor_id)
    if not safe_booking or not safe_doctor:
        raise PermissionError("Appointment not found.")
    scope = _scope_bookings(safe_doctor, safe_booking)
    if scope is None:
        raise PermissionError("Appointment not found.")
    patient_id, bookings = scope

    excluded = _flagged_documents(patient_id)
    documents = _documents_of_bookings(patient_id, [booking for booking, _start, _note in bookings])
    results = _latest_flagged_results(patient_id, None, excluded, documents=documents)
    # The booking note, and the patient's own words in the chat that made each booking.
    # Reading only the note missed every symptom the patient described once the note stopped
    # being filled in without their consent — they said it in the chat, not in a note.
    sources: dict[str, str] = {}
    for index, (booking, start_time, booking_note) in enumerate(bookings):
        # This visit's say "booking note"; an earlier visit's carry its date.
        when = "" if index == 0 or not start_time else f", {start_time.day} {start_time:%b}"
        for symptom in symptoms_in(booking_note):
            sources.setdefault(symptom, f"booking note{when}")
        for symptom in symptoms_in(_booking_chat_patient_text(patient_id, booking)):
            sources.setdefault(symptom, f"booking chat{when}")
    return patient_id, safe_booking, excluded, results, sources, len(bookings) - 1


def nutrition_focus_for_appointment(doctor_id: str, booking_id: str) -> list[str]:
    """The heading for a visit's food guidance — which findings and symptoms it is for —
    without generating anything. Empty when nothing diet-related was found (or no access)."""
    try:
        _patient, _booking, _excluded, results, sources, _earlier = _appointment_inputs(doctor_id, booking_id)
    except PermissionError:
        return []
    return focus_labels(guidance_items(results, list(sources), sources))


def nutrition_focus_for_document(patient_id: str, document_id: str) -> list[str]:
    """The same for one document's flagged results. None for a document reported inaccurate."""
    if document_id in _flagged_documents(patient_id):
        return []
    return focus_labels(guidance_items(_latest_flagged_results(patient_id, document_id, set()), []))


async def guidance_for_appointment(doctor_id: str, booking_id: str) -> dict:
    """For the visit brief: the latest flagged results among the documents brought to this
    appointment and this doctor's earlier ones with the patient, from documents nobody has
    reported inaccurate, and the diet-relevant symptoms in those bookings' notes and chats.

    The booking's own doctor only, as for the brief. Raises PermissionError otherwise.
    """
    patient_id, safe_booking, excluded, results, sources, earlier = _appointment_inputs(doctor_id, booking_id)
    guidance = await build_guidance(results, list(sources), sources)
    guidance["excluded_documents"] = len(excluded)
    # How many earlier visits with this doctor it also read — said under the heading.
    guidance["earlier_visits"] = earlier
    # The organised page (nutrition_plan) records discussions against the patient.
    guidance["patient_id"] = patient_id
    _audit(doctor_id, {"patient_id": patient_id, "booking_id": str(safe_booking),
                       "terms": len(guidance["items"])})
    return guidance


async def guidance_for_document(doctor_id: str, patient_id: str, document_id: str) -> dict:
    """For the document viewer: this document's flagged results only. The caller has run
    assert_doctor_may_read_document. A document reported inaccurate gets none."""
    excluded = _flagged_documents(patient_id)
    if document_id in excluded:
        guidance = {"focus": [], "items": [], "cautions": [], "unavailable": [],
                    "prompt_version": NUTRITION_PROMPT_VERSION, "reported_inaccurate": True}
    else:
        guidance = await build_guidance(_latest_flagged_results(patient_id, document_id, set()), [])
        guidance["reported_inaccurate"] = False
    _audit(doctor_id, {"patient_id": patient_id, "document_id": document_id,
                       "terms": len(guidance["items"])})
    return guidance


async def prewarm_for_document(document_id: str) -> int:
    """Generates any missing guidance for a newly processed document's flagged results, so
    the first doctor to open its nutrition section does not wait. Returns terms prepared."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT canonical_name, abnormal FROM document_findings
                   WHERE document_id = %s AND canonical_name IS NOT NULL AND abnormal IN ('low', 'high')""",
                (document_id,),
            )
            rows = cur.fetchall()
        conn.commit()
    keys = [(KIND_FINDING, *_term_for(name, flag)) for name, flag in rows]
    return len(await entries_for(keys))
