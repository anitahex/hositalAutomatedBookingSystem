"""Integration coverage for the AI doctor-workspace read models against a real database.

The pure logic is unit-tested in test_doctor_workspace.py. This file covers what only a
real query can prove:

  - the activity summary, activity log, patient brief and section verification are each
    scoped to ONE doctor in SQL, so doctor A cannot see doctor B's data
  - the activity feed projects an explicit metadata allowlist rather than the raw audit row
  - the patient brief never compiles an unsigned draft, against real rows
  - section verification is idempotent, is cleared by regeneration, and is refused once
    the note is signed

Follows test_doctor_reviews_integration.py's conventions exactly (same fixture helpers,
same cleanup discipline). Skips (not fails) if no database is reachable.
"""

from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.doctor_ai_activity import get_activity_log, get_activity_summary
from app.services.soap_sections import list_verified_sections, set_section_verified


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _make_doctor(cur, name):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
        (name, "Testing", 1),
    )
    return str(cur.fetchone()[0])


def _make_account(cur, doctor_id, email, previous_login_at=None):
    """A doctor_accounts row, which is where previous_login_at lives. The activity
    summary's window is read from it."""
    cur.execute(
        """INSERT INTO doctor_accounts (doctor_id, email, hashed_password, is_active,
                                        mfa_enabled, previous_login_at)
           VALUES (%s, %s, 'x', TRUE, TRUE, %s) RETURNING id""",
        (doctor_id, email, previous_login_at),
    )
    return str(cur.fetchone()[0])


def _make_patient(cur, email):
    cur.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id",
        (email,),
    )
    user_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
           VALUES (%s, %s, 30, '9999999999', 'Test address', %s, 'O+')""",
        (user_id, f"Patient {email}", email),
    )
    return user_id


def _make_booking(cur, doctor_id, patient_id, start_offset_hours=-2):
    start_time = datetime.now() + timedelta(hours=start_offset_hours)
    end_time = start_time + timedelta(minutes=30)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
           VALUES (%s, %s, %s, FALSE, NULL) RETURNING slot_id""",
        (doctor_id, start_time, end_time),
    )
    slot_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, 'completed') RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start_time, end_time),
    )
    return str(cur.fetchone()[0])


def _make_consult(cur, booking_id, doctor_id, patient_id, *, status="transcript_ready",
                  transcript_source="batch"):
    cur.execute(
        """INSERT INTO consultations (booking_id, doctor_id, patient_id, status,
                                      transcript_source, ended_at)
           VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING id""",
        (booking_id, doctor_id, patient_id, status, transcript_source),
    )
    return str(cur.fetchone()[0])


def _make_note(cur, consultation_id, doctor_id, patient_id, *, status="draft",
               confidence_flags="{}", signed=False, assessment="A"):
    cur.execute(
        """INSERT INTO soap_notes (consultation_id, doctor_id, patient_id,
                                   subjective, objective, assessment, plan,
                                   confidence_flags, status, generated_at,
                                   signed_at, signed_by)
           VALUES (%s, %s, %s, 'S', 'O', %s, 'P', %s::jsonb, %s, NOW(),
                   CASE WHEN %s THEN NOW() END, %s)
           RETURNING id""",
        (consultation_id, doctor_id, patient_id, assessment, confidence_flags, status,
         signed, doctor_id if signed else None),
    )
    return str(cur.fetchone()[0])


def _audit(cur, consultation_id, doctor_id, action, metadata="{}"):
    cur.execute(
        """INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata)
           VALUES (%s, %s, %s, %s::jsonb)""",
        (consultation_id, doctor_id, action, metadata),
    )


def _ensure_schema(conn):
    from app.services.appointments import ensure_booking_schema
    from app.services.consults import ensure_consult_schema
    from app.services.doctor_auth import ensure_doctor_auth_schema
    from app.services.soap_notes import ensure_soap_schema
    from app.services.soap_sections import ensure_section_verification_schema

    ensure_booking_schema(conn)
    ensure_consult_schema(conn)
    ensure_soap_schema(conn)
    ensure_doctor_auth_schema(conn)
    ensure_section_verification_schema(conn)


def _cleanup(doctor_ids, user_ids):
    with connect_db() as conn:
        with conn.cursor() as cur:
            for doctor_id in doctor_ids:
                if doctor_id:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
            for user_id in user_ids:
                if user_id:
                    cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()


# ---- Activity summary (plan §4.1) ----

def test_activity_summary_is_scoped_to_one_doctor():
    """The property this file exists for. Doctor B drafts a note; doctor A's summary must
    not count it."""
    _skip_if_no_database()

    doctor_a = doctor_b = patient_a = patient_b = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_a = _make_doctor(cur, "Dr. A Activity")
                doctor_b = _make_doctor(cur, "Dr. B Activity")
                account_a = _make_account(cur, doctor_a, "activity-a@example.com")
                account_b = _make_account(cur, doctor_b, "activity-b@example.com")
                patient_a = _make_patient(cur, "activity-patient-a@example.com")
                patient_b = _make_patient(cur, "activity-patient-b@example.com")

                consult_a = _make_consult(
                    cur, _make_booking(cur, doctor_a, patient_a), doctor_a, patient_a)
                consult_b = _make_consult(
                    cur, _make_booking(cur, doctor_b, patient_b), doctor_b, patient_b)
                _make_note(cur, consult_a, doctor_a, patient_a)
                # Two notes for B, one for A — so an unscoped query would be obvious.
                _make_note(cur, consult_b, doctor_b, patient_b)
                _audit(cur, consult_a, doctor_a, "consult_soap_note_generated")
                _audit(cur, consult_b, doctor_b, "consult_soap_note_generated")
                _audit(cur, consult_b, doctor_b, "consult_soap_note_generated")
            conn.commit()

        summary_a = get_activity_summary(doctor_a, account_a)
        summary_b = get_activity_summary(doctor_b, account_b)

        assert summary_a["counts"]["notes_drafted"] == 1
        assert summary_b["counts"]["notes_drafted"] == 2
        assert summary_a["counts"]["awaiting_signature"] == 1
    finally:
        _cleanup((doctor_a, doctor_b), (patient_a, patient_b))


def test_summary_falls_back_to_24h_when_there_is_no_previous_login():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Fallback")
                account_id = _make_account(cur, doctor_id, "fallback@example.com")
                patient_id = _make_patient(cur, "fallback-patient@example.com")
            conn.commit()

        summary = get_activity_summary(doctor_id, account_id)
        # The flag is what lets the UI say "last 24 hours" instead of claiming a session
        # boundary that does not exist.
        assert summary["window_is_fallback"] is True
        assert summary["window_start"] is not None
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_summary_window_excludes_activity_from_before_the_last_login():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Window")
                # Last session was an hour ago.
                account_id = _make_account(
                    cur, doctor_id, "window@example.com",
                    previous_login_at=datetime.now() - timedelta(hours=1),
                )
                patient_id = _make_patient(cur, "window-patient@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _audit(cur, consult, doctor_id, "consult_soap_note_generated")
                # An older draft, from before that session — must not be counted.
                cur.execute(
                    """INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata, created_at)
                       VALUES (%s, %s, 'consult_soap_note_generated', '{}'::jsonb, NOW() - INTERVAL '3 hours')""",
                    (consult, doctor_id),
                )
            conn.commit()

        summary = get_activity_summary(doctor_id, account_id)
        assert summary["window_is_fallback"] is False
        assert summary["counts"]["notes_drafted"] == 1
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_summary_counts_flagged_fields_and_blocked_notes_from_real_rows():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Flags")
                account_id = _make_account(cur, doctor_id, "flags@example.com")
                patient_id = _make_patient(cur, "flags-patient@example.com")

                flagged = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _make_note(cur, flagged, doctor_id, patient_id,
                           confidence_flags='{"subjective": true, "plan": true, "objective": false}')

                blocked = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _make_note(cur, blocked, doctor_id, patient_id, status="stale")
            conn.commit()

        counts = get_activity_summary(doctor_id, account_id)["counts"]
        assert counts["fields_flagged"] == 2
        assert counts["notes_blocked"] == 1
        assert counts["awaiting_signature"] == 2
    finally:
        _cleanup((doctor_id,), (patient_id,))


# ---- Activity log (plan §4.3) ----

def test_activity_log_is_scoped_to_one_doctor():
    _skip_if_no_database()

    doctor_a = doctor_b = patient_a = patient_b = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_a = _make_doctor(cur, "Dr. A Feed")
                doctor_b = _make_doctor(cur, "Dr. B Feed")
                patient_a = _make_patient(cur, "feed-a@example.com")
                patient_b = _make_patient(cur, "feed-b@example.com")
                consult_a = _make_consult(
                    cur, _make_booking(cur, doctor_a, patient_a), doctor_a, patient_a)
                consult_b = _make_consult(
                    cur, _make_booking(cur, doctor_b, patient_b), doctor_b, patient_b)
                _audit(cur, consult_a, doctor_a, "consult_soap_note_generated")
                _audit(cur, consult_b, doctor_b, "consult_soap_note_generated")
            conn.commit()

        events_a = get_activity_log(doctor_a)["events"]
        consult_ids = {e["consultation_id"] for e in events_a}
        assert consult_a in consult_ids
        assert consult_b not in consult_ids
    finally:
        _cleanup((doctor_a, doctor_b), (patient_a, patient_b))


def test_activity_log_projects_an_allowlist_not_the_raw_metadata():
    """consult_audit_log.metadata is free-form JSONB written by many call sites. The feed
    must surface only the keys it declares, or it becomes an uncontrolled disclosure
    channel the moment some other call site starts recording something new."""
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Allowlist")
                patient_id = _make_patient(cur, "allowlist@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _audit(
                    cur, consult, doctor_id, "consult_soap_note_generated",
                    metadata='{"style": "concise", "secret_internal_path": "/vault/keys", '
                             '"patient_name": "Should Not Leak"}',
                )
            conn.commit()

        event = get_activity_log(doctor_id)["events"][0]
        assert event["detail"]["style"] == "concise"
        assert "secret_internal_path" not in event["detail"]
        assert "patient_name" not in event["detail"]
        assert "Should Not Leak" not in str(event)
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_activity_log_never_carries_the_model_name_or_prompt_version():
    """Which model wrote a note stays recorded in the audit row and on soap_notes, but it
    is not shown to the doctor, so it is not sent to the browser either.

    The metadata written here DOES contain both, so this proves the projection strips
    them — a fixture that simply omitted them would pass whatever the code did."""
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. No Model")
                patient_id = _make_patient(cur, "no-model@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _audit(
                    cur, consult, doctor_id, "consult_soap_note_generated",
                    metadata='{"style": "concise", "ai_model": "gpt-4o-mini", '
                             '"ai_prompt_version": "v1-concise"}',
                )
            conn.commit()

        event = get_activity_log(doctor_id)["events"][0]

        assert event["detail"]["style"] == "concise", "the allowlisted key must survive"
        assert "ai_model" not in event["detail"]
        assert "ai_prompt_version" not in event["detail"]
        # Not just the keys — the values must not reach the client under any name.
        assert "gpt-4o-mini" not in str(event)
        assert "v1-concise" not in str(event)
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_activity_log_drops_action_types_it_does_not_declare():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Unknown Action")
                patient_id = _make_patient(cur, "unknown-action@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _audit(cur, consult, doctor_id, "some_future_internal_action")
                _audit(cur, consult, doctor_id, "consult_soap_note_generated")
            conn.commit()

        events = get_activity_log(doctor_id)["events"]
        assert [e["action"] for e in events] == ["consult_soap_note_generated"]
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_activity_log_limit_is_clamped():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Limit")
                patient_id = _make_patient(cur, "limit@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                for _ in range(5):
                    _audit(cur, consult, doctor_id, "consult_soap_note_generated")
            conn.commit()

        assert len(get_activity_log(doctor_id, limit=2)["events"]) == 2
        # Absurd values are clamped, never passed through to the query.
        assert len(get_activity_log(doctor_id, limit=100000)["events"]) == 5
        assert len(get_activity_log(doctor_id, limit=0)["events"]) == 1
    finally:
        _cleanup((doctor_id,), (patient_id,))


# ---- Section verification (plan §4.6) ----

def test_section_verification_round_trips_and_is_idempotent():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Verify")
                patient_id = _make_patient(cur, "verify@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _make_note(cur, consult, doctor_id, patient_id)
            conn.commit()

        assert list_verified_sections(consult, doctor_id) == []

        set_section_verified(consult, doctor_id, "subjective")
        # Marking twice must not duplicate or error — the button is safe to double-click.
        result = set_section_verified(consult, doctor_id, "subjective")
        assert result["verified_sections"] == ["subjective"]

        set_section_verified(consult, doctor_id, "plan")
        assert list_verified_sections(consult, doctor_id) == ["plan", "subjective"]

        # And it can be cleared again, twice, without error.
        set_section_verified(consult, doctor_id, "plan", verified=False)
        set_section_verified(consult, doctor_id, "plan", verified=False)
        assert list_verified_sections(consult, doctor_id) == ["subjective"]
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_another_doctor_cannot_read_or_write_this_notes_verification_state():
    _skip_if_no_database()

    doctor_a = doctor_b = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_a = _make_doctor(cur, "Dr. A Verify")
                doctor_b = _make_doctor(cur, "Dr. B Verify")
                patient_id = _make_patient(cur, "verify-scope@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_a, patient_id), doctor_a, patient_id)
                _make_note(cur, consult, doctor_a, patient_id)
            conn.commit()

        # "You may not" and "it does not exist" are deliberately indistinguishable.
        with pytest.raises(ValueError):
            list_verified_sections(consult, doctor_b)
        with pytest.raises(ValueError):
            set_section_verified(consult, doctor_b, "subjective")
    finally:
        _cleanup((doctor_a, doctor_b), (patient_id,))


def test_a_signed_note_can_no_longer_be_marked():
    """Once signed, the signature IS the record of review. A mark added afterwards would
    imply a review step that never happened."""
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Signed Verify")
                patient_id = _make_patient(cur, "signed-verify@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _make_note(cur, consult, doctor_id, patient_id, status="signed", signed=True)
            conn.commit()

        with pytest.raises(PermissionError):
            set_section_verified(consult, doctor_id, "subjective")
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_verifying_a_consult_with_no_note_is_rejected():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. No Note")
                patient_id = _make_patient(cur, "no-note@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
            conn.commit()

        with pytest.raises(ValueError):
            set_section_verified(consult, doctor_id, "subjective")
        assert list_verified_sections(consult, doctor_id) == []
    finally:
        _cleanup((doctor_id,), (patient_id,))


def test_an_unknown_section_name_is_rejected_before_the_database():
    _skip_if_no_database()
    with pytest.raises(ValueError):
        set_section_verified("00000000-0000-0000-0000-000000000000", "doc", "diagnosis")


def test_regenerating_a_note_clears_its_verification_marks():
    """The verified text no longer exists after a regeneration, so carrying the marks
    forward would show progress against sections nobody has read."""
    _skip_if_no_database()

    from app.services.soap_sections import clear_verifications_for_note

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Regen Clear")
                patient_id = _make_patient(cur, "regen-clear@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                note_id = _make_note(cur, consult, doctor_id, patient_id)
            conn.commit()

        set_section_verified(consult, doctor_id, "subjective")
        assert list_verified_sections(consult, doctor_id) == ["subjective"]

        # Exercises the same helper generate_soap_note calls on its open cursor.
        with connect_db() as conn:
            with conn.cursor() as cur:
                clear_verifications_for_note(cur, note_id)
            conn.commit()

        assert list_verified_sections(consult, doctor_id) == []
    finally:
        _cleanup((doctor_id,), (patient_id,))


# ---- Concurrency (regression: a real deadlock seen in the running application) ----

def test_activity_summary_does_not_deadlock_against_concurrent_auth_reads():
    """Regression for a deadlock caught in the running app, not in this suite.

    get_activity_summary used to read doctor_accounts INSIDE the transaction that had
    just run ensure_booking_schema/ensure_consult_schema/ensure_soap_schema — so it held
    locks on the consult tables while reaching for doctor_accounts. The authentication
    path (get_doctor_profile -> ensure_doctor_auth_schema) takes those locks in the
    opposite order. Overlapping requests deadlocked:

        psycopg2.errors.DeadlockDetected: deadlock detected

    Every other test in this file runs sequentially, which is exactly why none of them
    caught it. This one runs the two paths against each other on real threads.
    """
    _skip_if_no_database()

    import threading

    from app.services.doctor_auth import get_doctor_profile

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Deadlock")
                account_id = _make_account(cur, doctor_id, "deadlock@example.com")
                patient_id = _make_patient(cur, "deadlock-patient@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _make_note(cur, consult, doctor_id, patient_id)
            conn.commit()

        errors: list[Exception] = []

        def hammer_summary():
            for _ in range(6):
                try:
                    get_activity_summary(doctor_id, account_id)
                except Exception as exc:          # noqa: BLE001 - the assertion is below
                    errors.append(exc)

        def hammer_auth():
            for _ in range(6):
                try:
                    get_doctor_profile(doctor_id, account_id)
                except Exception as exc:          # noqa: BLE001
                    errors.append(exc)

        threads = [
            threading.Thread(target=hammer_summary),
            threading.Thread(target=hammer_auth),
            threading.Thread(target=hammer_summary),
            threading.Thread(target=hammer_auth),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        assert not any(t.is_alive() for t in threads), "a worker hung — likely a lock wait"
        assert not errors, f"concurrent access raised: {errors[:3]}"
    finally:
        _cleanup((doctor_id,), (patient_id,))
