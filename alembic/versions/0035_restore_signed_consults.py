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

Left alone, and listed in the migration output: a consult whose booking has since had
another consult started. Restoring it would give that visit two live consults, and which
one the visit shows is not a guess to make here.

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
    skipped = bind.exec_driver_sql(
        f"SELECT c.id::text, c.booking_id::text FROM consultations c "
        f"WHERE {_SIGNED_AND_DISCARDED} AND {_ANOTHER_LIVE_CONSULT}"
    ).fetchall()
    for consult, booking in skipped:
        print(f"0035: NOT restored — consult {consult} (booking {booking}) has a signed note, "
              f"but the booking has another consult since")
    restored = bind.exec_driver_sql(
        f"""
        WITH restored AS (
            UPDATE consultations c SET status = 'transcript_ready', updated_at = NOW()
            WHERE {_SIGNED_AND_DISCARDED} AND NOT {_ANOTHER_LIVE_CONSULT}
            RETURNING c.id, c.doctor_id
        )
        INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata)
        SELECT id, doctor_id, 'consult_restored_signed',
               '{{"reason": "discarded after its note was signed; the transcript could not be restored"}}'::jsonb
        FROM restored
        RETURNING consultation_id::text
        """
    ).fetchall()
    print(f"0035: restored {len(restored)} consult(s) with a signed note; skipped {len(skipped)}")


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
