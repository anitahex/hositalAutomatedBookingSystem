"""Patient chat with documents: several per message, questions from their findings, and a
pre-appointment summary the patient sees and the doctor receives.

What was wrong, each reproduced before it was fixed:
  - Declining one file dropped every file queued for the session, and removing a pill left
    its file staged, so it was analysed with the next message anyway.
  - Several files in one message were all given the FIRST file's type and department.
  - The questions after an upload were three generic templates, none about the findings.
  - After the questions the chat went straight to booking: no clinical analysis, no
    summary, yet the patient was then asked whether to forward "the report".
  - pre_checkup_summary and pre_checkup_clinical_note were never declared in GraphState,
    so LangGraph dropped them: the summary the patient read never reached the booking.
  - "End the chat" typed mid-intake was taken as an intake answer.

No model and no network: the model calls are replaced, as in test_document_followup.py.
"""
from __future__ import annotations

import asyncio
import json
import re
import typing
from pathlib import Path

import pytest

from app.agents import checkup_report as checkup
from app.agents import document_followup as followup
from app.agents import supervisor
from app.agents.document_followup import (
    AWAITING_DOCUMENT_FOLLOW_UP,
    MAX_DOCUMENT_FOLLOW_UP_QUESTIONS,
    MIN_DOCUMENT_FOLLOW_UP_QUESTIONS,
)

REAL_DEPARTMENTS = [
    "General Physician", "Gastroenterology", "Cardiology", "Neurology",
    "Orthopedics", "Oncology", "Pulmonology", "Psychiatry", "Nephrology",
    "Endocrinology", "Hematology", "Dermatology",
]

BLOOD_ANALYSIS = """## Blood Report Analysis
**Date:** 20 Sep 2026
### Patient Information
- **Name:** Test Patient
- **Referred By:** Not stated
- **Clinical History:** Not stated
### Test Results
| Test | Result | Normal Range | Status |
|---|---|---|---|
| HbA1c | 8.1 % | 4.0 - 5.6 | ⚠️ High |
| Haemoglobin | 13.9 g/dL | 13 - 17 | Normal |
| Vitamin D | 13.8 ng/mL | 30 - 100 | ⚠️ Low |
### Key Findings
- HbA1c is raised, consistent with poorly controlled blood sugar.
- **Vitamin D** is deficient.
### Recommended Specialist
**Endocrinology**
**Reason:** Raised HbA1c needs diabetes review.
"""

MRI_ANALYSIS = """## MRI Report
**Date:** 12 Sep 2026
### Patient Information
- **Name:** Test Patient
- **Referred By:** Dr. Rao, Orthopedics
- **Clinical History:** low back pain radiating to the left leg
### Imaging Details
- **Body Region:** Lumbar spine  - **Technique:** T1/T2
### Findings
- L4-L5 disc bulge indenting the thecal sac.
- Mild left foraminal narrowing.
### Impression
Degenerative disc disease at L4-L5 with left foraminal narrowing.
### Recommended Specialist
**Orthopedics**
**Reason:** Disc bulge with nerve root narrowing.
"""


@pytest.fixture(autouse=True)
def _pure(monkeypatch):
    from app.services import appointments as appointments_service

    monkeypatch.setattr(appointments_service, "routable_departments", lambda *a, **k: list(REAL_DEPARTMENTS))


def _model_returns(monkeypatch, *answers):
    """Replaces the question model with canned replies, one per call; records the prompts."""
    calls = []
    replies = list(answers)

    def fake(system_prompt, user_prompt, state):
        calls.append({"system": system_prompt, "user": user_prompt})
        if not replies:
            raise RuntimeError("no more canned replies")
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)

    monkeypatch.setattr(followup, "_ask_model", fake)
    return calls


def _document(name="blood.pdf", analysis=BLOOD_ANALYSIS, **overrides):
    document = {
        "file_name": name,
        "document_type": "blood_report",
        "department": "Endocrinology",
        "referring_doctor": None,
        "referring_department": None,
        "clinical_history": None,
        "key_findings": followup.parse_key_findings(analysis),
        "followup_round": 1,
    }
    document.update(overrides)
    return document


def _state(**overrides):
    state = {
        "awaiting": AWAITING_DOCUMENT_FOLLOW_UP,
        "analyzed_documents": [_document()],
        "document_topics_asked": [],
        "document_followup_qa": [],
        "document_followup_round": 1,
        "questions_asked": [],
        "symptoms": [],
        "user_input": "",
    }
    state.update(overrides)
    return state


# ---- what a document found ----

def test_abnormal_table_rows_come_first_with_value_range_and_flag():
    findings = followup.parse_key_findings(BLOOD_ANALYSIS)
    assert findings[0] == "HbA1c: 8.1 % (normal 4.0 - 5.6) — High"
    assert findings[1] == "Vitamin D: 13.8 ng/mL (normal 30 - 100) — Low"


def test_a_normal_result_and_the_table_header_are_not_findings():
    findings = " ".join(followup.parse_key_findings(BLOOD_ANALYSIS))
    assert "Haemoglobin" not in findings
    assert "Test:" not in findings and "---" not in findings


def test_key_findings_bullets_are_kept_without_markdown():
    findings = followup.parse_key_findings(BLOOD_ANALYSIS)
    assert "Vitamin D is deficient." in findings
    assert not any("**" in f for f in findings)


def test_imaging_findings_and_impression_are_read_but_not_technique():
    findings = followup.parse_key_findings(MRI_ANALYSIS)
    assert "L4-L5 disc bulge indenting the thecal sac." in findings
    assert any(f.startswith("Degenerative disc disease") for f in findings)
    assert not any("Lumbar spine" in f or "T1/T2" in f for f in findings)
    assert not any("Referred By" in f for f in findings)


def test_findings_are_bounded():
    many = "### Key Findings\n" + "\n".join(f"- finding number {i} " + "x" * 400 for i in range(30))
    findings = followup.parse_key_findings(many)
    assert len(findings) == followup.MAX_KEY_FINDINGS
    assert all(len(f) <= followup.MAX_FINDING_CHARS for f in findings)


def test_no_analysis_gives_no_findings():
    assert followup.parse_key_findings("") == []
    assert followup.parse_key_findings(None) == []


# ---- the model's question, checked by code ----

def test_an_answer_that_is_not_json_is_unusable():
    assert followup.validate_model_question("not json at all", _state()) is None


@pytest.mark.parametrize("reply, problem", [
    ({"done": False, "topic": "x", "question": "Tell me about your sugar levels."}, "question mark"),
    ({"done": False, "topic": "x", "question": "Is it painful? How long? Does it spread?"}, "one question"),
    ({"done": False, "topic": "x", "question": "Is it " + "very " * 80 + "painful?"}, "under"),
    ({"done": False, "topic": "x", "question": ""}, "question mark"),
])
def test_a_question_that_breaks_a_rule_is_refused_with_the_reason(reply, problem):
    result = followup.validate_model_question(json.dumps(reply), _state())
    assert result["question"] is None and problem in result["problem"]


def test_a_question_with_one_clarifier_is_accepted():
    """What the model actually wrote in the live run, refused by the first version."""
    question = ("Can you describe the type of pain you feel in your lower back and leg? "
                "Is it sharp, burning, or aching?")
    result = followup.validate_model_question(json.dumps({"done": False, "topic": "pain", "question": question}), _state())
    assert result["question"] == question


def test_a_question_on_a_topic_already_asked_is_refused():
    state = _state(document_topics_asked=["doc_hba1c"])
    raw = json.dumps({"done": False, "topic": "hba1c", "question": "Were you told you have diabetes?"})
    assert followup.validate_model_question(raw, state)["question"] is None


def test_the_same_question_worded_the_same_is_refused():
    state = _state(document_followup_qa=[{"topic": "doc_a", "question": "Do you feel thirsty often?", "answer": "no"}])
    raw = json.dumps({"done": False, "topic": "thirst", "question": "Do you feel thirsty often?"})
    assert followup.validate_model_question(raw, state)["question"] is None


def test_a_refused_question_keeps_the_symptoms_from_the_answer():
    """Losing them left the templates with no symptoms, and the questions ended at two."""
    raw = json.dumps({"done": False, "topic": "x", "question": "No question mark",
                      "symptoms_mentioned": ["leg pain"]})
    assert followup.validate_model_question(raw, _state())["symptoms"] == ["leg pain"]


def test_a_good_question_is_accepted_with_its_symptoms():
    raw = 'Sure: {"done": false, "topic": "HbA1c High", "question": "Your HbA1c is 8.1%, which is high. Have you noticed more thirst?", "symptoms_mentioned": ["tiredness"]}'
    result = followup.validate_model_question(raw, _state())
    assert result == {
        "done": False,
        "topic": "doc_hba1chigh",
        "question": "Your HbA1c is 8.1%, which is high. Have you noticed more thirst?",
        "symptoms": ["tiredness"],
        "problem": None,
    }


def test_a_refused_question_is_asked_for_again_with_the_reason(monkeypatch):
    calls = _model_returns(
        monkeypatch,
        {"done": False, "topic": "a", "question": "Tell me more", "symptoms_mentioned": ["fatigue"]},
        {"done": False, "topic": "b", "question": "How long have you felt tired?"},
    )
    result = followup.model_question(_state())
    assert result["question"] == "How long have you felt tired?"
    assert "question mark" in calls[1]["user"]
    assert result["symptoms"] == ["fatigue"]


def test_done_before_the_minimum_is_asked_for_again(monkeypatch):
    calls = _model_returns(monkeypatch, {"done": True}, {"done": False, "topic": "b", "question": "Any fever?"})
    topic, question = followup.choose_next_question(_state(document_topics_asked=["doc_a"]))["question"]
    assert question == "Any fever?"
    assert "at least 3 questions" in calls[1]["user"]


def test_two_refusals_fall_back_to_the_templates_keeping_the_symptoms(monkeypatch):
    bad = {"done": False, "topic": "a", "question": "no mark", "symptoms_mentioned": ["back pain"]}
    _model_returns(monkeypatch, bad, bad)
    choice = followup.choose_next_question(_state())
    assert choice["question"][0] == followup.TOPIC_SYMPTOMS
    assert choice["symptoms"] == ["back pain"]


def test_the_prompt_carries_every_document_finding_and_the_answers(monkeypatch):
    calls = _model_returns(monkeypatch, {"done": False, "topic": "a", "question": "Any thirst?"})
    state = _state(
        analyzed_documents=[_document(), _document("mri.pdf", MRI_ANALYSIS, document_type="mri_report")],
        document_followup_qa=[{"topic": "doc_x", "question": "How long?", "answer": "three weeks"}],
        symptoms=["back pain"],
    )
    followup.model_question(state, "it hurts when I sit")
    prompt = calls[0]["user"]
    assert "HbA1c: 8.1 %" in prompt and "L4-L5 disc bulge" in prompt
    assert "three weeks" in prompt and "back pain" in prompt and "it hurts when I sit" in prompt


# ---- choosing the next question ----

def test_a_printed_referral_is_still_asked_first_without_the_model(monkeypatch):
    calls = _model_returns(monkeypatch)
    state = _state(analyzed_documents=[
        _document(),
        _document("mri.pdf", MRI_ANALYSIS, referring_doctor="Dr. Rao", referring_department="Orthopedics"),
    ])
    choice = followup.choose_next_question(state)
    topic, question = choice["question"]
    assert topic == followup.TOPIC_REFERRAL and "Orthopedics" in question
    assert calls == []


def test_the_model_question_is_used_when_it_passes(monkeypatch):
    _model_returns(monkeypatch, {"done": False, "topic": "thirst", "question": "Your HbA1c is high. Any extra thirst?"})
    topic, question = followup.choose_next_question(_state())["question"]
    assert (topic, question) == ("doc_thirst", "Your HbA1c is high. Any extra thirst?")


def test_a_failed_model_falls_back_to_the_templates(monkeypatch):
    _model_returns(monkeypatch, RuntimeError("model down"))
    topic, _ = followup.choose_next_question(_state())["question"]
    assert topic == followup.TOPIC_SYMPTOMS


def test_done_before_the_minimum_does_not_end_the_questions(monkeypatch):
    _model_returns(monkeypatch, {"done": True})
    state = _state(document_topics_asked=["doc_a"])
    assert followup.choose_next_question(state)["question"] is not None


def test_done_after_the_minimum_ends_the_questions(monkeypatch):
    _model_returns(monkeypatch, {"done": True})
    state = _state(document_topics_asked=[f"doc_{i}" for i in range(MIN_DOCUMENT_FOLLOW_UP_QUESTIONS)])
    assert followup.choose_next_question(state)["question"] is None


def test_the_maximum_stops_the_questions_without_asking_the_model(monkeypatch):
    calls = _model_returns(monkeypatch)
    state = _state(document_topics_asked=[f"doc_{i}" for i in range(MAX_DOCUMENT_FOLLOW_UP_QUESTIONS)])
    assert followup.choose_next_question(state)["question"] is None
    assert calls == []


def test_the_minimum_is_three_and_the_maximum_four():
    assert (MIN_DOCUMENT_FOLLOW_UP_QUESTIONS, MAX_DOCUMENT_FOLLOW_UP_QUESTIONS) == (3, 4)


# ---- answers and rounds ----

def test_an_answer_fills_only_the_question_asked_last():
    state = _state(document_followup_qa=[
        {"topic": "a", "question": "Q1?", "answer": "yes"},
        {"topic": "b", "question": "Q2?", "answer": None},
    ])
    qa = followup.record_answer(state, "  about   two weeks ")["document_followup_qa"]
    assert [q["answer"] for q in qa] == ["yes", "about two weeks"]


def test_an_answer_with_nothing_outstanding_changes_nothing():
    state = _state(document_followup_qa=[{"topic": "a", "question": "Q1?", "answer": "yes"}])
    assert followup.record_answer(state, "hello") == {}


def test_a_new_upload_starts_a_new_round():
    delta = followup.start_round(_state(document_followup_round=2, document_topics_asked=["a"], checkup_summary_shown=True))
    assert delta == {"document_followup_round": 3, "document_topics_asked": [], "checkup_summary_shown": False}


def test_questions_are_about_this_round_but_every_document_is_kept():
    old = _document("old.pdf", followup_round=1)
    new = _document("mri.pdf", MRI_ANALYSIS, followup_round=2)
    state = _state(analyzed_documents=[old, new], document_followup_round=2)
    assert [d["file_name"] for d in followup.round_documents(state)] == ["mri.pdf"]


# ---- the supervisor turn ----

def test_an_answer_is_recorded_and_the_next_question_asked(monkeypatch):
    _model_returns(monkeypatch, {
        "done": False, "topic": "thirst", "question": "Any extra thirst?", "symptoms_mentioned": ["fatigue"],
    })
    state = _state(
        document_topics_asked=["doc_first"],
        document_followup_qa=[{"topic": "doc_first", "question": "How are you feeling?", "answer": None}],
    )
    result = supervisor._handle_document_follow_up(state, "tired for 3 weeks")
    assert result["next_agent"] == "finish"
    assert result["awaiting"] == AWAITING_DOCUMENT_FOLLOW_UP
    assert result["final_response"] == "Any extra thirst?"
    assert [q["answer"] for q in result["document_followup_qa"]] == ["tired for 3 weeks", None]
    assert result["symptoms"] == ["fatigue"]
    assert result["collected_data"]["duration"] == "for 3 weeks"


def test_after_the_questions_the_summary_comes_before_any_booking(monkeypatch):
    _model_returns(monkeypatch, {"done": True})
    state = _state(
        document_topics_asked=["doc_a", "doc_b", "doc_c"],
        document_followup_qa=[{"topic": "doc_c", "question": "Q?", "answer": None}],
    )
    result = supervisor._handle_document_follow_up(state, "no")
    assert result["next_agent"] == "checkup_report"
    assert result["checkup_summary_shown"] is False
    assert result["target_department"] == "Endocrinology"
    assert result["document_followup_qa"][-1]["answer"] == "no"


def test_a_referral_on_any_document_counts_not_only_the_latest(monkeypatch):
    """A referral printed on the first of two documents is still a referral."""
    _model_returns(monkeypatch)
    referral = _document("letter.pdf", "", document_type="other", department=None,
                         referring_department="Psychiatry", referring_doctor="Dr. Sen")
    state = _state(analyzed_documents=[referral, _document()], document_topics_asked=["a", "b", "c", "d"])
    result = supervisor._handle_document_follow_up(state, "ok")
    offered = {c["department"] for c in result["candidate_departments"]}
    assert "Psychiatry" in offered


def test_a_conflict_clears_a_department_left_from_earlier(monkeypatch):
    _model_returns(monkeypatch)
    referral = _document("letter.pdf", "", referring_department="Psychiatry", referring_doctor="Dr. Sen")
    state = _state(analyzed_documents=[referral], document_topics_asked=["a", "b", "c", "d"],
                   target_department="Cardiology")
    result = supervisor._handle_document_follow_up(state, "ok")
    assert result["target_department"] is None


# ---- the summary ----

class _FakeModel:
    """Stands in for generate_text in checkup_report: an analysis, then the summary."""

    def __init__(self, recommended="General Physician"):
        self.calls = []
        self.recommended = recommended

    def __call__(self, *, system_prompt, user_prompt, node_name, **kwargs):
        self.calls.append({"system": system_prompt, "user": user_prompt, "node": node_name})
        if node_name == "clinical_analyzer":
            return json.dumps({
                "clinical_analysis": "Raised HbA1c suggests poorly controlled diabetes.",
                "recommended_department": self.recommended,
                "reasoning": "Blood sugar control needs review.",
                "home_care_advice": ["Cut down on sugary drinks", "Walk daily"],
                "severity_assessment": "moderate",
            })
        return "## PRE-APPOINTMENT AI CLINICAL SUMMARY\n**Document Findings:**\n- HbA1c 8.1% high"


def _summary_state(**overrides):
    state = _state(
        awaiting=None,
        document_followup_qa=[{"topic": "doc_a", "question": "Any extra thirst?", "answer": "yes, a lot"}],
        department_match_source="document_followup",
        target_department="Endocrinology",
        patient_profile={"name": "Test Patient", "age": 40, "blood_group": "O+"},
    )
    state.update(overrides)
    return state


def test_the_summary_is_built_from_the_findings_and_answers(monkeypatch):
    model = _FakeModel()
    monkeypatch.setattr(checkup, "generate_text", model)
    result = checkup.checkup_report_node(_summary_state())
    summary_call = next(c for c in model.calls if c["node"] == "checkup_report")
    assert "**Document Findings:**" in summary_call["system"]
    assert "HbA1c: 8.1 %" in summary_call["user"] and "yes, a lot" in summary_call["user"]
    assert result["pre_checkup_summary"].startswith("## PRE-APPOINTMENT AI CLINICAL SUMMARY")


def test_the_patient_sees_the_analysis_and_summary_before_booking(monkeypatch):
    monkeypatch.setattr(checkup, "generate_text", _FakeModel())
    result = checkup.checkup_report_node(_summary_state())
    shown = result["final_response"]
    assert "Raised HbA1c suggests" in shown
    assert "PRE-APPOINTMENT AI CLINICAL SUMMARY" in shown
    assert result["awaiting"] == "booking_decision"
    assert "- Cut down on sugary drinks" in shown and "['" not in shown


def test_the_department_the_follow_up_decided_is_kept_over_the_model(monkeypatch):
    monkeypatch.setattr(checkup, "generate_text", _FakeModel(recommended="Cardiology"))
    result = checkup.checkup_report_node(_summary_state())
    assert result["target_department"] == "Endocrinology"
    assert "Endocrinology" in result["final_response"].rsplit("---", 1)[-1]


def test_on_a_conflict_the_summary_ends_with_the_department_choice(monkeypatch):
    monkeypatch.setattr(checkup, "generate_text", _FakeModel())
    candidates = [
        {"department": "Psychiatry", "reason": "referred", "matched_terms": []},
        {"department": "Endocrinology", "reason": "findings", "matched_terms": []},
    ]
    result = checkup.checkup_report_node(_summary_state(target_department=None, candidate_departments=candidates))
    assert result["awaiting"] == "department_selection"
    assert result["target_department"] is None
    assert [c["department"] for c in result["candidate_departments"]] == ["Psychiatry", "Endocrinology"]
    closing = result["final_response"].rsplit("---", 1)[-1]
    assert "1. Psychiatry" in closing and "2. Endocrinology" in closing
    assert "patient to choose" in result["pre_checkup_clinical_note"]


def test_the_doctor_note_lists_every_document_and_the_answers(monkeypatch):
    monkeypatch.setattr(checkup, "generate_text", _FakeModel())
    state = _summary_state(analyzed_documents=[_document(), _document("mri.pdf", MRI_ANALYSIS, document_type="mri_report")])
    note = checkup.checkup_report_node(state)["pre_checkup_clinical_note"]
    assert "DOCUMENT FINDINGS (read by AI from the uploaded documents — check the originals):" in note
    assert "blood.pdf (blood report)" in note and "mri.pdf (mri report)" in note
    assert "  - L4-L5 disc bulge indenting the thecal sac." in note
    assert "A: yes, a lot" in note


def test_the_symptom_only_summary_is_unchanged(monkeypatch):
    """No documents: the prompts carry no document section, and the flow is as before."""
    model = _FakeModel(recommended="Cardiology")
    monkeypatch.setattr(checkup, "generate_text", model)
    state = {"symptoms": ["chest pain"], "patient_profile": {"name": "P", "age": 50}, "collected_data": {}}
    result = checkup.checkup_report_node(state)
    summary_call = next(c for c in model.calls if c["node"] == "checkup_report")
    assert summary_call["system"] == checkup.STATIC_CHECKUP_PROMPT + (
        "\n\nIMPORTANT: Generate this clinical summary in English only. "
        "Do not translate it to the patient's conversation language."
    )
    assert "DOCUMENTS" not in summary_call["user"]
    assert result["target_department"] == "Cardiology" and result["awaiting"] == "booking_decision"
    assert "DOCUMENT FINDINGS" not in result["pre_checkup_clinical_note"]


# ---- the summary survives to the booking ----

def test_every_state_key_the_patient_agents_read_is_declared():
    """LangGraph drops undeclared keys silently. That is how the summary was lost."""
    from app.agents.state import GraphState

    declared = set(typing.get_type_hints(GraphState))
    agents = Path(__file__).resolve().parents[1] / "app" / "agents"
    missing = {}
    for path in agents.glob("*.py"):
        if path.name == "consult_documentation_graph.py":  # its own graph and state
            continue
        source = path.read_text(encoding="utf-8")
        for key in re.findall(r"state\.get\(\s*[\"']([a-z_]+)[\"']", source):
            if key not in declared:
                missing.setdefault(key, set()).add(path.name)
    assert missing == {}


def test_the_summary_keys_survive_a_real_graph_step():
    from langgraph.graph import END, StateGraph

    from app.agents.state import GraphState

    def write(state):
        return {"pre_checkup_summary": "S", "pre_checkup_clinical_note": "N", "document_followup_qa": [{"q": 1}]}

    def read(state):
        return {"final_response": f"{state.get('pre_checkup_summary')}|{state.get('pre_checkup_clinical_note')}"}

    graph = StateGraph(GraphState)
    graph.add_node("write", write)
    graph.add_node("read", read)
    graph.set_entry_point("write")
    graph.add_edge("write", "read")
    graph.add_edge("read", END)
    out = graph.compile().invoke({"user_input": "x"})
    assert out["final_response"] == "S|N"
    assert out["document_followup_qa"] == [{"q": 1}]


def test_forwarding_sends_the_summary_the_patient_saw(monkeypatch):
    sent = {}
    monkeypatch.setattr(supervisor, "update_booking_note",
                        lambda booking_id, patient_id, booking_note: sent.update(note=booking_note) or {
                            "booking_id": booking_id, "doctor": "Dr. A", "time": "10:00", "booking_note": booking_note})
    monkeypatch.setattr(supervisor, "_generate_clinical_note",
                        lambda *a, **k: pytest.fail("must not regenerate a note when the summary exists"))
    state = {
        "awaiting": "report_forwarding_decision",
        "user_input": "yes",
        "patient_id": "p1",
        "report_forwarding_booking_id": "b1",
        "upcoming_bookings": [{"booking_id": "b1", "doctor": "Dr. A", "time": "10:00"}],
        "pre_checkup_summary": "## PRE-APPOINTMENT AI CLINICAL SUMMARY\n**Document Findings:**\n- HbA1c high",
    }
    supervisor.continue_current_node(state)
    assert sent["note"] == state["pre_checkup_summary"]


def test_a_note_sent_without_a_summary_still_carries_the_findings(monkeypatch):
    """The patient named a department and skipped the questions: no summary was made. If
    they agree to send a note, it is written then, with the documents' findings added."""
    monkeypatch.setattr(supervisor, "_generate_clinical_note",
                        lambda state, user_text=None: "## PRE-APPOINTMENT AI CLINICAL SUMMARY\n**Chief Complaint:** back pain")
    state = _state(document_followup_qa=[{"topic": "a", "question": "How long?", "answer": "a month"}])
    note = supervisor._forwardable_summary(state)
    assert note.startswith("## PRE-APPOINTMENT AI CLINICAL SUMMARY")
    assert "## Documents shared in the booking chat" in note
    assert "**blood.pdf** · blood report" in note
    assert "- HbA1c: 8.1 % (normal 4.0 - 5.6) — High" in note
    assert "- How long? — a month" in note


def test_the_formatted_summary_is_what_gets_sent_never_the_plain_report():
    state = {"pre_checkup_summary": "## PRE-APPOINTMENT AI CLINICAL SUMMARY\n**Document Findings:**",
             "pre_checkup_clinical_note": "PRE-AI INTAKE CHECKUP REPORT (Auto-generated from patient chat)"}
    assert supervisor._forwardable_summary(state) == state["pre_checkup_summary"]


def test_a_missing_summary_heading_is_added(monkeypatch):
    """The doctor's screens recognise the summary by this heading; the model sometimes omits it."""
    class NoHeading(_FakeModel):
        def __call__(self, *, system_prompt, user_prompt, node_name, **kwargs):
            reply = super().__call__(system_prompt=system_prompt, user_prompt=user_prompt, node_name=node_name)
            return reply if node_name == "clinical_analyzer" else "**Patient:** Test | **Chief Complaint:** back pain"

    monkeypatch.setattr(checkup, "generate_text", NoHeading())
    summary = checkup.checkup_report_node(_summary_state())["pre_checkup_summary"]
    assert summary.startswith("## PRE-APPOINTMENT AI CLINICAL SUMMARY\n\n**Patient:** Test")


# ---- consent before anything is attached ----

def _book(monkeypatch, **state_overrides):
    """Books slot 1 through the real booker; returns (result, the note the booking was made with)."""
    from app.agents import appointment_booker

    seen = {}

    def fake_book(slot_id, patient_id=None, booking_note=None, booking_context=None):
        seen["note"] = booking_note
        return {"booking_id": "bk-1", "slot_id": slot_id, "doctor_name": "Dr. Thanvi",
                "department": "Orthopedics", "start_time": "2026-10-01T10:00:00"}

    monkeypatch.setattr(appointment_booker, "book_selected_slot", fake_book)
    state = {
        "awaiting": "slot_selection", "user_input": "1", "patient_id": "p1",
        "slot_options": [{"slot_id": "s1", "start_time": "2026-10-01T10:00:00"}],
        "pre_checkup_summary": "## PRE-APPOINTMENT AI CLINICAL SUMMARY",
        "pre_checkup_clinical_note": "PRE-AI INTAKE CHECKUP REPORT",
        "target_department": "Orthopedics",
    }
    state.update(state_overrides)
    return appointment_booker.book_preferred_slot(state), seen["note"]


def test_nothing_is_attached_at_booking(monkeypatch):
    """The plain-text report used to be attached automatically, without asking."""
    result, note = _book(monkeypatch)
    assert note is None
    assert result["awaiting"] == "report_forwarding_decision"
    assert result["report_forwarding_booking_id"] == "bk-1"


def test_every_booking_asks_first_even_with_more_departments_to_book(monkeypatch):
    """Multi-department chats used to skip the question and claim the summary was attached."""
    candidates = [{"department": "Orthopedics"}, {"department": "Psychiatry"}, {"department": "Endocrinology"}]
    result, note = _book(monkeypatch, candidate_departments=candidates, analyzed_documents=[_document()])
    assert note is None
    assert result["awaiting"] == "report_forwarding_decision"
    assert [c["department"] for c in result["candidate_departments"]] == ["Psychiatry", "Endocrinology"]
    assert "attached" not in result["final_response"]
    response = result["final_response"]
    said = "Your pre-appointment summary includes the findings from the documents you shared."
    assert said in response and response.index(said) < response.index("forward")


def _forward(monkeypatch, answer, **state_overrides):
    sent = {}
    monkeypatch.setattr(supervisor, "update_booking_note",
                        lambda booking_id, patient_id, booking_note: sent.update(note=booking_note, booking=booking_id) or {
                            "booking_id": booking_id, "doctor": "Dr. Thanvi", "time": "10:00", "booking_note": booking_note})
    state = {
        "awaiting": "report_forwarding_decision", "user_input": answer, "patient_id": "p1",
        "report_forwarding_booking_id": "bk-1",
        "upcoming_bookings": [{"booking_id": "bk-1", "doctor": "Dr. Thanvi", "time": "10:00"}],
        "pre_checkup_summary": "## PRE-APPOINTMENT AI CLINICAL SUMMARY",
    }
    state.update(state_overrides)
    return supervisor.continue_current_node(state), sent


def test_yes_sends_the_summary_to_that_booking_then_offers_the_next_department(monkeypatch):
    result, sent = _forward(monkeypatch, "yes", candidate_departments=[{"department": "Psychiatry"}])
    assert sent == {"note": "## PRE-APPOINTMENT AI CLINICAL SUMMARY", "booking": "bk-1"}
    assert result["note_forwarded"] is True
    assert result["awaiting"] == "department_selection"
    assert [c["department"] for c in result["candidate_departments"]] == ["Psychiatry"]
    assert "1. Psychiatry" in result["final_response"]


def test_no_sends_nothing_and_still_offers_the_next_department(monkeypatch):
    result, sent = _forward(monkeypatch, "no", candidate_departments=[{"department": "Psychiatry"}])
    assert sent == {}
    assert result["note_forwarded"] is False
    assert result["awaiting"] == "department_selection"


def test_with_nothing_left_to_book_the_chat_winds_down(monkeypatch):
    result, _ = _forward(monkeypatch, "yes", candidate_departments=[])
    assert result["awaiting"] == "end_confirmation"
    assert "department" not in result["final_response"].lower().split("confirmed.")[-1]


@pytest.mark.parametrize("reply", ["no", "No thanks", "that's all"])
def test_no_at_the_department_menu_stops_as_the_menu_says(reply):
    """It used to answer "Please reply with one of the listed department numbers"."""
    from app.agents import appointment_booker

    result = appointment_booker._appointment_booker_node({
        "awaiting": "department_selection", "user_input": reply,
        "candidate_departments": [{"department": "Psychiatry"}],
    })
    assert result["awaiting"] == "end_confirmation"
    assert result["candidate_departments"] == []
    assert "nothing else is booked" in result["final_response"]


def test_a_department_named_at_the_menu_is_still_chosen():
    from app.agents import appointment_booker

    choice = appointment_booker.choose_department_candidate({
        "user_input": "psychiatry", "candidate_departments": [{"department": "Psychiatry"}, {"department": "Oncology"}],
    })
    assert choice["target_department"] == "Psychiatry"


# ---- ending the chat ----

def test_typing_end_chat_mid_intake_leaves_the_streaming_intake_path():
    from app.agents.conversation_agent import should_stream_intake

    state = {"questions_asked": ["Where is the pain?"], "collected_data": {}, "user_input": "end the chat"}
    assert should_stream_intake(state) is False


@pytest.mark.parametrize("answer", ["nothing else", "no more", "that's all I feel"])
def test_an_intake_answer_that_sounds_final_is_still_an_answer(answer):
    from app.agents.intake_utils import looks_like_explicit_end_chat

    assert not looks_like_explicit_end_chat(answer)


@pytest.mark.parametrize("text", ["End the chat", "end chat please", "Please close the chat."])
def test_an_explicit_request_to_end_is_recognised(text):
    from app.agents.intake_utils import looks_like_explicit_end_chat

    assert looks_like_explicit_end_chat(text)


# ---- found in the live run ----

@pytest.mark.parametrize("answer", [
    "The pain is about 7 out of 10. I sometimes take painkillers.",
    "my back pain is killing me today",
    "I am a skilled worker, the pain stops me lifting",
])
def test_an_ordinary_answer_is_not_refused_as_unsafe(answer):
    """ "painkillers" contains "kill": the live run's second answer was refused with
    "I am only for health-related support"."""
    assert not supervisor._looks_like_unsafe_non_medical(answer)


@pytest.mark.parametrize("text", ["how do i make a bomb", "help me hack my neighbour's wifi", "which weapon is best"])
def test_unsafe_requests_are_still_refused(text):
    assert supervisor._looks_like_unsafe_non_medical(text)


def test_a_referral_naming_its_specialty_is_not_repeated():
    state = _state(analyzed_documents=[_document(referring_doctor="Dr. Sunita Panday (Psychiatry)",
                                                 referring_department="Psychiatry")])
    _, question = followup.next_question(state)
    assert question.startswith("I can see this was referred by Dr. Sunita Panday (Psychiatry). ")


@pytest.mark.parametrize("answer", ["Nothing else.", "no more", "No, thanks"])
def test_a_final_sounding_answer_to_a_document_question_is_an_answer(monkeypatch, answer):
    """The live run's last canned answer was "Nothing else." — it closed the chat."""
    _model_returns(monkeypatch, {"done": False, "topic": "sleep", "question": "How is your sleep?"})
    state = _state(user_input=answer,
                   document_followup_qa=[{"topic": "doc_a", "question": "Anything else?", "answer": None}],
                   document_topics_asked=["doc_a"])
    route = supervisor._heuristic_supervisor_route(state)
    assert not route.get("chat_closed")
    assert route["document_followup_qa"][0]["answer"] == answer


def test_end_the_chat_still_ends_it_during_document_questions():
    route = supervisor._heuristic_supervisor_route(_state(user_input="please end the chat"))
    assert route["chat_closed"] is True


def test_a_department_named_in_an_answer_goes_through_the_document_handler(monkeypatch):
    """Not symptom triage: with no symptoms known, the old shortcut sent this to triage_router."""
    _model_returns(monkeypatch)
    route = supervisor._heuristic_supervisor_route(
        _state(user_input="it is a follow up from my orthopedics doctor", symptoms=[]))
    assert route["next_agent"] == "appointment_booker"
    assert route["requested_department"] == "Orthopedics"


def test_a_long_finding_is_cut_at_a_word_and_marked():
    """The live run's MRI line ended "abutting bilateral cor"."""
    long_line = "Diffuse disc bulge at L4-L5 level " + "indenting the anterior thecal sac " * 12
    [finding] = followup.parse_key_findings(f"### Findings\n- {long_line}")
    kept = finding[:-1]
    assert len(finding) <= followup.MAX_FINDING_CHARS and finding.endswith("…")
    assert long_line.startswith(kept) and long_line[len(kept)] == " "


def test_a_three_document_note_and_the_forwarded_summary_fit_the_booking_note():
    from app.services.appointments import BOOKING_NOTE_MAX_LENGTH

    # The live run's note was 3529 characters; the summary forwarded after it is ~2500.
    assert BOOKING_NOTE_MAX_LENGTH >= 3529 + 2500 * 2
