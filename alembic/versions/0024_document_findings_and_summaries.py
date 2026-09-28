"""Patient history, feature 3: measurements and grounded clinician summaries.

Two tables, both additive. Nothing existing is altered or dropped.

1. document_findings — one row per measurement, in Postgres rather than in a blob.

   The extractor already produces per-analyte values, but they live inside the summary
   JSON in blob storage, nested under a panel name, as strings. That is readable and
   unusable: flagging an abnormal result needs a number and a unit, and plotting Vitamin D
   across three reports needs a query, not three blob downloads and a join in Python.

   `canonical_name` is what a trend groups on — one measurement has many printed
   spellings ("Vitamin D, 25-Hydroxy (Total)", "25-OH Vitamin D"), and a series that did
   not collapse them would render as several one-point lines, which reads as no history
   rather than as a bug.

   `abnormal` is COMPUTED in Python against code-owned reference ranges and stored, never
   asked of a model. 'unknown' is a real and common value — no range for this analyte, or
   a unit that does not match the range's unit — and it means no flag is displayed. It is
   deliberately distinct from 'normal', which asserts that a range was actually applied.

   `value_operator` preserves a censored result ("<0.01"). Such a value is never
   classified and never plotted as a point, because it is a bound, not a measurement.

2. document_summaries — the clinician-register summary, sentence by sentence.

   Separate from the patient-facing summary already written to blob storage: the two have
   different registers, different audiences and different lifecycles, and overwriting one
   with the other would silently change what a patient sees.

   `sentences` holds only sentences that PASSED verification — each with the verbatim
   quote and the page it was found on, so a doctor can click through to the evidence and
   so the claim stays checkable long after the file is only in storage.

   `verification` records the outcome for the document as a whole: 'passed', 'partial'
   (some sentences dropped) or 'failed' (none survived — the UI then shows the structured
   findings and says no readable summary could be produced). A row with verification
   'failed' and no sentences is a legitimate, meaningful state.

Reversible. The downgrade drops both tables; everything in them is DERIVED from documents
that still exist, so it can be rebuilt by re-running extraction — unlike revision 0023,
whose snapshots are irreplaceable.

revision: 0024_document_findings_and_summaries
"""
from alembic import op

revision = "0024_document_findings_and_summaries"
down_revision = "0023_patient_history_capture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_findings (
            finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id TEXT NOT NULL,
            patient_id TEXT NOT NULL,
            panel TEXT,
            printed_name TEXT NOT NULL,
            canonical_name TEXT,
            value_text TEXT NOT NULL DEFAULT '',
            value_num NUMERIC,
            value_operator TEXT,
            unit TEXT,
            ref_low NUMERIC,
            ref_high NUMERIC,
            abnormal TEXT NOT NULL DEFAULT 'unknown'
                CHECK (abnormal IN ('low', 'high', 'normal', 'unknown')),
            clinical_date DATE,
            page_no INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            -- Re-extracting a document replaces its measurements rather than appending a
            -- second set; without this a re-run would double every point on a trend.
            UNIQUE (document_id, printed_name)
        );

        -- The trend query: this patient, this measurement, oldest to newest.
        CREATE INDEX IF NOT EXISTS idx_document_findings_trend
            ON document_findings(patient_id, canonical_name, clinical_date DESC);
        CREATE INDEX IF NOT EXISTS idx_document_findings_document
            ON document_findings(document_id);
        -- Abnormal chips for one patient, without scanning their normal results.
        CREATE INDEX IF NOT EXISTS idx_document_findings_abnormal
            ON document_findings(patient_id, abnormal) WHERE abnormal IN ('low', 'high');

        CREATE TABLE IF NOT EXISTS document_summaries (
            document_id TEXT PRIMARY KEY,
            sentences JSONB NOT NULL DEFAULT '[]'::jsonb,
            register TEXT NOT NULL DEFAULT 'clinician',
            model TEXT,
            prompt_version TEXT,
            verification TEXT NOT NULL DEFAULT 'failed'
                CHECK (verification IN ('passed', 'partial', 'failed')),
            rejected_count INTEGER NOT NULL DEFAULT 0,
            -- Whether the source text was a real PDF text layer or a vision
            -- transcription of a scan. The verification guarantee is materially weaker
            -- for the latter and the UI must be able to say so.
            source_kind TEXT,
            generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS document_summaries;
        DROP INDEX IF EXISTS idx_document_findings_abnormal;
        DROP INDEX IF EXISTS idx_document_findings_document;
        DROP INDEX IF EXISTS idx_document_findings_trend;
        DROP TABLE IF EXISTS document_findings;
        """
    )
