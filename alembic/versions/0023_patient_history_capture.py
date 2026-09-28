"""Patient history, phase 1a: capture what is currently being thrown away.

This revision ships BEFORE any screen that reads it, deliberately. The pre-visit context
it records does not exist anywhere today — not in a table, not in a log, not in a blob —
so every appointment booked before it is applied is permanently unreconstructable. There
is no backfill for booking_context_snapshots and there never can be one.

Purely additive: no column is dropped, no type changed, no existing row rewritten. Safe to
apply ahead of the reading code and safe under a rolling deploy.

1. booking_context_snapshots — what happened before the visit.

   appointment_bookings records booking_note and nothing else. Which conversation produced
   the booking, what the assistant recommended, what the patient actually chose, and which
   documents they uploaded while booking all live in transient LangGraph state that is
   discarded when the turn ends.

   The snapshot is IMMUTABLE by construction, not by convention. It holds its own
   ai_summary and its own explicit document_ids list, and pins the transcript to a
   message-id range rather than to "the session", because a session keeps growing. It is
   written in the same transaction as the booking row and there is no UPDATE path to it
   anywhere in the codebase — a later edit to the conversation cannot change what this
   appointment shows a doctor.

   UNIQUE on booking_id: one booking, one context, enforced by the database rather than by
   the caller remembering.

2. document_pages — per-page source text.

   document_pipeline._extract_pdf_text already walks pages but flattens them with
   "\\n\\n".join(chunks) and persists nothing, so page numbers are lost the moment
   extraction finishes. Grounded per-document summaries have to quote a page and be
   verifiable against it later, which needs the text kept. `source` distinguishes a real
   PDF text layer from a vision transcription of a scan — the verification guarantee is
   materially weaker for the latter and callers must be able to tell them apart.

3. document_catalog: booking_id, source_doctor_id, referring_doctor, referring_department,
   body_region.

   The extractor already returns referring_doctor, referring_department and body_region
   (azure_client.gpt4o_structured_extraction) and chat.py drops all three on the floor when
   it builds the summary payload. These columns stop that. booking_id answers "which
   appointment did this document arrive with", which today can only be guessed by matching
   session ids.

4. appointment_bookings.status gains 'no_show'.

   The constraint is widened here so the value is legal; nothing sets it yet, and the
   action that does is a later phase. Widening a CHECK is safe in both directions as long
   as no row uses the new value, which is why the downgrade re-narrows it only after
   asserting that.

Reversible. The downgrade drops the snapshot table, which discards every pre-visit context
recorded while this revision was applied — that data cannot be recovered from anywhere
else, so a downgrade is a real loss of clinical context, not just of a schema object.

revision: 0023_patient_history_capture
"""
from alembic import op

revision = "0023_patient_history_capture"
down_revision = "0022_doctor_workspace_ai"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS booking_context_snapshots (
            snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            booking_id UUID NOT NULL UNIQUE
                REFERENCES appointment_bookings(booking_id) ON DELETE CASCADE,
            patient_id TEXT,
            chat_session_id UUID,
            -- The frozen transcript window, as an INCLUSIVE timestamp range. NULL when
            -- the booking did not come from a conversation (the REST booking route),
            -- which is a real case, not a gap.
            --
            -- Timestamps, not message ids, because chat_messages.created_at defaults to
            -- now() and a turn writes the patient message and the assistant reply in ONE
            -- transaction — so both rows carry the SAME created_at. Verified on live
            -- data: one session holds 26 messages across 13 distinct timestamps. Ordering
            -- by created_at is therefore ambiguous, and any id-based "first and last"
            -- would pick arbitrarily between the two halves of a turn. A boundary is
            -- exact: "everything said up to the moment this was booked", and a tie at the
            -- edge resolves inclusively, which keeps both halves of the final turn.
            transcript_from_at TIMESTAMP,
            transcript_to_at TIMESTAMP,
            transcript_message_count INTEGER NOT NULL DEFAULT 0,
            -- {why_came, symptoms_verbatim, duration, severity, concerns,
            --  questions_asked, red_flags[]}. Empty object until the summariser runs;
            --  the snapshot is still useful without it.
            ai_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
            ai_summary_status TEXT NOT NULL DEFAULT 'pending'
                CHECK (ai_summary_status IN ('pending', 'complete', 'failed', 'skipped')),
            -- What the assistant proposed vs what the patient actually got. Stored
            -- separately and both nullable: "the assistant had no opinion" and "the
            -- assistant agreed" are different facts, and neither may be inferred from
            -- the other.
            suggested_department TEXT,
            chosen_department TEXT,
            department_match_source TEXT,
            department_match_reason TEXT,
            document_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_booking_snapshots_patient
            ON booking_context_snapshots(patient_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS document_pages (
            document_id TEXT NOT NULL,
            page_no INTEGER NOT NULL CHECK (page_no >= 1),
            text TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL CHECK (source IN ('pdf_text', 'vision_transcription')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (document_id, page_no)
        );

        ALTER TABLE document_catalog
            ADD COLUMN IF NOT EXISTS booking_id UUID,
            ADD COLUMN IF NOT EXISTS source_doctor_id UUID,
            ADD COLUMN IF NOT EXISTS referring_doctor TEXT,
            ADD COLUMN IF NOT EXISTS referring_department TEXT,
            ADD COLUMN IF NOT EXISTS body_region TEXT;

        CREATE INDEX IF NOT EXISTS idx_document_catalog_booking
            ON document_catalog(booking_id) WHERE booking_id IS NOT NULL;

        ALTER TABLE appointment_bookings DROP CONSTRAINT IF EXISTS appointment_bookings_status_check;
        ALTER TABLE appointment_bookings ADD CONSTRAINT appointment_bookings_status_check
            CHECK (status IN ('booked', 'completed', 'cancelled', 'no_show'));
        """
    )


def downgrade() -> None:
    op.execute(
        """
        -- Re-narrowing the CHECK would fail on any row already marked no_show, which is
        -- the correct outcome: silently rewriting a real clinical status to make a
        -- downgrade succeed would falsify the record. Fix the rows first, then downgrade.
        ALTER TABLE appointment_bookings DROP CONSTRAINT IF EXISTS appointment_bookings_status_check;
        ALTER TABLE appointment_bookings ADD CONSTRAINT appointment_bookings_status_check
            CHECK (status IN ('booked', 'completed', 'cancelled'));

        DROP INDEX IF EXISTS idx_document_catalog_booking;
        ALTER TABLE document_catalog
            DROP COLUMN IF EXISTS body_region,
            DROP COLUMN IF EXISTS referring_department,
            DROP COLUMN IF EXISTS referring_doctor,
            DROP COLUMN IF EXISTS source_doctor_id,
            DROP COLUMN IF EXISTS booking_id;

        DROP TABLE IF EXISTS document_pages;
        DROP INDEX IF EXISTS idx_booking_snapshots_patient;
        DROP TABLE IF EXISTS booking_context_snapshots;
        """
    )
