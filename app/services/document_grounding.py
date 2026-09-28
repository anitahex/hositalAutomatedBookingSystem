"""Verifying that a generated document summary only says what the document says.

THE PROBLEM. A summary of a clinical report is read as fact at a glance. A model that
writes "Vitamin D 18 ng/mL, low" about a report that says 38 has produced something worse
than no summary at all: confidently wrong, in the clinician's own words, with nothing to
signal it. Prompting a model to "only use the source" reduces that; it does not prevent it,
and it leaves no way to tell afterwards whether a given sentence was grounded.

THE APPROACH. The model is required to return, for each sentence, a verbatim quote and
the page it came from. Code then checks — against the page text stored at ingestion — that:

  1. the quote genuinely occurs on that page, and
  2. every number in the sentence occurs inside THAT QUOTE — not merely somewhere on the
     page, because a reference range elsewhere on the page would otherwise let an
     inverted value verify. See numbers_are_grounded.

A sentence failing either check is DROPPED. It is never rewritten, never "corrected", and
never shown with a warning: a sentence we cannot verify is one we have no basis to display
beside a clinical record.

This is a verifier, not a truth oracle. What it guarantees:

  - a displayed sentence quotes text that really is in the document
  - a displayed number really appears in the document

What it cannot guarantee:

  - that the sentence draws the right CONCLUSION from the quote. "Thyroid normal" quoting
    a TSH line is verified; whether normal is the right reading is clinical judgement.
  - anything at all about a SCANNED document beyond the transcription. Where page text
    came from vision transcription rather than a PDF text layer, both checks run against
    the model's own reading of an image, so they prove the summary invented nothing beyond
    what was transcribed — not that the transcription was correct. Callers must surface
    that distinction; document_catalog.PAGE_SOURCE_VISION is how they tell.

The VERIFIER is pure — normalize_for_match, numbers_in, quote_is_grounded,
numbers_are_grounded and verify_sentences call nothing and are directly tested. Only
summarise_document reaches out, and it exists to put the verifier between the model and
the database: an unverified sentence is never persisted, so there is no state in which
the wrong thing is one rendering bug away from a clinician.
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Outcomes recorded against a stored summary.
VERIFICATION_PASSED = "passed"    # every sentence survived
VERIFICATION_PARTIAL = "partial"  # some dropped, some kept
VERIFICATION_FAILED = "failed"    # nothing survived; show structured findings instead

# A quote has to carry enough of the document to be evidence. "18" or "low" would match
# almost any report and would make the check meaningless without failing it.
MIN_QUOTE_CHARS = 12

# A single fragment of a multi-line quote. Below this it is noise (a wrapped word, a
# stray bracket) and matching it proves nothing.
FRAGMENT_MIN_CHARS = 6

_NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")
_WORD_SPLIT = re.compile(r"\s+")
# "..." or "…" — how a model marks the rows it skipped between two quoted lines.
_ELISION_PATTERN = re.compile(r"\.{2,}|…")


@dataclass(frozen=True)
class VerifiedSentence:
    text: str
    quote: str
    page_no: int


@dataclass(frozen=True)
class RejectedSentence:
    text: str
    reason: str


@dataclass(frozen=True)
class GroundingResult:
    sentences: list[VerifiedSentence]
    rejected: list[RejectedSentence]
    status: str

    @property
    def prose(self) -> str:
        return " ".join(sentence.text for sentence in self.sentences).strip()


def normalize_for_match(text: str | None) -> str:
    """Lowercase, NFKC, punctuation-insensitive, whitespace-collapsed.

    PDF text extraction is not faithful to the glyphs a model sees: it produces non-
    breaking spaces, ligatures, en/em dashes where the model writes a hyphen, and line
    breaks mid-phrase. Comparing raw strings would reject correct quotes constantly, and
    the pressure would then be to relax the check itself — so normalise aggressively here
    and keep the check strict.

    Punctuation is stripped rather than mapped because its only role in a quote match is
    noise; the numbers, which carry the clinical weight, are checked separately and
    numerically.
    """
    if not text:
        return ""
    folded = unicodedata.normalize("NFKC", str(text)).casefold()
    kept = [char if (char.isalnum() or char.isspace()) else " " for char in folded]
    return _WORD_SPLIT.sub(" ", "".join(kept)).strip()


def numbers_in(text: str | None) -> list[float]:
    """Every numeric literal in `text`, compared by VALUE, not by spelling.

    Value, because a document may print 18.0 where a summary writes 18, and rejecting that
    would train us to loosen the check. A comma is treated as a decimal separator — this
    is a clinical value like "18,5", never a thousands separator, because lab figures in
    this range do not reach four digits.
    """
    values: list[float] = []
    for raw in _NUMBER_PATTERN.findall(str(text or "")):
        try:
            values.append(float(raw.replace(",", ".")))
        except ValueError:
            continue
    return values


def quote_fragments(quote: str | None) -> list[str]:
    """A quote split into the pieces that must each be verbatim.

    Models cite a table by pulling together the lines that matter and eliding what sits
    between them:

        "Vitamin D, 25-Hydroxy (Total) 13.8 L ng/mL Insufficient: 20 - 29
         Vitamin B12 (Cyanocobalamin) 178 L pg/mL 211 - 911"

    Both lines are verbatim from page 2, but eleven other analytes separate them, so the
    concatenation is not a substring of anything. Requiring the whole quote to match as
    one string therefore rejected three of five correct sentences on a real lab report —
    Vitamin D, hs-CRP and the lipid panel, all genuinely in the document.

    Splitting on line breaks and on elision markers keeps the property that matters
    (nothing in the citation was invented) without demanding the model quote a page in
    one contiguous run. Fragments shorter than FRAGMENT_MIN_CHARS are dropped as noise —
    a wrapped "Protein)" carries no evidential weight and would match almost anything.
    """
    fragments: list[str] = []
    for chunk in _ELISION_PATTERN.split(str(quote or "")):
        for line in chunk.splitlines():
            normalized = normalize_for_match(line)
            if len(normalized) >= FRAGMENT_MIN_CHARS:
                fragments.append(normalized)
    return fragments


def quote_is_grounded(quote: str | None, page_text: str | None) -> bool:
    """Is every substantial fragment of this quote verbatim on this page?

    ALL fragments must match — one invented line among three real ones is still a
    fabrication — and at least one must be long enough to be evidence on its own, so a
    quote assembled entirely from short common phrases cannot pass.
    """
    fragments = quote_fragments(quote)
    if not fragments:
        return False
    if max(len(fragment) for fragment in fragments) < MIN_QUOTE_CHARS:
        # A short quote is evidence only when it is a WHOLE line of the page. Prescriptions
        # are written in short lines — "R/A 15 days" (review after 15 days) is 11
        # characters — and without this they could never be quoted, so the summary always
        # lost them. A whole line matched exactly is not a lucky substring the way "18" is.
        lines = {normalize_for_match(line) for line in str(page_text or "").splitlines()}
        return len(fragments) == 1 and fragments[0] in lines
    page = normalize_for_match(page_text)
    return all(fragment in page for fragment in fragments)


def numbers_are_grounded(sentence: str | None, evidence: str | None) -> bool:
    """Does every number in the sentence appear in the EVIDENCE — the quote, not the page?

    Scoped to the quote deliberately. Checking the whole page lets an unrelated figure
    launder a wrong value: on a page reading

        Vitamin D (25-OH)  18 ng/mL   (ref 30 - 100)

    the sentence "Vitamin D is 30 ng/mL, normal" passes a page-wide check, because 30 is
    present — as the bottom of the reference range. The true value is 18 and the summary
    has inverted the finding. Requiring the number to sit in the quoted evidence removes
    every version of that which spans lines or sections.

    RESIDUAL RISK, not covered here: a reference range printed on the SAME LINE is inside
    the quote too, so the example above still passes if the model quotes the whole line.
    Closing that needs value-attribution — knowing 18 is the result and 30 is a bound —
    which is what the structured `findings` extraction does. That is why the UI shows
    extracted values as chips beside the prose rather than relying on the prose alone: the
    doctor sees the parsed value, from a different pipeline, next to the sentence.

    The direction matters: each number the SENTENCE asserts must exist in the evidence.
    The reverse is not required — a summary is allowed to omit values, and must be, or it
    could not summarise at all. Inventing one is the failure being prevented.
    """
    evidence_numbers = numbers_in(evidence)
    return all(
        any(abs(claimed - present) < 1e-9 for present in evidence_numbers)
        for claimed in numbers_in(sentence)
    )


# A vertebral level: L5, L4-5, L5-S1, C3/C4, T12. Case-sensitive on purpose — these are
# printed in capitals, and "s1" or "l5" in running text is not a level.
_SPINAL_LEVEL = re.compile(r"(?<![A-Za-z0-9])[CTLS]\d{1,2}(?:\s*[-/–]\s*[CTLS]?\d{1,2})?(?![A-Za-z0-9])")


def _level_key(level: str) -> str:
    return re.sub(r"\s+", "", level).replace("–", "-").replace("/", "-")


def levels_named_on_the_quotes_line(quote: str | None, page_text: str | None) -> set[str]:
    """Spinal levels printed on the page line(s) the quote was found on.

    Radiology reports state a level once and refer back to it:

        • Diffuse disc bulge ... at L5-S1 level ... Mild bilateral facetal arthropathy is
          noted at this level.

    The model writes "Mild facetal arthropathy at L5-S1" and quotes "...is noted at this
    level." — true, and on a real MRI both facet findings were dropped for it, because "5"
    and "1" are not inside the quote. Only LEVELS are taken from the line, never other
    numbers: a level is not a measured value, so it cannot do what a reference range on
    the same line could (let "Vitamin D 30" verify against "18 ng/mL (ref 30 - 100)").
    """
    fragments = quote_fragments(quote)
    if not fragments:
        return set()
    levels: set[str] = set()
    for line in str(page_text or "").splitlines():
        normalized = normalize_for_match(line)
        if any(fragment in normalized for fragment in fragments):
            levels.update(_level_key(match) for match in _SPINAL_LEVEL.findall(line))
    return levels


def strip_grounded_levels(sentence: str, quote: str | None, page_text: str | None) -> str:
    """The sentence with every spinal level removed that its quote's line names, so only
    the remaining numbers go to numbers_are_grounded. A level the line does NOT name stays
    in, and still has to be inside the quote."""
    grounded = levels_named_on_the_quotes_line(quote, page_text)
    if not grounded:
        return sentence
    return _SPINAL_LEVEL.sub(
        lambda match: " " if _level_key(match.group(0)) in grounded else match.group(0), sentence
    )


def verify_sentences(raw_sentences, pages) -> GroundingResult:
    """Keeps only sentences whose quote and numbers are both grounded in their page.

    `pages` is document_catalog.get_document_pages()'s shape: [{page_no, text, ...}].
    `raw_sentences` is model output: [{text, quote, page_no}], and is treated as hostile —
    wrong types, missing keys and pages that do not exist are all expected inputs.
    """
    page_text_by_no = {
        int(page["page_no"]): str(page.get("text") or "")
        for page in (pages or [])
        if str(page.get("page_no", "")).strip().isdigit() or isinstance(page.get("page_no"), int)
    }

    kept: list[VerifiedSentence] = []
    rejected: list[RejectedSentence] = []

    for item in raw_sentences or []:
        if not isinstance(item, dict):
            rejected.append(RejectedSentence(text=str(item)[:200], reason="malformed"))
            continue

        text = str(item.get("text") or "").strip()
        quote = str(item.get("quote") or "").strip()
        if not text:
            continue

        try:
            page_no = int(item.get("page_no"))
        except (TypeError, ValueError):
            rejected.append(RejectedSentence(text=text, reason="no page number"))
            continue

        # Where the quote ACTUALLY is, preferring the page the model named.
        #
        # Models mis-cite pages. Measured on a real 3-page lab report: three of five
        # sentences were correct and useful — Vitamin D 13.8, hs-CRP 3.6, triglycerides
        # 176, all genuinely in the document — but every one was attributed to page 1
        # when the content sat on pages 2 and 3. Dropping them discarded true clinical
        # content over a citation slip.
        #
        # So the page number is treated as a HINT and the quote as the claim. The
        # guarantee is unchanged and arguably stronger: the quote must still be found
        # verbatim somewhere in this document, and the page recorded is the one WE
        # located it on, not the one the model asserted. A quote found nowhere is still
        # a fabrication and still dropped.
        located_page = None
        if quote_is_grounded(quote, page_text_by_no.get(page_no)):
            located_page = page_no
        else:
            for candidate_no in sorted(page_text_by_no):
                if quote_is_grounded(quote, page_text_by_no[candidate_no]):
                    located_page = candidate_no
                    break

        if located_page is None:
            reason = (
                f"page {page_no} not in document"
                if page_no not in page_text_by_no
                else "quote not found anywhere in the document"
            )
            rejected.append(RejectedSentence(text=text, reason=reason))
            continue

        if located_page != page_no:
            logger.info(
                "document_grounding: corrected citation from page %s to page %s",
                page_no, located_page,
            )
        page_no = located_page

        # Against the quote, not the page — see numbers_are_grounded. A spinal level the
        # finding refers back to ("... at this level") is taken from the quote's own line;
        # see levels_named_on_the_quotes_line.
        checked_text = strip_grounded_levels(text, quote, page_text_by_no.get(page_no))
        if not numbers_are_grounded(checked_text, quote):
            rejected.append(RejectedSentence(text=text, reason="a number is not in the quoted evidence"))
            continue

        kept.append(VerifiedSentence(text=text, quote=quote, page_no=page_no))

    if kept and not rejected:
        status = VERIFICATION_PASSED
    elif kept:
        status = VERIFICATION_PARTIAL
    else:
        status = VERIFICATION_FAILED

    if rejected:
        logger.warning(
            "document_grounding: dropped %d of %d sentences (%s)",
            len(rejected), len(kept) + len(rejected),
            "; ".join(sorted({item.reason for item in rejected})),
        )

    return GroundingResult(sentences=kept, rejected=rejected, status=status)


# ---- The prompt ----

SUMMARY_PROMPT_VERSION = "doc-summary-v5-every-item"
# Written before the model accounted for every line; no line accounting is shown for them.
LEGACY_SUMMARY_VERSIONS = frozenset({
    "doc-summary-v1-clinician", "doc-summary-v2-every-abnormal", "doc-summary-v3-every-abnormal",
})

# v2: "1 to 3 sentences" could not hold a report with more abnormal findings than that — an
# MRI with five abnormal levels, a lab report flagging twelve results — so findings were
# silently left out. Now every abnormal or critical finding gets its own sentence, and
# normal results are not listed. Verification is unchanged: each sentence still needs its
# own verbatim quote, and a sentence that fails is still dropped.
# v3: a finding that says "at this level" quotes its whole bullet, so the level it
# names is inside the quote. On a real MRI, both facet-arthropathy findings were dropped
# by the number check because the quote held only "at this level".
# v4: v2 and v3 asked only for ABNORMAL FINDINGS, which is what a lab report or a scan
# holds but not what a prescription holds. On a real prescription the summary shrank to
# one sentence and lost every medication, the physiotherapy and the exercises. The prompt
# now says what "everything" means for each kind of document, and asks the model to
# account for EVERY line: each is either inside a sentence's quote or copied verbatim into
# not_clinical. Code checks that accounting (uncovered_lines) and shows the doctor any line
# that is in neither, so a line cannot silently disappear from the summary.
# v5: the lab's interpretive comments were set aside as "non-clinical" on a real report;
# the prompt now says they are clinical, and code refuses clinical-looking set-aside lines
# (verify_not_clinical). Headings and reference bands are recognised by code instead.
SUMMARY_SYSTEM = """You summarise ONE medical document for a doctor who has not read it.
The doctor relies on your summary containing EVERYTHING clinically relevant in it.

REGISTER — this is read by a clinician, not a patient:
- Use normal clinical vocabulary. Do not expand or explain standard terms.
- Do not simplify to patient level ("a test that checks your blood").
- Do not inflate into jargon either. Plain, dense, unhurried-to-read.

COMPLETENESS — nothing clinically relevant may be left out:
- ONE sentence per item. Never merge two findings, two medications or two instructions
  into one sentence, and never stop early.
- Lab report: every result the report marks abnormal (H, L, High, Low, Critical, *) or
  prints outside its own reference range; the lab's interpretive comments; its
  conclusion. Normal results are NOT listed — they are shown separately by code.
- Imaging or pathology: every abnormal finding (each level, each lesion), then the
  impression.
- Prescription, OPD or consultation note: the complaints; findings or investigations
  noted (e.g. an MRI result); the diagnosis; EVERY medication as its own sentence with
  name, strength, dose, frequency and duration exactly as written (keep BD, OD, TDS, SOS,
  HS as written); every investigation advised; every non-drug instruction (physiotherapy,
  exercises, a belt or brace, diet, rest); the follow-up or review.
- Discharge summary: diagnosis, procedures, course, every discharge medication, every
  instruction, the follow-up.
- Any other document: every clinically relevant statement.

ACCOUNT FOR EVERY LINE:
- Every line of the document must end up EITHER inside one of your sentence quotes, OR
  copied verbatim into "not_clinical".
- not_clinical is ONLY for lines with no clinical content: letterhead, hospital or clinic
  name, address, phone, email, registration numbers, the patient's name/age/ID line, staff
  names and signatures, page numbers, disclaimers, method notes. NEVER put a complaint,
  finding, medication, instruction or result there.
- Lines of NORMAL lab results, section headings, table column headers and printed
  reference bands ("Deficient: < 20") may be left out of both.
- A lab's interpretive comments, remarks or notes ARE clinical: summarise each one. Never
  put them in not_clinical.

GROUNDING — every sentence you write is checked by code before it is shown:
- For each sentence, give a VERBATIM quote copied exactly from the page it came from, and
  that page's number. Copy the characters; do not paraphrase the quote.
- The quote must be at least a dozen characters and must actually appear on that page.
- Every number you state must appear INSIDE YOUR OWN QUOTE, not merely somewhere on the
  page. Quote enough of the line to contain the values you cite. If you cannot find a
  value in the text, do not state it.
- A finding that refers back to its site ("Mild facetal arthropathy is noted at this
  level") must quote from the start of its bullet or paragraph, so the level it names
  ("L5-S1") is inside the quote.
- Say nothing the document does not say. Do not add likely diagnoses, do not infer what
  was not measured, do not expand an abbreviation you are unsure of, and do not reassure.
- A sentence whose quote or numbers cannot be found is discarded, and its line is then
  shown to the doctor as it was written.

Return JSON only:
{"sentences": [{"text": "...", "quote": "verbatim from the page", "page_no": 1}],
 "not_clinical": ["verbatim line", "..."]}

Worked example, a lab report — one result per sentence:
  "Morning cortisol raised at 24.6 µg/dL (ref 6.2 - 19.4)."
  "Vitamin B12 low at 178 pg/mL (ref 211 - 911)."
Worked example, a prescription — one item per sentence:
  "Complaint: low back ache with right lower-limb numbness."
  "Tab Gabantin-NT 400/100 BD for 15 days."
  "Advised physiotherapy with back-strengthening exercises."
  "Review after 15 days."
"""


def store_summary(
    document_id: str, result: GroundingResult, *, model=None, source_kind=None,
    not_clinical: list[str] | None = None,
) -> None:
    """Persists ONLY what survived verification.

    Rejected sentences are counted, not kept. Storing them would create a second copy of
    the text we decided was not safe to show, one schema change away from being rendered
    by mistake — and the count is what actually matters operationally, because a document
    that drops most of its sentences signals a bad transcription, not a bad model.

    `not_clinical` is the verified list of lines the model set aside (verify_not_clinical);
    uncovered_lines needs it to tell a set-aside letterhead from a missed medication.
    """
    from app.db.connection import connect_db

    payload = json.dumps([
        {"text": sentence.text, "quote": sentence.quote, "page_no": sentence.page_no}
        for sentence in result.sentences
    ])

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO document_summaries (
                    document_id, sentences, register, model, prompt_version,
                    verification, rejected_count, source_kind, not_clinical, generated_at
                ) VALUES (%s, %s::jsonb, 'clinician', %s, %s, %s, %s, %s, %s::jsonb, NOW())
                ON CONFLICT (document_id) DO UPDATE SET
                    sentences = EXCLUDED.sentences,
                    model = EXCLUDED.model,
                    prompt_version = EXCLUDED.prompt_version,
                    verification = EXCLUDED.verification,
                    rejected_count = EXCLUDED.rejected_count,
                    source_kind = EXCLUDED.source_kind,
                    not_clinical = EXCLUDED.not_clinical,
                    generated_at = NOW()
                """,
                (document_id, payload, model, SUMMARY_PROMPT_VERSION,
                 result.status, len(result.rejected), source_kind,
                 json.dumps(list(not_clinical or []))),
            )
        conn.commit()

    logger.info(
        "document_grounding: stored summary for %s — %d kept, %d dropped, %s",
        document_id, len(result.sentences), len(result.rejected), result.status,
    )


def get_summary(document_id: str) -> dict | None:
    """The stored clinician summary, or None if one was never generated.

    None and a 'failed' row mean different things — never generated versus generated and
    entirely unverifiable — and the UI says something different for each.
    """
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT sentences, verification, rejected_count, source_kind,
                          generated_at, model, not_clinical, prompt_version
                   FROM document_summaries WHERE document_id = %s""",
                (document_id,),
            )
            row = cur.fetchone()
        conn.commit()

    if not row:
        return None
    sentences = row[0] or []
    return {
        "sentences": sentences,
        "prose": " ".join(str(item.get("text") or "") for item in sentences).strip(),
        "verification": row[1],
        "rejected_count": int(row[2] or 0),
        # 'vision_transcription' means quotes were verified against a model's reading of
        # an image, not a text layer. The UI must say so rather than presenting the two
        # as equally checked.
        "source_kind": row[3],
        "generated_at": row[4].isoformat() if row[4] else None,
        # Deliberately NOT returned to the client by the route — kept here for support.
        "model": row[5],
        "not_clinical": row[6] or [],
        "prompt_version": row[7],
    }


async def summarise_document(document_id: str, pages: list[dict], document_type: str | None = None) -> GroundingResult:
    """Generate, verify, store. The only path by which a summary reaches the database.

    Verification sits between the model and storage rather than between storage and the
    screen, so an unverified sentence is never persisted at all — there is no state in
    which the wrong thing is one rendering bug away from a clinician.

    `document_type` ("prescription", "blood_report"...) tells the model what "everything"
    means for this document; looked up from the catalog when not given.

    Non-fatal by contract: on any failure the document keeps its structured findings and
    stays viewable. A missing summary is a smaller harm than a wrong one.
    """
    from app.inference.azure_client import gpt4o_document_summary

    if not pages:
        logger.info("document_grounding: no stored page text for %s, skipping summary", document_id)
        return GroundingResult(sentences=[], rejected=[], status=VERIFICATION_FAILED)

    if document_type is None:
        document_type = _catalog_document_type(document_id)
    source_kind = pages[0].get("source")
    try:
        generated = await gpt4o_document_summary(pages=pages, document_type=document_type)
    except Exception as exc:
        logger.error("document_grounding: summary generation failed for %s: %s", document_id, exc)
        return GroundingResult(sentences=[], rejected=[], status=VERIFICATION_FAILED)

    result = verify_sentences(generated.get("sentences"), pages)
    not_clinical = verify_not_clinical(generated.get("not_clinical"), pages)
    try:
        store_summary(document_id, result, model=generated.get("model"), source_kind=source_kind,
                      not_clinical=not_clinical)
    except Exception as exc:
        logger.error("document_grounding: could not store summary for %s: %s", document_id, exc)
    return result


def _catalog_document_type(document_id: str) -> str | None:
    from app.db.connection import connect_db

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT document_type FROM document_catalog WHERE document_id = %s", (document_id,))
                row = cur.fetchone()
            conn.commit()
        return row[0] if row else None
    except Exception:
        return None


def build_summary_user_content(pages: list[dict], document_type: str | None = None) -> str:
    """The document, page by page, with page numbers the model must cite.

    One document per call. Batching several would let the model blend findings across
    reports, which is exactly the cross-document inference this design keeps in code.
    The extracted document type, when known, says which COMPLETENESS rules apply.
    """
    blocks = [
        f"--- PAGE {page['page_no']} ---\n{page.get('text') or ''}".strip()
        for page in pages or []
    ]
    header = f"Document type (as extracted): {document_type}\n\n" if document_type else ""
    return header + "\n\n".join(blocks)


# ---- accounting for every line ----
#
# "Nothing missed" as something code can check, for any kind of document. Every line of
# the page text must be accounted for in one of three ways:
#
#   1. inside the quote of a verified summary sentence
#   2. a result line code already parsed and lists (document_findings, located on the page)
#   3. set aside by the model as non-clinical — letterhead, phone, signatures — and found
#      verbatim on the page (verify_not_clinical)
#
# Anything else is UNCOVERED and is shown to the doctor as it was written. So a medication
# the model forgot, or a sentence dropped because its quote failed verification, does not
# disappear: its line appears under "also in the document". The only way to hide a clinical
# line is for the model to call it non-clinical, and those lines are shown on request too.

# A line needs this much text to count; "(2)", "AC" and stray marks are not content.
_MIN_LINE_CHARS = 4


# Words that make a line clinical. A set-aside line containing one is refused, so it stays
# uncovered and is shown. On a real lab report the model set the whole "Interpretive
# Comments" block aside as non-clinical — "cortisol is elevated", "deficient range" — which
# the line accounting cannot catch unless the set-aside list itself is checked.
_CLINICAL_TERMS = re.compile(
    r"\b(tab|tabs|tablets?|caps?|capsules?|syp|syrup|inj|injections?|mg|mcg|bd|od|tds|qid|sos|"
    r"adv|advised?|advice|rx|diagnos\w*|impression|comments?|remarks?|elevated|raised|"
    r"increased|decreased|reduced|deficien\w*|insufficien\w*|abnormal\w*|suggest\w*|"
    r"findings?|disc|bulge|protrusion|fracture|lesions?|mass|nodules?|effusion|stenosis|"
    r"degenerat\w*|inflammat\w*|infection|positive|negative|review|follow|physiotherapy|"
    r"exercises?|diet|belt|brace|pain|numbness|fever|complain\w*|history|c/o|h/o|"
    r"dyslipid\w*|anaemi\w*|anemi\w*|diabet\w*|hypertens\w*|"
    # A statement that something is NORMAL is still a clinical statement: "Thyroid function
    # tests are within reference limits" was set aside as non-clinical on a real report.
    # "within" only as a clinical phrase: "notified within 7 days" in a disclaimer is not one.
    r"within (?:the )?(?:normal|reference|range|limits)|normal|limits)\b",
    re.I,
)


def verify_not_clinical(lines, pages) -> list[str]:
    """The model's set-aside lines that really are on the page, and really are not clinical.
    Anything it did not copy faithfully, or that carries a clinical term, does not count —
    so the line it was meant to cover stays uncovered and is shown to the doctor."""
    page_lines = [
        normalize_for_match(line)
        for page in pages or []
        for line in str(page.get("text") or "").splitlines()
    ]
    kept: list[str] = []
    for line in lines or []:
        if not isinstance(line, str):
            continue
        normalized = normalize_for_match(line)
        if len(normalized) < _MIN_LINE_CHARS or _CLINICAL_TERMS.search(line):
            continue
        if any(normalized == page_line or (len(normalized) >= FRAGMENT_MIN_CHARS and normalized in page_line)
               for page_line in page_lines):
            kept.append(" ".join(line.split()))
    return kept


def accepted_set_aside(lines) -> list[str]:
    """The stored set-aside lines that the CURRENT rule accepts as non-clinical."""
    return [line for line in lines or [] if isinstance(line, str) and not _CLINICAL_TERMS.search(line)]


def _overlaps(line: str, pieces: list[str]) -> bool:
    """A piece covers a line when one contains the other. Pieces are at least
    FRAGMENT_MIN_CHARS long (quote_fragments), so a stray short word cannot cover a line."""
    return any(piece and (piece in line or (len(line) >= FRAGMENT_MIN_CHARS and line in piece))
               for piece in pieces)


# A results table's column header: "Test Description Result Flag Units Biological Ref.
# Interval". Three or more of these words and nothing else of substance.
_HEADER_WORDS = frozenset({
    "test", "tests", "description", "result", "results", "flag", "flags", "unit", "units",
    "reference", "ref", "interval", "range", "value", "values", "investigation", "parameter",
    "biological", "observed", "method", "specimen",
})
# A line that is only a label for what follows: "Interpretive Comments", "Impression:".
# Its content is on the next lines, accountable in its own right.
_LABEL_ONLY = re.compile(
    r"^\W*(interpretive comments?|comments?|remarks?|impression|opinion|findings?|advice|"
    r"conclusion|notes?|clinical (?:history|details|notes))\W*$",
    re.I,
)
# A printed reference band: "Deficient: < 20", "Prediabetes: 5.7 - 6.4", "High: > 3.0".
_BAND = re.compile(r"^\s*[A-Za-z][A-Za-z .]{0,30}:\s*(?:[<>≤≥]=?\s*\d|\d[\d.,]*\s*[-–]\s*\d)")


def _is_column_header(raw: str) -> bool:
    words = normalize_for_match(raw).split()
    return len(words) >= 3 and sum(word in _HEADER_WORDS for word in words) >= 3 \
        and sum(word in _HEADER_WORDS for word in words) >= len(words) - 2


def structural_lines(pages, result_lines) -> list[dict]:
    """Lines that are the layout of a results table, not content: column headers, printed
    reference bands, and headings whose next lines are parsed results ("Liver Function
    Test" above "Bilirubin, Total 0.8 mg/dL"). Recognised by code, never by the model, and
    only in these narrow shapes — a short line NOT followed by results (a prescription's
    "Physiotherapy") is content and stays accountable. [{"page_no", "text"}]. Pure."""
    results = {normalize_for_match(line) for line in result_lines or []}
    out: list[dict] = []
    for page in pages or []:
        lines = [raw for raw in str(page.get("text") or "").splitlines() if raw.strip()]
        for index, raw in enumerate(lines):
            if _is_column_header(raw) or _BAND.match(raw) or _LABEL_ONLY.match(raw):
                out.append({"page_no": page.get("page_no"), "text": " ".join(raw.split())})
                continue
            words = normalize_for_match(re.sub(r"\([^)]*\)", " ", raw)).split()
            if not words or len(words) > 6 or re.search(r"\d", re.sub(r"\([^)]*\)", " ", raw)):
                continue
            following = lines[index + 1:index + 3]
            if any(normalize_for_match(nxt) in results or _is_column_header(nxt) for nxt in following):
                out.append({"page_no": page.get("page_no"), "text": " ".join(raw.split())})
    return out


def uncovered_lines(pages, sentences, not_clinical, result_lines) -> list[dict]:
    """Page lines accounted for by none of: a verified sentence's quote, a parsed result's
    line, a verified non-clinical line, the layout of a results table. [{"page_no",
    "text"}], in document order. Pure."""
    quoted = [fragment for sentence in sentences or [] for fragment in quote_fragments(sentence.get("quote"))]
    # Re-checked on every read, not only when the summary was stored: a list stored under
    # an older, looser rule must not keep hiding a clinical line.
    set_aside = [normalize_for_match(line) for line in accepted_set_aside(not_clinical)]
    results = [normalize_for_match(line) for line in result_lines or []]
    layout = {normalize_for_match(line["text"]) for line in structural_lines(pages, result_lines)}
    out: list[dict] = []
    for page in pages or []:
        previous = ""
        for raw in str(page.get("text") or "").splitlines():
            line = normalize_for_match(raw)
            if len(line) < _MIN_LINE_CHARS or not re.search(r"[a-z]", line):
                previous = raw if raw.strip() else previous
                continue
            if not (_overlaps(line, quoted) or line in set_aside or _overlaps(line, results) or line in layout):
                entry = {"page_no": page.get("page_no"), "text": " ".join(raw.split())}
                # A wrapped sentence's second half ("range but towards the lower end.") means
                # nothing alone; the line it continues is given as context.
                if raw.strip()[:1].islower() and previous.strip():
                    entry["context"] = " ".join(previous.split())
                out.append(entry)
            previous = raw
    return out
