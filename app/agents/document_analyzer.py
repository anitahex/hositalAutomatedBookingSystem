"""
Document analyzer node — handles two distinct paths:

Path A (blob catalog): the patient asks a question about a previously
ingested document. Queries the Postgres catalog, selects relevant
document(s), fetches their summary JSON from blob storage, and composes
an answer via the HF chat model.

Path B (in-memory): a file was uploaded in the current chat turn.
Primary: Azure GPT-4o structured extraction.
Fallback: HF vision model (agenerate_multimodal_text).

Routing: pending_file_data present → Path B. Otherwise → Path A.
"""
from __future__ import annotations

import base64 as _base64
import json
import logging
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser

from app.agents.intake_utils import compact_fact_summary, compact_state_summary
from app.agents.schemas import DocumentAnalysisDecision
from app.agents.state import GraphState
from app.inference.llm import agenerate_multimodal_text

logger = logging.getLogger(__name__)

parser = PydanticOutputParser(pydantic_object=DocumentAnalysisDecision)

STATIC_DOCUMENT_PROMPT = """You are a cautious multimodal medical document analyzer for a hospital assistant.

You will receive:
- extracted text from a medical document
- the user's short clarification
- a small number of page images when available

Your job:
1. Identify the document type.
2. Summarize the core issue in simple language.
3. Map it to the most relevant hospital department.
4. Provide only 1-2 sentences of safe, basic temporary relief.
5. Ask whether the user wants to book an appointment with the recommended department.

Safety rules:
- Do NOT give a diagnosis.
- Do NOT provide long-term home remedies.
- Do NOT provide definitive medical advice.
- Keep the answer concise and practical.

Return ONLY valid JSON matching this exact structure:
{
  "document_type": "string or null",
  "summary": "string",
  "department": "string",
  "temporary_relief": "string",
  "specialist_advice": "string",
  "booking_prompt": "string or null"
}"""


def _file_payload(state: GraphState) -> dict[str, Any]:
    payload = state.get("pending_file_data") or {}
    return payload if isinstance(payload, dict) else {}


def _build_user_parts(state: GraphState) -> list[dict]:
    payload = _file_payload(state)
    extracted_text = str(payload.get("text") or "").strip()
    file_name = str(payload.get("file_name") or state.get("pending_file_name") or "uploaded document")
    file_type = str(payload.get("mime_type") or state.get("pending_file_mime_type") or "unknown")
    page_count = payload.get("page_count")
    source = payload.get("source")
    clarification = (state.get("user_input") or "").strip()
    context = compact_state_summary(state)
    facts = compact_fact_summary(state.get("collected_facts") or state.get("collected_data") or state.get("collected_info"))

    text_block = f"""Extracted Text: {extracted_text or 'No readable text was extracted.'}
File Name: {file_name}
File Type: {file_type}
Page Count: {page_count or 'unknown'}
Source: {source or 'unknown'}
User Context: {context}
Known Facts: {facts}
User Clarification: {clarification or 'None'}"""

    parts = [{"type": "text", "text": text_block}]
    for image in list(payload.get("images") or []):
        if not isinstance(image, dict):
            continue
        url = str(image.get("data_url") or image.get("url") or "").strip()
        if url:
            parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts


def _parse_json(raw_output: str) -> DocumentAnalysisDecision:
    cleaned = (raw_output or "").replace("```json", "").replace("```", "").strip()
    try:
        return parser.parse(cleaned)
    except Exception:
        try:
            data = json.loads(cleaned)
        except Exception:
            data = {}
        return DocumentAnalysisDecision(
            document_type=data.get("document_type"),
            summary=str(data.get("summary") or "The uploaded document appears to need specialist review."),
            department=str(data.get("department") or "General Physician"),
            temporary_relief=str(
                data.get("temporary_relief")
                or "Please rest, stay hydrated, and avoid anything that worsens your symptoms."
            ),
            specialist_advice=str(
                data.get("specialist_advice")
                or "Please see the relevant specialist for a formal review."
            ),
            booking_prompt=data.get("booking_prompt") or "Would you like me to help book an appointment?",
        )


# ---- Path A: catalog-based retrieval ----

async def _catalog_retrieval_response(state: GraphState) -> dict | None:
    """
    Attempt to answer the user's question from the blob catalog.
    Returns a state-update dict on success, None if the catalog is
    unavailable or no documents are found/relevant.
    """
    user_id = state.get("user_id") or (
        state.get("patient_profile") or {}
    ).get("patient_id")
    if not user_id:
        return None

    question = (state.get("user_input") or "").strip()
    if not question:
        return None

    try:
        from app.services.document_catalog import (
            list_user_documents,
            select_relevant_documents,
            answer_from_documents,
        )
    except ImportError as exc:
        logger.warning("document_analyzer: catalog service unavailable: %s", exc)
        return None

    try:
        catalog = list_user_documents(str(user_id))
    except Exception as exc:
        logger.warning("document_analyzer: catalog query failed (table may not exist yet): %s", exc)
        return None
    if not catalog:
        logger.info("document_analyzer: no complete documents in catalog for user_id=%s", user_id)
        return None

    patient_id = str(state.get("patient_id") or user_id)
    chat_session_id = str(state.get("chat_session_id") or "")

    selected_ids = select_relevant_documents(
        question,
        catalog,
        patient_id=patient_id,
        chat_session_id=chat_session_id,
    )

    if not selected_ids:
        logger.info("document_analyzer: no relevant documents found for question")
        return None

    session_cache: dict[str, Any] = dict(state.get("document_session_cache") or {})
    answer = await answer_from_documents(
        question,
        selected_ids,
        catalog,
        patient_id=patient_id,
        chat_session_id=chat_session_id,
        session_summary_cache=session_cache,
    )

    if not answer:
        return None

    history = list(state.get("conversation_history") or [])
    history.append({"role": "assistant", "text": answer})

    return {
        "active_document_id": selected_ids[0],
        "document_session_cache": session_cache,
        "awaiting": "user_input",
        "conversation_history": history,
        "messages": history[-6:],
        "final_response": answer,
    }


# ---- Path B: in-memory analysis — Azure GPT-4o primary, HF vision fallback ----

_DEPT_MAP: dict[str, str] = {
    "blood_report": "Pathology",
    "mri_report": "Radiology",
    "ct_report": "Radiology",
    "xray_report": "Radiology",
    "pathology_report": "Pathology",
    "prescription": "General Physician",
    "discharge_summary": "General Physician",
}

# Ordered by specificity — first match wins
_CONTENT_DEPT_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Orthopedics",    ["ortho", "spine", "lumbar", "cervical", "vertebra", "lba", "back ache",
                        "fracture", "bone", "joint", "ligament", "tendon", "arthritis", "osteo",
                        "scoliosis", "disc", "slipped", "sciatic"]),
    ("Cardiology",     ["cardio", "heart", "ecg", "echo", "hypertension", "cardiac",
                        "chest pain", "angina", "coronary", "artery", "palpitation"]),
    ("Neurology",      ["neuro", "brain", "nerve", "epilepsy", "seizure", "stroke",
                        "neuropathy", "radiculopathy", "mri brain"]),
    ("Endocrinology",  ["diabetes", "thyroid", "insulin", "glucose", "hba1c", "endocrine",
                        "hormonal", "hypothyroid", "hyperthyroid"]),
    ("Pulmonology",    ["lung", "respiratory", "asthma", "copd", "pulmonary",
                        "bronchitis", "pneumonia", "sputum", "wheeze"]),
    ("Gastroenterology", ["gastro", "liver", "stomach", "intestine", "ibs", "colitis",
                          "abdominal", "bowel", "hepatitis", "digestion", "bile"]),
    ("Nephrology",     ["kidney", "renal", "creatinine", "dialysis", "nephritis", "glomerulo"]),
    ("Oncology",       ["cancer", "tumor", "malignant", "biopsy", "chemo", "oncology", "carcinoma"]),
    ("Ophthalmology",  ["eye", "vision", "retina", "cataract", "glaucoma", "cornea", "optic"]),
    ("ENT",            ["ear", "nose", "throat", "sinus", "hearing", "tonsil", "ent", "rhinitis"]),
    ("Dermatology",    ["skin", "rash", "eczema", "psoriasis", "derma", "acne", "fungal"]),
    ("Gynecology",     ["gynae", "uterus", "ovary", "pregnancy", "menstrual", "pcos", "ob-gyn"]),
    ("Urology",        ["urology", "prostate", "bladder", "uti", "urinary tract"]),
    ("Psychiatry",     ["anxiety", "depression", "psychiatric", "mental health", "insomnia", "bipolar"]),
    ("Radiology",      ["mri", "ct scan", "x-ray", "xray", "ultrasound", "radiograph", "imaging"]),
    ("Pathology",      ["blood report", "cbc", "haemoglobin", "wbc", "rbc", "platelet", "lab result"]),
]


def _infer_department(doc_type: str, impression: str, findings: dict) -> str:
    """Pick the most relevant department from the actual clinical content."""
    combined = (impression + " " + " ".join(str(v) for v in findings.values())).lower()
    for dept, keywords in _CONTENT_DEPT_KEYWORDS:
        if any(kw in combined for kw in keywords):
            return dept
    return _DEPT_MAP.get(doc_type, "General Physician")


def _format_finding_value(v: Any) -> str:
    """Render a finding value as readable text, handling nested dicts/lists."""
    if isinstance(v, dict):
        lines = [f"  - {sk}: {sv}" for sk, sv in v.items()]
        return "\n" + "\n".join(lines)
    if isinstance(v, list):
        return ", ".join(str(i) for i in v)
    return str(v)


async def _try_azure_extraction(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Attempt structured extraction via Azure GPT-4o. Returns None on any failure."""
    try:
        from app.inference.azure_client import gpt4o_structured_extraction

        mime_type: str = payload.get("mime_type") or "application/octet-stream"
        extracted_text: str | None = payload.get("text") or None
        images: list[dict] = list(payload.get("images") or [])

        if mime_type.startswith("image/") and images:
            # Image file: decode the data_url → raw bytes for GPT-4o vision
            data_url: str = images[0].get("data_url") or ""
            if "," in data_url:
                b64_part = data_url.split(",", 1)[1]
                file_bytes = _base64.b64decode(b64_part)
            else:
                file_bytes = b""
            actual_mime = images[0].get("mime_type") or mime_type
        elif mime_type == "application/pdf" and images and not extracted_text:
            # Scanned/image-only PDF with no extractable text: send first page image
            data_url = images[0].get("data_url") or ""
            if "," in data_url:
                b64_part = data_url.split(",", 1)[1]
                file_bytes = _base64.b64decode(b64_part)
            else:
                file_bytes = b""
            actual_mime = images[0].get("mime_type") or "image/jpeg"
        else:
            # Text-based PDF: GPT-4o reads extracted_text directly
            file_bytes = b""
            actual_mime = mime_type

        return await gpt4o_structured_extraction(
            mime_type=actual_mime,
            file_bytes=file_bytes,
            extracted_text=extracted_text,
        )
    except Exception as exc:
        logger.warning("document_analyzer: Azure GPT-4o extraction failed, will try HF vision: %s", exc)
        return None


def _build_response_from_extraction(extraction: dict[str, Any]) -> tuple[str, str, dict]:
    """Format GPT-4o extraction result into (response_text, department, collected_facts)."""
    doc_type = str(extraction.get("document_type") or "medical document")
    summary = str(extraction.get("overall_impression") or "The document has been analyzed by the medical AI.")
    findings: dict = dict(extraction.get("findings") or {})
    clinical_date = extraction.get("clinical_date")

    department = _infer_department(doc_type, summary, findings)

    doc_label = doc_type.replace("_", " ").title()
    date_line = f" (dated {clinical_date})" if clinical_date else ""
    response = f"Here is what I found in your **{doc_label}**{date_line}:\n\n{summary}"

    if findings:
        findings_lines = "\n".join(
            f"• **{k}:** {_format_finding_value(v)}"
            for k, v in list(findings.items())[:12]
            if str(v).strip()
        )
        if findings_lines:
            response += f"\n\n**Key Details:**\n{findings_lines}"

    response += (
        f"\n\nBased on this report, I recommend a consultation with **{department}**. "
        "Would you like me to help book an appointment?"
    )

    collected = {
        "document_type": doc_type,
        "document_summary": summary,
        "document_department": department,
        "document_findings": findings,
    }
    return response, department, collected


async def _in_memory_document_analysis(state: GraphState) -> dict:
    payload = _file_payload(state)

    # Primary: Azure GPT-4o structured extraction
    extraction = await _try_azure_extraction(payload)

    if extraction:
        response, department, extra_facts = _build_response_from_extraction(extraction)
        decision_dept = department
    else:
        # Fallback: HF vision model
        user_parts = _build_user_parts(state)
        raw_output = await agenerate_multimodal_text(
            system_prompt=STATIC_DOCUMENT_PROMPT,
            user_parts=user_parts,
            node_name="document_analyzer",
            patient_id=str(state.get("patient_id") or ""),
            chat_session_id=str(state.get("chat_session_id") or ""),
        )
        try:
            decision = _parse_json(raw_output)
        except Exception:
            decision = DocumentAnalysisDecision(
                document_type=payload.get("source") or "medical document",
                summary="The uploaded document appears to describe a medical concern that needs specialist review.",
                department=state.get("target_department") or "General Physician",
                temporary_relief="Please keep monitoring your symptoms and avoid anything that makes them worse.",
                specialist_advice="Please see the relevant specialist for a formal review.",
                booking_prompt="Would you like me to help book an appointment with the recommended department?",
            )
        decision_dept = decision.department
        response = "\n\n".join(
            part for part in [
                decision.summary,
                decision.temporary_relief,
                decision.specialist_advice,
                decision.booking_prompt or "Would you like me to help book an appointment?",
            ] if part
        )
        extra_facts = {
            "document_type": decision.document_type or payload.get("source") or "medical_document",
            "document_summary": decision.summary,
            "document_department": decision.department,
            "document_temporary_relief": decision.temporary_relief,
            "document_specialist_advice": decision.specialist_advice,
        }

    collected = dict(state.get("collected_facts") or state.get("collected_data") or state.get("collected_info") or {})
    collected.update(extra_facts)

    history = list(state.get("conversation_history") or [])
    history.append({"role": "assistant", "text": response})

    # Append to the persistent document analysis log so the supervisor never forgets
    payload = _file_payload(state)
    doc_log = list(state.get("analyzed_documents") or [])
    doc_summary = extra_facts.get("document_summary") or ""
    doc_log.append({
        "file_name": payload.get("file_name") or state.get("pending_file_name") or "uploaded document",
        "document_type": extra_facts.get("document_type") or "document",
        "department": decision_dept,
        "summary": doc_summary[:150] + ("…" if len(doc_summary) > 150 else ""),
    })

    return {
        "pending_file_data": None,
        "pending_file_name": None,
        "pending_file_mime_type": None,
        "file_clarification_context": state.get("user_input") or state.get("file_clarification_context"),
        "awaiting": "user_input",
        "active_intent": "direct_booking",
        "intent": "direct_booking",
        "target_department": decision_dept,
        "collected_facts": collected,
        "collected_data": collected,
        "collected_info": collected,
        "analyzed_documents": doc_log,
        "conversation_history": history,
        "messages": history[-6:],
        "final_response": response,
    }


async def _multi_file_analysis(state: GraphState, files: list[dict[str, Any]]) -> dict:
    """Process all queued files and return a combined structured response."""
    sections: list[str] = []
    doc_log = list(state.get("analyzed_documents") or [])
    collected = dict(state.get("collected_facts") or state.get("collected_data") or state.get("collected_info") or {})
    primary_dept = "General Physician"

    for i, payload in enumerate(files):
        extraction = await _try_azure_extraction(payload)
        if not extraction:
            logger.warning("document_analyzer: multi-file extraction failed for file %d (%s)", i + 1, payload.get("file_name"))
            sections.append(f"**Document {i + 1} ({payload.get('file_name', 'unknown')}):** Could not extract content — please ensure the file is a readable medical document.")
            continue

        doc_type = str(extraction.get("document_type") or "medical document")
        summary = str(extraction.get("overall_impression") or "The document has been analyzed.")
        findings: dict = dict(extraction.get("findings") or {})
        clinical_date = extraction.get("clinical_date")
        department = _infer_department(doc_type, summary, findings)

        if i == 0:
            primary_dept = department

        doc_label = doc_type.replace("_", " ").title()
        date_line = f" (dated {clinical_date})" if clinical_date else ""
        section = f"### Document {i + 1} — {doc_label}{date_line}\n\n{summary}"

        if findings:
            lines = "\n".join(
                f"• **{k}:** {_format_finding_value(v)}"
                for k, v in list(findings.items())[:12]
                if str(v).strip()
            )
            if lines:
                section += f"\n\n**Key Details:**\n{lines}"

        section += f"\n\n*Recommended department: **{department}***"
        sections.append(section)

        collected.update({
            f"doc{i+1}_type": doc_type,
            f"doc{i+1}_summary": summary,
            f"doc{i+1}_department": department,
        })
        doc_log.append({
            "file_name": payload.get("file_name") or f"document_{i+1}",
            "document_type": doc_type,
            "department": department,
            "summary": summary[:150] + ("…" if len(summary) > 150 else ""),
        })

    combined = "\n\n---\n\n".join(sections)
    combined += f"\n\nWould you like me to help book an appointment with **{primary_dept}** or another department?"

    history = list(state.get("conversation_history") or [])
    history.append({"role": "assistant", "text": combined})

    return {
        "pending_file_data": None,
        "pending_files_data": None,
        "pending_file_name": None,
        "pending_file_mime_type": None,
        "file_clarification_context": state.get("user_input") or state.get("file_clarification_context"),
        "awaiting": "user_input",
        "active_intent": "direct_booking",
        "intent": "direct_booking",
        "target_department": primary_dept,
        "collected_facts": collected,
        "collected_data": collected,
        "collected_info": collected,
        "analyzed_documents": doc_log,
        "conversation_history": history,
        "messages": history[-6:],
        "final_response": combined,
    }


# ---- Main node ----

async def document_analyzer_node(state: GraphState) -> dict:
    """
    Route to Path A (blob catalog) or Path B (in-memory) based on state.

    Path B (in-memory) takes priority when pending_file_data is set,
    meaning a file was just uploaded in the current chat turn.
    Path A (blob catalog) is used for questions about previously ingested
    documents when pending_file_data is absent.
    """
    pending_files = list(state.get("pending_files_data") or [])
    if len(pending_files) > 1:
        logger.info("document_analyzer: Path B — multi-file analysis (%d files)", len(pending_files))
        return await _multi_file_analysis(state, pending_files)

    if _file_payload(state):
        logger.info("document_analyzer: Path B — in-memory vision analysis")
        return await _in_memory_document_analysis(state)

    logger.info("document_analyzer: Path A — blob catalog retrieval")
    catalog_result = await _catalog_retrieval_response(state)
    if catalog_result is not None:
        return catalog_result

    # Fallback: no file uploaded and no catalog match — ask the user to upload
    response = (
        "I don't see any previously uploaded medical documents for your account. "
        "Please upload a document using the upload button, or describe your symptoms "
        "so I can help you find the right department."
    )
    history = list(state.get("conversation_history") or [])
    history.append({"role": "assistant", "text": response})
    return {
        "awaiting": "user_input",
        "conversation_history": history,
        "messages": history[-6:],
        "final_response": response,
    }
