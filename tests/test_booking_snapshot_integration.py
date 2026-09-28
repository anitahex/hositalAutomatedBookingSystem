"""The pre-visit snapshot against a real database.

These cover what only real SQL can prove, and every one of them protects something that
cannot be recovered if it breaks:

  - the snapshot commits in the BOOKING'S transaction, so an appointment can never exist
    without the record of what produced it
  - it is immutable: a second write is refused, and later conversation cannot alter it
  - the transcript is pinned to a range, not to a session, so messages sent afterwards do
    not retroactively change what the doctor sees
  - documents are frozen at booking time
  - a snapshot failure never costs the patient their appointment

Conventions follow test_doctor_workspace_integration.py — same fixture shape, same
cleanup, skips rather than fails without a database.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.appointments import book_selected_slot
from app.services.booking_context import (
    SnapshotContext, get_snapshot, get_snapshot_for_doctor,
)


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _make_doctor(cur, name, department="Testing"):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, %s, 1, TRUE) RETURNING doctor_id""",
        (name, department),
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


def _make_free_slot(cur, doctor_id, hours_ahead=48):
    """Must satisfy book_selected_slot's own window: >30 min away and <=7 days out."""
    start = datetime.now() + timedelta(hours=hours_ahead)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
           VALUES (%s, %s, %s, FALSE, NULL) RETURNING slot_id""",
        (doctor_id, start, start + timedelta(minutes=30)),
    )
    return str(cur.fetchone()[0])


def _say(cur, patient_id, session_id, role, text):
    cur.execute(
        """INSERT INTO chat_messages (patient_id, chat_session_id, role, text)
           VALUES (%s, %s, %s, %s) RETURNING message_id""",
        (patient_id, session_id, role, text),
    )
    return str(cur.fetchone()[0])


def _add_document(cur, patient_id, session_id, filename):
    document_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO document_catalog
               (document_id, user_id, session_id, blob_summary_path, original_filename,
                ingestion_status)
           VALUES (%s, %s, %s, %s, %s, 'complete')""",
        (document_id, patient_id, session_id, f"summaries/{document_id}.json", filename),
    )
    return document_id


def _cleanup(doctor_id, patient_id):
    with connect_db() as conn:
        with conn.cursor() as cur:
            if patient_id:
                cur.execute("DELETE FROM document_catalog WHERE user_id = %s", (patient_id,))
                cur.execute("DELETE FROM chat_messages WHERE patient_id = %s", (patient_id,))
            if doctor_id:
                cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
            if patient_id:
                cur.execute("DELETE FROM users WHERE user_id = %s", (patient_id,))
        conn.commit()


@pytest.fixture
def booking_world():
    """A doctor, a patient, a bookable slot and a conversation that led to it."""
    _skip_if_no_database()
    doctor_id = patient_id = None
    try:
        session_id = str(uuid.uuid4())
        with connect_db() as conn:
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. Snapshot", "Psychiatry")
                patient_id = _make_patient(cur, f"snapshot-{uuid.uuid4().hex[:8]}@example.com")
                slot_id = _make_free_slot(cur, doctor_id)
                first = _say(cur, patient_id, session_id, "patient", "I cannot sleep and I feel anxious")
                _say(cur, patient_id, session_id, "assistant", "How long has that been going on?")
                last = _say(cur, patient_id, session_id, "patient", "About two weeks")
                document_id = _add_document(cur, patient_id, session_id, "blood-report.pdf")
            conn.commit()
        yield {
            "doctor_id": doctor_id, "patient_id": patient_id, "slot_id": slot_id,
            "session_id": session_id, "first": first, "last": last,
            "document_id": document_id,
        }
    finally:
        _cleanup(doctor_id, patient_id)


# ---- it is written at all, and with the booking ----

def test_booking_through_the_assistant_records_its_context(booking_world):
    context = SnapshotContext(
        chat_session_id=booking_world["session_id"],
        suggested_department="Endocrinology",
        chosen_department="Psychiatry",
        department_match_source="document_findings",
        department_match_reason="raised morning cortisol",
    )

    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=context,
    )
    assert booked is not None

    snapshot = get_snapshot(booked["booking_id"])
    assert snapshot is not None, "the appointment exists with no record of what produced it"
    assert snapshot["suggested_department"] == "Endocrinology"
    assert snapshot["chosen_department"] == "Psychiatry"
    assert snapshot["department_match_reason"] == "raised morning cortisol"


def test_the_disagreement_survives_to_the_doctor(booking_world):
    """The whole point of §1: the doctor sees that the assistant said one thing and the
    patient chose another."""
    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(
            chat_session_id=booking_world["session_id"],
            suggested_department="Endocrinology",
            chosen_department="Psychiatry",
        ),
    )
    snapshot = get_snapshot(booked["booking_id"])

    assert snapshot["suggested_department"] != snapshot["chosen_department"]


# ---- the transcript pin ----

def test_the_transcript_is_pinned_to_the_messages_that_existed_at_booking(booking_world):
    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
    )
    snapshot = get_snapshot(booked["booking_id"])

    assert snapshot["transcript_message_count"] == 3
    assert snapshot["transcript_from_at"] is not None
    assert snapshot["transcript_to_at"] is not None
    assert snapshot["transcript_from_at"] <= snapshot["transcript_to_at"]


def test_the_pin_is_a_time_window_because_a_turn_shares_one_timestamp(booking_world):
    """chat_messages.created_at defaults to now(), which is constant within a
    transaction, and a turn writes the patient message and the assistant reply together.
    Live data: one 26-message session had 13 distinct timestamps.

    So "the last message" is not a well-defined row, and an id-based pin would silently
    pick one half of the final turn. This asserts the fixture really does produce tied
    timestamps — otherwise the window semantics below would be untested — and that the
    window still spans every message.
    """
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*), COUNT(DISTINCT created_at) FROM chat_messages
                   WHERE patient_id = %s AND chat_session_id = %s""",
                (booking_world["patient_id"], booking_world["session_id"]),
            )
            total, distinct = cur.fetchone()
        conn.commit()

    assert total == 3
    assert distinct < total, "fixture no longer reproduces tied timestamps"

    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
    )
    snapshot = get_snapshot(booked["booking_id"])

    # Every message falls inside the pinned window, ties included.
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) FROM chat_messages
                   WHERE patient_id = %s AND chat_session_id = %s
                     AND created_at BETWEEN %s AND %s""",
                (
                    booking_world["patient_id"], booking_world["session_id"],
                    snapshot["transcript_from_at"], snapshot["transcript_to_at"],
                ),
            )
            in_window = cur.fetchone()[0]
        conn.commit()

    assert in_window == snapshot["transcript_message_count"] == 3


def test_later_conversation_does_not_change_what_the_appointment_shows(booking_world):
    """The immutability requirement, asserted against the thing that would break it. If
    the snapshot pinned "the session" rather than a message range, everything the patient
    said afterwards would silently become part of this appointment's record."""
    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
    )
    before = get_snapshot(booked["booking_id"])

    with connect_db() as conn:
        with conn.cursor() as cur:
            _say(cur, booking_world["patient_id"], booking_world["session_id"],
                 "patient", "actually I also have chest pain")
        conn.commit()

    assert get_snapshot(booked["booking_id"]) == before


# ---- the document pin ----

def test_documents_uploaded_during_the_conversation_are_attached(booking_world):
    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
    )
    snapshot = get_snapshot(booked["booking_id"])

    assert snapshot["document_ids"] == [booking_world["document_id"]]


def test_a_document_uploaded_afterwards_is_not_retrofitted_onto_the_appointment(booking_world):
    """It was not part of what the patient brought to this visit, and showing it as though
    it were would misrepresent the record."""
    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
    )

    with connect_db() as conn:
        with conn.cursor() as cur:
            _add_document(cur, booking_world["patient_id"], booking_world["session_id"], "later.pdf")
        conn.commit()

    assert get_snapshot(booked["booking_id"])["document_ids"] == [booking_world["document_id"]]


def test_another_patients_documents_are_never_pulled_in(booking_world):
    """The lookup is scoped by patient as well as session, so a guessed or collided
    session id cannot attach someone else's records to this appointment."""
    other = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                other = _make_patient(cur, f"other-{uuid.uuid4().hex[:8]}@example.com")
                _add_document(cur, other, booking_world["session_id"], "not-theirs.pdf")
            conn.commit()

        booked = book_selected_slot(
            slot_id=booking_world["slot_id"],
            patient_id=booking_world["patient_id"],
            booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
        )
        assert get_snapshot(booked["booking_id"])["document_ids"] == [booking_world["document_id"]]
    finally:
        if other:
            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM document_catalog WHERE user_id = %s", (other,))
                    cur.execute("DELETE FROM users WHERE user_id = %s", (other,))
                conn.commit()


# ---- bookings with no conversation ----

def test_a_booking_with_no_conversation_is_recorded_as_skipped_not_pending(booking_world):
    """The REST booking route has no transcript. 'skipped' says so; 'pending' would leave
    a background summariser retrying forever over a conversation that never existed."""
    booked = book_selected_slot(
        slot_id=booking_world["slot_id"], patient_id=booking_world["patient_id"]
    )
    snapshot = get_snapshot(booked["booking_id"])

    assert snapshot is not None, "even a direct booking must have a context row"
    assert snapshot["ai_summary_status"] == "skipped"
    assert snapshot["transcript_message_count"] == 0
    assert snapshot["document_ids"] == []


def test_a_conversation_booking_is_marked_pending_for_summarising(booking_world):
    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
    )
    assert get_snapshot(booked["booking_id"])["ai_summary_status"] == "pending"


# ---- immutability and resilience ----

def test_a_second_snapshot_for_one_booking_is_refused_by_the_database(booking_world):
    """Not by this code remembering to check. A doctor may already have read the first."""
    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
    )

    with connect_db() as conn:
        with conn.cursor() as cur:
            with pytest.raises(Exception):
                cur.execute(
                    """INSERT INTO booking_context_snapshots (booking_id, patient_id)
                       VALUES (%s, %s)""",
                    (booked["booking_id"], booking_world["patient_id"]),
                )
        conn.rollback()


def test_a_snapshot_failure_does_not_cost_the_patient_their_appointment(booking_world, monkeypatch):
    """The SAVEPOINT's whole purpose. In Postgres a failed statement aborts the entire
    transaction, so without it a broken snapshot would roll back the booking — turning a
    degraded record into a patient who does not get seen."""
    from app.services import booking_context as module

    def explode(*args, **kwargs):
        raise RuntimeError("snapshot capture is broken")

    monkeypatch.setattr(module, "capture_snapshot_safely", explode)

    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
    )

    assert booked is not None, "the booking was lost because its context could not be recorded"
    assert booked["booking_id"]
    assert get_snapshot(booked["booking_id"]) is None


def test_a_failing_SQL_statement_in_the_snapshot_does_not_abort_the_booking(booking_world, monkeypatch):
    """The realistic failure, and the one the SAVEPOINT actually exists for.

    A Python exception is the easy case. A failed *SQL statement* puts Postgres into
    "current transaction is aborted, commands ignored until end of transaction block" —
    every later statement in the booking, including the COMMIT, fails too. Only a
    SAVEPOINT can recover the transaction, which is why capture is wrapped in one rather
    than in a plain try/except.
    """
    from app.services import booking_context as module

    def broken_sql(cur, **kwargs):
        cur.execute("INSERT INTO booking_context_snapshots (booking_id) VALUES ('not-a-uuid')")

    monkeypatch.setattr(module, "capture_snapshot_safely", broken_sql)

    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
    )

    assert booked is not None, "a poisoned transaction took the booking down with it"

    # And the booking is genuinely committed, not just returned.
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM appointment_bookings WHERE booking_id = %s",
                (booked["booking_id"],),
            )
            assert cur.fetchone()[0] == "booked"
        conn.commit()


# ---- the read side ----

def test_the_owning_doctor_can_read_the_context(booking_world):
    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(
            chat_session_id=booking_world["session_id"],
            suggested_department="Endocrinology",
            chosen_department="Psychiatry",
        ),
    )

    snapshot = get_snapshot_for_doctor(booking_world["doctor_id"], booked["booking_id"])

    assert snapshot["suggested_department"] == "Endocrinology"
    assert snapshot["chosen_department"] == "Psychiatry"


def test_another_doctor_cannot_read_it_and_cannot_tell_it_exists(booking_world):
    """PermissionError for both "not yours" and "no such booking", deliberately
    indistinguishable, so this cannot be used to probe which appointments exist.

    Note the rule here is the booking's OWN doctor, not doctor_treats_patient — that is
    true of any doctor who has ever booked this patient, and a colleague's appointment
    context is not part of what treating this patient entitles you to.
    """
    other_doctor = None
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                other_doctor = _make_doctor(cur, "Dr. Not Involved")
            conn.commit()

        booked = book_selected_slot(
            slot_id=booking_world["slot_id"],
            patient_id=booking_world["patient_id"],
            booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
        )

        with pytest.raises(PermissionError):
            get_snapshot_for_doctor(other_doctor, booked["booking_id"])

        with pytest.raises(PermissionError):
            get_snapshot_for_doctor(other_doctor, str(uuid.uuid4()))
    finally:
        if other_doctor:
            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (other_doctor,))
                conn.commit()


@pytest.mark.parametrize("bad", ["not-a-uuid", "' OR 1=1--", "", "   "])
def test_a_malformed_booking_id_is_not_found_rather_than_a_server_error(booking_world, bad):
    """booking_id comes from the URL path. Handing a non-UUID straight to Postgres raises
    InvalidTextRepresentation, which surfaces as a 500 and tells the caller their input
    reached the database."""
    with pytest.raises(PermissionError):
        get_snapshot_for_doctor(booking_world["doctor_id"], bad)


def test_reading_the_context_is_audited(booking_world):
    """A booking transcript is clinical content, so reading it is recorded — the same rule
    document_catalog applies to document content."""
    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
    )
    get_snapshot_for_doctor(booking_world["doctor_id"], booked["booking_id"])

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) FROM consult_audit_log
                   WHERE doctor_id = %s AND action_type = 'booking_context_viewed'
                     AND metadata->>'booking_id' = %s""",
                (booking_world["doctor_id"], str(booked["booking_id"])),
            )
            assert cur.fetchone()[0] == 1
        conn.commit()


def test_an_appointment_booked_before_capture_existed_reports_that_honestly(booking_world):
    """Returns None, which the route renders as recorded:false. An empty context object
    would read as "the patient said nothing", which is a different and false claim."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            start = datetime.now() + timedelta(hours=72)
            cur.execute(
                """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
                   VALUES (%s, %s, %s, TRUE, %s) RETURNING slot_id""",
                (booking_world["doctor_id"], start, start + timedelta(minutes=30),
                 booking_world["patient_id"]),
            )
            slot = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time)
                   VALUES (%s, %s, %s, %s, %s) RETURNING booking_id""",
                (slot, booking_world["doctor_id"], booking_world["patient_id"],
                 start, start + timedelta(minutes=30)),
            )
            legacy_booking = str(cur.fetchone()[0])
        conn.commit()

    assert get_snapshot_for_doctor(booking_world["doctor_id"], legacy_booking) is None


def test_the_booking_and_its_context_commit_together(booking_world):
    """Asserted from the database, not from the return value: if these could commit
    separately there would be a window where an appointment exists with no context."""
    booked = book_selected_slot(
        slot_id=booking_world["slot_id"],
        patient_id=booking_world["patient_id"],
        booking_context=SnapshotContext(chat_session_id=booking_world["session_id"]),
    )

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) FROM appointment_bookings b
                   JOIN booking_context_snapshots s ON s.booking_id = b.booking_id
                   WHERE b.booking_id = %s""",
                (booked["booking_id"],),
            )
            assert cur.fetchone()[0] == 1
        conn.commit()
