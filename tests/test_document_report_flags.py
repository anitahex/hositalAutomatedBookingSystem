"""Reading the report's own flag and printed range beside each result.

Pure — no database, no model.

The fixture is a real lab report's result tables, as stored in document_pages (the header
with the patient's name, phone and hospital numbers is left out — only the results are
needed), and the 48 measurements the extractor stored for it. On this report the lab flags
12 results. Before this change the doctor's viewer showed 8: RDW-CV and VLDL had no range in
code, ESR's "mm/1st hr" did not match "mm/hr", and the TC/HDL ratio was filed as HDL.
"""
from __future__ import annotations

import pytest

from app.services.document_findings import (
    ABNORMAL_HIGH,
    ABNORMAL_LOW,
    ABNORMAL_NORMAL,
    ABNORMAL_UNKNOWN,
    FLAG_SOURCE_REPORT_FLAG,
    FLAG_SOURCE_REPORT_RANGE,
    FLAG_SOURCE_STANDARD_RANGE,
    apply_report_flags,
    canonical_name,
    classify,
    classify_row,
    count_report_flags,
    flatten_findings,
    locate_printed_result,
    parse_measurement,
    parse_printed_range,
    to_number,
)

PAGE_1 = """HAEMATOLOGY - COMPLETE BLOOD COUNT (CBC)
Test Description Result Flag Units Biological Ref. Interval
Haemoglobin 13.1 g/dL 13.0 - 17.0
Total RBC Count 4.62 million/µL 4.5 - 5.5
Packed Cell Volume (PCV) 40.3 % 40 - 50
Mean Corpuscular Volume (MCV) 87.2 fL 83 - 101
Mean Corpuscular Hb (MCH) 28.4 pg 27 - 32
MCHC 32.5 g/dL 31.5 - 34.5
Red Cell Distribution Width (RDW-CV) 14.8 H % 11.6 - 14.0
Total Leucocyte Count 7,850 cells/µL 4,000 - 10,000
Differential Leucocyte Count
Neutrophils 68 % 40 - 80
Lymphocytes 24 % 20 - 40
Monocytes 6 % 2 - 10
Eosinophils 2 % 1 - 6
Basophils 0 % 0 - 2
Platelet Count 2.41 lakh/µL 1.50 - 4.10
ESR (Westergren) 14 H mm/1st hr 0 - 10
Method: Automated cell counter (impedance / flow cytometry); DLC verified by peripheral smear.
ENDOCRINOLOGY
Test Description Result Flag Units Biological Ref. Interval
Cortisol - Morning (08:00 AM) 24.6 H µg/dL 6.2 - 19.4
Thyroid Profile
TSH (Ultrasensitive) 3.84 µIU/mL 0.27 - 4.20
Free T3 2.61 pg/mL 2.00 - 4.40
Free T4 1.08 ng/dL 0.93 - 1.70
Method: Electrochemiluminescence Immunoassay (ECLIA). Sample drawn at 08:12 AM.
Results relate only to the sample tested. Kindly correlate clinically. Page 1"""

PAGE_2 = """VITAMINS & MINERALS
Test Description Result Flag Units Biological Ref. Interval
Deficient: < 20
Vitamin D, 25-Hydroxy (Total) 13.8 L ng/mL Insufficient: 20 - 29
Sufficient: 30 - 100
Vitamin B12 (Cyanocobalamin) 178 L pg/mL 211 - 911
Folic Acid (Serum) 4.2 ng/mL 3.1 - 20.5
Ferritin 38.5 ng/mL 30 - 400
Magnesium 1.8 mg/dL 1.6 - 2.6
Calcium, Total 9.1 mg/dL 8.6 - 10.2
Method: CLIA / ECLIA; Magnesium - Xylidyl blue; Calcium - Arsenazo III.
CLINICAL BIOCHEMISTRY
Test Description Result Flag Units Biological Ref. Interval
Glucose Metabolism
Glucose - Fasting (Plasma) 94 mg/dL 70 - 100
Normal: < 5.7
HbA1c (Glycated Haemoglobin) 5.4 %
Prediabetes: 5.7 - 6.4
Lipid Profile (12 hr fasting)
Total Cholesterol 204 H mg/dL Desirable: < 200
Triglycerides 176 H mg/dL Normal: < 150
HDL Cholesterol 38 L mg/dL > 40
Optimal: < 100
LDL Cholesterol (Calculated) 130.8 H mg/dL
Near optimal: 100 - 129
VLDL Cholesterol (Calculated) 35.2 H mg/dL < 30
Total Cholesterol / HDL Ratio 5.37 H Ratio < 5.0
Liver Function Test
Bilirubin, Total 0.8 mg/dL 0.3 - 1.2
Bilirubin, Direct 0.2 mg/dL 0.0 - 0.3
SGPT (ALT) 24 U/L < 41
SGOT (AST) 22 U/L < 40
Alkaline Phosphatase 86 U/L 40 - 129
Total Protein 7.2 g/dL 6.4 - 8.3
Albumin 4.3 g/dL 3.5 - 5.2
Kidney Function Test
Blood Urea 22 mg/dL 17 - 43
Serum Creatinine 0.94 mg/dL 0.70 - 1.30
eGFR (CKD-EPI 2021) 113 mL/min/1.73m² > 90
Uric Acid 5.6 mg/dL 3.5 - 7.2
Electrolytes
Sodium (Na+) 139 mmol/L 136 - 145
Potassium (K+) 4.2 mmol/L 3.5 - 5.1
Chloride (Cl-) 102 mmol/L 98 - 107
Method: Automated clinical chemistry analyser; HbA1c by HPLC (NGSP certified method).
Results relate only to the sample tested. Kindly correlate clinically. Page 2"""

PAGE_3 = """IMMUNOLOGY / INFLAMMATORY MARKERS
Test Description Result Flag Units Biological Ref. Interval
Low risk: < 1.0
hs-CRP (High Sensitivity C-Reactive
3.6 H mg/L Average: 1.0 - 3.0
Protein)
High: > 3.0
Method: Immunoturbidimetry.
Interpretive Comments
1. Morning serum cortisol is elevated. Values may be raised by physiological or psychological stress, sleep disturbance, acute illness
2. Vitamin D (25-OH) is in the deficient range and Vitamin B12 is below the reference interval. Serum folate and ferritin are within
3. Mildly raised hs-CRP and ESR suggest low-grade systemic inflammation; non-specific finding.
4. Dyslipidaemic pattern noted: raised triglycerides and LDL with low HDL.
5. Thyroid function tests are within reference limits (TSH in upper-normal range).
*** End of Report ***
Results relate only to the sample tested. Kindly correlate clinically. Page 3"""

PAGES = [
    {"page_no": 1, "text": PAGE_1},
    {"page_no": 2, "text": PAGE_2},
    {"page_no": 3, "text": PAGE_3},
]

# (printed name as the extractor stored it, value as it stored it)
STORED = [
    ("Basophils", "0 %"), ("ESR (Westergren)", "14 mm/1st hr"), ("Eosinophils", "2 %"),
    ("Haemoglobin", "13.1 g/dL"), ("Lymphocytes", "24 %"), ("MCHC", "32.5 g/dL"),
    ("Mean Corpuscular Hb (MCH)", "28.4 pg"), ("Mean Corpuscular Volume (MCV)", "87.2 fL"),
    ("Monocytes", "6 %"), ("Neutrophils", "68 %"), ("Packed Cell Volume (PCV)", "40.3 %"),
    ("Platelet Count", "2.41 lakh/µL"), ("Red Cell Distribution Width (RDW-CV)", "14.8 %"),
    ("Total Leucocyte Count", "7,850 cells/µL"), ("Total RBC Count", "4.62 million/µL"),
    ("Albumin", "4.3 g/dL"), ("Alkaline Phosphatase", "86 U/L"), ("Bilirubin, Direct", "0.2 mg/dL"),
    ("Bilirubin, Total", "0.8 mg/dL"), ("Blood Urea", "22 mg/dL"), ("Chloride (Cl-)", "102 mmol/L"),
    ("Glucose - Fasting (Plasma)", "94 mg/dL"), ("HDL Cholesterol", "38 mg/dL"),
    ("HbA1c (Glycated Haemoglobin)", "5.4 %"), ("LDL Cholesterol (Calculated)", "130.8 mg/dL"),
    ("Potassium (K+)", "4.2 mmol/L"), ("SGOT (AST)", "22 U/L"), ("SGPT (ALT)", "24 U/L"),
    ("Serum Creatinine", "0.94 mg/dL"), ("Sodium (Na+)", "139 mmol/L"),
    ("Total Cholesterol", "204 mg/dL"), ("Total Cholesterol / HDL Ratio", "5.37"),
    ("Total Protein", "7.2 g/dL"), ("Triglycerides", "176 mg/dL"), ("Uric Acid", "5.6 mg/dL"),
    ("VLDL Cholesterol (Calculated)", "35.2 mg/dL"), ("eGFR (CKD-EPI 2021)", "113 mL/min/1.73m²"),
    ("Cortisol - Morning", "24.6 µg/dL"), ("Free T3", "2.61 pg/mL"), ("Free T4", "1.08 ng/dL"),
    ("TSH (Ultrasensitive)", "3.84 µIU/mL"),
    ("hs-CRP (High Sensitivity C-Reactive Protein)", "3.6 mg/L"),
    ("Calcium, Total", "9.1 mg/dL"), ("Ferritin", "38.5 ng/mL"), ("Folic Acid (Serum)", "4.2 ng/mL"),
    ("Magnesium", "1.8 mg/dL"), ("Vitamin B12 (Cyanocobalamin)", "178 pg/mL"),
    ("Vitamin D, 25-Hydroxy (Total)", "13.8 ng/mL"),
]

# What the lab itself marked, and which way.
LAB_FLAGGED = {
    "Red Cell Distribution Width (RDW-CV)": ABNORMAL_HIGH,
    "ESR (Westergren)": ABNORMAL_HIGH,
    "Cortisol - Morning": ABNORMAL_HIGH,
    "Vitamin D, 25-Hydroxy (Total)": ABNORMAL_LOW,
    "Vitamin B12 (Cyanocobalamin)": ABNORMAL_LOW,
    "Total Cholesterol": ABNORMAL_HIGH,
    "Triglycerides": ABNORMAL_HIGH,
    "HDL Cholesterol": ABNORMAL_LOW,
    "LDL Cholesterol (Calculated)": ABNORMAL_HIGH,
    "VLDL Cholesterol (Calculated)": ABNORMAL_HIGH,
    "Total Cholesterol / HDL Ratio": ABNORMAL_HIGH,
    "hs-CRP (High Sensitivity C-Reactive Protein)": ABNORMAL_HIGH,
}


def _row(name: str, value_text: str) -> dict:
    value, unit, operator = parse_measurement(value_text)
    return {"name": name, "canonical_name": canonical_name(name), "value_text": value_text,
            "value_num": value, "unit": unit, "operator": operator}


@pytest.fixture(scope="module")
def classified() -> dict[str, dict]:
    rows = apply_report_flags([_row(name, value) for name, value in STORED], PAGES)
    return {row["name"]: row for row in rows}


# ---- the whole report ----

def test_exactly_the_results_the_lab_flagged_are_flagged(classified):
    flagged = {
        name: row["abnormal"] for name, row in classified.items()
        if row["abnormal"] in (ABNORMAL_LOW, ABNORMAL_HIGH)
    }
    assert flagged == LAB_FLAGGED


def test_every_lab_flag_is_attributed_to_the_report(classified):
    for name in LAB_FLAGGED:
        assert classified[name]["flag_source"] == FLAG_SOURCE_REPORT_FLAG, name


def test_every_result_is_found_on_its_page(classified):
    """48 of 48 located, so every flag and range came from the line the value is on."""
    unlocated = [name for name, row in classified.items() if row["page_no"] is None]
    assert unlocated == []
    assert classified["hs-CRP (High Sensitivity C-Reactive Protein)"]["page_no"] == 3
    assert classified["Haemoglobin"]["page_no"] == 1


def test_the_report_flag_count_matches_what_is_listed(classified):
    listed = sum(1 for row in classified.values() if row["flag_source"] == FLAG_SOURCE_REPORT_FLAG)
    assert count_report_flags(PAGES) == 12 == listed


def test_a_result_the_extractor_missed_shows_up_in_the_count():
    """If the extractor never read RDW-CV, the report still marks 12 and we list 11 — the
    viewer says so instead of presenting 11 as the whole list."""
    rows = apply_report_flags(
        [_row(name, value) for name, value in STORED if not name.startswith("Red Cell")], PAGES
    )
    listed = sum(1 for row in rows if row["flag_source"] == FLAG_SOURCE_REPORT_FLAG)
    assert (count_report_flags(PAGES), listed) == (12, 11)


# ---- the four that used to be missed ----

def test_rdw_is_flagged_by_the_report_with_its_printed_range(classified):
    row = classified["Red Cell Distribution Width (RDW-CV)"]
    assert (row["abnormal"], row["report_flag"], row["report_ref_text"]) == (ABNORMAL_HIGH, "H", "11.6 - 14.0")
    assert (row["ref_low"], row["ref_high"], row["ref_source"]) == (11.6, 14.0, "report")


def test_esr_is_flagged_by_the_labs_own_range_not_ours(classified):
    """Our standard ESR range is 0 - 20, which would call 14 normal. This lab prints 0 - 10
    and flags it H — the report's verdict is the one shown."""
    row = classified["ESR (Westergren)"]
    assert (row["abnormal"], row["flag_source"], row["report_ref_text"]) == (
        ABNORMAL_HIGH, FLAG_SOURCE_REPORT_FLAG, "0 - 10",
    )
    # "mm/1st hr" is now comparable to "mm/hr" at all, instead of 'unknown'.
    assert classify("ESR", 14.0, "mm/1st hr") == ABNORMAL_NORMAL
    assert classify("ESR", 24.0, "mm/1st hr") == ABNORMAL_HIGH


def test_the_ratio_is_flagged_as_the_ratio_not_as_hdl(classified):
    row = classified["Total Cholesterol / HDL Ratio"]
    assert row["canonical_name"] == "Total Cholesterol HDL Ratio"
    assert (row["abnormal"], row["report_ref_text"]) == (ABNORMAL_HIGH, "< 5.0")


def test_vldl_is_flagged_by_the_report(classified):
    assert classified["VLDL Cholesterol (Calculated)"]["abnormal"] == ABNORMAL_HIGH


# ---- reading a line correctly ----

def test_a_name_that_wraps_onto_the_next_line_is_still_matched(classified):
    row = classified["hs-CRP (High Sensitivity C-Reactive Protein)"]
    assert (row["abnormal"], row["report_flag"]) == (ABNORMAL_HIGH, "H")


def test_a_band_is_never_taken_for_the_reference_range(classified):
    """Vitamin D's line prints "Insufficient: 20 - 29". Taking that as the range would make
    13.8 merely low-ish; taking a later band could call it normal. The flag decides, and the
    range shown is labelled as the standard one, not the report's."""
    row = classified["Vitamin D, 25-Hydroxy (Total)"]
    assert row["report_flag"] == "L" and row["report_ref_text"] is None
    assert row["ref_source"] == "standard"
    crp = classified["hs-CRP (High Sensitivity C-Reactive Protein)"]
    assert crp["report_ref_text"] is None, "Average: 1.0 - 3.0 is a band"


def test_a_thousands_separator_is_not_a_decimal_point(classified):
    """7,850 was stored as 7.85 — a severe LOW against 4,000 - 10,000, from a normal count."""
    row = classified["Total Leucocyte Count"]
    assert row["value_num"] == 7850.0
    assert (row["ref_low"], row["ref_high"]) == (4000.0, 10000.0)
    assert row["abnormal"] == ABNORMAL_NORMAL and row["flag_source"] == FLAG_SOURCE_REPORT_RANGE


def test_an_unflagged_value_is_judged_by_the_reports_range_not_ours(classified):
    """TSH 3.84: the report prints 0.27 - 4.20; ours is 0.4 - 4.0. The report's applies."""
    row = classified["TSH (Ultrasensitive)"]
    assert (row["abnormal"], row["flag_source"], row["ref_high"]) == (ABNORMAL_NORMAL, FLAG_SOURCE_REPORT_RANGE, 4.2)


def test_the_standard_range_is_used_only_when_the_report_prints_none(classified):
    row = classified["HbA1c (Glycated Haemoglobin)"]
    assert (row["flag_source"], row["ref_source"]) == (FLAG_SOURCE_STANDARD_RANGE, "standard")


def test_flatten_alone_uses_only_the_standard_range():
    """Before the page text is at hand nothing is claimed from the report."""
    row = flatten_findings({"Vitamin D": "13.8 ng/mL"})[0]
    assert (row["abnormal"], row["flag_source"], row["report_flag"]) == (
        ABNORMAL_LOW, FLAG_SOURCE_STANDARD_RANGE, None,
    )


# ---- the pieces ----

@pytest.mark.parametrize("token,expected", [
    ("7,850", 7850.0), ("10,000", 10000.0), ("1,234,567.5", 1234567.5),
    ("13,8", 13.8), ("0,25", 0.25), ("14.8", 14.8), ("", None), ("abc", None),
])
def test_to_number(token, expected):
    assert to_number(token) == expected


@pytest.mark.parametrize("text,low,high,printed", [
    (" % 11.6 - 14.0", 11.6, 14.0, "11.6 - 14.0"),
    (" U/L < 41", None, 41.0, "< 41"),
    (" mg/dL > 40", 40.0, None, "> 40"),
    (" mg/dL Desirable: < 200", None, 200.0, "Desirable: < 200"),
    (" cells/µL 4,000 - 10,000", 4000.0, 10000.0, "4,000 - 10,000"),
    (" mm/1st hr 0 - 10", 0.0, 10.0, "0 - 10"),
    (" mL/min/1.73m² > 90", 90.0, None, "> 90"),
    (" mg/dL Reference range: 70 to 100", 70.0, 100.0, "Reference range: 70 to 100"),
])
def test_a_printed_range_is_read(text, low, high, printed):
    parsed = parse_printed_range(text)
    assert (parsed["low"], parsed["high"], parsed["text"]) == (low, high, printed)


@pytest.mark.parametrize("text", [
    " ng/mL Insufficient: 20 - 29",
    " mg/L Average: 1.0 - 3.0",
    " %",
    "",
    " mg/dL 10 - 2",
])
def test_no_range_is_invented(text):
    assert parse_printed_range(text) is None


def test_a_bound_is_exclusive_where_the_report_says_less_than():
    """"< 200" means 200 itself is not desirable."""
    row = {"name": "Total Cholesterol", "canonical_name": "Total Cholesterol",
           "value_text": "200 mg/dL", "value_num": 200.0, "unit": "mg/dL"}
    pages = [{"page_no": 1, "text": "Total Cholesterol 200 mg/dL Desirable: < 200"}]
    assert apply_report_flags([row], pages)[0]["abnormal"] == ABNORMAL_HIGH


@pytest.mark.parametrize("line", [
    "Sodium (Na+) 139 mmol/L 136 - 145",
    "HDL Cholesterol 38 mg/dL > 40",
    "Lumbar spine 5 L4-L5 disc",
    "hs-CRP 0.5 Low risk: < 1.0",
])
def test_things_that_look_like_flags_are_not(line):
    assert count_report_flags([{"page_no": 1, "text": line}]) == 0


def test_a_flag_printed_after_the_unit_is_read():
    row = _row("Red Cell Distribution Width (RDW-CV)", "14.8 %")
    found = locate_printed_result(row, [{"page_no": 1, "text": "Red Cell Distribution Width (RDW-CV) 14.8 % H 11.6 - 14.0"}])
    assert found["flag"] == "H"
    assert found["range"]["text"] == "11.6 - 14.0"


def test_a_critical_flag_is_marked_critical():
    row = _row("Potassium (K+)", "6.9 mmol/L")
    out = apply_report_flags([row], [{"page_no": 1, "text": "Potassium (K+) 6.9 HH mmol/L 3.5 - 5.1"}])[0]
    assert (out["abnormal"], out["critical"], out["report_flag"]) == (ABNORMAL_HIGH, True, "HH")


def test_a_star_takes_its_direction_from_the_printed_range():
    row = _row("Uric Acid", "8.1 mg/dL")
    out = apply_report_flags([row], [{"page_no": 1, "text": "Uric Acid 8.1 * mg/dL 3.5 - 7.2"}])[0]
    assert (out["abnormal"], out["flag_source"], out["critical"]) == (ABNORMAL_HIGH, FLAG_SOURCE_REPORT_FLAG, False)


def test_a_value_is_never_matched_to_a_different_results_line():
    """The value must follow its OWN name. 38 appears on the HDL line; asked about LDL, it
    must not borrow HDL's "L"."""
    row = _row("LDL Cholesterol", "38 mg/dL")
    assert locate_printed_result(row, [{"page_no": 1, "text": "HDL Cholesterol 38 L mg/dL > 40"}]) is None


def test_a_value_inside_a_longer_number_is_not_a_match():
    row = _row("ESR", "14 mm/hr")
    assert locate_printed_result(row, [{"page_no": 1, "text": "ESR 14.8 H mm/hr 0 - 10"}]) is None


def test_with_no_page_text_nothing_is_claimed_from_the_report():
    out = classify_row(_row("Vitamin D", "13.8 ng/mL"), None)
    assert out["report_flag"] is None and out["flag_source"] == FLAG_SOURCE_STANDARD_RANGE


def test_a_censored_value_is_still_never_compared_to_a_range():
    row = _row("TSH", "<0.01 uIU/mL")
    out = apply_report_flags([row], [{"page_no": 1, "text": "TSH <0.01 uIU/mL 0.27 - 4.20"}])[0]
    assert out["abnormal"] == ABNORMAL_UNKNOWN


def test_a_censored_value_the_lab_flags_is_still_flagged():
    """The flag is the lab's statement, not a comparison we make."""
    row = _row("TSH", "<0.01 uIU/mL")
    out = apply_report_flags([row], [{"page_no": 1, "text": "TSH <0.01 L uIU/mL 0.27 - 4.20"}])[0]
    assert (out["abnormal"], out["flag_source"]) == (ABNORMAL_LOW, FLAG_SOURCE_REPORT_FLAG)


@pytest.mark.parametrize("printed,expected", [
    ("VLDL Cholesterol (Calculated)", "VLDL Cholesterol"),
    ("SGOT (AST)", "SGOT"),
    ("Total RBC Count", "Total RBC Count"),
    ("Blood Urea", "Blood Urea"),
])
def test_an_analyte_outside_the_known_list_keeps_its_acronyms(printed, expected):
    """It was shown as "Vldl Cholesterol" and "Sgot" on the viewer and the overview."""
    assert canonical_name(printed) == expected
