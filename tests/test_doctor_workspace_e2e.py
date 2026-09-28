"""End-to-end flows through the AI doctor workspace, over the real HTTP API.

"End-to-end" here means what it already means in this repository (see
test_soap_note_e2e.py and test_appointments_rest_e2e.py): a real FastAPI TestClient
against a real Postgres, driving whole flows through the actual routes with real
doctor session tokens — not a browser. This project has no browser-automation tooling
(no package.json, no Playwright/Selenium); that gap, and the decision to cover these
flows at the API level instead, is recorded in docs/ai-redesign/plan.md D2.

The five flows required by the redesign brief:

  1. open the overview, take the top prioritised item, verify its sections, sign it
  2. regenerate a blocked (stale) note
  3. approve a prescription and confirm it becomes read-only
  4. share a signed note, then confirm the patient-facing view carries no clinician-only
     signals
  5. reach every sidebar destination

Each flow asserts the SAFETY invariant that belongs to it, not merely that the happy path
returns 200. Where a step must be refused, the test asserts the refusal.

Skips (not fails) if no database is reachable.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.db.connection import connect_db
from app.services.tokens import create_doctor_session_token

client = TestClient(app)


def _skip_if_no_database():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


# ---- fixtures (same shape as test_doctor_workspace_integration.py) ----

def _make_doctor(cur, name):
    cur.execute(
        """INSERT INTO doctors (name, department, experience_years, is_active)
           VALUES (%s, %s, %s, TRUE) RETURNING doctor_id""",
        (name, "Testing", 1),
    )
    return str(cur.fetchone()[0])


def _make_account(cur, doctor_id, email):
    cur.execute(
        """INSERT INTO doctor_accounts (doctor_id, email, hashed_password, is_active, mfa_enabled)
           VALUES (%s, %s, 'x', TRUE, TRUE) RETURNING id""",
        (doctor_id, email),
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


def _make_booking(cur, doctor_id, patient_id, hours_ago=2):
    start_time = datetime.now() - timedelta(hours=hours_ago)
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


def _make_consult(cur, booking_id, doctor_id, patient_id, transcript_source="batch"):
    cur.execute(
        """INSERT INTO consultations (booking_id, doctor_id, patient_id, status,
                                      transcript_source, ended_at)
           VALUES (%s, %s, %s, 'transcript_ready', %s, NOW()) RETURNING id""",
        (booking_id, doctor_id, patient_id, transcript_source),
    )
    return str(cur.fetchone()[0])


def _make_note(cur, consultation_id, doctor_id, patient_id, *, status="draft",
               confidence_flags="{}", plan="- Amlodipine 5 mg once daily"):
    cur.execute(
        """INSERT INTO soap_notes (consultation_id, doctor_id, patient_id,
                                   subjective, objective, assessment, plan,
                                   field_citations, confidence_flags, status,
                                   generated_at, ai_model, ai_prompt_version)
           VALUES (%s, %s, %s, 'Reports headache.', 'BP 130/80.', 'Tension headache.', %s,
                   '{"subjective": ["said headache"]}'::jsonb, %s::jsonb, %s, NOW(),
                   'test-model', 'v1-concise')
           RETURNING id""",
        (consultation_id, doctor_id, patient_id, plan, confidence_flags, status),
    )
    return str(cur.fetchone()[0])


def _ensure_schema(conn):
    from app.services.appointments import ensure_booking_schema
    from app.services.clinical_items import ensure_clinical_items_schema
    from app.services.consults import ensure_consult_schema
    from app.services.doctor_auth import ensure_doctor_auth_schema
    from app.services.soap_notes import ensure_soap_schema
    from app.services.soap_sections import ensure_section_verification_schema

    ensure_booking_schema(conn)
    ensure_consult_schema(conn)
    ensure_soap_schema(conn)
    ensure_doctor_auth_schema(conn)
    ensure_clinical_items_schema(conn)
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


def _headers(doctor_id, account_id, email="e2e@example.com"):
    """A real doctor session token, minted the same way the MFA challenge mints it, so
    every request below goes through get_current_doctor exactly as a browser would."""
    token = create_doctor_session_token(doctor_id=doctor_id, account_id=account_id, email=email)
    return {"Authorization": f"Bearer {token}"}


# ---- Flow 1: overview -> prioritised item -> verify sections -> sign ----

def test_flow_overview_to_signed_note():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. E2E Flow1")
                account_id = _make_account(cur, doctor_id, "flow1@example.com")
                patient_id = _make_patient(cur, "flow1-patient@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _make_note(cur, consult, doctor_id, patient_id,
                           confidence_flags='{"assessment": true}')
            conn.commit()

        headers = _headers(doctor_id, account_id)

        # The overview's two AI panels load.
        summary = client.get("/doctor/ai/activity-summary", headers=headers)
        assert summary.status_code == 200
        assert summary.json()["counts"]["awaiting_signature"] == 1

        assert client.get("/doctor/ai/activity-log", headers=headers).status_code == 200

        # The prioritised queue puts this item at the top, with its lane and explanation.
        reviews = client.get("/doctor/reviews?scope=pending", headers=headers)
        assert reviews.status_code == 200
        payload = reviews.json()
        assert payload["ranked_consultation_ids"][0] == consult
        row = payload["reviews"][0]
        assert row["lane"] == "quick_review"
        assert row["ai_explanation"]

        # Verify each section in turn; progress accumulates.
        for index, section in enumerate(("subjective", "objective", "assessment", "plan"), start=1):
            response = client.post(
                f"/doctor/consult/{consult}/soap/sections/{section}/verify",
                headers=headers, json={"verified": True},
            )
            assert response.status_code == 200
            assert len(response.json()["verified_sections"]) == index

        # Sign. Note the flagged 'assessment' section did NOT block this (plan D4).
        signed = client.post(f"/doctor/consult/{consult}/soap/sign", headers=headers)
        assert signed.status_code == 200
        assert signed.json()["status"] == "signed"
        assert signed.json()["signed_at"]

        # Signed notes leave the pending queue.
        after = client.get("/doctor/reviews?scope=pending", headers=headers).json()
        assert consult not in [r["consultation_id"] for r in after["reviews"]]

        # And a section can no longer be marked, because the signature is now the record.
        refused = client.post(
            f"/doctor/consult/{consult}/soap/sections/plan/verify",
            headers=headers, json={"verified": False},
        )
        assert refused.status_code == 409
    finally:
        _cleanup((doctor_id,), (patient_id,))


# ---- Flow 2: a blocked note ----

def test_flow_blocked_note_cannot_be_signed_through_the_api():
    """SAFETY (plan §5). The UI disables the sign button on a blocked note, but that is a
    convenience — the API must refuse it regardless of what any client sends."""
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. E2E Flow2")
                account_id = _make_account(cur, doctor_id, "flow2@example.com")
                patient_id = _make_patient(cur, "flow2-patient@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _make_note(cur, consult, doctor_id, patient_id, status="stale")
            conn.commit()

        headers = _headers(doctor_id, account_id)

        # It is surfaced as blocked, in the needs-attention lane, ranked first.
        payload = client.get("/doctor/reviews?scope=pending", headers=headers).json()
        row = next(r for r in payload["reviews"] if r["consultation_id"] == consult)
        assert row["is_stale"] is True
        assert row["lane"] == "needs_attention"
        assert payload["ranked_consultation_ids"][0] == consult
        assert "regenerate" in row["ai_explanation"].lower()

        # Signing is refused at the API.
        refused = client.post(f"/doctor/consult/{consult}/soap/sign", headers=headers)
        assert refused.status_code == 409

        # It is still blocked, and still unsigned.
        note = client.get(f"/doctor/consult/{consult}/soap", headers=headers).json()
        assert note["status"] == "stale"
        assert note["signed_at"] is None

        # Its plan cannot be copied into a prescription either, because it is not signed.
        assert client.get(
            f"/doctor/consult/{consult}/soap/plan-medications", headers=headers
        ).status_code == 409
    finally:
        _cleanup((doctor_id,), (patient_id,))


# ---- Flow 3: approve a prescription, confirm it locks ----

def test_flow_approve_prescription_becomes_read_only():
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. E2E Flow3")
                account_id = _make_account(cur, doctor_id, "flow3@example.com")
                patient_id = _make_patient(cur, "flow3-patient@example.com")
                consult = _make_consult(
                    cur, _make_booking(cur, doctor_id, patient_id), doctor_id, patient_id)
                _make_note(cur, consult, doctor_id, patient_id, status="signed")
                cur.execute(
                    "UPDATE soap_notes SET signed_at = NOW(), signed_by = %s WHERE consultation_id = %s",
                    (doctor_id, consult),
                )
            conn.commit()

        headers = _headers(doctor_id, account_id)

        # Insert from plan copies the signed plan's medication line, verbatim.
        copied = client.get(f"/doctor/consult/{consult}/soap/plan-medications", headers=headers)
        assert copied.status_code == 200
        assert copied.json()["lines"] == ["Amlodipine 5 mg once daily"]
        assert copied.json()["validated"] is False

        # Save it as a draft prescription, then approve.
        saved = client.put(
            f"/doctor/consult/{consult}/clinical-items/prescription",
            headers=headers, json={"content": "Amlodipine 5 mg once daily"},
        )
        assert saved.status_code == 200
        assert saved.json()["status"] == "draft"

        approved = client.post(
            f"/doctor/consult/{consult}/clinical-items/prescription/approve", headers=headers
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        assert approved.json()["approved_at"]

        # SAFETY: an approved record is immutable at the API, not merely disabled in the UI.
        refused = client.put(
            f"/doctor/consult/{consult}/clinical-items/prescription",
            headers=headers, json={"content": "Amlodipine 10 mg once daily"},
        )
        assert refused.status_code == 409

        # The stored content is unchanged by the refused write.
        current = client.get(
            f"/doctor/consult/{consult}/clinical-items/prescription", headers=headers
        ).json()
        assert current["content"] == "Amlodipine 5 mg once daily"
        assert current["status"] == "approved"
    finally:
        _cleanup((doctor_id,), (patient_id,))


# ---- Flow 4: share a signed note; patient view carries no clinician-only signals ----

def test_flow_share_and_patient_view_has_no_clinician_signals():
    """SAFETY (plan §5). The patient-facing projection must never carry citations,
    confidence flags, transcript provenance, model or prompt details, or verification
    state — whatever is stored on the note."""
    _skip_if_no_database()

    doctor_id = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. E2E Flow4")
                account_id = _make_account(cur, doctor_id, "flow4@example.com")
                patient_id = _make_patient(cur, "flow4-patient@example.com")
                booking = _make_booking(cur, doctor_id, patient_id)
                consult = _make_consult(cur, booking, doctor_id, patient_id,
                                        transcript_source="live_fallback")
                _make_note(cur, consult, doctor_id, patient_id, status="draft",
                           confidence_flags='{"assessment": true}')
                cur.execute(
                    "UPDATE soap_notes SET source_transcript_type = 'live_fallback' "
                    "WHERE consultation_id = %s", (consult,),
                )
            conn.commit()

        headers = _headers(doctor_id, account_id)

        # Cannot share before signing.
        assert client.post(
            f"/doctor/consult/{consult}/soap/share", headers=headers
        ).status_code == 409

        assert client.post(f"/doctor/consult/{consult}/soap/sign", headers=headers).status_code == 200
        shared = client.post(f"/doctor/consult/{consult}/soap/share", headers=headers)
        assert shared.status_code == 200
        assert shared.json()["shared_with_patient_at"]

        # The doctor's own view still carries the clinician-only signals...
        doctor_view = client.get(f"/doctor/consult/{consult}/soap", headers=headers).json()
        assert doctor_view["ai_model"] == "test-model"
        assert doctor_view["confidence_flags"]
        assert doctor_view["field_citations"]

        # ...but the patient's projection carries none of them.
        from app.services.soap_notes import list_shared_notes_for_patient

        patient_view = list_shared_notes_for_patient(patient_id, [booking])
        assert booking in patient_view
        visit = patient_view[booking]
        assert visit["assessment"] == "Tension headache."
        for forbidden in (
            "field_citations", "confidence_flags", "source_transcript_type",
            "ai_model", "ai_prompt_version", "status", "verified_sections",
        ):
            assert forbidden not in visit, f"patient view leaked {forbidden}"
        # And nothing that merely LOOKS like a flag leaked through the values either.
        assert "test-model" not in str(visit)
        assert "live_fallback" not in str(visit)
    finally:
        _cleanup((doctor_id,), (patient_id,))


# ---- Flow 5: every sidebar destination ----

def test_flow_every_sidebar_destination_loads():
    """The five sidebar items map to these endpoints. A brand-new doctor with no data must
    get an empty state from each, never an error."""
    _skip_if_no_database()

    doctor_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_id = _make_doctor(cur, "Dr. E2E Flow5")
                account_id = _make_account(cur, doctor_id, "flow5@example.com")
            conn.commit()

        headers = _headers(doctor_id, account_id)

        for label, url in (
            ("Overview: profile", "/doctor/me"),
            ("Overview: activity", "/doctor/ai/activity-summary"),
            ("Overview: feed", "/doctor/ai/activity-log"),
            ("Reviews: pending", "/doctor/reviews?scope=pending"),
            ("Reviews: signed", "/doctor/reviews?scope=completed"),
            ("Upcoming", "/doctor/appointments?scope=upcoming"),
            ("Past", "/doctor/appointments?scope=past"),
            ("Patients", "/doctor/patients"),
        ):
            response = client.get(url, headers=headers)
            assert response.status_code == 200, f"{label} returned {response.status_code}"

        # Log out is a client-side token discard; the server-side property that matters is
        # that no doctor endpoint answers without a valid token at all.
        for url in ("/doctor/me", "/doctor/reviews", "/doctor/ai/activity-summary",
                    "/doctor/patients", "/doctor/appointments?scope=upcoming"):
            assert client.get(url).status_code == 401, f"{url} answered without a token"
    finally:
        _cleanup((doctor_id,), ())


# ---- Cross-doctor isolation across the whole new surface ----

def test_doctor_a_cannot_reach_doctor_bs_workspace_data():
    """SAFETY (plan §5). One test that walks the entire new surface as the wrong doctor."""
    _skip_if_no_database()

    doctor_a = doctor_b = patient_id = None
    try:
        with connect_db() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                doctor_a = _make_doctor(cur, "Dr. E2E A")
                doctor_b = _make_doctor(cur, "Dr. E2E B")
                account_b = _make_account(cur, doctor_b, "e2e-b@example.com")
                patient_id = _make_patient(cur, "e2e-isolation@example.com")
                booking_a = _make_booking(cur, doctor_a, patient_id)
                consult_a = _make_consult(cur, booking_a, doctor_a, patient_id)
                _make_note(cur, consult_a, doctor_a, patient_id)
            conn.commit()

        headers_b = _headers(doctor_b, account_b, "e2e-b@example.com")

        # Doctor B sees none of A's work in their own queue or counts.
        payload = client.get("/doctor/reviews?scope=pending", headers=headers_b).json()
        assert consult_a not in [r["consultation_id"] for r in payload["reviews"]]
        assert consult_a not in payload["ranked_consultation_ids"]
        assert client.get(
            "/doctor/ai/activity-summary", headers=headers_b
        ).json()["counts"]["awaiting_signature"] == 0

        # And cannot reach A's consult directly by id, on any of the new routes.
        for method, url in (
            ("get", f"/doctor/consult/{consult_a}/soap"),
            ("get", f"/doctor/consult/{consult_a}/soap/sections"),
            ("get", f"/doctor/consult/{consult_a}/soap/plan-medications"),
            ("post", f"/doctor/consult/{consult_a}/soap/sign"),
        ):
            response = getattr(client, method)(url, headers=headers_b)
            assert response.status_code in (404, 409), f"{url} returned {response.status_code}"

        # Nor A's appointment's visit brief — 404, never 403.
        assert client.get(
            f"/doctor/appointments/{booking_a}/brief", headers=headers_b
        ).status_code == 404
        assert client.post(
            f"/doctor/consult/{consult_a}/soap/sections/plan/verify",
            headers=headers_b, json={"verified": True},
        ).status_code == 404
    finally:
        _cleanup((doctor_a, doctor_b), (patient_id,))
