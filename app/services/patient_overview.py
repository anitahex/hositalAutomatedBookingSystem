"""The at-a-glance card at the top of a patient's page.

WHAT IT IS. Five to eight lines a doctor reads before they start: active concerns, current
medications, allergies, key diagnoses, recent abnormal results, last visit and next
appointment — each line carrying where it came from.

HOW IT IS GROUNDED. The agreed design, and every part of it is enforced here:

  1. CODE gathers the facts. Each gets an id, a source and, where it matters, a label.
     The model never sees a document, a note or a transcript.
  2. The model is given ONLY that fact list and may only phrase it. It cannot introduce a
     medication, a diagnosis or a number, because it is never shown anything to introduce
     them from.
  3. After phrasing, CODE verifies that every fact id came back and that every number in
     the prose appears in the fact it claims to come from. If anything is missing or
     altered, the prose is DISCARDED and the plain structured list is rendered instead.
     A doctor then reads a slightly drier card — never a wrong one.
  4. Trends and cross-document comparisons are not done here at all; they are SQL
     (document_findings.trend_for).

LABELS THAT ARE NOT DECORATION:

  - "Patient reports" — anything originating in the triage chat or the patient's own
    free-text health issues. It can never be promoted into a diagnosis or a history item,
    because nobody clinical has confirmed it.
  - "Reported, unverified" — a medication read off a document the patient uploaded, such
    as a prescription from another clinic. Shown, never hidden: a drug the patient is
    actually taking matters even when this hospital did not prescribe it, and hiding it
    would be the more dangerous choice. It is simply never presented as our prescription.

DISCLOSURE. The overview obeys the same restriction as the timeline: a fact derived from a
sensitive specialty's note is excluded for a doctor outside it. Without that, the summary
card would quietly undo the restriction one line above the timeline that enforces it.
"""
from __future__ import annotations

import json
import logging
import re

from app.db.connection import connect_db
from app.services.patient_timeline import may_read_note

logger = logging.getLogger(__name__)

# Versions the whole card, not only the phrasing prompt: it is stored with every cached
# card and a card built by any other version is rebuilt on read. Bump it whenever what
# gather_facts selects changes — otherwise a fix to fact selection reaches no patient whose
# record has not happened to change since (the cache otherwise only rebuilds on new input).
#   v2: medications from documents come from the structured medication finding, not the
#       first two summary sentences (which put an MRI finding on the card as a drug);
#       abnormal results newest first with no alphabetical cut; scanned-source flag.
#   v3: same-date readings of one analyte resolved deterministically (classified first).
#   v4: abnormal results are no longer phrased into the card's lines; they are shown by
#       document (overview_documents), with who verified each and what changed.
OVERVIEW_PROMPT_VERSION = "overview-v4"

# Enough to show every current abnormal result in a normal panel, bounded so a very long
# record cannot turn the card into a lab report. Newest first, so any cut loses the oldest.
MAX_ABNORMAL_FACTS = 12

# How a medication list is keyed in a document's extracted findings. The key is chosen by
# the extraction model, so it varies ("Medication", "Medications", "Prescribed drugs",
# "Rx"); matched loosely here rather than on one spelling that would silently miss the rest.
_MEDICATION_KEY_PATTERNS = ("%medic%", "%prescri%", "%drug%", "rx%")

# Enough to be a summary, few enough to be read at a glance. The brief asked for 5-8.
MAX_OVERVIEW_LINES = 8

LABEL_PATIENT_REPORTS = "Patient reports"
LABEL_REPORTED_UNVERIFIED = "Reported, unverified"

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def _numbers(text: str | None) -> set[float]:
    values = set()
    for raw in _NUMBER.findall(str(text or "")):
        try:
            values.add(float(raw.replace(",", ".")))
        except ValueError:
            continue
    return values


def gather_facts(doctor_id: str, patient_id: str, viewer_department: str | None) -> list[dict]:
    """Everything the card may say, read from the record — never from a model.

    Four queries, not one per section: this runs on every patient open and the application
    shares one pool of ten connections across all users.
    """
    facts: list[dict] = []

    def add(kind: str, text: str, *, label=None, source_type=None, source_id=None, scanned=False):
        if not str(text or "").strip():
            return
        facts.append({
            "id": f"f{len(facts) + 1}",
            "kind": kind,
            "text": " ".join(str(text).split()),
            "label": label,
            "source_type": source_type,
            "source_id": str(source_id) if source_id else None,
            # Read off a photograph or scan rather than a text layer. Kept separate from
            # `label` so the label stays exactly "Reported, unverified" — the UI shows both.
            "scanned": bool(scanned),
        })

    with connect_db() as conn:
        with conn.cursor() as cur:
            # Patient's own words. Never promoted beyond "reports" — nobody clinical has
            # confirmed any of it.
            cur.execute(
                "SELECT health_issues FROM patient_profiles WHERE user_id = %s", (patient_id,)
            )
            row = cur.fetchone()
            if row and row[0]:
                add("concern", row[0], label=LABEL_PATIENT_REPORTS, source_type="patient_profile")

            # Diagnoses from SIGNED notes only, with the department so sensitive ones can
            # be filtered. A draft is not a diagnosis.
            cur.execute(
                """
                SELECT sn.assessment, d.department, sn.signed_at, sn.consultation_id
                FROM soap_notes sn
                JOIN consultations c ON c.id = sn.consultation_id
                JOIN doctors d ON d.doctor_id = sn.doctor_id
                WHERE sn.patient_id = %s AND sn.status = 'signed' AND sn.assessment <> ''
                ORDER BY sn.signed_at DESC NULLS LAST
                LIMIT 6
                """,
                (patient_id,),
            )
            for assessment, department, _signed_at, consultation_id in cur.fetchall():
                if not may_read_note(viewer_department, department):
                    # Excluded entirely rather than shown as "restricted": this is a
                    # summary, and a redaction notice in an at-a-glance card is noise. The
                    # timeline is where the existence of that encounter is disclosed.
                    continue
                add("diagnosis", assessment, source_type="note", source_id=consultation_id)

            # Medications this hospital actually prescribed: approved clinical items only.
            cur.execute(
                """
                SELECT ci.content, ci.consultation_id, d.department
                FROM consult_clinical_items ci
                JOIN doctors d ON d.doctor_id = ci.doctor_id
                WHERE ci.patient_id = %s AND ci.kind = 'prescription' AND ci.status = 'approved'
                ORDER BY ci.updated_at DESC
                LIMIT 6
                """,
                (patient_id,),
            )
            for content, consultation_id, department in cur.fetchall():
                if not may_read_note(viewer_department, department):
                    continue
                add("medication", content, source_type="note", source_id=consultation_id)

            # Medications read off documents the patient uploaded — another clinic's
            # prescription, a discharge summary. Labelled, never hidden.
            #
            # From the STRUCTURED medication finding, not from the summary. This used to take
            # the first two summary sentences of any prescription-type document and call them
            # medications; a prescription photo's summary opens with the MRI result written on
            # it, so "MRI shows L5/S1-C3, L4 Butterfly Vertebra" appeared on the card as a
            # drug. The extraction already separates the medication list — that is the source.
            # Not restricted to document_type = 'prescription' for the same reason in reverse:
            # a discharge summary lists medications too.
            cur.execute(
                """
                SELECT DISTINCT ON (df.document_id, df.value_text)
                       df.value_text, df.document_id, dc.clinical_date,
                       (dc.original_filename ~* '\\.(png|jpe?g)$'
                        OR EXISTS (SELECT 1 FROM document_pages dp
                                   WHERE dp.document_id = df.document_id
                                     AND dp.source = 'vision_transcription')) AS scanned
                FROM document_findings df
                JOIN document_catalog dc ON dc.document_id = df.document_id
                WHERE df.patient_id = %s
                  AND COALESCE(df.value_text, '') <> ''
                  AND (LOWER(df.printed_name) LIKE ANY(%s)
                       OR LOWER(COALESCE(df.canonical_name, '')) LIKE ANY(%s)
                       OR LOWER(COALESCE(df.panel, '')) LIKE ANY(%s))
                ORDER BY df.document_id, df.value_text, dc.clinical_date DESC NULLS LAST
                """,
                (patient_id, list(_MEDICATION_KEY_PATTERNS), list(_MEDICATION_KEY_PATTERNS),
                 list(_MEDICATION_KEY_PATTERNS)),
            )
            document_meds = sorted(
                cur.fetchall(), key=lambda row: str(row[2] or ""), reverse=True
            )[:3]
            for value_text, document_id, _clinical_date, scanned in document_meds:
                add("medication", value_text,
                    label=LABEL_REPORTED_UNVERIFIED,
                    source_type="document", source_id=document_id, scanned=scanned)

            # Current out-of-range results, computed by code, one per measurement: the latest
            # reading of each, and only if THAT reading is abnormal.
            #
            # Newest first, then by name. This used to keep the first six ALPHABETICALLY, so
            # a patient with eight abnormal results lost Vitamin D (deficient) and hs-CRP
            # while Total Cholesterol stayed — the selection said nothing about importance.
            cur.execute(
                """
                SELECT canonical_name, value_num, unit, abnormal, clinical_date, document_id
                FROM (
                    SELECT DISTINCT ON (canonical_name)
                           canonical_name, value_num, unit, abnormal, clinical_date, document_id
                    FROM document_findings
                    WHERE patient_id = %s AND canonical_name IS NOT NULL
                    -- Several readings on the same date (the same report uploaded twice, or
                    -- two rows sharing a name) must not be picked between at random: one we
                    -- could classify beats one we could not, then the newest stored.
                    ORDER BY canonical_name, clinical_date DESC NULLS LAST,
                             (abnormal = 'unknown'), created_at DESC
                ) latest
                WHERE abnormal IN ('low', 'high')
                ORDER BY clinical_date DESC NULLS LAST, canonical_name
                LIMIT %s
                """,
                (patient_id, MAX_ABNORMAL_FACTS),
            )
            for name, value, unit, flag, clinical_date, document_id in cur.fetchall():
                when = f" ({clinical_date.isoformat()})" if clinical_date else ""
                add("abnormal",
                    f"{name} {flag} at {value}{(' ' + unit) if unit else ''}{when}",
                    source_type="document", source_id=document_id)

            # Last visit and next appointment, in one pass over the bookings.
            cur.execute(
                """
                SELECT b.start_time, d.name, d.department, b.status,
                       (b.start_time >= NOW()) AS upcoming
                FROM appointment_bookings b
                JOIN doctors d ON d.doctor_id = b.doctor_id
                WHERE b.patient_id = %s AND b.status <> 'cancelled'
                ORDER BY b.start_time DESC
                """,
                (patient_id,),
            )
            bookings = cur.fetchall()
        conn.commit()

    past = [b for b in bookings if not b[4]]
    future = [b for b in bookings if b[4]]
    if past:
        start, name, department, _status, _ = past[0]
        add("visit", f"Last seen {start.strftime('%d %b %Y')} by {name}, {department}",
            source_type="booking")
    if future:
        start, name, department, _status, _ = future[-1]
        add("visit", f"Next appointment {start.strftime('%d %b %Y')} with {name}, {department}",
            source_type="booking")

    return facts


def structured_lines(facts: list[dict]) -> list[dict]:
    """The fallback rendering: the facts themselves, grouped, with their labels.

    This is what a doctor sees whenever the phrased version cannot be trusted. It is drier
    and completely faithful, which is the right way round — the prose is a convenience,
    the facts are the point.
    """
    order = ["concern", "diagnosis", "medication", "abnormal", "visit"]
    headings = {
        "concern": "Active concerns",
        "diagnosis": "Diagnoses",
        "medication": "Medications",
        "abnormal": "Recent abnormal results",
        "visit": "Visits",
    }
    lines = []
    for kind in order:
        matching = [fact for fact in facts if fact["kind"] == kind]
        if not matching:
            continue
        lines.append({
            "heading": headings[kind],
            "items": [
                {"text": fact["text"], "label": fact["label"],
                 "source_type": fact["source_type"], "source_id": fact["source_id"],
                 "fact_id": fact["id"], "scanned": bool(fact.get("scanned"))}
                for fact in matching
            ],
        })
    return lines


def verify_phrasing(lines, facts: list[dict]) -> tuple[bool, str]:
    """Rule 1. Every fact id must come back, and every number must match its fact.

    Returns (ok, reason). A failure is not repaired — the caller falls back to the
    structured list, because a summary that has dropped or altered a fact is a summary
    whose other lines cannot be trusted either.
    """
    if not isinstance(lines, list) or not lines:
        return False, "no lines returned"
    if len(lines) > MAX_OVERVIEW_LINES:
        return False, "more lines than the card allows"

    facts_by_id = {fact["id"]: fact for fact in facts}
    cited: set[str] = set()

    for line in lines:
        if not isinstance(line, dict):
            return False, "malformed line"
        text = str(line.get("text") or "").strip()
        ids = line.get("fact_ids")
        if not text or not isinstance(ids, list) or not ids:
            return False, "a line cites no fact"

        referenced = [facts_by_id.get(str(i)) for i in ids]
        if any(fact is None for fact in referenced):
            # A citation to a fact that was never supplied is an invention.
            return False, "a line cites an unknown fact"
        cited.update(str(i) for i in ids)

        available = set()
        for fact in referenced:
            available |= _numbers(fact["text"])
        if not _numbers(text) <= available:
            return False, "a number does not appear in the cited facts"

    missing = set(facts_by_id) - cited
    if missing:
        # Silently dropping a fact is how an overview omits a medication or an abnormal
        # result. Treated as a failure of the whole phrasing, not of one line.
        return False, f"{len(missing)} fact(s) were dropped"

    return True, ""


def latest_source_change(patient_id: str):
    """When anything the overview is built from last changed.

    Used instead of invalidation hooks scattered across every writer. A cache that
    recomputes when its inputs are newer cannot go stale because somebody forgot to call
    an invalidate() — the same class of bug as the undeclared graph keys fixed earlier.
    """
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT GREATEST(
                    COALESCE((SELECT MAX(signed_at) FROM soap_notes WHERE patient_id = %(p)s), 'epoch'),
                    COALESCE((SELECT MAX(updated_at) FROM consult_clinical_items WHERE patient_id = %(p)s), 'epoch'),
                    COALESCE((SELECT MAX(created_at)::timestamp FROM document_catalog WHERE user_id = %(p)s), 'epoch'),
                    COALESCE((SELECT MAX(created_at) FROM appointment_bookings WHERE patient_id = %(p)s), 'epoch'),
                    COALESCE((SELECT MAX(updated_at) FROM patient_profiles WHERE user_id = %(p)s), 'epoch')
                )
                """,
                {"p": patient_id},
            )
            latest = cur.fetchone()[0]
        conn.commit()
    return latest


# ---- Composition and cache ----

def _cache_key(viewer_department: str | None) -> str:
    return " ".join(str(viewer_department or "").split())


def _read_cache(patient_id: str, viewer_department: str | None, source_changed_at) -> dict | None:
    """The stored card, if it was built from inputs that have not moved since.

    Staleness is decided by comparing recorded inputs against current ones rather than by
    trusting a writer to have invalidated. A cache that needs every future writer to
    remember an invalidate() call goes stale silently the first time one does not.
    """
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT lines, facts, mode, reason, source_changed_at, generated_at,
                          prompt_version
                   FROM patient_overviews
                   WHERE patient_id = %s AND viewer_department = %s""",
                (patient_id, _cache_key(viewer_department)),
            )
            row = cur.fetchone()
        conn.commit()

    if not row:
        return None
    if source_changed_at and row[4] and row[4] < source_changed_at:
        return None
    # Built by an older version of this module: its facts were selected by rules that have
    # since been corrected, so it is rebuilt rather than served. prompt_version was always
    # stored and never checked, which is how a fix could otherwise miss every cached card.
    if row[6] != OVERVIEW_PROMPT_VERSION:
        return None
    return {
        "lines": row[0] or [],
        "facts": row[1] or [],
        "mode": row[2],
        "reason": row[3],
        "generated_at": row[5].isoformat() if row[5] else None,
        "cached": True,
    }


def _write_cache(patient_id, viewer_department, *, lines, facts, mode, reason, source_changed_at):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO patient_overviews (patient_id, viewer_department, lines, facts,
                                               mode, reason, prompt_version, source_changed_at,
                                               generated_at)
                VALUES (%s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, NOW())
                ON CONFLICT (patient_id, viewer_department) DO UPDATE SET
                    lines = EXCLUDED.lines, facts = EXCLUDED.facts, mode = EXCLUDED.mode,
                    reason = EXCLUDED.reason, prompt_version = EXCLUDED.prompt_version,
                    source_changed_at = EXCLUDED.source_changed_at, generated_at = NOW()
                """,
                (patient_id, _cache_key(viewer_department), json.dumps(lines), json.dumps(facts),
                 mode, reason, OVERVIEW_PROMPT_VERSION, source_changed_at),
            )
        conn.commit()


async def refresh_cached_overviews(patient_id: str) -> int:
    """Rebuilds every department's cached card for this patient. Returns how many.

    Called after something the card is built from changes — a note signed, a prescription
    approved, a document processed — so the next doctor to open the patient reads a card
    that is already built. Otherwise the FIRST open after any change paid for the model
    phrasing call (~4s) while the doctor waited.

    Only departments that already have a card are rebuilt: a department whose doctors never
    open this patient should not cost a model call every time the record changes.
    """
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT viewer_department FROM patient_overviews WHERE patient_id = %s",
                (patient_id,),
            )
            departments = [row[0] for row in cur.fetchall()]
        conn.commit()
    for department in departments:
        # get_overview rebuilds only if its inputs moved since the stored card — which is
        # exactly the case after the change that triggered this. doctor_id is not used in
        # building the card (it is per patient and viewing department), hence None.
        await get_overview(None, patient_id, department or None)
    return len(departments)


def schedule_overview_refresh(*, patient_id: str | None = None, consultation_id: str | None = None) -> None:
    """Fire-and-forget refresh, safe to call from a sync route or from async code.

    Runs on its own thread with its own event loop, so the caller — a sign or approve
    request — returns without waiting on a model call, and a failure here can never fail
    that clinical action. Pass the consultation instead of the patient when that is what
    the caller has; it is resolved on the thread, off the request path.
    """
    import asyncio
    import threading

    if not patient_id and not consultation_id:
        return

    def run() -> None:
        try:
            target = patient_id
            if not target:
                with connect_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT patient_id FROM consultations WHERE id::text = %s",
                                    (str(consultation_id),))
                        row = cur.fetchone()
                    conn.commit()
                target = row[0] if row else None
            if target:
                rebuilt = asyncio.run(refresh_cached_overviews(str(target)))
                logger.info("patient_overview: rebuilt %d cached card(s) in the background", rebuilt)
        except Exception as exc:
            logger.warning("patient_overview: background refresh failed: %s", exc)

    threading.Thread(target=run, name="overview-refresh", daemon=True).start()


async def get_overview(doctor_id: str, patient_id: str, viewer_department: str | None) -> dict:
    """The at-a-glance card. Cached per (patient, viewing department).

    Per department because the card obeys the sensitive-specialty restriction, so its
    content differs by who is reading. A cache keyed on the patient alone would hand one
    doctor's card to another and quietly undo that restriction.

    Falls back to the structured list whenever the phrasing cannot be verified, and says
    which it is returning. Never raises for a model failure: a doctor must get the facts
    even when nothing can phrase them.
    """
    from app.inference.azure_client import gpt4o_overview_phrasing

    changed_at = latest_source_change(patient_id)
    cached = _read_cache(patient_id, viewer_department, changed_at)
    if cached:
        return cached

    facts = gather_facts(doctor_id, patient_id, viewer_department)
    if not facts:
        # An empty record produces an empty card, never an invented one.
        result = {"lines": [], "facts": [], "mode": "structured",
                  "reason": "nothing on record yet", "cached": False}
        _write_cache(patient_id, viewer_department, lines=[], facts=[],
                     mode="structured", reason=result["reason"], source_changed_at=changed_at)
        return result

    # Abnormal results are shown by document, beside who verified that document and what
    # changed (overview_documents), so they are not phrased into the lines as well. They stay
    # in `facts`: the audit of this read counts them, and the selection rules stay tested here.
    phrase_facts = [fact for fact in facts if fact["kind"] != "abnormal"]
    mode, reason, lines = "structured", "", structured_lines(phrase_facts)
    if not phrase_facts:
        reason = "only results on record; shown by document"
    else:
        try:
            phrased = await gpt4o_overview_phrasing(facts=phrase_facts)
            ok, why = verify_phrasing(phrased.get("lines"), phrase_facts)
            if ok:
                mode, lines = "phrased", phrased["lines"]
            else:
                reason = why
                logger.warning("patient_overview: phrasing rejected for %s — %s", patient_id, why)
        except Exception as exc:
            reason = "the summary could not be generated"
            logger.error("patient_overview: phrasing failed for %s: %s", patient_id, exc)

    _write_cache(patient_id, viewer_department, lines=lines, facts=facts,
                 mode=mode, reason=reason, source_changed_at=changed_at)
    return {"lines": lines, "facts": facts, "mode": mode, "reason": reason, "cached": False}
