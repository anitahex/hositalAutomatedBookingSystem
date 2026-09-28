"""Patient history, feature 4: the at-a-glance overview card's cache.

One table. The card is composed from a model call, and it is read on every patient open,
so recomputing it each time would add a model round-trip and its cost to opening a
patient's record.

KEYED BY (patient_id, viewer_department), not by patient alone. The card obeys the same
sensitive-specialty restriction as the timeline, so its CONTENT differs by who is looking:
a cardiologist's card for a patient omits what a psychiatrist's includes. A cache keyed on
the patient alone would serve one doctor's card to another and silently undo the
restriction — the most dangerous possible caching bug here, because it would look like a
performance optimisation. NULL departments collapse to '' so the primary key holds.

`source_changed_at` is what makes the cache self-correcting. It records the newest input
the card was built from; a read compares it against the newest input that exists now and
rebuilds if anything has moved. That is deliberately used INSTEAD of invalidation hooks in
every writer: a cache that depends on each writer remembering to call invalidate() goes
stale the first time somebody adds a writer and forgets, and it does so silently.

`mode` records whether the doctor is reading phrased prose or the structured fallback, so
"the model's phrasing failed verification" is visible in the data rather than only
inferable from the shape of `lines`.

Reversible, and cheap to reverse: everything here is derived and rebuilds on next read.

revision: 0025_patient_overview_cache
"""
from alembic import op

revision = "0025_patient_overview_cache"
down_revision = "0024_document_findings_and_summaries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS patient_overviews (
            patient_id TEXT NOT NULL,
            -- '' rather than NULL for "no department recorded", so the primary key works.
            viewer_department TEXT NOT NULL DEFAULT '',
            lines JSONB NOT NULL DEFAULT '[]'::jsonb,
            facts JSONB NOT NULL DEFAULT '[]'::jsonb,
            mode TEXT NOT NULL DEFAULT 'structured'
                CHECK (mode IN ('phrased', 'structured')),
            reason TEXT,
            prompt_version TEXT,
            source_changed_at TIMESTAMP,
            generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (patient_id, viewer_department)
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS patient_overviews;")
