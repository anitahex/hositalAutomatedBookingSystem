"""What the at-a-glance card SELECTS, against a real database.

Two defects were found in live data, and each is pinned here by reproducing it:

  1. A prescription photo's summary opens with the MRI result written on it. The card took
     the first two summary sentences of any prescription document as "medications", so
     "MRI shows ... Butterfly Vertebra" appeared as a drug. Medications now come from the
     structured medication finding the extraction already produces.
  2. Abnormal results were cut to six ALPHABETICALLY: a patient with eight lost Vitamin D
     (deficient) and hs-CRP while Total Cholesterol stayed.

Plus the cache: a card built by an older version of the selection rules must be rebuilt,
or a fix like the two above would reach no patient whose record has not changed since.

Pure grounding rules are in test_patient_overview.py; restriction and caching basics in
test_patient_overview_integration.py.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date, datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services import patient_overview as po
from app.services.patient_overview import LABEL_REPORTED_UNVERIFIED, gather_facts, get_overview


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _doctor(cur):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES ('Dr. Selection', 'Orthopedics', 1, TRUE) RETURNING doctor_id"""
    )
    return str(cur.fetchone()[0])


def _patient(cur):
    email = f"sel-{uuid.uuid4().hex[:10]}@example.com"
    cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id", (email,))
    user_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
           VALUES (%s, 'Selection Patient', 30, '9999999999', 'Test', %s, 'O+')""",
        (user_id, email),
    )
    return user_id


def _booking(cur, doctor_id, patient_id):
    start = datetime.now() - timedelta(days=1)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
           VALUES (%s, %s, %s, TRUE, %s) RETURNING slot_id""",
        (doctor_id, start, start + timedelta(minutes=30), patient_id),
    )
    slot_id = cur.fetchone()[0]
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, 'completed')""",
        (slot_id, doctor_id, patient_id, start, start + timedelta(minutes=30)),
    )


def _document(cur, patient_id, filename, document_type, clinical_date):
    document_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO document_catalog (document_id, user_id, session_id, original_filename,
                                         blob_summary_path, document_type, clinical_date,
                                         ingestion_status)
           VALUES (%s, %s, %s, %s, 'summaries/x.json', %s, %s, 'complete')""",
        (document_id, patient_id, str(uuid.uuid4()), filename, document_type, clinical_date),
    )
    return document_id


def _finding(cur, document_id, patient_id, name, value_text, *, value_num=None, unit=None,
             abnormal="unknown", clinical_date=None, canonical=None):
    cur.execute(
        """INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name,
                                          value_text, value_num, unit, abnormal, clinical_date)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (document_id, patient_id, name, canonical or name, value_text, value_num, unit,
         abnormal, clinical_date),
    )


@pytest.fixture
def world():
    _skip_if_no_database()
    ids = {}
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                ids["doctor"] = _doctor(cur)
                ids["patient"] = patient = _patient(cur)
                _booking(cur, ids["doctor"], patient)

                # The live defect, reproduced: a photographed prescription whose summary
                # leads with the MRI result, and whose extraction has a Medication finding.
                rx = _document(cur, patient, "prescription-photo.png", "prescription", date(2026, 9, 20))
                ids["rx"] = rx
                cur.execute(
                    """INSERT INTO document_summaries (document_id, sentences, verification, source_kind)
                       VALUES (%s, %s::jsonb, 'partial', 'vision_transcription')""",
                    (rx, json.dumps([
                        {"text": "MRI shows L4 Butterfly Vertebra with degenerative changes.",
                         "quote": "MRI L4 Butterfly Vertebra", "page_no": 1},
                        {"text": "Advised physiotherapy.", "quote": "Physiotherapy", "page_no": 1},
                    ])),
                )
                _finding(cur, rx, patient, "Medication", "Tab Gabantin NT 400/100 BD x 15 days")
                _finding(cur, rx, patient, "MRI", "L4 Butterfly Vertebra")

                # A text-layer lab report: eight abnormal results, plus one measurement whose
                # LATEST reading is normal and must therefore not be shown as abnormal.
                labs = _document(cur, patient, "lab.pdf", "blood_report", date(2026, 9, 20))
                older = _document(cur, patient, "older-lab.pdf", "blood_report", date(2026, 8, 1))
                abnormal = [
                    ("Cortisol (morning)", 24.6, "µg/dL", "high"),
                    ("HDL Cholesterol", 38.0, "mg/dL", "low"),
                    ("LDL Cholesterol", 130.8, "mg/dL", "high"),
                    ("Total Cholesterol", 204.0, "mg/dL", "high"),
                    ("Triglycerides", 176.0, "mg/dL", "high"),
                    ("Vitamin B12", 178.0, "pg/mL", "low"),
                    ("Vitamin D", 13.8, "ng/mL", "low"),
                    ("hs-CRP", 3.6, "mg/L", "high"),
                ]
                for name, value, unit, flag in abnormal:
                    _finding(cur, labs, patient, name, str(value), value_num=value, unit=unit,
                             abnormal=flag, clinical_date=date(2026, 9, 20))
                _finding(cur, older, patient, "Haemoglobin", "9.1", value_num=9.1, unit="g/dL",
                         abnormal="low", clinical_date=date(2026, 8, 1))
                _finding(cur, labs, patient, "Haemoglobin", "13.4", value_num=13.4, unit="g/dL",
                         abnormal="normal", clinical_date=date(2026, 9, 20))
                # As the OLD canonicaliser stored it: the ratio filed under HDL Cholesterol, with
                # HDL's range, on the same date as the real (low) HDL result.
                cur.execute(
                    """INSERT INTO document_findings (document_id, patient_id, printed_name,
                           canonical_name, value_text, value_num, unit, ref_low, ref_high,
                           abnormal, clinical_date)
                       VALUES (%s, %s, 'Total Cholesterol / HDL Ratio', 'HDL Cholesterol',
                               '5.37', 5.37, NULL, 40, 100, 'unknown', %s)""",
                    (labs, patient, date(2026, 9, 20)),
                )
            conn.commit()
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                patient = ids.get("patient")
                if patient:
                    cur.execute("DELETE FROM patient_overviews WHERE patient_id = %s", (patient,))
                    cur.execute("DELETE FROM document_summaries WHERE document_id IN "
                                "(SELECT document_id FROM document_catalog WHERE user_id = %s)", (patient,))
                    cur.execute("DELETE FROM document_findings WHERE patient_id = %s", (patient,))
                    cur.execute("DELETE FROM document_catalog WHERE user_id = %s", (patient,))
                if ids.get("doctor"):
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (ids["doctor"],))
                if patient:
                    cur.execute("DELETE FROM users WHERE user_id = %s", (patient,))
            conn.commit()


def _facts(world, kind):
    return [f for f in gather_facts(world["doctor"], world["patient"], "Orthopedics") if f["kind"] == kind]


# ---- medications ----

def test_a_summary_sentence_is_never_listed_as_a_medication(world):
    """The live defect: the MRI line from a prescription photo's summary, shown as a drug."""
    medications = _facts(world, "medication")
    assert "Butterfly" not in str(medications)
    assert "physiotherapy" not in str(medications).lower()


def test_the_structured_medication_finding_is_listed_and_labelled(world):
    medications = _facts(world, "medication")
    assert [m["text"] for m in medications] == ["Tab Gabantin NT 400/100 BD x 15 days"]
    # Rule 4: another clinic's prescription is shown, never hidden, never passed off as ours.
    assert medications[0]["label"] == LABEL_REPORTED_UNVERIFIED
    assert medications[0]["source_id"] == world["rx"]


def test_a_medication_read_off_a_photo_says_so(world):
    """Two AI passes over the same photo have read one drug two ways. The doctor is told."""
    assert _facts(world, "medication")[0]["scanned"] is True


# ---- abnormal results ----

def test_no_abnormal_result_is_dropped_by_alphabet(world):
    """The live defect: eight abnormal results, and the card kept the first six by name."""
    names = " ".join(f["text"] for f in _facts(world, "abnormal"))
    for expected in ("Vitamin D", "hs-CRP", "Cortisol", "Vitamin B12"):
        assert expected in names


def test_a_measurement_whose_latest_reading_is_normal_is_not_abnormal(world):
    """Haemoglobin was low in August and normal in September. Showing 'low' would present an
    old result as the patient's current state."""
    assert "Haemoglobin" not in " ".join(f["text"] for f in _facts(world, "abnormal"))


def test_abnormal_results_are_bounded(world):
    assert len(_facts(world, "abnormal")) <= po.MAX_ABNORMAL_FACTS


# ---- the cache ----

def test_a_card_built_by_an_older_version_is_rebuilt(world, monkeypatch):
    """prompt_version was stored with every card and never checked. A correction to what the
    card selects would otherwise reach only patients whose record changed afterwards."""
    async def no_model(**kwargs):
        raise RuntimeError("no model in tests")

    import app.inference.azure_client as azure
    monkeypatch.setattr(azure, "gpt4o_overview_phrasing", no_model)

    first = asyncio.run(get_overview(world["doctor"], world["patient"], "Orthopedics"))
    assert first["cached"] is False
    assert asyncio.run(get_overview(world["doctor"], world["patient"], "Orthopedics"))["cached"] is True

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE patient_overviews SET prompt_version = 'overview-v1' WHERE patient_id = %s",
                        (world["patient"],))
        conn.commit()

    rebuilt = asyncio.run(get_overview(world["doctor"], world["patient"], "Orthopedics"))
    assert rebuilt["cached"] is False, "a card from an older build was served from cache"


# ---- same-date readings, and the ratio that was filed as HDL ----

def test_an_unclassifiable_reading_never_hides_a_classified_one_on_the_same_date(world):
    """Found on real data: the ratio, filed as HDL, shared a date with the real HDL result,
    and picking one reading per analyte per date chose between them at random. Whenever the
    ratio won, a genuinely low HDL vanished from the card."""
    for _ in range(3):  # not a coin toss that happened to land right once
        texts = " ".join(f["text"] for f in _facts(world, "abnormal"))
        assert "HDL Cholesterol low at 38" in texts


def test_the_repair_moves_the_ratio_off_hdl_and_is_idempotent(world):
    from app.services.document_findings import recanonicalise_stored_findings

    first = recanonicalise_stored_findings(patient_id=world["patient"])
    assert first["changed"] >= 1

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT printed_name, canonical_name, ref_low, ref_high, abnormal
                   FROM document_findings WHERE patient_id = %s AND printed_name LIKE '%%HDL%%'
                   ORDER BY printed_name""",
                (world["patient"],),
            )
            rows = {row[0]: row[1:] for row in cur.fetchall()}
        conn.commit()

    ratio = rows["Total Cholesterol / HDL Ratio"]
    assert ratio[0] == "Total Cholesterol HDL Ratio"
    assert ratio[1] is None and ratio[2] is None, "the ratio kept HDL's reference range"
    assert rows["HDL Cholesterol"][0] == "HDL Cholesterol"
    assert rows["HDL Cholesterol"][3] == "low"

    assert recanonicalise_stored_findings(patient_id=world["patient"])["changed"] == 0


def test_the_repair_leaves_other_patients_alone(world):
    """Scoped runs are how the tests stay off real patients' rows; prove the scope holds."""
    from app.services.document_findings import recanonicalise_stored_findings

    result = recanonicalise_stored_findings(patient_id=world["patient"], dry_run=True)
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM document_findings WHERE patient_id = %s", (world["patient"],))
            own = cur.fetchone()[0]
        conn.commit()
    assert result["checked"] == own
