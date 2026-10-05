import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from psycopg2 import DataError

from app.api.dependencies import bearer_scheme, get_current_doctor
from app.db.connection import connect_db
from app.services.appointments import (
    doctor_appointments, doctor_patient_detail, doctor_patients, doctor_treats_patient,
)
from app.services.blob_storage import sanitize_filename
from app.services.consults import list_latest_consult_status_by_booking
from app.services.document_catalog import (
    assert_doctor_may_read_document,
    get_document_pages, get_document_summary_for_doctor, list_documents_for_doctor,
    read_document_file_for_doctor, record_document_content_read,
)
from app.services.bulk_draft import draft_all_missing_notes
from app.services.doctor_workspace import (
    explain_item_status, group_into_lanes, lane_for_item, rank_pending_items,
)
from app.services.doctor_ai_activity import (
    ACTIVITY_ITEMS_DEFAULT_LIMIT, ACTIVITY_ITEMS_MAX_LIMIT, ACTIVITY_LOG_DEFAULT_LIMIT,
    ACTIVITY_LOG_MAX_LIMIT, ACTIVITY_TILES, ACTIVITY_WINDOWS, DEFAULT_WINDOW,
    get_activity_items, get_activity_log, get_activity_summary,
)
from app.services.booking_context import get_snapshot_for_doctor
from app.services.document_findings import (
    FLAG_SOURCE_REPORT_FLAG, count_report_flags, findings_for_document, locate_printed_result,
    trend_for, trendable_measurements,
)
from app.services.document_grounding import (
    LEGACY_SUMMARY_VERSIONS, accepted_set_aside, get_summary, structural_lines, uncovered_lines,
)
from app.services.document_reviews import ReviewConflict, record_review, review_states
from app.services.nutrition import (
    guidance_for_appointment, guidance_for_document, nutrition_focus_for_appointment,
    nutrition_focus_for_document,
)
from app.services.patient_timeline import (
    TIMELINE_DEFAULT_LIMIT, TIMELINE_MAX_LIMIT, get_patient_timeline, get_timeline_filters,
)
from app.services.login_lockout import AccountLockedError
from app.services.visit_brief import get_visit_brief
from app.services.patient_overview import get_overview, mark_new_since
from app.services.overview_documents import apply_review_labels, document_blocks
from app.services.doctor_auth import (
    authenticate_doctor_password, check_rate_limit, complete_invite, complete_mfa_challenge,
    issue_invite, start_mfa_enrollment, verify_mfa_enrollment,
)
from app.services.soap_notes import (
    REVIEW_DEFAULT_LIMIT, REVIEW_MAX_LIMIT, REVIEW_SCOPES, list_reviews_for_doctor,
)
from app.services.tokens import (
    create_doctor_mfa_enrollment_token, create_doctor_mfa_pending_token,
    create_doctor_session_token, verify_access_token,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class InviteRequest(BaseModel):
    email: str


class ResetInviteRequest(InviteRequest):
    confirm_reset: bool


class CompleteInviteRequest(BaseModel):
    token: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class DocumentReviewRequest(BaseModel):
    # verify | withdraw | flag | clear_flag — validated by document_reviews.record_review.
    action: str
    reason: str | None = None


class MfaCodeRequest(BaseModel):
    code: str


def _error(exc: Exception, status: int = 400):
    raise HTTPException(status_code=status, detail=str(exc))


def _mfa_token(credentials: HTTPAuthorizationCredentials | None, kind: str) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="MFA authentication token is required.")
    payload = verify_access_token(credentials.credentials)
    if not payload or payload.get("role") != "doctor" or payload.get("token_kind") != kind:
        raise HTTPException(status_code=401, detail="Invalid MFA authentication token.")
    return payload


@router.post("/auth/complete-invite")
def complete_invite_route(request: CompleteInviteRequest):
    try:
        account = complete_invite(request.token, request.password)
    except PermissionError as exc:
        _error(exc, 400)
    except ValueError as exc:
        _error(exc, 400)
    if account["mfa_enabled"]:
        return {"status": "password_reset"}
    token = create_doctor_mfa_enrollment_token(
        doctor_id=account["doctor_id"], account_id=account["account_id"], email=account["email"]
    )
    return {"status": "password_set", "mfa_enrollment_token": token, "token_type": "bearer"}


@router.post("/auth/mfa/enroll")
def mfa_enroll(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    payload = _mfa_token(credentials, "doctor_mfa_enrollment")
    try:
        uri = start_mfa_enrollment(str(payload["account_id"]))
    except (PermissionError, ValueError, RuntimeError) as exc:
        _error(exc, 400)
    return {"provisioning_uri": uri}


@router.post("/auth/mfa/verify")
def mfa_verify(request: MfaCodeRequest, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    payload = _mfa_token(credentials, "doctor_mfa_enrollment")
    try:
        recovery_codes = verify_mfa_enrollment(str(payload["account_id"]), request.code)
    except PermissionError as exc:
        _error(exc, 400)
    return {"status": "mfa_enabled", "recovery_codes": recovery_codes}


@router.post("/auth/login")
def doctor_login(request: LoginRequest, http_request: Request):
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("login", ip, request.email.strip().lower())
        account_id, doctor_id, email = authenticate_doctor_password(request.email, request.password)
    except AccountLockedError as exc:
        # Ahead of the PermissionError branch below, which AccountLockedError subclasses.
        minutes = max(1, round(exc.retry_after_seconds / 60))
        raise HTTPException(
            status_code=423,
            detail={
                "message": f"Too many failed attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
                "retry_after_seconds": exc.retry_after_seconds,
            },
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )
    except PermissionError as exc:
        if str(exc).startswith("Too many"):
            raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "300"})
        _error(exc, 401)
    token = create_doctor_mfa_pending_token(account_id=account_id, doctor_id=doctor_id, email=email)
    return {"status": "mfa_required", "mfa_token": token, "token_type": "bearer"}


@router.post("/auth/mfa/challenge")
def mfa_challenge(request: MfaCodeRequest, http_request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    payload = _mfa_token(credentials, "doctor_mfa_pending")
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        check_rate_limit("mfa", ip, str(payload["account_id"]))
        doctor_id, email, account_id, recovery_used = complete_mfa_challenge(str(payload["account_id"]), request.code)
    except PermissionError as exc:
        if str(exc).startswith("Too many"):
            raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "300"})
        _error(exc, 401)
    token = create_doctor_session_token(doctor_id=doctor_id, account_id=account_id, email=email)
    return {"status": "authenticated", "access_token": token, "token_type": "bearer", "recovery_code_used": recovery_used}


@router.get("/me")
def doctor_me(doctor: dict = Depends(get_current_doctor)):
    return {"status": "authenticated", "doctor": doctor}


@router.get("/appointments")
def doctor_appointments_route(
    scope: str = Query(...),
    doctor: dict = Depends(get_current_doctor),
):
    normalized_scope = scope.strip().lower()
    if normalized_scope not in ("upcoming", "past"):
        raise HTTPException(status_code=400, detail="scope must be 'upcoming' or 'past'.")

    appointments = doctor_appointments(doctor["doctor_id"], normalized_scope)
    consult_by_booking = list_latest_consult_status_by_booking(
        doctor["doctor_id"], [appt["booking_id"] for appt in appointments]
    )
    for appt in appointments:
        consult = consult_by_booking.get(appt["booking_id"])
        appt["consult_id"] = consult["id"] if consult else None
        appt["consult_status"] = consult["status"] if consult else None
        appt["consult_started_at"] = consult["started_at"] if consult else None
        appt["consult_ended_at"] = consult["ended_at"] if consult else None
    return {"appointments": appointments}


@router.get("/reviews")
def doctor_reviews_route(
    scope: str = Query("pending"),
    limit: int = Query(REVIEW_DEFAULT_LIMIT, ge=1, le=REVIEW_MAX_LIMIT),
    doctor: dict = Depends(get_current_doctor),
):
    """The authenticated doctor's own AI-note review queue. There is deliberately no
    doctor_id parameter: the queue is always the caller's own, taken from their JWT, and
    list_reviews_for_doctor scopes every row by it inside the SQL."""
    normalized_scope = scope.strip().lower()
    if normalized_scope not in REVIEW_SCOPES:
        raise HTTPException(status_code=400, detail="scope must be 'pending' or 'completed'.")

    payload = list_reviews_for_doctor(doctor["doctor_id"], normalized_scope, limit)

    # Triage view, added here rather than inside list_reviews_for_doctor so that function's
    # existing contract (and the order of `reviews`) is untouched. Computed server-side so
    # the ranking rules live in exactly ONE place — doctor_workspace.rank_pending_items,
    # which is unit-tested — instead of being reimplemented in the browser where they could
    # silently drift.
    #
    # Only for the pending scope: `completed` is a history list, and ranking or lane-ing
    # already-signed work would imply outstanding triage that does not exist.
    if normalized_scope == "pending":
        reviews = payload.get("reviews") or []
        for review in reviews:
            review["lane"] = lane_for_item(review)
            review["ai_explanation"] = explain_item_status(review)
        payload["ranked_consultation_ids"] = [
            item["consultation_id"] for item in rank_pending_items(reviews)
        ]
        payload["lanes"] = {
            lane: [item["consultation_id"] for item in items]
            for lane, items in group_into_lanes(reviews).items()
        }

    return payload


# ---- AI workspace read models ----
#
# Same discipline as /reviews above: there is deliberately no doctor_id parameter on any
# of these. The doctor is always the caller, taken from their JWT, and every query is
# scoped by it inside the SQL.

@router.get("/ai/activity-summary")
def doctor_ai_activity_summary_route(
    # Annotated rather than `= Query(DEFAULT_WINDOW)` so the Python default is the string
    # itself. With the Query object as the default, calling this function directly — which
    # is how the route tests drive it — hands the body a Query instance instead of a
    # window, and the validation below fails on it rather than on a real value.
    window: Annotated[str, Query()] = DEFAULT_WINDOW,
    doctor: dict = Depends(get_current_doctor),
):
    """What AI did for this doctor over `window`. Counts only; no clinical content.

    Rejects an unknown window rather than defaulting, so a bad value can never silently
    change what these figures count — same discipline as the `scope` parameters above.
    """
    normalized_window = window.strip().lower()
    if normalized_window not in ACTIVITY_WINDOWS:
        raise HTTPException(
            status_code=400, detail=f"window must be one of {', '.join(ACTIVITY_WINDOWS)}."
        )
    return get_activity_summary(doctor["doctor_id"], doctor["account_id"], normalized_window)


@router.get("/ai/activity-items")
def doctor_ai_activity_items_route(
    tile: Annotated[str, Query()],
    window: Annotated[str, Query()] = DEFAULT_WINDOW,
    limit: int = Query(ACTIVITY_ITEMS_DEFAULT_LIMIT, ge=1, le=ACTIVITY_ITEMS_MAX_LIMIT),
    doctor: dict = Depends(get_current_doctor),
):
    """The rows behind one activity tile, built from the same predicate as its count.

    Both parameters are rejected rather than defaulted when unknown, for the same reason
    as the summary: a typo must not quietly show a different list under the tile's label.
    """
    normalized_window = window.strip().lower()
    normalized_tile = tile.strip().lower()
    if normalized_window not in ACTIVITY_WINDOWS:
        raise HTTPException(
            status_code=400, detail=f"window must be one of {', '.join(ACTIVITY_WINDOWS)}."
        )
    if normalized_tile not in ACTIVITY_TILES:
        raise HTTPException(
            status_code=400, detail=f"tile must be one of {', '.join(ACTIVITY_TILES)}."
        )
    result = get_activity_items(
        doctor["doctor_id"], doctor["account_id"], normalized_window, normalized_tile, limit
    )
    if normalized_tile == "documents_summarized":
        # Who has verified or reported each summary, as on the documents list.
        states = review_states(
            [item["document_id"] for item in result.get("items", [])],
            doctor["doctor_id"], doctor.get("department"),
        )
        for item in result.get("items", []):
            item["review"] = states.get(item["document_id"])
    return result


@router.get("/ai/activity-log")
def doctor_ai_activity_log_route(
    limit: int = Query(ACTIVITY_LOG_DEFAULT_LIMIT, ge=1, le=ACTIVITY_LOG_MAX_LIMIT),
    doctor: dict = Depends(get_current_doctor),
):
    """This doctor's own AI/clinical action feed, newest first."""
    return get_activity_log(doctor["doctor_id"], limit)


@router.get("/ai/document-actions")
def doctor_document_actions_route(doctor: dict = Depends(get_current_doctor)):
    """Document work for "Your next actions": reports a colleague flagged, new abnormal
    results for patients seen soon, and their recent documents no doctor has verified.
    Scoped to this doctor's own appointments; reviewers are shown as this doctor may see them.
    """
    from app.services.doctor_next_actions import document_actions

    return document_actions(doctor["doctor_id"], doctor.get("department"))


@router.post("/reviews/draft-all")
async def doctor_draft_all_missing_notes_route(
    http_request: Request,
    style: str = Query("concise"),
    doctor: dict = Depends(get_current_doctor),
):
    """Drafts notes for this doctor's undrafted consults, in one bounded, idempotent batch.

    Idempotent by construction (it only ever selects consults with no note at all), so a
    double-click or a retry after a dropped connection cannot double-draft or overwrite
    in-progress work. Rate limited per doctor — each item is an LLM call.
    """
    normalized_style = style.strip().lower()
    if normalized_style not in ("concise", "detailed"):
        raise HTTPException(status_code=400, detail="style must be 'concise' or 'detailed'.")

    ip = http_request.client.host if http_request.client else "unknown"
    try:
        return await draft_all_missing_notes(doctor["doctor_id"], ip, normalized_style)
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "300"})


@router.get("/patients")
def doctor_patients_route(doctor: dict = Depends(get_current_doctor)):
    return {"patients": doctor_patients(doctor["doctor_id"])}


@router.get("/patients/{patient_id}")
def doctor_patient_detail_route(patient_id: str, doctor: dict = Depends(get_current_doctor)):
    detail = doctor_patient_detail(doctor["doctor_id"], patient_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return detail


@router.get("/appointments/{booking_id}/brief")
def doctor_visit_brief_route(booking_id: str, doctor: dict = Depends(get_current_doctor)):
    """What this doctor needs for THIS appointment: why the patient booked, the documents
    brought to it, and this doctor's previous visits with the patient. See
    app/services/visit_brief.py.

    Replaces /patients/{id}/ai-brief, which summarised the whole patient a second time
    beside the at-a-glance card, from unverified document text read one blob at a time.

    The viewing doctor's department comes from the token and decides whether a sensitive
    specialty's note content is shown — a client-supplied one would be a way round that.
    """
    try:
        brief = get_visit_brief(doctor["doctor_id"], booking_id, doctor.get("department"))
    except PermissionError:
        # 404 not 403 — the same non-disclosure rule as the booking context below.
        raise HTTPException(status_code=404, detail="Appointment not found.")
    # What the food guidance below is for — named in its heading before it is opened, by the
    # same selection that writes it (nutrition.guidance_items). Code only, no model.
    try:
        brief["nutrition_focus"] = nutrition_focus_for_appointment(doctor["doctor_id"], booking_id)
    except Exception as exc:  # a heading must never cost the doctor the brief
        logger.error("brief: nutrition focus failed for %s: %s", booking_id, exc)
        brief["nutrition_focus"] = []
    return brief


@router.get("/appointments/{booking_id}/nutrition")
async def doctor_visit_nutrition_route(booking_id: str, doctor: dict = Depends(get_current_doctor)):
    """The AI nutritionist for this appointment: food guidance, vegetarian and non-
    vegetarian, for the flagged results in the documents brought to this appointment and to
    this doctor's earlier ones with the patient, and the diet-relevant symptoms in those
    bookings' notes and chats. See app/services/nutrition.py.

    Loaded separately from the brief, so the brief stays a fast, model-free read; guidance
    for a result nobody has had before is generated here, once, and then reused.
    """
    try:
        guidance = await guidance_for_appointment(doctor["doctor_id"], booking_id)
    except PermissionError:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    return _with_nutrition_plan(guidance, doctor, guidance["patient_id"])


def _with_nutrition_plan(guidance: dict, doctor: dict, patient_id: str) -> dict:
    """The checked guidance, organised into themes, foods that help most, a sample day and
    which themes were discussed (app/services/nutrition_plan.py). Code only, no model."""
    from app.services.nutrition_plan import discussions_for, organize, shared_handouts

    discussions = discussions_for(patient_id, doctor["doctor_id"], doctor.get("department"))
    return {**guidance, "patient_id": patient_id, "plan": organize(guidance, discussions),
            "shared_handouts": shared_handouts(patient_id, doctor["doctor_id"])}


class NutritionDiscussedRequest(BaseModel):
    theme: str = Field(..., max_length=40)
    discussed: bool = True
    booking_id: str | None = Field(None, max_length=64)


class NutritionHandoutRequest(BaseModel):
    diet: str = Field("veg", max_length=10)
    # Accepted for older pages; the handout always covers every theme on the page.
    themes: list[str] = Field(default_factory=list, max_length=20)
    booking_id: str | None = Field(None, max_length=64)
    # From the document viewer's nutritionist, which has no booking.
    document_id: str | None = Field(None, max_length=128)
    # Whose dishes the day is made of: "all" (a mix), or north, south, east, west.
    region: str = Field("all", max_length=10)


def _assert_nutrition_access(doctor_id: str, patient_id: str, booking_id: str | None) -> str | None:
    """A doctor treating the patient; a booking, when named, must be theirs with this patient.
    Returns the booking id to record, or raises 404 — the same answer for every refusal."""
    from app.services.visit_brief import _uuid_or_none

    if not doctor_treats_patient(doctor_id, patient_id):
        raise HTTPException(status_code=404, detail="Patient not found.")
    if not booking_id:
        return None
    safe_booking = _uuid_or_none(booking_id)
    if not safe_booking:
        raise HTTPException(status_code=404, detail="Patient not found.")
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM appointment_bookings WHERE booking_id = %s AND doctor_id = %s AND patient_id = %s",
                (safe_booking, doctor_id, patient_id),
            )
            found = cur.fetchone() is not None
        conn.commit()
    if not found:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return str(safe_booking)


@router.post("/patients/{patient_id}/nutrition/discussed")
def doctor_nutrition_discussed_route(
    patient_id: str, request: NutritionDiscussedRequest, doctor: dict = Depends(get_current_doctor),
):
    """Marks a nutrition theme discussed with the patient, or withdraws this doctor's own mark
    for this visit. Shown at the next visit; audited either way."""
    from app.services.nutrition_plan import discussions_for, mark_discussed

    booking_id = _assert_nutrition_access(doctor["doctor_id"], patient_id, request.booking_id)
    try:
        mark_discussed(doctor["doctor_id"], patient_id, request.theme, booking_id, request.discussed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"discussed": discussions_for(patient_id, doctor["doctor_id"], doctor.get("department"))}


@router.post("/patients/{patient_id}/nutrition/handout")
async def doctor_nutrition_handout_route(
    patient_id: str, request: NutritionHandoutRequest, doctor: dict = Depends(get_current_doctor),
):
    """Shares the patient's food handout to their account (Records › Food suggestions).

    Built here from the same guidance the doctor is looking at (the visit's, or the
    document's). Contains no values, no document names and no doses (nutrition_plan).
    Sharing the same handout again stores nothing new: `already_shared` says so, with when.
    """
    from app.services.nutrition_plan import build_handout, organize, save_handout, shared_handouts

    booking_id = _assert_nutrition_access(doctor["doctor_id"], patient_id, request.booking_id)
    if booking_id:
        try:
            guidance = await guidance_for_appointment(doctor["doctor_id"], booking_id)
        except PermissionError:
            raise HTTPException(status_code=404, detail="Patient not found.")
    elif request.document_id:
        try:
            assert_doctor_may_read_document(doctor["doctor_id"], patient_id, request.document_id)
        except PermissionError:
            raise HTTPException(status_code=404, detail="Patient not found.")
        except ValueError:
            raise HTTPException(status_code=409, detail="This document has not finished processing.")
        guidance = await guidance_for_document(doctor["doctor_id"], patient_id, request.document_id)
    else:
        raise HTTPException(status_code=422, detail="Say which visit or document the handout is for.")
    content = build_handout(organize(guidance), request.diet, request.region)
    if not content["themes"]:
        raise HTTPException(status_code=409, detail="There is no food guidance to hand out.")
    shared = save_handout(doctor["doctor_id"], patient_id, booking_id,
                          None if booking_id else request.document_id, content)
    return {"id": shared["id"], "handout": content, "saved_to_patient_account": True,
            "already_shared": not shared["created"], "shared_at": shared["shared_at"],
            "shared_handouts": shared_handouts(patient_id, doctor["doctor_id"])}


@router.get("/appointments/{booking_id}/context")
def doctor_appointment_context_route(
    booking_id: str, doctor: dict = Depends(get_current_doctor),
):
    """What happened before this visit: the booking conversation's shape, which department
    the assistant suggested versus which the patient chose, and the documents they brought.

    Returns `recorded: false` for an appointment booked before this was captured, rather
    than an empty context — "nothing was recorded" and "the patient said nothing" are
    different facts and must not look the same on a clinical screen.
    """
    try:
        snapshot = get_snapshot_for_doctor(doctor["doctor_id"], booking_id)
    except PermissionError:
        # 404 not 403 — same non-disclosure rule as the document routes below.
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if snapshot is None:
        return {"recorded": False, "context": None}
    return {"recorded": True, "context": snapshot}


# ---- Patient documents ----
#
# Every route below is scoped by a treating relationship (an actual booking history).
# A doctor with no such relationship gets 404 "Patient not found." — never 403 — so these
# endpoints cannot be used to discover which patients or documents exist.

@router.get("/patients/{patient_id}/documents")
def doctor_patient_documents_route(patient_id: str, doctor: dict = Depends(get_current_doctor)):
    try:
        documents = list_documents_for_doctor(doctor["doctor_id"], patient_id)
    except PermissionError:
        raise HTTPException(status_code=404, detail="Patient not found.")
    # Who has verified or reported each one, so the list shows it without opening each.
    states = review_states(
        [doc["document_id"] for doc in documents], doctor["doctor_id"], doctor.get("department"),
    )
    for doc in documents:
        doc["review"] = states.get(doc["document_id"])
    return {"documents": documents}


@router.get("/patients/{patient_id}/documents/{document_id}")
async def doctor_patient_document_summary_route(
    patient_id: str, document_id: str, doctor: dict = Depends(get_current_doctor),
):
    """The AI-extracted summary of one document. This is unreviewed model output — the
    response carries is_ai_generated/clinician_reviewed so the UI can badge it as such."""
    try:
        return await get_document_summary_for_doctor(doctor["doctor_id"], patient_id, document_id)
    except PermissionError:
        raise HTTPException(status_code=404, detail="Patient not found.")
    except ValueError as exc:
        raise HTTPException(
            status_code=409 if "processing" in str(exc).lower() else 404, detail=str(exc)
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="This document's stored summary is no longer available.")
    except RuntimeError as exc:
        # Never echo this one back. A storage-layer RuntimeError carries the internal
        # object path and the raw provider exception (see blob_storage.download_blob_json),
        # which would disclose storage layout and another identifier in an API response.
        logger.error("doctor document summary unavailable (document_id=%s): %s", document_id, exc)
        raise HTTPException(status_code=502, detail="This document could not be read right now.")


@router.get("/patients/{patient_id}/documents/{document_id}/clinical")
def doctor_patient_document_clinical_route(
    patient_id: str, document_id: str, doctor: dict = Depends(get_current_doctor),
):
    """The clinician view of one document: verified summary sentences plus the measurements
    parsed out of it.

    The two come from different pipelines on purpose. The summary is model prose that
    survived quote-and-number verification; the chips are values parsed by code and
    classified against code-owned reference ranges. A doctor reading a sentence sees the
    parsed number beside it, so a plausible-sounding sentence has something independent to
    be checked against.

    `summary` is null when none was ever generated, which is different from a summary whose
    every sentence failed verification — that comes back with verification='failed' and no
    sentences, and the UI says something different for each.
    """
    try:
        assert_doctor_may_read_document(doctor["doctor_id"], patient_id, document_id)
    except PermissionError:
        # Not your patient, no such document, or another patient's document: one answer
        # for all three, so this cannot be used to discover which document ids exist.
        raise HTTPException(status_code=404, detail="Patient not found.")
    except ValueError:
        raise HTTPException(status_code=409, detail="This document has not finished processing.")

    summary = get_summary(document_id)
    if summary:
        # The model name is recorded but never shown to a doctor.
        summary.pop("model", None)
    findings = findings_for_document(document_id)

    # "Nothing missed", made checkable: how many results the REPORT marks with a flag,
    # counted straight from its page text, against how many we list as flagged by it. A
    # result the extractor never read, or one we could not find on its line, makes the
    # first number larger — and the viewer says so instead of showing a short list as
    # complete.
    pages = get_document_pages(document_id)
    completeness = {
        "report_flagged": count_report_flags(pages),
        "listed_from_report": sum(1 for row in findings if row["flag_source"] == FLAG_SOURCE_REPORT_FLAG),
    }

    # Every line of the document accounted for: in a verified sentence, a parsed result, or
    # set aside as non-clinical. Any other line is returned as written, so the viewer shows
    # it instead of letting it disappear (document_grounding.uncovered_lines). Summaries
    # from before the model was asked to account for lines have nothing set aside, so for
    # them every letterhead line would look missed — they get no accounting until re-run.
    coverage = None
    if summary and summary.get("prompt_version") not in LEGACY_SUMMARY_VERSIONS:
        result_lines = []
        for row in findings:
            located = locate_printed_result(row, pages)
            if located:
                result_lines.append(located["line"])
        not_clinical = accepted_set_aside(summary.get("not_clinical"))
        coverage = {
            "uncovered": uncovered_lines(pages, summary.get("sentences") or [], not_clinical, result_lines),
            "not_clinical": not_clinical,
            # Table headings and printed reference bands, recognised by code: shown with the
            # set-aside lines rather than as content the summary missed.
            "structural": [line["text"] for line in structural_lines(pages, result_lines)],
        }
    if summary:
        summary.pop("not_clinical", None)

    # This is document CONTENT — verified summary sentences and parsed results — and every
    # read of content is audited. The viewer moved here from the older summary route, which
    # audited internally; this one did not, so moving the viewer silently stopped recording
    # who read patients' documents. Written after the reads succeed, as the older route does.
    record_document_content_read(doctor["doctor_id"], patient_id, document_id)

    return {
        "document_id": document_id,
        "summary": summary,
        "findings": findings,
        "completeness": completeness,
        "coverage": coverage,
        "review": review_states([document_id], doctor["doctor_id"], doctor.get("department"))[document_id],
        # What this document's food guidance is for, for its heading (no model).
        "nutrition_focus": _document_nutrition_focus(patient_id, document_id),
    }


def _document_nutrition_focus(patient_id: str, document_id: str) -> list[str]:
    try:
        return nutrition_focus_for_document(patient_id, document_id)
    except Exception as exc:  # the heading is a convenience; the document must still open
        logger.error("document: nutrition focus failed for %s: %s", document_id, exc)
        return []


@router.get("/patients/{patient_id}/documents/{document_id}/nutrition")
async def doctor_patient_document_nutrition_route(
    patient_id: str, document_id: str, doctor: dict = Depends(get_current_doctor),
):
    """The AI nutritionist for ONE document: food guidance for its flagged results. Same
    gate as reading the document, and nothing for a document reported inaccurate."""
    try:
        assert_doctor_may_read_document(doctor["doctor_id"], patient_id, document_id)
    except PermissionError:
        raise HTTPException(status_code=404, detail="Patient not found.")
    except ValueError:
        raise HTTPException(status_code=409, detail="This document has not finished processing.")
    guidance = await guidance_for_document(doctor["doctor_id"], patient_id, document_id)
    return _with_nutrition_plan(guidance, doctor, patient_id)


@router.post("/patients/{patient_id}/documents/{document_id}/review")
def doctor_patient_document_review_route(
    patient_id: str, document_id: str, request: DocumentReviewRequest,
    doctor: dict = Depends(get_current_doctor),
):
    """Verify, withdraw a verification, report inaccurate, or clear a report — shared with
    every doctor treating this patient. See app/services/document_reviews.py for the rules.

    Same gate as reading the document: a doctor who may not read it may not review it, and
    gets the same 404 either way.
    """
    try:
        assert_doctor_may_read_document(doctor["doctor_id"], patient_id, document_id)
    except PermissionError:
        raise HTTPException(status_code=404, detail="Patient not found.")
    except ValueError:
        raise HTTPException(status_code=409, detail="This document has not finished processing.")

    try:
        review = record_review(
            doctor["doctor_id"], patient_id, document_id, request.action, request.reason,
            viewer_department=doctor.get("department"),
        )
    except ReviewConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"document_id": document_id, "review": review}


@router.get("/patients/{patient_id}/findings/{canonical_name}/trend")
def doctor_patient_finding_trend_route(
    patient_id: str, canonical_name: str, doctor: dict = Depends(get_current_doctor),
):
    """One measurement over time for this patient — computed in SQL, never by a model."""
    if not doctor_treats_patient(doctor["doctor_id"], patient_id):
        # 404 not 403 — the same non-disclosure rule as every other patient route here.
        raise HTTPException(status_code=404, detail="Patient not found.")

    return {
        "canonical_name": canonical_name,
        "points": trend_for(patient_id, canonical_name),
    }


@router.get("/patients/{patient_id}/overview")
async def doctor_patient_overview_route(
    patient_id: str, doctor: dict = Depends(get_current_doctor),
):
    """The at-a-glance card: five to eight lines, each traceable to a source.

    `mode` says which the doctor is reading. "phrased" is model prose that passed
    verification; "structured" is the plain fact list, served whenever the phrasing was
    rejected or could not be produced. The UI must show the difference rather than
    presenting the fallback as though it were the summary.

    The viewing doctor's own department comes from the token and decides what they may
    see — a client-supplied department would be a way to read a restricted specialty by
    claiming to be in it.
    """
    if not doctor_treats_patient(doctor["doctor_id"], patient_id):
        raise HTTPException(status_code=404, detail="Patient not found.")

    overview = await get_overview(doctor["doctor_id"], patient_id, doctor.get("department"))
    # Read on every open, never cached with the card: a document can be verified or
    # reported at any moment, and that is not one of the inputs the card is cached on.
    overview = apply_review_labels(overview, doctor["doctor_id"], doctor.get("department"))
    # "New since your last visit" is this doctor's, so it is marked here, after the cache.
    try:
        overview = mark_new_since(overview, doctor["doctor_id"], patient_id)
    except Exception as exc:  # a missing "New" marker must never cost the doctor the card
        logger.error("overview: new-since marking failed for %s: %s", patient_id, exc)
    try:
        overview["documents"] = document_blocks(doctor["doctor_id"], patient_id, doctor.get("department"))
    except Exception as exc:  # the card must still load if this part cannot be built
        logger.error("overview: document blocks failed for %s: %s", patient_id, exc)
        overview["documents"] = []
    # Every view, cached or not: the audit records who READ the record, and a cache hit is
    # still a read.
    _audit_overview_view(doctor["doctor_id"], patient_id, overview)
    return overview


@router.get("/patients/{patient_id}/timeline")
def doctor_patient_timeline_route(
    patient_id: str,
    department: Annotated[str | None, Query()] = None,
    doctor_id: Annotated[str | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    document_type: Annotated[str | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: int = Query(TIMELINE_DEFAULT_LIMIT, ge=1, le=TIMELINE_MAX_LIMIT),
    doctor: dict = Depends(get_current_doctor),
):
    """Every encounter this patient has had, across all doctors, newest first.

    This is the route that widens what a doctor can see, so it is audited on every call.
    The `doctor_treats_patient` gate is unchanged; past it the whole hospital history is
    visible, with two exceptions enforced in patient_timeline: unsigned drafts are never
    shown to anyone but their author, and note content from a sensitive specialty is
    withheld from doctors outside it while the encounter itself still appears.

    `doctor_id` here filters the timeline BY a doctor. The viewing doctor is always taken
    from the token and can never be supplied by a client.
    """
    if not doctor_treats_patient(doctor["doctor_id"], patient_id):
        raise HTTPException(status_code=404, detail="Patient not found.")

    try:
        timeline = get_patient_timeline(
            doctor["doctor_id"], patient_id, doctor.get("department"),
            department=department, other_doctor_id=doctor_id,
            date_from=date_from, date_to=date_to, document_type=document_type,
            limit=limit, cursor=cursor,
        )
    except (ValueError, DataError) as exc:
        # A malformed date or cursor is the caller's error, not a server fault, and must
        # not surface as a 500 carrying a database message.
        logger.info("timeline rejected a bad filter (patient=%s): %s", patient_id, exc)
        raise HTTPException(status_code=400, detail="One of the filters is not valid.")

    _audit_timeline_view(doctor["doctor_id"], patient_id, len(timeline["encounters"]))
    return timeline


@router.get("/patients/{patient_id}/timeline/filters")
def doctor_patient_timeline_filters_route(
    patient_id: str, doctor: dict = Depends(get_current_doctor),
):
    """Only the departments, doctors and document types this patient actually has."""
    if not doctor_treats_patient(doctor["doctor_id"], patient_id):
        raise HTTPException(status_code=404, detail="Patient not found.")
    return get_timeline_filters(patient_id)


def _audit_patient_view(doctor_id: str, patient_id: str, action: str, **metadata) -> None:
    """Reading another doctor's clinical record is a disclosure, so it is recorded.

    Written to consult_audit_log, this codebase's single clinical audit trail, with the
    same NULL-consultation_id pattern document_catalog uses. Never fails the request: an
    audit write that breaks must not stop a doctor seeing their patient's record, but it
    must be loud in the logs.
    """
    import json as _json

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO consult_audit_log (consultation_id, doctor_id, action_type, metadata)
                       VALUES (NULL, %s, %s, %s::jsonb)""",
                    (doctor_id, action, _json.dumps({"patient_id": patient_id, **metadata})),
                )
            conn.commit()
    except Exception as exc:
        logger.error(
            "could not audit %s doctor=%s patient=%s: %s", action, doctor_id, patient_id, exc
        )


def _audit_timeline_view(doctor_id: str, patient_id: str, count: int) -> None:
    _audit_patient_view(doctor_id, patient_id, "patient_timeline_viewed", encounters=count)


def _audit_overview_view(doctor_id: str, patient_id: str, overview: dict) -> None:
    # The card lists diagnoses from OTHER doctors' signed notes across departments — the
    # same disclosure the timeline audits. It went unrecorded, so a doctor could read a
    # colleague's diagnoses of a patient without any trace, provided they stopped at the
    # summary. What was shown is recorded as a count by kind, never the text itself.
    kinds: dict = {}
    for fact in overview.get("facts") or []:
        kinds[fact.get("kind") or "other"] = kinds.get(fact.get("kind") or "other", 0) + 1
    _audit_patient_view(
        doctor_id, patient_id, "patient_overview_viewed",
        mode=overview.get("mode"), facts=kinds,
    )


@router.get("/patients/{patient_id}/trends")
def doctor_patient_trends_route(patient_id: str, doctor: dict = Depends(get_current_doctor)):
    """Which measurements this patient has an actual history for. Asked once, so the UI
    does not probe per analyte."""
    if not doctor_treats_patient(doctor["doctor_id"], patient_id):
        # 404 not 403 — the same non-disclosure rule as every other patient route here.
        raise HTTPException(status_code=404, detail="Patient not found.")

    return {"trends": trendable_measurements(patient_id)}


@router.get("/patients/{patient_id}/documents/{document_id}/file")
async def doctor_patient_document_file_route(
    patient_id: str, document_id: str, doctor: dict = Depends(get_current_doctor),
):
    """The original uploaded file, always as an attachment.

    Content-Disposition is unconditionally 'attachment' and the content type comes from a
    four-entry allowlist: a stored file the browser renders inline would be stored XSS
    against the doctor's authenticated session on this same origin. The filename is run
    through the same sanitizer used when it was stored, which strips everything outside
    [\\w.-] and so cannot inject a CR/LF into the header.
    """
    try:
        data, filename, content_type = await read_document_file_for_doctor(
            doctor["doctor_id"], patient_id, document_id
        )
    except PermissionError:
        raise HTTPException(status_code=404, detail="Patient not found.")
    except ValueError as exc:
        raise HTTPException(
            status_code=409 if "processing" in str(exc).lower() else 404, detail=str(exc)
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="The original file for this document is no longer available.")
    except RuntimeError as exc:
        # Same disclosure hazard as the summary route above — log it, don't return it.
        logger.error("doctor document download failed (document_id=%s): %s", document_id, exc)
        raise HTTPException(status_code=502, detail="This document could not be read right now.")

    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{sanitize_filename(filename)}"',
            # Belt-and-braces against content sniffing overriding the allowlisted type.
            "X-Content-Type-Options": "nosniff",
        },
    )
