"""Bring the consult/SOAP feature schema into Alembic (closes TECH_DEBT.md #4).

Previously this entire schema (consultations, transcript_segments,
keyterm_vocabulary, consult_audit_log, soap_notes, soap_note_addenda) existed
only via idempotent runtime DDL in ensure_consult_schema()/ensure_soap_schema()
(app/services/consults.py, app/services/soap_notes.py) — those functions still
run on every request and are left in place unchanged; every statement here uses
the same IF NOT EXISTS guards so the two mechanisms coexist safely, matching how
0004/0005 already coexist with ensure_doctor_auth_schema()/ensure_admin_schema().
This migration is a byte-for-byte match of that runtime DDL as it exists today,
including the ux_consultations_active_booking unique index added this session
(FULL_SYSTEM_AUDIT.md P1 #8).
"""
from alembic import op

revision = "0007_consult_and_soap_schema"
down_revision = "0006_patient_lockout_and_token_revocation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS consultations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            booking_id UUID NOT NULL REFERENCES appointment_bookings(booking_id) ON DELETE CASCADE,
            doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
            patient_id TEXT,
            status TEXT NOT NULL DEFAULT 'not_started',
            consent_confirmed_by UUID,
            consent_confirmed_at TIMESTAMP,
            started_at TIMESTAMP,
            ended_at TIMESTAMP,
            audio_blob_path TEXT,
            audio_sample_rate INTEGER,
            transcript_source TEXT,
            transcript_fallback_error TEXT,
            retention_expires_at TIMESTAMP,
            audio_deleted_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_consultations_doctor ON consultations(doctor_id);
        CREATE INDEX IF NOT EXISTS idx_consultations_booking ON consultations(booking_id);
        CREATE INDEX IF NOT EXISTS idx_consultations_retention
            ON consultations(retention_expires_at)
            WHERE audio_deleted_at IS NULL AND audio_blob_path IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS ux_consultations_active_booking
            ON consultations(booking_id)
            WHERE status IN ('recording', 'transcribing', 'transcript_ready');

        CREATE TABLE IF NOT EXISTS transcript_segments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            consultation_id UUID NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
            speaker TEXT NOT NULL DEFAULT 'unknown',
            start_ms INTEGER NOT NULL,
            end_ms INTEGER NOT NULL,
            text TEXT NOT NULL,
            confidence REAL,
            is_final BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_transcript_segments_consultation
            ON transcript_segments(consultation_id, start_ms);

        CREATE TABLE IF NOT EXISTS keyterm_vocabulary (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            term TEXT NOT NULL,
            department TEXT,
            source TEXT NOT NULL DEFAULT 'doctor_submitted',
            created_by UUID,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_keyterm_vocabulary_department ON keyterm_vocabulary(department);

        CREATE TABLE IF NOT EXISTS consult_audit_log (
            audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            consultation_id UUID REFERENCES consultations(id) ON DELETE SET NULL,
            doctor_id UUID REFERENCES doctors(doctor_id) ON DELETE SET NULL,
            action_type TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_consult_audit_consultation
            ON consult_audit_log(consultation_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS soap_notes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            consultation_id UUID NOT NULL UNIQUE REFERENCES consultations(id) ON DELETE CASCADE,
            doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
            patient_id TEXT,
            subjective TEXT,
            objective TEXT,
            assessment TEXT,
            plan TEXT,
            field_citations JSONB NOT NULL DEFAULT '{}'::jsonb,
            confidence_flags JSONB NOT NULL DEFAULT '{}'::jsonb,
            status TEXT NOT NULL DEFAULT 'draft',
            generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            edited_at TIMESTAMP,
            signed_at TIMESTAMP,
            signed_by UUID,
            shared_with_patient_at TIMESTAMP,
            shared_by UUID,
            source_transcript_type TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_soap_notes_doctor ON soap_notes(doctor_id);
        CREATE INDEX IF NOT EXISTS idx_soap_notes_patient_shared
            ON soap_notes(patient_id)
            WHERE shared_with_patient_at IS NOT NULL;

        CREATE TABLE IF NOT EXISTS soap_note_addenda (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            soap_note_id UUID NOT NULL REFERENCES soap_notes(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            added_by UUID NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_soap_note_addenda_note
            ON soap_note_addenda(soap_note_id, created_at);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS soap_note_addenda;")
    op.execute("DROP TABLE IF EXISTS soap_notes;")
    op.execute("DROP TABLE IF EXISTS consult_audit_log;")
    op.execute("DROP TABLE IF EXISTS keyterm_vocabulary;")
    op.execute("DROP TABLE IF EXISTS transcript_segments;")
    op.execute("DROP INDEX IF EXISTS ux_consultations_active_booking;")
    op.execute("DROP TABLE IF EXISTS consultations;")
