"""Measurements and trends against a real database.

The pure parsing and classification are covered in test_document_findings.py. These cover
what only SQL can prove: that re-extraction replaces rather than duplicates, that a trend
is scoped to one patient and one unit, and that "the same report uploaded twice" does not
become a history.
"""
from __future__ import annotations

import uuid

import pytest

from app.db.connection import connect_db
from app.services.document_findings import (
    findings_for_document,
    save_findings,
    trend_for,
    trendable_measurements,
)


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _measurement(name="Vitamin D, 25-Hydroxy (Total)", canonical="Vitamin D",
                 value=13.8, unit="ng/mL", operator=None, abnormal="low", panel="Vitamins"):
    return {
        "panel": panel, "name": name, "canonical_name": canonical,
        "value_text": f"{value} {unit}", "value_num": value, "unit": unit,
        "operator": operator, "abnormal": abnormal,
    }


@pytest.fixture
def patient_id():
    _skip_if_no_database()
    pid = f"findings-{uuid.uuid4().hex[:10]}"
    try:
        yield pid
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_findings WHERE patient_id = %s", (pid,))
            conn.commit()


# ---- storage ----

def test_measurements_round_trip_with_their_reference_range(patient_id):
    """The bounds are stored alongside, so the UI can show "13.8 (ref 30-100)" without
    re-deriving them from a table it might disagree with."""
    save_findings("doc-1", patient_id, [_measurement()], "2026-09-20")

    stored = findings_for_document("doc-1")
    assert len(stored) == 1
    assert stored[0]["canonical_name"] == "Vitamin D"
    assert stored[0]["value_num"] == pytest.approx(13.8)
    assert stored[0]["ref_low"] == pytest.approx(30.0)
    assert stored[0]["ref_high"] == pytest.approx(100.0)
    assert stored[0]["abnormal"] == "low"


def test_re_extracting_a_document_replaces_rather_than_duplicates(patient_id):
    """Without this a re-run would double every point on that patient's trends."""
    save_findings("doc-1", patient_id, [_measurement(value=13.8)], "2026-09-20")
    save_findings("doc-1", patient_id, [_measurement(value=14.2)], "2026-09-20")

    stored = findings_for_document("doc-1")
    assert len(stored) == 1
    assert stored[0]["value_num"] == pytest.approx(14.2)


def test_abnormal_results_sort_first_within_a_document(patient_id):
    save_findings("doc-1", patient_id, [
        _measurement(name="TSH", canonical="TSH", value=2.1, unit="uIU/mL", abnormal="normal"),
        _measurement(),
    ], "2026-09-20")

    assert findings_for_document("doc-1")[0]["abnormal"] == "low"


# ---- trends ----

def test_a_trend_is_ordered_oldest_to_newest(patient_id):
    save_findings("doc-2", patient_id, [_measurement(value=22.0)], "2026-10-15")
    save_findings("doc-1", patient_id, [_measurement(value=13.8)], "2026-09-20")

    series = trend_for(patient_id, "Vitamin D")
    assert [point["value"] for point in series] == [13.8, 22.0]


def test_the_same_report_uploaded_twice_is_one_point_not_two(patient_id):
    """Real data: the same blood report had been uploaded three times. Three readings of
    one draw are one observation, however many documents carry them."""
    for document_id in ("doc-1", "doc-2", "doc-3"):
        save_findings(document_id, patient_id, [_measurement(value=13.8)], "2026-09-20")

    assert len(trend_for(patient_id, "Vitamin D")) == 1


def test_two_different_results_on_the_same_day_are_both_kept(patient_id):
    """Two labs genuinely disagreeing is a clinical fact, not duplication. The dedupe is
    on (date, value, unit), so it cannot swallow this."""
    save_findings("doc-1", patient_id, [_measurement(value=13.8)], "2026-09-20")
    save_findings("doc-2", patient_id, [_measurement(value=29.5)], "2026-09-20")

    assert sorted(point["value"] for point in trend_for(patient_id, "Vitamin D")) == [13.8, 29.5]


def test_a_unit_change_does_not_produce_a_fake_step_change(patient_id):
    """A lab switching ng/mL to nmol/L would otherwise show a 2.5x jump that looks
    clinical and is purely an artefact. Only the latest unit's readings are returned."""
    save_findings("doc-1", patient_id, [_measurement(value=13.8, unit="ng/mL")], "2026-09-20")
    save_findings("doc-2", patient_id, [_measurement(value=55.0, unit="nmol/L")], "2026-10-15")

    series = trend_for(patient_id, "Vitamin D")
    assert {point["unit"] for point in series} == {"nmol/L"}


def test_a_censored_value_is_never_plotted(patient_id):
    """"<0.01" is a bound, not a measurement. Plotting it as a point would assert
    precision the lab declined to give."""
    save_findings("doc-1", patient_id, [
        _measurement(name="TSH", canonical="TSH", value=0.01, unit="uIU/mL",
                     operator="<", abnormal="unknown"),
    ], "2026-09-20")

    assert trend_for(patient_id, "TSH") == []


def test_a_trend_never_crosses_patients(patient_id):
    other = f"other-{uuid.uuid4().hex[:8]}"
    try:
        save_findings("doc-1", patient_id, [_measurement(value=13.8)], "2026-09-20")
        save_findings("doc-9", other, [_measurement(value=99.0)], "2026-09-21")

        assert [point["value"] for point in trend_for(patient_id, "Vitamin D")] == [13.8]
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_findings WHERE patient_id = %s", (other,))
            conn.commit()


# ---- what counts as trendable ----

def test_one_date_is_not_a_trend_however_many_documents_carry_it(patient_id):
    for document_id in ("doc-1", "doc-2", "doc-3"):
        save_findings(document_id, patient_id, [_measurement()], "2026-09-20")

    assert trendable_measurements(patient_id) == []


def test_two_distinct_dates_make_a_trend(patient_id):
    save_findings("doc-1", patient_id, [_measurement(value=13.8)], "2026-09-20")
    save_findings("doc-2", patient_id, [_measurement(value=22.0)], "2026-10-15")

    trendable = trendable_measurements(patient_id)
    assert len(trendable) == 1
    assert trendable[0]["canonical_name"] == "Vitamin D"
    assert trendable[0]["dates"] == 2


def test_a_measurement_with_no_date_cannot_be_trended(patient_id):
    """Time is the axis. A reading with no clinical date has nowhere to sit on it."""
    save_findings("doc-1", patient_id, [_measurement(value=13.8)], None)
    save_findings("doc-2", patient_id, [_measurement(value=22.0)], None)

    assert trendable_measurements(patient_id) == []
