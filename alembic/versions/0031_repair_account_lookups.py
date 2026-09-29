"""Repair: accounts older than the registry could not log in or recover their password.

WHAT HAPPENED. Login finds an account through account_email_registry, never through the
account tables themselves. Migration 0005 created the registry and copied every existing
account into it — but the app's startup also creates that table, and 0005's plain CREATE
TABLE then fails, so on a database where the app ran first 0005 was stamped rather than
run and the copy never happened. Every account older than the registry was invisible to
login: "Invalid email or password" with the right password, and again after a successful
password reset — which is exactly "forgot password cannot recover old accounts".

The mobile path had the same shape: patient_profiles.mobile_number_normalized (0012) was
to be filled for existing rows by a manual script, so forgot-password by phone number said
"No account found" for those accounts.

WHAT THIS DOES — each step idempotent and conflict-safe:
  1. Stored patient emails are lowercased and trimmed, as signup and login already do —
     except where that would collide with another account (left for a person to resolve).
  2. Every patient, doctor and admin account missing from the registry is added.
     An email already registered is left exactly as it is.
  3. mobile_number_normalized is filled where it is empty and the number normalizes,
     using the same three shapes as users.normalize_mobile_number_india. A number another
     profile already holds is skipped, as the unique index requires.

revision: 0031_repair_account_lookups
"""
from alembic import op

revision = "0031_repair_account_lookups"
down_revision = "0030_repair_document_catalog_filename"
branch_labels = None
depends_on = None

# users.normalize_mobile_number_india, in SQL: 10 digits, 0 + 10 digits, or 91 + 10 digits.
NORMALIZED_MOBILE_SQL = """
    CASE
        WHEN length(d) = 10 THEN '+91' || d
        WHEN length(d) = 11 AND left(d, 1) = '0' THEN '+91' || substr(d, 2)
        WHEN length(d) = 12 AND left(d, 2) = '91' THEN '+' || d
    END
"""


def upgrade() -> None:
    op.execute(
        f"""
        -- 1. Emails as signup and login already write them.
        UPDATE users u
           SET email = lower(btrim(u.email))
         WHERE u.email <> lower(btrim(u.email))
           AND NOT EXISTS (SELECT 1 FROM users o
                            WHERE o.user_id <> u.user_id AND lower(btrim(o.email)) = lower(btrim(u.email)));

        -- 2. Every account the registry is missing. First writer wins on a shared email.
        INSERT INTO account_email_registry (email, account_type, account_id)
            SELECT lower(btrim(email)), 'patient', user_id FROM users
        ON CONFLICT (email) DO NOTHING;

        DO $$
        BEGIN
            IF to_regclass('doctor_accounts') IS NOT NULL THEN
                INSERT INTO account_email_registry (email, account_type, account_id)
                    SELECT lower(btrim(email)), 'doctor', id FROM doctor_accounts
                ON CONFLICT (email) DO NOTHING;
            END IF;
            IF to_regclass('admin_accounts') IS NOT NULL THEN
                INSERT INTO account_email_registry (email, account_type, account_id)
                    SELECT lower(btrim(email)), 'admin', admin_id FROM admin_accounts
                ON CONFLICT (email) DO NOTHING;
            END IF;
        END $$;

        -- 3. Normalized mobile numbers for profiles that never got one.
        WITH candidates AS (
            SELECT user_id, {NORMALIZED_MOBILE_SQL} AS normalized
              FROM (SELECT user_id, regexp_replace(COALESCE(mobile_number, ''), '\\D', '', 'g') AS d
                      FROM patient_profiles
                     WHERE mobile_number_normalized IS NULL) raw
        ),
        claimable AS (
            SELECT user_id, normalized,
                   row_number() OVER (PARTITION BY normalized ORDER BY user_id) AS n
              FROM candidates
             WHERE normalized IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM patient_profiles p
                                WHERE p.mobile_number_normalized = candidates.normalized)
        )
        UPDATE patient_profiles p
           SET mobile_number_normalized = c.normalized
          FROM claimable c
         WHERE p.user_id = c.user_id AND c.n = 1;
        """
    )


def downgrade() -> None:
    # A repair of missing data: nothing to undo that would not break login again.
    pass
