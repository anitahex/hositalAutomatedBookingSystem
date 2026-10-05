"""Earlier versions of a document's summary and measurements, kept when they are replaced.

WHY. A document's summary (document_summaries) and its measurements (document_findings) are
rewritten in place when it is processed again — re-summarised after a prompt fix, re-flagged
after a rule fix, re-extracted. Before this, the text a doctor had verified was simply gone:
the verification stopped applying (it is tied to the summary it was made against) and nothing
showed what had been verified or why it changed. A medical record must not lose what a
clinician confirmed.

WHAT IS KEPT. The row as it stood, whole (`previous`, every column, so nothing is lost when a
column is added later), with when and by what it was replaced. Copied in the SAME transaction
as the overwrite, by the code that overwrites — so there is no path that replaces a row
without keeping it.

The app creates these tables at startup too (production's database is stamped rather than
migrated); migration 0034 creates them for a migrated one.
"""
from __future__ import annotations

from app.db.schema_once import once_per_process

REPLACED_BY_RESUMMARY = "summary regenerated"
REPLACED_BY_EXTRACTION = "measurements re-extracted"
REPLACED_BY_REFLAG = "measurements re-derived"


@once_per_process
def ensure_document_versions_schema(conn) -> None:
    """Also created by migration 0034; here too for production's stamped database."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS document_summary_versions (
                id BIGSERIAL PRIMARY KEY,
                document_id TEXT NOT NULL,
                generated_at TIMESTAMPTZ,
                previous JSONB NOT NULL,
                replaced_by TEXT NOT NULL,
                replaced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_document_summary_versions_document
                ON document_summary_versions (document_id, generated_at DESC);
            CREATE TABLE IF NOT EXISTS document_findings_versions (
                id BIGSERIAL PRIMARY KEY,
                document_id TEXT NOT NULL,
                printed_name TEXT,
                previous JSONB NOT NULL,
                replaced_by TEXT NOT NULL,
                replaced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_document_findings_versions_document
                ON document_findings_versions (document_id, replaced_at DESC);
            """
        )
    conn.commit()


def archive_summary(cur, document_id: str, replaced_by: str) -> int:
    """Keeps the document's current summary before it is replaced. Returns rows kept (0/1)."""
    cur.execute(
        """
        INSERT INTO document_summary_versions (document_id, generated_at, previous, replaced_by)
        SELECT s.document_id, s.generated_at, to_jsonb(s), %s
        FROM document_summaries s
        WHERE s.document_id = %s
        """,
        (replaced_by, str(document_id)),
    )
    return cur.rowcount


def archive_findings(cur, finding_ids: list, replaced_by: str) -> int:
    """Keeps these measurement rows as they stand, before they are changed."""
    ids = [str(finding_id) for finding_id in finding_ids or []]
    if not ids:
        return 0
    cur.execute(
        """
        INSERT INTO document_findings_versions (document_id, printed_name, previous, replaced_by)
        SELECT f.document_id, f.printed_name, to_jsonb(f), %s
        FROM document_findings f
        WHERE f.finding_id::text = ANY(%s)
        """,
        (replaced_by, ids),
    )
    return cur.rowcount


def summary_versions(document_id: str) -> list[dict]:
    """The document's earlier summaries, newest first: {"generated_at", "sentences",
    "verification", "replaced_by", "replaced_at"}."""
    from app.db.connection import connect_db

    with connect_db() as conn:
        ensure_document_versions_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT generated_at, previous, replaced_by, replaced_at
                FROM document_summary_versions
                WHERE document_id = %s
                ORDER BY generated_at DESC NULLS LAST, replaced_at DESC
                """,
                (str(document_id),),
            )
            rows = cur.fetchall()
        conn.commit()
    return [
        {"generated_at": generated_at.isoformat() if generated_at else None,
         "sentences": (previous or {}).get("sentences") or [],
         "verification": (previous or {}).get("verification"),
         "replaced_by": replaced_by,
         "replaced_at": replaced_at.isoformat() if replaced_at else None}
        for generated_at, previous, replaced_by, replaced_at in rows
    ]
