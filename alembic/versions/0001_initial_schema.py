"""Initial schema with all tables and indexes

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-24

"""
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.execute(
        """
        CREATE TABLE users (
            user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE patient_profiles (
            user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            age INTEGER NOT NULL CHECK (age > 0 AND age < 130),
            mobile_number TEXT NOT NULL,
            address TEXT NOT NULL,
            email TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            health_issues TEXT,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE doctors (
            doctor_id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            experience_years INTEGER NOT NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE appointment_slots (
            slot_id UUID PRIMARY KEY,
            doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            is_booked BOOLEAN NOT NULL DEFAULT FALSE,
            booked_by_patient_id TEXT,
            UNIQUE (doctor_id, start_time)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE appointment_bookings (
            booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slot_id UUID NOT NULL REFERENCES appointment_slots(slot_id) ON DELETE CASCADE,
            doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
            patient_id TEXT,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            status TEXT NOT NULL DEFAULT 'booked',
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE chat_sessions (
            chat_session_id UUID PRIMARY KEY,
            patient_id TEXT NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            llm_calls INTEGER NOT NULL DEFAULT 0,
            chat_summary TEXT NOT NULL DEFAULT '',
            started_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE llm_token_usage (
            usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chat_session_id UUID NOT NULL REFERENCES chat_sessions(chat_session_id) ON DELETE CASCADE,
            patient_id TEXT NOT NULL,
            model TEXT NOT NULL,
            call_type TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE token_logs (
            session_id VARCHAR NOT NULL,
            patient_id VARCHAR NOT NULL,
            node_name VARCHAR NOT NULL,
            model_name VARCHAR NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            status VARCHAR NOT NULL CHECK (status IN ('SUCCESS', 'ERROR')),
            latency_ms INTEGER NOT NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE chat_messages (
            message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id TEXT NOT NULL,
            chat_session_id UUID,
            role TEXT NOT NULL CHECK (role IN ('patient', 'assistant')),
            text TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute(
        "CREATE INDEX idx_doctors_department ON doctors(department);"
    )

    op.execute(
        """
        CREATE INDEX idx_slots_available ON appointment_slots(start_time)
        WHERE is_booked = FALSE;
        """
    )

    op.execute(
        """
        CREATE INDEX idx_appointment_bookings_active
        ON appointment_bookings(slot_id, end_time)
        WHERE status = 'booked';
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX ux_appointment_bookings_booked_slot
        ON appointment_bookings(slot_id)
        WHERE status = 'booked';
        """
    )

    op.execute(
        """
        CREATE INDEX idx_llm_token_usage_session_created
        ON llm_token_usage(chat_session_id, created_at);
        """
    )

    op.execute(
        """
        CREATE INDEX idx_chat_sessions_patient_updated
        ON chat_sessions(patient_id, updated_at);
        """
    )

    op.execute(
        "CREATE INDEX idx_token_logs_session ON token_logs(session_id);"
    )

    op.execute(
        "CREATE INDEX idx_token_logs_patient ON token_logs(patient_id);"
    )

    op.execute(
        """
        CREATE INDEX idx_chat_messages_patient_created
        ON chat_messages(patient_id, created_at);
        """
    )

    op.execute(
        """
        CREATE INDEX idx_chat_messages_patient_session_created
        ON chat_messages(patient_id, chat_session_id, created_at);
        """
    )

    # Document catalog tables
    op.execute(
        """
        CREATE TABLE document_catalog (
            document_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            document_type TEXT,
            clinical_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            blob_summary_path TEXT NOT NULL,
            findings_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
            ingestion_status TEXT NOT NULL DEFAULT 'processing'
                CONSTRAINT document_catalog_status_check
                    CHECK (ingestion_status IN ('processing', 'complete', 'failed'))
        );
        """
    )

    op.execute(
        """
        CREATE INDEX idx_document_catalog_user_status_date
        ON document_catalog (user_id, ingestion_status, created_at DESC);
        """
    )

    op.execute(
        """
        CREATE TABLE pending_uploads (
            document_token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            blob_path TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            consumed BOOLEAN NOT NULL DEFAULT FALSE
        );
        """
    )

    op.execute(
        """
        CREATE INDEX idx_pending_uploads_created_at
        ON pending_uploads (created_at)
        WHERE consumed = FALSE;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_pending_uploads_created_at;")
    op.execute("DROP TABLE IF EXISTS pending_uploads;")
    op.execute("DROP INDEX IF EXISTS idx_document_catalog_user_status_date;")
    op.execute("DROP TABLE IF EXISTS document_catalog;")
    op.execute("DROP INDEX IF EXISTS idx_chat_messages_patient_session_created;")
    op.execute("DROP INDEX IF EXISTS idx_chat_messages_patient_created;")
    op.execute("DROP INDEX IF EXISTS idx_token_logs_patient;")
    op.execute("DROP INDEX IF EXISTS idx_token_logs_session;")
    op.execute("DROP INDEX IF EXISTS idx_chat_sessions_patient_updated;")
    op.execute("DROP INDEX IF EXISTS idx_llm_token_usage_session_created;")
    op.execute("DROP INDEX IF EXISTS ux_appointment_bookings_booked_slot;")
    op.execute("DROP INDEX IF EXISTS idx_appointment_bookings_active;")
    op.execute("DROP INDEX IF EXISTS idx_slots_available;")
    op.execute("DROP INDEX IF EXISTS idx_doctors_department;")
    op.execute("DROP TABLE IF EXISTS chat_messages;")
    op.execute("DROP TABLE IF EXISTS token_logs;")
    op.execute("DROP TABLE IF EXISTS llm_token_usage;")
    op.execute("DROP TABLE IF EXISTS chat_sessions;")
    op.execute("DROP TABLE IF EXISTS appointment_bookings;")
    op.execute("DROP TABLE IF EXISTS appointment_slots;")
    op.execute("DROP TABLE IF EXISTS doctors;")
    op.execute("DROP TABLE IF EXISTS patient_profiles;")
    op.execute("DROP TABLE IF EXISTS users;")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
