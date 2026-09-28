"""The AI nutritionist against a real database, with the model replaced by a stub.

What only the database can prove: two patients with the same results get byte-identical
guidance, the second without a model call; an entry that fails the checks is retried once
with the reason and never stored if it fails again; a document someone reported inaccurate
contributes nothing; and every view is audited.

The prompt version is set to a throwaway value for each test, so nothing written here can
ever be served to a real patient's doctor.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

from app.db.connection import connect_db
from app.services import nutrition

VALID = {
    "nutrient_focus": "Vitamin D, with calcium to use it well.",
    "veg_foods": ["Fortified milk", "Curd", "Paneer"],
    "non_veg_foods": ["Salmon", "Egg yolk"],
    "limit": [],
    "note": "",
}


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM nutrition_guidance LIMIT 0")
    except Exception as exc:
        pytest.skip(f"Requires Postgres with migration 0028 applied: {exc}")


@pytest.fixture
def model(monkeypatch):
    """The stub model: records every call and answers from a queue (default: VALID)."""
    _skip_if_no_database()
    version = f"test-{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(nutrition, "NUTRITION_PROMPT_VERSION", version)
    # The back-off is process state; one test's failures must not leak into the next.
    monkeypatch.setattr(nutrition, "_recent_failures", {})
    state = {"calls": [], "answers": []}

    async def fake(*, kind, term, direction, retry_reason=None):
        state["calls"].append((kind, term, direction, retry_reason))
        answer = state["answers"].pop(0) if state["answers"] else VALID
        return {"entry": answer, "model": "stub"}

    import app.inference.azure_client as azure_client
    monkeypatch.setattr(azure_client, "gpt4o_nutrition_entry", fake)
    try:
        yield state
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM nutrition_guidance WHERE prompt_version = %s", (version,))
            conn.commit()


@pytest.fixture
def patients():
    _skip_if_no_database()
    made = {"patients": [], "documents": [], "doctor": str(uuid.uuid4())}
    # A real doctor row: the audit log's doctor_id is a foreign key.
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO doctors (doctor_id, name, department, experience_years, is_active) "
                        "VALUES (%s, 'Dr. Test Nutrition', 'Cardiology', 5, TRUE)", (made["doctor"],))
        conn.commit()

    def make(findings, *, flagged_by_doctor=False):
        patient = f"nutrition-patient-{uuid.uuid4().hex[:8]}"
        document = f"nutrition-doc-{uuid.uuid4().hex[:8]}"
        made["patients"].append(patient)
        made["documents"].append(document)
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO document_catalog (document_id, user_id, session_id, document_type,
                                                     clinical_date, blob_summary_path, ingestion_status,
                                                     original_filename)
                       VALUES (%s, %s, 'test', 'blood_report', '2026-09-20', 'x', 'complete', 'lab.pdf')""",
                    (document, patient),
                )
                for name, printed, value_text, flag in findings:
                    cur.execute(
                        """INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name,
                                                          value_text, abnormal, clinical_date, page_no)
                           VALUES (%s, %s, %s, %s, %s, %s, '2026-09-20', 2)""",
                        (document, patient, printed, name, value_text, flag),
                    )
                if flagged_by_doctor:
                    cur.execute(
                        """INSERT INTO document_reviews (document_id, patient_id, doctor_id, action, reason)
                           VALUES (%s, %s, %s, 'flagged_inaccurate', 'Values misread')""",
                        (document, patient, made["doctor"]),
                    )
            conn.commit()
        return patient, document

    make.doctor = made["doctor"]
    try:
        yield make
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_findings WHERE patient_id = ANY(%s)", (made["patients"],))
                cur.execute("DELETE FROM document_reviews WHERE document_id = ANY(%s)", (made["documents"],))
                cur.execute("DELETE FROM document_catalog WHERE document_id = ANY(%s)", (made["documents"],))
                cur.execute("DELETE FROM consult_audit_log WHERE action_type = 'nutrition_guidance_viewed' "
                            "AND metadata->>'patient_id' = ANY(%s)", (made["patients"],))
                cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (made["doctor"],))
            conn.commit()


LOW_VITAMIN_D = [("Vitamin D", "Vitamin D, 25-Hydroxy (Total)", "13.8 ng/mL", "low")]


def _for_document(patient, document, doctor=None):
    return asyncio.run(nutrition.guidance_for_document(doctor or str(uuid.uuid4()), patient, document))


def test_two_patients_with_the_same_result_get_identical_guidance_from_one_model_call(model, patients):
    first = _for_document(*patients(LOW_VITAMIN_D))
    second = _for_document(*patients([("Vitamin D", "Vitamin D (25-OH)", "11.2 ng/mL", "low")]))

    assert len(model["calls"]) == 1, "the second patient should have been served from the store"
    strip = lambda item: {k: v for k, v in item.items() if k != "because"}  # noqa: E731
    assert [strip(i) for i in first["items"]] == [strip(i) for i in second["items"]]
    # What IS patient-specific comes from each patient's own record.
    assert first["items"][0]["because"][0]["value_text"] == "13.8 ng/mL"
    assert second["items"][0]["because"][0]["value_text"] == "11.2 ng/mL"


def test_a_rejected_entry_is_retried_once_with_the_reason(model, patients):
    model["answers"] = [{**VALID, "veg_foods": ["Boiled eggs"]}, VALID]
    result = _for_document(*patients(LOW_VITAMIN_D))
    assert len(model["calls"]) == 2
    assert "vegetarian" in model["calls"][1][3]
    assert result["items"][0]["veg_foods"] == VALID["veg_foods"]


def test_an_entry_that_fails_twice_is_never_stored_or_shown(model, patients):
    model["answers"] = [{**VALID, "note": "Take 2 capsules."}, {**VALID, "veg_foods": ["Chicken"]}]
    result = _for_document(*patients(LOW_VITAMIN_D))
    assert result["items"] == [] and result["unavailable"] == ["Vitamin D"]
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM nutrition_guidance WHERE prompt_version = %s",
                        (nutrition.NUTRITION_PROMPT_VERSION,))
            assert cur.fetchone()[0] == 0
        conn.commit()


def test_a_document_reported_inaccurate_contributes_nothing(model, patients):
    patient, document = patients(LOW_VITAMIN_D, flagged_by_doctor=True)
    result = _for_document(patient, document)
    assert result["reported_inaccurate"] is True and result["items"] == []
    assert model["calls"] == []


def test_lipid_results_become_one_item_with_every_result_as_evidence(model, patients):
    result = _for_document(*patients([
        ("Total Cholesterol", "Total Cholesterol", "204 mg/dL", "high"),
        ("Triglycerides", "Triglycerides", "176 mg/dL", "high"),
        ("HDL Cholesterol", "HDL Cholesterol", "38 mg/dL", "low"),
    ]))
    assert [item["term"] for item in result["items"]] == ["Blood lipids"]
    assert len(result["items"][0]["because"]) == 3
    assert len(model["calls"]) == 1


def test_a_kidney_result_changes_what_another_results_guidance_offers(model, patients):
    model["answers"] = [
        {**VALID, "veg_foods": ["Banana", "Curd"]},   # whichever term is generated first
        {**VALID, "veg_foods": ["Banana", "Curd"]},
    ]
    result = _for_document(*patients(LOW_VITAMIN_D + [("Creatinine", "Serum Creatinine", "2.1 mg/dL", "high")]))
    assert nutrition.CAUTION_KIDNEY in result["cautions"]
    assert all("Banana" not in item["veg_foods"] for item in result["items"])


def test_every_view_is_audited(model, patients):
    patient, document = patients(LOW_VITAMIN_D)
    doctor = patients.doctor
    _for_document(patient, document, doctor)
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT doctor_id::text, metadata->>'document_id', (metadata->>'terms')::int
                   FROM consult_audit_log WHERE action_type = 'nutrition_guidance_viewed'
                     AND metadata->>'patient_id' = %s""",
                (patient,),
            )
            assert cur.fetchall() == [(doctor, document, 1)]
        conn.commit()


def test_an_appointment_that_is_not_the_doctors_is_refused(model):
    with pytest.raises(PermissionError):
        asyncio.run(nutrition.guidance_for_appointment(str(uuid.uuid4()), str(uuid.uuid4())))
    with pytest.raises(PermissionError):
        asyncio.run(nutrition.guidance_for_appointment("not-a-uuid", "also-not"))


def test_a_term_that_failed_twice_is_not_retried_on_every_request(model, patients, monkeypatch):
    monkeypatch.setattr(nutrition, "_recent_failures", {})
    model["answers"] = [{**VALID, "veg_foods": ["Chicken"]}, {**VALID, "veg_foods": ["Fish"]}]
    patient, document = patients(LOW_VITAMIN_D)
    _for_document(patient, document)
    _for_document(patient, document)
    assert len(model["calls"]) == 2, "the second request should not have asked the model again"
