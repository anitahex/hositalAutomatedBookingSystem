"""Re-derives every stored measurement, reading the report's own flags and ranges.

WHY THIS IS NEEDED. A measurement's name, number, flag and range are computed once, when a
document is extracted, and stored. Three corrections only reach documents uploaded after
them unless stored rows are re-derived:

  - the report's own flag and printed range now decide abnormal (a real report flagged 12
    results; the viewer showed 8, because only 19 analytes had a range in code)
  - "7,850" is seven thousand eight hundred and fifty, not 7.85
  - "Total Cholesterol / HDL Ratio" is its own measurement, not HDL Cholesterol

WHAT IT DOES. Recomputes each row from its printed name, printed value and its document's
stored page text (document_findings.rederive_stored_findings), writes only rows that
change, and rebuilds the cached at-a-glance cards of the patients affected. Makes no model
calls for the findings; rebuilding a card may make one phrasing call per card.

Run:  python scripts/reflag_findings.py            (dry run: reports only)
      python scripts/reflag_findings.py --apply    (writes the changes)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.document_findings import rederive_stored_findings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    parser.add_argument("--patient", help="limit to one patient id")
    args = parser.parse_args()

    # The cards that exist now: the re-derivation drops a changed patient's cards (they were
    # built from the old rows), and they are rebuilt afterwards so the next doctor to open
    # one of these patients does not wait on a model call.
    cards = _existing_cards(args.patient) if args.apply else []

    result = rederive_stored_findings(dry_run=not args.apply, patient_id=args.patient)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    if not args.apply:
        if result["changed"]:
            print("\nDry run — nothing written. Re-run with --apply to write these changes.")
        return 0

    print(f"overview cards rebuilt: {asyncio.run(_rebuild(cards))}")
    return 0


async def _rebuild(cards: list[tuple[str, str]]) -> int:
    """All in ONE event loop: the model client is created once and bound to the loop it was
    first used on, so an asyncio.run() per card failed every card after the first with
    "Event loop is closed" and left them in the facts-only fallback."""
    from app.services.patient_overview import get_overview

    for patient_id, department in cards:
        # get_overview rebuilds when no card is stored; doctor_id is not used in building
        # a card (it is per patient and viewing department), hence None.
        await get_overview(None, patient_id, department or None)
    return len(cards)


def _existing_cards(patient_id: str | None) -> list[tuple[str, str]]:
    from app.db.connection import connect_db

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT o.patient_id, o.viewer_department FROM patient_overviews o
                   WHERE EXISTS (SELECT 1 FROM document_findings f WHERE f.patient_id = o.patient_id)
                     AND (%(p)s::text IS NULL OR o.patient_id = %(p)s)""",
                {"p": patient_id},
            )
            return [(row[0], row[1]) for row in cur.fetchall()]


if __name__ == "__main__":
    raise SystemExit(main())
