"""Restores consults that were discarded after their note was signed.

Discarding a consult used to be allowed at any point, even after its note was signed. It
deleted the transcript and marked the consult 'discarded', and every screen reads a visit's
latest consult that is NOT discarded — so the signed note, and the prescription approved
with it, vanished from the history, the visit brief and the appointment, though both were
the patient's record. Discarding is now refused once the note is signed
(consults.discard_consult); this puts back the ones discarded before.

A consult goes back to 'transcript_ready': the only status a note can be generated, and so
signed, in (soap_notes.generate). Its transcript was deleted by the discard and cannot come
back; the note, its sections and its approved items were never touched.

One per booking: a booking keeps at most one live consult (ux_consultations_active_booking),
so where several of its consults were signed and then discarded, only the most recently
signed is restored. Production had such a booking, and restoring all of them made the
first version of this migration fail on that index and stop the backend from starting.

Left alone, and listed in the migration output:
  - a consult whose booking has since had another consult started — restoring it would
    give that visit two live consults, and which one it shows is not a guess to make here;
  - the older signed consults of a booking where a later one is restored.

Each restore is audited (consult_restored_signed), next to the discard it reverses.

revision: 0035_restore_signed_consults
"""
from alembic import op

revision = "0035_restore_signed_consults"
down_revision = "0034_document_versions"
branch_labels = None
depends_on = None

_SIGNED_AND_DISCARDED = """
    c.status = 'discarded'
    AND EXISTS (SELECT 1 FROM soap_notes sn WHERE sn.consultation_id = c.id AND sn.status = 'signed')
"""
_ANOTHER_LIVE_CONSULT = """
    EXISTS (SELECT 1 FROM consultations o
            WHERE o.booking_id = c.booking_id AND o.id <> c.id AND o.status <> 'discarded')
"""


def upgrade() -> None:
    bind = op.get_bind()
    restored = bind.exec_driver_sql(
        f"""
        WITH chosen AS (
            -- At most one per booking: its most recently signed.
            SELECT DISTINCT ON (c.booking_id) c.id
            FROM consultations c
            JOIN soap_notes sn ON sn.consultation_id = c.id AND sn.status = 'signed'
            WHERE c.status = 'discarded' AND NOT {_ANOTHER_LIVE_CONSULT}
            ORDER BY c.booking_id, sn.signed_at DESC NULLS LAST, c.created_at DESC, c.id
        ),
        restored AS (
            UPDATE consultations c SET status = 'transcript_ready', updated_at = NOW()
            FROM chosen WHERE c.id = chosen.id
            RETURNING c.id, c.doctor_id
        )
        INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata)
        SELECT id, doctor_id, 'consult_restored_signed',
               '{{"reason": "discarded after its note was signed; the transcript could not be restored"}}'::jsonb
        FROM restored
        RETURNING consultation_id::text
        """
    ).fetchall()
    # Read after the restore: whatever is still signed and discarded was left alone.
    skipped = bind.exec_driver_sql(
        f"SELECT c.id::text, c.booking_id::text FROM consultations c WHERE {_SIGNED_AND_DISCARDED}"
    ).fetchall()
    for consult, booking in skipped:
        print(f"0035: NOT restored - consult {consult} (booking {booking}) has a signed note, but "
              f"the booking has another consult live or restored")
    print(f"0035: restored {len(restored)} consult(s) with a signed note; left {len(skipped)} as they were")


def downgrade() -> None:
    # Back to 'discarded' — exactly the consults this migration restored, by its audit rows.
    # The audit rows stay: the restore happened.
    op.execute(
        """
        UPDATE consultations SET status = 'discarded', updated_at = NOW()
        WHERE id IN (SELECT consultation_id FROM consult_audit_log
                     WHERE action_type = 'consult_restored_signed')
          AND status = 'transcript_ready'
        """
    )
