"""At a glance, by document: each report's findings together, who verified it, what changed.

What was wrong: abnormal results were listed one line at a time with no sign of which report
each came from or whether any doctor had checked it, so a result a colleague had verified
read exactly like one nobody had looked at, and a new report said nothing about what changed.
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.services import overview_documents as od
from app.services.overview_documents import (
    CHANGE_BETTER, CHANGE_FIRST, CHANGE_FLIPPED, CHANGE_NEW, CHANGE_RESOLVED, CHANGE_SAME,
    CHANGE_WORSE, describe_change,
)


def _reading(value, flag, clinical_date="2026-09-20", unit="ng/mL"):
    return {"value": value, "unit": unit, "flag": flag, "clinical_date": clinical_date}


# ---- what changed, decided by code ----

@pytest.mark.parametrize("latest, previous, kind", [
    (_reading(13.8, "low"), None, CHANGE_FIRST),
    (_reading(13.8, "low"), _reading(35, "normal", "2026-05-01"), CHANGE_NEW),
    (_reading(13.8, "low"), _reading(18.2, "low", "2026-05-01"), CHANGE_WORSE),
    (_reading(22.0, "low"), _reading(18.2, "low", "2026-05-01"), CHANGE_BETTER),
    (_reading(8.1, "high", unit="%"), _reading(7.2, "high", "2026-05-01", unit="%"), CHANGE_WORSE),
    (_reading(6.9, "high", unit="%"), _reading(7.2, "high", "2026-05-01", unit="%"), CHANGE_BETTER),
    (_reading(18.2, "low"), _reading(18.2, "low", "2026-05-01"), CHANGE_SAME),
    (_reading(160, "high"), _reading(20, "low", "2026-05-01"), CHANGE_FLIPPED),
    (_reading(40, "normal"), _reading(18.2, "low", "2026-05-01"), CHANGE_RESOLVED),
])
def test_each_kind_of_change(latest, previous, kind):
    assert describe_change(latest, previous)["kind"] == kind


def test_a_normal_reading_after_a_normal_one_says_nothing():
    assert describe_change(_reading(40, "normal"), _reading(35, "normal", "2026-05-01")) is None


def test_values_in_different_units_are_not_compared():
    """ng/mL against nmol/L would read as a step change that is purely a units artefact."""
    latest = _reading(13.8, "low", unit="ng/mL")
    previous = _reading(30, "low", "2026-05-01", unit="nmol/L")
    assert describe_change(latest, previous) is None


def test_an_unclassified_previous_reading_is_not_guessed_about():
    assert describe_change(_reading(13.8, "low"), _reading(12, "unknown", "2026-05-01")) is None


def test_a_change_carries_the_previous_reading():
    change = describe_change(_reading(13.8, "low"), _reading(18.2, "low", "2026-05-01"))
    assert change["previous_value"] == 18.2 and change["previous_date"] == "2026-05-01"
    assert change["previous_flag"] == "low" and change["previous_unit"] == "ng/mL"


def test_the_same_report_uploaded_twice_is_not_its_own_previous_reading():
    """Same date means same report: comparing it with itself would read "unchanged"."""
    row = ("Vitamin D", "Vitamin D", 13.8, None, "ng/mL", "low", None, date(2026, 9, 20), "doc-a")
    copy = ("Vitamin D", "Vitamin D", 13.8, None, "ng/mL", "low", None, date(2026, 9, 20), "doc-b")
    older = ("Vitamin D", "Vitamin D", 18.2, None, "ng/mL", "low", None, date(2026, 5, 1), "doc-c")
    latest, previous = od._latest_and_previous([row, copy, older])["Vitamin D"]
    assert latest["document_id"] == "doc-a"
    assert previous["document_id"] == "doc-c"


# ---- medication labels follow the document's review ----

def _overview(mode="structured"):
    fact = {"id": "f1", "kind": "medication", "text": "Tab Gabantin", "label": "Reported, unverified",
            "source_type": "document", "source_id": "doc-rx"}
    lines = [{"heading": "Medications", "items": [{**fact, "fact_id": "f1"}]}]
    return {"facts": [fact], "lines": lines, "mode": mode}


def _review_of_doc_rx(monkeypatch, state):
    """The report's review, as merged across its copies (here: one copy)."""
    monkeypatch.setattr(od, "copy_groups", lambda ids: {i: [i] for i in ids})
    monkeypatch.setattr("app.services.document_reviews.merged_review_states", lambda groups, d, v: {"doc-rx": state})


def test_a_medication_from_a_verified_document_says_who_verified_it(monkeypatch):
    _review_of_doc_rx(monkeypatch, {"status": "verified", "verified_by": [{"name": "Dr. Thanvi", "is_me": False}]})
    card = od.apply_review_labels(_overview(), "d1", "Orthopedics")
    assert card["facts"][0]["label"] == "From a document · verified by Dr. Thanvi"
    assert card["lines"][0]["items"][0]["label"] == "From a document · verified by Dr. Thanvi"


def test_a_medication_from_a_reported_document_says_so(monkeypatch):
    _review_of_doc_rx(monkeypatch, {"status": "flagged", "verified_by": [], "flagged_by": [{"name": "Dr. X"}]})
    card = od.apply_review_labels(_overview("phrased"), "d1", None)
    assert card["facts"][0]["label"] == "From a document · reported inaccurate by Dr. X"


def test_a_reported_document_says_who_objected_and_why(monkeypatch):
    """Kept in the summary (the agreed rule), with the objection beside it."""
    _review_of_doc_rx(monkeypatch, {"status": "flagged", "verified_by": [], "flagged_by": [
        {"name": "Dr. X", "reason": "Dose misread"}, {"name": "Dr. Y", "reason": None}]})
    card = od.apply_review_labels(_overview(), "d1", None)
    assert card["facts"][0]["label"] == "From a document · reported inaccurate by Dr. X: “Dose misread”; Dr. Y"
    assert card["facts"][0]["text"] == "Tab Gabantin"


def test_a_finding_from_a_document_is_labelled_like_a_medicine(monkeypatch):
    _review_of_doc_rx(monkeypatch, {"status": "verified", "verified_by": [{"name": "Dr. Thanvi", "is_me": True}]})
    overview = _overview()
    overview["facts"][0] = {**overview["facts"][0], "kind": "finding", "label": None}
    card = od.apply_review_labels(overview, "d1", None)
    assert card["facts"][0]["label"] == "From a document · verified by you"


def test_an_unreviewed_medication_keeps_reported_unverified(monkeypatch):
    _review_of_doc_rx(monkeypatch, {"status": "unverified", "verified_by": [], "flagged_by": []})
    assert od.apply_review_labels(_overview(), "d1", None)["facts"][0]["label"] == "Reported, unverified"


# ---- the card no longer phrases results twice ----

def test_results_are_not_phrased_into_the_card(monkeypatch):
    """They are shown by document; phrasing them too said everything twice."""
    import asyncio

    from app.services import patient_overview

    seen = {}

    async def fake_phrase(*, facts):
        seen["kinds"] = sorted({fact["kind"] for fact in facts})
        return {"lines": []}

    monkeypatch.setattr("app.inference.azure_client.gpt4o_overview_phrasing", fake_phrase)
    monkeypatch.setattr(patient_overview, "latest_source_change", lambda p: None)
    monkeypatch.setattr(patient_overview, "_read_cache", lambda *a: None)
    monkeypatch.setattr(patient_overview, "_write_cache", lambda *a, **k: None)
    monkeypatch.setattr(patient_overview, "gather_facts", lambda d, p, v: [
        {"id": "f1", "kind": "diagnosis", "text": "Lumbar disc bulge", "label": None, "source_type": "note", "source_id": "c1"},
        {"id": "f2", "kind": "abnormal", "text": "Vitamin D low at 13.8 ng/mL", "label": None, "source_type": "document", "source_id": "d1"},
    ])
    card = asyncio.run(patient_overview.get_overview("doc", "p1", None))
    assert seen["kinds"] == ["diagnosis"]
    assert [f["kind"] for f in card["facts"]] == ["diagnosis", "abnormal"]  # still audited


def test_a_card_with_only_results_makes_no_model_call(monkeypatch):
    import asyncio

    from app.services import patient_overview

    async def must_not_phrase(*, facts):
        pytest.fail("nothing to phrase")

    monkeypatch.setattr("app.inference.azure_client.gpt4o_overview_phrasing", must_not_phrase)
    monkeypatch.setattr(patient_overview, "latest_source_change", lambda p: None)
    monkeypatch.setattr(patient_overview, "_read_cache", lambda *a: None)
    monkeypatch.setattr(patient_overview, "_write_cache", lambda *a, **k: None)
    monkeypatch.setattr(patient_overview, "gather_facts", lambda d, p, v: [
        {"id": "f1", "kind": "abnormal", "text": "x", "label": None, "source_type": "document", "source_id": "d1"}])
    card = asyncio.run(patient_overview.get_overview("doc", "p1", None))
    assert card["lines"] == [] and card["mode"] == "structured"


# ---- against a real database ----

def _skip_if_no_database():
    from app.db.connection import connect_db

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM document_findings LIMIT 0")
                cur.execute("SELECT 1 FROM document_reviews LIMIT 0")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


@pytest.fixture
def record():
    """Three documents for one patient: a May lab report, a September lab report, an MRI."""
    _skip_if_no_database()
    from app.db.connection import connect_db

    tag = uuid.uuid4().hex[:8]
    ids = {
        "patient": f"glance-patient-{tag}",
        "may": f"glance-may-{tag}", "sep": f"glance-sep-{tag}", "sep_copy": f"glance-copy-{tag}",
        "mri": f"glance-mri-{tag}",
        "doctor": str(uuid.uuid4()),
    }
    documents = [
        ("may", "may-labs.pdf", "blood_report", date(2026, 5, 1)),
        ("sep", "sep-labs.pdf", "blood_report", date(2026, 9, 20)),
        ("mri", "mri.png", "mri_report", date(2026, 4, 23)),
    ]
    readings = [
        # (document, canonical, value, unit, flag)
        ("may", "Vitamin D", 18.2, "ng/mL", "low"),
        ("may", "HbA1c", 5.4, "%", "normal"),
        ("may", "Haemoglobin", 11.9, "g/dL", "low"),
        ("sep", "Vitamin D", 13.8, "ng/mL", "low"),
        ("sep", "HbA1c", 8.1, "%", "high"),
        ("sep", "Haemoglobin", 13.9, "g/dL", "normal"),
    ]
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO doctors (doctor_id, name, department, experience_years, is_active) "
                "VALUES (%s, 'Dr. Glance Test', 'Orthopedics', 5, TRUE)", (ids["doctor"],))
            for key, filename, document_type, clinical_date in documents:
                cur.execute(
                    """INSERT INTO document_catalog (document_id, user_id, session_id, document_type,
                                                     clinical_date, blob_summary_path, original_filename,
                                                     ingestion_status)
                       VALUES (%s, %s, 's', %s, %s, 'x', %s, 'complete')""",
                    (ids[key], ids["patient"], document_type, clinical_date, filename))
            cur.execute(
                """INSERT INTO document_summaries (document_id, sentences, register, verification,
                                                   rejected_count, generated_at)
                   VALUES (%s, %s::jsonb, 'clinician', 'passed', 0, NOW())""",
                (ids["mri"], '[{"text": "Disc bulge at L4-L5 with mild foraminal narrowing."}, '
                             '{"text": "Butterfly vertebra at L3-L4."}]'))
            for key, canonical, value, unit, flag in readings:
                clinical_date = next(d for k, _, _, d in documents if k == key)
                cur.execute(
                    """INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name,
                                                      value_text, value_num, unit, abnormal, clinical_date)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (ids[key], ids["patient"], canonical, canonical, f"{value} {unit}", value, unit,
                     flag, clinical_date))
        conn.commit()
    try:
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                all_documents = [ids[k] for k in ("may", "sep", "sep_copy", "mri")]
                cur.execute("DELETE FROM document_reviews WHERE document_id = ANY(%s)", (all_documents,))
                cur.execute("DELETE FROM consult_audit_log WHERE metadata->>'document_id' = ANY(%s)", (all_documents,))
                cur.execute("DELETE FROM document_findings WHERE document_id = ANY(%s)", (all_documents,))
                cur.execute("DELETE FROM document_summaries WHERE document_id = ANY(%s)", (all_documents,))
                cur.execute("DELETE FROM document_catalog WHERE document_id = ANY(%s)", (all_documents,))
                cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (ids["doctor"],))
            conn.commit()


def _block(blocks, document_id):
    return next(b for b in blocks if b["document_id"] == document_id)


def test_each_report_groups_its_current_findings_with_what_changed(record):
    blocks = od.document_blocks(record["doctor"], record["patient"], "Orthopedics")
    assert [b["document_id"] for b in blocks] == [record["sep"], record["mri"]]
    sep = _block(blocks, record["sep"])
    by_name = {f["name"]: f for f in sep["findings"]}
    assert by_name["Vitamin D"]["change"]["kind"] == CHANGE_WORSE
    assert by_name["Vitamin D"]["change"]["previous_value"] == 18.2
    assert by_name["HbA1c"]["change"]["kind"] == CHANGE_NEW
    assert by_name["Haemoglobin"]["change"]["kind"] == CHANGE_RESOLVED
    assert sep["changes"] == {CHANGE_WORSE: 1, CHANGE_NEW: 1, CHANGE_RESOLVED: 1}
    # Out of range first, then the result back in range.
    assert [f["name"] for f in sep["findings"]][-1] == "Haemoglobin"


def test_a_report_whose_readings_were_all_superseded_is_not_shown(record):
    """May's results all have a later reading, so May has nothing current to say."""
    blocks = od.document_blocks(record["doctor"], record["patient"], None)
    assert record["may"] not in [b["document_id"] for b in blocks]


def test_an_imaging_report_speaks_through_its_verified_summary(record):
    mri = _block(od.document_blocks(record["doctor"], record["patient"], None), record["mri"])
    assert mri["findings"] == []
    assert mri["summary"][0] == "Disc bulge at L4-L5 with mild foraminal narrowing."


def test_verification_shows_on_the_block_with_the_doctors_name(record):
    from app.services.document_reviews import record_review

    before = _block(od.document_blocks(record["doctor"], record["patient"], None), record["sep"])
    assert before["review"]["status"] == "unverified"
    record_review(record["doctor"], record["patient"], record["sep"], "verify")
    other_doctor = str(uuid.uuid4())
    after = _block(od.document_blocks(other_doctor, record["patient"], "Cardiology"), record["sep"])
    assert after["review"]["status"] == "verified"
    assert after["review"]["verified_by"][0]["name"] == "Dr. Glance Test"
    assert after["review"]["verified_by"][0]["department"] == "Orthopedics"


def test_the_same_report_uploaded_twice_is_one_block(record):
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_catalog (document_id, user_id, session_id, document_type,
                                                 clinical_date, blob_summary_path, original_filename,
                                                 ingestion_status, created_at)
                   VALUES (%s, %s, 's', 'mri_report', %s, 'x', 'mri.png', 'complete', NOW() - interval '1 day')""",
                (record["sep_copy"], record["patient"], date(2026, 4, 23)))
            cur.execute(
                """INSERT INTO document_summaries (document_id, sentences, register, verification,
                                                   rejected_count, generated_at)
                   VALUES (%s, '[{"text": "Disc bulge at L4-L5."}]'::jsonb, 'clinician', 'passed', 0, NOW())""",
                (record["sep_copy"],))
        conn.commit()
    blocks = od.document_blocks(record["doctor"], record["patient"], None)
    mri_blocks = [b for b in blocks if b["original_filename"] == "mri.png"]
    assert len(mri_blocks) == 1 and mri_blocks[0]["copies"] == 2


def test_a_browser_numbered_copy_of_a_lab_report_is_the_same_report(record):
    """Live data: "Lab_Report.pdf" uploaded four times, one saved as "Lab_Report (4).pdf".
    The copy holding the current readings was one block and the other copies a second,
    showing summary sentences — the same report twice."""
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                                 blob_summary_path, original_filename, ingestion_status, created_at)
                   VALUES (%s, %s, 's', 'blood_report', %s, 'x', 'sep-labs (1).pdf', 'complete', NOW() - interval '2 days')""",
                (record["sep_copy"], record["patient"], date(2026, 9, 20)))
            cur.execute(
                """INSERT INTO document_summaries (document_id, sentences, register, verification, rejected_count, generated_at)
                   VALUES (%s, '[{"text": "Vitamin D is low."}]'::jsonb, 'clinician', 'passed', 0, NOW())""",
                (record["sep_copy"],))
            cur.execute(
                """INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name, value_text,
                                                  value_num, unit, abnormal, clinical_date, created_at)
                   VALUES (%s, %s, 'Vitamin D', 'Vitamin D', '13.8 ng/mL', 13.8, 'ng/mL', 'low', %s, NOW() - interval '2 days')""",
                (record["sep_copy"], record["patient"], date(2026, 9, 20)))
        conn.commit()
    blocks = od.document_blocks(record["doctor"], record["patient"], None)
    lab_blocks = [b for b in blocks if b["document_type"] == "blood_report"]
    assert len(lab_blocks) == 1
    assert lab_blocks[0]["copies"] == 2 and lab_blocks[0]["findings"]


@pytest.mark.parametrize("a, b", [
    ("Lab_Report (4).pdf", "Lab_Report.pdf"),
    ("scan(2).PNG", "scan.png"),
])
def test_copy_keys_ignore_a_browsers_download_number(a, b):
    assert od._copy_key(a, "blood_report", "2026-09-20") == od._copy_key(b, "blood_report", "2026-09-20")


def test_different_reports_with_the_same_file_name_stay_apart():
    assert od._copy_key("image.png", "mri_report", "2022-04-23") != od._copy_key("image.png", "prescription", "2022-05-21")


def test_a_prescription_with_a_stray_number_still_shows_its_summary(record):
    """Seen on the server: a prescription whose "Age/Gender 23/M" was read as the number 23
    counted as a lab report, so its summary was withheld and, with no abnormal readings,
    the prescription was missing from the card altogether."""
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                                 blob_summary_path, original_filename, ingestion_status)
                   VALUES (%s, %s, 's', 'prescription', %s, 'x', 'rx.png', 'complete')""",
                (record["sep_copy"], record["patient"], date(2022, 5, 21)))
            cur.execute(
                """INSERT INTO document_summaries (document_id, sentences, register, verification, rejected_count, generated_at)
                   VALUES (%s, '[{"text": "Advised serum Vitamin B12 and Vitamin D tests."}]'::jsonb,
                           'clinician', 'passed', 0, NOW())""",
                (record["sep_copy"],))
            cur.execute(
                """INSERT INTO document_findings (document_id, patient_id, printed_name, canonical_name, value_text,
                                                  value_num, unit, abnormal, clinical_date)
                   VALUES (%s, %s, 'Age/Gender', 'Age Gender', '23/M', 23, '/M', 'unknown', %s)""",
                (record["sep_copy"], record["patient"], date(2022, 5, 21)))
        conn.commit()
    rx = _block(od.document_blocks(record["doctor"], record["patient"], None), record["sep_copy"])
    assert rx["summary"] == ["Advised serum Vitamin B12 and Vitamin D tests."]
    assert rx["findings"] == []


def test_an_older_lab_report_with_a_summary_is_not_shown_once_superseded(record):
    """A lab report speaks through its current readings. May's summary would otherwise put
    May's (superseded) values back on the card as prose."""
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_summaries (document_id, sentences, register, verification, rejected_count, generated_at)
                   VALUES (%s, '[{"text": "Vitamin D was 18.2 ng/mL, low."}]'::jsonb, 'clinician', 'passed', 0, NOW())""",
                (record["may"],))
        conn.commit()
    blocks = od.document_blocks(record["doctor"], record["patient"], None)
    assert record["may"] not in [b["document_id"] for b in blocks]


# ---- a report's review covers every copy of it ----

def _add_mri_copy(record, summary="Disc bulge at L4-L5."):
    """A second upload of the fixture's MRI ("mri (1).png"), stored after the first."""
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                                 blob_summary_path, original_filename, ingestion_status, created_at)
                   VALUES (%s, %s, 's', 'mri_report', %s, 'x', 'mri (1).png', 'complete', NOW() + interval '1 hour')""",
                (record["sep_copy"], record["patient"], date(2026, 4, 23)))
            cur.execute(
                """INSERT INTO document_summaries (document_id, sentences, register, verification, rejected_count, generated_at)
                   VALUES (%s, %s::jsonb, 'clinician', 'passed', 0, NOW())""",
                (record["sep_copy"], f'[{{"text": "{summary}"}}]'))
        conn.commit()
    return record["sep_copy"]


def test_a_report_verified_on_an_older_copy_still_shows_verified(record):
    """Seen locally: once the newest copy of a prescription could show, the block showed it —
    and "unverified", though a doctor had verified the copy they opened."""
    from app.services.document_reviews import record_review

    record_review(record["doctor"], record["patient"], record["mri"], "verify")
    _add_mri_copy(record, summary="A newer reading of the same scan.")
    mri = next(b for b in od.document_blocks(record["doctor"], record["patient"], None) if b["document_type"] == "mri_report")
    assert mri["review"]["status"] == "verified" and mri["copies"] == 2
    # The block speaks through the copy that was checked, not the newer unchecked one.
    assert mri["document_id"] == record["mri"]
    assert mri["summary"][0] == "Disc bulge at L4-L5 with mild foraminal narrowing."


def test_a_doctor_who_verified_two_copies_is_named_once(record):
    from app.services.document_reviews import record_review

    copy = _add_mri_copy(record)
    record_review(record["doctor"], record["patient"], record["mri"], "verify")
    record_review(record["doctor"], record["patient"], copy, "verify")
    mri = next(b for b in od.document_blocks(record["doctor"], record["patient"], None) if b["document_type"] == "mri_report")
    assert [p["name"] for p in mri["review"]["verified_by"]] == ["Dr. Glance Test"]
    assert mri["review"]["mine"] == "verified"


def test_a_report_flagged_on_any_copy_is_flagged(record):
    from app.services.document_reviews import record_review

    copy = _add_mri_copy(record)
    # Reported first, verified on the other copy after: the report must still win.
    record_review(record["doctor"], record["patient"], copy, "flag", reason="Wrong vertebral level")
    record_review(record["doctor"], record["patient"], record["mri"], "verify")
    mri = next(b for b in od.document_blocks(record["doctor"], record["patient"], None) if b["document_type"] == "mri_report")
    assert mri["review"]["status"] == "flagged" and mri["review"]["mine"] == "flagged"


def test_a_lab_report_verified_on_a_copy_without_the_current_readings(record):
    """The readings live on one copy; the doctor may have verified another."""
    from app.db.connection import connect_db
    from app.services.document_reviews import record_review

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                                 blob_summary_path, original_filename, ingestion_status, created_at)
                   VALUES (%s, %s, 's', 'blood_report', %s, 'x', 'sep-labs (1).pdf', 'complete', NOW() - interval '2 days')""",
                (record["sep_copy"], record["patient"], date(2026, 9, 20)))
        conn.commit()
    record_review(record["doctor"], record["patient"], record["sep_copy"], "verify")
    sep = next(b for b in od.document_blocks(record["doctor"], record["patient"], None) if b["findings"])
    assert sep["document_id"] == record["sep"]
    assert sep["review"]["status"] == "verified"


def test_a_medicine_from_one_copy_is_verified_when_another_copy_is(record):
    from app.services.document_reviews import record_review

    copy = _add_mri_copy(record)
    record_review(record["doctor"], record["patient"], record["mri"], "verify")
    fact = {"id": "f1", "kind": "medication", "text": "Tab X", "label": "Reported, unverified",
            "source_type": "document", "source_id": copy}
    card = od.apply_review_labels({"facts": [fact], "lines": [], "mode": "phrased"}, record["doctor"], None)
    assert card["facts"][0]["label"] == "From a document · verified by you"


def test_copy_groups_keep_different_reports_apart(record):
    copy = _add_mri_copy(record)
    groups = od.copy_groups([record["mri"], record["sep"], "not-a-document"])
    assert sorted(groups[record["mri"]]) == sorted([record["mri"], copy])
    assert groups[record["sep"]] == [record["sep"]]
    assert groups["not-a-document"] == ["not-a-document"]


def test_two_copies_listed_together_both_show_the_reports_review(record):
    """Seen live: the history listed both uploads of one prescription, under two visits — one
    said verified and the other, the same report, unverified."""
    from app.services.document_reviews import merged_review_states, record_review

    copy = _add_mri_copy(record)
    record_review(record["doctor"], record["patient"], record["mri"], "verify")
    states = merged_review_states(od.copy_groups([record["mri"], copy]), record["doctor"], None)
    assert states[record["mri"]]["status"] == "verified"
    assert states[copy]["status"] == "verified"
    assert [p["name"] for p in states[copy]["verified_by"]] == ["Dr. Glance Test"]
