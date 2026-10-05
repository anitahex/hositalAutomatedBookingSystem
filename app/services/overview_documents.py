"""At a glance, by document: what each report found, who has checked it, and what changed.

WHY. The at-a-glance card listed abnormal results one line at a time, with no sign of which
report each came from or whether any doctor had checked it against the original. A result a
colleague had verified read exactly like one nobody had looked at, and a new report gave no
hint of what it changed.

WHAT THIS BUILDS, per document, newest first:
  - its current findings together: the abnormal results it holds the LATEST reading of
    (the same rule as patient_overview.gather_facts, so the two never disagree), and the
    results it brought back into range; for an imaging report or a prescription, which have
    no numbers, the verified sentences of its summary;
  - its review state from document_reviews: verified by whom and when, or reported
    inaccurate and why — as the viewing doctor may see it (a verifier in a restricted
    specialty is not named outside it);
  - what changed since the previous reading of each result, and a count for the document.

HOW "WHAT CHANGED" IS DECIDED. By code, from stored readings: the previous reading of a
measurement is its latest reading from an EARLIER date. Never the same date — the same report
uploaded twice would otherwise read as "unchanged" against itself. Values are compared only
when their units match. No model is involved; a trend is an ORDER BY, not an inference.

NOT CACHED. The at-a-glance card is cached per department until its inputs change; a review
can happen at any moment and is not one of those inputs. This is read on every open, in two
queries plus review_states.

HISTORY IS NOT DROPPED. Every reading stays in document_findings; a new report adds rows and
never replaces them. That is what lets a later report be compared with an earlier one here,
and the full series is always available from the trends view (document_findings.trend_for).
"""
from __future__ import annotations

import logging

from app.db.connection import connect_db

logger = logging.getLogger(__name__)

# Enough for the recent picture without turning the card into the record. Older documents
# are on the Documents tab and the timeline.
MAX_DOCUMENT_BLOCKS = 6
MAX_FINDINGS_PER_BLOCK = 12
MAX_SUMMARY_SENTENCES = 3

ABNORMAL = ("low", "high")

CHANGE_FIRST = "first"          # no earlier reading on record
CHANGE_NEW = "new"              # was in range, now out of range
CHANGE_WORSE = "worse"          # out of range in the same direction, further out
CHANGE_BETTER = "better"        # out of range in the same direction, closer to range
CHANGE_SAME = "unchanged"       # same value as before
CHANGE_FLIPPED = "flipped"      # was low, now high (or the reverse)
CHANGE_RESOLVED = "back_to_normal"  # was out of range, now in range


def _same_unit(a: str | None, b: str | None) -> bool:
    from app.services.document_findings import normalize_unit

    return (normalize_unit(a) or "") == (normalize_unit(b) or "")


def describe_change(latest: dict, previous: dict | None) -> dict | None:
    """How `latest` differs from `previous`, or None when there is nothing to say.

    Both are readings: {"value", "unit", "flag", "clinical_date"}. Only in-range → out of
    range, direction and resolution are said; a comparison needing numbers is made only when
    both have one, in the same unit.
    """
    flag = latest.get("flag")
    if previous is None:
        return {"kind": CHANGE_FIRST} if flag in ABNORMAL else None

    before = previous.get("flag")
    base = {
        "previous_value": previous.get("value"),
        "previous_unit": previous.get("unit"),
        "previous_flag": before,
        "previous_date": previous.get("clinical_date"),
    }
    if flag == "normal" and before in ABNORMAL:
        return {"kind": CHANGE_RESOLVED, **base}
    if flag not in ABNORMAL:
        return None
    if before == "normal":
        return {"kind": CHANGE_NEW, **base}
    if before in ABNORMAL and before != flag:
        return {"kind": CHANGE_FLIPPED, **base}
    if before != flag:
        return None  # previous could not be classified; say nothing rather than guess

    now, then = latest.get("value"), previous.get("value")
    if now is None or then is None or not _same_unit(latest.get("unit"), previous.get("unit")):
        return None
    if now == then:
        return {"kind": CHANGE_SAME, **base}
    further_out = now > then if flag == "high" else now < then
    return {"kind": CHANGE_WORSE if further_out else CHANGE_BETTER, **base}


def _change_counts(findings: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for finding in findings:
        kind = (finding.get("change") or {}).get("kind")
        if kind and kind != CHANGE_FIRST:
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _latest_and_previous(rows) -> dict[str, tuple[dict, dict | None]]:
    """Per measurement: its latest reading, and its latest reading from an earlier date.

    `rows` arrive ordered by measurement, then newest first with the same tie-break as
    gather_facts (a classified reading beats an unclassified one on the same date).
    """
    result: dict[str, tuple[dict, dict | None]] = {}
    for row in rows:
        (canonical, printed, value, value_text, unit, flag, report_ref, clinical_date,
         document_id) = row
        reading = {
            "name": printed or canonical,
            "canonical": canonical,
            "value": float(value) if value is not None else None,
            "value_text": value_text,
            "unit": unit,
            "flag": flag,
            "report_ref": report_ref,
            "clinical_date": _iso(clinical_date),
            "document_id": document_id,
        }
        if canonical not in result:
            result[canonical] = (reading, None)
            continue
        latest, previous = result[canonical]
        if previous is None and latest["clinical_date"] and reading["clinical_date"] \
                and reading["clinical_date"] < latest["clinical_date"]:
            result[canonical] = (latest, reading)
    return result


def _copy_key(filename, document_type, clinical_date) -> tuple:
    """Uploads of the same report share a key: the file name without a browser's " (4)"
    download suffix, the document type and the clinical date."""
    import re

    name = re.sub(r"\s*\(\d+\)(?=\.[A-Za-z0-9]+$)", "", str(filename or "")).strip().lower()
    return (name, document_type, _iso(clinical_date))


# Why a complete document is not one of the blocks (scripts/check_document_display.py).
HIDDEN_NO_CURRENT_VALUES = "lab values, none out of range now (all normal, or a newer report replaced them)"
HIDDEN_NO_SUMMARY = "no summary stored (never made, or it failed its check against the document)"
HIDDEN_COPY = "another upload of a report already shown"
HIDDEN_OVER_LIMIT = f"beyond the newest {MAX_DOCUMENT_BLOCKS} documents shown"


def document_blocks(doctor_id: str | None, patient_id: str, viewer_department: str | None,
                    explain: list | None = None) -> list[dict]:
    """The document blocks for the at-a-glance card, newest document first.

    `explain`, when given, receives {"document_id", "reason"} for every complete document
    left out, by the same rules that left it out — so a check can never disagree with the
    screen."""
    from app.services.document_catalog import _content_type_for
    from app.services.document_reviews import STATUS_UNVERIFIED, merged_review_states, review_states

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT canonical_name, printed_name, value_num, value_text, unit, abnormal,
                       report_ref_text, clinical_date, document_id
                FROM document_findings
                WHERE patient_id = %s AND canonical_name IS NOT NULL
                ORDER BY canonical_name, clinical_date DESC NULLS LAST,
                         (abnormal = 'unknown'), created_at DESC
                """,
                (patient_id,),
            )
            rows = cur.fetchall()
            readings = _latest_and_previous(rows)
            # Documents that carry measured values. When none of their readings is current,
            # they have nothing to say here — even if they have a summary. A reading counts
            # only when it was judged against a range (normal, high or low): a prescription
            # whose "Age/Gender 23/M" was read as the number 23 is not a lab report, and
            # counting it hid the prescription's summary entirely.
            numeric_documents = {str(row[8]) for row in rows if row[2] is not None and row[5] != "unknown"}

            cur.execute(
                """
                SELECT dc.document_id, dc.original_filename, dc.document_type, dc.clinical_date,
                       dc.created_at, ds.sentences
                FROM document_catalog dc
                LEFT JOIN document_summaries ds ON ds.document_id = dc.document_id
                WHERE dc.user_id = %s AND dc.ingestion_status = 'complete'
                ORDER BY dc.clinical_date DESC NULLS LAST, dc.created_at DESC
                """,
                (patient_id,),
            )
            documents = cur.fetchall()
        conn.commit()

    # Each measurement's current state belongs to the document holding its latest reading.
    by_document: dict[str, list[dict]] = {}
    for latest, previous in readings.values():
        change = describe_change(latest, previous)
        if latest["flag"] not in ABNORMAL and not (change and change["kind"] == CHANGE_RESOLVED):
            continue
        by_document.setdefault(str(latest["document_id"]), []).append({
            "name": latest["name"],
            "value": latest["value"],
            "value_text": latest["value_text"],
            "unit": latest["unit"],
            "flag": latest["flag"],
            "report_ref": latest["report_ref"],
            "change": change,
        })

    # How many times each report was uploaded: the same file saved twice by a browser comes
    # back as "report (1).pdf", which is still the same report.
    ids_by_key: dict[tuple, list[str]] = {}
    for document_id, filename, document_type, clinical_date, _created, _sentences in documents:
        ids_by_key.setdefault(_copy_key(filename, document_type, clinical_date), []).append(str(document_id))
    copies = {key: len(ids) for key, ids in ids_by_key.items()}

    # Within one report's copies, a copy a doctor reviewed comes first: a prescription or
    # scan speaks through ONE copy's summary, and it should be the summary that was checked
    # (the newest copy otherwise — a re-upload must not hide a verification).
    reviewed = {
        document_id for document_id, state in review_states(
            [str(row[0]) for row in documents], doctor_id, viewer_department).items()
        if state["status"] != STATUS_UNVERIFIED
    }
    first_seen = {key: index for index, key in enumerate(dict.fromkeys(
        _copy_key(row[1], row[2], row[3]) for row in documents))}
    documents = sorted(documents, key=lambda row: (
        first_seen[_copy_key(row[1], row[2], row[3])], str(row[0]) not in reviewed))

    blocks: list[dict] = []
    block_keys: dict[str, tuple] = {}
    shown: set[tuple] = set()
    for document_id, filename, document_type, clinical_date, created_at, sentences in documents:
        document_id = str(document_id)
        findings = by_document.get(document_id, [])
        # A report with measured values speaks through its current readings only: when they
        # are all in range, or all superseded by a later report or another copy of this one,
        # it has nothing current to say. A text report (imaging, prescription) speaks
        # through its verified summary.
        summary = [
            str(item.get("text") or "").strip()
            for item in (sentences or []) if isinstance(item, dict) and str(item.get("text") or "").strip()
        ][:MAX_SUMMARY_SENTENCES] if not findings and document_id not in numeric_documents else []
        if not findings and not summary:
            if explain is not None:
                explain.append({"document_id": document_id, "reason": HIDDEN_NO_CURRENT_VALUES
                                if document_id in numeric_documents else HIDDEN_NO_SUMMARY})
            continue
        # The same report uploaded more than once is one block, counted.
        key = _copy_key(filename, document_type, clinical_date)
        if key in shown and not findings:
            if explain is not None:
                explain.append({"document_id": document_id, "reason": HIDDEN_COPY})
            continue
        if len(blocks) >= MAX_DOCUMENT_BLOCKS:
            if explain is not None:
                explain.append({"document_id": document_id, "reason": HIDDEN_OVER_LIMIT})
            continue
        shown.add(key)
        block_keys[document_id] = key
        # Abnormal first, then the ones back in range; highs and lows keep the report's order.
        findings.sort(key=lambda f: (f["flag"] not in ABNORMAL, f["name"] or ""))
        block = {
            "document_id": document_id,
            "original_filename": filename or document_id,
            "document_type": document_type or "other",
            "clinical_date": _iso(clinical_date),
            "uploaded_at": _iso(created_at),
            "content_type": _content_type_for(filename),
            "findings": findings[:MAX_FINDINGS_PER_BLOCK],
            "more_findings": max(0, len(findings) - MAX_FINDINGS_PER_BLOCK),
            "summary": summary,
            "changes": _change_counts(findings),
            "copies": copies.get(key, 1),
            "review": None,
        }
        blocks.append(block)

    if explain is not None:
        # An older upload of a lab report that IS shown has no current readings of its own
        # because its copy holds them — it is that report, not a report with nothing to say.
        key_of = {str(row[0]): _copy_key(row[1], row[2], row[3]) for row in documents}
        for entry in explain:
            if entry["reason"] == HIDDEN_NO_CURRENT_VALUES and key_of.get(entry["document_id"]) in shown:
                entry["reason"] = HIDDEN_COPY

    # Verified on any copy is verified: the review shown is the whole report's.
    states = merged_review_states(
        {b["document_id"]: ids_by_key[block_keys[b["document_id"]]] for b in blocks},
        doctor_id, viewer_department,
    )
    for block in blocks:
        block["review"] = states.get(block["document_id"])
    return blocks


def copy_groups(document_ids) -> dict[str, list[str]]:
    """Each document id -> every complete copy of the same report by the same patient
    (itself included; just itself when it has no other copy or is not complete)."""
    ids = [str(document_id) for document_id in dict.fromkeys(document_ids or []) if document_id]
    if not ids:
        return {}
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT dc.document_id, dc.user_id, dc.original_filename, dc.document_type, dc.clinical_date
                FROM document_catalog dc
                WHERE dc.ingestion_status = 'complete'
                  AND dc.user_id IN (SELECT user_id FROM document_catalog WHERE document_id = ANY(%s))
                """,
                (ids,),
            )
            rows = cur.fetchall()
        conn.commit()
    key_of: dict[str, tuple] = {}
    by_key: dict[tuple, list[str]] = {}
    for document_id, user_id, filename, document_type, clinical_date in rows:
        key = (str(user_id), _copy_key(filename, document_type, clinical_date))
        key_of[str(document_id)] = key
        by_key.setdefault(key, []).append(str(document_id))
    return {document_id: by_key[key_of[document_id]] if document_id in key_of else [document_id]
            for document_id in ids}


# Facts read off a document whose label follows that document's review: a medicine list, and
# a report's findings in the summary.
LABELLED_KINDS = frozenset({"medication", "finding"})


def _document_label(state: dict | None) -> str | None:
    """The label for something read off a document, given that document's review state."""
    if not state:
        return None
    if state.get("status") == "flagged":
        # Who objected and why, beside the line itself — the reason is written for doctors,
        # and this card is shown only to doctors treating the patient.
        objections = [
            f"{person.get('name') or 'a clinician'}: “{person['reason']}”" if person.get("reason")
            else (person.get("name") or "a clinician")
            for person in state.get("flagged_by") or []
        ]
        return "From a document · reported inaccurate" + (f" by {'; '.join(objections)}" if objections else "")
    if state.get("status") == "verified":
        names = ", ".join(
            "you" if person.get("is_me") else (person.get("name") or "a clinician")
            for person in state.get("verified_by") or []
        )
        return f"From a document · verified by {names}"
    return None


def apply_review_labels(overview: dict, doctor_id: str | None, viewer_department: str | None) -> dict:
    """The card with each document-sourced medication labelled by that document's review.

    "Reported, unverified" means two things: not prescribed here, and nobody has checked the
    reading. Verification settles the second, never the first, so the new label still says
    the drug came from a document. Read at request time — a review is not an input the card
    is cached on. Covers both renderings: the facts (phrased lines read labels from their
    cited facts) and the structured lines' own copies.
    """
    from app.services.document_reviews import merged_review_states

    facts = overview.get("facts") or []
    document_ids = [
        str(fact["source_id"]) for fact in facts
        if fact.get("kind") in LABELLED_KINDS and fact.get("source_type") == "document" and fact.get("source_id")
    ]
    if not document_ids:
        return overview
    # A medicine read off one copy of a prescription is verified when any copy is.
    states = merged_review_states(copy_groups(document_ids), doctor_id, viewer_department)

    def relabel(item: dict) -> dict:
        if item.get("source_type") != "document":
            return item
        label = _document_label(states.get(str(item.get("source_id"))))
        return {**item, "label": label} if label else item

    relabelled = {**overview, "facts": [relabel(fact) if fact.get("kind") in LABELLED_KINDS else fact
                                        for fact in facts]}
    if overview.get("mode") != "phrased":
        relabelled["lines"] = [
            {**group, "items": [relabel(item) for item in group.get("items") or []]}
            for group in overview.get("lines") or []
        ]
    return relabelled
