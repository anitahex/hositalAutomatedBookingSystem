"""Doctor-facing AI activity: the "what did AI do since you were last here?" summary and
the timestamped activity feed (plan §4.1 and §4.3).

Read-only. Nothing in this module writes clinical data; it reports what already happened.

Authorization: every query here filters by doctor_id IN THE SQL, exactly as every other
doctor_* query in this codebase does (soap_notes.list_reviews_for_doctor,
appointments.doctor_appointments). Nothing is post-filtered in Python, so a doctor can no
more reach another doctor's activity than they can reach their appointments. The counts
that reach across to patient documents are additionally constrained by the same
treating-relationship rule as document_catalog — an actual booking history.

The feed is NOT the raw audit log. consult_audit_log.metadata is free-form JSONB written
by a dozen call sites; returning it wholesale would disclose whatever any of them happens
to put there, now or in future. Every event below is projected through an explicit
per-action allowlist (_FEED_ACTIONS), and an action_type not in that map is dropped rather
than passed through with a generic label.

Timezone: this stack runs with naive timestamps authored as India-local, with both
Postgres and the app pinned to Asia/Kolkata (see docker-compose.yml). Every comparison
here stays inside the database and uses NOW(), so it inherits that convention rather than
introducing a second one. document_catalog.created_at is TIMESTAMPTZ while the rest are
naive TIMESTAMP; Postgres casts the naive bound using the session timezone, which is the
same Asia/Kolkata, so the windows agree.
"""
from __future__ import annotations

from app.db.connection import connect_db

# Mirrors the limit discipline of soap_notes.REVIEW_* and appointments' doctor_* queries:
# a doctor's activity feed is bounded per-doctor work, never an unbounded scan.
ACTIVITY_LOG_DEFAULT_LIMIT = 25
ACTIVITY_LOG_MAX_LIMIT = 100

# Fallback window when an account has no previous login recorded (its first ever login,
# or an account that predates previous_login_at). Specified by plan §4.1.
DEFAULT_WINDOW_HOURS = 24

# The windows the doctor can ask for. "last_visit" is the previous_login_at window; the
# other two are fixed durations measured against the database clock.
WINDOW_LAST_VISIT = "last_visit"
ACTIVITY_WINDOWS = (WINDOW_LAST_VISIT, "24h", "7d")
DEFAULT_WINDOW = WINDOW_LAST_VISIT
_WINDOW_HOURS = {"24h": 24, "7d": 24 * 7}

# A "last visit" shorter than this is not a visit — it is the same person signing back in.
# Without this floor, logging out and straight back in makes previous_login_at a few
# minutes ago, every count inside that window is legitimately 0, and the overview reads as
# blank when plenty has actually happened. Observed in the running app: previous_login_at
# 15:24:56 against last_login_at 15:27:36, a 2m40s window.
#
# Deliberately the SAME number as doctor_auth.SESSION_GROUPING_MINUTES, which stops most
# of these at the source by not advancing previous_login_at for a quick re-login. Keeping
# them equal means one definition of a visit boundary rather than two: a gap that is not
# long enough to START a new visit is not long enough to REPORT one either. This is the
# second line of defence, and it also covers rows written before that rule existed.
# test_doctor_activity_window.py pins the two together.
MIN_LAST_VISIT_MINUTES = 30

# Which audit actions appear on the feed, and how each is described to the doctor.
#
# `ai` marks whether the actor was the model or the doctor. The feed shows both, because
# the §4.11 audit trail is exactly the story of "AI drafted -> you signed -> you shared",
# and showing only the AI half would make the doctor's own acts invisible in their own
# audit trail. `fields` is the allowlist of metadata keys that may be surfaced for that
# action — anything else in the row's metadata is dropped.
_FEED_ACTIONS = {
    "consult_soap_note_generated": {
        "label": "Drafted a clinical note",
        "ai": True,
        # NOT ai_model / ai_prompt_version. Which model wrote a note is recorded in the
        # audit row and on soap_notes, and stays there — but it is not shown to the
        # doctor, so it is not sent to the browser either. Dropping it here means the
        # allowlist enforces that, rather than relying on the UI choosing not to render
        # a field it was handed.
        "fields": ("style",),
    },
    "consult_soap_note_held_back": {
        "label": "Held a note back for regeneration",
        "ai": True,
        "fields": ("reason",),
    },
    "consult_soap_note_signed": {
        "label": "You reviewed and signed the note",
        "ai": False,
        "fields": (),
    },
    "consult_soap_note_shared": {
        "label": "You shared the note with the patient",
        "ai": False,
        "fields": (),
    },
    "consult_soap_note_edited": {
        "label": "You edited the draft",
        "ai": False,
        "fields": ("fields",),
    },
    "consult_soap_note_addendum_added": {
        "label": "You added an addendum",
        "ai": False,
        "fields": (),
    },
    "consult_soap_section_verified": {
        "label": "You marked a section verified",
        "ai": False,
        "fields": ("section",),
    },
    "patient_document_summarised": {
        "label": "Summarised a patient document",
        "ai": True,
        "fields": ("document_id",),
    },
    # A discarded consult keeps its drafted note, so without this the feed showed "Drafted a
    # clinical note" for a note the doctor could then find nowhere — half a story, with the
    # half that explains it recorded in the audit log and dropped here.
    "consult_discarded": {
        "label": "You discarded the consult",
        "ai": False,
        "fields": (),
    },
    # A doctor's review of a patient document (document_reviews). Recorded in the audit table
    # since that feature shipped, but absent from this allowlist, so a doctor who verified a
    # document could find no trace of it in their own audit log.
    "document_verified": {
        "label": "You verified a document",
        "ai": False,
        "fields": ("document_id",),
    },
    "document_verification_withdrawn": {
        "label": "You withdrew your verification",
        "ai": False,
        "fields": ("document_id",),
    },
    "document_flagged_inaccurate": {
        "label": "You reported a document inaccurate",
        "ai": False,
        # The doctor's own words about the document, shown back to that same doctor.
        "fields": ("document_id", "reason"),
    },
    "document_flag_cleared": {
        "label": "You cleared your inaccuracy report",
        "ai": False,
        "fields": ("document_id",),
    },
    # The AI nutritionist (nutrition_plan): what the doctor did with its suggestions.
    "nutrition_theme_discussed": {
        "label": "You discussed a nutrition topic",
        "ai": False,
        "fields": ("theme_title",),
    },
    "nutrition_theme_discussion_withdrawn": {
        "label": "You withdrew a nutrition discussion",
        "ai": False,
        "fields": ("theme_title",),
    },
    "nutrition_handout_created": {
        "label": "You created a nutrition handout",
        "ai": False,
        "fields": ("diet",),
    },
}

# The feed actions whose metadata names a patient document: their rows open the document.
_DOCUMENT_ACTIONS = {
    "patient_document_summarised", "document_verified", "document_verification_withdrawn",
    "document_flagged_inaccurate", "document_flag_cleared",
}


def _window_lower_bound(account_id: str):
    """The doctor's previous login, or None if they have none.

    Deliberately its OWN sequential connect_db() block, fully committed before the caller
    opens the connection it runs the counts on — NOT a cursor passed in from that block.

    This is the same lock-ordering discipline check_rate_limit already documents, and it
    is load-bearing rather than stylistic. Reading doctor_accounts inside the transaction
    that has just run ensure_booking_schema/ensure_consult_schema/ensure_soap_schema means
    holding table locks on the consult tables while asking for a lock on doctor_accounts.
    The authentication path (get_doctor_profile -> ensure_doctor_auth_schema) does the
    reverse: it holds doctor_accounts and reaches for its own tables. Two requests
    overlapping in that order deadlock, which is not hypothetical — it was caught in the
    running application:

        psycopg2.errors.DeadlockDetected: deadlock detected
        Process A waits for AccessShareLock ... blocked by process B;
        Process B waits for AccessShareLock ... blocked by process A.

    Sequential, not nested: the block below is closed before the caller opens its own, so
    this never reuses a connection the caller is already holding (the pool is keyed by
    thread id — see the hazard documented in soap_notes.update_soap_note).
    """
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT previous_login_at FROM doctor_accounts WHERE id = %s", (account_id,)
            )
            row = cur.fetchone()
        conn.commit()
    return row[0] if row else None


# ---- The four tiles' predicates ----
#
# Each tile's number and the list behind it are built from the SAME fragment below. That
# is the whole point of keeping them here rather than inline: a doctor who clicks "1" and
# is shown two rows has been told something false by one of them, and nothing would say
# which. With one fragment per tile, the count and the list cannot drift apart without
# someone editing the fragment itself — and test_doctor_activity_items reconciles every
# tile's list against its count in every window, so that edit would be caught.
#
# Named parameters throughout: %(doctor_id)s and %(since)s.

_DRAFTED_WHERE = """
    a.doctor_id = %(doctor_id)s
    AND a.created_at >= %(since)s
    AND a.action_type = 'consult_soap_note_generated'
"""

# Documents belonging to this doctor's patients that finished processing inside the
# window. See the count below for why this is the catalog and not the audit log.
_DOCUMENTS_WHERE = """
    dc.ingestion_status = 'complete'
    AND dc.created_at >= %(since)s
    AND EXISTS (
        SELECT 1 FROM appointment_bookings b
        WHERE b.doctor_id = %(doctor_id)s AND b.patient_id = dc.user_id
    )
"""

_FLAGGED_WHERE = """
    sn.doctor_id = %(doctor_id)s AND sn.generated_at >= %(since)s
"""

# The four real sections only, so a stray key in confidence_flags cannot inflate the
# count. The order is the order they are listed to the doctor.
FLAG_SECTIONS = ("subjective", "objective", "assessment", "plan")
_FLAG_SUM = " + ".join(
    f"(CASE WHEN sn.confidence_flags->>'{section}' = 'true' THEN 1 ELSE 0 END)"
    for section in FLAG_SECTIONS
)

# Current state, not windowed — see get_activity_summary's docstring. The join on the
# consult's status is what keeps a discarded consult's leftover note out of this.
_BLOCKED_WHERE = """
    sn.doctor_id = %(doctor_id)s AND c.status = 'transcript_ready'
"""

ACTIVITY_TILES = ("notes_drafted", "documents_summarized", "fields_flagged", "notes_blocked")
ACTIVITY_ITEMS_DEFAULT_LIMIT = 50
ACTIVITY_ITEMS_MAX_LIMIT = 100


def _resolve_window(cur, since, window: str) -> tuple:
    """(window_start, used_fixed_window) against the database clock.

    Shared by the summary and the drill-down lists so the two can never measure from
    different starting points — the tile and its list are only comparable if they agree
    on when the period began.

    Resolved inside SQL so the bound is computed against the database clock, the same one
    every created_at below was written with. make_interval(), not INTERVAL '%s hours': a
    placeholder inside a quoted literal is a well-known psycopg2 footgun, and this keeps it
    a real parameter.

    Two cases take the fixed window: no previous login at all, and a previous login so
    recent it is the same session (MIN_LAST_VISIT_MINUTES). The second value reports which
    branch ran, so the caller states the window it actually got rather than the one it
    asked for.

    The ::timestamp on the CASE is load-bearing. NOW() is timestamptz, so without it
    Postgres unifies the branches to timestamptz and window_start comes back tz-aware —
    every other timestamp in this module is naive India-local (see the module docstring),
    and mixing the two raises on the first comparison.
    """
    cur.execute(
        """
        SELECT
            (CASE WHEN %(since)s::timestamp IS NULL
                       OR %(since)s::timestamp > NOW() - make_interval(mins => %(floor_mins)s)
                  THEN NOW() - make_interval(hours => %(hours)s)
                  ELSE %(since)s::timestamp
             END)::timestamp,
            (%(since)s::timestamp IS NULL
             OR %(since)s::timestamp > NOW() - make_interval(mins => %(floor_mins)s))
        """,
        {
            "since": since,
            "hours": _WINDOW_HOURS.get(window, DEFAULT_WINDOW_HOURS),
            # A fixed window has no floor to apply; `since` is already NULL there.
            "floor_mins": MIN_LAST_VISIT_MINUTES if window == WINDOW_LAST_VISIT else 0,
        },
    )
    return cur.fetchone()


def get_activity_summary(doctor_id: str, account_id: str, window: str = DEFAULT_WINDOW) -> dict:
    """Counts of what AI did for this doctor over `window` (plan §4.1).

    `window` is one of ACTIVITY_WINDOWS. "last_visit" measures from previous_login_at; the
    others are fixed durations. An unknown value raises ValueError rather than quietly
    falling back, so a typo in a caller cannot silently change what a clinical figure
    counts.

    Every number is measured, never estimated. Where the underlying data cannot support a
    count it reports zero rather than a plausible-looking figure.

    `notes_blocked` is deliberately CURRENT STATE, not a windowed event count: it answers
    "how many of my notes are stuck right now", which is what the doctor must act on. The
    other three are genuine within-window event counts, and only those three move when the
    window changes.
    """
    from app.services.appointments import ensure_booking_schema
    from app.services.consults import ensure_consult_schema
    from app.services.soap_notes import ensure_soap_schema

    if window not in ACTIVITY_WINDOWS:
        raise ValueError(f"window must be one of {ACTIVITY_WINDOWS}.")

    # Only the last_visit window consults the account row at all — a fixed window needs no
    # login history, so it must not fail or vary because of one.
    #
    # Read FIRST, in its own committed transaction, before the block below takes any lock
    # on the consult tables. See _window_lower_bound for why the ordering matters.
    since = _window_lower_bound(account_id) if window == WINDOW_LAST_VISIT else None

    with connect_db() as conn:
        ensure_booking_schema(conn)
        ensure_consult_schema(conn)
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            window_start, used_fixed_window = _resolve_window(cur, since, window)
            params = {"doctor_id": doctor_id, "since": window_start}

            cur.execute(
                f"SELECT COUNT(*) FROM consult_audit_log a WHERE {_DRAFTED_WHERE}", params
            )
            notes_drafted = cur.fetchone()[0]

            # Counted from the catalog rather than the audit log because summarisation
            # happens on the patient's upload path, where no doctor is the actor — so there
            # is no doctor-attributed audit row to count. Scoped by the same
            # treating-relationship rule document_catalog enforces (a real booking history).
            # DISTINCT is belt-and-braces: EXISTS already cannot multiply rows, and
            # document_id is the primary key.
            cur.execute(
                f"SELECT COUNT(DISTINCT dc.document_id) FROM document_catalog dc WHERE {_DOCUMENTS_WHERE}",
                params,
            )
            documents_summarized = int(cur.fetchone()[0])

            # confidence_flags maps a field to True when the model was NOT confident (see
            # soap_notes._low_confidence_count).
            cur.execute(
                f"SELECT COALESCE(SUM({_FLAG_SUM}), 0) FROM soap_notes sn WHERE {_FLAGGED_WHERE}",
                params,
            )
            fields_flagged = int(cur.fetchone()[0])

            # Current state, not a windowed count — see this function's docstring.
            cur.execute(
                f"""
                SELECT COUNT(*) FILTER (WHERE sn.status = 'stale'),
                       COUNT(*) FILTER (WHERE sn.status IN ('draft', 'stale'))
                FROM soap_notes sn
                JOIN consultations c ON c.id = sn.consultation_id
                WHERE {_BLOCKED_WHERE}
                """,
                params,
            )
            notes_blocked, awaiting_signature = cur.fetchone()

    counts = {
        "notes_drafted": int(notes_drafted or 0),
        "documents_summarized": documents_summarized,
        "fields_flagged": fields_flagged,
        "notes_blocked": int(notes_blocked or 0),
        "awaiting_signature": int(awaiting_signature or 0),
    }

    from app.services.doctor_workspace import summarize_activity

    # Only a REQUESTED last_visit that could not be honoured is a fallback. Asking for 24h
    # and getting 24h is not, even though both resolve through the same SQL branch — so
    # the UI never says "last 24 hours (we could not find your last visit)" to someone who
    # chose 24 hours.
    is_fallback = bool(used_fixed_window) and window == WINDOW_LAST_VISIT

    return {
        "window_start": window_start.isoformat() if window_start else None,
        # What was asked for, and what was actually applied. They differ only on a
        # fallback, and the UI labels the panel from `window` so it can never claim a
        # session boundary that does not exist.
        "window_requested": window,
        "window": "24h" if is_fallback else window,
        "window_is_fallback": is_fallback,
        "counts": counts,
        "headline": summarize_activity(counts),
    }


# Everything a note-backed row needs so the UI can open it on the existing appointment
# detail screen (openReviewFromQueue synthesises the same shape from a review row). LEFT
# JOINs throughout: every join is one-to-one (soap_notes.consultation_id and
# patient_profiles.user_id are unique), so they can never add rows, and a LEFT JOIN means a
# missing profile cannot silently remove one — either would break the list's agreement with
# its tile.
_CONSULT_ITEM_COLUMNS = """
    c.id, c.booking_id, c.patient_id, c.status, c.ended_at,
    b.start_time, d.department, pp.name, sn.status
"""
_CONSULT_ITEM_JOINS = """
    LEFT JOIN appointment_bookings b ON b.booking_id = c.booking_id
    LEFT JOIN doctors d ON d.doctor_id = c.doctor_id
    LEFT JOIN patient_profiles pp ON pp.user_id::text = c.patient_id
"""


def _consult_item(row) -> dict:
    (consultation_id, booking_id, patient_id, consult_status, ended_at,
     start_time, department, patient_name, note_status) = row
    return {
        "consultation_id": str(consultation_id) if consultation_id else None,
        "booking_id": str(booking_id) if booking_id else None,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "department": department,
        "appointment_start": start_time.isoformat() if start_time else None,
        "consult_status": consult_status,
        "consult_ended_at": ended_at.isoformat() if ended_at else None,
        "note_status": note_status,
        # A discarded consult keeps its note row (discard_consult deletes the transcript
        # only), but every screen that shows a consult filters discarded ones out, so there
        # is nowhere to open it. Saying so is better than a link that lands on nothing.
        "openable": bool(booking_id) and consult_status != "discarded",
    }


def get_activity_items(
    doctor_id: str,
    account_id: str,
    window: str,
    tile: str,
    limit: int = ACTIVITY_ITEMS_DEFAULT_LIMIT,
) -> dict:
    """What is behind one of the four tiles: the rows that make up its number.

    Built from the same predicate as the tile (_DRAFTED_WHERE and friends) and measured
    from the same window (_resolve_window), so the list reconciles with the count:

      notes_drafted         one row per draft EVENT — regenerating a note three times is
                            three rows, because the tile counts three
      documents_summarized  one row per document
      fields_flagged        one row per note with at least one flag; the tile is the sum
                            of each row's len(flagged_sections)
      notes_blocked         one row per held-back note (current state, as the tile is)

    Listing, not content: patient names, times and statuses, never note text or document
    findings. Same rule as the other list endpoints — content reads are audited, lists
    are not — so opening a row goes through the existing audited routes.

    Patient names ARE included, unlike the activity feed. The feed renders on the
    dashboard unprompted; this renders only when the doctor asks for it, and a list of
    their own patients' notes is useless without saying whose they are. The appointment
    and review lists already show names on the same basis.
    """
    from app.services.appointments import ensure_booking_schema
    from app.services.consults import ensure_consult_schema
    from app.services.soap_notes import ensure_soap_schema

    if window not in ACTIVITY_WINDOWS:
        raise ValueError(f"window must be one of {ACTIVITY_WINDOWS}.")
    if tile not in ACTIVITY_TILES:
        raise ValueError(f"tile must be one of {ACTIVITY_TILES}.")
    limit = max(1, min(int(limit), ACTIVITY_ITEMS_MAX_LIMIT))

    # Same ordering discipline as get_activity_summary: the account row is read in its own
    # committed transaction before any consult-table lock is taken.
    since = _window_lower_bound(account_id) if window == WINDOW_LAST_VISIT else None

    with connect_db() as conn:
        ensure_booking_schema(conn)
        ensure_consult_schema(conn)
        ensure_soap_schema(conn)
        with conn.cursor() as cur:
            window_start, used_fixed_window = _resolve_window(cur, since, window)
            # limit + 1 so truncation is detected rather than guessed from len == limit.
            params = {"doctor_id": doctor_id, "since": window_start, "limit": limit + 1}

            if tile == "notes_drafted":
                cur.execute(
                    f"""
                    SELECT a.created_at, a.metadata->>'style', {_CONSULT_ITEM_COLUMNS}
                    FROM consult_audit_log a
                    LEFT JOIN consultations c ON c.id = a.consultation_id
                    LEFT JOIN soap_notes sn ON sn.consultation_id = c.id
                    {_CONSULT_ITEM_JOINS}
                    WHERE {_DRAFTED_WHERE}
                    ORDER BY a.created_at DESC
                    LIMIT %(limit)s
                    """,
                    params,
                )
                items = [
                    {
                        **_consult_item(row[2:]),
                        "occurred_at": row[0].isoformat() if row[0] else None,
                        # Allowlisted the same way the feed allowlists it: a known value or
                        # nothing, never whatever the metadata happens to hold.
                        "style": row[1] if row[1] in ("concise", "detailed") else None,
                    }
                    for row in cur.fetchall()
                ]

            elif tile == "documents_summarized":
                cur.execute(
                    f"""
                    SELECT dc.document_id, dc.original_filename, dc.document_type,
                           dc.clinical_date, dc.created_at, dc.user_id, pp.name,
                           ds.verification
                    FROM document_catalog dc
                    LEFT JOIN patient_profiles pp ON pp.user_id::text = dc.user_id
                    LEFT JOIN document_summaries ds ON ds.document_id = dc.document_id
                    WHERE {_DOCUMENTS_WHERE}
                    ORDER BY dc.created_at DESC
                    LIMIT %(limit)s
                    """,
                    params,
                )
                from app.services.document_catalog import _content_type_for

                items = [
                    {
                        "document_id": document_id,
                        "original_filename": filename or document_id,
                        "document_type": document_type or "other",
                        "clinical_date": str(clinical_date) if clinical_date else None,
                        "uploaded_at": created_at.isoformat() if created_at else None,
                        # The viewer decides how to render from the bytes, but it reads
                        # this to label the file — same field the documents list sends.
                        "content_type": _content_type_for(filename),
                        "patient_id": patient_id,
                        "patient_name": patient_name,
                        # Whether a verified clinician summary exists: 'passed', 'partial',
                        # 'failed', or None when none was ever produced.
                        "summary_verification": verification,
                        "openable": True,
                    }
                    for (document_id, filename, document_type, clinical_date, created_at,
                         patient_id, patient_name, verification) in cur.fetchall()
                ]

            elif tile == "fields_flagged":
                flag_columns = ", ".join(
                    f"(sn.confidence_flags->>'{section}' = 'true')" for section in FLAG_SECTIONS
                )
                cur.execute(
                    f"""
                    SELECT sn.generated_at, {flag_columns}, {_CONSULT_ITEM_COLUMNS}
                    FROM soap_notes sn
                    LEFT JOIN consultations c ON c.id = sn.consultation_id
                    {_CONSULT_ITEM_JOINS}
                    WHERE {_FLAGGED_WHERE} AND ({_FLAG_SUM}) > 0
                    ORDER BY sn.generated_at DESC
                    LIMIT %(limit)s
                    """,
                    params,
                )
                offset = 1 + len(FLAG_SECTIONS)
                items = [
                    {
                        **_consult_item(row[offset:]),
                        "occurred_at": row[0].isoformat() if row[0] else None,
                        "flagged_sections": [
                            section for section, flagged
                            in zip(FLAG_SECTIONS, row[1:offset]) if flagged
                        ],
                    }
                    for row in cur.fetchall()
                ]

            else:  # notes_blocked
                cur.execute(
                    f"""
                    SELECT sn.generated_at, {_CONSULT_ITEM_COLUMNS}
                    FROM soap_notes sn
                    JOIN consultations c ON c.id = sn.consultation_id
                    {_CONSULT_ITEM_JOINS}
                    WHERE {_BLOCKED_WHERE} AND sn.status = 'stale'
                    ORDER BY sn.generated_at DESC
                    LIMIT %(limit)s
                    """,
                    params,
                )
                items = [
                    {
                        **_consult_item(row[1:]),
                        "occurred_at": row[0].isoformat() if row[0] else None,
                    }
                    for row in cur.fetchall()
                ]

    truncated = len(items) > limit
    return {
        "tile": tile,
        "window_requested": window,
        "window": "24h" if (bool(used_fixed_window) and window == WINDOW_LAST_VISIT) else window,
        "window_start": window_start.isoformat() if window_start else None,
        "items": items[:limit],
        "truncated": truncated,
    }


def _project_event(action_type: str, metadata, created_at, consultation_id, consult_row=None,
                   document_row=None) -> dict | None:
    """Projects one audit row onto the feed through the per-action allowlist. Returns None
    for an action that does not belong on the feed.

    `consult_row` is the _CONSULT_ITEM_COLUMNS tuple for the event's consult, when it has
    one; it adds what the UI needs to open that appointment (see get_activity_log).
    `document_row` is _DOCUMENT_COLUMNS for an event about a patient document: it names the
    file and lets the row open it in the viewer."""
    spec = _FEED_ACTIONS.get(action_type)
    if spec is None:
        return None

    safe_metadata = {}
    if isinstance(metadata, dict):
        # Allowlist, not denylist: a key nobody anticipated is dropped, not surfaced.
        safe_metadata = {key: metadata[key] for key in spec["fields"] if key in metadata}

    event = {
        "action": action_type,
        "label": spec["label"],
        "is_ai": spec["ai"],
        "consultation_id": str(consultation_id) if consultation_id else None,
        "occurred_at": created_at.isoformat() if created_at else None,
        "detail": safe_metadata,
        "openable": False,
    }
    if consultation_id and consult_row is not None and consult_row[0] is not None:
        # Same shape as the drill-down rows, so the UI opens both with one function.
        # The consultation_id from the audit row stays authoritative.
        event.update({key: value for key, value in _consult_item(consult_row).items()
                      if key != "consultation_id"})
    if action_type in _DOCUMENT_ACTIONS and document_row is not None and document_row[0] is not None:
        from app.services.document_catalog import _content_type_for

        document_id, filename, document_type, clinical_date, patient_id = document_row
        event["document"] = {
            "document_id": str(document_id),
            "original_filename": filename or str(document_id),
            "document_type": document_type or "other",
            "clinical_date": clinical_date.isoformat() if hasattr(clinical_date, "isoformat") else clinical_date,
            "patient_id": str(patient_id) if patient_id else None,
            "content_type": _content_type_for(filename),
        }
        event["openable"] = bool(patient_id)
    return event


# The patient document an audit row names, for the document actions. document_catalog's key
# is TEXT; the audit metadata stores it as text too.
_DOCUMENT_COLUMNS = "dc.document_id, dc.original_filename, dc.document_type, dc.clinical_date, dc.user_id"


def get_activity_log(doctor_id: str, limit: int = ACTIVITY_LOG_DEFAULT_LIMIT) -> dict:
    """This doctor's own AI/clinical activity feed, newest first (plan §4.3).

    Reads consult_audit_log — which has recorded every clinical action in this codebase
    since revision 0007 — rather than introducing a parallel event source. Scoped by
    doctor_id in the SQL and served by idx_consult_audit_doctor (revision 0022).

    Patient names are NOT rendered on the feed. It is a list of actions, and a name on every
    row would turn an activity log into a disclosure of who this doctor saw and when, on a
    dashboard that may be over someone's shoulder. Each event does carry what is needed to
    OPEN its appointment — booking, patient id and name — because the row links through to
    the consult, where the name is shown in context. That link was promised here before it
    existed: the UI received consultation_id and did nothing with it.

    An event whose consult was discarded is marked not openable: every screen that shows a
    consult filters discarded ones out, so there is nowhere to land.
    """
    from app.services.consults import ensure_consult_schema

    limit = max(1, min(int(limit), ACTIVITY_LOG_MAX_LIMIT))

    with connect_db() as conn:
        ensure_consult_schema(conn)
        with conn.cursor() as cur:
            # Filtered to the feed's action types in SQL so an audit table dominated by
            # other actions cannot push every feed-worthy row past the limit. The joins are
            # one-to-one (see _CONSULT_ITEM_JOINS) and LEFT, so they neither add nor drop rows.
            cur.execute(
                f"""
                SELECT a.action_type, a.metadata, a.created_at, a.consultation_id,
                       {_DOCUMENT_COLUMNS},
                       {_CONSULT_ITEM_COLUMNS}
                FROM consult_audit_log a
                LEFT JOIN consultations c ON c.id = a.consultation_id
                LEFT JOIN soap_notes sn ON sn.consultation_id = c.id
                {_CONSULT_ITEM_JOINS}
                -- One-to-one too: document_id is document_catalog's primary key.
                LEFT JOIN document_catalog dc ON dc.document_id = a.metadata->>'document_id'
                WHERE a.doctor_id = %s AND a.action_type = ANY(%s)
                ORDER BY a.created_at DESC
                LIMIT %s
                """,
                (doctor_id, list(_FEED_ACTIONS.keys()), limit),
            )
            rows = cur.fetchall()

    events = [
        event for event in (
            _project_event(*row[:4], document_row=row[4:9], consult_row=row[9:]) for row in rows
        )
        if event is not None
    ]
    return {"events": events}
