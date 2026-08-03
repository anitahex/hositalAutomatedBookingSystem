"""Add original filename to document catalog.

Revision ID: 0002_add_document_original_filename
Revises: 0001_initial_schema
Create Date: 2026-07-07
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "0002_add_document_original_filename"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE document_catalog
        ADD COLUMN IF NOT EXISTS original_filename TEXT NOT NULL DEFAULT 'uploaded-file';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE document_catalog
        DROP COLUMN IF EXISTS original_filename;
        """
    )
