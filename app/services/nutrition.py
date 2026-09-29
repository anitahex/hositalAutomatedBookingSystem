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
  - the vegetarian list holds no meat, fish, seafood or egg (lacto-vegetarian: dairy is
    allowed, as is usual in India)
  - food only: no supplements, tablets, doses or medicines — those are the doctor's call
  - no numbers at all, so no amount or value can be invented
  - bounded lists of short items

WHAT IT IS NOT. A diet prescription. The UI labels it "AI generated · food suggestions to
discuss, not a diet prescription", and it is shown to doctors. The patient sees only the
handout a doctor chooses to make (nutrition_plan.build_handout): foods and tips, no values.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

from app.db.connection import connect_db

logger = logging.getLogger(__name__)

NUTRITION_PROMPT_VERSION = "nutrition-v1"

NUTRITION_SYSTEM = """You are a clinical nutritionist writing food guidance for doctors in an Indian hospital.
You write guidance for ONE lab finding or symptom at a time — never about a particular patient.

Return JSON only:
{"nutrient_focus": "...", "veg_foods": ["..."], "non_veg_foods": ["..."], "limit": ["..."], "note": "..."}

- nutrient_focus: one short sentence naming the nutrient(s) or dietary pattern that matters
  for this finding, e.g. "Vitamin D, with calcium to use it well."
- veg_foods: up to 8 foods for a LACTO-VEGETARIAN diet — plant foods and dairy only. NEVER
  meat, poultry, fish, seafood or eggs.
- non_veg_foods: up to 8 foods for a non-vegetarian diet. Lead with the animal sources that
  help most (fish, eggs, poultry, meat); plant foods may follow.
- limit: up to 6 foods or habits to limit for this finding, or [] if none matter.
- note: one short practical sentence (preparation, pairing, timing), or "".

Rules:
- Foods commonly available in India, named plainly ("ragi", "paneer", "sardines", "amla").
- Each food is a short name, not a sentence.
- FOOD ONLY. No supplements, tablets, capsules, doses, medicines or brand names.
- NO NUMBERS anywhere: no amounts, grams, servings, percentages, times or values.
- Conventional, evidence-based dietary advice for adults. Nothing speculative.
- Do not diagnose, and do not mention the patient.
"""

MAX_FOODS = 8
MAX_LIMIT = 6
MAX_ITEM_CHARS = 60
MAX_FOCUS_CHARS = 180
MAX_NOTE_CHARS = 220
GENERATION_CONCURRENCY = 4
GENERATION_TIMEOUT_SECONDS = 45

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
_NUTRIENT_NAMES_WITH_DIGITS = re.compile(r"\b(?:b\s?(?:12|6|1|2|3|5|7|9)|d\s?[23]|k\s?[12]|omega[\s-]?(?:3|6|9))\b", re.I)


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


def check_entry(raw) -> tuple[dict | None, str | None]:
    """(clean entry, None) when it passes every rule, else (None, why it failed).

    Pure. The reason is phrased for the model, which is told it on its one retry.
    """
    if not isinstance(raw, dict):
        return None, "the answer was not a JSON object"
    focus = " ".join(str(raw.get("nutrient_focus") or "").split())
    note = " ".join(str(raw.get("note") or "").split())
    veg = _clean_list(raw.get("veg_foods"), MAX_FOODS)
    non_veg = _clean_list(raw.get("non_veg_foods"), MAX_FOODS)
    limit = _clean_list(raw.get("limit"), MAX_LIMIT)
    if veg is None or non_veg is None or limit is None:
        return None, f"every list must be a list of short food names, each under {MAX_ITEM_CHARS} characters"
    if not focus or len(focus) > MAX_FOCUS_CHARS:
        return None, "nutrient_focus must be one short sentence"
    if len(note) > MAX_NOTE_CHARS:
        return None, "note must be one short sentence"
    if not veg and not non_veg:
        return None, "give at least one food"

    offending = [food for food in veg if _NON_VEG.search(food)]
    if offending:
        return None, f"the vegetarian list contained non-vegetarian food ({', '.join(offending)})"
    every_text = [focus, note, *veg, *non_veg, *limit]
    if any(_DIGIT.search(_NUTRIENT_NAMES_WITH_DIGITS.sub(" ", text)) for text in every_text):
        return None, "it contained a number; use no amounts or values (nutrient names such as B12 are fine)"
    not_food = [text for text in every_text if _NOT_FOOD.search(text)]
    if not_food:
        return None, f"it mentioned supplements, doses or medicines ({not_food[0]}); give food only"

    return {"nutrient_focus": focus, "veg_foods": veg, "non_veg_foods": non_veg,
            "limit": limit, "note": note}, None


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
    """Documents a doctor has reported inaccurate: their results are left out."""
    from app.services.document_reviews import STATUS_FLAGGED, review_states

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT document_id FROM document_findings WHERE patient_id = %s", (patient_id,))
            ids = [row[0] for row in cur.fetchall()]
        conn.commit()
    states = review_states(ids, None, None)
    return {document_id for document_id, state in states.items() if state["status"] == STATUS_FLAGGED}


def _latest_flagged_results(patient_id: str, document_id: str | None, excluded: set[str]) -> list[dict]:
    """The latest reading of each measurement, where it is flagged low or high. For one
    document when `document_id` is given, otherwise across the patient's documents — with
    the same latest-reading rule and tie-break as the overview and the visit brief."""
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
                      AND NOT (df.document_id = ANY(%(excluded)s))
                    ORDER BY df.canonical_name, df.clinical_date DESC NULLS LAST,
                             (df.abnormal = 'unknown'), df.created_at DESC
                ) latest
                WHERE abnormal IN ('low', 'high')
                ORDER BY canonical_name
                """,
                {"patient": patient_id, "document": document_id, "excluded": sorted(excluded)},
            )
            rows = cur.fetchall()
        conn.commit()
    return [
        {"canonical_name": r[0], "printed_name": r[1], "value_text": r[2], "flag": r[3],
         "clinical_date": r[4].isoformat() if r[4] else None, "page_no": r[5],
         "document_id": r[6], "document_type": r[7]}
        for r in rows
    ]


async def build_guidance(results: list[dict], symptoms: list[str],
                         symptom_sources: dict[str, str] | None = None) -> dict:
    """Items for these results and symptoms: stored guidance plus the evidence behind it.

    `symptom_sources` says where each symptom was found ("booking note", "booking chat");
    shown beside it so the doctor can see what the suggestion rests on.
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


async def guidance_for_appointment(doctor_id: str, booking_id: str) -> dict:
    """For the visit brief: the patient's latest flagged results, from documents nobody has
    reported inaccurate, and the diet-relevant symptoms in this booking's note.

    The booking's own doctor only, as for the brief. Raises PermissionError otherwise.
    """
    from app.services.visit_brief import _uuid_or_none

    safe_booking, safe_doctor = _uuid_or_none(booking_id), _uuid_or_none(doctor_id)
    if not safe_booking or not safe_doctor:
        raise PermissionError("Appointment not found.")
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT patient_id, booking_note FROM appointment_bookings WHERE booking_id = %s AND doctor_id = %s",
                (safe_booking, safe_doctor),
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise PermissionError("Appointment not found.")
    patient_id, booking_note = row

    excluded = _flagged_documents(patient_id)
    results = _latest_flagged_results(patient_id, None, excluded)
    # The booking note, and the patient's own words in the chat that made this booking.
    # Reading only the note missed every symptom the patient described once the note stopped
    # being filled in without their consent — they said it in the chat, not in a note.
    sources: dict[str, str] = {}
    for symptom in symptoms_in(booking_note):
        sources.setdefault(symptom, "booking note")
    for symptom in symptoms_in(_booking_chat_patient_text(patient_id, str(safe_booking))):
        sources.setdefault(symptom, "booking chat")
    guidance = await build_guidance(results, list(sources), sources)
    guidance["excluded_documents"] = len(excluded)
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
        guidance = {"items": [], "cautions": [], "unavailable": [],
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
