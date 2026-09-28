"""Route wiring for the AI doctor-workspace endpoints.

Same convention as test_doctor_reviews.py: the route functions are called directly with
the service monkeypatched, proving each one passes the *authenticated* doctor's own
identity and never anything a client could supply, plus the input-validation and error
mapping branches.

test_doctor_workspace_integration.py covers the actual SQL (cross-doctor isolation) and
test_doctor_workspace.py the pure logic. This file covers the layer between them, and in
particular pins down the property that matters most: **none of these route signatures has
a client-controllable doctor_id or patient-scope parameter.**
"""

import asyncio

import pytest
from fastapi import HTTPException

from app.api.routes import consult as consult_route
from app.api.routes import doctor as doctor_route


def _doctor(doctor_id="doctor-1", account_id="account-1"):
    return {
        "doctor_id": doctor_id,
        "account_id": account_id,
        "name": "Dr. Test",
        "department": "Neurology",
    }


class _Request:
    """Minimal stand-in for fastapi.Request — the rate-limited routes read client.host."""

    def __init__(self, host="203.0.113.10"):
        self.client = type("Client", (), {"host": host})()


# ---- activity summary ----

def test_activity_summary_passes_the_authenticated_doctor_and_account(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        doctor_route, "get_activity_summary",
        lambda doctor_id, account_id, window: seen.update(
            doctor_id=doctor_id, account_id=account_id, window=window
        ) or {},
    )

    doctor_route.doctor_ai_activity_summary_route(
        doctor=_doctor("authenticated-doctor", "authenticated-account")
    )

    assert seen == {
        "doctor_id": "authenticated-doctor",
        "account_id": "authenticated-account",
        "window": "last_visit",
    }


@pytest.mark.parametrize("window", ["last_visit", "24h", "7d"])
def test_activity_summary_forwards_each_supported_window(monkeypatch, window):
    seen = {}
    monkeypatch.setattr(
        doctor_route, "get_activity_summary",
        lambda doctor_id, account_id, w: seen.update(window=w) or {},
    )

    doctor_route.doctor_ai_activity_summary_route(
        window=window, doctor=_doctor("d", "a")
    )

    assert seen["window"] == window


@pytest.mark.parametrize("window", ["last_week", "", "1h", "LAST_VISIT; DROP TABLE"])
def test_activity_summary_rejects_an_unknown_window_rather_than_defaulting(monkeypatch, window):
    """Silently falling back to the default would change what a clinical figure counts
    without telling anyone — the same discipline the scope parameters use."""
    called = []
    monkeypatch.setattr(
        doctor_route, "get_activity_summary",
        lambda *args: called.append(args) or {},
    )

    with pytest.raises(HTTPException) as caught:
        doctor_route.doctor_ai_activity_summary_route(window=window, doctor=_doctor("d", "a"))

    assert caught.value.status_code == 400
    assert not called, "the service was reached with an unvalidated window"


def test_a_window_is_accepted_regardless_of_case_and_padding(monkeypatch):
    """Normalised the same way the scope parameters are, so "24H " is not a 400."""
    seen = {}
    monkeypatch.setattr(
        doctor_route, "get_activity_summary",
        lambda doctor_id, account_id, w: seen.update(window=w) or {},
    )

    doctor_route.doctor_ai_activity_summary_route(window="  24H ", doctor=_doctor("d", "a"))

    assert seen["window"] == "24h"


# ---- activity tile drill-downs ----

def test_activity_items_scope_to_the_authenticated_doctor_and_normalise(monkeypatch):
    """No doctor_id parameter exists on the route: the caller is always the JWT's doctor."""
    seen = {}
    monkeypatch.setattr(
        doctor_route, "get_activity_items",
        lambda doctor_id, account_id, window, tile, limit: seen.update(
            doctor_id=doctor_id, account_id=account_id, window=window, tile=tile, limit=limit
        ) or {},
    )

    doctor_route.doctor_ai_activity_items_route(
        tile=" Notes_Drafted ", window="7D", limit=10,
        doctor=_doctor("authenticated-doctor", "authenticated-account"),
    )

    assert seen == {
        "doctor_id": "authenticated-doctor", "account_id": "authenticated-account",
        "window": "7d", "tile": "notes_drafted", "limit": 10,
    }


@pytest.mark.parametrize("tile, window", [
    ("everything", "7d"),
    ("", "7d"),
    ("notes_drafted; DROP TABLE", "7d"),
    ("notes_drafted", "30d"),
    ("notes_drafted", ""),
])
def test_activity_items_reject_an_unknown_tile_or_window(monkeypatch, tile, window):
    """Defaulting would show a different list under the tile's label."""
    called = []
    monkeypatch.setattr(doctor_route, "get_activity_items", lambda *args: called.append(args) or {})

    with pytest.raises(HTTPException) as caught:
        doctor_route.doctor_ai_activity_items_route(
            tile=tile, window=window, limit=50, doctor=_doctor("d", "a")
        )

    assert caught.value.status_code == 400
    assert not called, "the service was reached with an unvalidated parameter"


# ---- activity log ----

def test_activity_log_passes_the_authenticated_doctor(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        doctor_route, "get_activity_log",
        lambda doctor_id, limit: seen.update(doctor_id=doctor_id, limit=limit) or {"events": []},
    )

    doctor_route.doctor_ai_activity_log_route(limit=10, doctor=_doctor("authenticated-doctor"))

    assert seen == {"doctor_id": "authenticated-doctor", "limit": 10}


def test_activity_log_limit_bounds_are_declared_on_the_route():
    """The clamp is enforced twice — FastAPI's ge/le here, and again in the service. This
    asserts the route-level half is actually wired, since a Query default is easy to drop
    in an edit."""
    from app.services.doctor_ai_activity import ACTIVITY_LOG_DEFAULT_LIMIT, ACTIVITY_LOG_MAX_LIMIT

    assert ACTIVITY_LOG_DEFAULT_LIMIT <= ACTIVITY_LOG_MAX_LIMIT
    query = doctor_route.doctor_ai_activity_log_route.__defaults__[0]
    assert query.default == ACTIVITY_LOG_DEFAULT_LIMIT
    # Pydantic v2 keeps the constraints as annotated-types metadata on the Query object.
    bounds = {type(item).__name__: getattr(item, attr)
              for item, attr in ((m, m.__class__.__name__.lower()) for m in query.metadata)}
    assert bounds == {"Ge": 1, "Le": ACTIVITY_LOG_MAX_LIMIT}


# ---- bulk draft ----

def test_draft_all_rejects_an_unknown_style():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(doctor_route.doctor_draft_all_missing_notes_route(
            http_request=_Request(), style="poetic", doctor=_doctor()
        ))
    assert exc.value.status_code == 400


def test_draft_all_normalizes_style_and_passes_the_authenticated_doctor(monkeypatch):
    seen = {}

    async def fake_bulk(doctor_id, ip, style):
        seen.update(doctor_id=doctor_id, ip=ip, style=style)
        return {"drafted": [], "failed": [], "attempted": 0, "remaining": 0}

    monkeypatch.setattr(doctor_route, "draft_all_missing_notes", fake_bulk)

    asyncio.run(doctor_route.doctor_draft_all_missing_notes_route(
        http_request=_Request("198.51.100.7"), style="  DETAILED  ",
        doctor=_doctor("authenticated-doctor"),
    ))

    assert seen["doctor_id"] == "authenticated-doctor"
    assert seen["style"] == "detailed"
    assert seen["ip"] == "198.51.100.7"


def test_draft_all_maps_the_rate_limit_to_429_with_retry_after(monkeypatch):
    async def fake_bulk(doctor_id, ip, style):
        raise PermissionError("Too many bulk drafting requests.")

    monkeypatch.setattr(doctor_route, "draft_all_missing_notes", fake_bulk)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(doctor_route.doctor_draft_all_missing_notes_route(
            http_request=_Request(), style="concise", doctor=_doctor()
        ))

    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"] == "300"


# ---- visit brief ----

def test_visit_brief_takes_the_doctor_and_department_from_the_token(monkeypatch):
    """The department decides whether a sensitive specialty's notes are shown, so it must
    never be something a client can claim."""
    seen = {}
    monkeypatch.setattr(
        doctor_route, "get_visit_brief",
        lambda doctor_id, booking_id, department: seen.update(
            doctor_id=doctor_id, booking_id=booking_id, department=department
        ) or {},
    )

    doctor_route.doctor_visit_brief_route("b-1", doctor=_doctor("authenticated-doctor", "a"))

    assert seen == {"doctor_id": "authenticated-doctor", "booking_id": "b-1", "department": "Neurology"}


def test_visit_brief_maps_not_yours_to_404_not_403(monkeypatch):
    def refuse(*args, **kwargs):
        raise PermissionError("Appointment not found.")

    monkeypatch.setattr(doctor_route, "get_visit_brief", refuse)
    with pytest.raises(HTTPException) as exc:
        doctor_route.doctor_visit_brief_route("someone-elses-booking", doctor=_doctor())
    assert exc.value.status_code == 404


# ---- section verification ----

def test_verify_section_passes_the_authenticated_doctor(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        consult_route, "set_section_verified",
        lambda consultation_id, doctor_id, section, verified: seen.update(
            consultation_id=consultation_id, doctor_id=doctor_id,
            section=section, verified=verified,
        ) or {"verified_sections": [section]},
    )

    consult_route.verify_section_route(
        consultation_id="consult-1", section="assessment",
        request=consult_route.SectionVerifyRequest(verified=True),
        doctor=_doctor("authenticated-doctor"),
    )

    assert seen == {
        "consultation_id": "consult-1", "doctor_id": "authenticated-doctor",
        "section": "assessment", "verified": True,
    }


def test_verify_section_defaults_to_marking_when_no_body_is_sent():
    assert consult_route.SectionVerifyRequest().verified is True


def test_verify_section_supports_clearing_a_mark(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        consult_route, "set_section_verified",
        lambda consultation_id, doctor_id, section, verified: seen.update(verified=verified)
        or {"verified_sections": []},
    )

    consult_route.verify_section_route(
        consultation_id="consult-1", section="plan",
        request=consult_route.SectionVerifyRequest(verified=False),
        doctor=_doctor(),
    )

    assert seen["verified"] is False


def test_verify_section_maps_an_unknown_section_to_400(monkeypatch):
    def fake(consultation_id, doctor_id, section, verified):
        raise ValueError("section must be one of ('subjective', 'objective', 'assessment', 'plan').")

    monkeypatch.setattr(consult_route, "set_section_verified", fake)

    with pytest.raises(HTTPException) as exc:
        consult_route.verify_section_route(
            consultation_id="consult-1", section="diagnosis",
            request=consult_route.SectionVerifyRequest(), doctor=_doctor(),
        )
    assert exc.value.status_code == 400


def test_verify_section_maps_a_signed_note_to_409(monkeypatch):
    def fake(consultation_id, doctor_id, section, verified):
        raise PermissionError("This note is signed.")

    monkeypatch.setattr(consult_route, "set_section_verified", fake)

    with pytest.raises(HTTPException) as exc:
        consult_route.verify_section_route(
            consultation_id="consult-1", section="plan",
            request=consult_route.SectionVerifyRequest(), doctor=_doctor(),
        )
    assert exc.value.status_code == 409


def test_verify_section_maps_a_missing_consult_to_404(monkeypatch):
    def fake(consultation_id, doctor_id, section, verified):
        raise ValueError("Consult not found.")

    monkeypatch.setattr(consult_route, "set_section_verified", fake)

    with pytest.raises(HTTPException) as exc:
        consult_route.verify_section_route(
            consultation_id="nope", section="plan",
            request=consult_route.SectionVerifyRequest(), doctor=_doctor(),
        )
    assert exc.value.status_code == 404


def test_get_verified_sections_passes_the_authenticated_doctor(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        consult_route, "list_verified_sections",
        lambda consultation_id, doctor_id: seen.update(
            consultation_id=consultation_id, doctor_id=doctor_id) or ["plan"],
    )

    result = consult_route.get_verified_sections_route(
        consultation_id="consult-9", doctor=_doctor("authenticated-doctor")
    )

    assert seen == {"consultation_id": "consult-9", "doctor_id": "authenticated-doctor"}
    assert result == {"verified_sections": ["plan"]}


# ---- Insert from plan ----

def test_plan_medications_refuses_an_unsigned_note(monkeypatch):
    """SAFETY (plan §5). Copying an unsigned draft's plan into a prescription field would
    move AI output into a clinical action with no signature behind it."""
    monkeypatch.setattr(
        consult_route, "get_soap_note",
        lambda consultation_id, doctor_id: {"status": "draft", "plan": "- Amlodipine 5 mg daily"},
    )

    with pytest.raises(HTTPException) as exc:
        consult_route.get_plan_medications_route(consultation_id="c1", doctor=_doctor())

    assert exc.value.status_code == 409


def test_plan_medications_returns_signed_lines_and_says_nothing_is_validated(monkeypatch):
    monkeypatch.setattr(
        consult_route, "get_soap_note",
        lambda consultation_id, doctor_id: {
            "status": "signed",
            "plan": "Medications:\n- Amlodipine 5 mg once daily\nReview in six weeks.",
        },
    )

    result = consult_route.get_plan_medications_route(consultation_id="c1", doctor=_doctor())

    assert result["lines"] == ["Amlodipine 5 mg once daily"]
    # The payload must carry its own disclaimer, so a client cannot present these as
    # checked content without also having been told they are not.
    assert result["validated"] is False
    assert "no dose" in result["notice"].lower()


def test_plan_medications_passes_the_authenticated_doctor(monkeypatch):
    seen = {}

    def fake_get(consultation_id, doctor_id):
        seen.update(consultation_id=consultation_id, doctor_id=doctor_id)
        return {"status": "signed", "plan": "- Ramipril 2.5 mg daily"}

    monkeypatch.setattr(consult_route, "get_soap_note", fake_get)

    consult_route.get_plan_medications_route(
        consultation_id="c9", doctor=_doctor("authenticated-doctor")
    )

    assert seen == {"consultation_id": "c9", "doctor_id": "authenticated-doctor"}


def test_plan_medications_maps_a_missing_note_to_404(monkeypatch):
    monkeypatch.setattr(consult_route, "get_soap_note", lambda consultation_id, doctor_id: None)

    with pytest.raises(HTTPException) as exc:
        consult_route.get_plan_medications_route(consultation_id="c1", doctor=_doctor())

    assert exc.value.status_code == 404


# ---- the shape of the whole surface ----

def test_no_new_route_accepts_a_client_supplied_doctor_id():
    """The single most important property of this surface. Asserted structurally so a
    future edit that adds a doctor_id parameter to any of these fails here rather than
    silently widening access."""
    import inspect

    routes = (
        doctor_route.doctor_ai_activity_summary_route,
        doctor_route.doctor_ai_activity_log_route,
        doctor_route.doctor_draft_all_missing_notes_route,
        doctor_route.doctor_visit_brief_route,
        consult_route.verify_section_route,
        consult_route.get_verified_sections_route,
        consult_route.get_plan_medications_route,
    )
    for route in routes:
        params = set(inspect.signature(route).parameters)
        assert "doctor_id" not in params, f"{route.__name__} exposes a client-controllable doctor_id"
        assert "account_id" not in params, f"{route.__name__} exposes a client-controllable account_id"
        assert "doctor" in params, f"{route.__name__} does not take the authenticated doctor"


def test_there_is_no_unverify_all_or_bulk_sign_route():
    """Verification is per-section and signing is per-note, deliberately. A bulk-sign
    button would let a doctor sign AI output they have not read, which is the exact
    failure this whole design exists to prevent."""
    paths = [getattr(route, "__name__", "") for route in vars(consult_route).values() if callable(route)]
    assert not any("bulk_sign" in name or "sign_all" in name for name in paths)
    doctor_paths = [getattr(route, "__name__", "") for route in vars(doctor_route).values() if callable(route)]
    assert not any("sign_all" in name or "approve_all" in name for name in doctor_paths)


# ---- document clinical view and trends (patient history, feature 3) ----

def test_the_clinical_view_refuses_a_document_the_doctor_may_not_read(monkeypatch):
    """404, not 403 — the same non-disclosure rule the other document routes use, so this
    cannot be used to probe which documents exist."""
    def refuse(*args, **kwargs):
        raise PermissionError("Patient not found.")

    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", refuse)

    with pytest.raises(HTTPException) as caught:
        doctor_route.doctor_patient_document_clinical_route(
            "p1", "d1", doctor=_doctor("d", "a")
        )
    assert caught.value.status_code == 404


def test_the_clinical_view_never_returns_the_model_name(monkeypatch):
    """Which model wrote a summary is recorded for support, but a doctor is not shown it —
    and it must not reach the browser either."""
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "record_document_content_read", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "findings_for_document", lambda *a, **k: [])
    monkeypatch.setattr(doctor_route, "get_document_pages", lambda *a, **k: [])
    monkeypatch.setattr(doctor_route, "review_states", lambda ids, *a, **k: {i: None for i in ids})
    monkeypatch.setattr(
        doctor_route, "get_summary",
        lambda *a, **k: {"sentences": [], "verification": "passed", "model": "gpt-4o-mini"},
    )

    payload = doctor_route.doctor_patient_document_clinical_route(
        "p1", "d1", doctor=_doctor("d", "a")
    )

    assert "model" not in payload["summary"]
    assert "gpt-4o-mini" not in str(payload)


def test_a_document_with_no_summary_returns_null_not_an_empty_one(monkeypatch):
    """None means "never generated"; a verification='failed' row means "generated and
    entirely unverifiable". The UI says something different for each, so the route must
    not collapse them."""
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "record_document_content_read", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "findings_for_document", lambda *a, **k: [])
    monkeypatch.setattr(doctor_route, "get_document_pages", lambda *a, **k: [])
    monkeypatch.setattr(doctor_route, "review_states", lambda ids, *a, **k: {i: None for i in ids})
    monkeypatch.setattr(doctor_route, "get_summary", lambda *a, **k: None)

    payload = doctor_route.doctor_patient_document_clinical_route(
        "p1", "d1", doctor=_doctor("d", "a")
    )
    assert payload["summary"] is None


def test_the_clinical_view_answers_409_for_a_document_still_processing(monkeypatch):
    """A real state of a document the doctor may read — not a server fault. It used to be a
    500, because the route caught PermissionError only."""
    def processing(*args, **kwargs):
        raise ValueError("This document has not finished processing.")

    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", processing)
    with pytest.raises(HTTPException) as caught:
        doctor_route.doctor_patient_document_clinical_route("p1", "d1", doctor=_doctor("d", "a"))
    assert caught.value.status_code == 409


def test_reading_the_clinical_view_is_audited(monkeypatch):
    """Document CONTENT reads are audited. The viewer moved here from a route that audited
    internally, and this one did not, so the move silently stopped the record."""
    seen = []
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "findings_for_document", lambda *a, **k: [])
    monkeypatch.setattr(doctor_route, "get_document_pages", lambda *a, **k: [])
    monkeypatch.setattr(doctor_route, "review_states", lambda ids, *a, **k: {i: None for i in ids})
    monkeypatch.setattr(doctor_route, "get_summary", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "record_document_content_read", lambda *a, **k: seen.append(a))

    doctor_route.doctor_patient_document_clinical_route("p1", "d1", doctor=_doctor("doc-1", "a"))

    assert seen == [("doc-1", "p1", "d1")]


def test_the_clinical_view_reports_how_many_results_the_report_itself_flags(monkeypatch):
    """"Nothing missed", made checkable: the report's own flag count travels with the list,
    so the viewer can say "the report marks 3; 2 are listed" instead of looking complete."""
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "record_document_content_read", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "get_summary", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "get_document_pages", lambda *a, **k: [{
        "page_no": 1,
        "text": "RDW-CV 14.8 H % 11.6 - 14.0\nESR 14 H mm/1st hr 0 - 10\nVitamin B12 178 L pg/mL 211 - 911",
    }])
    monkeypatch.setattr(doctor_route, "findings_for_document", lambda *a, **k: [
        {"flag_source": "report_flag"}, {"flag_source": "report_flag"}, {"flag_source": "report_range"},
    ])
    monkeypatch.setattr(doctor_route, "review_states", lambda ids, *a, **k: {i: None for i in ids})

    payload = doctor_route.doctor_patient_document_clinical_route("p1", "d1", doctor=_doctor("d", "a"))
    assert payload["completeness"] == {"report_flagged": 3, "listed_from_report": 2}


def test_a_refused_clinical_read_is_not_recorded_as_a_read(monkeypatch):
    seen = []
    def refuse(*args, **kwargs):
        raise PermissionError("Patient not found.")
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", refuse)
    monkeypatch.setattr(doctor_route, "record_document_content_read", lambda *a, **k: seen.append(a))

    with pytest.raises(HTTPException):
        doctor_route.doctor_patient_document_clinical_route("p1", "d1", doctor=_doctor("d", "a"))
    assert seen == []


@pytest.mark.parametrize("message", ["Document not found.", "Some other lookup failure."])
def test_the_document_access_check_hides_existence(monkeypatch, message):
    """assert_doctor_may_read_document documents PermissionError for "not yours" and "does not
    exist" alike. _owned_entry signals those with ValueError, which used to pass straight
    through — so a wrong document id was a 500 next to a 404 for a foreign patient."""
    from app.services import document_catalog

    def missing(*args, **kwargs):
        raise ValueError(message)

    monkeypatch.setattr(document_catalog, "_owned_entry", missing)
    with pytest.raises(PermissionError):
        document_catalog.assert_doctor_may_read_document("d", "p", "doc")


def test_the_document_access_check_keeps_processing_distinct(monkeypatch):
    from app.services import document_catalog

    def processing(*args, **kwargs):
        raise ValueError("This document has not finished processing.")

    monkeypatch.setattr(document_catalog, "_owned_entry", processing)
    with pytest.raises(ValueError):
        document_catalog.assert_doctor_may_read_document("d", "p", "doc")


def test_viewing_the_overview_is_audited_even_from_cache(monkeypatch):
    """The card shows other departments' signed diagnoses — the disclosure the timeline
    audits. A cache hit is still a read. Only counts are recorded, never the text."""
    import asyncio

    seen = []
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda *a: True)

    async def overview(*args):
        return {"mode": "phrased", "cached": True, "lines": [],
                "facts": [{"kind": "diagnosis", "text": "Secret diagnosis"},
                          {"kind": "abnormal", "text": "x"}, {"kind": "abnormal", "text": "y"}]}

    monkeypatch.setattr(doctor_route, "get_overview", overview)
    monkeypatch.setattr(doctor_route, "_audit_patient_view",
                        lambda doctor_id, patient_id, action, **meta: seen.append((doctor_id, patient_id, action, meta)))

    asyncio.run(doctor_route.doctor_patient_overview_route("p1", doctor=_doctor("doc-1", "a")))

    assert len(seen) == 1
    doctor_id, patient_id, action, meta = seen[0]
    assert (doctor_id, patient_id, action) == ("doc-1", "p1", "patient_overview_viewed")
    assert meta["facts"] == {"diagnosis": 1, "abnormal": 2}
    assert "Secret diagnosis" not in str(meta)


@pytest.mark.parametrize(
    "route,args",
    [
        ("doctor_patient_finding_trend_route", ("p1", "Vitamin D")),
        ("doctor_patient_trends_route", ("p1",)),
    ],
)
def test_the_trend_routes_require_a_treating_relationship(monkeypatch, route, args):
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda *a, **k: False)

    with pytest.raises(HTTPException) as caught:
        getattr(doctor_route, route)(*args, doctor=_doctor("d", "a"))
    assert caught.value.status_code == 404


# ---- cross-doctor timeline (patient history, feature 2) ----

def test_the_timeline_requires_a_treating_relationship(monkeypatch):
    """404, never 403 — the same non-disclosure rule as every other patient route."""
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda *a, **k: False)

    with pytest.raises(HTTPException) as caught:
        doctor_route.doctor_patient_timeline_route("p1", doctor=_doctor("d", "a"))
    assert caught.value.status_code == 404


def test_the_timeline_passes_the_authenticated_doctor_and_their_own_department(monkeypatch):
    """The viewing doctor and the department that decides what they may read both come
    from the token. A client-supplied department would be a way to read a restricted
    specialty's notes by claiming to be in it."""
    seen = {}
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda *a, **k: True)
    monkeypatch.setattr(doctor_route, "_audit_timeline_view", lambda *a, **k: None)
    monkeypatch.setattr(
        doctor_route, "get_patient_timeline",
        lambda doctor_id, patient_id, viewer_department, **kw: seen.update(
            doctor_id=doctor_id, patient_id=patient_id, viewer_department=viewer_department, **kw
        ) or {"encounters": []},
    )

    doctor_route.doctor_patient_timeline_route(
        "patient-42", doctor=_doctor("authenticated-doctor", "a")
    )

    assert seen["doctor_id"] == "authenticated-doctor"
    assert seen["patient_id"] == "patient-42"
    assert seen["viewer_department"] == "Neurology"


def test_the_doctor_filter_narrows_the_timeline_and_is_not_the_viewer(monkeypatch):
    """`doctor_id` filters the timeline BY a doctor. It must never be mistaken for who is
    doing the viewing."""
    seen = {}
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda *a, **k: True)
    monkeypatch.setattr(doctor_route, "_audit_timeline_view", lambda *a, **k: None)
    monkeypatch.setattr(
        doctor_route, "get_patient_timeline",
        lambda doctor_id, patient_id, viewer_department, **kw: seen.update(
            viewer=doctor_id, filtered_by=kw.get("other_doctor_id")
        ) or {"encounters": []},
    )

    doctor_route.doctor_patient_timeline_route(
        "p1", doctor_id="some-other-doctor", doctor=_doctor("authenticated-doctor", "a")
    )

    assert seen["viewer"] == "authenticated-doctor"
    assert seen["filtered_by"] == "some-other-doctor"


def test_viewing_the_timeline_is_audited(monkeypatch):
    """This route widened what a doctor can see, so every call is recorded."""
    audited = {}
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda *a, **k: True)
    monkeypatch.setattr(
        doctor_route, "get_patient_timeline",
        lambda *a, **k: {"encounters": [{"booking_id": "b1"}]},
    )
    monkeypatch.setattr(
        doctor_route, "_audit_timeline_view",
        lambda doctor_id, patient_id, count: audited.update(
            doctor_id=doctor_id, patient_id=patient_id, count=count
        ),
    )

    doctor_route.doctor_patient_timeline_route("p1", doctor=_doctor("d", "a"))

    assert audited == {"doctor_id": "d", "patient_id": "p1", "count": 1}


def test_a_bad_filter_is_a_400_not_a_500(monkeypatch):
    """A malformed date must not surface as a server error carrying a database message."""
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda *a, **k: True)

    def bad_date(*args, **kwargs):
        raise ValueError('invalid input syntax for type date: "not-a-date"')

    monkeypatch.setattr(doctor_route, "get_patient_timeline", bad_date)

    with pytest.raises(HTTPException) as caught:
        doctor_route.doctor_patient_timeline_route(
            "p1", date_from="not-a-date", doctor=_doctor("d", "a")
        )
    assert caught.value.status_code == 400
    assert "syntax" not in str(caught.value.detail).lower()


# ---- patient overview (patient history, feature 4) ----

def test_the_overview_requires_a_treating_relationship(monkeypatch):
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda *a, **k: False)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(doctor_route.doctor_patient_overview_route("p1", doctor=_doctor("d", "a")))
    assert caught.value.status_code == 404


def test_the_overview_uses_the_viewers_own_department_from_the_token(monkeypatch):
    """The department decides what the card may include. A client-supplied one would be a
    way to read a restricted specialty by claiming to be in it."""
    seen = {}
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda *a, **k: True)

    async def fake_overview(doctor_id, patient_id, viewer_department):
        seen.update(doctor_id=doctor_id, patient_id=patient_id, department=viewer_department)
        return {"lines": [], "mode": "structured"}

    monkeypatch.setattr(doctor_route, "get_overview", fake_overview)

    asyncio.run(doctor_route.doctor_patient_overview_route(
        "patient-42", doctor=_doctor("authenticated-doctor", "a")
    ))

    assert seen == {
        "doctor_id": "authenticated-doctor",
        "patient_id": "patient-42",
        "department": "Neurology",
    }


def test_the_overview_reports_which_mode_it_is_returning(monkeypatch):
    """"phrased" and "structured" must stay distinguishable to the client: presenting the
    fallback as the summary would hide that verification failed."""
    monkeypatch.setattr(doctor_route, "doctor_treats_patient", lambda *a, **k: True)

    async def fake_overview(*args, **kwargs):
        return {"lines": [], "mode": "structured", "reason": "a fact was dropped"}

    monkeypatch.setattr(doctor_route, "get_overview", fake_overview)

    payload = asyncio.run(
        doctor_route.doctor_patient_overview_route("p1", doctor=_doctor("d", "a"))
    )
    assert payload["mode"] == "structured"
    assert payload["reason"]


# ---- verifying a document (shared across the patient's doctors) ----

def _review_request(action="verify", reason=None):
    return doctor_route.DocumentReviewRequest(action=action, reason=reason)


def test_a_doctor_who_may_not_read_a_document_may_not_review_it(monkeypatch):
    called = []
    def refuse(*args, **kwargs):
        raise PermissionError("Patient not found.")
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", refuse)
    monkeypatch.setattr(doctor_route, "record_review", lambda *a, **k: called.append(a))

    with pytest.raises(HTTPException) as caught:
        doctor_route.doctor_patient_document_review_route("p1", "d1", _review_request(), doctor=_doctor("d", "a"))
    assert caught.value.status_code == 404
    assert called == []


def test_a_document_still_processing_cannot_be_reviewed(monkeypatch):
    def processing(*args, **kwargs):
        raise ValueError("This document has not finished processing.")
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", processing)
    with pytest.raises(HTTPException) as caught:
        doctor_route.doctor_patient_document_review_route("p1", "d1", _review_request(), doctor=_doctor("d", "a"))
    assert caught.value.status_code == 409


@pytest.mark.parametrize("error, status", [
    (doctor_route.ReviewConflict("You have not verified this document."), 409),
    (ValueError("Say what is inaccurate, so other doctors know what to check."), 422),
])
def test_review_errors_map_to_their_status(monkeypatch, error, status):
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", lambda *a, **k: None)
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(doctor_route, "record_review", fail)
    with pytest.raises(HTTPException) as caught:
        doctor_route.doctor_patient_document_review_route("p1", "d1", _review_request("withdraw"), doctor=_doctor("d", "a"))
    assert caught.value.status_code == status


def test_a_review_is_recorded_as_the_authenticated_doctor(monkeypatch):
    """No doctor id in the request: the reviewer is always the token's doctor, and the
    state returned is masked for THEIR department."""
    seen = {}
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", lambda *a, **k: None)
    def record(doctor_id, patient_id, document_id, verb, reason, viewer_department=None):
        seen.update(doctor=doctor_id, patient=patient_id, document=document_id, verb=verb,
                    reason=reason, department=viewer_department)
        return {"status": "flagged"}
    monkeypatch.setattr(doctor_route, "record_review", record)
    doctor = {**_doctor("doc-1", "acct-1"), "department": "Cardiology"}

    payload = doctor_route.doctor_patient_document_review_route(
        "p1", "d1", _review_request("flag", "wrong units"), doctor=doctor,
    )
    assert payload == {"document_id": "d1", "review": {"status": "flagged"}}
    assert seen == {"doctor": "doc-1", "patient": "p1", "document": "d1", "verb": "flag",
                    "reason": "wrong units", "department": "Cardiology"}


# ---- the AI nutritionist ----

def test_nutrition_for_an_appointment_that_is_not_yours_is_a_404(monkeypatch):
    import asyncio

    async def refuse(*args, **kwargs):
        raise PermissionError("Appointment not found.")
    monkeypatch.setattr(doctor_route, "guidance_for_appointment", refuse)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(doctor_route.doctor_visit_nutrition_route("b1", doctor=_doctor("d", "a")))
    assert caught.value.status_code == 404


@pytest.mark.parametrize("error, status", [
    (PermissionError("Patient not found."), 404),
    (ValueError("This document has not finished processing."), 409),
])
def test_document_nutrition_uses_the_document_read_gate(monkeypatch, error, status):
    import asyncio

    called = []
    def gate(*args, **kwargs):
        raise error
    async def guidance(*args, **kwargs):
        called.append(args)
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", gate)
    monkeypatch.setattr(doctor_route, "guidance_for_document", guidance)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(doctor_route.doctor_patient_document_nutrition_route("p1", "d1", doctor=_doctor("d", "a")))
    assert caught.value.status_code == status
    assert called == []


# ---- every line of a document accounted for ----

def _clinical_with(monkeypatch, summary, pages):
    monkeypatch.setattr(doctor_route, "assert_doctor_may_read_document", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "record_document_content_read", lambda *a, **k: None)
    monkeypatch.setattr(doctor_route, "findings_for_document", lambda *a, **k: [])
    monkeypatch.setattr(doctor_route, "review_states", lambda ids, *a, **k: {i: None for i in ids})
    monkeypatch.setattr(doctor_route, "get_summary", lambda *a, **k: summary)
    monkeypatch.setattr(doctor_route, "get_document_pages", lambda *a, **k: pages)
    return doctor_route.doctor_patient_document_clinical_route("p1", "d1", doctor=_doctor("d", "a"))


PAGES = [{"page_no": 1, "text": "Rajasthan Hospital\n- Tab Gabantin - NT 400/100 BD x 15 days\nPhysiotherapy"}]


def test_lines_the_summary_left_out_are_returned_as_written(monkeypatch):
    payload = _clinical_with(monkeypatch, {
        "sentences": [{"text": "Gabantin-NT 400/100 BD for 15 days.", "quote": "- Tab Gabantin - NT 400/100 BD x 15 days"}],
        "not_clinical": ["Rajasthan Hospital"], "prompt_version": "doc-summary-v5-every-item",
    }, PAGES)
    assert payload["coverage"] == {
        "uncovered": [{"page_no": 1, "text": "Physiotherapy"}],
        "not_clinical": ["Rajasthan Hospital"],
        "structural": [],
    }
    assert "not_clinical" not in payload["summary"]


def test_a_summary_from_before_line_accounting_gets_none(monkeypatch):
    """It set nothing aside, so every letterhead line would look like a miss."""
    payload = _clinical_with(monkeypatch, {
        "sentences": [], "not_clinical": [], "prompt_version": "doc-summary-v3-every-abnormal",
    }, PAGES)
    assert payload["coverage"] is None
