# Doctor workspace — feature inventory (pre-redesign baseline)

Every item below exists today and must still work after the AI redesign. This file is the
regression checklist; `verification-report.md` will carry a pass/fail against each row.

Compiled by reading the source, not by guessing from the UI:

- `app/api/routes/doctor.py`, `app/api/routes/consult.py`
- `app/services/soap_notes.py`, `clinical_items.py`, `appointments.py`, `document_catalog.py`, `consults.py`
- `app/api/static/index.html` (doctor panes, lines 174–560), `app/api/static/app.js` (doctor logic, ~lines 1095–3050)

## How to read the coverage column

- **Covered** — a named automated test asserts this behaviour today.
- **Backend only** — the service/route behaviour is tested; the UI that renders it is not.
- **None** — no automated test asserts this at all.

There is no JavaScript test runner, no browser automation and no accessibility tooling in
this repository (no `package.json`, no Playwright/Selenium/axe). So **no UI behaviour in
this table is covered today**, and none can be without introducing new tooling. That
decision is raised in `plan.md` §7 rather than taken unilaterally.

---

## 1. Sidebar navigation

| # | Feature | Source | Coverage |
|---|---------|--------|----------|
| 1.1 | Overview nav item | `index.html:184` | None (UI) |
| 1.2 | Reviews nav item | `index.html:190` | None (UI) |
| 1.3 | Reviews count badge (`doctorReviewNavCount`) | `index.html:195`, `app.js:1321` `renderDoctorReviewCounts` | Backend only — counts from `list_reviews_for_doctor`, `test_doctor_reviews_integration.py::test_pending_queue_surfaces_all_three_item_types` |
| 1.4 | Upcoming nav item | `index.html:197` | None (UI) |
| 1.5 | Past nav item | `index.html:203` | None (UI) |
| 1.6 | Patients nav item | `index.html:209` | None (UI) |
| 1.7 | Log out | `index.html:218` `doctorLogoutBtn` | None (UI) |

## 2. Overview pane

| # | Feature | Source | Coverage |
|---|---------|--------|----------|
| 2.1 | Today's appointments stat | `index.html:240` `doctorStatToday` | Backend only — `doctor_appointments`, `test_doctor_appointments.py` |
| 2.2 | "Awaiting your review" stat | `index.html:244` `doctorStatReviews` | Backend only — `test_doctor_reviews_integration.py` |
| 2.3 | "Needs attention" stat | `index.html:248` `doctorStatAttention` | Backend only — `counts.stale` + `counts.low_quality_transcript` |
| 2.4 | Today's schedule list | `index.html:256`, `app.js:1508` `renderDoctorTodaySchedule` | Backend only |
| 2.5 | Pending reviews list + "Review all" | `index.html:262`, `app.js:1441` | Backend only |
| 2.6 | Doctor profile grid (name/dept/experience/MFA) | `index.html:265–268` | Backend only — `/doctor/me` |

## 3. Reviews queue

| # | Feature | Source | Coverage |
|---|---------|--------|----------|
| 3.1 | Pending / Signed tabs | `index.html:285–286` | Backend only — `test_doctor_reviews.py::test_reviews_route_rejects_invalid_scope`, `::test_reviews_route_defaults_to_pending` |
| 3.2 | Search by patient name | `index.html:288` `doctorReviewSearchInput` | None — client-side filter only |
| 3.3 | State: AI generated (`draft`) | `soap_notes.py:243–248` | Covered — `test_doctor_reviews.py::test_row_projection_distinguishes_untouched_ai_output_from_doctor_edits` |
| 3.4 | State: Needs regenerating / blocked (`stale`) | `soap_notes.py:266` | Covered — `::test_row_projection_flags_stale_notes` |
| 3.5 | State: No note yet (`not_generated`) | `soap_notes.py:243` | Covered — `::test_row_projection_marks_a_missing_note_as_not_generated` |
| 3.6 | Fields needing checking (`low_confidence_fields`) | `soap_notes.py:222–229` | Covered — `::test_low_confidence_count_*` (3 tests), `::test_row_projection_surfaces_low_confidence_field_count` |
| 3.7 | Lower-quality transcript (`live_fallback`) | `soap_notes.py:268` | Covered — `::test_row_projection_flags_live_fallback_transcripts` |
| 3.8 | Edits in progress (`is_edited`) | `soap_notes.py:267` | Covered — `::test_row_projection_distinguishes_untouched_ai_output_from_doctor_edits` |
| 3.9 | Waiting time (from `appointment_start`) | `soap_notes.py:256` | Covered — `::test_row_projection_serializes_timestamps_as_iso_strings` |
| 3.10 | Queue never leaks note content | `soap_notes.py:250–270` | Covered — `::test_row_projection_does_not_leak_note_content` |
| 3.11 | Queue scoped to the authenticated doctor | `doctor.py:170–183` | Covered — `::test_reviews_route_scopes_to_authenticated_doctor_only`, `test_doctor_reviews_integration.py::test_doctor_cannot_see_another_doctors_reviews` |

## 4. SOAP note

| # | Feature | Source | Coverage |
|---|---------|--------|----------|
| 4.1 | Generate | `consult.py:211`, `soap_notes.py:390` | Covered — `test_soap_notes_integration.py::test_generate_creates_draft_note_with_citations` |
| 4.2 | Regenerate (replaces draft/stale) | `soap_notes.py:439–455` | Covered — `::test_generate_silently_replaces_existing_draft`, `::test_generate_silently_replaces_stale_note` |
| 4.3 | Regenerate blocked once signed | `soap_notes.py:411` | Covered — `::test_generate_rejected_once_signed_and_note_left_untouched` |
| 4.4 | Detail level Concise / Detailed | `index.html:466–470`, `consult_documentation_graph.py` | Covered — `test_clinical_items.py::test_both_style_directives_exist_for_every_declared_style`, `::test_generate_route_rejects_an_unknown_style`, `::test_style_reaches_the_model_prompt` |
| 4.5 | Model / prompt version / generation time on the note | `soap_notes.py:175–176`, `app.js:2265` `renderNoteProvenance` | Covered (backend) — `test_clinical_items.py::test_provenance_reports_the_model_actually_configured`, `::test_prompt_version_is_recorded_with_the_style` |
| 4.6 | Per-field citations "Show citation (n)" | `field_citations` JSONB | Backend only — `::test_generate_creates_draft_note_with_citations` |
| 4.7 | "Needs review" flags | `confidence_flags` JSONB | Backend only |
| 4.8 | Editing + Save changes | `consult.py:241`, `soap_notes.py:486` | Covered — `::test_update_soap_note_edits_fields_while_draft` |
| 4.9 | Edit rejected once signed | `soap_notes.py:512` | Covered — `::test_update_soap_note_rejected_at_service_layer_once_signed` |
| 4.10 | Sign note | `consult.py:254`, `soap_notes.py:540` | Covered — `::test_sign_soap_note_transitions_status_and_sets_signed_by` |
| 4.11 | **Blocked (stale) notes cannot be signed** | `soap_notes.py:557` (`status = 'draft'` only) | Covered — `::test_sign_soap_note_rejected_when_stale` |
| 4.12 | Cannot sign twice | `soap_notes.py:571` | Covered — `::test_sign_soap_note_rejected_when_already_signed` |
| 4.13 | Empty state before a note exists | `index.html:456` `doctorNoteEmptyState` | None (UI) |
| 4.14 | Addenda after signing | `soap_notes.py:705` | Covered — `::test_addendum_rejected_before_signed_and_allowed_after`, `::test_addendum_rejects_empty_content` |
| 4.15 | Cross-doctor isolation on every note op | `consult.py`, `get_consult_owned` | Covered — `::test_doctor_cannot_generate_sign_or_edit_another_doctors_consult` |

## 5. Clinical actions

| # | Feature | Source | Coverage |
|---|---------|--------|----------|
| 5.1 | Prescription / Care plan / Referral tabs | `index.html:531+`, `clinical_items.py:23` | Covered — `test_clinical_items.py::test_valid_kinds_are_accepted`, `::test_invalid_kinds_are_rejected_at_the_route` |
| 5.2 | Save draft | `consult.py:308`, `clinical_items.py:119` | Covered — `test_clinical_items_integration.py::test_the_three_kinds_are_independent_of_one_another` |
| 5.3 | Approve with confirmation step | `index.html` `doctorClinicalItemApproveConfirm`, `consult.py:323` | Backend covered — `test_clinical_items_integration.py::test_approval_is_one_way_and_locks_the_record`; confirmation UI untested |
| 5.4 | **Approved records are read-only and locked** | `clinical_items.py:144`, `175` | Covered — `::test_approval_is_one_way_and_locks_the_record`, `test_clinical_items.py::test_save_route_maps_approved_item_to_conflict`, `::test_there_is_no_unapprove_route` |
| 5.5 | Empty record cannot be approved | `clinical_items.py:177` | Covered — `::test_an_empty_record_cannot_be_approved` |
| 5.6 | "No dose/formulary/interaction checking" notice | `index.html:531+`, `clinical_items.py:1–15` | None (UI) |
| 5.7 | Content length bounded (5000) | `clinical_items.py:30` | Covered — `::test_content_length_is_bounded` |
| 5.8 | Every action writes an audit row | `clinical_items.py:61` | Covered — `::test_every_action_writes_an_audit_row` |
| 5.9 | Cross-doctor isolation | `consult.py:298–334` | Covered — `::test_another_doctor_cannot_read_or_write_this_consults_items`, `test_clinical_items.py::test_routes_scope_to_the_authenticated_doctor` |

## 6. Patient detail

| # | Feature | Source | Coverage |
|---|---------|--------|----------|
| 6.1 | Patient-reported health issues alert, marked unverified | `index.html:341–345` | None (UI) — the "not a verified clinical record" caption is UI-only text |
| 6.2 | Profile fields | `index.html:347`, `doctor_patient_detail` | Backend only — `test_doctor_appointments.py::test_patient_detail_route_rejects_when_no_shared_booking_history` |
| 6.3 | Visit history tab | `index.html:350`, `app.js:2660` | Covered (backend) — `test_doctor_appointments_integration.py::test_shared_patient_detail_shows_only_this_doctors_own_visits` |
| 6.4 | Documents tab | `index.html:351` | Backend only |
| 6.5 | AI document summaries | `doctor.py:214`, `document_catalog.py:419` | Covered — `test_doctor_patient_documents.py::test_document_summary_route_scopes_to_the_authenticated_doctor` + error mappings (404/409/502) |
| 6.6 | Labelled "not reviewed by a clinician" | `index.html:363–367`, `doctor.py:218` | Backend flags covered (`is_ai_generated`/`clinician_reviewed`); UI label untested |
| 6.7 | "Open original" download | `doctor.py:238` | Covered — `::test_file_download_is_always_an_attachment_and_never_sniffable`, `::test_file_download_sanitizes_the_filename_in_the_header` |
| 6.8 | Document list carries no clinical content | `document_catalog.py:381` | Covered — `::test_document_list_payload_carries_no_clinical_content` |
| 6.9 | Treating-relationship authorization (404 not 403) | `doctor.py:199–211` | Covered — `::test_listing_requires_a_treating_relationship`, `::test_document_list_route_maps_no_relationship_to_404_not_403`, `::test_a_document_belonging_to_another_patient_is_unreachable` |

## 7. Signed note and sharing

| # | Feature | Source | Coverage |
|---|---------|--------|----------|
| 7.1 | "Share with patient" confirmation | `index.html:506–512` | Backend covered; confirmation UI untested |
| 7.2 | Sharing cannot be withdrawn | `soap_notes.py:583–597` | Covered — `test_soap_note_sharing.py::test_there_is_no_unshare_route` |
| 7.3 | Shared timestamp | `shared_with_patient_at` | Covered — `test_soap_note_sharing_integration.py::test_sharing_twice_is_idempotent_and_does_not_move_the_timestamp` |
| 7.4 | **Only a signed note can be shared** | `soap_notes.py:611` | Covered — `::test_an_unsigned_note_can_never_be_shared`, `test_soap_note_sharing.py::test_share_route_maps_unsigned_note_to_conflict` |
| 7.5 | Sharing does not alter clinical content | `soap_notes.py:609` | Covered — `::test_sharing_does_not_alter_the_clinical_content` |
| 7.6 | Copy note | `index.html:498` | None (UI) |

## 8. Patient view of a shared note

| # | Feature | Source | Coverage |
|---|---------|--------|----------|
| 8.1 | Plain-language visit summary | `soap_notes.py:655` `list_shared_notes_for_patient` | Covered — `test_soap_note_sharing.py::test_visit_summary_is_attached_to_the_matching_booking` |
| 8.2 | **No citations / flags / transcript / model details** | `soap_notes.py:650–652` `_PATIENT_VISIBLE_NOTE_FIELDS` | Covered — `::test_patient_visible_fields_exclude_clinician_only_signals`, `test_soap_note_sharing_integration.py::test_patient_projection_never_carries_clinician_only_signals` |
| 8.3 | Scoped to the authenticated patient | `soap_notes.py:682–685` | Covered — `::test_visit_summary_lookup_is_scoped_to_the_authenticated_patient`, `::test_sharing_a_signed_note_makes_it_visible_to_that_patient_only` |
| 8.4 | Enrichment is one batched query (no N+1) | `soap_notes.py:655` | Covered — `::test_visit_summary_enrichment_is_one_batched_call_not_one_per_booking` |

## 9. Authentication, roles and permissions

| # | Feature | Source | Coverage |
|---|---------|--------|----------|
| 9.1 | Doctor login (password) | `doctor.py:103` | Covered — `test_doctor_auth.py`, `test_unified_login.py` |
| 9.2 | Mandatory TOTP MFA challenge | `doctor.py:128` | Covered — `test_doctor_auth.py` |
| 9.3 | MFA enrolment + recovery codes | `doctor.py:83`, `93` | Covered — `test_doctor_auth.py`, `test_admin_mfa_reset.py` |
| 9.4 | Invite completion / password set | `doctor.py:67` | Covered — `test_doctor_auth.py` |
| 9.5 | Rate limiting (login / mfa scopes) | `doctor_auth.check_rate_limit` | Covered — `test_rate_limiter.py`, `test_users_lockout_integration.py` |
| 9.6 | Account lockout (423 + Retry-After) | `doctor.py:109–119` | Covered — `test_users_lockout_integration.py` |
| 9.7 | Token revocation / refresh | `tokens.py`, `refresh_tokens.py` | Covered — `test_token_revocation_integration.py`, `test_refresh_tokens.py` |
| 9.8 | `get_current_doctor` guards every doctor route | `dependencies.py` | Covered — `test_appointments_auth_required.py` |
| 9.9 | Doctor identity never taken from the client | `doctor.py:157`, `183`, `188` | Covered — `test_doctor_appointments.py::test_appointments_route_ignores_any_client_supplied_doctor_id`, `::test_patient_detail_route_passes_authenticated_doctor_id_not_a_client_value` |

---

## Baseline test run

Command (see `plan.md` §7 — the standards' `CLAUDE.md` Repository Commands are all `TBD`,
so this was derived from `docker-compose.yml` and `pytest.ini`, and is proposed there as
the value to fill in):

```
DATABASE_URL=postgresql://postgres:<POSTGRES_PASSWORD>@127.0.0.1:5433/hospital_db \
  .venv/Scripts/python.exe -m pytest tests -q
```

`DATABASE_URL` must be overridden because the host's own `:5432` is an unrelated native
Postgres install; the application's database is the container's, published on `5433` by
the gitignored `docker-compose.override.yml`. Without the override every database-backed
test skips silently and a green run means nothing.

**Result — 2026-09-22, before any change:**

```
1 failed, 605 passed, 1 skipped, 1 warning in 187.75s (0:03:07)
FAILED tests/test_multilingual.py::test_global_and_asian_expansion_languages_are_detected
```

The single failure is **pre-existing and environmental, not a defect in scope here**:
`app/services/language.py` needs the 131 MB fastText model at `models/lid.176.bin`, which
is fetched into the container at build time (confirmed present at `/app/models/lid.176.bin`)
and does not exist on the host. The test then falls back to script detection and
mis-detects Spanish as English. It touches nothing in the doctor workspace.

**Everything in this inventory that has backend coverage was green at baseline.**
