"""The routes behind the patient's records, the doctor's handout, and "Insert from plan".

Called directly, as in test_document_upload_e2e.py; storage and models are replaced.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date

import pytest
from fastapi import HTTPException

from app.api.routes import chat as chat_route
from app.api.routes import doctor as doctor_route
from app.db.connection import connect_db
from app.services import nutrition_plan as np_


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            np_.ensure_handout_schema(conn)
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


@pytest.fixture
def patient():
    _skip_if_no_database()
    tag = uuid.uuid4().hex[:8]
    ids = {"patient": f"route-p-{tag}", "other": f"route-o-{tag}", "doctor": str(uuid.uuid4()),
           "done": f"route-done-{tag}", "proc": f"route-proc-{tag}"}
    with connect_db() as conn:
        with conn.cursor() as cur:
            # consult_audit_log.doctor_id is a foreign key: the audited doctor must exist.
            cur.execute("INSERT INTO doctors (doctor_id, name, department, experience_years, is_active) "
                        "VALUES (%s, 'Dr. Route', 'Orthopedics', 5, TRUE)", (ids["doctor"],))
            for key, status in (("done", "complete"), ("proc", "processing")):
                cur.execute(
                    """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                                     blob_summary_path, original_filename, ingestion_status)
                       VALUES (%s, %s, %s, 'blood_report', %s, 'x', %s, %s)""",
                    (ids[key], ids["patient"], str(uuid.uuid4()), date(2026, 9, 20), f"{key}.pdf", status))
        conn.commit()
    try:
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_catalog WHERE document_id = ANY(%s)", ([ids["done"], ids["proc"]],))
                cur.execute("DELETE FROM nutrition_handouts WHERE patient_id = %s", (ids["patient"],))
                cur.execute("DELETE FROM consult_audit_log WHERE metadata->>'patient_id' = %s", (ids["patient"],))
                cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (ids["doctor"],))
            conn.commit()


def _user(patient_id):
    return {"patient_id": patient_id, "name": "Route Patient"}


# ---- the patient's records ----

def test_records_list_the_patients_own_documents_and_handouts(patient):
    np_.save_handout(patient["doctor"], patient["patient"], None, None,
                     {"diet": "veg", "themes": [{"title": "Vitamins & blood", "blurb": "", "foods": ["paneer"],
                                                 "go_easy": [], "tips": []}], "sample_day": [], "note": "n"})
    data = chat_route.patient_records(user=_user(patient["patient"]))
    statuses = {d["original_filename"]: d["status"] for d in data["documents"]}
    assert statuses == {"done.pdf": "not_reviewed", "proc.pdf": "processing"}
    [handout] = data["handouts"]
    assert handout["content"]["themes"][0]["foods"] == ["paneer"]
    assert chat_route.patient_records(user=_user(patient["other"])) == {"documents": [], "handouts": []}


def test_a_patient_downloads_their_own_file_as_an_attachment(patient, monkeypatch):
    async def fake_read(path):
        assert path.startswith(f"vault/{patient['patient']}/")
        return b"%PDF-1.4 own file"

    monkeypatch.setattr("app.services.document_storage.read_document_bytes", fake_read)
    response = asyncio.run(chat_route.patient_document_file(patient["done"], user=_user(patient["patient"])))
    assert response.body == b"%PDF-1.4 own file"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.media_type == "application/pdf"


def test_another_patients_file_is_not_found(patient):
    with pytest.raises(HTTPException) as refused:
        asyncio.run(chat_route.patient_document_file(patient["done"], user=_user(patient["other"])))
    assert refused.value.status_code == 404


def test_a_file_still_processing_is_refused(patient):
    with pytest.raises(HTTPException) as refused:
        asyncio.run(chat_route.patient_document_file(patient["proc"], user=_user(patient["patient"])))
    assert refused.value.status_code == 409


# ---- the doctor's handout reaches the patient's account ----

GUIDANCE = {"items": [{
    "kind": "finding", "term": "Vitamin D", "direction": "low",
    "veg_foods": ["paneer", "oats"], "non_veg_foods": ["salmon"], "limit": ["fried foods"], "note": "",
    "because": [{"canonical_name": "Vitamin D", "printed_name": "Vitamin D", "value_text": "13.8 ng/mL",
                 "flag": "low", "clinical_date": "2026-09-20", "page_no": 2, "document_id": "d",
                 "document_type": "blood_report"}]}], "cautions": [], "unavailable": []}


def test_a_handout_made_from_a_document_is_saved_to_the_patients_account(patient, monkeypatch):
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda d, p: True)
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", lambda d, p, doc: None)

    async def fake_guidance(doctor_id, patient_id, document_id):
        return dict(GUIDANCE)

    monkeypatch.setattr(doctor_route, "guidance_for_document", fake_guidance)
    request = doctor_route.NutritionHandoutRequest(diet="non_veg", document_id=patient["done"])
    result = asyncio.run(doctor_route.doctor_nutrition_handout_route(
        patient["patient"], request, doctor={"doctor_id": patient["doctor"], "department": "Orthopedics"}))
    assert result["saved_to_patient_account"] is True
    assert result["handout"]["themes"][0]["foods"] == ["Salmon"]
    [handout] = chat_route.patient_records(user=_user(patient["patient"]))["handouts"]
    assert handout["id"] == result["id"] and handout["content"] == result["handout"]
    assert "13.8" not in str(handout)


def _share(patient, monkeypatch, diet="non_veg"):
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda d, p: True)
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", lambda d, p, doc: None)

    async def fake_guidance(doctor_id, patient_id, document_id):
        return dict(GUIDANCE)

    monkeypatch.setattr(doctor_route, "guidance_for_document", fake_guidance)
    return asyncio.run(doctor_route.doctor_nutrition_handout_route(
        patient["patient"], doctor_route.NutritionHandoutRequest(diet=diet, document_id=patient["done"]),
        doctor={"doctor_id": patient["doctor"], "department": "Orthopedics"}))


def test_sharing_again_tells_the_doctor_it_is_already_there(patient, monkeypatch):
    first = _share(patient, monkeypatch)
    again = _share(patient, monkeypatch)
    assert first["already_shared"] is False and again["already_shared"] is True
    assert again["id"] == first["id"] and again["shared_at"] == first["shared_at"]
    # The patient has it once.
    assert len(chat_route.patient_records(user=_user(patient["patient"]))["handouts"]) == 1
    # And the doctor's page is told what is in the account now.
    [shared] = again["shared_handouts"]
    assert shared["by_me"] is True and shared["diet"] == "non_veg" and shared["doctor_name"] == "Dr. Route"


def test_the_nutritionist_page_lists_what_was_already_shared(patient, monkeypatch):
    doctor = {"doctor_id": patient["doctor"], "department": "Orthopedics"}
    before = doctor_route._with_nutrition_plan(dict(GUIDANCE), doctor, patient["patient"])
    assert before["shared_handouts"] == []
    _share(patient, monkeypatch, diet="veg")
    after = doctor_route._with_nutrition_plan(dict(GUIDANCE), doctor, patient["patient"])
    assert [h["diet"] for h in after["shared_handouts"]] == ["veg"]


def test_a_handout_needs_a_visit_or_a_document(patient, monkeypatch):
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda d, p: True)
    with pytest.raises(HTTPException) as refused:
        asyncio.run(doctor_route.doctor_nutrition_handout_route(
            patient["patient"], doctor_route.NutritionHandoutRequest(diet="veg"),
            doctor={"doctor_id": patient["doctor"], "department": None}))
    assert refused.value.status_code == 422


def test_a_doctor_not_treating_the_patient_cannot_make_one(patient, monkeypatch):
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda d, p: False)
    with pytest.raises(HTTPException) as refused:
        asyncio.run(doctor_route.doctor_nutrition_handout_route(
            patient["patient"], doctor_route.NutritionHandoutRequest(diet="veg", document_id=patient["done"]),
            doctor={"doctor_id": patient["doctor"], "department": None}))
    assert refused.value.status_code == 404
    assert chat_route.patient_records(user=_user(patient["patient"]))["handouts"] == []


# ---- "Insert from plan" carries tests and reports ----

def test_insert_from_plan_returns_medicines_and_tests(monkeypatch):
    from app.api.routes import consult as consult_route

    monkeypatch.setattr(consult_route, "get_soap_note", lambda c, d: {
        "status": "signed",
        "plan": "- Tab Gabapentin 400 mg BD x 15 days\n- Serum Vitamin B12 and Vitamin D levels\n- MRI lumbar spine",
    })
    result = consult_route.get_plan_medications_route("c1", doctor={"doctor_id": "d1"})
    assert result["medications"] == ["Tab Gabapentin 400 mg BD x 15 days"]
    assert result["tests"] == ["Serum Vitamin B12 and Vitamin D levels", "MRI lumbar spine"]
    assert result["validated"] is False
    # Unchanged for older pages: every list line, as before.
    assert result["lines"] == ["Tab Gabapentin 400 mg BD x 15 days", "Serum Vitamin B12 and Vitamin D levels",
                               "MRI lumbar spine"]


def test_insert_from_plan_still_refuses_an_unsigned_note(monkeypatch):
    from app.api.routes import consult as consult_route

    monkeypatch.setattr(consult_route, "get_soap_note", lambda c, d: {"status": "draft", "plan": "- MRI"})
    with pytest.raises(HTTPException) as refused:
        consult_route.get_plan_medications_route("c1", doctor={"doctor_id": "d1"})
    assert refused.value.status_code == 409



# ---- food guidance v2: the heading reaches the page; the handout follows the region ----

def test_the_visit_brief_carries_what_its_food_guidance_is_for(monkeypatch):
    monkeypatch.setattr(doctor_route, "get_visit_brief", lambda d, b, v: {"booking_id": b, "patient_id": "p"})
    monkeypatch.setattr(doctor_route, "nutrition_focus_for_appointment",
                        lambda d, b: ["Low Vitamin D", "Joint or back pain"])
    brief = doctor_route.doctor_visit_brief_route("b1", doctor={"doctor_id": "d1", "department": None})
    assert brief["nutrition_focus"] == ["Low Vitamin D", "Joint or back pain"]


def test_the_document_viewer_carries_what_its_food_guidance_is_for(monkeypatch):
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "record_document_content_read", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "findings_for_document", lambda *a, **k: [])
    monkeypatch.setattr(doctor_route, "review_states", lambda ids, *a, **k: {i: None for i in ids})
    monkeypatch.setattr(doctor_route, "get_summary", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "get_document_pages", lambda *a, **k: [])
    asked = []
    monkeypatch.setattr(doctor_route, "nutrition_focus_for_document",
                        lambda p, d: asked.append((p, d)) or ["Low Vitamin B12", "High ESR"])
    payload = doctor_route.doctor_patient_document_clinical_route("p1", "doc1", doctor={"doctor_id": "d1"})
    assert payload["nutrition_focus"] == ["Low Vitamin B12", "High ESR"]
    assert asked == [("p1", "doc1")]


def test_a_failing_heading_never_costs_the_doctor_the_brief_or_the_document(monkeypatch):
    def broken(*args):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(doctor_route, "get_visit_brief", lambda d, b, v: {"booking_id": b})
    monkeypatch.setattr(doctor_route, "nutrition_focus_for_appointment", broken)
    assert doctor_route.doctor_visit_brief_route("b1", doctor={"doctor_id": "d1"})["nutrition_focus"] == []
    monkeypatch.setattr(doctor_route, "nutrition_focus_for_document", broken)
    assert doctor_route._document_nutrition_focus("p", "doc") == []


def test_a_handout_is_shared_in_the_region_the_doctor_chose(patient, monkeypatch):
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda d, p: True)
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", lambda d, p, doc: None)
    meals = {region: {"veg": [{"meal": "breakfast", "dish": f"{region} idli with sambar"},
                              {"meal": "lunch", "dish": f"{region} dal with rice"}],
                      "non_veg": [{"meal": "breakfast", "dish": f"{region} egg dosa"},
                                  {"meal": "lunch", "dish": f"{region} fish curry with rice"}]}
             for region in ("north", "south", "east", "west")}

    async def fake_guidance(doctor_id, patient_id, document_id):
        item = dict(GUIDANCE["items"][0])
        item.update({"why": "Vitamin D helps your bones use calcium.", "meals": meals,
                     "swaps": [{"instead_of": "white bread", "try": "whole-wheat roti"}], "habits": []})
        return {**GUIDANCE, "items": [item]}

    monkeypatch.setattr(doctor_route, "guidance_for_document", fake_guidance)
    result = asyncio.run(doctor_route.doctor_nutrition_handout_route(
        patient["patient"], doctor_route.NutritionHandoutRequest(diet="veg", region="south", document_id=patient["done"]),
        doctor={"doctor_id": patient["doctor"], "department": "Orthopedics"}))
    handout = result["handout"]
    assert handout["region"] == "south" and handout["region_label"] == "South Indian"
    assert [meal["dish"] for meal in handout["sample_day"]] == ["south idli with sambar", "south dal with rice"]
    assert handout["themes"][0]["swaps"] == [{"instead_of": "white bread", "try": "whole-wheat roti"}]
    # The same food in another region is another handout, not "already shared".
    again = asyncio.run(doctor_route.doctor_nutrition_handout_route(
        patient["patient"], doctor_route.NutritionHandoutRequest(diet="veg", region="east", document_id=patient["done"]),
        doctor={"doctor_id": patient["doctor"], "department": "Orthopedics"}))
    assert again["already_shared"] is False and again["handout"]["region"] == "east"
