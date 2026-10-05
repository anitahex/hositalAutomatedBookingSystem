"""Turning extracted findings into comparable measurements.

WHY THIS EXISTS. The extractor already stores per-analyte values, nested one level under
a panel name:

    {"Vitamins & Minerals": {"Vitamin D, 25-Hydroxy (Total)": "13.8 ng/mL", ...}}

That is enough to READ but not enough to USE. You cannot flag an abnormal value, and you
cannot plot Vitamin D across three reports, when the value is a string, the analyte is
spelled differently on every lab's stationery, and the whole structure lives in a blob
rather than in the database.

This module is the deterministic half of the feature. Per the approved plan:

  - reference ranges are CODE-OWNED, never asked of a model
  - abnormal/normal is COMPUTED here, never asked of a model
  - trends are a SQL query over what this produces, never a model comparing reports

A model reads the document. It never decides whether a result is abnormal, and it is never
asked to compare two documents. Those are the judgements most likely to be wrong and least
likely to be checked, so they are the ones that stay in code.

UNITS ARE PART OF THE SAFETY ARGUMENT. Vitamin D in nmol/L is ~2.5x the same result in
ng/mL. Comparing a value to a range in the wrong unit would silently invert "deficient"
and "normal", so a unit that does not match the reference unit yields UNKNOWN rather than
a guess — and unknown means no flag is shown at all.
"""
from __future__ import annotations

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

ABNORMAL_LOW = "low"
ABNORMAL_HIGH = "high"
ABNORMAL_NORMAL = "normal"
ABNORMAL_UNKNOWN = "unknown"

# "13.8 ng/mL", "4.62 million/uL", "24.6 µg/dL", "5.4 %", "<0.01 mIU/L", "7,850 cells/µL"
_NUMBER = r"\d+(?:[.,]\d+)*"
_VALUE_PATTERN = re.compile(
    rf"^\s*(?P<op>[<>]=?)?\s*(?P<num>{_NUMBER})\s*(?P<unit>.*?)\s*$"
)
_THOUSANDS = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")
_PARENTHETICAL = re.compile(r"\([^)]*\)")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_RATIO = re.compile(r"\bratio\b")
# Kept upper-case when a name is title-cased, so "LDL HDL Ratio" does not read "Ldl Hdl".
_ACRONYMS = frozenset({
    "hdl", "ldl", "vldl", "bun", "crp", "tsh", "alt", "ast", "ggt", "ag", "egfr", "sgot", "sgpt",
    "rbc", "wbc", "rdw", "pcv", "esr", "mcv", "mch", "mchc", "tlc", "dlc", "alp", "ldh", "cpk", "psa",
    "inr", "pt", "aptt", "tibc", "ft3", "ft4", "t3", "t4", "hba1c", "cv",
})


def parse_measurement(raw: str | None) -> tuple[float | None, str | None, str | None]:
    """"13.8 ng/mL" -> (13.8, "ng/mL", None); "<0.01 mIU/L" -> (0.01, "mIU/L", "<").

    Returns (value, unit, operator). A value that is not numeric at all — a comment, or
    the extractor's '[Incomplete/Illegible text in document]' marker — yields (None, ...),
    and callers must store it as text without a number rather than dropping it: "this was
    measured but could not be read" is itself worth showing a doctor.

    The operator is kept because "<0.01" is not 0.01. A censored value must not be plotted
    or compared as though it were exact.
    """
    text = str(raw or "").strip()
    if not text:
        return None, None, None
    match = _VALUE_PATTERN.match(text)
    if not match:
        return None, None, None
    value = to_number(match.group("num"))
    if value is None:
        return None, None, None
    unit = (match.group("unit") or "").strip() or None
    return value, unit, match.group("op")


def to_number(token: str | None) -> float | None:
    """A printed number, reading a comma the way the lab meant it.

    "7,850" is seven thousand eight hundred and fifty; "13,8" is thirteen point eight.
    Every comma was read as a decimal point, so a white count of 7,850 cells/µL was stored
    as 7.85 — against the report's own printed range of 4,000 - 10,000 that is a severe
    LOW, from a normal result. A comma followed by exactly three digits (and repeating) is
    a thousands separator; a single other comma is a decimal point.
    """
    text = str(token or "").strip()
    if not text:
        return None
    if _THOUSANDS.fullmatch(text):
        text = text.replace(",", "")
    elif text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def normalize_unit(unit: str | None) -> str | None:
    """Case- and micron-insensitive unit key.

    Labs print µg, ug and mcg for the same thing, and PDF extraction mangles µ into any of
    several codepoints. Treating those as different units would make a correct value
    unclassifiable, which shows up as a missing flag rather than a visible error.
    """
    if not unit:
        return None
    cleaned = str(unit).strip().lower()
    for micro in ("µ", "μ", "�", "mc"):
        cleaned = cleaned.replace(micro, "u")
    cleaned = _NON_ALNUM.sub("", cleaned)
    return _UNIT_ALIASES.get(cleaned, cleaned) or None


# Spellings of one unit that the character rules above cannot fold. ESR is printed
# "mm/1st hr" (Westergren, first hour) by most Indian labs; it is the same mm/hr.
_UNIT_ALIASES = {
    "mm1sthr": "mmhr",
    "mm1sthour": "mmhr",
    "mmin1sthr": "mmhr",
}


def canonical_name(name: str | None) -> str | None:
    """Collapses one analyte's many printed spellings to a single key.

    "Vitamin D, 25-Hydroxy (Total)", "25-OH Vitamin D" and "Vitamin D (25-OH)" are one
    measurement, and a trend that did not join them would show three one-point series —
    which looks like no history rather than like a bug.
    """
    if not name:
        return None
    text = _PARENTHETICAL.sub(" ", str(name)).lower()
    key = _NON_ALNUM.sub(" ", text).strip()
    if not key:
        return None
    # A ratio of two analytes is its own measurement. "Total Cholesterol / HDL Ratio"
    # contains "hdl", so it matched the HDL pattern below and was stored AS HDL Cholesterol,
    # with HDL's 40-100 mg/dL range: 5.37 sat beside 38.0 in the same series, and the at-a-
    # glance card, picking one HDL reading per date, could pick the ratio and drop the real
    # (low) HDL result. Checked first so no analyte pattern can claim it.
    if _RATIO.search(key):
        return " ".join(
            word.upper() if word in _ACRONYMS else word.capitalize() for word in key.split()
        )
    for pattern, canonical in _CANONICAL_PATTERNS:
        if pattern.search(key):
            return canonical
    # Title-cased, but "VLDL Cholesterol" not "Vldl Cholesterol", "SGOT" not "Sgot".
    return " ".join(word.upper() if word in _ACRONYMS else word.capitalize() for word in key.split())


# Ordered: the first match wins, so more specific patterns come first.
#
# The corpuscular indices are listed BEFORE haemoglobin on purpose. "Mean Corpuscular Hb
# (MCH)" contains the token "hb" and was being canonicalised to Haemoglobin — which the
# unit guard caught before it produced a wrong flag (28.4 pg against a g/dL range), but
# which would still have mixed MCH points into a Haemoglobin trend. A trend is grouped by
# canonical name alone, so a collision there is silent in a way a misflag is not.
_CANONICAL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bmchc\b|mean corpuscular (hb|haemoglobin|hemoglobin) conc"), "MCHC"),
    (re.compile(r"\bmch\b|mean corpuscular (hb|haemoglobin|hemoglobin)"), "MCH"),
    (re.compile(r"\bmcv\b|mean corpuscular volume"), "MCV"),
    (re.compile(r"\bvitamin d\b|\b25 hydroxy\b|\b25 oh\b"), "Vitamin D"),
    (re.compile(r"\bvitamin b ?12\b|\bcyanocobalamin\b"), "Vitamin B12"),
    (re.compile(r"\bfolic acid\b|\bfolate\b"), "Folate"),
    (re.compile(r"\bferritin\b"), "Ferritin"),
    (re.compile(r"\bcortisol\b"), "Cortisol (morning)"),
    (re.compile(r"\btsh\b|\bthyroid stimulating\b"), "TSH"),
    (re.compile(r"\bfree t3\b|\bft3\b"), "Free T3"),
    (re.compile(r"\bfree t4\b|\bft4\b"), "Free T4"),
    (re.compile(r"\bhba1c\b|\bglycated\b"), "HbA1c"),
    (re.compile(r"\bhs crp\b|\bc reactive\b|\bcrp\b"), "hs-CRP"),
    (re.compile(r"\besr\b|\berythrocyte sedimentation\b"), "ESR"),
    (re.compile(r"\bhdl\b"), "HDL Cholesterol"),
    (re.compile(r"\bldl\b"), "LDL Cholesterol"),
    (re.compile(r"\btriglyceride"), "Triglycerides"),
    (re.compile(r"\btotal cholesterol\b"), "Total Cholesterol"),
    (re.compile(r"\bhaemoglobin\b|\bhemoglobin\b|\bhb\b"), "Haemoglobin"),
    (re.compile(r"\bplatelet"), "Platelets"),
    (re.compile(r"\bglucose\b"), "Glucose (fasting)"),
    (re.compile(r"\bcreatinine\b"), "Creatinine"),
    (re.compile(r"\bmagnesium\b"), "Magnesium"),
]

# Adult reference ranges, with the unit each is expressed in. A value in any OTHER unit is
# not converted — it is left unclassified, because a wrong conversion is worse than a
# missing flag. Ranges are conventional adult values and are intentionally conservative;
# they drive a visual flag that points a doctor at a number, never a clinical decision.
#
# name -> (low, high, unit)
REFERENCE_RANGES: dict[str, tuple[float, float, str]] = {
    "Vitamin D": (30.0, 100.0, "ng/mL"),
    "Vitamin B12": (200.0, 900.0, "pg/mL"),
    "Folate": (3.0, 17.0, "ng/mL"),
    "Ferritin": (30.0, 400.0, "ng/mL"),
    "Cortisol (morning)": (6.2, 19.4, "ug/dL"),
    "TSH": (0.4, 4.0, "uIU/mL"),
    "Free T3": (2.3, 4.2, "pg/mL"),
    "Free T4": (0.8, 1.8, "ng/dL"),
    "HbA1c": (4.0, 5.6, "%"),
    "hs-CRP": (0.0, 3.0, "mg/L"),
    "ESR": (0.0, 20.0, "mm/hr"),
    "HDL Cholesterol": (40.0, 100.0, "mg/dL"),
    "LDL Cholesterol": (0.0, 100.0, "mg/dL"),
    "Triglycerides": (0.0, 150.0, "mg/dL"),
    "Total Cholesterol": (0.0, 200.0, "mg/dL"),
    "Haemoglobin": (13.0, 17.0, "g/dL"),
    "Glucose (fasting)": (70.0, 100.0, "mg/dL"),
    "Creatinine": (0.7, 1.3, "mg/dL"),
    "Magnesium": (1.7, 2.2, "mg/dL"),
}


def classify(canonical: str | None, value: float | None, unit: str | None) -> str:
    """low / high / normal / unknown — computed, never asked of a model.

    UNKNOWN whenever anything is uncertain: no value, no reference range for this analyte,
    or a unit that does not match the range's unit. Unknown renders as no flag at all,
    which is the honest outcome — the alternative is telling a doctor a result is normal
    on the strength of a range we did not actually apply.
    """
    if value is None or not canonical:
        return ABNORMAL_UNKNOWN
    reference = REFERENCE_RANGES.get(canonical)
    if not reference:
        return ABNORMAL_UNKNOWN
    low, high, reference_unit = reference
    if normalize_unit(unit) != normalize_unit(reference_unit):
        logger.debug(
            "document_findings: %s in %r not comparable to reference unit %r",
            canonical, unit, reference_unit,
        )
        return ABNORMAL_UNKNOWN
    if value < low:
        return ABNORMAL_LOW
    if value > high:
        return ABNORMAL_HIGH
    return ABNORMAL_NORMAL


def flatten_findings(findings) -> list[dict]:
    """The nested extractor output as a flat list of measurements.

    Handles both shapes seen in stored data: panel -> {analyte: value}, and the flat
    analyte -> value the schema nominally specifies. Both occur, so both are read rather
    than one being declared wrong after the fact.

    Every measurement carries its canonical name, parsed value, unit and computed flag.
    Non-numeric values are kept with value=None: "measured but unreadable" is information.
    """
    rows: list[dict] = []
    if not isinstance(findings, dict):
        return rows

    def _add(panel: str | None, name: str, raw_value) -> None:
        if not isinstance(raw_value, (str, int, float)):
            return
        value, unit, operator = parse_measurement(str(raw_value))
        canonical = canonical_name(name)
        row = {
            "panel": panel,
            "name": str(name).strip(),
            "canonical_name": canonical,
            "value_text": str(raw_value).strip(),
            "value_num": value,
            "unit": unit,
            "operator": operator,
        }
        # Classified against the standard range only; apply_report_flags() re-classifies
        # with what the report printed once the page text is at hand. A censored value
        # ("<0.01") is never compared against a range — see classify_row.
        rows.append({**row, **classify_row(row, None)})

    for key, value in findings.items():
        if isinstance(value, dict):
            for analyte, analyte_value in value.items():
                _add(str(key), str(analyte), analyte_value)
        else:
            _add(None, str(key), value)
    return rows


def reference_for(canonical: str | None) -> tuple[float | None, float | None]:
    """The stored bounds for a measurement, so the UI can show "18 (ref 30–100)" without
    re-deriving them. (None, None) when we have no range — which is why `abnormal` is
    'unknown' for that row."""
    reference = REFERENCE_RANGES.get(canonical or "")
    return (reference[0], reference[1]) if reference else (None, None)


# ---- what the report itself printed ----
#
# The lab prints its own verdict beside most results — "14.8 H % 11.6 - 14.0" — and the
# extractor kept only "14.8 %". With only the 19-analyte table above to go on, everything
# else stayed 'unknown' and was never shown as abnormal, "H" printed beside it or not.
# Measured on a real report: the lab flagged 12 results, the doctor's viewer showed 8.
#
# So the flag and the range are read here, by code, from the page line the value is
# printed on, and they decide in this order:
#
#   1. the report's flag           H, L, HH, LL, High, Low, Critical, *
#   2. the report's printed range  "11.6 - 14.0", "< 41", "> 40", "Desirable: < 200"
#   3. the standard range above    shown labelled as such: it is not on the report
#   4. unknown                     listed, never flagged
#
# Still no model: a model named the analyte and read its value; finding that value on the
# page and reading what the lab printed after it is string work, checked against the page
# text already stored. For a scanned document the "page" is the vision transcription, which
# carries the same caveat the summary already shows.

FLAG_SOURCE_REPORT_FLAG = "report_flag"
FLAG_SOURCE_REPORT_RANGE = "report_range"
FLAG_SOURCE_STANDARD_RANGE = "standard_range"
REF_SOURCE_REPORT = "report"
REF_SOURCE_STANDARD = "standard"

# Short flags are upper-case and must stand alone: "L" is a flag, "HDL", "L5" and "mmol/L"
# are not. "Low risk" is a band label ("Low risk: < 1.0"), not a verdict.
_FLAG_TOKENS = r"HH|LL|H|L|\*{1,2}|(?i:high|low|critical|crit|panic)"
_FLAG_END = r"(?=$|[\s,;|)\]])(?!\s+(?i:risk))"
_FLAG_AT_START = re.compile(rf"\s*(?P<flag>{_FLAG_TOKENS}){_FLAG_END}")
_FLAG_DIRECTION = {"H": ABNORMAL_HIGH, "HH": ABNORMAL_HIGH, "HIGH": ABNORMAL_HIGH,
                   "L": ABNORMAL_LOW, "LL": ABNORMAL_LOW, "LOW": ABNORMAL_LOW}
_CRITICAL_FLAGS = frozenset({"HH", "LL", "CRITICAL", "CRIT", "PANIC"})

# A value followed by a flag, anywhere on a line: how many results the REPORT marks.
_FLAGGED_VALUE = re.compile(rf"(?<![\w.,/:])[<>]?{_NUMBER}\s+(?:{_FLAG_TOKENS}){_FLAG_END}")

_RANGE_BETWEEN = re.compile(
    rf"(?<![\w.,])(?P<low>{_NUMBER})\s*(?:-|–|—|\bto\b)\s*(?P<high>{_NUMBER})(?![\w.,]*\d)"
)
_RANGE_BOUND = re.compile(rf"(?P<op><=|>=|≤|≥|<|>|(?i:up\s*to))\s*(?P<num>{_NUMBER})(?![\w.,]*\d)")
# A labelled range is the reference interval only under one of these labels. Anything else
# is a band — "Insufficient: 20 - 29", "Average: 1.0 - 3.0" — and taking a band for the
# reference range would call a deficient Vitamin D normal.
_REFERENCE_LABELS = (
    "biological reference interval", "biological ref interval", "biological ref. interval",
    "reference range", "reference interval", "normal range", "ref range", "reference",
    "ref", "normal", "desirable", "optimal",
)


def _words(text: str | None) -> list[str]:
    folded = unicodedata.normalize("NFKC", str(text or "")).casefold()
    return _NON_ALNUM.sub(" ", folded).split()


def parse_printed_range(text: str | None) -> dict | None:
    """The reference range printed in `text` (the rest of a result line), or None.

    Returns {"low", "high", "low_inclusive", "high_inclusive", "text"}; one bound may be
    None ("< 41"). None when the line prints no range, only a band, or nonsense (low > high).
    """
    text = str(text or "")
    matches = [m for m in (_RANGE_BETWEEN.search(text), _RANGE_BOUND.search(text)) if m]
    if not matches:
        return None
    match = min(matches, key=lambda m: m.start())

    before = text[:match.start()].rstrip()
    start = match.start()
    if before.endswith(":"):
        head = before[:-1].rstrip().lower()
        label = next((lbl for lbl in _REFERENCE_LABELS if head.endswith(lbl)), None)
        if label is None:
            return None
        start = before.lower().rfind(label)
    printed = " ".join(text[start:match.end()].split())

    if match.re is _RANGE_BETWEEN:
        low, high = to_number(match.group("low")), to_number(match.group("high"))
        if low is None or high is None or low > high:
            return None
        return {"low": low, "high": high, "low_inclusive": True, "high_inclusive": True, "text": printed}

    number = to_number(match.group("num"))
    if number is None:
        return None
    op = " ".join(match.group("op").lower().split())
    if op in ("<", "<=", "≤", "up to", "upto"):
        return {"low": None, "high": number, "low_inclusive": True,
                "high_inclusive": op != "<", "text": printed}
    return {"low": number, "high": None, "low_inclusive": op != ">",
            "high_inclusive": True, "text": printed}


def _against(value: float, printed_range: dict) -> str:
    low, high = printed_range["low"], printed_range["high"]
    if low is not None and (value < low or (value == low and not printed_range["low_inclusive"])):
        return ABNORMAL_LOW
    if high is not None and (value > high or (value == high and not printed_range["high_inclusive"])):
        return ABNORMAL_HIGH
    return ABNORMAL_NORMAL


def locate_printed_result(row: dict, pages: list[dict] | None) -> dict | None:
    """Where this measurement is printed, and what the report says beside it.

    Finds the page line on which the stored value follows the analyte's name. The name may
    wrap: "hs-CRP (High Sensitivity C-Reactive" on one line and "3.6 H mg/L" on the next,
    so a value that starts its line is matched against the line above. Only that line is
    read for the flag and the range — a number elsewhere on the page is never taken as
    this result's.

    Returns {"page_no", "line", "flag", "range"} or None when the value cannot be found
    after its name, in which case nothing from the report is claimed.
    """
    value_text = str(row.get("value_text") or "")
    number = re.search(_NUMBER, value_text)
    name_words = _words(_PARENTHETICAL.sub(" ", str(row.get("name") or row.get("printed_name") or "")))
    if not number or not name_words:
        return None
    token = number.group(0)
    spellings = {token, token.replace(",", "")} if _THOUSANDS.fullmatch(token) else {token}
    value_pattern = re.compile(
        r"(?<![\w.,])(?:" + "|".join(re.escape(s) for s in sorted(spellings, key=len, reverse=True))
        + r")(?![.,]?\d)"
    )
    wanted = set(name_words)

    for page in pages or []:
        lines = str(page.get("text") or "").splitlines()
        for index, line in enumerate(lines):
            for found in value_pattern.finditer(line):
                before = line[:found.start()]
                context = before
                if not re.search(r"[A-Za-z]", before) and index > 0:
                    context = lines[index - 1] + " " + before
                if not wanted.issubset(_words(context)):
                    continue
                rest = line[found.end():]
                flag_match = _FLAG_AT_START.match(rest)
                after = rest[flag_match.end():] if flag_match else rest
                if not flag_match and row.get("unit"):
                    # Some labs print the flag after the unit: "14.8 % H".
                    unit_and_rest = rest.split(None, 1)
                    if (len(unit_and_rest) == 2
                            and normalize_unit(unit_and_rest[0]) == normalize_unit(row["unit"])):
                        flag_match = _FLAG_AT_START.match(unit_and_rest[1])
                        if flag_match:
                            after = unit_and_rest[1][flag_match.end():]
                return {
                    "page_no": page.get("page_no"),
                    "line": " ".join(line.split()),
                    "flag": flag_match.group("flag") if flag_match else None,
                    "range": parse_printed_range(after),
                }
    return None


def classify_row(row: dict, printed: dict | None) -> dict:
    """The flag, range and their provenance for one measurement, in the order above.

    `printed` is locate_printed_result()'s answer, or None when there is no page text.
    """
    canonical, value = row.get("canonical_name"), row.get("value_num")
    unit, operator = row.get("unit"), row.get("operator")
    standard_low, standard_high = reference_for(canonical)
    has_standard = standard_low is not None or standard_high is not None
    result = {
        "abnormal": ABNORMAL_UNKNOWN,
        "flag_source": None,
        "critical": False,
        "report_flag": None,
        "report_ref_text": None,
        "ref_low": standard_low,
        "ref_high": standard_high,
        "ref_source": REF_SOURCE_STANDARD if has_standard else None,
        "page_no": row.get("page_no"),
    }
    printed_range = printed.get("range") if printed else None
    if printed:
        result["page_no"] = printed.get("page_no") or result["page_no"]
    if printed_range:
        result.update(
            ref_low=printed_range["low"], ref_high=printed_range["high"],
            ref_source=REF_SOURCE_REPORT, report_ref_text=printed_range["text"],
        )

    flag = printed.get("flag") if printed else None
    if flag:
        key = flag.upper()
        direction = _FLAG_DIRECTION.get(key)
        if direction is None and value is not None and not operator:
            # "*" or "Critical" says abnormal without saying which way; the range does.
            if printed_range:
                direction = _against(value, printed_range)
            else:
                direction = classify(canonical, value, unit)
            if direction not in (ABNORMAL_LOW, ABNORMAL_HIGH):
                direction = None
        result.update(
            abnormal=direction or ABNORMAL_UNKNOWN,
            flag_source=FLAG_SOURCE_REPORT_FLAG,
            critical=key in _CRITICAL_FLAGS,
            report_flag=flag,
        )
        return result

    # A censored value ("<0.01") is a bound, not a measurement: never compared to a range.
    if operator or value is None:
        return result
    if printed_range:
        result.update(abnormal=_against(value, printed_range), flag_source=FLAG_SOURCE_REPORT_RANGE)
        return result
    standard = classify(canonical, value, unit)
    if standard != ABNORMAL_UNKNOWN:
        result.update(abnormal=standard, flag_source=FLAG_SOURCE_STANDARD_RANGE)
    return result


def apply_report_flags(rows: list[dict], pages: list[dict] | None) -> list[dict]:
    """Every row re-classified with what its report printed. Pure; returns new dicts."""
    return [{**row, **classify_row(row, locate_printed_result(row, pages))} for row in rows]


def count_report_flags(pages: list[dict] | None) -> int:
    """How many lines of the report carry a value with a flag after it.

    The check behind "nothing missed": if the report marks more results than we list as
    flagged by the report, the doctor is told, with both numbers, rather than trusting a
    list that is silently short.
    """
    return sum(
        1
        for page in pages or []
        for line in str(page.get("text") or "").splitlines()
        if _FLAGGED_VALUE.search(line)
    )


# ---- persistence ----

def save_findings(document_id: str, patient_id: str, rows: list[dict], clinical_date=None) -> int:
    """Replaces this document's measurements. Returns how many were stored.

    Replaces rather than appends: re-extracting a document must not double every point on
    a trend. The UNIQUE (document_id, printed_name) constraint makes that the database's
    rule rather than this function's.
    """
    from app.db.connection import connect_db

    if not rows:
        return 0

    payload = []
    for row in rows:
        # Rows from classify_row carry the range actually applied (the report's, else the
        # standard one) and where it came from; a bare row gets the standard range.
        if "ref_source" in row:
            ref_low, ref_high, ref_source = row.get("ref_low"), row.get("ref_high"), row.get("ref_source")
        else:
            ref_low, ref_high = reference_for(row.get("canonical_name"))
            ref_source = REF_SOURCE_STANDARD if (ref_low is not None or ref_high is not None) else None
        payload.append((
            document_id, patient_id, row.get("panel"), row["name"],
            row.get("canonical_name"), row.get("value_text") or "",
            row.get("value_num"), row.get("operator"), row.get("unit"),
            ref_low, ref_high, row.get("abnormal") or ABNORMAL_UNKNOWN,
            clinical_date, row.get("page_no"),
            row.get("report_flag"), row.get("report_ref_text"), ref_source,
            row.get("flag_source"), bool(row.get("critical")),
        ))

    from app.services.document_versions import (
        REPLACED_BY_EXTRACTION, archive_findings, ensure_document_versions_schema,
    )

    with connect_db() as conn:
        ensure_document_versions_schema(conn)
        with conn.cursor() as cur:
            # A measurement this run changes is kept as it stood first (document_versions):
            # a re-extraction must not erase the value a doctor read or verified.
            cur.execute(
                """SELECT finding_id, printed_name, canonical_name, value_text, value_num, unit,
                          abnormal, clinical_date
                   FROM document_findings WHERE document_id = %s""",
                (document_id,),
            )
            incoming = {item[3]: item for item in payload}
            changed = []
            for finding_id, printed, canonical, value_text, value_num, unit, abnormal, stored_date in cur.fetchall():
                new = incoming.get(printed)
                if new is None:
                    continue
                before = (canonical, value_text or "", _comparable(value_num), unit, abnormal,
                          str(stored_date) if stored_date else None)
                after = (new[4], new[5], _comparable(new[6]), new[8], new[11],
                         str(new[12]) if new[12] else None)
                if before != after:
                    changed.append(finding_id)
            archive_findings(cur, changed, REPLACED_BY_EXTRACTION)
            cur.executemany(
                """
                INSERT INTO document_findings (
                    document_id, patient_id, panel, printed_name, canonical_name,
                    value_text, value_num, value_operator, unit, ref_low, ref_high,
                    abnormal, clinical_date, page_no,
                    report_flag, report_ref_text, ref_source, flag_source, critical
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (document_id, printed_name) DO UPDATE SET
                    panel = EXCLUDED.panel,
                    canonical_name = EXCLUDED.canonical_name,
                    value_text = EXCLUDED.value_text,
                    value_num = EXCLUDED.value_num,
                    value_operator = EXCLUDED.value_operator,
                    unit = EXCLUDED.unit,
                    ref_low = EXCLUDED.ref_low,
                    ref_high = EXCLUDED.ref_high,
                    abnormal = EXCLUDED.abnormal,
                    clinical_date = EXCLUDED.clinical_date,
                    page_no = EXCLUDED.page_no,
                    report_flag = EXCLUDED.report_flag,
                    report_ref_text = EXCLUDED.report_ref_text,
                    ref_source = EXCLUDED.ref_source,
                    flag_source = EXCLUDED.flag_source,
                    critical = EXCLUDED.critical
                """,
                payload,
            )
        conn.commit()
    logger.info("document_findings: stored %d measurements for document=%s", len(payload), document_id)
    return len(payload)


def rederive_stored_findings(*, dry_run: bool = False, patient_id: str | None = None) -> dict:
    """Re-derives every stored measurement from its printed name, its printed value and its
    document's page text, using the rules above as they stand now.

    Needed because all of it is computed once, at extraction time, and stored. A correction
    — the ratio rule, the thousands separator, reading the report's own flags — otherwise
    reaches only documents uploaded afterwards; rows already stored keep the old answer
    forever, and keep feeding the viewer, the trends and the at-a-glance card.

    Recomputed per row: canonical name, number/unit/operator (from value_text), and the
    flag, range and provenance (classify_row against the report's own line). Makes no model
    calls.

    Idempotent: a row whose recomputed values already match is not written. The cached
    at-a-glance cards of patients whose findings changed are dropped — they were built from
    the old rows, and nothing else would tell the cache its inputs moved.

    `patient_id` limits it to one patient — for a targeted repair, and so a test never
    rewrites anyone else's rows.

    Returns {"checked", "changed", "patients", "documents", "examples", "dry_run"}.
    """
    from app.db.connection import connect_db

    columns = ("canonical_name", "value_num", "value_operator", "unit", "ref_low", "ref_high",
               "abnormal", "page_no", "report_flag", "report_ref_text", "ref_source",
               "flag_source", "critical")
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT finding_id, patient_id, document_id, printed_name, value_text,
                           {", ".join(columns)}
                    FROM document_findings
                    WHERE %(patient)s::text IS NULL OR patient_id = %(patient)s""",
                {"patient": patient_id},
            )
            rows = cur.fetchall()

            documents = sorted({row[2] for row in rows})
            pages_by_document: dict[str, list[dict]] = {}
            if documents:
                cur.execute(
                    """SELECT document_id, page_no, text FROM document_pages
                       WHERE document_id = ANY(%s) ORDER BY document_id, page_no""",
                    (documents,),
                )
                for document_id, page_no, text in cur.fetchall():
                    pages_by_document.setdefault(document_id, []).append(
                        {"page_no": page_no, "text": text}
                    )

            changes = []
            for finding_id, row_patient, document_id, printed, value_text, *stored in rows:
                old = dict(zip(columns, stored))
                # Re-parsed from the printed text (that is where "7,850" was misread), but a
                # unit or operator stored in its own column is not thrown away when the text
                # alone does not carry it.
                value, unit, operator = parse_measurement(value_text)
                value = value if value is not None else _comparable(old["value_num"])
                unit = unit or old["unit"]
                operator = operator or old["value_operator"]
                row = {"name": printed, "canonical_name": canonical_name(printed),
                       "value_text": value_text, "value_num": value, "unit": unit,
                       "operator": operator, "page_no": old["page_no"]}
                new = {**row, **classify_row(row, locate_printed_result(row, pages_by_document.get(document_id)))}
                new["value_operator"] = operator
                before = {key: _comparable(old[key]) for key in columns}
                after = {key: _comparable(new.get(key)) for key in columns}
                if before != after:
                    changes.append((finding_id, row_patient, printed, before, after))

            if changes and not dry_run:
                from app.services.document_versions import (
                    REPLACED_BY_REFLAG, archive_findings, ensure_document_versions_schema,
                )

                ensure_document_versions_schema(conn)
                # Each row is kept as it stood before this re-derivation rewrites it.
                archive_findings(cur, [finding_id for finding_id, *_rest in changes], REPLACED_BY_REFLAG)
                cur.executemany(
                    f"""UPDATE document_findings
                        SET {", ".join(f"{key} = %s" for key in columns)}
                        WHERE finding_id = %s""",
                    [tuple(after[key] for key in columns) + (finding_id,)
                     for finding_id, _p, _n, _before, after in changes],
                )
                patients = sorted({str(row_patient) for _f, row_patient, _n, _b, _a in changes})
                cur.execute(
                    "DELETE FROM patient_overviews WHERE patient_id = ANY(%s)", (patients,)
                )
        if not dry_run:
            conn.commit()

    return {
        "checked": len(rows),
        "changed": len(changes),
        "patients": len({str(c[1]) for c in changes}),
        "documents": len(documents),
        "examples": [
            {"printed_name": printed,
             "was": {k: v for k, v in before.items() if before[k] != after[k]},
             "now": {k: v for k, v in after.items() if before[k] != after[k]}}
            for _f, _p, printed, before, after in changes[:60]
        ],
        "dry_run": dry_run,
    }


# The earlier name, kept for the script and callers that already use it.
recanonicalise_stored_findings = rederive_stored_findings


def _comparable(value):
    """Stored NUMERIC comes back as Decimal; compare numbers as floats."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)) or type(value).__name__ == "Decimal":
        return float(value)
    return value


def _as_float(value):
    return float(value) if value is not None else None


def _row_to_finding(row) -> dict:
    return {
        "panel": row[0], "printed_name": row[1], "canonical_name": row[2],
        "value_text": row[3], "value_num": float(row[4]) if row[4] is not None else None,
        "value_operator": row[5], "unit": row[6],
        "ref_low": float(row[7]) if row[7] is not None else None,
        "ref_high": float(row[8]) if row[8] is not None else None,
        "abnormal": row[9],
        "clinical_date": row[10].isoformat() if row[10] else None,
        # Where the flag and the range came from, so the viewer can say "flagged by the
        # report" or "standard adult range — not printed on this report".
        "report_flag": row[11],
        "report_ref_text": row[12],
        "ref_source": row[13],
        "flag_source": row[14],
        "critical": bool(row[15]),
        "page_no": row[16],
    }


_SELECT_COLUMNS = """
    panel, printed_name, canonical_name, value_text, value_num, value_operator,
    unit, ref_low, ref_high, abnormal, clinical_date,
    report_flag, report_ref_text, ref_source, flag_source, critical, page_no
"""


def findings_for_document(document_id: str) -> list[dict]:
    """Every measurement from one document. No authorization — the caller must have
    already applied the treating-relationship check."""
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT {_SELECT_COLUMNS} FROM document_findings
                    WHERE document_id = %s
                    ORDER BY critical DESC,
                             (abnormal IN ('low','high') OR report_flag IS NOT NULL) DESC,
                             panel NULLS LAST, printed_name""",
                (document_id,),
            )
            rows = cur.fetchall()
        conn.commit()
    return [_row_to_finding(row) for row in rows]


def trend_for(patient_id: str, canonical: str, limit: int = 24) -> list[dict]:
    """One measurement over time for one patient, oldest first — computed in SQL.

    Rule 2 of the grounding design: cross-report comparison is never done by a model. This
    is the whole of it — an ORDER BY, not an inference.

    Censored values ("<0.01") and unparseable ones are excluded: a trend line is a series
    of measurements, and a bound plotted as a point would misstate the history. They are
    still visible on the document itself.

    Only measurements sharing the most recent entry's UNIT are returned. A lab that
    switched from ng/mL to nmol/L would otherwise produce a step change that looks
    clinical and is purely a units artefact.
    """
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT unit FROM document_findings
                WHERE patient_id = %s AND canonical_name = %s
                  AND value_num IS NOT NULL AND value_operator IS NULL
                ORDER BY clinical_date DESC NULLS LAST, created_at DESC
                LIMIT 1
                """,
                (patient_id, canonical),
            )
            latest = cur.fetchone()
            if not latest:
                conn.commit()
                return []
            unit = latest[0]

            # DISTINCT ON (date, value, unit): the SAME reading arriving on several
            # documents — a report uploaded more than once, which does happen — is one
            # observation and must plot as one point. Two DIFFERENT values on one date are
            # kept, because two labs genuinely disagreeing is a clinical fact, not noise.
            cur.execute(
                """
                SELECT DISTINCT ON (clinical_date, value_num, unit)
                       value_num, unit, clinical_date, abnormal, ref_low, ref_high, document_id
                FROM document_findings
                WHERE patient_id = %s AND canonical_name = %s
                  AND value_num IS NOT NULL AND value_operator IS NULL
                  AND unit IS NOT DISTINCT FROM %s
                ORDER BY clinical_date ASC NULLS FIRST, value_num, unit, created_at ASC
                LIMIT %s
                """,
                (patient_id, canonical, unit, max(1, min(int(limit), 100))),
            )
            rows = cur.fetchall()
        conn.commit()

    return [
        {
            "value": float(row[0]), "unit": row[1],
            "clinical_date": row[2].isoformat() if row[2] else None,
            "abnormal": row[3],
            "ref_low": float(row[4]) if row[4] is not None else None,
            "ref_high": float(row[5]) if row[5] is not None else None,
            "document_id": row[6],
        }
        for row in rows
    ]


def trendable_measurements(patient_id: str, minimum_points: int = 2) -> list[dict]:
    """Which measurements this patient actually has a history for.

    A one-point "trend" is not a trend; offering it would fill the screen with lines that
    say nothing. Counted in SQL so the UI can ask once rather than probing per analyte.

    Counted by DISTINCT clinical_date, not by row. Found on real data: the same blood
    report had been uploaded three times, which produced three rows per analyte on one
    date and made every measurement in it look trendable. Three readings of the same draw
    are one observation, however many documents carry it — a trend needs movement over
    time, and time is the date, not the upload.
    """
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT canonical_name,
                       COUNT(DISTINCT clinical_date) AS dates,
                       COUNT(*) AS readings,
                       MAX(clinical_date) AS latest
                FROM document_findings
                WHERE patient_id = %s AND canonical_name IS NOT NULL
                  AND value_num IS NOT NULL AND value_operator IS NULL
                  AND clinical_date IS NOT NULL
                GROUP BY canonical_name
                HAVING COUNT(DISTINCT clinical_date) >= %s
                ORDER BY MAX(clinical_date) DESC NULLS LAST, canonical_name
                """,
                (patient_id, max(2, int(minimum_points))),
            )
            rows = cur.fetchall()
        conn.commit()
    return [
        {"canonical_name": row[0], "dates": int(row[1]), "readings": int(row[2]),
         "latest": row[3].isoformat() if row[3] else None}
        for row in rows
    ]


def abnormal_only(rows: list[dict]) -> list[dict]:
    """The subset a doctor should see as chips. Ordered high-then-low so the most likely
    to matter reads first; `unknown` is excluded because an unflagged value must not look
    like a cleared one."""
    flagged = [row for row in rows if row.get("abnormal") in (ABNORMAL_HIGH, ABNORMAL_LOW)]
    return sorted(flagged, key=lambda row: (row["abnormal"] != ABNORMAL_HIGH, row["canonical_name"] or ""))
