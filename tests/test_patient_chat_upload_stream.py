"""Several documents in one chat message: staging, consent per file, and the analysis stream.

Same convention as test_document_upload_e2e.py — route functions called directly, blob
storage and the models replaced, no network. The analysis cache is replaced with an empty
dict per test so nothing queued here leaks into another test.

What was wrong, each reproduced first:
  - declining one file dropped every file queued for the session;
  - removing a pill left its file queued, and it was analysed with the next message;
  - a file could be analysed before the patient agreed to it once consent moved to Send;
  - every document of a multi-file message got the first one's type and department;
  - the analysis ended without a question, so the patient had to type something first.
"""
from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.agents import document_followup as followup
from app.api.routes import chat as chat_route
from tests.test_patient_chat_documents import BLOOD_ANALYSIS, MRI_ANALYSIS, REAL_DEPARTMENTS


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    from app.services import appointments as appointments_service

    monkeypatch.setattr(chat_route, "_doc_analysis_cache", {})
    monkeypatch.setattr(appointments_service, "routable_departments", lambda *a, **k: list(REAL_DEPARTMENTS))


def _entry(token, name="report.pdf", consented=False):
    return {"file_name": name, "mime_type": "application/pdf", "text": "x", "images": [],
            "document_token": token, "consented": consented}


def _key(user="patient-1", session="session-1"):
    return chat_route._doc_cache_key(user, session)


def _user(patient_id="patient-1"):
    return {"patient_id": patient_id, "name": "Test Patient"}


def _pending_record(token_session="session-1"):
    return {"user_id": "patient-1", "session_id": token_session, "document_id": "doc-1",
            "blob_path": "staging/patient-1/doc-1/report.pdf", "original_filename": "report.pdf"}


# ---- the queue ----

def test_discarding_one_file_keeps_the_others():
    chat_route._doc_analysis_cache[_key()] = [_entry("t1"), _entry("t2"), _entry("t3")]
    chat_route._discard_cached_document("patient-1", "session-1", "t2")
    assert [e["document_token"] for e in chat_route._doc_analysis_cache[_key()]] == ["t1", "t3"]


def test_discarding_the_last_file_empties_the_queue():
    chat_route._doc_analysis_cache[_key()] = [_entry("t1")]
    chat_route._discard_cached_document("patient-1", "session-1", "t1")
    assert _key() not in chat_route._doc_analysis_cache


def test_only_consented_files_are_taken_for_analysis():
    chat_route._doc_analysis_cache[_key()] = [_entry("t1", consented=True), _entry("t2"), _entry("t3", consented=True)]
    taken = chat_route._take_consented_documents(_key())
    assert [e["document_token"] for e in taken] == ["t1", "t3"]
    assert [e["document_token"] for e in chat_route._doc_analysis_cache[_key()]] == ["t2"]


# ---- consent, per file ----

def test_declining_one_file_leaves_the_other_queued(monkeypatch):
    chat_route._doc_analysis_cache[_key()] = [_entry("tok-1"), _entry("tok-2", consented=True)]
    monkeypatch.setattr(chat_route, "consume_pending_upload", lambda token: _pending_record())

    async def fake_delete_blob(path):
        return None

    monkeypatch.setattr(chat_route, "delete_blob", fake_delete_blob)
    request = chat_route.ConfirmProcessingRequest(document_token="tok-1", consent_granted=False)
    asyncio.run(chat_route.confirm_processing(request, BackgroundTasks(), user=_user()))
    assert [e["document_token"] for e in chat_route._doc_analysis_cache[_key()]] == ["tok-2"]


def test_consent_marks_only_that_file_ready_for_analysis(monkeypatch):
    chat_route._doc_analysis_cache[_key()] = [_entry("tok-1"), _entry("tok-2")]
    monkeypatch.setattr(chat_route, "consume_pending_upload", lambda token: _pending_record())

    async def fake_move_blob(source, dest):
        return None

    monkeypatch.setattr(chat_route, "move_blob", fake_move_blob)
    request = chat_route.ConfirmProcessingRequest(document_token="tok-1", consent_granted=True)
    asyncio.run(chat_route.confirm_processing(request, BackgroundTasks(), user=_user()))
    assert [e["consented"] for e in chat_route._doc_analysis_cache[_key()]] == [True, False]


def test_a_file_that_could_not_be_stored_is_not_analysed(monkeypatch):
    chat_route._doc_analysis_cache[_key()] = [_entry("tok-1")]
    monkeypatch.setattr(chat_route, "consume_pending_upload", lambda token: _pending_record())

    async def failing_move(source, dest):
        raise OSError("storage down")

    monkeypatch.setattr(chat_route, "move_blob", failing_move)
    request = chat_route.ConfirmProcessingRequest(document_token="tok-1", consent_granted=True)
    with pytest.raises(HTTPException):
        asyncio.run(chat_route.confirm_processing(request, BackgroundTasks(), user=_user()))
    assert _key() not in chat_route._doc_analysis_cache


# ---- the per-message cap ----

class _FakeUploadFile:
    filename = "fourth.pdf"
    content_type = "application/pdf"

    async def read(self):
        return b"%PDF-1.4 fourth"


class _FakeRequest:
    async def form(self):
        return {"file": _FakeUploadFile(), "session_id": "session-1"}


def test_a_fourth_document_for_one_message_is_refused_before_any_model_call(monkeypatch):
    chat_route._doc_analysis_cache[_key()] = [_entry("t1"), _entry("t2"), _entry("t3")]

    async def must_not_run(**kwargs):
        pytest.fail("the relevance check must not run for a refused file")

    monkeypatch.setattr("app.inference.azure_client.gpt4o_relevance_check", must_not_run)
    with pytest.raises(HTTPException) as refused:
        asyncio.run(chat_route.upload_document(_FakeRequest(), user=_user()))
    assert refused.value.status_code == 400
    assert "up to 3 documents" in refused.value.detail


def test_an_upload_is_queued_with_its_token_and_without_consent(monkeypatch):
    async def relevant(**kwargs):
        return True

    async def fake_upload_blob(path, data, content_type="application/octet-stream"):
        return None

    monkeypatch.setattr("app.inference.azure_client.gpt4o_relevance_check", relevant)
    monkeypatch.setattr(chat_route, "upload_blob", fake_upload_blob)
    monkeypatch.setattr(chat_route, "save_pending_upload", lambda **kwargs: None)
    monkeypatch.setattr("app.services.document_pipeline._extract_pdf_images", lambda data: [])
    result = asyncio.run(chat_route.upload_document(_FakeRequest(), user=_user()))
    [entry] = chat_route._doc_analysis_cache[_key()]
    assert entry["document_token"] == result["document_token"]
    assert entry["consented"] is False


# ---- the analysis stream ----

def _run_stream(monkeypatch, files, message="Please analyze these medical documents.", model_reply=None,
                prepared=None, analyses=(BLOOD_ANALYSIS, MRI_ANALYSIS, BLOOD_ANALYSIS)):
    analyses = iter(analyses)

    async def fake_stream_analysis(**kwargs):
        text = next(analyses)
        for index in range(0, len(text), 40):
            yield text[index:index + 40]

    async def fake_parse(request):
        return {"message": message, "session_id": "session-1", "state": {}}, None

    def fake_prepare(payload, user):
        base = {"session_id": "session-1", "chat_session_id": "session-1", "conversation_history": []}
        return {**base, **(prepared or {})}, None

    prompts = []

    def fake_model(system_prompt, user_prompt, state):
        prompts.append(user_prompt)
        return json.dumps(model_reply or {
            "done": False, "topic": "hba1c", "question": "Your HbA1c is 8.1%, which is high. Any extra thirst?",
        })

    monkeypatch.setattr("app.inference.azure_client.gpt4o_stream_analysis", fake_stream_analysis)
    monkeypatch.setattr(chat_route, "_parse_chat_request", fake_parse)
    monkeypatch.setattr(chat_route, "_prepare_chat_state", fake_prepare)
    monkeypatch.setattr(followup, "_ask_model", fake_model)
    chat_route._doc_analysis_cache[_key()] = files

    async def collect():
        response = await chat_route.chat_stream(object(), user=_user())
        events = []
        async for chunk in response.body_iterator:
            text = chunk.decode() if isinstance(chunk, bytes) else chunk
            events.extend(json.loads(line) for line in text.splitlines() if line.strip())
        return events

    events = asyncio.run(collect())
    final = next(e for e in events if e["type"] == "final")
    return events, final, prompts


def test_each_document_gets_its_own_labels_and_findings(monkeypatch):
    files = [_entry("t1", "blood.pdf", consented=True), _entry("t2", "mri.pdf", consented=True)]
    _, final, _ = _run_stream(monkeypatch, files)
    blood, mri = final["state"]["analyzed_documents"]
    assert (blood["file_name"], blood["document_type"], blood["department"]) == ("blood.pdf", "blood_report", "Endocrinology")
    assert (mri["file_name"], mri["document_type"], mri["department"]) == ("mri.pdf", "mri_report", "Orthopedics")
    assert blood["referring_department"] is None and mri["referring_department"] == "Orthopedics"
    assert "HbA1c: 8.1 % (normal 4.0 - 5.6) — High" in blood["key_findings"]
    assert "L4-L5 disc bulge indenting the thecal sac." in mri["key_findings"]
    assert {blood["followup_round"], mri["followup_round"]} == {1}


def test_several_documents_are_headed_one_by_one(monkeypatch):
    files = [_entry("t1", "blood.pdf", consented=True), _entry("t2", "mri.pdf", consented=True)]
    _, final, _ = _run_stream(monkeypatch, files)
    assert "**Document 1 of 2 — blood.pdf**" in final["response"]
    assert "**Document 2 of 2 — mri.pdf**" in final["response"]


def test_the_first_question_arrives_with_the_analysis(monkeypatch):
    """A printed referral is asked about first, by the fixed question."""
    files = [_entry("t1", "blood.pdf", consented=True), _entry("t2", "mri.pdf", consented=True)]
    _, final, _ = _run_stream(monkeypatch, files)
    state = final["state"]
    assert state["awaiting"] == followup.AWAITING_DOCUMENT_FOLLOW_UP
    assert state["document_topics_asked"] == [followup.TOPIC_REFERRAL]
    assert state["document_followup_qa"][0]["answer"] is None
    assert "A few quick questions" in final["response"]
    assert state["document_followup_qa"][0]["question"] in final["response"]


def test_without_a_referral_the_first_question_is_about_the_findings(monkeypatch):
    _, final, prompts = _run_stream(monkeypatch, [_entry("t1", "blood.pdf", consented=True)])
    assert final["response"].endswith("Your HbA1c is 8.1%, which is high. Any extra thirst?")
    assert "HbA1c: 8.1 %" in prompts[0]


def test_a_file_without_consent_is_not_analysed_and_stays_queued(monkeypatch):
    files = [_entry("t1", "blood.pdf", consented=True), _entry("t2", "waiting.pdf")]
    _, final, _ = _run_stream(monkeypatch, files)
    assert [d["file_name"] for d in final["state"]["analyzed_documents"]] == ["blood.pdf"]
    assert [e["document_token"] for e in chat_route._doc_analysis_cache[_key()]] == ["t2"]


def test_just_store_it_gets_no_questions(monkeypatch):
    _, final, prompts = _run_stream(monkeypatch, [_entry("t1", "blood.pdf", consented=True)],
                                    message="just store it for my records")
    assert final["state"]["awaiting"] is None
    assert "won't book anything" in final["response"]
    assert prompts == []


def test_a_second_upload_starts_a_second_round(monkeypatch):
    earlier = {"file_name": "old.pdf", "followup_round": 1, "document_type": "blood_report"}
    prepared = {"analyzed_documents": [earlier], "document_followup_round": 1,
                "document_topics_asked": ["doc_a", "doc_b", "doc_c"], "checkup_summary_shown": True}
    _, final, _ = _run_stream(monkeypatch, [_entry("t2", "mri.pdf", consented=True)],
                              message="one more", prepared=prepared, analyses=(MRI_ANALYSIS,))
    state = final["state"]
    assert state["document_followup_round"] == 2
    assert state["checkup_summary_shown"] is False
    assert state["document_topics_asked"] == [followup.TOPIC_REFERRAL]
    assert [d["file_name"] for d in state["analyzed_documents"]] == ["old.pdf", "mri.pdf"]
    assert state["analyzed_documents"][-1]["followup_round"] == 2
