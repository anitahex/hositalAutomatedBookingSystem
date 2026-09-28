"""Every line of a document is accounted for — the check behind "the summary misses nothing".

Pure — no database, no model. The fixture is a real handwritten prescription's stored
transcription. A summary prompt written for lab reports ("one sentence per abnormal
finding") reduced its summary to a single sentence about the MRI, and every medication,
the physiotherapy and the exercises vanished without anything noticing. These tests pin
the check that now notices: a line in no verified sentence, no parsed result and no
verified non-clinical list is returned, to be shown to the doctor as written.
"""
from __future__ import annotations

from app.services.document_grounding import (
    LEGACY_SUMMARY_VERSIONS,
    SUMMARY_PROMPT_VERSION,
    SUMMARY_SYSTEM,
    build_summary_user_content,
    structural_lines,
    uncovered_lines,
    verify_not_clinical,
)

PRESCRIPTION = [{"page_no": 1, "text": """RH/00/00000
01/1/22

Test Patient
23/M

- LBA c Rt LL Numbness

MRI L5/S1-C3, L4 Butterfly Vertebra
- Degenerative changes +

Adv S.Vit B12, S.Vit D
- wear L-S Belt
- Tab Duxilaf Habs BD x 7 days
(FF) then OD

Physiotherapy
Back Strengthening
exercise

- Tab Gabantin - NT 400/100 BD x 15 days
- Cap Rarpen 1 OD x 15 days
- Tab Drol-D 100 x 15 days

R/A 15 days"""}]

# What the lab-report prompt produced for it: one sentence.
ONE_SENTENCE = [{
    "text": "Degenerative changes noted at L5/S1-C3, L4 Butterfly Vertebra.",
    "quote": "MRI L5/S1-C3, L4 Butterfly Vertebra\n- Degenerative changes +",
    "page_no": 1,
}]

COMPLETE = [
    {"text": "Complaint: low back ache with right lower-limb numbness.", "quote": "- LBA c Rt LL Numbness"},
    {"text": "MRI: L4 butterfly vertebra with degenerative changes.", "quote": "MRI L5/S1-C3, L4 Butterfly Vertebra\n- Degenerative changes +"},
    {"text": "Serum vitamin B12 and vitamin D advised.", "quote": "Adv S.Vit B12, S.Vit D"},
    {"text": "Advised to wear an L-S belt.", "quote": "- wear L-S Belt"},
    {"text": "Tab Duxilaf BD for 7 days, then OD.", "quote": "- Tab Duxilaf Habs BD x 7 days\n(FF) then OD"},
    {"text": "Physiotherapy with back-strengthening exercise.", "quote": "Physiotherapy\nBack Strengthening\nexercise"},
    {"text": "Tab Gabantin-NT 400/100 BD for 15 days.", "quote": "- Tab Gabantin - NT 400/100 BD x 15 days"},
    {"text": "Cap Rarpen 1 OD for 15 days.", "quote": "- Cap Rarpen 1 OD x 15 days"},
    {"text": "Tab Drol-D 100 for 15 days.", "quote": "- Tab Drol-D 100 x 15 days"},
    {"text": "Review after 15 days.", "quote": "R/A 15 days"},
]
SET_ASIDE = ["RH/00/00000", "Test Patient", "23/M"]


def _texts(lines):
    return [line["text"] for line in lines]


def test_the_one_sentence_summary_leaves_every_medication_and_instruction_uncovered():
    """The bug, as the check now sees it."""
    missed = _texts(uncovered_lines(PRESCRIPTION, ONE_SENTENCE, SET_ASIDE, []))
    for expected in ("- Tab Gabantin - NT 400/100 BD x 15 days", "- Cap Rarpen 1 OD x 15 days",
                     "- Tab Drol-D 100 x 15 days", "- Tab Duxilaf Habs BD x 7 days", "Physiotherapy",
                     "Back Strengthening", "exercise", "- wear L-S Belt", "Adv S.Vit B12, S.Vit D",
                     "R/A 15 days", "- LBA c Rt LL Numbness"):
        assert expected in missed, expected


def test_a_complete_summary_leaves_nothing_uncovered():
    assert uncovered_lines(PRESCRIPTION, COMPLETE, SET_ASIDE, []) == []


def test_a_sentence_dropped_at_verification_does_not_take_its_line_with_it():
    """Dropping an unverifiable sentence must surface its line, not lose it."""
    without_rarpen = [s for s in COMPLETE if "Rarpen" not in s["text"]]
    assert _texts(uncovered_lines(PRESCRIPTION, without_rarpen, SET_ASIDE, [])) == ["- Cap Rarpen 1 OD x 15 days"]


def test_a_line_nobody_set_aside_is_still_shown():
    assert _texts(uncovered_lines(PRESCRIPTION, COMPLETE, [], [])) == ["RH/00/00000", "Test Patient", "23/M"]


def test_lines_without_words_are_not_counted():
    """"01/1/22" is a date, "(2)" a page mark: nothing a summary could leave out."""
    assert "01/1/22" not in _texts(uncovered_lines(PRESCRIPTION, [], [], []))


def test_parsed_result_lines_count_as_covered():
    """A lab report's normal results are listed by code, not by the summary."""
    page = [{"page_no": 1, "text": "Haemoglobin 13.1 g/dL 13.0 - 17.0\nRDW-CV 14.8 H % 11.6 - 14.0"}]
    sentences = [{"text": "RDW high at 14.8%.", "quote": "RDW-CV 14.8 H % 11.6 - 14.0"}]
    assert uncovered_lines(page, sentences, [], ["Haemoglobin 13.1 g/dL 13.0 - 17.0"]) == []
    assert _texts(uncovered_lines(page, sentences, [], [])) == ["Haemoglobin 13.1 g/dL 13.0 - 17.0"]


# ---- the set-aside list is checked, not trusted ----

def test_a_set_aside_line_must_really_be_on_the_page():
    kept = verify_not_clinical(["Test Patient", "Dr. Somebody Else", "", 42, "RH/00/00000"], PRESCRIPTION)
    assert kept == ["Test Patient", "RH/00/00000"]


def test_a_misquoted_set_aside_line_leaves_the_real_line_uncovered():
    kept = verify_not_clinical(["Test Patiant"], PRESCRIPTION)
    assert "Test Patient" in _texts(uncovered_lines(PRESCRIPTION, COMPLETE, kept, []))


# ---- what the model is asked for ----

def test_the_prompt_asks_for_every_medication_and_instruction_not_only_abnormal_findings():
    for required in ("EVERY medication", "every non-drug instruction", "physiotherapy",
                     "the follow-up or review", "not_clinical", "ACCOUNT FOR EVERY LINE"):
        assert required in SUMMARY_SYSTEM, required
    assert SUMMARY_PROMPT_VERSION not in LEGACY_SUMMARY_VERSIONS


def test_the_model_is_told_what_kind_of_document_it_is():
    content = build_summary_user_content(PRESCRIPTION, "prescription")
    assert content.startswith("Document type (as extracted): prescription")
    assert "--- PAGE 1 ---" in content
    assert not build_summary_user_content(PRESCRIPTION).startswith("Document type")


# ---- found on the real lab report and MRI ----

LAB = [{"page_no": 2, "text": """CLINICAL BIOCHEMISTRY
Test Description Result Flag Units Biological Ref. Interval
Glucose Metabolism
Glucose - Fasting (Plasma) 94 mg/dL 70 - 100
Normal: < 5.7
HbA1c (Glycated Haemoglobin) 5.4 %
Prediabetes: 5.7 - 6.4
Liver Function Test
Bilirubin, Total 0.8 mg/dL 0.3 - 1.2
Interpretive Comments
1. Morning serum cortisol is elevated. Values may be raised by physiological or psychological stress
2. Vitamin D (25-OH) is in the deficient range and Vitamin B12 is below the reference interval."""}]
LAB_RESULTS = ["Glucose - Fasting (Plasma) 94 mg/dL 70 - 100", "HbA1c (Glycated Haemoglobin) 5.4 %",
               "Bilirubin, Total 0.8 mg/dL 0.3 - 1.2"]


def test_the_labs_interpretive_comments_cannot_be_set_aside_as_non_clinical():
    """The model did exactly this on the real report. A set-aside line with a clinical term
    is refused, so it stays uncovered and is shown."""
    kept = verify_not_clinical([
        "1. Morning serum cortisol is elevated. Values may be raised by physiological or psychological stress",
        "2. Vitamin D (25-OH) is in the deficient range and Vitamin B12 is below the reference interval.",
        "CLINICAL BIOCHEMISTRY",
    ], LAB)
    assert kept == ["CLINICAL BIOCHEMISTRY"]
    missed = [line["text"] for line in uncovered_lines(LAB, [], kept, LAB_RESULTS)]
    assert any(text.startswith("1. Morning serum cortisol is elevated") for text in missed)
    assert any(text.startswith("2. Vitamin D (25-OH)") for text in missed)


def test_a_results_tables_layout_is_not_reported_as_missed():
    """Twenty-three headings, column headers and reference bands were listed as "not in the
    summary" on the real report, burying anything that really was missed."""
    missed = [line["text"] for line in uncovered_lines(LAB, [], ["CLINICAL BIOCHEMISTRY"], LAB_RESULTS)]
    for layout in ("Test Description Result Flag Units Biological Ref. Interval", "Normal: < 5.7",
                   "Prediabetes: 5.7 - 6.4", "Glucose Metabolism", "Liver Function Test"):
        assert layout not in missed, layout
    layout = [line["text"] for line in structural_lines(LAB, LAB_RESULTS)]
    assert "Liver Function Test" in layout and "Normal: < 5.7" in layout


def test_a_short_prescription_line_is_content_not_a_heading():
    """"Physiotherapy" is short and has no digits, like a heading — but no results follow it."""
    assert structural_lines(PRESCRIPTION, []) == []
    assert "Physiotherapy" in [line["text"] for line in uncovered_lines(PRESCRIPTION, ONE_SENTENCE, SET_ASIDE, [])]


def test_a_short_line_can_be_quoted_when_the_quote_is_the_whole_line():
    """"R/A 15 days" is 11 characters, under the 12 a quote needs, so the review instruction
    could never be verified — and was dropped from the real prescription's summary."""
    from app.services.document_grounding import quote_is_grounded, verify_sentences

    assert quote_is_grounded("R/A 15 days", PRESCRIPTION[0]["text"])
    result = verify_sentences([{"text": "Review after 15 days.", "quote": "R/A 15 days", "page_no": 1}], PRESCRIPTION)
    assert len(result.sentences) == 1


def test_a_short_quote_that_is_only_part_of_a_line_is_still_not_evidence():
    from app.services.document_grounding import quote_is_grounded

    assert not quote_is_grounded("15 days", PRESCRIPTION[0]["text"])
    assert not quote_is_grounded("Tab Drol-D", PRESCRIPTION[0]["text"])


def test_the_prompt_says_interpretive_comments_are_clinical():
    assert "interpretive comments" in SUMMARY_SYSTEM and "Never" in SUMMARY_SYSTEM


def test_a_statement_that_something_is_normal_is_still_clinical():
    """Set aside as "non-clinical" on the real report."""
    line = "5. Thyroid function tests are within reference limits (TSH in upper-normal range)."
    page = [{"page_no": 1, "text": line}]
    assert verify_not_clinical([line], page) == []
    assert [x["text"] for x in uncovered_lines(page, [], [line], [])] == [line]


def test_a_set_aside_list_stored_under_an_older_rule_is_rechecked_on_read():
    line = "2. Vitamin D (25-OH) is in the deficient range"
    page = [{"page_no": 1, "text": line}]
    assert [x["text"] for x in uncovered_lines(page, [], [line], [])] == [line]


def test_a_label_line_is_layout_its_content_is_not():
    page = [{"page_no": 1, "text": "Interpretive Comments\n1. Morning serum cortisol is elevated."}]
    layout = [x["text"] for x in structural_lines(page, [])]
    assert layout == ["Interpretive Comments"]
    assert [x["text"] for x in uncovered_lines(page, [], [], [])] == ["1. Morning serum cortisol is elevated."]


def test_a_disclaimers_within_is_not_clinical():
    line = "Typographical errors should be notified within 7 days"
    assert verify_not_clinical([line], [{"page_no": 1, "text": line}]) == [line]


def test_the_second_half_of_a_wrapped_sentence_comes_with_its_first_half():
    page = [{"page_no": 1, "text": "2. Serum folate and ferritin are within\nrange but towards the lower end."}]
    sentences = [{"quote": "2. Serum folate and ferritin are within"}]
    assert uncovered_lines(page, sentences, [], []) == [{
        "page_no": 1, "text": "range but towards the lower end.",
        "context": "2. Serum folate and ferritin are within",
    }]
