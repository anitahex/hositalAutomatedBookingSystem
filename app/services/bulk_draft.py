"""The "Draft all missing notes" bulk action on the review inbox (plan §4.5).

One click here triggers one LLM call per undrafted consult, which makes this the most
expensive button in the application. It is therefore bounded on every axis the standards
require (engineering-standards.md §Scalability, §Reliability):

  - BOUNDED BATCH. At most BULK_DRAFT_MAX_ITEMS consults per call, taken in the queue's own
    priority order, however many are outstanding.
  - RATE LIMITED. Reuses the existing Postgres-backed sliding-window limiter
    (doctor_auth.check_rate_limit) under its own 'bulk_draft' scope, rather than adding a
    second limiter. That one is already correct across multiple workers, which an
    in-process counter would not be.
  - IDEMPOTENT. Selects only consults that have NO note at all. Running it twice in a row
    drafts nothing the second time, because the first run's notes now exist. This is the
    property that makes the button safe to double-click, safe to retry on a dropped
    connection, and safe to fire from two tabs.
  - SEQUENTIAL. Deliberately not concurrent. These are LLM calls against a shared quota;
    a fan-out of ten would trade a bounded, predictable cost for a burst that could
    exhaust it. One at a time, with per-item failure isolation.
  - FAILURE ISOLATED. One consult failing to draft does not abort the batch or roll back
    the notes already written; it is reported as a failure for that item and the run
    continues.

It NEVER touches an existing note. A draft the doctor has been editing, a stale note, and
a signed note are all simply not selected — regeneration stays an explicit, per-note,
doctor-initiated action, because silently replacing in-progress work from a bulk button
would be a data-loss bug.
"""
from __future__ import annotations

import logging

from app.db.connection import connect_db
from app.services.doctor_workspace import BULK_DRAFT_MAX_ITEMS

logger = logging.getLogger(__name__)

# Per-doctor budget. Deliberately tighter than the auth limiter's default: this is an
# expensive, deliberate action, not something a doctor does in a loop.
BULK_DRAFT_RATE_LIMIT = 3
BULK_DRAFT_RATE_WINDOW_SECONDS = 300


def _select_undrafted(cur, doctor_id: str, limit: int) -> list[tuple[str, str]]:
    """Consults of this doctor's that are ready to draft and have no note at all.

    `sn.id IS NULL` is the idempotency key: a consult that already has a note in ANY state
    is excluded, so a repeat run selects nothing. Ordered oldest-appointment-first to match
    the review queue's own ordering, so the bulk action works through the backlog in the
    same order the doctor sees it.
    """
    cur.execute(
        """
        SELECT c.id, c.booking_id
        FROM consultations c
        JOIN appointment_bookings b ON b.booking_id = c.booking_id
        LEFT JOIN soap_notes sn ON sn.consultation_id = c.id
        WHERE c.doctor_id = %s
            AND c.status = 'transcript_ready'
            AND sn.id IS NULL
        ORDER BY b.start_time ASC
        LIMIT %s
        """,
        (doctor_id, limit),
    )
    return [(str(row[0]), str(row[1])) for row in cur.fetchall()]


async def draft_all_missing_notes(doctor_id: str, ip: str, style: str = "concise") -> dict:
    """Drafts a note for up to BULK_DRAFT_MAX_ITEMS of this doctor's undrafted consults.

    Returns {"drafted": [...], "failed": [...], "attempted": n, "remaining": n} — per-item
    results, never a bare success. `remaining` tells the doctor whether the batch cap left
    work behind, so the cap is visible rather than silently truncating.

    Raises PermissionError when rate limited.
    """
    from app.services.appointments import ensure_booking_schema
    from app.services.consults import ensure_consult_schema
    from app.services.doctor_auth import check_rate_limit
    from app.services.soap_notes import ensure_soap_schema, generate_soap_note

    try:
        check_rate_limit(
            "bulk_draft", ip, str(doctor_id),
            limit=BULK_DRAFT_RATE_LIMIT, window_seconds=BULK_DRAFT_RATE_WINDOW_SECONDS,
        )
    except PermissionError:
        # The shared limiter's message talks about authentication attempts, which would be
        # wrong and confusing here. Re-raised with this action's own wording.
        raise PermissionError(
            "Too many bulk drafting requests. Please wait a few minutes before trying again."
        )

    with connect_db() as conn:
        ensure_booking_schema(conn)
        ensure_consult_schema(conn)
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            targets = _select_undrafted(cur, doctor_id, BULK_DRAFT_MAX_ITEMS)
            # Counted separately from the capped selection so "remaining" is honest about
            # how much work the cap left behind.
            cur.execute(
                """
                SELECT COUNT(*)
                FROM consultations c
                LEFT JOIN soap_notes sn ON sn.consultation_id = c.id
                WHERE c.doctor_id = %s AND c.status = 'transcript_ready' AND sn.id IS NULL
                """,
                (doctor_id,),
            )
            total_outstanding = int(cur.fetchone()[0])

    drafted: list[dict] = []
    failed: list[dict] = []

    for consultation_id, booking_id in targets:
        try:
            # generate_soap_note re-checks ownership and transcript readiness itself, so
            # this loop never widens access on the strength of the selection query alone.
            await generate_soap_note(consultation_id, doctor_id, style)
            drafted.append({"consultation_id": consultation_id, "booking_id": booking_id})
        except Exception as exc:
            # Isolated per item: the notes already written stay written. The reason is
            # logged rather than returned, because it can carry model/storage internals.
            logger.warning(
                "bulk_draft: could not draft consult=%s for doctor=%s: %s",
                consultation_id, doctor_id, exc,
            )
            failed.append({
                "consultation_id": consultation_id,
                "booking_id": booking_id,
                "error": "This note could not be drafted. Open the consult and try again.",
            })

    return {
        "attempted": len(targets),
        "drafted": drafted,
        "failed": failed,
        "remaining": max(0, total_outstanding - len(drafted)),
        "batch_limit": BULK_DRAFT_MAX_ITEMS,
    }
