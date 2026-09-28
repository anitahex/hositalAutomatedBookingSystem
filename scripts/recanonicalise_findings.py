"""Re-derives the canonical name, reference range and flag of every stored measurement.

WHY THIS IS NEEDED. Those three are computed once, when a document is extracted, and then
stored. A correction to how names are canonicalised therefore reaches only documents
uploaded afterwards — rows already stored keep the old, wrong name, and keep feeding the
wrong analyte's trend and the at-a-glance card.

The case that prompted it: "Total Cholesterol / HDL Ratio" was stored as HDL Cholesterol,
with HDL's 40-100 mg/dL range. On the card, which takes one reading per analyte per date,
the ratio could be picked over the real (low) HDL result, so a low HDL disappeared.

WHAT IT DOES. Recomputes each row with document_findings' own functions and writes only
rows whose values actually change, so re-running it is a no-op. Drops the cached overview
cards of the affected patients, which were built from the old rows. Makes no model calls.

Run:  python scripts/recanonicalise_findings.py            (dry run: reports only)
      python scripts/recanonicalise_findings.py --apply    (writes the changes)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.document_findings import recanonicalise_stored_findings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    args = parser.parse_args()

    result = recanonicalise_stored_findings(dry_run=not args.apply)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    if not args.apply and result["changed"]:
        print("\nDry run — nothing written. Re-run with --apply to write these changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
