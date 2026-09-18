"""Add admin_patient_actions_log for admin actions taken on a patient's behalf
(currently: MFA reset). Nothing generic for "admin action on a patient" existed
before — doctor_auth_audit_log is doctor-scoped, unified_auth_audit_log is login-only.
"""
from alembic import op

revision = "0017_admin_patient_actions_log"
down_revision = "0016_patient_mfa_last_step"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    CREATE TABLE IF NOT EXISTS admin_patient_actions_log (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        admin_email TEXT NOT NULL,
        patient_id UUID NOT NULL,
        action TEXT NOT NULL,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_admin_patient_actions_log_patient
        ON admin_patient_actions_log(patient_id, created_at DESC);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS admin_patient_actions_log;")
