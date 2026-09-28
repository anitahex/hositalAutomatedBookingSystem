"""
OpenAI vision client — INGESTION PATH ONLY.

Import this module ONLY from the document ingestion pipeline
(Guardrail 1 relevance check + Tier 2 structured extraction).
Every other LLM call in the system goes through app.inference.llm (HF client).
"""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")

try:
    from openai import AsyncOpenAI
    _HAS_OPENAI = True
except ImportError:
    AsyncOpenAI = None  # type: ignore[assignment, misc]
    _HAS_OPENAI = False

_openai_client: "AsyncOpenAI | None" = None


def _get_openai_client() -> "AsyncOpenAI":
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    if not _HAS_OPENAI:
        raise RuntimeError(
            "openai package is not installed. Run: pip install openai>=1.0"
        )
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OpenAI is not configured. Set OPENAI_API_KEY in .env."
        )
    _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    logger.info("openai_client: AsyncOpenAI initialised (model=%s)", OPENAI_VISION_MODEL)
    return _openai_client


_RELEVANCE_SYSTEM = (
    "Analyze this text/image. Is it a medical document, clinical report, lab result, "
    "MRI/X-ray breakdown, or prescription? Answer strictly with either TRUE or FALSE."
)

_EXTRACTION_SYSTEM = """\
You are a medical document extraction AI.
Extract structured information from the provided document.

Return ONLY valid JSON matching this exact structure:
{
  "document_type": "prescription | blood_report | mri_report | ct_report | xray_report | ultrasound_report | ecg_report | pathology_report | discharge_summary | other",
  "clinical_date": "YYYY-MM-DD or null",
  "referring_doctor": "Name exactly as printed, including title, or null",
  "referring_department": "Only if a specialty is printed on the document, else null",
  "clinical_history": "The stated reason the test was ordered, or null",
  "body_region": "Imaging only: the region examined, else null",
  "overall_impression": "Final diagnostic summary or conclusion in 1-3 sentences",
  "findings": {
    "key": "value"
  }
}

Rules:
- document_type must be one of the listed values (use 'other' if none match).
- clinical_date must be ISO format YYYY-MM-DD or null if absent.
- findings keys must be consistent canonical names (e.g. 'CBC', 'Hemoglobin', 'WBC', 'Blood Pressure').
- If a field is illegible or missing, set its value to '[Incomplete/Illegible text in document]'.
- Transcribe values exactly as written. Do NOT invent or estimate any value.
- Read the LETTERHEAD and HEADER, not just the results table. Look for 'Referred By',
  'Ref. By', 'Referring Physician', 'Consultant', 'Under care of' or 'Advised by', and
  transcribe the value verbatim into referring_doctor.
- Never infer referring_department from the findings. If only a name is printed, fill
  referring_doctor and set referring_department to null.
- clinical_history is the indication as STATED on the document ("Clinical history: low
  back pain x 3 months"). Do not summarise the results into it; use null if absent.\
"""


async def gpt4o_relevance_check(
    *,
    mime_type: str,
    file_bytes: bytes,
    extracted_text: str | None = None,
) -> bool:
    """
    Guardrail 1 — verify the uploaded file is a valid medical document.

    Uses GPT-4o vision for images; sends a text sample for PDFs.
    Returns True if the document is medical, False otherwise.
    Treats any ambiguous / non-TRUE response as False and logs a warning.
    """
    client = _get_openai_client()

    if mime_type.startswith("image/"):
        b64 = base64.b64encode(file_bytes).decode("ascii")
        user_content: Any = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}", "detail": "low"},
            }
        ]
    else:
        sample = (extracted_text or "")[:6000].strip()
        if not sample:
            logger.warning("gpt4o_relevance_check: no extractable text — treating as FALSE")
            return False
        user_content = sample

    logger.info("gpt4o_relevance_check: calling GPT-4o (mime=%s)", mime_type)
    try:
        response = await client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            messages=[
                {"role": "system", "content": _RELEVANCE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_completion_tokens=10,
            temperature=0,
        )
        raw = (response.choices[0].message.content or "").strip().upper()
        logger.info("gpt4o_relevance_check: raw=%r", raw)

        tokens = raw.split()
        if "TRUE" in tokens:
            return True
        if "FALSE" in tokens:
            return False
        logger.warning("gpt4o_relevance_check: ambiguous response %r — defaulting to FALSE", raw)
        return False
    except Exception as exc:
        logger.error("gpt4o_relevance_check failed: %s", exc, exc_info=True)
        raise RuntimeError(f"GPT-4o relevance check failed: {exc}") from exc


async def gpt4o_structured_extraction(
    *,
    mime_type: str,
    file_bytes: bytes,
    extracted_text: str | None = None,
) -> dict[str, Any]:
    """
    Tier 2 — structured JSON extraction using GPT-4o.
    This is the LAST GPT-4o call for a given document.

    Returns a dict with keys:
        document_type, clinical_date, overall_impression, findings
    """
    client = _get_openai_client()

    if mime_type.startswith("image/"):
        b64 = base64.b64encode(file_bytes).decode("ascii")
        user_content: Any = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}", "detail": "high"},
            },
            {"type": "text", "text": "Extract structured information from this medical document."},
        ]
    else:
        text_content = extracted_text or ""
        user_content = (
            f"Extract structured information from this medical document:\n\n{text_content}"
        )

    logger.info("gpt4o_structured_extraction: calling GPT-4o (mime=%s)", mime_type)
    try:
        response = await client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_completion_tokens=1500,
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = (response.choices[0].message.content or "").strip()
        logger.info("gpt4o_structured_extraction: response length=%d chars", len(raw))

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"GPT-4o returned invalid JSON: {exc}. Raw: {raw[:300]}") from exc

        return {
            "document_type": str(data.get("document_type") or "other"),
            "clinical_date": data.get("clinical_date") or None,
            "overall_impression": str(data.get("overall_impression") or ""),
            "findings": dict(data.get("findings") or {}),
            # Additive and nullable. A model that omits them yields None rather than a
            # guess, and every existing consumer reads only the four keys above, so this
            # cannot break them. referring_department is a claim the document makes, not a
            # routing decision — it is validated against real departments downstream.
            "referring_doctor": data.get("referring_doctor") or None,
            "referring_department": data.get("referring_department") or None,
            "clinical_history": data.get("clinical_history") or None,
            "body_region": data.get("body_region") or None,
        }
    except RuntimeError:
        raise
    except Exception as exc:
        logger.error("gpt4o_structured_extraction failed: %s", exc, exc_info=True)
        raise RuntimeError(f"GPT-4o structured extraction failed: {exc}") from exc


_STREAM_FORMAT_SYSTEM = """\
You are a medical document analysis AI. Analyze the provided document and generate a
BEAUTIFULLY FORMATTED MARKDOWN REPORT that is clear and patient-friendly.

Adapt sections to the document type:

**PRESCRIPTION:**
## Prescription Summary
**Date:** [date]
### Patient Information
- **Name:** [name]  - **Age/Gender:** [age] / [gender]
- **Referred By:** [referring doctor and specialty exactly as printed, or "Not stated"]
- **Clinical History:** [the stated reason for this test, or "Not stated"]
### Clinical Assessment
- [diagnoses and symptoms as bullets; sub-bullets for MRI/lab sub-findings]
### Treatment Plan
**[Therapy type]**
- [instructions]
**Medications**
| Medication | Dosage / Duration |
|---|---|
| [name] | [dose and duration] |
### Additional Instructions
- [notes]
### Recommended Specialist
**[Department]**
**Reason:** [1–2 sentences referencing specific findings]

**BLOOD / LAB REPORT:**
## Blood Report Analysis
**Date:** [date]
### Patient Information
- **Name:** ...
- **Referred By:** [referring doctor and specialty exactly as printed, or "Not stated"]
- **Clinical History:** [the stated reason for this test, or "Not stated"]
### Test Results
| Test | Result | Normal Range | Status |
|---|---|---|---|
| [name] | [value + unit] | [range] | Normal / ⚠️ Low / ⚠️ High |
### Key Findings
- [noteworthy values and interpretations]
### Recommended Specialist
**[Department]**
**Reason:** ...

**IMAGING (MRI / CT / X-Ray):**
## [Type] Report
**Date:** [date]
### Patient Information
- **Name:** ...
- **Referred By:** [referring doctor and specialty exactly as printed, or "Not stated"]
- **Clinical History:** [the stated reason for this scan, or "Not stated"]
### Imaging Details
- **Body Region:** ...  - **Technique:** ...
### Findings
- [bullet list of findings]
### Impression
[summary conclusion]
### Recommended Specialist
**[Department]**
**Reason:** ...

**DISCHARGE SUMMARY / OTHER:**
Use appropriate sections for the document type found.

Rules:
- Transcribe values EXACTLY as written; never invent values.
- For unclear handwriting, give your single best-effort reading of the full word/name rather than truncating it — mark low-confidence readings inline with (?), e.g. "Tab Oxyral (?)". Only write *Illegible in document* if truly nothing can be read at all, not merely because you are uncertain of a letter or two.
- If the patient asked a specific question, add: ### Answer to Your Question
- Always include the Recommended Specialist section last.
- NEVER name Radiology, Pathology or a laboratory as the Recommended Specialist. Those
  services produced this report; they do not treat the patient. Name the department that
  should act on it — normally whoever ordered the test.
- If a referring doctor or department is printed anywhere on the document, state it under
  Referred By and mention it in the Reason.
- Use markdown tables for medications and lab values.
- Keep language simple and patient-friendly.\
"""


def build_stream_format_system_prompt(departments: "list[str] | None" = None) -> str:
    """The analysis prompt, optionally constrained to the departments this hospital has.

    The department list is INJECTED rather than written into the prompt string, so it can
    never drift from the doctors table. Without it the model was free to end its analysis
    with "Recommended Specialist: Pathology" — a service that produced the report and a
    department with no doctors — which the patient then read as actionable advice.

    Returns the base prompt verbatim when no list is supplied, so the unconstrained path
    is provably unchanged.
    """
    if not departments:
        return _STREAM_FORMAT_SYSTEM
    allowed = " | ".join(str(d).strip() for d in departments if str(d).strip())
    return (
        f"{_STREAM_FORMAT_SYSTEM}\n\n"
        f"Allowed departments for Recommended Specialist (copy ONE exactly): {allowed}\n"
        "If none of them fits, use General Physician."
    )


async def gpt4o_stream_analysis(
    *,
    mime_type: str,
    file_bytes: bytes,
    extracted_text: str | None = None,
    user_question: str = "",
    valid_departments: "list[str] | None" = None,
):
    """
    Stream a beautifully formatted markdown analysis of a medical document.
    Yields string tokens suitable for direct SSE forwarding.

    valid_departments constrains the "Recommended Specialist" line to departments this
    hospital actually staffs. Optional and defaulting to None so every existing caller is
    unaffected; whatever the model names is re-validated server-side regardless.
    """
    client = _get_openai_client()

    if mime_type.startswith("image/") and file_bytes:
        b64 = base64.b64encode(file_bytes).decode("ascii")
        user_content: Any = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}", "detail": "high"},
            },
            {
                "type": "text",
                "text": user_question or "Please provide a detailed formatted analysis of this medical document.",
            },
        ]
    elif extracted_text:
        question_note = f"\n\nPatient's question: {user_question}" if user_question else ""
        user_content = f"Analyze this medical document:\n\n{extracted_text}{question_note}"
    else:
        user_content = user_question or "Please analyze this medical document."

    logger.info("gpt4o_stream_analysis: streaming GPT-4o (mime=%s)", mime_type)

    response = await client.chat.completions.create(
        model=OPENAI_VISION_MODEL,
        messages=[
            {"role": "system", "content": build_stream_format_system_prompt(valid_departments)},
            {"role": "user", "content": user_content},
        ],
        max_completion_tokens=2000,
        temperature=0,
        stream=True,
    )

    async for chunk in response:
        if chunk.choices:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


async def gpt4o_document_summary(*, pages: "list[dict]", document_type: str | None = None) -> "dict[str, Any]":
    """A clinician-register summary of ONE document, with a quote and page per sentence.

    Text-only: the model is given the page text that was extracted and stored at
    ingestion, never the file. That is deliberate. Every sentence it writes is verified
    against exactly this text afterwards (document_grounding.verify_sentences), so letting
    it see the image as well would let it write sentences that are true of the document
    but unverifiable against the stored source — which would then be dropped, wasting the
    call and quietly degrading the summary.

    ONE document per call. Batching would let findings from two reports blend, which is
    the cross-document inference this design keeps in code.

    Returns {"sentences": [...]} exactly as the model produced it. Nothing here is trusted
    — the caller verifies before anything is stored or shown.
    """
    from app.services.document_grounding import SUMMARY_SYSTEM, build_summary_user_content

    if not pages:
        return {"sentences": []}

    client = _get_openai_client()
    logger.info("gpt4o_document_summary: summarising %d pages", len(pages))

    response = await client.chat.completions.create(
        model=OPENAI_VISION_MODEL,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user", "content": build_summary_user_content(pages, document_type)},
        ],
        # Room for one quoted sentence per item AND the verbatim non-clinical lines: a lab
        # report can flag a dozen results, and a truncated JSON reply loses everything.
        max_completion_tokens=4000,
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = (response.choices[0].message.content or "").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"document summary returned invalid JSON: {exc}. Raw: {raw[:300]}") from exc

    sentences = data.get("sentences")
    not_clinical = data.get("not_clinical")
    return {
        "sentences": sentences if isinstance(sentences, list) else [],
        # Lines the model set aside as letterhead, contact details, signatures and the
        # like. Checked verbatim against the page before they count for anything.
        "not_clinical": not_clinical if isinstance(not_clinical, list) else [],
        "model": OPENAI_VISION_MODEL,
    }


_TRANSCRIPTION_SYSTEM = """\
You transcribe a photographed or scanned medical document.

Reproduce the text EXACTLY as printed, line by line, top to bottom. This transcript is
used to verify a later summary against the document, so faithfulness matters far more
than tidiness:

- Copy every value, unit and reference range exactly as written. Do not round, reformat,
  convert units, or correct what looks like a typo.
- Keep the reading order of tables: one row per line, columns separated by spaces.
- Do not summarise, interpret, diagnose, or add anything that is not printed.
- If a word or number is genuinely illegible, write [illegible] in its place rather than
  guessing. A guess would become a quotable "fact" about a patient.

Return JSON only: {"text": "the full transcription"}
"""


async def gpt4o_transcribe_document_image(*, mime_type: str, file_bytes: bytes) -> str:
    """Verbatim transcription of an image document, used as the source text a later
    summary is verified against.

    WHY THIS IS A SEPARATE CALL from the structured extraction. Extraction returns fields;
    this returns the document's own words. Grounded summarisation checks that every quoted
    sentence appears in the source, and for a photograph there is no text layer to check
    against — so the transcription becomes the source of record.

    THE GUARANTEE IS WEAKER HERE, and callers must say so. Verifying a summary against a
    transcription proves the summary invented nothing beyond what was transcribed; it
    cannot prove the transcription was right. Stored with
    document_catalog.PAGE_SOURCE_VISION precisely so that distinction survives, and the
    viewer labels it.
    """
    client = _get_openai_client()
    b64 = base64.b64encode(file_bytes).decode("ascii")

    logger.info("gpt4o_transcribe_document_image: transcribing (mime=%s)", mime_type)
    response = await client.chat.completions.create(
        model=OPENAI_VISION_MODEL,
        messages=[
            {"role": "system", "content": _TRANSCRIPTION_SYSTEM},
            {"role": "user", "content": [
                {"type": "text", "text": "Transcribe this document verbatim."},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
            ]},
        ],
        max_completion_tokens=3000,
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = (response.choices[0].message.content or "").strip()
    try:
        return str(json.loads(raw).get("text") or "").strip()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"transcription returned invalid JSON: {exc}") from exc


_OVERVIEW_SYSTEM = """\
You phrase an at-a-glance summary for a doctor opening a patient's record.

You are given a LIST OF FACTS, each with an id. That list is the whole of what you know.
You have not been shown any document, note or conversation, and you must not act as though
you have.

RULES, all of which are checked by code afterwards:
- Use EVERY fact. A fact you leave out is a medication or a result the doctor does not see.
  Dropping one causes the whole phrasing to be discarded.
- Invent nothing. No diagnosis, no drug, no value that is not in the facts.
- Every number you write must appear in a fact you cite on that same line.
- Cite the fact ids each line came from.
- Related facts may be combined into one line. That is the point of the exercise.
- Keep the label's meaning. A fact labelled "Patient reports" is what the patient said,
  not a finding. One labelled "Reported, unverified" is a medication from another clinic's
  document, not something prescribed here. Never restate either as established fact.
- At most 8 lines, ideally 5 to 6. Clinical register, no filler, no reassurance, no advice.

Return JSON only:
{"lines": [{"text": "...", "fact_ids": ["f1", "f2"]}]}
"""


async def gpt4o_overview_phrasing(*, facts: "list[dict]") -> "dict[str, Any]":
    """Phrases a prepared fact list into an at-a-glance card.

    The model receives ONLY the facts — never a document, a note or a transcript — so it
    has nothing to hallucinate a medication or a diagnosis from. Everything it returns is
    verified against those same facts before it is stored or shown
    (patient_overview.verify_phrasing), and discarded wholesale if it does not hold.
    """
    if not facts:
        return {"lines": []}

    client = _get_openai_client()
    payload = [
        {"id": fact["id"], "text": fact["text"], "label": fact.get("label")}
        for fact in facts
    ]
    logger.info("gpt4o_overview_phrasing: phrasing %d facts", len(payload))

    response = await client.chat.completions.create(
        model=OPENAI_VISION_MODEL,
        messages=[
            {"role": "system", "content": _OVERVIEW_SYSTEM},
            {"role": "user", "content": json.dumps({"facts": payload}, ensure_ascii=False)},
        ],
        max_completion_tokens=700,
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = (response.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"overview phrasing returned invalid JSON: {exc}") from exc

    lines = data.get("lines")
    return {"lines": lines if isinstance(lines, list) else []}



async def gpt4o_nutrition_entry(*, kind: str, term: str, direction: str, retry_reason: str | None = None) -> "dict[str, Any]":
    """Food guidance for ONE finding or symptom — never for a patient.

    The model is told the term and nothing else: no values, no documents, no history. That
    is what makes the guidance the same for every patient with the same result, and why it
    cannot leak one patient's details into another's. Everything returned is checked by
    app/services/nutrition.check_entry before it is stored or shown.

    `retry_reason` is the check that rejected the previous answer, so a retry is told why.
    """
    from app.services.nutrition import NUTRITION_SYSTEM, describe_term

    client = _get_openai_client()
    user = describe_term(kind, term, direction)
    if retry_reason:
        user += f"\n\nYour previous answer was rejected: {retry_reason}. Answer again, following every rule."
    logger.info("gpt4o_nutrition_entry: %s %s %s", kind, term, direction)

    response = await client.chat.completions.create(
        model=OPENAI_VISION_MODEL,
        messages=[
            {"role": "system", "content": NUTRITION_SYSTEM},
            {"role": "user", "content": user},
        ],
        max_completion_tokens=600,
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = (response.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"nutrition entry returned invalid JSON: {exc}") from exc
    return {"entry": data if isinstance(data, dict) else {}, "model": OPENAI_VISION_MODEL}
