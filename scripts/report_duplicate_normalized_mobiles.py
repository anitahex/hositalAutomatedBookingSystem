"""Report duplicate patient_profiles.mobile_number_normalized values.

Read-only — never auto-resolves anything. Run after the backfill script and before
0013_add_mobile_normalized_unique_index.py, which will fail outright if any duplicates
are still present (CREATE UNIQUE INDEX rejects duplicate values). Flag any output here
for human review before proceeding.

    python scripts/report_duplicate_normalized_mobiles.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.connection import connect_db


def report_duplicates():
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT mobile_number_normalized, array_agg(user_id ORDER BY user_id)
                FROM patient_profiles
                WHERE mobile_number_normalized IS NOT NULL
                GROUP BY mobile_number_normalized
                HAVING COUNT(*) > 1
                ORDER BY mobile_number_normalized;
                """
            )
            rows = cur.fetchall()

    if not rows:
        print("No duplicates found.")
        return 0

    print(f"Found {len(rows)} duplicate normalized mobile number(s):")
    for normalized, user_ids in rows:
        print(f"  {normalized} -> {len(user_ids)} accounts: {[str(u) for u in user_ids]}")
    return len(rows)


if __name__ == "__main__":
    count = report_duplicates()
    sys.exit(1 if count else 0)
