"""Doctor-authored clinical actions (prescription / care plan / referral).

These records are deliberately NOT AI-generated — there is no formulary, dose or
interaction checking behind them. What must hold is the same discipline the SOAP note
already has: consult ownership, an immutable approved state, and no approving of an empty
record. Plus the AI provenance and detail-level additions to note generation.

Integration coverage (real SQL: ownership, the approve transition, the audit rows) is in
test_clinical_items_integration.py.
"""

import asyncio

from fastapi import HTTPException
import pytest

from app.agents import consult_documentation_graph as graph
from app.api.routes import consult as consult_route
from app.services import clinical_items


def _doctor(doctor_id="doctor-1"):
    return {"doctor_id": doctor_id, "account_id": "account-1", "name": "Dr. Test"}


# ---- kind validation ----

@pytest.mark.parametrize("kind", ["prescription", "care_plan", "referral"])
def test_valid_kinds_are_accepted(kind):
    assert consult_route._validated_kind(kind) == kind


@pytest.mark.parametrize("kind", ["", "diagnosis", "PRESCRIPTION; DROP TABLE", "../referral"])
def test_invalid_kinds_are_rejected_at_the_route(kind):
    """kind is interpolated into no SQL, but it does select a CHECK-constrained column
    value — rejecting it at the boundary keeps the failure a 400 rather than a 500."""
    if kind == "PRESCRIPTION; DROP TABLE":
        pass
    with pytest.raises(HTTPException) as exc:
        consult_route._validated_kind(kind)
    assert exc.value.status_code == 400


def test_kind_is_normalized_for_case_and_whitespace():
    assert consult_route._validated_kind("  Prescription  ") == "prescription"


def test_service_rejects_unknown_kind_before_touching_the_database():
    with pytest.raises(ValueError):
        clinical_items._validate("something_else")


# ---- empty-state projection ----

def test_a_never_written_item_reads_as_an_empty_draft():
    """One shape for the UI to render, whether or not a row exists yet."""
    item = clinical_items._row_to_item(None, "consult-1", "referral")
    assert item["content"] == ""
    assert item["status"] == "draft"
    assert item["kind"] == "referral"
    assert item["approved_at"] is None


def test_an_existing_row_projects_its_status_and_timestamps():
    from datetime import datetime
    row = ("item-1", "prescription", "Sumatriptan 50mg PRN", "approved",
           datetime(2026, 9, 22, 9, 0), datetime(2026, 9, 22, 9, 30),
           datetime(2026, 9, 22, 10, 0), "doctor-1")
    item = clinical_items._row_to_item(row, "consult-1", "prescription")
    assert item["status"] == "approved"
    assert item["approved_at"] == "2026-09-22T10:00:00"
    assert item["content"] == "Sumatriptan 50mg PRN"


# ---- route error mapping ----

def test_save_route_maps_approved_item_to_conflict(monkeypatch):
    """An approved record is immutable, exactly as a signed note is."""
    def fake_save(consultation_id, doctor_id, kind, content):
        raise PermissionError("This record has already been approved and can no longer be edited.")

    monkeypatch.setattr(consult_route, "save_clinical_item", fake_save)

    with pytest.raises(HTTPException) as exc:
        consult_route.save_clinical_item_route(
            "consult-1", "prescription",
            consult_route.ClinicalItemRequest(content="x"), doctor=_doctor(),
        )
    assert exc.value.status_code == 409


def test_approve_route_maps_empty_record_to_400(monkeypatch):
    def fake_approve(consultation_id, doctor_id, kind):
        raise ValueError("There is nothing to approve — write the record first.")

    monkeypatch.setattr(consult_route, "approve_clinical_item", fake_approve)

    with pytest.raises(HTTPException) as exc:
        consult_route.approve_clinical_item_route("consult-1", "referral", doctor=_doctor())
    assert exc.value.status_code == 400


def test_routes_scope_to_the_authenticated_doctor(monkeypatch):
    seen = {}

    def fake_get(consultation_id, doctor_id, kind):
        seen.update(consultation_id=consultation_id, doctor_id=doctor_id, kind=kind)
        return {"content": ""}

    monkeypatch.setattr(consult_route, "get_clinical_item", fake_get)

    consult_route.get_clinical_item_route("consult-1", "care_plan", doctor=_doctor("doctor-auth"))

    assert seen == {"consultation_id": "consult-1", "doctor_id": "doctor-auth", "kind": "care_plan"}


def test_there_is_no_unapprove_route():
    """Approval is irreversible by design, matching sign_soap_note."""
    paths = {r.path for r in consult_route.router.routes}
    assert not any("unapprove" in p for p in paths)


# ---- SOAP detail level + provenance ----

def test_both_style_directives_exist_for_every_declared_style():
    assert set(graph.SOAP_NOTE_STYLES) == set(graph._STYLE_DIRECTIVES)


def test_the_citation_rule_is_shared_by_both_styles_not_duplicated():
    """The citation and confidence rules are safety-critical. They live in the shared
    prompt precisely so they cannot drift between the two length variants."""
    for style in graph.SOAP_NOTE_STYLES:
        assert "CITATION RULE" not in graph._STYLE_DIRECTIVES[style]
    assert "CITATION RULE" in graph.SOAP_EXTRACTOR_SYSTEM_PROMPT


def test_detailed_style_still_forbids_inventing_content():
    """A longer note must expand on what was said, never fabricate beyond it."""
    directive = graph._STYLE_DIRECTIVES["detailed"].lower()
    assert "forbidden" in directive or "not said" in directive


def test_generate_route_rejects_an_unknown_style():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(consult_route.generate_soap_note_route(
            "consult-1", consult_route.SoapGenerateRequest(style="verbose"), doctor=_doctor()
        ))
    assert exc.value.status_code == 400


def test_generate_route_defaults_to_concise_when_no_body_is_sent(monkeypatch):
    """An existing client that POSTs nothing must keep working unchanged."""
    seen = {}

    async def fake_generate(consultation_id, doctor_id, style):
        seen["style"] = style
        return {"id": "note-1"}

    monkeypatch.setattr(consult_route, "generate_soap_note", fake_generate)

    asyncio.run(consult_route.generate_soap_note_route("consult-1", None, doctor=_doctor()))

    assert seen["style"] == "concise"


def test_generate_route_passes_the_requested_style_through(monkeypatch):
    seen = {}

    async def fake_generate(consultation_id, doctor_id, style):
        seen["style"] = style
        return {"id": "note-1"}

    monkeypatch.setattr(consult_route, "generate_soap_note", fake_generate)

    asyncio.run(consult_route.generate_soap_note_route(
        "consult-1", consult_route.SoapGenerateRequest(style="Detailed"), doctor=_doctor()
    ))

    assert seen["style"] == "detailed"


def test_agenerate_rejects_an_unknown_style_before_calling_the_model():
    with pytest.raises(ValueError):
        asyncio.run(graph.agenerate_soap_note("c1", "p1", [{"id": "s1", "text": "x"}], "verbose"))


def test_prompt_version_is_recorded_with_the_style(monkeypatch):
    """ai_prompt_version must identify the exact prompt+style that produced the text, so
    it stays answerable after the prompt is next edited."""
    async def fake_invoke(state):
        return {"subjective": "s", "objective": "o", "assessment": "a", "plan": "p",
                "field_citations": {}, "confidence_flags": {}}

    monkeypatch.setattr(graph.consult_documentation_graph, "ainvoke", fake_invoke)

    result = asyncio.run(graph.agenerate_soap_note("c1", "p1", [], "detailed"))

    assert result["ai_prompt_version"] == f"{graph.SOAP_PROMPT_VERSION}:detailed"
    assert result["ai_model"]


def test_provenance_reports_the_model_actually_configured(monkeypatch):
    """Read at call time, not hardcoded — a note records what generated it, not what the
    code assumed would."""
    from app.inference import llm

    async def fake_invoke(state):
        return {"subjective": "", "objective": "", "assessment": "", "plan": "",
                "field_citations": {}, "confidence_flags": {}}

    monkeypatch.setattr(graph.consult_documentation_graph, "ainvoke", fake_invoke)

    result = asyncio.run(graph.agenerate_soap_note("c1", "p1", [], "concise"))

    assert result["ai_model"] == llm.CONV_MODEL


def test_style_reaches_the_model_prompt(monkeypatch):
    """The directive must actually be appended to the system prompt, not merely accepted."""
    captured = {}

    async def fake_agenerate_text(system_prompt, user_prompt, **kwargs):
        captured["system_prompt"] = system_prompt
        return '{"subjective":{"text":"","citations":[],"confident":true},"objective":{"text":"","citations":[],"confident":true},"assessment":{"text":"","citations":[],"confident":true},"plan":{"text":"","citations":[],"confident":true}}'

    monkeypatch.setattr(graph, "agenerate_text", fake_agenerate_text)

    asyncio.run(graph.soap_extractor_node({"transcript_text": "x", "style": "detailed", "segments": []}))

    assert graph._STYLE_DIRECTIVES["detailed"] in captured["system_prompt"]
    assert "CITATION RULE" in captured["system_prompt"]
