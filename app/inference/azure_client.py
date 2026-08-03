"""
Azure OpenAI GPT-4o client — INGESTION PATH ONLY.

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

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

try:
    from openai import AsyncAzureOpenAI
    _HAS_OPENAI = True
except ImportError:
    AsyncAzureOpenAI = None  # type: ignore[assignment, misc]
    _HAS_OPENAI = False

_azure_client: "AsyncAzureOpenAI | None" = None


def _get_azure_client() -> "AsyncAzureOpenAI":
    global _azure_client
    if _azure_client is not None:
        return _azure_client
    if not _HAS_OPENAI:
        raise RuntimeError(
            "openai package is not installed. Run: pip install openai>=1.0"
        )
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
        raise RuntimeError(
            "Azure OpenAI is not configured. "
            "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env."
        )
    _azure_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )
    logger.info("azure_client: AsyncAzureOpenAI initialised (deployment=%s)", AZURE_OPENAI_DEPLOYMENT_NAME)
    return _azure_client


_RELEVANCE_SYSTEM = (
    "Analyze this text/image. Is it a medical document, clinical report, lab result, "
    "MRI/X-ray breakdown, or prescription? Answer strictly with either TRUE or FALSE."
)

_EXTRACTION_SYSTEM = """\
You are a medical document extraction AI.
Extract structured information from the provided document.

Return ONLY valid JSON matching this exact structure:
{
  "document_type": "prescription | blood_report | mri_report | ct_report | xray_report | pathology_report | discharge_summary | other",
  "clinical_date": "YYYY-MM-DD or null",
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
- Transcribe values exactly as written. Do NOT invent or estimate any value.\
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
    client = _get_azure_client()

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
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
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
    client = _get_azure_client()

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
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
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
- If illegible write: *Illegible in document*
- If the patient asked a specific question, add: ### Answer to Your Question
- Always include the Recommended Specialist section last.
- Use markdown tables for medications and lab values.
- Keep language simple and patient-friendly.\
"""


async def gpt4o_stream_analysis(
    *,
    mime_type: str,
    file_bytes: bytes,
    extracted_text: str | None = None,
    user_question: str = "",
):
    """
    Stream a beautifully formatted markdown analysis of a medical document.
    Yields string tokens suitable for direct SSE forwarding.
    """
    client = _get_azure_client()

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
        model=AZURE_OPENAI_DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": _STREAM_FORMAT_SYSTEM},
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
