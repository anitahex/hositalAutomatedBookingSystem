"""Repair: document_catalog.original_filename on databases that never got migration 0002.

WHAT HAPPENED. On the production database, document_catalog was created by
app/db/schema_document_catalog.sql at app startup — which has no original_filename — and
the database was then stamped past 0002 rather than migrated through it. The column never
existed there. The code before this release knew (document_catalog._document_catalog_has
_original_filename falls back to the document id), but the doctor workspace's newer
queries read dc.original_filename directly, and every one of them failed with
UndefinedColumn: the visit brief, the timeline, the activity drill-down, the overview.

WHAT THIS DOES.
  1. Adds the column exactly as 0002 does. A no-op where 0002 already ran.
  2. Restores each document's real filename from pending_uploads, which recorded it at
     upload and is only ever marked consumed, never deleted. The filename matters beyond
     display: the original file is stored under vault/<user>/<session>/<document>/<name>,
     so with the placeholder name the viewer cannot find the file ("no longer available").
     Only rows still holding the placeholder are touched; a real name is never overwritten.

Idempotent, and safe on a fresh database (0001 creates pending_uploads).

revision: 0030_repair_document_catalog_filename
"""
from alembic import op

revision = "0030_repair_document_catalog_filename"
down_revision = "0029_summary_not_clinical"
branch_labels = None
depends_on = None

PLACEHOLDER = "uploaded-file"


def upgrade() -> None:
    op.execute(
        f"""
        ALTER TABLE document_catalog
            ADD COLUMN IF NOT EXISTS original_filename TEXT NOT NULL DEFAULT '{PLACEHOLDER}';

        DO $$
        BEGIN
            IF to_regclass('pending_uploads') IS NOT NULL THEN
                UPDATE document_catalog dc
                   SET original_filename = pu.original_filename
                  FROM (
                        SELECT DISTINCT ON (document_id) document_id, original_filename
                          FROM pending_uploads
                         WHERE COALESCE(original_filename, '') <> ''
                         ORDER BY document_id, created_at DESC
                       ) pu
                 WHERE pu.document_id = dc.document_id
                   AND dc.original_filename = '{PLACEHOLDER}';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Deliberately not dropping the column: 0002 owns it, and on databases where 0002
    # ran, dropping it here would destroy real filenames.
    pass
