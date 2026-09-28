"""Pure read-model logic for the AI doctor workspace.

Everything in this module is a deterministic function over data the caller has already
fetched and already authorized. There is no database access, no network call and no model
call anywhere in here, which is the point: ranking, lane grouping, progress and parsing are
the parts most worth testing exhaustively, and they are testable without a database or an
LLM (the same reason soap_notes._low_confidence_count is already unit-tested in isolation).

AUTHORIZATION IS NOT DONE HERE. Every function takes rows that the caller has already
scoped to one doctor in SQL. Nothing in this module filters by doctor_id, so nothing in it
may ever be handed rows from more than one doctor.

NO CLINICAL REASONING HAPPENS HERE. The ranking below orders documentation work by
workflow signals (blocked, flag count, waiting time). It is explicitly NOT a clinical
urgency or triage ranking: no severity, acuity or risk score is persisted anywhere in this
schema, so none can honestly be computed. Nothing here generates dosing, interaction or
formulary advice, and rank_pending_items must never be described to a doctor as
"most urgent patient first".
"""
from __future__ import annotations

import re

SOAP_SECTIONS = ("subjective", "objective", "assessment", "plan")

# Review-inbox lanes (plan §4.5). Every pending item lands in exactly one.
LANE_NEEDS_ATTENTION = "needs_attention"
LANE_QUICK_REVIEW = "quick_review"
LANE_NOT_DRAFTED = "not_drafted"
LANES = (LANE_NEEDS_ATTENTION, LANE_QUICK_REVIEW, LANE_NOT_DRAFTED)

# A lower-quality ('live_fallback') transcript weighs this much when ranking by "most
# flags". Chosen so a lower-quality transcript outranks a single flagged field but not
# three: the transcript being weak casts doubt over every section at once, while one
# flagged field is a single localized doubt.
_LOW_QUALITY_WEIGHT = 2

# Bulk "draft all missing notes" (plan §4.5). Each drafted note is an LLM call, so the
# batch is hard-capped at the service layer rather than trusting the client or the queue
# length — an uncapped bulk action is a cost and latency incident waiting to happen
# (engineering-standards.md §Scalability: "Every loop, query, queue, cache, retry, and
# concurrency pool has an intentional limit").
BULK_DRAFT_MAX_ITEMS = 10


def _appointment_sort_key(item: dict) -> str:
    """ISO-8601 timestamps sort correctly as strings, which keeps this module free of
    date parsing. A missing timestamp sorts last rather than raising: it is a data gap,
    not a reason to fail the whole queue."""
    return item.get("appointment_start") or "9999-12-31T23:59:59"


def flag_weight(item: dict) -> int:
    """How much doubt is attached to this draft. Higher means more to check."""
    flags = item.get("low_confidence_fields") or 0
    if not isinstance(flags, int) or flags < 0:
        flags = 0
    return flags + (_LOW_QUALITY_WEIGHT if item.get("low_quality_transcript") else 0)


def rank_pending_items(items: list[dict]) -> list[dict]:
    """Deterministic, rule-based ordering of the pending review queue (plan §4.2).

    Order, as specified:
      1. blocked (is_stale) — these cannot be signed at all until regenerated, so they
         block the doctor's work completely rather than merely waiting on it
      2. drafts with the most flags / a lower-quality transcript
      3. oldest waiting first
      4. transcripts with no note yet

    The final consultation_id term makes this a TOTAL order: without it, two items
    identical on every other term could come back in either order from one load to the
    next, and a "prioritised" list that reshuffles under the doctor is worse than an
    unsorted one. Does not mutate the input.
    """
    def sort_key(item: dict):
        return (
            0 if item.get("is_stale") else 1,
            -flag_weight(item),
            _appointment_sort_key(item),
            1 if item.get("item_type") == "not_generated" else 0,
            str(item.get("consultation_id") or ""),
        )

    return sorted(items, key=sort_key)


def lane_for_item(item: dict) -> str:
    """Which review-inbox lane one pending item belongs to.

    Checked in priority order, so an item that qualifies for two lanes lands in the more
    serious one: a blocked item with no note is 'needs attention', not 'not drafted'.
    """
    if item.get("is_stale") or item.get("low_quality_transcript"):
        return LANE_NEEDS_ATTENTION
    if item.get("item_type") == "not_generated":
        return LANE_NOT_DRAFTED
    return LANE_QUICK_REVIEW


def group_into_lanes(items: list[dict]) -> dict[str, list[dict]]:
    """Groups the pending queue into the three lanes, each internally ranked by
    rank_pending_items. Always returns all three keys, so the UI renders three lanes with
    empty states rather than three different shapes."""
    lanes: dict[str, list[dict]] = {lane: [] for lane in LANES}
    for item in items:
        lanes[lane_for_item(item)].append(item)
    return {lane: rank_pending_items(rows) for lane, rows in lanes.items()}


def explain_item_status(item: dict) -> str:
    """The one-line, plain-language explanation shown on a review card (plan §4.5).

    Describes only what is recorded about the DOCUMENTATION — never the patient, never
    anything clinical. Ordered most-blocking first so the sentence leads with the reason
    the doctor cannot simply sign.
    """
    if item.get("is_stale"):
        return "Transcript labels changed after this draft was written — regenerate before signing."
    if item.get("item_type") == "not_generated":
        return "Transcript captured, ready to draft."
    if item.get("low_quality_transcript"):
        return "Drafted from a lower-quality transcript — check it against the recording."
    flags = item.get("low_confidence_fields") or 0
    if flags:
        return f"{flags} section{'s' if flags != 1 else ''} flagged where the transcript support was thin."
    if item.get("is_edited"):
        return "You have edits in progress on this draft."
    return "Drafted with every section cited to the transcript."


def verification_progress(verified_sections, note: dict | None = None) -> dict:
    """"n of 4 sections verified" (plan §4.6).

    Counts only the four real SOAP sections, and only once each, so a duplicate or unknown
    section name recorded against a note can never push the count above 4 or produce a
    progress bar over 100%.
    """
    verified = {s for s in (verified_sections or []) if s in SOAP_SECTIONS}
    total = len(SOAP_SECTIONS)
    count = len(verified)
    flags = (note or {}).get("confidence_flags") or {}
    if not isinstance(flags, dict):
        flags = {}
    unresolved = sorted(s for s in SOAP_SECTIONS if flags.get(s) is True and s not in verified)
    return {
        "verified": sorted(verified),
        "verified_count": count,
        "total": total,
        "complete": count == total,
        "percent": round(count * 100 / total),
        # Drives the D4 warning on the sign confirmation. It is a WARNING, never a block:
        # confidence_flags is the model's self-assessment, and a doctor who has read the
        # transcript overrules it. (A 'stale' note is a different matter entirely and is
        # rejected by soap_notes.sign_soap_note itself, not by anything here.)
        "unresolved_flagged_sections": unresolved,
    }


def summarize_activity(counts: dict) -> str:
    """The headline sentence over the activity tiles (plan §4.1).

    Built only from counts the caller measured. It never claims an action that did not
    happen, and it degrades to an honest "no activity" line rather than an upbeat one.
    """
    drafted = counts.get("notes_drafted", 0)
    summarized = counts.get("documents_summarized", 0)
    awaiting = counts.get("awaiting_signature", 0)

    def plural(n: int, one: str, many: str) -> str:
        return f"{n} {one if n == 1 else many}"

    if not drafted and not summarized:
        if awaiting:
            return f"No new AI activity. {plural(awaiting, 'item', 'items')} still waiting on your sign-off."
        return "No new AI activity since you were last here."

    parts = []
    if drafted:
        parts.append(plural(drafted, "note drafted", "notes drafted"))
    if summarized:
        parts.append(plural(summarized, "document summarised", "documents summarised"))
    headline = " and ".join(parts).capitalize()
    if awaiting:
        # "1 item waits" / "4 items wait" — the verb agrees too, not just the noun.
        verb = "waits" if awaiting == 1 else "wait"
        return f"{headline}. {plural(awaiting, 'item', 'items')} {verb} on your sign-off."
    return f"{headline}. Nothing is waiting on your sign-off."


# ---- Insert from plan (plan §4.10) ----

# A leading list marker: "-", "*", "1.", "1)", or a unicode bullet.
_LIST_MARKER = re.compile(r"^\s*(?:[-*•·]|\d+[.)])\s+")

# Lines that are section headings rather than medication lines.
_HEADING = re.compile(r"^\s*(?:plan|medications?|rx|prescriptions?)\s*:?\s*$", re.IGNORECASE)

# A line is treated as a medication line only if it looks like one: a list item, or text
# carrying a dose-like token. This is a FORMATTING heuristic for a copy-into-a-textarea
# convenience, NOT clinical parsing — see the guarantees in extract_plan_medication_lines.
_DOSE_HINT = re.compile(
    r"\b\d+\s*(?:mg|mcg|g|ml|iu|units?)\b|\b(?:od|bd|tds|qds|prn|daily|twice|nightly)\b",
    re.IGNORECASE,
)


def extract_plan_medication_lines(plan_text: str | None, limit: int = 20) -> list[str]:
    """Pulls the medication-looking lines out of a signed note's Plan, for "Insert from
    plan" to drop into the prescription textarea as an editable draft.

    WHAT THIS DOES NOT DO, deliberately and permanently:
      - It does not validate a dose, a route, a frequency or a drug name.
      - It does not check a formulary, an interaction or an allergy.
      - It does not normalise, correct, complete or reformat what the doctor wrote.
      - It does not add anything that was not already in the signed text.

    It is a copy, not a suggestion. Every line it returns was already written and signed by
    a clinician; this only saves retyping it. The "no dose/interaction checking" notice
    stays on screen precisely because nothing here checks anything. Output is returned
    verbatim (whitespace-trimmed and de-marked only) so the doctor edits their own words.
    """
    if not plan_text or not isinstance(plan_text, str):
        return []

    lines: list[str] = []
    seen: set[str] = set()
    for raw in plan_text.splitlines():
        stripped = raw.strip()
        if not stripped or _HEADING.match(stripped):
            continue
        is_list_item = bool(_LIST_MARKER.match(stripped))
        if not is_list_item and not _DOSE_HINT.search(stripped):
            continue
        text = _LIST_MARKER.sub("", stripped).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        lines.append(text)
        if len(lines) >= limit:
            break
    return lines
