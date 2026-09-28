"""The rows behind each activity tile, against a real database.

The tiles say a number; clicking one shows a list. If the two ever disagree the doctor has
been told something false by one of them and nothing on screen says which. So the first
test here is the one the rest exist to support: in every window, for every tile, the list
reconciles with the count.

The rest pin the behaviours a doctor would otherwise find out about the hard way:

  - a regenerated note is two draft events, and shows as two rows because the tile says 2
  - a discarded consult's leftover note still counts as drafted (it was), but is marked as
    not openable, because every screen that shows a consult filters discarded ones out
  - that same leftover note is NOT held back — the consult is gone
  - a stray key in confidence_flags cannot add a flagged section
  - another doctor's rows never appear, in any tile
  - an unknown tile or window is refused, never defaulted

Follows test_doctor_workspace_integration.py's fixture conventions. Skips (not fails) if
no database is reachable.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from app.db.connection import connect_db
from app.services.doctor_ai_activity import (
    ACTIVITY_TILES,
    ACTIVITY_WINDOWS,
    get_activity_items,
    get_activity_summary,
)


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def _doctor(cur, name):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, 'Testing', 1, TRUE) RETURNING doctor_id""",
        (name,),
    )
    return str(cur.fetchone()[0])


def _account(cur, doctor_id, previous_login_at):
    cur.execute(
        """INSERT INTO doctor_accounts (doctor_id, email, hashed_password, is_active,
                                        mfa_enabled, previous_login_at)
           VALUES (%s, %s, 'x', TRUE, TRUE, %s) RETURNING id""",
        (doctor_id, f"items-{uuid.uuid4().hex[:10]}@example.com", previous_login_at),
    )
    return str(cur.fetchone()[0])


def _patient(cur, name):
    email = f"items-{uuid.uuid4().hex[:10]}@example.com"
    cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING user_id", (email,))
    user_id = str(cur.fetchone()[0])
    cur.execute(
        """INSERT INTO patient_profiles (user_id, name, age, mobile_number, address, email, blood_group)
           VALUES (%s, %s, 30, '9999999999', 'Test', %s, 'O+')""",
        (user_id, name, email),
    )
    return user_id


def _booking(cur, doctor_id, patient_id):
    start = datetime.now() - timedelta(hours=2)
    cur.execute(
        """INSERT INTO appointment_slots (doctor_id, start_time, end_time, is_booked, booked_by_patient_id)
           VALUES (%s, %s, %s, FALSE, NULL) RETURNING slot_id""",
        (doctor_id, start, start + timedelta(minutes=30)),
    )
    slot_id = cur.fetchone()[0]
    cur.execute(
        """INSERT INTO appointment_bookings (slot_id, doctor_id, patient_id, start_time, end_time, status)
           VALUES (%s, %s, %s, %s, %s, 'completed') RETURNING booking_id""",
        (slot_id, doctor_id, patient_id, start, start + timedelta(minutes=30)),
    )
    return str(cur.fetchone()[0])


def _consult(cur, booking_id, doctor_id, patient_id, status="transcript_ready"):
    cur.execute(
        """INSERT INTO consultations (booking_id, doctor_id, patient_id, status, transcript_source, ended_at)
           VALUES (%s, %s, %s, %s, 'batch', NOW()) RETURNING id""",
        (booking_id, doctor_id, patient_id, status),
    )
    return str(cur.fetchone()[0])


def _note(cur, consultation_id, doctor_id, patient_id, *, status="draft", flags="{}", hours_ago=0):
    cur.execute(
        """INSERT INTO soap_notes (consultation_id, doctor_id, patient_id,
                                   subjective, objective, assessment, plan,
                                   confidence_flags, status, generated_at)
           VALUES (%s, %s, %s, 'S', 'O', 'A', 'P', %s::jsonb, %s, NOW() - make_interval(hours => %s))""",
        (consultation_id, doctor_id, patient_id, flags, status, hours_ago),
    )


def _drafted(cur, consultation_id, doctor_id, *, hours_ago=0, style="concise"):
    cur.execute(
        """INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata, created_at)
           VALUES (%s, %s, 'consult_soap_note_generated', %s::jsonb, NOW() - make_interval(hours => %s))""",
        (consultation_id, doctor_id, f'{{"style": "{style}", "ai_model": "should-never-surface"}}', hours_ago),
    )


def _document(cur, patient_id, filename, *, hours_ago=0, status="complete"):
    document_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO document_catalog (document_id, user_id, session_id, original_filename,
                                         blob_summary_path, document_type, ingestion_status, created_at)
           VALUES (%s, %s, %s, %s, 'summaries/x.json', 'lab_report', %s, NOW() - make_interval(hours => %s))""",
        (document_id, patient_id, str(uuid.uuid4()), filename, status, hours_ago),
    )
    return document_id


def _list_total(tile, items):
    """The unit each tile counts in. fields_flagged counts SECTIONS, so its list total is
    the sum of each row's flagged sections, not the row count."""
    if tile == "fields_flagged":
        return sum(len(item["flagged_sections"]) for item in items)
    return len(items)


@pytest.fixture
def world():
    """Two doctors. A has a varied history spread across all three windows; B has one of
    everything, all of which must stay invisible to A."""
    _skip_if_no_database()
    ids = {"doctors": [], "users": []}
    try:
        with connect_db() as conn:
            from app.services.appointments import ensure_booking_schema
            from app.services.consults import ensure_consult_schema
            from app.services.doctor_auth import ensure_doctor_auth_schema
            from app.services.soap_notes import ensure_soap_schema

            ensure_booking_schema(conn)
            ensure_consult_schema(conn)
            ensure_soap_schema(conn)
            ensure_doctor_auth_schema(conn)
            with conn.cursor() as cur:
                a = _doctor(cur, "Dr. Items A")
                b = _doctor(cur, "Dr. Items B")
                ids["doctors"] += [a, b]
                # Last visit 6 hours ago, so the three windows genuinely differ:
                # last_visit < 24h < 7d.
                ids["account_a"] = _account(cur, a, datetime.now() - timedelta(hours=6))
                ids["account_b"] = _account(cur, b, datetime.now() - timedelta(hours=6))
                ids["a"], ids["b"] = a, b

                p1 = _patient(cur, "Asha Items")
                p2 = _patient(cur, "Ravi Items")
                pb = _patient(cur, "Other Doctors Patient")
                ids["users"] += [p1, p2, pb]
                ids["p1"] = p1

                # 1. A draft, regenerated: two draft events, one inside last_visit, one at 12h.
                c1 = _consult(cur, _booking(cur, a, p1), a, p1)
                _note(cur, c1, a, p1, status="draft",
                      flags='{"subjective": true, "plan": true, "objective": false, "stray": true}')
                _drafted(cur, c1, a, hours_ago=1)
                _drafted(cur, c1, a, hours_ago=12)
                ids["regenerated"] = c1

                # 2. Held back (stale), drafted 3 days ago — only the 7d window sees the draft,
                #    but notes_blocked is current state and sees it in every window.
                c2 = _consult(cur, _booking(cur, a, p2), a, p2)
                _note(cur, c2, a, p2, status="stale", flags='{"assessment": true}', hours_ago=72)
                _drafted(cur, c2, a, hours_ago=72)
                ids["stale"] = c2

                # 3. Discarded consult that still has its draft row, as discard_consult leaves it.
                c3 = _consult(cur, _booking(cur, a, p1), a, p1, status="discarded")
                _note(cur, c3, a, p1, status="stale")
                _drafted(cur, c3, a, hours_ago=2, style="something-unexpected")
                ids["discarded"] = c3

                # 4. Documents: one recent, one at 30h, one still processing (never counted).
                ids["doc_recent"] = _document(cur, p1, "recent-cbc.pdf", hours_ago=1)
                _document(cur, p2, "older-lipids.pdf", hours_ago=30)
                _document(cur, p1, "still-processing.pdf", hours_ago=1, status="processing")

                # 5. Doctor B: one of everything. None of it may reach A.
                cb = _consult(cur, _booking(cur, b, pb), b, pb)
                _note(cur, cb, b, pb, status="stale", flags='{"plan": true}')
                _drafted(cur, cb, b, hours_ago=1)
                _document(cur, pb, "doctor-b-only.pdf", hours_ago=1)
            conn.commit()
        yield ids
    finally:
        with connect_db() as conn:
            with conn.cursor() as cur:
                for user_id in ids["users"]:
                    cur.execute("DELETE FROM document_catalog WHERE user_id = %s", (user_id,))
                for doctor_id in ids["doctors"]:
                    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                for user_id in ids["users"]:
                    cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            conn.commit()


# ---- the property the feature rests on ----

@pytest.mark.parametrize("window", ACTIVITY_WINDOWS)
@pytest.mark.parametrize("tile", ACTIVITY_TILES)
def test_every_tile_list_reconciles_with_its_count(world, tile, window):
    """Clicking a tile that says N must show exactly N of what it counts."""
    counts = get_activity_summary(world["a"], world["account_a"], window)["counts"]
    result = get_activity_items(world["a"], world["account_a"], window, tile)

    assert not result["truncated"]
    assert _list_total(tile, result["items"]) == counts[tile]


def test_the_windows_are_genuinely_different_in_this_fixture(world):
    """Guards the test above: if every window returned the same numbers, reconciling them
    would prove nothing about the window being shared between count and list."""
    per_window = {
        w: get_activity_summary(world["a"], world["account_a"], w)["counts"]["notes_drafted"]
        for w in ACTIVITY_WINDOWS
    }
    assert per_window == {"last_visit": 2, "24h": 3, "7d": 4}


# ---- notes drafted ----

def test_a_regenerated_note_is_one_row_per_draft(world):
    items = get_activity_items(world["a"], world["account_a"], "24h", "notes_drafted")["items"]
    regenerated = [i for i in items if i["consultation_id"] == world["regenerated"]]
    assert len(regenerated) == 2


def test_a_discarded_consults_note_is_listed_but_not_openable(world):
    """It WAS drafted, so it is counted and listed. But no screen shows a discarded
    consult, so offering to open it would land the doctor on nothing."""
    items = get_activity_items(world["a"], world["account_a"], "last_visit", "notes_drafted")["items"]
    discarded = [i for i in items if i["consultation_id"] == world["discarded"]]

    assert len(discarded) == 1
    assert discarded[0]["consult_status"] == "discarded"
    assert discarded[0]["openable"] is False


def test_openable_rows_carry_what_the_appointment_screen_needs(world):
    """The UI opens these through openReviewFromQueue, which needs exactly these fields."""
    items = get_activity_items(world["a"], world["account_a"], "last_visit", "notes_drafted")["items"]
    row = next(i for i in items if i["consultation_id"] == world["regenerated"])

    assert row["openable"] is True
    for field in ("booking_id", "patient_id", "patient_name", "department",
                  "appointment_start", "consult_status"):
        assert row[field], field
    assert row["patient_name"] == "Asha Items"


def test_style_is_allowlisted_and_the_model_name_never_leaves(world):
    items = get_activity_items(world["a"], world["account_a"], "7d", "notes_drafted")["items"]

    assert {i["style"] for i in items} <= {"concise", "detailed", None}
    assert "should-never-surface" not in str(items)
    assert "ai_model" not in str(items)


# ---- notes held back ----

def test_a_discarded_consults_leftover_note_is_not_held_back(world):
    """The same rule the tile applies: a discarded consult has no work left in it."""
    items = get_activity_items(world["a"], world["account_a"], "7d", "notes_blocked")["items"]
    assert [i["consultation_id"] for i in items] == [world["stale"]]


def test_held_back_is_current_state_in_every_window(world):
    """Drafted 3 days ago, still held back now — so it shows even since-last-visit."""
    for window in ACTIVITY_WINDOWS:
        items = get_activity_items(world["a"], world["account_a"], window, "notes_blocked")["items"]
        assert [i["consultation_id"] for i in items] == [world["stale"]], window


# ---- fields flagged ----

def test_flagged_sections_are_named_and_a_stray_key_adds_nothing(world):
    items = get_activity_items(world["a"], world["account_a"], "24h", "fields_flagged")["items"]
    row = next(i for i in items if i["consultation_id"] == world["regenerated"])

    # "stray": true is in the JSONB and must not appear; "objective": false must not either.
    assert row["flagged_sections"] == ["subjective", "plan"]


# ---- documents ----

def test_documents_exclude_unfinished_uploads_and_carry_viewer_fields(world):
    items = get_activity_items(world["a"], world["account_a"], "last_visit", "documents_summarized")["items"]

    assert [i["original_filename"] for i in items] == ["recent-cbc.pdf"]
    row = items[0]
    assert row["document_id"] == world["doc_recent"]
    assert row["patient_id"] == world["p1"]
    assert row["content_type"] == "application/pdf"
    assert row["openable"] is True


# ---- scoping ----

@pytest.mark.parametrize("tile", ACTIVITY_TILES)
def test_another_doctors_rows_never_appear(world, tile):
    items = get_activity_items(world["a"], world["account_a"], "7d", tile)["items"]
    assert "Other Doctors Patient" not in str(items)
    assert "doctor-b-only.pdf" not in str(items)


# ---- bounds and validation ----

def test_truncation_is_reported_not_silent(world):
    result = get_activity_items(world["a"], world["account_a"], "7d", "notes_drafted", limit=2)
    assert len(result["items"]) == 2
    assert result["truncated"] is True


def test_an_unknown_tile_or_window_is_refused(world):
    with pytest.raises(ValueError):
        get_activity_items(world["a"], world["account_a"], "7d", "everything")
    with pytest.raises(ValueError):
        get_activity_items(world["a"], world["account_a"], "30d", "notes_drafted")
