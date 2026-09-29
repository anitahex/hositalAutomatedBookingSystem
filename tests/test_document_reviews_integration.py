"""Doctors verifying and reporting a document — shared across every treating doctor.

Against a real database, because the rules are about what OTHER doctors see: one doctor's
verification is visible to all, only its author can withdraw it, a report outranks any
verification, re-processing the document lapses everything, and a verifier in a sensitive
specialty is not named to doctors outside it.
"""
from __future__ import annotations

import uuid

import pytest

from app.db.connection import connect_db
from app.services.document_reviews import (
    ReviewConflict,
    STATUS_FLAGGED,
    STATUS_UNVERIFIED,
    STATUS_VERIFIED,
    record_review,
    review_states,
)


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM document_reviews LIMIT 0")
    except Exception as exc:
        pytest.skip(f"Requires Postgres with migration 0027 applied: {exc}")


@pytest.fixture
def world():
    _skip_if_no_database()
    ids = {
        "patient": f"review-patient-{uuid.uuid4().hex[:8]}",
        "document": f"review-doc-{uuid.uuid4().hex[:8]}",
        "bare": f"review-bare-{uuid.uuid4().hex[:8]}",
        "ortho": str(uuid.uuid4()), "psych": str(uuid.uuid4()), "cardio": str(uuid.uuid4()),
    }
    with connect_db() as conn:
        with conn.cursor() as cur:
            for key, name, department in (("ortho", "Dr. Test Ortho", "Orthopedics"),
                                          ("psych", "Dr. Test Psych", "Psychiatry"),
                                          ("cardio", "Dr. Test Cardio", "Cardiology")):
                cur.execute(
                    "INSERT INTO doctors (doctor_id, name, department, experience_years, is_active) "
                    "VALUES (%s, %s, %s, 5, TRUE)",
                    (ids[key], name, department),
                )
            cur.execute(
                """INSERT INTO document_summaries (document_id, sentences, register, verification,
                                                   rejected_count, generated_at)
                   VALUES (%s, '[]'::jsonb, 'clinician', 'passed', 0, NOW() - interval '1 day')""",
                (ids["document"],),
            )
        conn.commit()
    try:
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                documents = [ids["document"], ids["bare"]]
                cur.execute("DELETE FROM document_reviews WHERE document_id = ANY(%s)", (documents,))
                cur.execute(
                    "DELETE FROM consult_audit_log WHERE metadata->>'document_id' = ANY(%s)", (documents,)
                )
                cur.execute("DELETE FROM document_summaries WHERE document_id = ANY(%s)", (documents,))
                cur.execute(
                    "DELETE FROM doctors WHERE doctor_id = ANY(%s::uuid[])",
                    ([ids["ortho"], ids["psych"], ids["cardio"]],),
                )
            conn.commit()


def _review(world, who, verb, reason=None, document="document", department=None):
    return record_review(world[who], world["patient"], world[document], verb, reason,
                         viewer_department=department)


def _state(world, who, department, document="document"):
    return review_states([world[document]], world[who], department)[world[document]]


def test_a_document_nobody_reviewed_is_unverified(world):
    state = _state(world, "ortho", "Orthopedics")
    assert state == {"status": STATUS_UNVERIFIED, "verified_by": [], "flagged_by": [], "mine": None}


def test_one_doctors_verification_is_seen_by_every_treating_doctor(world):
    _review(world, "ortho", "verify")
    seen_by_cardio = _state(world, "cardio", "Cardiology")
    assert seen_by_cardio["status"] == STATUS_VERIFIED
    assert [p["name"] for p in seen_by_cardio["verified_by"]] == ["Dr. Test Ortho"]
    assert seen_by_cardio["mine"] is None
    assert _state(world, "ortho", "Orthopedics")["mine"] == "verified"


def test_a_doctor_withdraws_only_their_own_verification(world):
    _review(world, "ortho", "verify")
    _review(world, "cardio", "verify")
    after = _review(world, "ortho", "withdraw", department="Orthopedics")
    assert [p["name"] for p in after["verified_by"]] == ["Dr. Test Cardio"]
    assert after["status"] == STATUS_VERIFIED and after["mine"] is None


def test_withdrawing_a_verification_you_never_made_is_refused(world):
    _review(world, "ortho", "verify")
    with pytest.raises(ReviewConflict):
        _review(world, "cardio", "withdraw")


def test_a_report_outranks_any_verification_and_everyone_sees_why(world):
    _review(world, "ortho", "verify")
    _review(world, "cardio", "flag", "Vitamin D is 18 on the report, not 13.8")
    seen_by_ortho = _state(world, "ortho", "Orthopedics")
    assert seen_by_ortho["status"] == STATUS_FLAGGED
    assert seen_by_ortho["flagged_by"][0]["reason"] == "Vitamin D is 18 on the report, not 13.8"
    assert [p["name"] for p in seen_by_ortho["verified_by"]] == ["Dr. Test Ortho"]


@pytest.mark.parametrize("reason", [None, "", "   ", "bad"])
def test_a_report_needs_a_reason(world, reason):
    with pytest.raises(ValueError):
        _review(world, "ortho", "flag", reason)
    assert _state(world, "ortho", "Orthopedics")["status"] == STATUS_UNVERIFIED


def test_only_the_reporter_can_clear_a_report(world):
    _review(world, "cardio", "flag", "Wrong date on the summary")
    with pytest.raises(ReviewConflict):
        _review(world, "ortho", "clear_flag")
    cleared = _review(world, "cardio", "clear_flag", department="Cardiology")
    assert cleared["status"] == STATUS_UNVERIFIED and cleared["mine"] is None


def test_verifying_twice_writes_one_row(world):
    _review(world, "ortho", "verify")
    _review(world, "ortho", "verify")
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM document_reviews WHERE document_id = %s", (world["document"],))
            assert cur.fetchone()[0] == 1
        conn.commit()


def test_reprocessing_the_document_lapses_every_review_but_keeps_the_history(world):
    """A doctor must never appear to have verified text they never saw."""
    _review(world, "ortho", "verify")
    _review(world, "cardio", "flag", "Wrong units on the summary")
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE document_summaries SET generated_at = NOW() WHERE document_id = %s",
                        (world["document"],))
        conn.commit()

    assert _state(world, "ortho", "Orthopedics")["status"] == STATUS_UNVERIFIED
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM document_reviews WHERE document_id = %s", (world["document"],))
            assert cur.fetchone()[0] == 2
        conn.commit()


def test_a_psychiatry_verifier_is_not_named_outside_psychiatry(world):
    """Naming them would tell a cardiologist the patient sees a psychiatrist."""
    _review(world, "psych", "verify")
    to_cardio = _state(world, "cardio", "Cardiology")["verified_by"][0]
    assert (to_cardio["name"], to_cardio["department"]) == ("A clinician", "restricted specialty")
    to_psych = _state(world, "psych", "Psychiatry")["verified_by"][0]
    assert to_psych["name"] == "Dr. Test Psych" and to_psych["is_me"] is True


def test_every_action_is_audited_with_the_reason(world):
    _review(world, "ortho", "verify")
    _review(world, "ortho", "withdraw")
    _review(world, "cardio", "flag", "Wrong laboratory named")
    _review(world, "cardio", "clear_flag")
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT action_type, metadata->>'reason' FROM consult_audit_log
                   WHERE metadata->>'document_id' = %s ORDER BY created_at""",
                (world["document"],),
            )
            rows = cur.fetchall()
        conn.commit()
    assert [row[0] for row in rows] == [
        "document_verified", "document_verification_withdrawn",
        "document_flagged_inaccurate", "document_flag_cleared",
    ]
    assert rows[2][1] == "Wrong laboratory named"


def test_a_document_with_no_summary_can_still_be_verified_and_lapses_when_one_arrives(world):
    """With no summary the doctor verified the extracted values alone. A summary appearing
    later is new text they have not seen."""
    _review(world, "ortho", "verify", document="bare")
    assert _state(world, "ortho", "Orthopedics", document="bare")["status"] == STATUS_VERIFIED
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_summaries (document_id, sentences, register, verification,
                                                   rejected_count, generated_at)
                   VALUES (%s, '[]'::jsonb, 'clinician', 'passed', 0, NOW())""",
                (world["bare"],),
            )
        conn.commit()
    assert _state(world, "ortho", "Orthopedics", document="bare")["status"] == STATUS_UNVERIFIED


def test_an_unknown_action_is_rejected(world):
    with pytest.raises(ValueError):
        _review(world, "ortho", "approve")


# ---- the doctor's own audit log ----

def test_a_review_appears_in_the_reviewing_doctors_audit_log_and_opens_the_document(world):
    """Recorded in consult_audit_log since reviews shipped, but never on the feed: a doctor
    who verified a document could find no trace of it in their own audit log."""
    from app.services.doctor_ai_activity import get_activity_log

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO document_catalog (document_id, user_id, session_id, document_type,
                                                 blob_summary_path, original_filename, ingestion_status)
                   VALUES (%s, %s, 'feed-session', 'blood_report', 'x', 'lab-feed.pdf', 'complete')""",
                (world["document"], world["patient"]),
            )
        conn.commit()
    try:
        _review(world, "ortho", "verify")
        _review(world, "ortho", "flag", reason="Vitamin D value misread")
        events = get_activity_log(world["ortho"])["events"]
        mine = [e for e in events if (e.get("detail") or {}).get("document_id") == world["document"]]
        assert [e["action"] for e in mine] == ["document_flagged_inaccurate", "document_verified"]
        flagged, verified = mine
        assert verified["label"] == "You verified a document" and verified["is_ai"] is False
        assert verified["openable"] is True
        assert verified["document"]["original_filename"] == "lab-feed.pdf"
        assert verified["document"]["patient_id"] == world["patient"]
        assert flagged["detail"]["reason"] == "Vitamin D value misread"
        # Another doctor's log does not show it.
        assert not [e for e in get_activity_log(world["psych"])["events"]
                    if (e.get("detail") or {}).get("document_id") == world["document"]]
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_catalog WHERE document_id = %s", (world["document"],))
            conn.commit()


def test_a_review_of_a_document_no_longer_catalogued_is_listed_but_not_openable(world):
    from app.services.doctor_ai_activity import get_activity_log

    _review(world, "cardio", "verify")
    [event] = [e for e in get_activity_log(world["cardio"])["events"]
               if (e.get("detail") or {}).get("document_id") == world["document"]]
    assert event["openable"] is False and "document" not in event
