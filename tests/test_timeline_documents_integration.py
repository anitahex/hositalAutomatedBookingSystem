"""Documents on the full timeline, and filters that narrow each other.

The bug: filtering the timeline by any document type returned "No encounters match". The
filter matched only documents whose document_catalog.booking_id was set — which nothing
sets for a patient's own uploads — so on real data every document filter was empty, and no
encounter ever listed its documents.

What links a document to a visit now, and only these: the document's own booking_id, or the
booking snapshot's record of documents the patient brought when booking. A document neither
record ties to a visit is its own timeline entry, never guessed onto a visit.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

import pytest

from app.db.connection import connect_db
from app.services.patient_timeline import get_patient_timeline, get_timeline_filters
from tests.test_patient_timeline_integration import _doctor, _encounter, _patient, _skip_if_no_database


def _document(cur, patient_id, document_type, *, filename=None, booking_id=None, days_ago=30):
    document_id = f"tl-doc-{uuid.uuid4().hex[:10]}"
    cur.execute(
        """INSERT INTO document_catalog (document_id, user_id, session_id, document_type, clinical_date,
                                         blob_summary_path, ingestion_status, original_filename, booking_id)
           VALUES (%s, %s, 'test', %s, %s, 'x', 'complete', %s, %s)""",
        (document_id, patient_id, document_type, date.today() - timedelta(days=days_ago),
         filename or f"{document_type}.pdf", booking_id),
    )
    return document_id


@pytest.fixture
def world():
    """A patient seen in Orthopedics (brought an MRI and a prescription when booking) and in
    Psychiatry (one document attached to the booking directly), plus a blood report
    uploaded three times that belongs to no visit."""
    _skip_if_no_database()
    ids: dict = {}
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                ids["patient"] = _patient(cur, f"tld-{uuid.uuid4().hex[:8]}@example.com")
                ids["ortho"] = _doctor(cur, "Dr. Ortho", "Orthopedics")
                ids["psych"] = _doctor(cur, "Dr. Psych", "Psychiatry")
                ids["b_ortho"] = _encounter(cur, ids["ortho"], ids["patient"], days_ago=3, note="Butterfly vertebra.")
                ids["b_psych"] = _encounter(cur, ids["psych"], ids["patient"], days_ago=6, note="Anxiety.")

                ids["mri"] = _document(cur, ids["patient"], "mri_report")
                ids["rx"] = _document(cur, ids["patient"], "prescription")
                cur.execute(
                    "INSERT INTO booking_context_snapshots (booking_id, patient_id, document_ids) VALUES (%s, %s, %s::jsonb)",
                    (ids["b_ortho"], ids["patient"], json.dumps([ids["mri"], ids["rx"]])),
                )
                ids["letter"] = _document(cur, ids["patient"], "discharge_summary", booking_id=ids["b_psych"])
                ids["blood"] = [
                    _document(cur, ids["patient"], "blood_report", filename="Lab_Report.pdf", days_ago=8)
                    for _ in range(3)
                ]
                # A second consult on the Orthopedics visit: one discarded, one restarted.
                # Created LATER than the real one, so "the latest consult" would pick it if
                # discarded consults were not excluded.
                cur.execute(
                    """INSERT INTO consultations (booking_id, doctor_id, patient_id, status, created_at)
                       VALUES (%s, %s, %s, 'discarded', NOW() + interval '1 minute')""",
                    (ids["b_ortho"], ids["ortho"], ids["patient"]),
                )
            conn.commit()
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                if ids.get("patient"):
                    cur.execute("DELETE FROM document_catalog WHERE user_id = %s", (ids["patient"],))
                for key in ("ortho", "psych"):
                    if ids.get(key):
                        cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (ids[key],))
                if ids.get("patient"):
                    cur.execute("DELETE FROM users WHERE user_id = %s", (ids["patient"],))
            conn.commit()


def _timeline(world, **filters):
    return get_patient_timeline(world["ortho"], world["patient"], "Orthopedics", **filters)


def _kinds(timeline):
    return [(item["kind"], item.get("booking_id") or item.get("document_type")) for item in timeline["items"]]


def test_a_document_filter_finds_the_visit_the_patient_brought_it_to(world):
    """The bug: "MRI Report" returned no encounters, because the link lives on the booking
    snapshot, which the filter never read."""
    timeline = _timeline(world, document_type="mri_report")
    assert _kinds(timeline) == [("encounter", world["b_ortho"])]


def test_a_visit_lists_the_documents_brought_to_it(world):
    ortho = next(i for i in _timeline(world)["items"] if i.get("booking_id") == world["b_ortho"])
    assert {d["document_id"] for d in ortho["documents"]} == {world["mri"], world["rx"]}


def test_a_document_attached_to_the_booking_directly_still_counts(world):
    assert _kinds(_timeline(world, document_type="discharge_summary")) == [("encounter", world["b_psych"])]


def test_a_document_that_belongs_to_no_visit_is_its_own_entry_not_guessed_onto_one(world):
    timeline = _timeline(world, document_type="blood_report")
    assert _kinds(timeline) == [("document", "blood_report")]
    assert all(not any(d["document_type"] == "blood_report" for d in item.get("documents", []))
               for item in timeline["items"] if item["kind"] == "encounter")


def test_a_report_uploaded_three_times_is_one_entry(world):
    [entry] = [i for i in _timeline(world)["items"] if i["kind"] == "document"]
    assert entry["copies"] == 3


def test_the_timeline_orders_visits_and_documents_together(world):
    assert [kind for kind, _ in _kinds(_timeline(world))] == ["encounter", "encounter", "document"]


def test_documents_without_a_visit_are_left_out_once_a_department_or_doctor_is_chosen(world):
    """They have neither, so they cannot match either filter."""
    assert all(item["kind"] == "encounter" for item in _timeline(world, department="Orthopedics")["items"])
    assert all(item["kind"] == "encounter" for item in _timeline(world, other_doctor_id=world["psych"])["items"])


def test_a_visit_with_a_discarded_and_a_restarted_consult_is_listed_once_with_the_real_note(world):
    """It was listed once per consult. Listed once now — and the note shown must be the
    signed one, not the later, discarded consult's nothing."""
    encounters = _timeline(world)["encounters"]
    assert [e["booking_id"] for e in encounters].count(world["b_ortho"]) == 1
    ortho = next(e for e in encounters if e["booking_id"] == world["b_ortho"])
    assert ortho["note"] and "Butterfly vertebra" in ortho["note"]["summary"]


def test_the_date_range_applies_to_documents_by_their_report_date(world):
    today = date.today()
    recent = _timeline(world, date_from=(today - timedelta(days=7)).isoformat(), date_to=today.isoformat())
    assert all(item["kind"] == "encounter" for item in recent["items"])
    older = _timeline(world, date_from=(today - timedelta(days=9)).isoformat(),
                      date_to=(today - timedelta(days=7)).isoformat())
    assert _kinds(older) == [("document", "blood_report")]


def test_the_cursor_pages_through_visits_and_documents_without_repeats(world):
    first = _timeline(world, limit=2)
    second = _timeline(world, limit=2, cursor=first["next_cursor"])
    seen = _kinds(first) + _kinds(second)
    assert len(seen) == 3 and len(set(seen)) == 3


# ---- the filters narrow each other ----

def test_the_facets_say_which_document_types_each_doctor_has(world):
    filters = get_timeline_filters(world["patient"])
    by_department = {facet["department"]: facet for facet in filters["facets"]}
    assert by_department["Orthopedics"]["document_types"] == ["mri_report", "prescription"]
    assert by_department["Psychiatry"]["document_types"] == ["discharge_summary"]
    assert by_department["Orthopedics"]["doctor_id"] == world["ortho"]
    assert filters["unlinked_document_types"] == ["blood_report"]


def test_every_document_type_offered_matches_something(world):
    filters = get_timeline_filters(world["patient"])
    for document_type in filters["document_types"]:
        assert _timeline(world, document_type=document_type)["items"], document_type
    for facet in filters["facets"]:
        for document_type in facet["document_types"]:
            assert _timeline(world, department=facet["department"], other_doctor_id=facet["doctor_id"],
                             document_type=document_type)["items"], (facet["department"], document_type)
