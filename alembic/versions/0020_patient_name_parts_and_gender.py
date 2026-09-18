"""Split patient_profiles.name into first_name/last_name and add gender, for the
editable profile form.

name is deliberately kept and maintained as the combined value rather than dropped:
the chat greeting, admin appointment cards, doctor dashboards and several queries all
read p.name, and rewriting every one of them to concatenate would be a much larger
change for no benefit. update_patient_profile keeps it in sync on every write.

Backfill splits on the first space — everything before it is the first name, everything
after is the last name. A single-word name backfills as first_name only, which is the
honest reading of "Priya" rather than guessing.

revision: 0020_patient_name_parts_and_gender
"""
from alembic import op

revision = "0020_patient_name_parts_and_gender"
down_revision = "0019_login_lockouts"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS first_name TEXT;
    ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS last_name TEXT;
    ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS gender TEXT;

    UPDATE patient_profiles
    SET first_name = NULLIF(split_part(trim(name), ' ', 1), ''),
        last_name = NULLIF(trim(substring(trim(name) FROM position(' ' IN trim(name)) + 1)), '')
    WHERE first_name IS NULL
      AND name IS NOT NULL;

    -- position() returns 0 when there is no space at all, which would make the
    -- substring above repeat the whole name as the last name too. Clear those.
    UPDATE patient_profiles
    SET last_name = NULL
    WHERE last_name IS NOT NULL
      AND name IS NOT NULL
      AND position(' ' IN trim(name)) = 0;
    """)


def downgrade():
    op.execute("""
    ALTER TABLE patient_profiles DROP COLUMN IF EXISTS first_name;
    ALTER TABLE patient_profiles DROP COLUMN IF EXISTS last_name;
    ALTER TABLE patient_profiles DROP COLUMN IF EXISTS gender;
    """)
