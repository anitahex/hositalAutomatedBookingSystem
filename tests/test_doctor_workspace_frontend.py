"""Structural guards on the doctor workspace's front end.

There is no JavaScript test framework in this repository (no package.json, no Node), so
behaviour in app.js is covered by the render harness under docs/ai-redesign/verification/.
What these tests cover instead is a class of defect that harness cannot see: two code
paths that must agree, drifting apart.

THE INCIDENT. Signing in went through loadDoctorDashboard, which loaded appointments, the
review queue AND the AI activity panels. Reloading the page went through bootstrapSession,
which loaded appointments only. So a hard refresh silently dropped the AI activity summary,
the activity feed and the entire review queue — including the sidebar's pending badge —
and the doctor was left looking at a workspace that appeared loaded but was not. Nothing
failed, nothing logged, and both functions read as correct in isolation.

These assert on source text, which is blunt, but the alternative is nothing: the failure
is *an absent call*, so there is no behaviour to observe and no error to catch. The same
technique already guards a two-table routing divergence in test_document_followup.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

APP_JS = Path(__file__).resolve().parents[1] / "app" / "api" / "static" / "app.js"


@pytest.fixture(scope="module")
def app_js() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    """The text of one top-level function, from its declaration to the next one."""
    match = re.search(rf"^(?:async )?function {re.escape(name)}\b", source, re.M)
    assert match, f"{name} no longer exists in app.js"
    rest = source[match.end():]
    end = re.search(r"^(?:async )?function \w+", rest, re.M)
    return rest[: end.start()] if end else rest


# ---- the incident ----

def test_both_ways_into_the_workspace_go_through_one_entry_point(app_js):
    """A fresh login and a page reload must load the same things. They are kept in
    agreement by both calling enterDoctorWorkspace, not by whoever edits one remembering
    to edit the other."""
    for path in ("loadDoctorDashboard", "bootstrapSession"):
        assert "enterDoctorWorkspace(" in _function_body(app_js, path), (
            f"{path} no longer routes through enterDoctorWorkspace — the hard-refresh "
            f"path and the login path can now load different data"
        )


def test_the_entry_point_loads_every_pane_the_overview_shows(app_js):
    """Appointments alone is what a reload used to load. All three must be there, or the
    review queue and the AI panels come back empty on refresh."""
    body = _function_body(app_js, "enterDoctorWorkspace")

    for loader in ("loadDoctorAppointments", "loadDoctorReviews", "loadDoctorAiActivity"):
        assert loader in body, f"enterDoctorWorkspace does not call {loader}"


def test_bootstrap_session_does_not_load_the_workspace_by_hand(app_js):
    """The specific regression: bootstrapSession calling loaders directly is how the two
    paths diverged in the first place."""
    body = _function_body(app_js, "bootstrapSession")

    assert "loadDoctorAppointments(" not in body
    assert "renderDoctorDashboard(" not in body


# ---- the refresh scheduler ----

def test_the_refresh_timer_is_stopped_on_logout(app_js):
    """Otherwise it outlives the session and keeps polling doctor endpoints with a
    cleared token until the tab is closed."""
    assert "stopDoctorRefresh()" in _function_body(app_js, "clearDoctorAuthenticated")


def test_background_refresh_never_runs_over_an_open_work_surface(app_js):
    """The SOAP editor saves on an explicit button press and has no dirty-tracking, so
    re-rendering a note under the doctor would discard whatever they had typed. The guard
    is what makes auto-refresh safe to have at all."""
    body = _function_body(app_js, "canRefreshDoctorViewNow")

    assert "doctorAppointmentDetailPane" in body, "the note editor is not excluded"
    assert "doctorPatientDetailPane" in body, "the patient detail pane is not excluded"
    assert "doctorActiveConsult" in body, "an active consult is not excluded"
    assert "document.hidden" in body, "a hidden tab is not excluded"


@pytest.mark.parametrize(
    "loader",
    ["loadDoctorAiActivity", "loadDoctorReviews", "loadDoctorAppointments", "loadDoctorPatientsList"],
)
def test_every_polled_loader_accepts_background_mode(app_js, loader):
    """A failed background refresh must keep the data already on screen. Without this the
    first lost poll replaces a correct review queue with "could not load"."""
    declaration = re.search(rf"^async function {loader}\(([^)]*)\)", app_js, re.M)
    assert declaration, f"{loader} no longer exists"
    assert "background" in declaration.group(1), f"{loader} cannot be called in background mode"


# ---- model name (issue 3) ----

def test_the_model_name_and_prompt_version_are_never_rendered(app_js):
    """They stay in the database and in the doctor's own API response; they are not put
    on screen. Comments may still name the fields — rendering code may not."""
    code_only = re.sub(r"/\*.*?\*/", "", app_js, flags=re.S)
    code_only = re.sub(r"^\s*//.*$", "", code_only, flags=re.M)

    for field in ("ai_model", "ai_prompt_version"):
        assert field not in code_only, f"{field} is still referenced by rendering code"


# ---- booking context, now the first section of the visit brief ----

def test_no_recorded_context_is_distinguished_from_an_empty_conversation(app_js):
    """On a clinical screen "nothing was recorded" and "the patient said nothing" look
    identical and mean opposite things. An appointment booked before capture existed must
    say the former explicitly, never render as a silent empty section."""
    body = _function_body(app_js, "buildVisitBrief")

    assert "why.recorded" in body, "the render path does not check whether a context exists"
    assert "No booking conversation was recorded" in body


def test_a_failed_brief_request_does_not_claim_nothing_was_recorded(app_js):
    """A request that failed says nothing about the record. Falling back to "nothing was
    recorded" would turn a network error into a false statement about the patient."""
    for loader in ("loadDoctorVisitBrief", "loadDoctorTodayBrief"):
        body = _function_body(app_js, loader)
        assert "No booking conversation was recorded" not in body
        assert "error" in body
    assert "could not be loaded" in _function_body(app_js, "renderDoctorVisitBrief")


def test_the_department_disagreement_is_surfaced_explicitly(app_js):
    """The assistant suggesting one department and the patient choosing another is the
    single most clinically useful thing in this section. It is called out, not left for
    the doctor to notice by comparing two adjacent lines."""
    body = _function_body(app_js, "buildVisitBrief")

    assert "suggested_department" in body and "chosen_department" in body
    assert "why.suggested_department !== why.chosen_department" in body


def test_the_note_provenance_line_survives_without_a_model_name(app_js):
    """This line used to be shown only when the note carried a model name. Removing the
    model name from its text without moving that gate would have deleted the line
    entirely, timestamp and all."""
    body = _function_body(app_js, "renderNoteProvenance")

    assert "generated_at" in body, "the provenance line is no longer gated on generated_at"


# ---- document viewer (patient history, feature 5) ----

def test_the_viewer_never_asks_the_browser_to_render_document_content(app_js):
    """The file route serves Content-Disposition: attachment deliberately — a stored file
    the browser renders inline is stored XSS against the doctor's authenticated session on
    this same origin (document_catalog._content_type_for records that decision).

    The viewer must therefore fetch BYTES and draw them, never point a browsing context at
    document content. An <iframe>, <embed>, <object> or a window.open on the file URL would
    each reintroduce exactly what the attachment header exists to prevent.
    """
    viewer = _function_body(app_js, "openDoctorDocumentViewer")

    assert "response.blob()" in viewer, "the viewer no longer reads the file as bytes"
    for forbidden in ("<iframe", "<embed", "<object", "window.open"):
        assert forbidden not in viewer, f"the viewer renders document content via {forbidden}"


def test_the_viewer_uses_the_authenticated_audited_file_route(app_js):
    """Not a signed storage URL. Every byte read must pass our auth and land in the audit
    log, which a URL handed to the browser would bypass after issue."""
    viewer = _function_body(app_js, "openDoctorDocumentViewer")

    assert "doctorAuthHeaders()" in viewer
    assert "/file" in viewer


def test_closing_the_viewer_releases_the_document(app_js):
    """A patient's record must not sit decoded in memory behind a closed overlay for the
    rest of the session."""
    body = _function_body(app_js, "closeDoctorViewer")

    assert "revokeObjectURL" in body
    assert "destroy" in body


def test_pdfjs_is_loaded_lazily_and_a_failure_is_not_cached(app_js):
    """~1.4 MB that most sessions never need. And a transient load error must not disable
    the viewer for the rest of the session."""
    body = _function_body(app_js, "loadPdfJs")

    assert "pdfjsPromise" in body
    assert "pdfjsPromise = null" in body, "a failed load is cached, disabling the viewer"


def test_brightness_and_contrast_are_display_only(app_js):
    """They exist for X-rays, where useful detail sits outside what a screen shows well.
    Applied as a CSS filter: the stored file is never altered."""
    body = _function_body(app_js, "applyViewerFilter")

    assert "style.filter" in body
    assert "brightness" in body and "contrast" in body


def test_the_viewer_decides_from_the_bytes_not_the_filename(app_js):
    """content_type comes from a four-entry EXTENSION allowlist
    (document_catalog._content_type_for), so a valid JPEG stored without a recognised
    extension arrives as application/octet-stream.

    That fell into the PDF branch and showed the doctor "Invalid PDF structure." about a
    file that is not a PDF and renders perfectly well. Sniffing the magic bytes fixes the
    file rather than the error message.
    """
    body = _function_body(app_js, "sniffDocumentKind")

    assert "0x25" in body, "the %PDF signature is not checked"
    assert "0x89" in body, "the PNG signature is not checked"
    assert "0xFF" in body, "the JPEG signature is not checked"
    # The declared type survives only as a fallback, never as the primary decision.
    assert "declaredType" in body


def test_an_unpreviewable_file_says_so_instead_of_failing_as_a_pdf(app_js):
    viewer = _function_body(app_js, "openDoctorDocumentViewer")

    assert "unsupported" in viewer
    assert "cannot be previewed" in viewer


def test_page_controls_are_hidden_for_a_single_image(app_js):
    """Leaving them live gives the doctor two buttons that silently do nothing."""
    viewer = _function_body(app_js, "openDoctorDocumentViewer")

    assert "doctorViewerPrev" in viewer and "doctorViewerNext" in viewer
    assert "isPdf" in viewer


# ---- activity tile drill-downs ----

def test_the_activity_tiles_are_disclosure_buttons(app_js):
    """A div with a click handler is unreachable by keyboard and announces nothing to a
    screen reader. The tiles must be real buttons that say what they control."""
    body = _function_body(app_js, "renderDoctorActivitySummary")

    assert 'document.createElement("button")' in body
    assert '"aria-controls", "doctorActivityDrill"' in body
    assert '"aria-expanded"' in body
    assert "toggleDoctorActivityDrill(" in body


def test_a_tile_cannot_be_opened_before_its_number_is_real(app_js):
    """A list under an em dash would be the rows behind a figure the doctor never saw."""
    body = _function_body(app_js, "renderDoctorActivitySummary")
    assert "tile.disabled = !summary" in body


def test_the_drill_down_lists_come_from_the_reconciled_endpoint(app_js):
    """The server builds these from the same predicate as the counts
    (test_doctor_activity_items reconciles them). Assembling a list client-side from some
    other endpoint would reopen exactly the disagreement that test closes."""
    body = _function_body(app_js, "loadDoctorActivityDrill")
    assert "/doctor/ai/activity-items" in body


def test_an_open_list_refreshes_with_its_tile(app_js):
    """Otherwise the number moves on the 30s refresh and the list under it does not."""
    body = _function_body(app_js, "loadDoctorAiActivity")
    assert "loadDoctorActivityDrill(" in body


def test_a_late_drill_response_cannot_overwrite_a_newer_one(app_js):
    """Switch tile, or window, while a slow request is in flight: the old answer must not
    paint under the new label."""
    body = _function_body(app_js, "loadDoctorActivityDrill")
    assert "requestId !== doctorActivityDrillRequest" in body


@pytest.mark.parametrize("path", ["clearDoctorAuthenticated", "enterDoctorWorkspace"])
def test_the_drill_down_is_emptied_at_both_session_boundaries(app_js, path):
    """The list carries patient names. On a shared workstation the next doctor to sign in
    must not inherit the previous one's open list — and closing it is not enough, the
    rows would still be in the DOM. Guarded at both ends because not every sign-out path
    runs clearDoctorAuthenticated."""
    assert "resetDoctorActivityDrill(" in _function_body(app_js, path)

    reset = _function_body(app_js, "resetDoctorActivityDrill")
    assert "doctorActivityDrillList?.replaceChildren()" in reset


def test_a_row_that_cannot_be_opened_is_not_a_button(app_js):
    """A discarded consult's note is listed (it was drafted) but there is nowhere to open
    it. A button that does nothing is worse than text that says why."""
    body = _function_body(app_js, "buildDoctorDrillRow")
    assert 'document.createElement(openable ? "button" : "div")' in body


# ---- clinical safety (review phase 1) ----

def test_signing_saves_unsaved_edits_first_and_stops_if_that_fails(app_js):
    """The server signs the last SAVED text. Signing with unsaved edits put a different note
    into the record than the one the doctor had just read and approved."""
    body = _function_body(app_js, "confirmSignSoapNote")
    save_at = body.index("await saveSoapNote()")
    sign_at = body.index("/soap/sign")
    assert save_at < sign_at, "the note is signed before unsaved edits are saved"
    assert "if (doctorNoteDirty)" in body[:save_at]
    between = body[save_at:sign_at]
    assert "if (!saved)" in between and "return;" in between, "a failed save does not stop signing"


def test_save_reports_whether_it_succeeded(app_js):
    body = _function_body(app_js, "saveSoapNote")
    assert "return true;" in body and "return false;" in body


def test_rerendering_the_draft_keeps_unsaved_text(app_js):
    """Mark verified re-renders the draft; it used to rebuild the fields from the last saved
    note, silently reverting whatever the doctor had typed."""
    body = _function_body(app_js, "renderNoteDraft")
    assert "doctorNoteDirty ? { ...note, ...collectNoteFieldValues() } : note" in body


def test_typing_in_the_draft_marks_it_unsaved(app_js):
    body = _function_body(app_js, "buildNoteFieldRow")
    assert 'addEventListener("input", () => { doctorNoteDirty = true; })' in body


@pytest.mark.parametrize("loader", ["loadSoapNote", "generateSoapNote", "saveSoapNote"])
def test_the_unsaved_flag_clears_when_the_fields_come_from_the_server(app_js, loader):
    assert "doctorNoteDirty = false" in _function_body(app_js, loader)


def test_approving_a_clinical_item_stops_when_its_save_fails(app_js):
    """The save used to swallow its own error and approval carried on, locking in the
    server's older text — for a prescription, a different drug list from the one shown."""
    body = _function_body(app_js, "approveClinicalItem")
    save_at = body.index("await saveClinicalItem(")
    approve_at = body.index("/approve")
    between = body[save_at:approve_at]
    assert "if (!saved)" in between and "return;" in between


def test_clinical_item_save_reports_whether_it_succeeded(app_js):
    body = _function_body(app_js, "saveClinicalItem")
    assert "return true;" in body and "return false;" in body


def test_switching_clinical_item_tabs_asks_before_discarding_text(app_js):
    assert "clinicalItemHasUnsavedText()" in _function_body(app_js, "setClinicalItemKind")


@pytest.mark.parametrize("loader,guard,paint", [
    ("loadDoctorOverview", "doctorPatientDetailId !== patientId", "renderDoctorOverview(overview)"),
    ("loadDetailPatientIssues", "doctorDetailAppointment?.patient_id !== patientId",
     "doctorDetailPatientIssues = issues"),
    ("loadDoctorTimelineFilters", "timelineState.patientId !== patientId",
     'fill("#doctorTimelineDepartment", filters'),
])
def test_a_late_response_for_another_patient_is_ignored(app_js, loader, guard, paint):
    """A slow response for the patient the doctor has just left must never render under the
    one they moved to. The overview is the likely case: a card built by the model takes
    seconds, a cached one milliseconds."""
    body = _function_body(app_js, loader)
    request = body.index("await doctorAuthedJson(")
    painted = body.index(paint)
    # The guard must sit BETWEEN the request returning and the result being painted — that
    # is where the race is. Anywhere else (only in the error path, say) guards nothing.
    assert guard in body[request:painted], f"{loader} paints a response without checking whose it is"


def test_the_overview_clears_the_previous_patients_card_before_loading(app_js):
    body = _function_body(app_js, "loadDoctorOverview")
    assert body.index("doctorOverviewLines?.replaceChildren()") < body.index("await doctorAuthedJson(")


def test_phrased_overview_lines_carry_their_facts_labels(app_js):
    """'Patient reports' and 'Reported, unverified' must never be hidden, and prose only
    keeps them if the model wrote them. They are read off the cited facts instead."""
    body = _function_body(app_js, "renderDoctorOverview")
    assert "factsById.get(String(id))" in body
    assert "buildOverviewLabel(label)" in body
    assert "From a scanned document" in body


def test_signing_out_closes_the_viewer_and_starts_the_page_over(app_js):
    """The viewer is outside the dashboard, so a patient's document stayed over the login
    screen; and every screen visited stayed in the DOM for the next person."""
    body = _function_body(app_js, "clearDoctorAuthenticated")
    assert "closeDoctorViewer()" in body
    assert "if (wasInWorkspace) window.location.reload()" in body
    assert "closeDoctorViewer()" in _function_body(app_js, "clearAuthenticated")


def test_leaving_live_work_asks_first(app_js):
    """A sidebar click during a recording ended the consult without a word."""
    guard = "if (!confirmLeavingConsultWork()) return;"
    wiring = app_js[app_js.index("doctorLogoutBtn.addEventListener"):]
    assert wiring.count(guard) >= 1, "log out"
    nav = app_js[app_js.index("doctorViewButtons.forEach((button) => {\n  button.addEventListener"):]
    assert guard in nav[:300], "sidebar"
    back = app_js[app_js.index("doctorAppointmentDetailBackBtn.addEventListener"):]
    assert guard in back[:200], "back"
    assert 'window.addEventListener("beforeunload"' in app_js


def test_the_recording_check_is_the_socket_not_the_timer(app_js):
    """doctorRecordingStartedAtMs outlives the recording, so using it would warn about a
    recording that has already ended."""
    body = _function_body(app_js, "isConsultRecordingLive")
    # Code only: the comment explaining why the timestamp is NOT used names it, and so does
    # the next function's doc comment, which _function_body also captures.
    code = "\n".join(
        line for line in body.splitlines()
        if not line.strip().startswith(("//", "/*", "*"))
    )
    assert "consultSocket" in code
    assert "doctorRecordingStartedAtMs" not in code


# ---- navigation and controls (review phase 2) ----

def test_every_pane_is_switched_from_one_list(app_js):
    """Three functions kept their own list of panes to hide, and two left Reviews out — so
    opening a note from the review queue showed the whole queue above the note."""
    panes = app_js[app_js.index("const DOCTOR_PANES = {"):]
    panes = panes[: panes.index("};")]
    for pane in ("doctorOverviewPane", "doctorReviewsPane", "doctorUpcomingPane", "doctorPastPane",
                 "doctorPatientsPane", "doctorPatientDetailPane", "doctorAppointmentDetailPane"):
        assert pane in panes, f"{pane} is missing from DOCTOR_PANES"
    for caller, key in (("showDoctorView", "showDoctorPane(nextView)"),
                        ("showDoctorAppointmentDetail", 'showDoctorPane("appointmentDetail")'),
                        ("renderDoctorPatientDetail", 'showDoctorPane("patientDetail")')):
        assert key in _function_body(app_js, caller), f"{caller} switches panes by hand"


def test_no_pane_is_shown_or_hidden_by_hand(app_js):
    panes = ("doctorOverviewPane", "doctorReviewsPane", "doctorUpcomingPane", "doctorPastPane",
             "doctorPatientsPane", "doctorPatientDetailPane", "doctorAppointmentDetailPane")
    # Showing or hiding only; reading state (classList.contains) is fine anywhere.
    for pane in panes:
        for sep in (".", "?."):
            for verb in ("add(", "remove(", "toggle("):
                form = f"{pane}{sep}classList.{verb}"
                assert form not in app_js, f"{pane} is toggled outside showDoctorPane"


def test_next_actions_read_the_pending_queue_not_the_reviews_tab(app_js):
    """It read doctorReviewsCache, which holds the SIGNED history whenever Reviews was last
    left on that tab — and then said nothing was waiting."""
    body = _function_body(app_js, "renderDoctorOverviewReviews")
    assert "doctorPendingQueue" in body
    assert "doctorReviewsCache" not in body
    for state in ("Loading your next actions", "could not be loaded", "Nothing is waiting"):
        assert state in body


def test_the_signed_tab_does_not_starve_the_pending_queue(app_js):
    body = _function_body(app_js, "loadDoctorReviews")
    assert "acceptPendingPayload(data)" in body
    assert "loadDoctorPendingQueue(" in body


def test_action_labels_say_what_pressing_them_does(app_js):
    """Every action opens the note. 'Generate' and 'Regenerate' promised something else."""
    body = _function_body(app_js, "reviewPrimaryAction")
    assert 'label: "Generate"' not in body and 'label: "Regenerate"' not in body
    for label in ("Open to regenerate", "Open to draft", "View signed", "Review"):
        assert label in body


def test_the_whole_review_card_opens_the_note(app_js):
    body = _function_body(app_js, "buildReviewCard")
    assert 'card.addEventListener("click", () => openReviewFromQueue(review))' in body


def test_start_ai_review_opens_the_top_item(app_js):
    """It used to do what See all and both stat cards do."""
    wiring = app_js[app_js.index("doctorStartReviewBtn.addEventListener"):][:300]
    assert "doctorPendingQueue[0]" in wiring and "openReviewFromQueue(" in wiring
    assert "doctorStartReviewBtn.disabled = !first" in _function_body(app_js, "renderDoctorStartReviewButton")


def test_the_attention_card_opens_its_lane_and_see_all_resets_the_tab(app_js):
    assert 'openDoctorReviews({ lane: "needs_attention" })' in app_js
    body = _function_body(app_js, "openDoctorReviews")
    assert 'setDoctorReviewScope("pending"' in body


def test_review_tabs_keep_aria_selected_in_step(app_js):
    body = _function_body(app_js, "syncDoctorReviewScopeTabs")
    assert '"aria-selected"' in body


def test_activity_log_rows_open_their_consult_and_full_audit_works(app_js):
    body = _function_body(app_js, "renderDoctorActivityLog")
    assert 'document.createElement(openable ? "button" : "div")' in body
    assert "openReviewFromQueue(event)" in body
    assert "doctorActivityLogExpanded ? events" in body
    assert "doctorActivityLogToggle?.addEventListener(\"click\", toggleDoctorActivityLog)" in app_js


def test_a_failed_activity_log_is_not_reported_as_an_empty_one(app_js):
    body = _function_body(app_js, "loadDoctorActivityLogOnly")
    assert "renderDoctorActivityLog([])" not in body
    assert "{ error: true }" in body


@pytest.mark.parametrize("fn,const", [
    ("generateSoapNote", "DOCTOR_GENERATE_TIMEOUT_MS"),
    ("draftAllMissingNotes", "DOCTOR_DRAFT_ALL_TIMEOUT_MS"),
])
def test_model_backed_calls_outlast_the_default_timeout(app_js, fn, const):
    """Under 15s the browser reported failure while the server carried on drafting."""
    assert f"timeoutMs: {const}" in _function_body(app_js, fn)


def test_a_filter_change_during_a_timeline_load_is_kept(app_js):
    body = _function_body(app_js, "loadDoctorTimeline")
    assert "timelineState.rerun = true" in body
    assert "if (timelineState.rerun)" in body
    # And the previous patient's encounters never paint under the new one.
    request = body.index("await doctorAuthedJson(")
    paint = body.index("buildTimelineEncounter(")
    assert "timelineState.patientId !== patientId" in body[request:paint]


def test_a_new_patient_starts_with_a_clean_timeline(app_js):
    body = _function_body(app_js, "resetDoctorTimelineForPatient")
    assert "#doctorTimelineFrom" in body and "#doctorTimelineTo" in body
    assert "timelineState.rerun = false" in body
    assert "doctorTimelineList?.replaceChildren()" in body


def test_visit_cards_report_what_happened(app_js):
    # The old hard-coded text, as code (a comment may still quote it).
    assert "· No clinical note yet`" not in _function_body(app_js, "renderDoctorPatientDetail")
    assert "describeVisitNote(visit)" in _function_body(app_js, "renderDoctorPatientDetail")


def test_doctor_mfa_errors_are_not_blamed_on_the_password(app_js):
    handler = app_js[app_js.index('doctorMfaForm.addEventListener("submit"'):][:1200]
    assert "Invalid email or password" not in handler
    assert "doctorMfaBackBtn.addEventListener" in app_js


def test_no_control_is_a_clickable_paragraph_or_div(app_js):
    assert "doctorRecoveryLowNotice.addEventListener(\"click\"" not in app_js
    body = _function_body(app_js, "renderDoctorTodaySchedule")
    assert 'const body = document.createElement("button")' in body


def test_insert_from_plan_is_rechecked_when_the_note_changes(app_js):
    """Computed only when the prescription box rendered, so signing left it hidden."""
    assert "updateInsertFromPlanVisibility()" in _function_body(app_js, "renderSoapNote")


# ---- the visit brief (review phase 3) ----

INDEX_HTML = APP_JS.parent / "index.html"


def test_the_patient_page_no_longer_carries_a_second_summary(app_js):
    """The old brief sat stacked above At a glance, summarising the same patient again from
    unverified text. The patient page now has one summary."""
    assert "/ai-brief" not in app_js
    assert "doctorPatientBriefBlock" not in INDEX_HTML.read_text(encoding="utf-8")


def test_the_appointment_opens_with_the_visit_brief(app_js):
    assert "loadDoctorVisitBrief(appt.booking_id)" in _function_body(app_js, "showDoctorAppointmentDetail")


def test_a_late_brief_for_another_appointment_is_ignored(app_js):
    body = _function_body(app_js, "loadDoctorVisitBrief")
    request = body.index("await doctorAuthedJson(")
    paint = body.index("renderDoctorVisitBrief(doctorVisitBriefBody, brief)")
    assert "doctorDetailAppointment?.booking_id !== bookingId" in body[request:paint]


def test_the_today_brief_is_a_disclosure_not_a_page_jump(app_js):
    """It used to open the whole patient page — a summary of the patient, not the visit."""
    body = _function_body(app_js, "renderDoctorTodaySchedule")
    assert "loadDoctorPatientDetail(" not in body
    assert 'briefBtn.setAttribute("aria-expanded"' in body
    assert 'briefBtn.setAttribute("aria-controls", panelId)' in body


def test_redrawing_today_never_refetches_a_brief(app_js):
    """Today redraws on every 30-second refresh, and each brief fetch is an audited read.
    Only opening a brief fetches it; a redraw paints from the session cache."""
    body = _function_body(app_js, "renderDoctorTodaySchedule")
    assert "doctorAuthedJson(" not in body
    assert "loadDoctorTodayBrief(" not in body
    assert "doctorTodayBriefCache.get(" in body
    assert "loadDoctorTodayBrief(bookingId)" in _function_body(app_js, "toggleDoctorTodayBrief")


def test_brief_text_is_never_parsed_as_html(app_js):
    """Every line comes from the record, and the booking note was typed by the patient."""
    for fn in ("buildVisitBrief", "buildBriefRow", "buildBriefSection"):
        assert "innerHTML" not in _function_body(app_js, fn)


def test_a_restricted_note_is_shown_as_restricted(app_js):
    body = _function_body(app_js, "buildVisitBrief")
    assert "note.restricted" in body and "note restricted" in body


# ---- booking-note formatting ----

def test_the_booking_note_is_rendered_not_shown_raw(app_js):
    """It showed '## PRE-APPOINTMENT CLINICAL SUMMARY **Patient:** ...' symbols and all."""
    assert "renderBookingNoteMarkdown(why.booking_note)" in _function_body(app_js, "buildVisitBrief")
    assert "renderBookingNoteMarkdown(encounter.reason)" in _function_body(app_js, "buildTimelineEncounter")


def test_the_booking_note_renderer_never_parses_html(app_js):
    """The note comes from a chat with the patient; markdown-to-innerHTML on that is an
    injection path. Every piece is placed with textContent or a text node."""
    body = _function_body(app_js, "renderBookingNoteMarkdown")
    assert "innerHTML" not in body and "insertAdjacentHTML" not in body
    assert "createTextNode" in body and "textContent" in body


def test_the_summary_is_labelled_as_ai_written(app_js):
    """The pre-appointment summary is written by the booking assistant. Notes stored before
    the prompts said so still carry the old heading; the display labels them correctly."""
    body = _function_body(app_js, "renderBookingNoteMarkdown")
    assert "Pre-Appointment AI Clinical Summary" in body
    from pathlib import Path
    root = APP_JS.parents[3]
    for prompt_file in ("app/agents/checkup_report.py", "app/agents/supervisor.py"):
        text = (root / prompt_file).read_text(encoding="utf-8")
        assert "## PRE-APPOINTMENT AI CLINICAL SUMMARY" in text, prompt_file
        assert "## PRE-APPOINTMENT CLINICAL SUMMARY" not in text, prompt_file


# ---- timeline filters and document-type names ----

def test_timeline_filters_are_fetched_again_when_the_tab_opens(app_js):
    """They load with the patient; when that request failed the dropdowns stayed empty
    until a hard refresh. Opening the tab retries for a patient whose options never loaded."""
    body = _function_body(app_js, "setDoctorPatientTab")
    assert "timelineState.filtersFor !== timelineState.patientId" in body
    assert "loadDoctorTimelineFilters(timelineState.patientId)" in body
    loader = _function_body(app_js, "loadDoctorTimelineFilters")
    # Marked loaded only after the late-answer guard, so another patient's answer never counts.
    assert loader.index("timelineState.patientId !== patientId") < loader.index("timelineState.filtersFor = patientId")
    assert "timelineState.filtersFor = null" in _function_body(app_js, "resetDoctorTimelineForPatient")


def test_document_types_have_readable_names(app_js):
    body = _function_body(app_js, "formatDocumentType")
    for label in ('"MRI Report"', '"Blood Report"', '"X-ray Report"', '"Prescription"', '"CT Report"'):
        assert label in app_js, label
    # A type added later is still title-cased, never shown with underscores.
    assert r"split(/[_\s]+/)" in body


def test_every_shown_document_type_goes_through_the_formatter(app_js):
    """'mri_report' was printed as-is in five places. A line that reads document_type is
    either data (an object key, a filter value) or passes it through formatDocumentType."""
    offenders = [
        line.strip() for line in app_js.splitlines()
        # The field itself, not lists of raw values ("document_types", "unlinked_document_types"),
        # whose labels are formatted where the options are built.
        if re.search(r"\bdocument_type\b", line)
        and "formatDocumentType" not in line
        and not re.match(r"\s*document_type:", line)
    ]
    assert not offenders, offenders
    loader = _function_body(app_js, "loadDoctorTimelineFilters")
    assert 'fill("#doctorTimelineDocType", filters.document_types || [], null, null, formatDocumentType)' in loader
    # The option VALUE stays the raw type the server filters on; only the label is named.
    assert "option.value = valueKey ? value[valueKey] : value;" in loader


# ---- every abnormal result in the document viewer ----

def test_the_viewer_lists_what_the_report_flagged_not_only_our_ranges(app_js):
    """The viewer listed low/high by our 19-analyte table only; a result the lab flagged H
    with no range in code never appeared. A row the report flags counts as flagged."""
    body = _function_body(app_js, "renderDocumentAbnormalResults")
    assert "Boolean(row.report_flag)" in body
    for group in ('"Critical"', '"High"', '"Low"'):
        assert group in body, group
    assert "renderDocumentAbnormalResults(container, findings, payload && payload.completeness)" in \
        _function_body(app_js, "renderDocumentClinical")


def test_a_short_list_is_never_shown_as_complete(app_js):
    body = _function_body(app_js, "renderDocumentAbnormalResults")
    assert "completeness.report_flagged > completeness.listed_from_report" in body
    assert "The report marks" in body


def test_our_standard_range_is_labelled_as_not_on_the_report(app_js):
    body = _function_body(app_js, "describeFindingRange")
    assert 'row.ref_source === "report"' in body
    assert "not printed on this report" in body


def test_abnormal_results_are_never_parsed_as_html(app_js):
    for fn in ("renderDocumentAbnormalResults", "describeFindingRange"):
        body = _function_body(app_js, fn)
        assert not re.search(r"\.innerHTML\s*[+]?=|insertAdjacentHTML", body), fn


# ---- verifying a document ----

def test_the_viewer_no_longer_says_not_reviewed_unconditionally(app_js):
    """It said "AI generated — not reviewed by a clinician" whatever had happened."""
    body = _function_body(app_js, "renderDocumentClinical")
    assert "AI generated — not reviewed by a clinician" not in body
    assert "renderDocumentReview(reviewHost" in body


def test_verifying_posts_to_the_review_route_and_explains_what_it_means(app_js):
    body = _function_body(app_js, "renderDocumentReview")
    assert "/review`" in body and 'method: "POST"' in body
    assert "not a clinical interpretation" in body
    for verb in ('send("verify")', 'send("withdraw")', 'send("clear_flag")', 'send("flag", reason)'):
        assert verb in body, verb


def test_the_buttons_follow_the_doctors_own_position(app_js):
    """Withdraw and Clear are offered only to the doctor who verified or reported."""
    body = _function_body(app_js, "renderDocumentReview")
    assert 'state.mine === "verified"' in body and 'state.mine === "flagged"' in body


def test_a_report_needs_a_reason_before_it_is_sent(app_js):
    body = _function_body(app_js, "renderDocumentReview")
    assert "reason.length < 5" in body


def test_a_late_summary_for_another_document_is_not_shown(app_js):
    """With a Verify button beside it, a stale panel could verify the wrong document."""
    body = _function_body(app_js, "openDoctorDocumentViewer")
    assert "if (viewerState.doc !== doc) return;" in body


def test_every_document_status_uses_the_shared_chip(app_js):
    assert "buildDocumentReviewChip(doc.document_id, doc.review)" in _function_body(app_js, "buildPatientDocumentCard")
    assert "buildDocumentReviewChip(doc.document_id, doc.review)" in _function_body(app_js, "buildVisitBrief")
    assert "refreshDocumentReviewChips(documentId, data.review)" in _function_body(app_js, "renderDocumentReview")


def test_review_text_is_never_parsed_as_html(app_js):
    for fn in ("renderDocumentReview", "describeDocumentReview", "buildDocumentReviewChip", "formatReviewer"):
        assert not re.search(r"\.innerHTML\s*[+]?=|insertAdjacentHTML", _function_body(app_js, fn)), fn


# ---- the AI nutritionist ----

def test_the_nutritionist_loads_only_when_opened(app_js):
    """Guidance for a new result is generated on that request; the brief must not wait on it."""
    body = _function_body(app_js, "buildNutritionSection")
    assert "if (!open || loaded) return;" in body
    assert body.index("addEventListener(\"click\"") < body.index("doctorAuthedJson(url")


def test_the_nutritionist_is_labelled_as_ai_and_not_a_prescription(app_js):
    body = _function_body(app_js, "renderNutritionGuidance")
    assert "AI generated · food suggestions to discuss, not a diet prescription" in body


def test_the_nutritionist_appears_where_there_are_documents(app_js):
    assert "brief.has_documents && brief.booking_id" in _function_body(app_js, "buildVisitBrief")
    clinical = _function_body(app_js, "renderDocumentClinical")
    assert "hasAbnormal" in clinical and "/nutrition`" in clinical


def test_one_diet_choice_applies_to_every_item(app_js):
    body = _function_body(app_js, "renderNutritionGuidance")
    assert 'setAttribute("aria-pressed", String(nutritionDiet === value))' in body
    assert 'nutritionDiet === "veg" ? item.veg_foods : item.non_veg_foods' in body


def test_nutrition_text_is_never_parsed_as_html(app_js):
    for fn in ("buildNutritionSection", "renderNutritionGuidance", "describeNutritionEvidence"):
        assert not re.search(r"\.innerHTML\s*[+]?=|insertAdjacentHTML", _function_body(app_js, fn)), fn


# ---- every line of a document accounted for ----

def test_the_viewer_shows_what_the_summary_left_out(app_js):
    """A prescription summary lost every medication unseen. Lines in no sentence, result or
    set-aside list are now shown word for word."""
    assert "renderDocumentCoverage(container, payload && payload.coverage, summary)" in \
        _function_body(app_js, "renderDocumentClinical")
    body = _function_body(app_js, "renderDocumentCoverage")
    assert "Also in the document — not in the summary" in body
    assert "Set aside as headings or non-clinical" in body
    assert not re.search(r"\.innerHTML\s*[+]?=|insertAdjacentHTML", body)


def test_text_items_are_not_counted_as_unflagged_measurements(app_js):
    """"4 values read, 4 with no reference range" about a prescription's medication list."""
    body = _function_body(app_js, "renderDocumentAbnormalResults")
    assert "row.value_num !== null && row.value_num !== undefined" in body
    assert "if (!measurements.length) return;" in body


# ---- the full timeline's filters narrow each other ----

def test_department_narrows_doctors_and_both_narrow_document_types(app_js):
    body = _function_body(app_js, "narrowTimelineFilters")
    assert "facet.department === department" in body
    assert "facet.doctor_id === doctor" in body
    assert "label: formatDocumentType(type)" in body  # "MRI Report", not "mri_report"
    # Documents with no visit have no department or doctor: offered only while neither is set.
    assert "if (!department && !doctor) (timelineState.unlinkedTypes" in body
    # A choice the narrowing no longer offers falls back to "All", never a silent empty list.
    assert 'select.value = options.some((option) => option.value === keep) ? keep : "";' in body


def test_every_filter_change_narrows_before_it_reloads(app_js):
    wiring = app_js[app_js.index("// ── Timeline controls"):]
    wiring = wiring[: wiring.index("doctorTimelineMore?.addEventListener")]
    assert wiring.count("narrowTimelineFilters();") == 2  # on change, and on Clear
    assert "narrowTimelineFilters();" in _function_body(app_js, "loadDoctorTimelineFilters")


def test_one_patients_visits_never_narrow_anothers_filters(app_js):
    body = _function_body(app_js, "resetDoctorTimelineForPatient")
    assert "timelineState.facets = null;" in body


def test_documents_without_a_visit_are_shown_on_the_timeline(app_js):
    body = _function_body(app_js, "loadDoctorTimeline")
    assert 'item.kind === "document" ? buildTimelineDocument(item) : buildTimelineEncounter(item)' in body
    doc = _function_body(app_js, "buildTimelineDocument")
    assert "not linked to a visit" in doc and "openDoctorDocumentViewer(" in doc
    assert not re.search(r"\.innerHTML\s*[+]?=|insertAdjacentHTML", doc)


# ---- drafting a clinical note is visibly in progress ----

def test_a_note_being_drafted_is_shown_and_cannot_be_started_twice(app_js):
    body = _function_body(app_js, "generateSoapNote")
    assert "if (!doctorActiveConsult || doctorNoteGenerating) return;" in body
    assert body.index("setNoteGenerating(true)") < body.index("await doctorAuthedJson(")
    assert "finally {" in body and "setNoteGenerating(false)" in body
    status = _function_body(app_js, "setNoteGenerating")
    assert "button.disabled = on" in status and "doctorNoteStyleButtons" in status


def test_a_failed_regenerate_says_the_previous_note_is_still_shown(app_js):
    assert "the note below is still the previous version" in _function_body(app_js, "generateSoapNote")


def test_a_note_drafted_for_another_consult_is_not_shown_here(app_js):
    body = _function_body(app_js, "generateSoapNote")
    assert "doctorActiveConsult.id !== consultId" in body


def test_the_generate_button_names_the_length_it_will_draft(app_js):
    label = _function_body(app_js, "updateNoteGenerateLabel")
    assert "Clinical Note (${length})" in label
    assert "updateNoteGenerateLabel();" in _function_body(app_js, "setDoctorNoteStyle")


# ---- a discarded consult leaves nothing of itself on screen ----

def test_a_discarded_consult_does_not_keep_its_id_or_duration_on_screen(app_js):
    """After a discard the old consult's ID and recording duration stayed, reading as if it
    were still this appointment's consult."""
    body = _function_body(app_js, "renderConsultState")
    assert 'doctorConsultIdLabel.textContent = status ? `Consult ID: ${doctorActiveConsult.id}` : "";' in body
    assert 'doctorConsultIdLabel.classList.toggle("hidden", !status);' in body
    assert "if (status && doctorActiveConsult?.started_at && doctorActiveConsult?.ended_at)" in body


def test_a_discard_says_it_happened_without_looking_like_an_error(app_js):
    assert 'setDoctorConsultNotice("Consult discarded. You can start a new one.")' in \
        _function_body(app_js, "confirmDiscardConsult")
