"""Doctors verifying a document's AI summary and extracted values — shared across doctors.

WHAT VERIFYING MEANS. "I have checked this summary and these values against the original
document." It is not a clinical interpretation, and the UI says so where the button is.

SHARED, SIGNED BY EACH DOCTOR. Every treating doctor sees the same document, so:

  - any treating doctor may verify it, and everyone sees who did and when
  - a doctor may withdraw only their OWN verification
  - any treating doctor may report it inaccurate, with a reason, and everyone sees that —
    a report outranks any number of verifications, because one doctor finding an error
    matters more than several who did not
  - a doctor may clear only their OWN report

A doctor's position is their latest row in document_reviews (append-only; see migration
0027). Only rows made against the CURRENT summary count: re-processing a document gives
its summary a new generated_at, and earlier verifications lapse on their own.

SENSITIVE SPECIALTIES. Who verified a document can disclose where a patient is being seen:
"Verified by Dr Panday (Psychiatry)" tells a cardiologist the patient sees a psychiatrist.
The same rule as the timeline applies (patient_timeline.may_read_note): to a doctor outside
that specialty, the reviewer is "A clinician (restricted specialty)".

Authorization is the caller's: routes run assert_doctor_may_read_document first.
"""
from __future__ import annotations

import json
import logging

from app.db.connection import connect_db
from app.services.patient_timeline import may_read_note

logger = logging.getLogger(__name__)

# API verb -> stored action.
ACTIONS = {
    "verify": "verified",
    "withdraw": "withdrawn",
    "flag": "flagged_inaccurate",
    "clear_flag": "flag_cleared",
}
_AUDIT_ACTIONS = {
    "verified": "document_verified",
    "withdrawn": "document_verification_withdrawn",
    "flagged_inaccurate": "document_flagged_inaccurate",
    "flag_cleared": "document_flag_cleared",
}

STATUS_FLAGGED = "flagged"
STATUS_VERIFIED = "verified"
STATUS_UNVERIFIED = "unverified"

REASON_MIN_CHARS = 5
REASON_MAX_CHARS = 500

RESTRICTED_REVIEWER = {"name": "A clinician", "department": "restricted specialty"}


class ReviewConflict(Exception):
    """The action does not apply to this doctor's current position (withdrawing a
    verification they never made, clearing a report they never filed). Answered with 409."""


def _current_positions(cur, document_ids: list[str]) -> list[tuple]:
    """(document_id, doctor_id, name, department, action, reason, created_at) for every
    doctor whose latest review of the document's CURRENT summary is a verification or a
    report. Withdrawn and cleared positions are simply absent."""
    cur.execute(
        """
        WITH current AS (
            SELECT ids.document_id, ds.generated_at
            FROM unnest(%s::text[]) AS ids(document_id)
            LEFT JOIN document_summaries ds ON ds.document_id = ids.document_id
        ),
        latest AS (
            SELECT DISTINCT ON (r.document_id, r.doctor_id)
                   r.document_id, r.doctor_id, r.action, r.reason, r.created_at
            FROM document_reviews r
            JOIN current c ON c.document_id = r.document_id
            WHERE r.summary_generated_at IS NOT DISTINCT FROM c.generated_at
            ORDER BY r.document_id, r.doctor_id, r.review_seq DESC
        )
        SELECT l.document_id, l.doctor_id::text, d.name, d.department, l.action, l.reason, l.created_at
        FROM latest l
        JOIN doctors d ON d.doctor_id = l.doctor_id
        WHERE l.action IN ('verified', 'flagged_inaccurate')
        ORDER BY l.created_at
        """,
        (list(document_ids),),
    )
    return cur.fetchall()


def _earlier_positions(cur, document_ids: list[str]) -> list[tuple]:
    """Verifications and reports made against an EARLIER version of a document's summary —
    before it was re-processed. They no longer apply to the text on screen, so they are not
    the document's status; but they happened, and the history must say so rather than lose
    them (the earlier text itself is kept in document_versions).

    Same columns as _current_positions, plus the version's generated_at."""
    cur.execute(
        """
        WITH current AS (
            SELECT ids.document_id, ds.generated_at
            FROM unnest(%s::text[]) AS ids(document_id)
            LEFT JOIN document_summaries ds ON ds.document_id = ids.document_id
        ),
        latest AS (
            SELECT DISTINCT ON (r.document_id, r.doctor_id)
                   r.document_id, r.doctor_id, r.action, r.reason, r.created_at, r.summary_generated_at
            FROM document_reviews r
            JOIN current c ON c.document_id = r.document_id
            WHERE r.summary_generated_at IS DISTINCT FROM c.generated_at
            ORDER BY r.document_id, r.doctor_id, r.review_seq DESC
        )
        SELECT l.document_id, l.doctor_id::text, d.name, d.department, l.action, l.reason,
               l.created_at, l.summary_generated_at
        FROM latest l
        JOIN doctors d ON d.doctor_id = l.doctor_id
        WHERE l.action IN ('verified', 'flagged_inaccurate')
        ORDER BY l.created_at
        """,
        (list(document_ids),),
    )
    return cur.fetchall()


def _reviewer(doctor_id, name, department, viewer_doctor_id, viewer_department) -> dict:
    if str(doctor_id) != str(viewer_doctor_id) and not may_read_note(viewer_department, department):
        return dict(RESTRICTED_REVIEWER)
    return {"name": name, "department": department}


def review_states(document_ids, viewer_doctor_id: str, viewer_department: str | None) -> dict[str, dict]:
    """The review state of each document, as `viewer_doctor_id` may see it.

    {document_id: {"status", "verified_by": [...], "flagged_by": [...], "mine"}}, where
    `mine` is the viewer's own position ("verified", "flagged" or None) — what decides which
    buttons they get. Every requested id gets a state, "unverified" when nobody reviewed it.
    """
    ids = [str(document_id) for document_id in dict.fromkeys(document_ids or []) if document_id]
    return merged_review_states({document_id: [document_id] for document_id in ids},
                                viewer_doctor_id, viewer_department)


def merged_review_states(groups: dict[str, list[str]], viewer_doctor_id: str,
                         viewer_department: str | None) -> dict[str, dict]:
    """One review state per GROUP of documents — the copies of one report, uploaded more
    than once ("report.pdf", "report (1).pdf"). A doctor who verified the copy they opened
    has verified the report: the state shown for it is every copy's, each doctor named once.
    A report anyone flagged on any copy is flagged. Same shape as review_states, keyed by
    group; `mine` is "flagged" over "verified" when the viewer took both positions.

    `earlier`: positions taken on an earlier version of the summary, before the document was
    re-processed, by doctors with no position on the current one — {name, department,
    action ("verified"/"flagged"), at, reason}. Not part of the status: they no longer apply
    to what is on screen. Kept so that history never silently loses a verification.
    """
    states = {
        key: {"status": STATUS_UNVERIFIED, "verified_by": [], "flagged_by": [], "mine": None, "earlier": []}
        for key in groups
    }
    # A document may belong to SEVERAL groups: when two copies of one report are both listed
    # (copy_groups gives each its whole copy list), each copy's group holds both. Every
    # review counts toward every group that holds its document — mapping each document to
    # one group showed one copy verified and the other, the same report, unverified.
    groups_of: dict[str, list] = {}
    for key, ids in groups.items():
        for document_id in ids:
            groups_of.setdefault(str(document_id), []).append(key)
    if not groups_of:
        return states

    with connect_db() as conn:
        with conn.cursor() as cur:
            rows = _current_positions(cur, list(groups_of))
            earlier_rows = _earlier_positions(cur, list(groups_of))
        conn.commit()

    current_doctors = {(key, str(row[1])) for row in rows for key in groups_of[str(row[0])]}
    earlier_seen: set[tuple] = set()
    for document_id, doctor_id, name, department, action, reason, created_at, _version in earlier_rows:
        for key in groups_of[str(document_id)]:
            if (key, str(doctor_id)) in current_doctors or (key, str(doctor_id)) in earlier_seen:
                continue
            earlier_seen.add((key, str(doctor_id)))
            states[key]["earlier"].append({
                **_reviewer(doctor_id, name, department, viewer_doctor_id, viewer_department),
                "action": "verified" if action == "verified" else "flagged",
                "reason": reason if action != "verified" else None,
                "at": created_at.isoformat() if created_at else None,
                "is_me": str(doctor_id) == str(viewer_doctor_id),
            })

    seen: set[tuple] = set()
    for document_id, doctor_id, name, department, action, reason, created_at in rows:
        for key in groups_of[str(document_id)]:
            if (key, str(doctor_id), action) in seen:
                continue
            seen.add((key, str(doctor_id), action))
            state = states[key]
            person = {
                **_reviewer(doctor_id, name, department, viewer_doctor_id, viewer_department),
                "at": created_at.isoformat() if created_at else None,
                "is_me": str(doctor_id) == str(viewer_doctor_id),
            }
            if action == "verified":
                state["verified_by"].append(person)
            else:
                state["flagged_by"].append({**person, "reason": reason})
            if person["is_me"] and state["mine"] != "flagged":
                state["mine"] = "verified" if action == "verified" else "flagged"

    for state in states.values():
        state["status"] = (
            STATUS_FLAGGED if state["flagged_by"]
            else STATUS_VERIFIED if state["verified_by"]
            else STATUS_UNVERIFIED
        )
    return states


def record_review(
    doctor_id: str, patient_id: str, document_id: str, verb: str,
    reason: str | None = None, viewer_department: str | None = None,
) -> dict:
    """Records one doctor's action on one document, and returns its new state.

    Raises ValueError for an unknown action or an unusable reason (422), ReviewConflict when
    the action does not fit this doctor's current position (409). Verifying twice is not a
    conflict — it is already true, so nothing is written.
    """
    action = ACTIONS.get(str(verb or ""))
    if action is None:
        raise ValueError("Unknown review action.")
    reason = " ".join(str(reason or "").split()) or None
    if action == "flagged_inaccurate":
        if not reason or len(reason) < REASON_MIN_CHARS:
            raise ValueError("Say what is inaccurate, so other doctors know what to check.")
        if len(reason) > REASON_MAX_CHARS:
            raise ValueError(f"Keep the reason under {REASON_MAX_CHARS} characters.")
    else:
        reason = None

    from app.services.consults import ensure_consult_schema

    with connect_db() as conn:
        ensure_consult_schema(conn)  # consult_audit_log; once per process
        with conn.cursor() as cur:
            cur.execute(
                "SELECT generated_at FROM document_summaries WHERE document_id = %s",
                (document_id,),
            )
            row = cur.fetchone()
            summary_generated_at = row[0] if row else None

            cur.execute(
                """SELECT action FROM document_reviews
                   WHERE document_id = %s AND doctor_id = %s
                     AND summary_generated_at IS NOT DISTINCT FROM %s
                   ORDER BY review_seq DESC LIMIT 1""",
                (document_id, doctor_id, summary_generated_at),
            )
            latest = cur.fetchone()
            mine = latest[0] if latest else None

            if action == "withdrawn" and mine != "verified":
                raise ReviewConflict("You have not verified this document.")
            if action == "flag_cleared" and mine != "flagged_inaccurate":
                raise ReviewConflict("You have not reported this document.")

            # Repeating the position you already hold writes nothing — except a report,
            # whose new reason replaces the old one.
            if mine != action or action == "flagged_inaccurate":
                cur.execute(
                    """INSERT INTO document_reviews
                           (document_id, patient_id, doctor_id, action, reason, summary_generated_at)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (document_id, patient_id, doctor_id, action, reason, summary_generated_at),
                )
                # Audited in the SAME transaction: a review with no audit row, or an audit
                # row for a review that was rolled back, would both misstate the record.
                cur.execute(
                    """INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata)
                       VALUES (NULL, %s, %s, %s::jsonb)""",
                    (doctor_id, _AUDIT_ACTIONS[action], json.dumps({
                        "document_id": document_id, "patient_id": patient_id,
                        **({"reason": reason} if reason else {}),
                    })),
                )
        conn.commit()

    logger.info("document_reviews: doctor=%s %s document=%s", doctor_id, action, document_id)
    return review_states([document_id], doctor_id, viewer_department)[document_id]
