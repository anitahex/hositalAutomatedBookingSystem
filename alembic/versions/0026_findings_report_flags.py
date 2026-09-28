"""The report's own flag and reference range, beside each measurement.

WHY. `abnormal` was computed only against a code-owned table of 19 analytes. Anything
outside it — RDW, VLDL, a ratio — stayed 'unknown' and was never shown as abnormal, even
when the lab had printed "H" beside it. On a real report the lab flagged 12 results and the
doctor's viewer showed 8. The lab's flag and printed range are facts IN the document; they
are now read (by code, from the line the value is printed on) and take precedence.

  report_flag      the flag token exactly as printed ("H", "L", "HH", "*"), or NULL
  report_ref_text  the printed range exactly as printed ("11.6 - 14.0", "Desirable: < 200")
  ref_source       where ref_low/ref_high came from: 'report' (printed) or 'standard'
                   (the code-owned table, used only when the report prints none)
  flag_source      what decided `abnormal`: the report's flag, the report's range, or the
                   standard range. NULL when nothing did ('unknown').
  critical         the report marked it critical (HH, LL, "Critical", "Panic")

`abnormal` keeps its four values, so every existing reader — the overview, the visit
brief, trends — picks up the corrected flags without a change.

revision: 0026_findings_report_flags
"""
from alembic import op

revision = "0026_findings_report_flags"
down_revision = "0025_patient_overview_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE document_findings
            ADD COLUMN IF NOT EXISTS report_flag TEXT,
            ADD COLUMN IF NOT EXISTS report_ref_text TEXT,
            ADD COLUMN IF NOT EXISTS ref_source TEXT
                CHECK (ref_source IN ('report', 'standard')),
            ADD COLUMN IF NOT EXISTS flag_source TEXT
                CHECK (flag_source IN ('report_flag', 'report_range', 'standard_range')),
            ADD COLUMN IF NOT EXISTS critical BOOLEAN NOT NULL DEFAULT FALSE;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE document_findings
            DROP COLUMN IF EXISTS critical,
            DROP COLUMN IF EXISTS flag_source,
            DROP COLUMN IF EXISTS ref_source,
            DROP COLUMN IF EXISTS report_ref_text,
            DROP COLUMN IF EXISTS report_flag;
        """
    )
