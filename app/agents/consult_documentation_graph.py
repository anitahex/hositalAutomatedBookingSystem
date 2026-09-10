"""SOAP clinical note generation subgraph (Phase 3, Part 2).

Entirely separate from app/agents/graph.py's patient-facing chat graph: different
state shape, different entry point, no shared nodes, no shared checkpointer. This is a
single-shot batch pipeline over an already-complete transcript (Transcript Segmenter ->
SOAP Extractor -> Confidence Validator) — there is no multi-turn conversation to resume,
so it is compiled with no checkpointer at all, unlike the patient graph's
SQLiteCheckpointer.

Structured output follows this codebase's existing convention (see triage_router.py /
remedy_agent.py): no JSON-mode/function-calling anywhere in this codebase — the system
prompt hand-writes the exact JSON shape, and the raw response is parsed with
PydanticOutputParser against app.agents.schemas.SOAPNoteExtraction.
"""
from __future__ import annotations

from typing import TypedDict

from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import END, StateGraph

from app.agents.schemas import SOAPNoteExtraction
from app.inference.llm import agenerate_text

_SOAP_FIELDS = ("subjective", "objective", "assessment", "plan")

_parser = PydanticOutputParser(pydantic_object=SOAPNoteExtraction)

SOAP_EXTRACTOR_SYSTEM_PROMPT = """You are a clinical documentation assistant producing a SOAP note from a doctor-patient consultation transcript. The transcript is speaker-labeled and each line is prefixed with its segment id in square brackets, e.g. "[a1b2c3] Doctor: How long has the pain lasted?".

Write four sections:
- Subjective: patient-reported symptoms, history, and complaints.
- Objective: observable/measurable findings the doctor stated (exam findings, vitals, test results mentioned).
- Assessment: the doctor's clinical assessment or diagnosis discussed.
- Plan: the treatment, medication, or follow-up plan the doctor discussed.

CITATION RULE — this is mandatory, not optional: every section with non-empty text MUST cite the exact segment id(s) (the bracketed tokens, without the brackets) it was derived from. Never write a sentence you cannot trace back to a specific transcript line. If the transcript genuinely contains nothing for a section, return an empty string for that section's text and an empty citations list — do not invent content to fill a section.

If you are not fully confident a section is accurate or complete (ambiguous speaker attribution, garbled transcript, conflicting statements), set that section's "confident" field to false rather than silently guessing.

Return ONLY valid JSON matching this exact structure (no markdown, no explanation):
{"subjective":{"text":"...","citations":["segid1","segid2"],"confident":true},"objective":{"text":"...","citations":[],"confident":true},"assessment":{"text":"...","citations":[],"confident":true},"plan":{"text":"...","citations":[],"confident":true}}"""


class ConsultDocState(TypedDict, total=False):
    consultation_id: str
    patient_id: str
    segments: list[dict]
    transcript_text: str
    subjective: str
    objective: str
    assessment: str
    plan: str
    field_citations: dict
    confidence_flags: dict
    parse_failed: bool


def _clean_json(raw_output: str) -> str:
    return raw_output.replace("```json", "").replace("```", "").strip()


def _speaker_label(speaker: str | None) -> str:
    return {"doctor": "Doctor", "patient": "Patient"}.get(speaker or "", "Unknown")


def transcript_segmenter_node(state: ConsultDocState) -> dict:
    """Formats the corrected final transcript into clean speaker-labeled dialogue,
    preserving each segment's id so the extractor (and, later, the doctor reviewing
    citations) can trace any sentence back to its exact transcript line."""
    segments = state.get("segments") or []
    lines = [
        f"[{segment['id']}] {_speaker_label(segment.get('speaker'))}: {segment.get('text', '')}"
        for segment in segments
        if segment.get("id")
    ]
    return {"transcript_text": "\n".join(lines)}


async def soap_extractor_node(state: ConsultDocState) -> dict:
    transcript_text = state.get("transcript_text") or ""
    user_prompt = f"Transcript:\n{transcript_text}"

    raw_output = await agenerate_text(
        system_prompt=SOAP_EXTRACTOR_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        node_name="soap_extractor",
        include_history=False,
        history_turns=0,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("consultation_id") or ""),
    )

    try:
        extracted = _parser.parse(_clean_json(raw_output))
    except Exception:
        return {"parse_failed": True}

    valid_ids = {segment["id"] for segment in (state.get("segments") or []) if segment.get("id")}

    def _valid_citations(field) -> list[str]:
        return [c for c in field.citations if c in valid_ids]

    fields = {
        "subjective": extracted.subjective,
        "objective": extracted.objective,
        "assessment": extracted.assessment,
        "plan": extracted.plan,
    }
    return {
        **{name: field.text for name, field in fields.items()},
        "field_citations": {name: _valid_citations(field) for name, field in fields.items()},
        "confidence_flags": {name: not field.confident for name, field in fields.items()},
    }


def confidence_validator_node(state: ConsultDocState) -> dict:
    """Flags any field whose text is non-empty but ended up with zero *valid* citations
    (the model either cited nothing, or cited only segment ids that don't exist in this
    transcript) as not-confident, even if the model itself claimed confident=true — an
    unverifiable field must never reach the doctor looking as trustworthy as a properly
    cited one."""
    field_citations = state.get("field_citations") or {}
    confidence_flags = dict(state.get("confidence_flags") or {})
    for field_name in _SOAP_FIELDS:
        text = (state.get(field_name) or "").strip()
        citations = field_citations.get(field_name) or []
        if text and not citations:
            confidence_flags[field_name] = True
    return {"confidence_flags": confidence_flags}


_workflow = StateGraph(ConsultDocState)
_workflow.add_node("transcript_segmenter", transcript_segmenter_node)
_workflow.add_node("soap_extractor", soap_extractor_node)
_workflow.add_node("confidence_validator", confidence_validator_node)
_workflow.set_entry_point("transcript_segmenter")
_workflow.add_edge("transcript_segmenter", "soap_extractor")
_workflow.add_edge("soap_extractor", "confidence_validator")
_workflow.add_edge("confidence_validator", END)

# No checkpointer: this is a single-shot batch pipeline invoked fresh on every
# generate-note request, with no multi-turn state to resume across calls.
consult_documentation_graph = _workflow.compile()


async def agenerate_soap_note(consultation_id: str, patient_id: str, segments: list[dict]) -> dict:
    """Runs the subgraph end-to-end and returns the fields the service layer needs to
    persist. Raises RuntimeError if the LLM's output could not be parsed into a
    structured note at all (total LLM failure, or malformed JSON) — callers must not
    persist a note in that case."""
    result = await consult_documentation_graph.ainvoke(
        {
            "consultation_id": consultation_id,
            "patient_id": patient_id,
            "segments": segments,
        }
    )
    if result.get("parse_failed"):
        raise RuntimeError(
            "Could not generate a structured clinical note from this transcript. Please try again."
        )
    return {
        "subjective": result.get("subjective") or "",
        "objective": result.get("objective") or "",
        "assessment": result.get("assessment") or "",
        "plan": result.get("plan") or "",
        "field_citations": result.get("field_citations") or {},
        "confidence_flags": result.get("confidence_flags") or {},
    }
