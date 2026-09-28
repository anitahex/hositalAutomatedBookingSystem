"""The grounding check: a summary sentence may only say what the document says.

Pure — no database, no model.

Every test here is a safety test and none may be relaxed to make a summary "read better".
A confidently wrong sentence about a clinical report, written in a clinician's own
register and shown beside the record, is worse than no summary at all. The failure mode
being prevented is not a model that refuses to answer; it is a model that answers
plausibly and wrongly, with nothing on screen to distinguish the two.

The rules, from the approved plan:
  - each sentence carries a verbatim quote and a page number
  - code verifies the quote really occurs on that page
  - code verifies every number in the sentence really occurs in the QUOTE — scoped to the
    quoted evidence rather than the whole page, because a reference range elsewhere on the
    page can otherwise launder an inverted value
  - a sentence failing either check is DROPPED, not rewritten
"""
from __future__ import annotations

import pytest

from app.services.document_grounding import (
    levels_named_on_the_quotes_line,
    strip_grounded_levels,
    MIN_QUOTE_CHARS,
    VERIFICATION_FAILED,
    VERIFICATION_PARTIAL,
    VERIFICATION_PASSED,
    normalize_for_match,
    numbers_are_grounded,
    numbers_in,
    quote_is_grounded,
    verify_sentences,
)

PAGES = [
    {
        "page_no": 1,
        "text": (
            "COMPREHENSIVE BLOOD PANEL\n"
            "Collected: 20/09/2026\n"
            "Morning cortisol   24.8 ug/dL   (ref 6.2 - 19.4)\n"
            "Vitamin D (25-OH)  18 ng/mL     (ref 30 - 100)\n"
            "Vitamin B12        142 pg/mL    (ref 200 - 900)\n"
        ),
    },
    {
        "page_no": 2,
        "text": "TSH 2.1 mIU/L within reference range.\nNo further action indicated.\n",
    },
]


def _sentence(text, quote, page_no=1):
    return {"text": text, "quote": quote, "page_no": page_no}


# ---- the sentence survives when it is genuinely supported ----

def test_a_grounded_sentence_is_kept():
    result = verify_sentences(
        [_sentence("Morning cortisol is raised at 24.8 ug/dL.", "Morning cortisol   24.8 ug/dL")],
        PAGES,
    )
    assert result.status == VERIFICATION_PASSED
    assert len(result.sentences) == 1
    assert result.sentences[0].page_no == 1


def test_a_sentence_with_no_numbers_at_all_is_fine():
    """Most of a good summary is qualitative. The number check must not make a
    number-free sentence impossible to state."""
    result = verify_sentences(
        [_sentence("Thyroid function is within range.", "TSH 2.1 mIU/L within reference range", 2)],
        PAGES,
    )
    assert result.status == VERIFICATION_PASSED


def test_a_summary_may_omit_values_it_does_not_mention():
    """The check runs sentence -> evidence, never evidence -> sentence. Requiring every
    value in the quote to appear in the sentence would make summarising impossible."""
    assert numbers_are_grounded("Vitamin D is low at 18 ng/mL.", "Vitamin D (25-OH)  18 ng/mL")


# ---- the sentence is dropped when it is not ----

def test_an_invented_number_drops_the_sentence():
    """The core failure. The report says 18; the summary says 38."""
    result = verify_sentences(
        [_sentence("Vitamin D 38 ng/mL, within range.", "Vitamin D (25-OH)  18 ng/mL")],
        PAGES,
    )
    assert result.status == VERIFICATION_FAILED
    assert result.sentences == []
    assert "number" in result.rejected[0].reason


def test_a_value_present_elsewhere_on_the_page_cannot_launder_a_wrong_one():
    """The reason the number check is scoped to the quote rather than the page.

    The page carries "Vitamin D (25-OH)  18 ng/mL   (ref 30 - 100)". A sentence claiming
    30 — the bottom of the reference range — inverts the finding while every digit it
    states is present somewhere on the page. Quote-scoping removes this whenever the
    misleading figure sits outside the quoted evidence.
    """
    result = verify_sentences(
        [_sentence("Vitamin D is 30 ng/mL, within range.", "Vitamin D (25-OH)  18 ng/mL")],
        PAGES,
    )
    assert result.status == VERIFICATION_FAILED


def test_a_same_line_reference_range_is_a_KNOWN_uncovered_case():
    """Pinned deliberately, so this limitation is visible in the suite rather than
    discovered in production.

    If the model quotes the whole line, the reference bounds are inside the quote and a
    sentence citing one of them verifies. Closing this needs value attribution — knowing
    18 is the result and 30 is a bound — which is the structured `findings` extraction's
    job, not this verifier's. It is why the UI shows extracted values as chips beside the
    prose: the doctor sees the parsed value from a separate pipeline next to the sentence.

    If this test ever starts FAILING, the verifier has become stronger and the assertion
    should be flipped, not deleted.
    """
    result = verify_sentences(
        [_sentence(
            "Vitamin D is 30 ng/mL, within range.",
            "Vitamin D (25-OH)  18 ng/mL     (ref 30 - 100)",
        )],
        PAGES,
    )
    assert result.status == VERIFICATION_PASSED, "the verifier changed; revisit this limitation"


def test_a_quote_that_is_not_in_the_document_drops_the_sentence():
    result = verify_sentences(
        [_sentence("Ferritin is depleted.", "Ferritin 8 ng/mL critically low")],
        PAGES,
    )
    assert result.status == VERIFICATION_FAILED
    assert "quote" in result.rejected[0].reason


def test_a_mis_cited_page_is_corrected_rather_than_dropped():
    """The citation has to be usable — a doctor clicking through must find the evidence
    where the summary says it is. There are two ways to achieve that, and dropping the
    sentence is the worse one.

    Measured on a real 3-page lab report: the model attributed Vitamin D, hs-CRP and the
    lipid panel to page 1 when they sat on pages 2 and 3. All three sentences were
    correct. Refusing them discarded true clinical content over a page-number slip.

    So the page is a hint and the quote is the claim. The recorded page is the one the
    verifier LOCATED the quote on, which makes the stored citation more trustworthy than
    the model's own, not less.
    """
    result = verify_sentences(
        [_sentence("Morning cortisol is raised.", "Morning cortisol   24.8 ug/dL", 2)],
        PAGES,
    )
    assert result.status == VERIFICATION_PASSED
    assert result.sentences[0].page_no == 1, "the citation was not corrected to where the quote is"


def test_a_quote_found_on_no_page_is_still_dropped():
    """Page correction must not become a way in for fabricated text."""
    result = verify_sentences(
        [_sentence("Ferritin is depleted.", "Ferritin 8 ng/mL critically low", 2)],
        PAGES,
    )
    assert result.status == VERIFICATION_FAILED


# ---- models cite tables by joining non-adjacent lines ----

def test_a_quote_spanning_non_adjacent_lines_is_accepted():
    """How a model actually cites a results table: it pulls together the rows that matter
    and skips what sits between them. Both lines below are verbatim from page 1, but two
    other analytes separate them, so the concatenation is not a substring of anything.

    Requiring one contiguous run rejected three of five correct sentences on a real
    report. Each FRAGMENT must be verbatim; they need not be adjacent.
    """
    quote = "Vitamin D (25-OH)  18 ng/mL\nVitamin B12        142 pg/mL"
    result = verify_sentences([_sentence("Vitamin D and B12 are both low.", quote)], PAGES)
    assert result.status == VERIFICATION_PASSED


def test_an_elision_marker_between_fragments_is_accepted():
    quote = "Morning cortisol   24.8 ug/dL\n...\nVitamin B12        142 pg/mL"
    result = verify_sentences([_sentence("Cortisol is raised and B12 is low.", quote)], PAGES)
    assert result.status == VERIFICATION_PASSED


def test_one_invented_line_among_real_ones_still_fails():
    """ALL fragments must be verbatim. A fabrication does not become acceptable by being
    surrounded by genuine quotes."""
    quote = "Vitamin D (25-OH)  18 ng/mL\nFerritin 8 ng/mL critically low"
    result = verify_sentences([_sentence("Vitamin D and ferritin are low.", quote)], PAGES)
    assert result.status == VERIFICATION_FAILED


def test_a_quote_made_only_of_short_fragments_is_not_evidence():
    """At least one fragment must stand on its own, or a quote assembled from common
    scraps would pass against almost any document."""
    result = verify_sentences([_sentence("Something.", "18\nng/mL\nlow\n100")], PAGES)
    assert result.status == VERIFICATION_FAILED


def test_citing_a_page_that_does_not_exist_drops_the_sentence():
    result = verify_sentences([_sentence("Something on page nine.", "a quote", 9)], PAGES)
    assert result.status == VERIFICATION_FAILED
    assert "not in document" in result.rejected[0].reason


@pytest.mark.parametrize("quote", ["18", "low", "ng/mL", "", "   "])
def test_a_quote_too_short_to_be_evidence_is_rejected(quote):
    """"18" appears in almost any report. A quote that short cannot distinguish a grounded
    sentence from a lucky one, so accepting it would make the check decorative."""
    assert not quote_is_grounded(quote, PAGES[0]["text"])
    assert len(quote.strip()) < MIN_QUOTE_CHARS


def test_a_sentence_is_dropped_not_rewritten():
    """No repair path, deliberately. Rewriting an ungrounded sentence would mean inventing
    a second time to cover the first."""
    result = verify_sentences(
        [
            _sentence("Vitamin D 38 ng/mL.", "Vitamin D (25-OH)  18 ng/mL"),
            _sentence("Vitamin B12 is low at 142 pg/mL.", "Vitamin B12        142 pg/mL"),
        ],
        PAGES,
    )
    assert [s.text for s in result.sentences] == ["Vitamin B12 is low at 142 pg/mL."]
    assert result.status == VERIFICATION_PARTIAL
    assert "38" not in result.prose


def test_when_nothing_survives_the_status_says_so():
    """The caller shows structured findings instead. It must be able to tell "no summary"
    from "an empty summary"."""
    result = verify_sentences([_sentence("Invented.", "not in the document anywhere")], PAGES)
    assert result.status == VERIFICATION_FAILED
    assert result.prose == ""


# ---- extraction is not faithful to glyphs; the check must survive that ----

def test_whitespace_and_line_breaks_do_not_reject_a_real_quote():
    """PDF extraction collapses and inserts whitespace freely. If real quotes were
    rejected for that, the pressure would be to weaken the check itself."""
    assert quote_is_grounded("Morning cortisol 24.8 ug/dL", PAGES[0]["text"])
    assert quote_is_grounded("Morning   cortisol\n24.8  ug/dL", PAGES[0]["text"])


def test_case_and_unicode_punctuation_do_not_reject_a_real_quote():
    page = {"page_no": 1, "text": "Vitamin D (25–OH)  18 ng/mL — LOW"}
    assert quote_is_grounded("vitamin d (25-oh) 18 ng/ml - low", page["text"])


def test_a_value_printed_with_a_trailing_zero_still_matches():
    """18.0 in the report and 18 in the summary are the same measurement. Comparing
    spellings rather than values would reject correct sentences."""
    assert numbers_are_grounded("Vitamin D 18", "Vitamin D 18.0 ng/mL")
    assert numbers_are_grounded("TSH 2.10", "TSH 2.1 mIU/L")


def test_a_decimal_comma_is_read_as_a_decimal_point():
    assert numbers_in("18,5")[0] == pytest.approx(18.5)


def test_a_date_in_the_sentence_must_be_inside_the_quote_too():
    """The worked example opens "Blood work (20 Sep 2026)". Under quote-scoping the model
    has to quote the collection line to state the date — which is the intended behaviour,
    and what the prompt asks for."""
    assert numbers_are_grounded("Blood work (20 Sep 2026): cortisol raised.", "Collected: 20/09/2026")
    assert not numbers_are_grounded(
        "Blood work (20 Sep 2026): cortisol raised.", "Morning cortisol   24.8 ug/dL"
    )


# ---- model output is hostile input ----

@pytest.mark.parametrize(
    "bad",
    [
        None, [], [None], ["a string"], [{}], [{"text": ""}],
        [{"text": "x", "quote": "y"}],                        # no page
        [{"text": "x", "quote": "y", "page_no": "one"}],      # unparseable page
        [{"text": "x", "quote": "y", "page_no": None}],
    ],
)
def test_malformed_model_output_never_raises_and_never_leaks_through(bad):
    result = verify_sentences(bad, PAGES)
    assert result.sentences == []
    assert result.status == VERIFICATION_FAILED


def test_no_pages_means_nothing_can_be_verified():
    """An image-only document has no stored text yet. Nothing may be shown as grounded
    against a source that is not there."""
    for pages in (None, [], [{"page_no": 1, "text": ""}]):
        result = verify_sentences([_sentence("Anything at all.", "a plausible quote here")], pages)
        assert result.status == VERIFICATION_FAILED


def test_normalisation_does_not_let_an_empty_quote_match_everything():
    """Stripping punctuation must not turn "..." into a quote that matches any page."""
    assert normalize_for_match("...") == ""
    assert not quote_is_grounded("...", PAGES[0]["text"])


# ---- a finding that refers back to its level ----

MRI_PAGE = [{
    "page_no": 1,
    "text": (
        "OPINION:- MR imaging reveals;\n"
        "• Diffuse disc bulge with mild postero-central disc protrusion noted at L5-S1 level, "
        "indenting anterior thecal sac. Mild bilateral facetal arthropathy is noted at this level.\n"
        "• Diffuse disc bulge at L4-5 level, indenting anterior thecal sac. Mild bilateral "
        "facetal arthropathy at this level.\n"
    ),
}]


def test_a_level_named_earlier_in_the_same_bullet_grounds_the_finding():
    """From a real MRI: both facet-arthropathy findings were dropped, because the model
    quoted "... at this level." and "5" and "1" were not inside the quote."""
    result = verify_sentences([
        _sentence("Mild bilateral facetal arthropathy is noted at L5-S1 level.",
                  "Mild bilateral facetal arthropathy is noted at this level."),
        _sentence("Mild bilateral facetal arthropathy at L4-5 level.",
                  "Mild bilateral facetal arthropathy at this level."),
    ], MRI_PAGE)
    assert result.status == VERIFICATION_PASSED
    assert len(result.sentences) == 2


def test_a_level_from_a_different_bullet_is_still_rejected():
    """The quote sits on the L4-5 line; claiming L5-S1 for it is a wrong level."""
    result = verify_sentences([
        _sentence("Mild bilateral facetal arthropathy at L5-S1 level.",
                  "Mild bilateral facetal arthropathy at this level."),
    ], [{"page_no": 1, "text": MRI_PAGE[0]["text"].split("\n", 2)[2]}])
    assert result.status == VERIFICATION_FAILED


def test_only_levels_are_taken_from_the_line_never_values():
    """The same-line allowance must not reopen the reference-range hole: on
    "Vitamin D (25-OH)  18 ng/mL (ref 30 - 100)" a tight quote still cannot carry "30"."""
    assert levels_named_on_the_quotes_line("Vitamin D (25-OH)  18 ng/mL", PAGES[0]["text"]) == set()
    result = verify_sentences(
        [_sentence("Vitamin D is 30 ng/mL, within range.", "Vitamin D (25-OH)  18 ng/mL")], PAGES,
    )
    assert result.status == VERIFICATION_FAILED


def test_a_number_that_is_not_a_level_still_needs_the_quote():
    result = verify_sentences([
        _sentence("Facetal arthropathy at L5-S1 level, 3 mm protrusion.",
                  "Mild bilateral facetal arthropathy is noted at this level."),
    ], MRI_PAGE)
    assert result.status == VERIFICATION_FAILED


def test_level_spellings_are_compared_loosely():
    """"L5/S1" in the sentence is the "L5-S1" printed on the line."""
    stripped = strip_grounded_levels(
        "Arthropathy at L5/S1.", "is noted at this level",
        "disc protrusion at L5-S1 level; arthropathy is noted at this level",
    )
    assert "L5" not in stripped and "S1" not in stripped
