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
from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services import nutrition

# A v2 entry also carries real dishes for every region and diet, swaps, habits and a plain
# sentence for the patient; the rules tested here are the same for every part.
MEALS = {
    region: {
        "veg": [{"meal": "breakfast", "dish": "Ragi dosa with coconut chutney"},
                {"meal": "dinner", "dish": "Mushroom masala with roti"}],
        "non_veg": [{"meal": "breakfast", "dish": "Egg bhurji with whole-wheat roti"},
                    {"meal": "lunch", "dish": "Fish curry with rice"}],
    }
    for region in ("north", "south", "east", "west")
}
V2 = {
    "why": "Vitamin D helps your bones and muscles make good use of calcium.",
    "meals": MEALS,
    "swaps": [{"instead_of": "white bread", "try": "whole-wheat roti"}],
    "habits": ["Sit in the morning sun on the balcony with your tea."],
}

VALID = {
    "nutrient_focus": "Vitamin D, with calcium to use it well.",
    "veg_foods": ["Fortified milk", "Curd", "Paneer"],
    "non_veg_foods": ["Salmon", "Egg yolk"],
    "limit": [],
    "note": "",
    **V2,
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



# ---- the heading: what the guidance is for, known before it is opened ----

FOCUS_RESULTS = [
    ("Vitamin D", "Vitamin D (25-OH)", "13.8 ng/mL", "low"),
    ("Total Cholesterol", "Total Cholesterol", "204 mg/dL", "high"),
    ("HDL Cholesterol", "HDL Cholesterol", "38 mg/dL", "low"),
]


def test_the_heading_needs_no_model_and_names_what_the_guidance_is_for(model, patients):
    patient, document = patients(FOCUS_RESULTS)
    heading = nutrition.nutrition_focus_for_document(patient, document)
    assert model["calls"] == []          # named before anything is generated
    guidance = _for_document(patient, document)
    # The same selection names it and writes it: they cannot disagree.
    assert heading == guidance["focus"] == ["Abnormal cholesterol & lipids", "Low Vitamin D"]
    assert {item["term"] for item in guidance["items"]} == {"Blood lipids", "Vitamin D"}


def test_a_document_reported_inaccurate_has_no_heading(model, patients):
    patient, document = patients(FOCUS_RESULTS, flagged_by_doctor=True)
    assert nutrition.nutrition_focus_for_document(patient, document) == []
    assert _for_document(patient, document)["focus"] == []


def test_a_document_with_nothing_out_of_range_has_no_heading(model, patients):
    patient, document = patients([("Vitamin D", "Vitamin D (25-OH)", "41 ng/mL", "normal")])
    assert nutrition.nutrition_focus_for_document(patient, document) == []


def test_an_appointment_that_is_not_the_doctors_has_no_heading(model):
    assert nutrition.nutrition_focus_for_appointment(str(uuid.uuid4()), str(uuid.uuid4())) == []
    assert nutrition.nutrition_focus_for_appointment("not-a-doctor", "not-a-booking") == []


# ---- a visit's guidance: what the patient brought to THIS doctor ----

def _scope_booking(cur, doctor_id, patient_id, when, *, note=None, status=None):
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
           VALUES (%s, %s, %s, TRUE, %s) RETURNING slot_id""",
        (doctor_id, when, when + timedelta(minutes=30), patient_id),
    )
    slot_id = cur.fetchone()[0]
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time,
                                             status, booking_note)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, when, when + timedelta(minutes=30),
         status or ("booked" if when > datetime.now() else "completed"), note),
    )
    return str(cur.fetchone()[0])


def _scope_document(cur, patient_id, name, flag, *, booking=None, filename=None):
    document = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                         blob_summary_path, ingestion_status, original_filename, booking_id)
           VALUES (%s, %s, 'test', 'blood_report', '2026-09-20', 'x', 'complete', %s, %s)""",
        (document, patient_id, filename or f"{name}.pdf", booking),
    )
    cur.execute(
        """INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name,
                                          value_text, abnormal, clinical_date, page_no)
           VALUES (%s, %s, %s, %s, '1', %s, '2026-09-20', 1)""",
        (document, patient_id, name, name, flag),
    )
    return document


@pytest.fixture
def visits():
    """One patient. With ME: an earlier visit (a report tied by document_catalog.booking_id,
    a note saying "tired", a booking chat saying "acidity"), a cancelled one and a later one,
    each with something that must NOT count, and this appointment ("knee pain"). With a
    COLLEAGUE: a visit with a cholesterol report brought through its booking chat. And a
    report uploaded with no appointment at all."""
    _skip_if_no_database()
    now = datetime.now()
    made = {}
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO doctors (name, department, experience_years, is_active) "
                        "VALUES ('Dr. Scope Me', 'Orthopedics', 5, TRUE) RETURNING doctor_id")
            me = made["me"] = str(cur.fetchone()[0])
            cur.execute("INSERT INTO doctors (name, department, experience_years, is_active) "
                        "VALUES ('Dr. Scope Colleague', 'Cardiology', 5, TRUE) RETURNING doctor_id")
            colleague = made["colleague"] = str(cur.fetchone()[0])
            cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id",
                        (f"scope-{uuid.uuid4().hex[:10]}@example.com",))
            patient = made["patient"] = str(cur.fetchone()[0])

            made["earlier_at"] = now - timedelta(days=10)
            earlier = made["earlier"] = _scope_booking(cur, me, patient, made["earlier_at"],
                                                       note="Feeling tired all week")
            made["mine"] = _scope_document(cur, patient, "Vitamin D", "low", booking=earlier)
            session = str(uuid.uuid4())
            t0 = made["earlier_at"] - timedelta(days=1)
            cur.execute("INSERT INTO chat_messages (patient_id, chat_session_id, role, text, created_at) "
                        "VALUES (%s, %s, 'patient', 'I get acidity after meals', %s)", (patient, session, t0))
            cur.execute(
                """INSERT INTO booking_context_snapshots (booking_id, patient_id, chat_session_id,
                                                          transcript_from_at, transcript_to_at, transcript_message_count)
                   VALUES (%s, %s, %s, %s, %s, 1)""",
                (earlier, patient, session, t0, t0))

            cancelled = _scope_booking(cur, me, patient, now - timedelta(days=3), note="constipation", status="cancelled")
            _scope_document(cur, patient, "Ferritin", "low", booking=cancelled)
            _scope_booking(cur, me, patient, now + timedelta(days=9), note="hair fall")

            theirs = _scope_booking(cur, colleague, patient, now - timedelta(days=5), note="bloating")
            echo = _scope_document(cur, patient, "Total Cholesterol", "high")
            cur.execute("INSERT INTO booking_context_snapshots (booking_id, patient_id, document_ids) "
                        "VALUES (%s, %s, %s::jsonb)", (theirs, patient, f'["{echo}"]'))
            _scope_document(cur, patient, "HbA1c", "high")

            made["booking"] = _scope_booking(cur, me, patient, now + timedelta(days=1), note="knee pain since Monday")
        conn.commit()
    try:
        yield made
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chat_messages WHERE patient_id = %s", (patient,))
                cur.execute("DELETE FROM document_findings WHERE patient_id = %s", (patient,))
                cur.execute("DELETE FROM document_reviews WHERE patient_id = %s", (patient,))
                cur.execute("DELETE FROM document_catalog WHERE user_id = %s", (patient,))
                cur.execute("DELETE FROM consult_audit_log WHERE metadata->>'patient_id' = %s", (patient,))
                cur.execute("DELETE FROM doctors WHERE doctor_id = ANY(%s::uuid[])", ([me, colleague],))
                cur.execute("DELETE FROM users WHERE user_id = %s", (patient,))
            conn.commit()


def _inputs(visits):
    return nutrition._appointment_inputs(visits["me"], visits["booking"])


def test_a_visits_guidance_reads_only_the_reports_brought_to_this_doctor(model, visits):
    _patient, _booking, _excluded, results, _sources, earlier = _inputs(visits)
    # Mine from the earlier visit; not the colleague's cholesterol, the loose HbA1c, or the
    # report from the visit that was cancelled.
    assert [r["canonical_name"] for r in results] == ["Vitamin D"]
    assert earlier == 1


def test_symptoms_come_from_this_and_my_earlier_bookings_with_where_they_were_said(model, visits):
    *_, sources, _earlier = _inputs(visits)
    when = visits["earlier_at"]
    assert sources == {
        "joint or back pain": "booking note",
        "fatigue": f"booking note, {when.day} {when:%b}",
        "acidity or heartburn": f"booking chat, {when.day} {when:%b}",
    }


def test_the_visits_heading_is_what_opens(model, visits):
    heading = nutrition.nutrition_focus_for_appointment(visits["me"], visits["booking"])
    guidance = asyncio.run(nutrition.guidance_for_appointment(visits["me"], visits["booking"]))
    assert heading == guidance["focus"]
    assert "Low Vitamin D" in heading and not any("cholesterol" in label for label in heading)
    assert guidance["earlier_visits"] == 1


def test_a_report_flagged_on_another_copy_is_left_out(model, visits):
    """The page labels a report by every copy (document_reviews.merged_review_states): one
    flagged anywhere is flagged, so its results must not shape the guidance either."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            copy = _scope_document(cur, visits["patient"], "Vitamin D", "low", filename="Vitamin D.pdf")
            cur.execute(
                """INSERT INTO document_reviews (document_id, patient_id, doctor_id, action, reason)
                   VALUES (%s, %s, %s, 'flagged_inaccurate', 'Values misread')""",
                (copy, visits["patient"], visits["colleague"]),
            )
        conn.commit()
    _patient, _booking, excluded, results, _sources, _earlier = _inputs(visits)
    assert visits["mine"] in excluded and results == []
