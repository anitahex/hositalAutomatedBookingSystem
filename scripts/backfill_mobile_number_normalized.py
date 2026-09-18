"""Backfill patient_profiles.mobile_number_normalized for existing rows.

Standalone script, not an Alembic migration — this is a data operation reusing
app-level normalization logic (app/services/users.py::normalize_mobile_number_india),
not schema DDL. Processes in batches of ~2000 rows ordered by user_id, committing per
batch rather than one giant transaction. Anything that doesn't normalize to one of the
three recognized shapes is left NULL and logged for manual review — never guessed.

Run manually, after 0012_add_mobile_number_normalized_column.py has been applied and
before 0013_add_mobile_normalized_unique_index.py:

    python scripts/backfill_mobile_number_normalized.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.connection import connect_db
from app.services.users import normalize_mobile_number_india

BATCH_SIZE = 2000


def backfill():
    total_updated = 0
    total_needs_review = 0
    last_user_id = None

    while True:
        with connect_db() as conn:
            with conn.cursor() as cur:
                if last_user_id is None:
                    cur.execute(
                        """
                        SELECT user_id, mobile_number FROM patient_profiles
                        WHERE mobile_number_normalized IS NULL
                        ORDER BY user_id
                        LIMIT %s;
                        """,
                        (BATCH_SIZE,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT user_id, mobile_number FROM patient_profiles
                        WHERE mobile_number_normalized IS NULL AND user_id > %s
                        ORDER BY user_id
                        LIMIT %s;
                        """,
                        (last_user_id, BATCH_SIZE),
                    )
                rows = cur.fetchall()

                if not rows:
                    break

                for user_id, mobile_number in rows:
                    normalized = normalize_mobile_number_india(mobile_number)
                    if normalized is None:
                        total_needs_review += 1
                        print(f"[needs-review] user_id={user_id} mobile_number={mobile_number!r} did not normalize", flush=True)
                        continue
                    cur.execute(
                        "UPDATE patient_profiles SET mobile_number_normalized = %s WHERE user_id = %s;",
                        (normalized, user_id),
                    )
                    total_updated += 1

                last_user_id = rows[-1][0]
            conn.commit()

        print(f"[batch] processed {len(rows)} rows, last user_id={last_user_id}", flush=True)

    print(f"Done. Updated: {total_updated}. Needs manual review (left NULL): {total_needs_review}.")


if __name__ == "__main__":
    backfill()
