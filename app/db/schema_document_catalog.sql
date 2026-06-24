-- ============================================================
-- Document catalog: metadata-only index for user-uploaded
-- document summaries. Clinical content lives in blob storage.
-- Run this once against the hospital_db database.
-- ============================================================

CREATE TABLE IF NOT EXISTS document_catalog (
    document_id         TEXT            PRIMARY KEY,
    user_id             TEXT            NOT NULL,
    session_id          TEXT            NOT NULL,
    document_type       TEXT,
    clinical_date       DATE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    blob_summary_path   TEXT            NOT NULL,
    findings_keys       JSONB           NOT NULL DEFAULT '[]'::jsonb,
    ingestion_status    TEXT            NOT NULL DEFAULT 'processing'
        CONSTRAINT document_catalog_status_check
            CHECK (ingestion_status IN ('processing', 'complete', 'failed'))
);

-- Fast lookups for list_user_documents() and document_discovery
CREATE INDEX IF NOT EXISTS idx_document_catalog_user_status_date
    ON document_catalog (user_id, ingestion_status, created_at DESC);


-- ============================================================
-- Pending uploads: short-lived staging records for consent
-- gating. Records expire after 30 minutes (enforced in the
-- application WHERE clause; a periodic cleanup job can also
-- DELETE FROM pending_uploads WHERE created_at < NOW() - INTERVAL '30 minutes').
-- ============================================================

CREATE TABLE IF NOT EXISTS pending_uploads (
    document_token      TEXT            PRIMARY KEY,
    user_id             TEXT            NOT NULL,
    session_id          TEXT            NOT NULL,
    document_id         TEXT            NOT NULL,
    blob_path           TEXT            NOT NULL,
    original_filename   TEXT            NOT NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    consumed            BOOLEAN         NOT NULL DEFAULT FALSE
);

-- For cleanup job: purge expired unconsumed staging records
CREATE INDEX IF NOT EXISTS idx_pending_uploads_created_at
    ON pending_uploads (created_at)
    WHERE consumed = FALSE;
