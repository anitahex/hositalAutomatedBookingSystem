"""Turning extracted findings into comparable measurements.

Pure — no database, no model.

The safety argument these protect: a model reads the document, but it never decides
whether a result is abnormal and it never compares two reports. Those judgements are
computed here, so they can be tested exhaustively and cannot drift with a prompt.

The fixture is a real report's shape, taken from stored data: findings are nested
panel -> {analyte: "value unit"}, analyte names are whatever the lab printed, and no
reference ranges are included.
"""
from __future__ import annotations

import pytest

from app.services.document_findings import (
    ABNORMAL_HIGH,
    ABNORMAL_LOW,
    ABNORMAL_NORMAL,
    ABNORMAL_UNKNOWN,
    REFERENCE_RANGES,
    abnormal_only,
    canonical_name,
    classify,
    flatten_findings,
    normalize_unit,
    parse_measurement,
)

REAL_FINDINGS = {
    "CBC": {
        "Haemoglobin": "13.1 g/dL",
        "Mean Corpuscular Hb (MCH)": "28.4 pg",
        "MCHC": "32.5 g/dL",
    },
    "Endocrinology": {
        "Cortisol - Morning (08:00 AM)": "24.6 µg/dL",
        "TSH (Ultrasensitive)": "3.84 µIU/mL",
    },
    "Vitamins & Minerals": {
        "Vitamin D, 25-Hydroxy (Total)": "13.8 ng/mL",
        "Vitamin B12 (Cyanocobalamin)": "178 pg/mL",
    },
}


# ---- parsing a printed value ----

@pytest.mark.parametrize(
    "raw,value,unit",
    [
        ("13.8 ng/mL", 13.8, "ng/mL"),
        ("178 pg/mL", 178.0, "pg/mL"),
        ("5.4 %", 5.4, "%"),
        ("4.62 million/uL", 4.62, "million/uL"),
        ("24.6 µg/dL", 24.6, "µg/dL"),
        ("13,8 ng/mL", 13.8, "ng/mL"),
        ("94", 94.0, None),
    ],
)
def test_a_printed_value_is_split_into_number_and_unit(raw, value, unit):
    parsed_value, parsed_unit, _ = parse_measurement(raw)
    assert parsed_value == pytest.approx(value)
    assert parsed_unit == unit


def test_a_censored_value_keeps_its_operator():
    """"<0.01" is not 0.01. Plotting or comparing it as an exact number would assert
    precision the lab explicitly declined to give."""
    value, unit, operator = parse_measurement("<0.01 mIU/L")
    assert value == pytest.approx(0.01)
    assert operator == "<"


def test_a_censored_value_is_never_classified():
    rows = flatten_findings({"TSH": "<0.01 uIU/mL"})
    assert rows[0]["abnormal"] == ABNORMAL_UNKNOWN


@pytest.mark.parametrize("raw", ["", None, "   ", "[Incomplete/Illegible text in document]", "Normal"])
def test_a_non_numeric_value_yields_no_number(raw):
    assert parse_measurement(raw)[0] is None


def test_an_unreadable_value_is_kept_rather_than_dropped():
    """"Measured but could not be read" is information a doctor should see. Dropping it
    would make the document look as though the test was never done."""
    rows = flatten_findings({"Ferritin": "[Incomplete/Illegible text in document]"})
    assert len(rows) == 1
    assert rows[0]["value_num"] is None
    assert rows[0]["value_text"]


# ---- canonical names ----

@pytest.mark.parametrize(
    "printed,expected",
    [
        ("Vitamin D, 25-Hydroxy (Total)", "Vitamin D"),
        ("25-OH Vitamin D", "Vitamin D"),
        ("Vitamin D (25-OH)", "Vitamin D"),
        ("Vitamin B12 (Cyanocobalamin)", "Vitamin B12"),
        ("Cortisol - Morning (08:00 AM)", "Cortisol (morning)"),
        ("TSH (Ultrasensitive)", "TSH"),
        ("Hemoglobin", "Haemoglobin"),
        ("Haemoglobin", "Haemoglobin"),
    ],
)
def test_one_measurement_has_one_canonical_name(printed, expected):
    """A trend joins on this. Three spellings of Vitamin D that did not collapse would
    render as three one-point series, which looks like no history rather than like a bug."""
    assert canonical_name(printed) == expected


@pytest.mark.parametrize(
    "printed,expected",
    [("Mean Corpuscular Hb (MCH)", "MCH"), ("MCHC", "MCHC"), ("Mean Corpuscular Volume (MCV)", "MCV")],
)
def test_the_corpuscular_indices_are_not_haemoglobin(printed, expected):
    """Found on real data: "Mean Corpuscular Hb (MCH)" contains the token "hb" and was
    canonicalising to Haemoglobin. The unit guard stopped it producing a wrong FLAG
    (28.4 pg against a g/dL range), but a trend groups by canonical name alone, so MCH
    points would have been plotted silently into a haemoglobin series."""
    assert canonical_name(printed) == expected
    assert canonical_name(printed) != "Haemoglobin"


@pytest.mark.parametrize(
    "printed,expected",
    [
        ("Total Cholesterol / HDL Ratio", "Total Cholesterol HDL Ratio"),
        ("LDL/HDL Ratio", "LDL HDL Ratio"),
        ("HDL Cholesterol Ratio", "HDL Cholesterol Ratio"),
    ],
)
def test_a_ratio_is_its_own_measurement(printed, expected):
    """Found on real data: "Total Cholesterol / HDL Ratio" contains "hdl" and was stored AS
    HDL Cholesterol with HDL's 40-100 mg/dL range. 5.37 then sat in the HDL series beside
    38.0, and the at-a-glance card, taking one HDL reading per date, could pick the ratio
    and drop the patient's real (low) HDL result."""
    assert canonical_name(printed) == expected
    for analyte in ("HDL Cholesterol", "LDL Cholesterol", "Total Cholesterol"):
        assert canonical_name(printed) != analyte


def test_the_analytes_themselves_are_unchanged_by_the_ratio_rule():
    assert canonical_name("HDL Cholesterol") == "HDL Cholesterol"
    assert canonical_name("LDL Cholesterol (Calculated)") == "LDL Cholesterol"
    assert canonical_name("Total Cholesterol") == "Total Cholesterol"


def test_a_ratio_gets_no_analyte_reference_range():
    """With its own name it has no range, so it is never flagged against one."""
    assert classify(canonical_name("Total Cholesterol / HDL Ratio"), 5.37, None) == ABNORMAL_UNKNOWN


# ---- classification is computed, and refuses to guess ----

def test_a_value_below_the_range_is_low_and_above_it_is_high():
    assert classify("Vitamin D", 13.8, "ng/mL") == ABNORMAL_LOW
    assert classify("Vitamin D", 55.0, "ng/mL") == ABNORMAL_NORMAL
    assert classify("Cortisol (morning)", 24.6, "ug/dL") == ABNORMAL_HIGH


def test_a_value_in_the_wrong_unit_is_never_classified():
    """Vitamin D in nmol/L is ~2.5x the same result in ng/mL. Comparing it to a ng/mL
    range would invert "deficient" and "normal" — the single most dangerous thing this
    module could do."""
    assert classify("Vitamin D", 75.0, "nmol/L") == ABNORMAL_UNKNOWN
    assert classify("Vitamin D", 75.0, None) == ABNORMAL_UNKNOWN


def test_micro_sign_variants_are_the_same_unit():
    """PDF extraction mangles µ into several codepoints. Treating those as different
    units would silently drop the flag on every cortisol result."""
    for micro in ("µg/dL", "μg/dL", "ug/dL", "mcg/dL", "�g/dL"):
        assert classify("Cortisol (morning)", 24.6, micro) == ABNORMAL_HIGH
        assert normalize_unit(micro) == "ugdl"


def test_an_analyte_with_no_reference_range_is_unknown_not_normal():
    """Unknown renders as no flag. Calling it normal would tell a doctor a result had been
    checked against a range that was never applied."""
    assert "Total Rbc Count" not in REFERENCE_RANGES
    assert classify("Total Rbc Count", 4.62, "million/uL") == ABNORMAL_UNKNOWN


def test_unknown_is_excluded_from_the_chips():
    """An unflagged value must not sit beside flagged ones looking cleared."""
    rows = flatten_findings(REAL_FINDINGS)
    assert all(row["abnormal"] in (ABNORMAL_HIGH, ABNORMAL_LOW) for row in abnormal_only(rows))


# ---- the real document shape ----

def test_the_nested_panel_shape_is_flattened():
    rows = flatten_findings(REAL_FINDINGS)
    by_name = {row["canonical_name"]: row for row in rows}

    assert by_name["Vitamin D"]["value_num"] == pytest.approx(13.8)
    assert by_name["Vitamin D"]["panel"] == "Vitamins & Minerals"
    assert by_name["Vitamin B12"]["abnormal"] == ABNORMAL_LOW


def test_the_flat_shape_the_schema_specifies_also_works():
    """Both shapes occur in stored data, so both are read rather than one being declared
    wrong after the fact."""
    rows = flatten_findings({"Vitamin D": "13.8 ng/mL"})
    assert rows[0]["canonical_name"] == "Vitamin D"
    assert rows[0]["abnormal"] == ABNORMAL_LOW


def test_the_flags_match_the_reports_own_impression():
    """Independent corroboration on the real document: the extractor's prose impression
    said elevated cortisol, deficient Vitamin D and low B12. The flags are computed from
    the numbers by a separate path and must agree."""
    flagged = {row["canonical_name"]: row["abnormal"] for row in abnormal_only(flatten_findings(REAL_FINDINGS))}

    assert flagged["Cortisol (morning)"] == ABNORMAL_HIGH
    assert flagged["Vitamin D"] == ABNORMAL_LOW
    assert flagged["Vitamin B12"] == ABNORMAL_LOW


def test_high_flags_sort_before_low_ones():
    rows = abnormal_only(flatten_findings(REAL_FINDINGS))
    assert [row["abnormal"] for row in rows] == sorted(
        [row["abnormal"] for row in rows], key=lambda value: value != ABNORMAL_HIGH
    )


@pytest.mark.parametrize("bad", [None, [], "text", 42, {"panel": None}, {"panel": {"a": None}}])
def test_malformed_findings_never_raise(bad):
    assert isinstance(flatten_findings(bad), list)
