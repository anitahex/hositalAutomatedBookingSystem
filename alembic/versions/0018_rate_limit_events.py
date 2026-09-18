"""Add rate_limit_events — a Postgres-backed sliding-window log replacing
app/services/doctor_auth.py::check_rate_limit's original in-memory implementation.

The in-memory version (a module-level dict guarded by a single process-wide Lock) is
correct only for a single worker process; it silently stops enforcing limits
correctly the moment this app scales to multiple workers or replicas, since each
process gets its own independent counters. This table makes the limiter correct
regardless of worker count. Self-pruning: old rows for a key are deleted on every
check (same convention as revoked_tokens/otp_verifications), no separate cleanup job.
"""
from alembic import op

revision = "0018_rate_limit_events"
down_revision = "0017_admin_patient_actions_log"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS rate_limit_events (
        id BIGSERIAL PRIMARY KEY,
        rate_key TEXT NOT NULL,
        occurred_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_rate_limit_events_key_time ON rate_limit_events(rate_key, occurred_at);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS rate_limit_events;")
