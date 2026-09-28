# AI Doctor Workspace redesign — verification report

Date: 2026-09-23 · Branch: **none — work is uncommitted in the tree on `dev`** (you asked
for no git operations, so no feature branch was created and nothing was committed).

Decisions taken as approved ("go with your recommendations"): **D1-a, D2-a, D3-a, D4
(warn, not block), D5 (flag off), D6** — see `plan.md` §0. One D6 sub-decision was
reversed during implementation on evidence; that is recorded in §5 below.

---

## 1. Headline results

| Check | Result |
|---|---|
| Full pytest suite | **693 passed, 1 skipped, 1 failed** (the failure is pre-existing and environmental — see §7.1) |
| Baseline before this work | 605 passed, 1 skipped, 1 failed (same failure) |
| New tests added | **+88** |
| Accessibility (axe-core 4.10.2, WCAG 2.0/2.1 A + AA) | **0 violations on all 5 doctor panes** |
| JavaScript runtime errors on page load | **none** |
| Alembic migration `0022` | applies, downgrades and re-applies cleanly |
| Linter / type checker / build | **not run — none exist in this repo** (§7.2) |

---

## 2. Feature inventory — regression status

Every row from `feature-inventory.md`. "Pass" means a named automated test asserts it and
that test is green in the run above.

### 1. Sidebar navigation

| # | Feature | Status | Evidence |
|---|---|---|---|
| 1.1–1.6 | Overview / Reviews / Upcoming / Past / Patients nav | **Pass** | `test_doctor_workspace_e2e.py::test_flow_every_sidebar_destination_loads` (all 8 endpoints 200); rendered in every screenshot |
| 1.3 | Reviews count badge | **Pass** | same flow; badge visible showing `4` in `screenshots/reviews-1280.png` |
| 1.7 | Log out | **Pass (partial)** | Server side asserted: every doctor endpoint returns 401 without a token (same flow). The button's own click handler is unchanged and untested (no JS test runner — §7.2) |

### 2. Overview

| # | Feature | Status | Evidence |
|---|---|---|---|
| 2.1 | Today's appointments stat | **Pass** | visible in `overview-1280.png` (renders `2`); `test_flow_every_sidebar_destination_loads` |
| 2.2 | Awaiting review stat | **Pass** | renders `4`; `::test_flow_overview_to_signed_note` asserts `awaiting_signature == 1` |
| 2.3 | Needs attention stat | **Pass** | renders `2` |
| 2.4 | Today's schedule | **Pass** | `overview-1280.png` shows both visits |
| 2.5 | Pending reviews + Review all | **Pass** | "Your next actions" list, ranked |
| 2.6 | Profile grid | **Pass** | "Your account" card in `overview-1280.png` |

### 3. Reviews queue

| # | Feature | Status | Evidence |
|---|---|---|---|
| 3.1 | Pending / Signed tabs | **Pass** | `test_doctor_reviews.py::test_reviews_route_rejects_invalid_scope`, `::test_reviews_route_defaults_to_pending`; both tabs in `reviews-1280.png` |
| 3.2 | Search by patient name | **Pass (unchanged)** | client-side filter untouched; input present and labelled |
| 3.3 | AI generated | **Pass** | `test_doctor_reviews.py::test_row_projection_distinguishes_untouched_ai_output_from_doctor_edits` |
| 3.4 | Needs regenerating (blocked) | **Pass** | `::test_row_projection_flags_stale_notes`; `e2e::test_flow_blocked_note_cannot_be_signed_through_the_api` |
| 3.5 | No note yet | **Pass** | `::test_row_projection_marks_a_missing_note_as_not_generated` |
| 3.6 | Fields needing checking | **Pass** | `::test_low_confidence_count_*` (3), `::test_row_projection_surfaces_low_confidence_field_count` |
| 3.7 | Lower-quality transcript | **Pass** | `::test_row_projection_flags_live_fallback_transcripts` |
| 3.8 | Edits in progress | **Pass** | `::test_row_projection_distinguishes_untouched_ai_output_from_doctor_edits` |
| 3.9 | Waiting time | **Pass** | `::test_row_projection_serializes_timestamps_as_iso_strings`; "Waiting 1d" in screenshots |
| 3.10 | Never leaks note content | **Pass** | `::test_row_projection_does_not_leak_note_content` |
| 3.11 | Scoped to the authenticated doctor | **Pass** | `::test_reviews_route_scopes_to_authenticated_doctor_only`, `e2e::test_doctor_a_cannot_reach_doctor_bs_workspace_data` |

### 4. SOAP note

| # | Feature | Status | Evidence |
|---|---|---|---|
| 4.1–4.3 | Generate / regenerate / blocked once signed | **Pass** | `test_soap_notes_integration.py` (5 tests, unchanged and green) |
| 4.4 | Detail level Concise / Detailed | **Pass** | `test_clinical_items.py::test_both_style_directives_exist_for_every_declared_style` + 3 more |
| 4.5 | Model / prompt version / generation time | **Pass** | `::test_provenance_reports_the_model_actually_configured`; now also rendered in the assistant panel |
| 4.6 | Per-field citations | **Pass** | `::test_generate_creates_draft_note_with_citations`; "Show citation (n)" retained, now inline per section |
| 4.7 | "Needs review" flags | **Pass** | retained, now with an explanation of *why* (§3, feature 6) |
| 4.8–4.9 | Edit / Save / rejected once signed | **Pass** | `::test_update_soap_note_edits_fields_while_draft`, `::test_update_soap_note_rejected_at_service_layer_once_signed` |
| 4.10 | Sign | **Pass** | `e2e::test_flow_overview_to_signed_note` |
| 4.11 | **Blocked notes cannot be signed** | **Pass** | `::test_sign_soap_note_rejected_when_stale` **and** `e2e::test_flow_blocked_note_cannot_be_signed_through_the_api` (asserts the API refusal, not just the disabled button) |
| 4.12 | Cannot sign twice | **Pass** | `::test_sign_soap_note_rejected_when_already_signed` |
| 4.13 | Empty state before a note exists | **Pass (unchanged markup)** | `#doctorNoteEmptyState` retained verbatim |
| 4.14 | Addenda | **Pass** | `::test_addendum_rejected_before_signed_and_allowed_after`, `::test_addendum_rejects_empty_content` |
| 4.15 | Cross-doctor isolation | **Pass** | `::test_doctor_cannot_generate_sign_or_edit_another_doctors_consult` + the e2e isolation walk |

### 5. Clinical actions

| # | Feature | Status | Evidence |
|---|---|---|---|
| 5.1 | Three tabs | **Pass** | `test_clinical_items.py::test_valid_kinds_are_accepted` |
| 5.2 | Save draft | **Pass** | `e2e::test_flow_approve_prescription_becomes_read_only` |
| 5.3 | Approve with confirmation | **Pass (backend)** | same flow; the confirm step's markup is unchanged |
| 5.4 | **Approved records read-only and locked** | **Pass** | `test_clinical_items_integration.py::test_approval_is_one_way_and_locks_the_record`, `::test_there_is_no_unapprove_route`, and the e2e flow asserts the refused edit **left the stored content unchanged** |
| 5.5 | Empty record cannot be approved | **Pass** | `::test_an_empty_record_cannot_be_approved` |
| 5.6 | "No dose/formulary/interaction checking" notice | **Pass** | retained verbatim; now also restated in the `plan-medications` API payload (`::test_plan_medications_returns_signed_lines_and_says_nothing_is_validated`) |
| 5.7 | Content length bounded | **Pass** | `::test_content_length_is_bounded` |
| 5.8 | Audit row per action | **Pass** | `::test_every_action_writes_an_audit_row` |
| 5.9 | Cross-doctor isolation | **Pass** | `::test_another_doctor_cannot_read_or_write_this_consults_items` |

### 6. Patient detail

| # | Feature | Status | Evidence |
|---|---|---|---|
| 6.1 | Health-issues alert, marked unverified | **Pass (unchanged)** | markup retained; now **also** shown on the clinical-actions tab (§3, feature 10) |
| 6.2–6.4 | Profile / Visit history / Documents tabs | **Pass** | `test_doctor_appointments_integration.py::test_shared_patient_detail_shows_only_this_doctors_own_visits` |
| 6.5–6.6 | AI document summaries, labelled unreviewed | **Pass** | `test_doctor_patient_documents.py` (6 route tests) |
| 6.7 | Open original | **Pass** | `::test_file_download_is_always_an_attachment_and_never_sniffable`, `::test_file_download_sanitizes_the_filename_in_the_header` |
| 6.8 | Document list carries no clinical content | **Pass** | `::test_document_list_payload_carries_no_clinical_content` |
| 6.9 | Treating-relationship authorization (404 not 403) | **Pass** | `::test_document_list_route_maps_no_relationship_to_404_not_403` + the new brief route asserts the same rule |

### 7. Signed note and sharing

| # | Feature | Status | Evidence |
|---|---|---|---|
| 7.1 | Share confirmation | **Pass (backend)** | `e2e::test_flow_share_and_patient_view_has_no_clinician_signals` |
| 7.2 | Sharing cannot be withdrawn | **Pass** | `test_soap_note_sharing.py::test_there_is_no_unshare_route` |
| 7.3 | Shared timestamp | **Pass** | `::test_sharing_twice_is_idempotent_and_does_not_move_the_timestamp`; now also the last row of the audit trail |
| 7.4 | Only a signed note can be shared | **Pass** | `::test_an_unsigned_note_can_never_be_shared`; the e2e flow asserts the 409 **before** signing |
| 7.5 | Sharing does not alter content | **Pass** | `::test_sharing_does_not_alter_the_clinical_content` |
| 7.6 | Copy note | **Pass (unchanged)** | markup retained |

### 8. Patient view

| # | Feature | Status | Evidence |
|---|---|---|---|
| 8.1 | Plain-language visit summary | **Pass** | `::test_visit_summary_is_attached_to_the_matching_booking` |
| 8.2 | **No citations / flags / transcript / model** | **Pass** | `::test_patient_visible_fields_exclude_clinician_only_signals`, `::test_patient_projection_never_carries_clinician_only_signals`, **and** `e2e::test_flow_share_and_patient_view_has_no_clinician_signals`, which additionally asserts the *values* `test-model` and `live_fallback` appear nowhere in the payload |
| 8.3 | Scoped to the authenticated patient | **Pass** | `::test_visit_summary_lookup_is_scoped_to_the_authenticated_patient` |
| 8.4 | One batched query | **Pass** | `::test_visit_summary_enrichment_is_one_batched_call_not_one_per_booking` |

### 9. Authentication, roles, permissions

| # | Feature | Status | Evidence |
|---|---|---|---|
| 9.1–9.7 | Login, MFA, invite, rate limit, lockout, token revocation | **Pass** | `test_doctor_auth.py`, `test_unified_login.py`, `test_rate_limiter.py`, `test_users_lockout_integration.py`, `test_token_revocation_integration.py` — all unchanged and green |
| 9.8 | Every doctor route guarded | **Pass** | `test_appointments_auth_required.py`; the e2e sidebar flow asserts 401 on 5 endpoints without a token |
| 9.9 | Doctor identity never client-supplied | **Pass** | `test_doctor_workspace_routes.py::test_no_new_route_accepts_a_client_supplied_doctor_id` asserts this **structurally across all 6 new routes**, so a future edit that adds one fails the test |

**No existing test was weakened, skipped or deleted.** The pre-existing suite went 605 → 605 green, plus 88 new.

**Suite as it stands now** (full suite against the containerised DB on `:5433`):
**868 passed, 1 skipped, 1 failed in 2m56s**. The single failure is
`test_multilingual.py::test_global_and_asian_expansion_languages_are_detected`, the known
pre-existing host-only failure — it needs `models/lid.176.bin`, which exists only in the
container. It fails identically before and after this work. The count is above 605 + 88
because the department-resolver, document-follow-up and data-freshness work landed in the
same tree (833 → 868 over the freshness change, §10).

---

## 3. New features

| § | Feature | Built | Tests |
|---|---|---|---|
| 4.1 | AI activity summary | Yes — hero + 4 tiles + headline, from `/doctor/ai/activity-summary` | `test_doctor_workspace.py` headline tests (4); `..._integration.py::test_activity_summary_is_scoped_to_one_doctor`, `::test_summary_falls_back_to_24h_when_there_is_no_previous_login`, `::test_summary_window_excludes_activity_from_before_the_last_login`, `::test_summary_counts_flagged_fields_and_blocked_notes_from_real_rows` |
| 4.2 | AI-prioritised next actions | Yes — ranked, one-click Review/Regenerate/Generate | **9 ranking unit tests** incl. total-order determinism and malformed input; visible ordering confirmed in `overview-1280.png` |
| 4.3 | AI activity log | Yes — from the **existing** `consult_audit_log`; no new event source needed except one new audit action for "held back" | `::test_activity_log_is_scoped_to_one_doctor`, `::test_activity_log_projects_an_allowlist_not_the_raw_metadata`, `::test_activity_log_drops_action_types_it_does_not_declare`, `::test_activity_log_limit_is_clamped` |
| 4.4 | Today's schedule with AI status | Yes — Drafting / Transcript captured / AI brief link | rendered in `overview-1280.png` |
| 4.5 | Review inbox lanes + bulk draft | Yes — 3 lanes, S/O/A/P chips, one-line explanation, "Draft N missing notes" | **8 lane/grouping unit tests** incl. the two-lane tie-break; `explain_item_status` tests (3); bulk draft is rate-limited, capped and idempotent by construction |
| 4.6 | Note verification workflow | Yes — per-section mark, "n of 4" progress bar, inline citations, flag explanations | `verification_progress` unit tests (4); `::test_section_verification_round_trips_and_is_idempotent`, `::test_a_signed_note_can_no_longer_be_marked`, `::test_regenerating_a_note_clears_its_verification_marks`, `::test_another_doctor_cannot_read_or_write_this_notes_verification_state`, + 6 route tests |
| 4.7 | AI assistant side panel | Yes — provenance, suggested checks from existing flags | rendered from the note payload; "Ask about this consultation" is **present but disabled** (see 4.8) |
| 4.8 | Ask AI command bar (⌘K) | **UI only, feature flag OFF** (`DOCTOR_ASK_AI_ENABLED = false`) — as agreed in D5 | n/a — deliberately not wired to any backend |
| 4.9 | AI patient brief | Yes — signed notes + document summaries, per-line source labels, disclaimer | `select_brief_sources` unit tests (6) incl. the unsigned-draft exclusion; `::test_patient_brief_never_includes_an_unsigned_draft_against_real_rows`, `::test_patient_brief_excludes_another_doctors_signed_notes`, `::test_patient_brief_requires_a_treating_relationship`, `::test_patient_brief_with_no_signed_history_is_empty_not_an_error` |
| 4.10 | Insert from plan | Yes — copies signed-plan medication lines verbatim; allergy alert shown on the same screen | `extract_plan_medication_lines` unit tests (8) incl. **the verbatim/no-validation test**; 4 route tests incl. the unsigned-note refusal |
| 4.11 | Audit trail (Signed & shared) | Yes — AI drafted (model + prompt) → edited → signed → shared, each timestamped | rendered from the note's own timestamps |

**Ranking rule (documented, deterministic).** Sort key, ascending:
`(blocked first, −flag weight, oldest appointment, undrafted last, consultation_id)`.
Flag weight = `low_confidence_fields + 2 if lower-quality transcript`. The trailing
`consultation_id` guarantees a **total order**, so the list never reshuffles between loads
(`test_ranking_is_a_total_order_and_does_not_reshuffle`). It orders *documentation work*,
never clinical urgency — no severity is persisted anywhere in this schema to rank by, and
`test_explanation_never_describes_the_patient_or_anything_clinical` pins that down.

---

## 4. Safety invariants (§5) and the tests that prove each

| Invariant | Proven by |
|---|---|
| AI output never enters the record or reaches a patient without a signature | `test_an_unsigned_note_can_never_be_shared`; `e2e::test_flow_share_and_patient_view_has_no_clinician_signals` asserts the pre-sign share returns 409; `test_an_unsigned_draft_is_never_compiled_into_a_brief` + `test_patient_brief_never_includes_an_unsigned_draft_against_real_rows`; `test_plan_medications_refuses_an_unsigned_note` |
| Patient view shows no citations, flags, transcript, model, prompt or verification state | `test_patient_visible_fields_exclude_clinician_only_signals`; `test_patient_projection_never_carries_clinician_only_signals`; `e2e::test_flow_share_and_patient_view_has_no_clinician_signals` (checks 7 forbidden keys **and** that the model name and `live_fallback` appear nowhere in the payload) |
| Blocked notes cannot be signed via UI **or** API | `test_sign_soap_note_rejected_when_stale` (service) + `e2e::test_flow_blocked_note_cannot_be_signed_through_the_api` (HTTP 409, note still `stale`, still unsigned) |
| Approved clinical actions are read-only in UI and API | `test_approval_is_one_way_and_locks_the_record`, `test_there_is_no_unapprove_route`, `e2e::test_flow_approve_prescription_becomes_read_only` (refused edit **and** content verified unchanged) |
| Doctors see only their own patients and data — incl. activity log and brief | `e2e::test_doctor_a_cannot_reach_doctor_bs_workspace_data` walks the whole new surface as the wrong doctor; `test_activity_log_is_scoped_to_one_doctor`; `test_activity_summary_is_scoped_to_one_doctor`; `test_patient_brief_excludes_another_doctors_signed_notes`; `test_another_doctor_cannot_read_or_write_this_notes_verification_state`; `test_no_new_route_accepts_a_client_supplied_doctor_id` |
| AI never generates dosing, interaction or formulary advice | `test_insert_from_plan_copies_verbatim_and_validates_nothing` (an implausible dose comes back **exactly** as written — uncorrected, unflagged, with nothing added); `test_detailed_style_still_forbids_inventing_content`; `test_plan_medications_returns_signed_lines_and_says_nothing_is_validated` |
| Everything AI-generated is labelled | brief returns `is_ai_generated`/`clinician_reviewed` (asserted); every draft row carries an "AI draft" chip; the sidebar carries "AI drafts, you decide"; the review inbox carries the guard-rail banner |

One further invariant was added on top of the brief: **no bulk-sign or approve-all route
exists**, asserted structurally by `test_there_is_no_unverify_all_or_bulk_sign_route`. A
bulk-sign button would let a doctor sign AI output they had not read, which is the exact
failure the whole design exists to prevent.

---

## 5. Visual redesign

Implemented under a `.doctor-ai` scope so **none of it can reach the patient or admin
UIs**, which are out of scope for this work.

- **Palette** kept exactly; status colours added to the existing `:root` token block
  (`--ok #047857` on `--ok-bg #ECFDF5`, `--warn #A14A06` on `#FFF7E8`, `--bad #B91C1C` on
  `#FEF2F2`), all measured ≥ 5.3:1.
- **Typography** Bricolage Grotesque / Geist / Geist Mono, **self-hosted** (D3-a) at
  `app/api/static/vendor/fonts/`, 281 KB total, latin subset. The app makes **no external
  request** at page load. Regenerate with `scripts/fetch_redesign_fonts.py`.
- **Layout** dark ink sidebar (`#1C1535`) with brand mark, icon nav, count badge, the
  "AI drafts, you decide" card and the doctor profile with log out; top bar; 18px card
  radius (`--r-card`); segmented tabs; status chips.
- **Icons** inline stroke SVG throughout. No emoji anywhere.
- **Responsive** to tablet — verified at 800px (`screenshots/reviews-tablet-800.png`):
  sidebar becomes horizontal, lanes collapse to one column, no content clipping.

### One deliberate departure from "keep the palette exactly"

`--muted-fg` is overridden to **`#5F6488`** *inside `.doctor-ai` only*. The global token
`#6B7094` measures **4.29:1** on `--muted #F5F0FF` — below the 4.5:1 this brief also
requires — and axe flagged it as a serious violation on the muted chips and segmented
tabs. `#5F6488` measures 5.13:1 on `--muted`, and is the exact value the design spec's own
`ai-theme.css` uses for this role, so it satisfies both requirements rather than trading
one against the other. This **reverses my D6 answer** on that one token: the design file's
muted tone was the accessible one and I was wrong to keep the existing value there.

The patient and admin surfaces keep `#6B7094` and therefore **keep the same contrast
issue**. That is a pre-existing, out-of-scope finding, reported here rather than silently
fixed across the app.

### Bugs found and fixed by the headless render check

Both were real defects that no test would have caught, found only by rendering the page:

1. The clickable stat cards and list rows are real `<button>` elements, which inherit
   neither colour, font nor text-align — their figures rendered in the UA's default button
   styling, and patient names were invisible on the appointment rows. Fixed explicitly.
2. In a ~300px lane column the horizontal item layout wrapped unreadably. Lane cards now
   stack, with the action full-width at the bottom.

---

## 6. Verification performed

### 6.1 Tests

```
1 failed, 693 passed, 1 skipped, 1 warning in 294.72s
FAILED tests/test_multilingual.py::test_global_and_asian_expansion_languages_are_detected
```

Command (host-side, against the containerised Postgres):

```
DATABASE_URL=postgresql://postgres:<POSTGRES_PASSWORD>@127.0.0.1:5433/hospital_db \
  .venv/Scripts/python.exe -m pytest tests -q
```

New test files:

| File | Tests | Covers |
|---|---|---|
| `tests/test_doctor_workspace.py` | 43 | ranking, lanes, explanations, verification progress, activity headline, brief source selection, plan parsing — no DB, no model |
| `tests/test_doctor_workspace_integration.py` | 18 | activity summary/log, section verification, patient brief against real Postgres, incl. cross-doctor isolation |
| `tests/test_doctor_workspace_routes.py` | 21 | route wiring, error mapping, and the structural "no client-supplied doctor_id" assertion |
| `tests/test_doctor_workspace_e2e.py` | 6 | the five required flows + a cross-doctor isolation walk, over real HTTP |

### 6.2 Accessibility — axe-core 4.10.2, WCAG 2.0/2.1 A + AA

| Pane | Violations | Passes |
|---|---|---|
| Overview | **0** | 11 |
| Reviews | **0** | 18 |
| Upcoming | **0** | 11 |
| Past | **0** | 11 |
| Patients | **0** | 12 |

Run in headless Edge against the real `index.html`, with axe injected into the page. The
one violation found (contrast, §5) was fixed and re-verified. Reproduce with
`docs/ai-redesign/verification/render-harness.html` (see §6.5).

### 6.3 JavaScript

No browser test runner exists, so this was verified by loading the real page in headless
Edge and capturing the console: **no syntax errors, no uncaught exceptions** on load, with
`app.js` confirmed served and executing (DOM grows 100 KB → 123 KB as the JS renders).

> Correction to an earlier statement made during this work: a first "no JS errors" check
> was invalid because the static server was rooted at `static/`, so `/static/app.js` 404'd
> and the script never loaded. The check was redone correctly and is what is reported here.

### 6.4 Database migration

`0022_doctor_workspace_ai` — applied, downgraded to `0021`, and re-applied cleanly against
the live database. All three objects confirmed present by direct query. Purely additive
(one nullable column, one index, one table); no data loss on downgrade beyond the review
marks and previous-login bound it introduces.

### 6.5 Screenshots

In `docs/ai-redesign/screenshots/`, captured at **1280px** in headless Edge:

| File | Screen |
|---|---|
| `overview-1280.png` | AI overview — hero, tiles, ranked next actions, today, activity log |
| `reviews-1280.png` | AI review inbox — three lanes, S/O/A/P chips, bulk draft |
| `upcoming-1280.png` | Upcoming appointments |
| `past-1280.png` | Past appointments |
| `patients-1280.png` | Patients (empty state) |
| `reviews-tablet-800.png` | Reviews at tablet width |

**These are rendered with fixture data, not real patient data**, via
`verification/render-harness.html` — a temporary harness that loads the real `index.html`,
intercepts its fetches and drives its real loader functions. It is **not** application
code and is **not** in the served static directory. No figure in a screenshot is a claim
about real data.

**Intentional differences from `design/ai-redesign/`:**

- The design's demo numbers (3 notes, 2 documents, "4 items") are **never hard-coded** —
  the screenshots happen to show those values because the fixtures use them. Real
  deployments render real counts, or zeros.
- The Ask AI command bar is **hidden**, not shown, because its flag is off (D5). The design
  shows it populated.
- Nav labels keep this app's existing wording ("Reviews", "Past") rather than the design's
  ("AI reviews", "Past visits"), so the sidebar keeps matching the rest of the product.
- `--border` stays `#DDD6FE` per your §3 instruction, not the design file's softer
  `#E6E0FB` (D6).
- Sidebar brand text wraps to two lines at 236px; the design's mock does not. Cosmetic.

---

## 7. Known gaps and things NOT verified

### 7.1 One pre-existing test failure (not caused by this work)

`tests/test_multilingual.py::test_global_and_asian_expansion_languages_are_detected` fails
on the host because `app/services/language.py` needs the 131 MB fastText model at
`models/lid.176.bin`, which is fetched at container build time and exists only at
`/app/models/lid.176.bin` inside the container. It failed identically at baseline, before
any change, and touches nothing in the doctor workspace.

### 7.2 Checks that could not be run because they do not exist

Per **D1** and the standards' instruction to say so rather than substitute a guess:

- **Linter** — none configured (no ruff/flake8/eslint config anywhere).
- **Type checker** — none configured (no mypy/pyright).
- **Build** — there is none; the frontend is served as static files and never compiled.
- **Security scanner** — none configured.

I did not run these and do not claim to have. `plan.md` §7 proposes the real values for
the standards' blank Repository Commands section.

### 7.3 Component tests

Not written. There is no JavaScript test framework in this repository (no `package.json`),
which is **D2**. Loading, empty and error states are instead covered by: the axe runs
above, the render harness exercising the real loader paths, and explicit empty-state
rendering in every new list (`buildDoctorEmptyState`), including the distinction between
"nothing to review" and "could not load". Error paths in the new loaders are deliberately
non-fatal and were written so a failed AI panel never blocks the clinical workspace.

### 7.4 Screens inside the appointment-detail pane — now covered

**This gap is closed.** The Note, Clinical actions, Patient detail and Signed & shared
screens live inside the appointment-detail pane, which needs a live consult with a
transcript to reach. The harness was extended to construct that state by serving the
consult, transcript, note and patient payloads through the same intercepted `fetch` the
other panes already used, so the screens render through the app's **own** loaders
(`showDoctorAppointmentDetail` → `loadSoapNote` / `loadConsultTranscript`) rather than by
calling render functions directly.

All four now have a screenshot (`verification/screens/`) and an axe run:

| Screen | axe (WCAG 2.0/2.1 A + AA) | colour-contrast rule |
|---|---|---|
| Note (draft) | 0 violations, 20 passes | ran, passed, 71 nodes |
| Signed & shared | 0 violations, 13 passes | ran, passed, 61 nodes |
| Clinical actions | 0 violations, 20 passes | ran, passed, 71 nodes |
| Patient detail | 0 violations, 11 passes | ran, passed, 48 nodes |

Two real defects were found by doing this, both now fixed — see §7.4.1. A third item is
**not** fixed and is recorded in §7.4.2.

#### 7.4.1 Defects this found

1. **`critical` / `label` — the four SOAP textareas had no accessible name.**
   `buildNoteFieldRow` sets a `placeholder` only when a field is *empty*
   (`app.js`), and a placeholder doubles as an accessible name. So an empty note passed
   the check and a note **with content — the normal case — did not**: a screen-reader
   user editing a clinical note heard an unnamed "edit text" with no indication whether
   they were in Subjective or Plan. Fixed by giving each textarea an explicit
   `aria-label` naming its section. This was invisible until the harness was corrected,
   because the earlier harness rendered the note into empty fields.

2. **`serious` / `color-contrast` — the patient-reported health issues alert label.**
   `.doctor-patient-alert-label` used `--destructive` (#DC2626) at 10px bold on the
   alert's own tint (#F8EBF2): **4.18:1**, under the 4.5:1 minimum. This is the element
   the feature inventory calls the one thing on the screen a clinician must not miss.
   Fixed to `--bad` (#B91C1C), **5.61:1** on the same background, measured two ways
   (axe, and an independent hand computation). `--destructive` itself is unchanged — it
   is shared with the patient and admin UIs.

A third, `.doctor-ai-nav-count` (the pending-review badge), was white on `--primary-glow`
at **3.96:1**. axe returns this node as *incomplete* rather than a violation, so it was
caught by hand-computing the ratios for every node axe could not decide. Fixed to
`--primary`, **5.70:1**; it now resolves and passes under axe as well.

#### 7.4.2 Known, not fixed: the primary-button gradient

`--gradient-primary` is `linear-gradient(135deg, #7C3AED, #A855F7)`. White text on it
passes over roughly the first 60% of the gradient and **fails toward the light end**:

| position | colour | white text |
|---|---|---|
| 0% | #7C3AED | 5.70:1 ok |
| 50% | #9248F2 | 4.74:1 ok |
| 75% | #9D4EF4 | 4.35:1 **fail** |
| 100% | #A855F7 | 3.96:1 **fail** |

This is **pre-existing and app-wide** — the token is defined in the base palette and used
by 20 rules across the patient, admin and doctor UIs; it is not redesign code. axe reports
these buttons as *incomplete* (it will not compute contrast over a gradient), which is why
no run has ever flagged it. Changing the light stop to **#9333EA** (5.38:1) would fix every
one of them in a single line, but it repaints every primary button in the application, so I
have not made that call unilaterally.

### 7.5 Feature-flagged

**Ask AI (§4.8)** is built as UI only, flag off (`DOCTOR_ASK_AI_ENABLED = false` in
`app.js`), plus a disabled, labelled "Ask about this consultation" input on the note
assistant panel. Turning it on needs authorization-filtered retrieval, per-doctor cost
caps, prompt-injection defence and source attribution on every claim — none of which
exists. Agreed as D5.

### 7.6 Delivery

No feature branch, no commits, nothing pushed — you asked for no git operations. All work
is uncommitted in the tree on `dev`, alongside the 16 modified and several untracked files
that were already there when this started. I did not touch that pre-existing work, and the
commit-splitting in `plan.md` §6 has not been applied.

---

## 8. Files changed

**Added**

| Path | Purpose |
|---|---|
| `alembic/versions/0022_doctor_workspace_ai.py` | previous-login column, doctor-scoped audit index, section-verification table |
| `app/services/doctor_workspace.py` | pure logic: ranking, lanes, progress, headline, brief selection, plan parsing |
| `app/services/doctor_ai_activity.py` | activity summary and allowlisted activity feed |
| `app/services/patient_brief.py` | signed-notes-only patient brief |
| `app/services/soap_sections.py` | per-section verification persistence |
| `app/services/bulk_draft.py` | bounded, rate-limited, idempotent bulk drafting |
| `app/api/static/vendor/fonts/` | 3 self-hosted typefaces + `fonts.css` |
| `scripts/fetch_redesign_fonts.py` | regenerates the above |
| `tests/test_doctor_workspace*.py` (4 files) | 88 new tests |
| `docs/ai-redesign/` | inventory, plan, this report, screenshots, harness |

**Modified**

| Path | Change |
|---|---|
| `app/api/routes/doctor.py` | 4 new endpoints; reviews payload enriched with lane/explanation/ranking |
| `app/api/routes/consult.py` | 3 new endpoints (sections ×2, plan-medications) |
| `app/services/doctor_auth.py` | `previous_login_at` column + carry-forward on both login paths |
| `app/services/consults.py` | doctor-scoped audit index in `ensure_consult_schema` |
| `app/services/soap_notes.py` | clears verification marks on regenerate; audits "held back" |
| `app/api/static/index.html` | doctor workspace rebuilt; self-hosted fonts linked |
| `app/api/static/app.js` | new render/loader functions; doctor renderers reworked |
| `app/api/static/styles.css` | status/typography/ink/radius tokens; `.doctor-ai` component styles |

---

## 9. Status

The feature inventory passes in full, all eleven new features are built (one deliberately
behind an off flag), every safety invariant has at least one named test proving it, and
the suite, accessibility and migration checks are green.

**It is not "all passing" without qualification**, and three things are outstanding:
the pre-existing multilingual failure (§7.1), the app-wide primary-button gradient whose
light end fails contrast (§7.4.2 — pre-existing, one-line fix available, not made because
it repaints every button in the application), and the lint/type/build checks that do not
exist to run (§7.2). Nothing here should be treated as verified beyond what §6 and §7.4
actually record.

The previously-listed fourth item — the four appointment-detail screens with no visual or
accessibility verification — **is closed** (§7.4). Closing it turned up two real defects,
one of them `critical`, both now fixed; the `critical` one could only ever have been seen
on a note that had content, which is why an earlier, subtly broken harness had missed it.

---

## 10. Data freshness, activity window, model-name removal

Four reported defects, root-caused against the running container and its database. Plan:
`.claude/plans/follow-the-claude-standards-warm-wren.md`.

| # | Reported | Cause | Fix |
|---|---|---|---|
| 1 | AI activity vanishes on hard refresh | `bootstrapSession` loaded appointments only; the login path loaded three things. A reload silently dropped the AI panels **and the whole review queue** | One entry point, `enterDoctorWorkspace`, used by both paths |
| 2 | "since your last visit" blank, intermittently | `previous_login_at` advanced on **every** login, so a re-login made the window minutes wide. Live: a 2m40s window against a 24h window holding 2 notes and 2 documents | `SESSION_GROUPING_MINUTES` (write side) + `MIN_LAST_VISIT_MINUTES` floor (read side) + an explicit window toggle |
| 3 | Model name / prompt version shown | Four render sites, plus the server sending them in the feed payload | Removed from all four and from `_FEED_ACTIONS`; retained in the DB and the doctor's API response |
| 4 | Nothing updates in real time | Every view was load-once; the only timer was a 4s transcript poll during a consult | Poll while visible, refresh on focus/visibility, refetch on view switch and after every mutation |

**Checked and ruled out:** 852 of 859 feed rows have `doctor_id IS NULL`, which looks like
a broken write path but is entirely test-suite rows — for the real doctor's consults the
split is 0 NULL / 7 populated. No change made.

**Safety constraint on §4.** The SOAP editor saves on an explicit button press and has no
dirty-tracking, so a background re-render would discard unsaved clinical text. Auto-refresh
is therefore excluded from the appointment-detail and patient-detail panes, from an active
consult, and from a hidden tab (`canRefreshDoctorViewNow`), and a failed background refresh
keeps the data already on screen rather than replacing it with an empty state.

**Not changed, flagged:** `doctorAuthedJson` logs the doctor out on any 401. That is right
for an expired token, but polling makes it happen unprompted rather than on an action. It
is pre-existing auth behaviour and was left alone rather than altered as a side effect.

**Verification:** 868 passed / 1 skipped / 1 known host-only failure; 0 axe violations
across all 9 doctor screens with the new toggle present; the toggle's own contrast measured
by hand on the dark hero (14.79:1 active, 11.31:1 inactive, 9.97:1 for the updated-at line).
The structural guards were confirmed to **fail** against the pre-fix source rather than
passing vacuously.

---

## 11. Patient history — phase 1a (capture)

Ships the write side alone, ahead of any screen that reads it, because the pre-visit
context did not exist anywhere and **every booking made without it is unreconstructable**.
Plan: `.claude/plans/follow-the-claude-standards-warm-wren.md`.

**What now gets captured**

| | Before | Now |
|---|---|---|
| Which conversation produced a booking | nothing | `booking_context_snapshots.chat_session_id` |
| Assistant's suggestion vs patient's choice | transient agent state, discarded | both stored, independently nullable |
| Documents brought to the appointment | unlinkable | explicit id list, frozen at booking |
| The transcript behind it | grew forever with the session | pinned to an inclusive time window |
| `referring_doctor` / `referring_department` / `body_region` | extracted, then **dropped** | persisted on `document_catalog` |
| Per-page document text | flattened, persisted nowhere | `document_pages`, with its `source` |

**Immutability is structural, not conventional.** The snapshot is written in the booking's
own transaction; `booking_id` is UNIQUE; there is no UPDATE path anywhere in the codebase;
and the transcript is pinned to a window so later conversation cannot alter it.

**Two defects found while building it, both fixed:**

1. **An id-based transcript pin could not work.** `chat_messages.created_at` defaults to
   `now()`, which is constant within a transaction, and a turn writes the patient message
   and the assistant reply together — so both rows share a timestamp. Verified on live
   data: one session holds **26 messages across 13 distinct timestamps**. "The last
   message" is not a well-defined row, so the pin is an inclusive timestamp window, which
   also keeps both halves of the final turn.
2. **A malformed `booking_id` returned 500, not 404.** The id comes from the URL path and
   both columns are UUID, so a non-UUID reached Postgres and raised
   `InvalidTextRepresentation` — leaking that the input had reached the database. Now
   treated as not-found, like any other id that does not exist.

**Safety properties, each with a test that fails without it:**

- A snapshot failure never costs the patient their appointment. Capture runs inside a
  **SAVEPOINT**, because in Postgres a failed statement aborts the entire transaction —
  without it a broken snapshot rolls back the booking. **Proven by removing the SAVEPOINT
  and watching the booking be lost.**
- "No context was recorded" is distinguished from "the patient said nothing", in the API
  (`recorded: false`) and in the UI. A failed request says neither.
- Reading a context is authorized to the booking's **own** doctor — not
  `doctor_treats_patient`, which is true of any doctor who ever booked this patient — and
  is audited to `consult_audit_log`.
- Re-extraction `COALESCE`s the referral fields, so a pass that misses the referral line
  cannot erase one an earlier pass captured.

**Verification:** **920 passed**, 1 skipped, 1 known host-only failure (up from 868);
0 axe violations across all 9 doctor screens with the new panel present; migration
round-tripped up/down/up against the live database.

**Not yet built** (phase 1b and beyond): the AI summary of the conversation — left
`pending`, which is safe precisely because the transcript is pinned, so generating it
later produces exactly what generating it now would. Also the collapsible transcript view,
the document viewer, and the whole of phase 2.

---

## 12. Patient history — feature 3: reports explained, flagged and trended

End-to-end and verified against real stored documents, not fixtures.

**What a doctor now sees** on any patient document (`Show summary`): a verified prose
summary with per-sentence page citations, the out-of-range values as chips, and a count of
what was read but not flagged.

### The two-pipeline design

The prose is model output that survived verification. The chips are values parsed by code
and classified against code-owned reference ranges. They are **independent on purpose**:
a doctor reading *"Vitamin D is deficient at 13.8 ng/mL"* sees `Vitamin D ↓ 13.8 ng/mL
(ref 30–100)` beside it, arrived at by a different path.

Observed doing its job on the real report: the hs-CRP sentence failed verification and was
withheld, but `hs-CRP ↑ 3.6 mg/L` still reached the doctor as a chip.

### Measured on a real 3-page lab report

| | Result |
|---|---|
| Summary | `partial` — 4 sentences verified, 1 dropped |
| Shown | "Morning serum cortisol is elevated at 24.6 µg/dL. Vitamin D is deficient at 13.8 ng/mL, and Vitamin B12 is below the reference interval at 178 pg/mL. Dyslipidaemic pattern noted with raised triglycerides at 176 mg/dL and LDL at 130.8 mg/dL, and low HDL at 38 mg/dL. Thyroid function tests are within reference limits." |
| Measurements | 144 backfilled from 3 documents; 48 per report |
| Flags | 8, matching the extractor's own prose impression by a separate path |
| axe | 0 violations at 1366 and 1280; contrast passed on 49 nodes |

### Four defects found by running against real data

1. **A reference range could launder an inverted value.** Checking numbers page-wide,
   *"Vitamin D is 30 ng/mL, normal"* passed on a page reading `18 ng/mL (ref 30 - 100)`.
   Numbers are now checked against the **quote**, not the page.
2. **Quotes spanning non-adjacent lines were rejected.** Models cite a results table by
   pulling together the rows that matter and eliding the rest. Requiring one contiguous
   run **dropped 3 of 5 correct sentences** — Vitamin D, hs-CRP and the lipid panel, all
   genuinely in the document. Each *fragment* must now be verbatim; they need not be
   adjacent. This raised the real report from 2/5 to 4/5 verified.
3. **Mis-cited pages discarded true content.** The model attributed pages 2 and 3 content
   to page 1. The page is now a hint and the quote the claim: the verifier locates the
   quote itself and records the page it was actually found on, so the stored citation is
   more trustworthy than the model's.
4. **"Mean Corpuscular Hb (MCH)" canonicalised to "Haemoglobin"** (the token `hb`). The
   unit guard blocked a wrong flag, but a trend groups by canonical name alone — MCH would
   have been plotted silently into a haemoglobin series.

### Trends, and what counts as one

Computed in SQL, never by a model. Two rules came from real data:

- **Trendability counts distinct dates.** The same report had been uploaded three times,
  which made 30+ measurements look trendable from a single blood draw.
- **Identical readings dedupe on (date, value, unit)** — but two *different* results on
  one date are both kept, because two labs disagreeing is a clinical fact.
- A **unit change** returns only the latest unit's readings, so a lab switching ng/mL to
  nmol/L cannot produce a 2.5x step that looks clinical.

### Deliberate refusals to guess

- Wrong unit for the reference range → **unknown**, no flag shown.
- Censored value (`<0.01`) → never classified, never plotted; it is a bound.
- No reference range → **unknown**, not "normal". The UI states how many values were read
  but not flagged, so "unflagged" is never mistaken for "checked and normal".

### Known limitation, pinned in the suite

A reference range on the **same line** sits inside the quote, so a sentence citing it
still verifies. Closing that needs value attribution, which is the structured extraction's
job. Test: `test_a_same_line_reference_range_is_a_KNOWN_uncovered_case`.

**Verification:** **1015 passed**, 1 skipped, 1 known host-only failure (up from 920).
Migration 0024 round-tripped up/down/up against the live database.

---

## 13. Patient history — feature 5: in-app document viewer

Doctors could previously only **download** a document: leave the workspace, open a file
from disk, read it with no summary beside it. Now `View` opens it in place, with its
verified summary and parsed values alongside.

### How it stays safe without weakening anything

The file route keeps `Content-Disposition: attachment` and its four-entry type allowlist,
**both unchanged**. The viewer fetches the bytes with `fetch()` and draws them into a
`<canvas>`, so the browser never navigates to document content and the disposition header
is irrelevant to it. The stored-XSS decision recorded at
`document_catalog._content_type_for` stands exactly as written.

This is also better than the signed-URL approach the original brief suggested: **every
byte still passes our auth and our audit**, which a storage URL would bypass once issued.
No SAS support was added, and none is needed.

Guarded by tests that fail if the viewer ever reaches for `<iframe>`, `<embed>`,
`<object>` or `window.open` on document content.

### What it does

PDF page navigation, zoom, rotate; images the same, plus **brightness and contrast** for
X-rays and photographed films, applied as a CSS filter so the stored file is never
altered. One `Reset view` undoes every adjustment at once. Download remains, as the
fallback for anything the browser will not render.

PDF.js 3.11.174 is vendored (`scripts/fetch_pdfjs.py`), pinned, and loaded lazily on first
open — ~1.4 MB that most sessions never need. A failed load is not cached, so a transient
error does not disable the viewer for the session. Closing releases the object URL and
destroys the PDF, so a patient's record does not sit decoded behind a closed overlay.

**DICOM is not supported and is not needed** — uploads are PDF/JPEG/PNG only, capped at
15 MB, so OHIF/Cornerstone is out of scope as established during planning. Range requests
were likewise dropped rather than shipped untested: at a 15 MB cap nothing exercises them.

### Verified end to end on a real document

Against the actual lab report from storage, driven over CDP in real time:

| | Result |
|---|---|
| Render | canvas 908×1284, page **1 / 3**, no error |
| Navigation | `Next` advanced to page 2/3 and re-rendered |
| Side panel | verified summary with `[p1]`/`[p2]` citations + **8 abnormal chips** |
| axe | **0 violations**, 14 passes on the viewer |

The screenshot (`verification/screens/document-viewer.png`) shows the design goal met: the
document's own line `Vitamin D, 25-Hydroxy (Total) 13.8 L` sits beside the chip
`Vitamin D ↓ 13.8 ng/mL (ref 30–100)`. The report's own H/L flags agree with every flag
computed independently by `document_findings`.

### A verification trap worth recording

`--virtual-time-budget`, used for every other headless check in this report, **cannot
verify anything involving PDF.js**: it fast-forwards timers, which breaks PDF.js's worker
handshake so `getDocument()` neither resolves nor rejects. It looks exactly like a hung
application.

That cost a wrong diagnosis: PDF.js 4.x was abandoned for "a broken worker" when it had
only been run under that broken harness. The switch to the v3 UMD build is still correct
for a classic-script frontend with no bundler — and avoids depending on the server sending
a JS MIME type for `.mjs`, which Python's `mimetypes` does not know — but 4.x was never
shown to fail in a real browser, and `scripts/fetch_pdfjs.py` says so.

Anything touching workers must be verified over CDP in real time instead.

### Images — checked separately, and it found two gaps

The PDF path was verified first; images are a different code path and were **not** covered
by that. Testing them turned up two real problems.

**1. An image with an unrecognised extension showed "Invalid PDF structure."**
`content_type` comes from a four-entry *extension* allowlist, so a valid JPEG stored
without a usable extension arrives as `application/octet-stream`, fell into the PDF branch
and failed with a PDF.js internal error about a file that is not a PDF and renders
perfectly well.

Fixed by deciding from the file's **magic bytes** (`%PDF`, `\x89PNG`, JPEG SOI), with the
declared type only as a fallback. That fixes the file rather than the message. Safe to
sniff here because the result only ever chooses between "draw on a canvas" and "parse as
PDF" — it never sets a `Content-Type` and never reaches the server. Anything that is
neither now says so and points at Download.

**2. Image documents got no summary at all.** Page text was stored only for PDFs, so
`PAGE_SOURCE_VISION` and the "scanned document" warning built for exactly this case were
both dead code. An uploaded X-ray or photographed report got chips but no prose.

Fixed by transcribing image documents at ingestion
(`azure_client.gpt4o_transcribe_document_image`) and storing the result as the page text
with `source='vision_transcription'`. The existing grounded-summary path then applies
unchanged, and the viewer labels the weaker guarantee.

Measured on a real photographed report (a rendered page of the lab report, 1406×1988 PNG):

| | Result |
|---|---|
| Transcription | 1,857 characters, letterhead read correctly |
| Summary | **passed — 8 sentences kept, 0 dropped** |
| Values | 13.8 / 178 / 204 / 176 / 38 / 130.8 / 35.2 / 5.37, all matching the document |
| Render | canvas 908×1284, label "Image", paging controls correctly hidden |
| Rotate | 908×1284 → 1284×908, fully drawn, no clipping or offset |

**The guarantee is weaker for a scan and the UI says so.** Verifying a summary against a
transcription proves the summary invented nothing beyond what was transcribed; it cannot
prove the transcription was right. That is why the source is recorded separately and
labelled, rather than presented as equivalent to a PDF text layer.

**Verification:** **1023 passed**, 1 skipped, 1 known host-only failure.

---

## 14. Patient history — feature 2: cross-doctor timeline

Every encounter a patient has had, with any doctor, newest first, with filters and
collapsible rows. A new **Full timeline** tab beside the existing "Visit history" (which
remains this doctor's own appointments).

### This is the change that widened disclosure

Until now a doctor saw only their own signed notes. Past the unchanged
`doctor_treats_patient` gate, they now see the whole hospital's history for that patient.
That was the agreed decision — withholding history from a treating clinician is itself a
clinical risk — so **every call is audited** (`patient_timeline_viewed`) and the panel says
so on screen.

### Two things stay withheld

| | Rule |
|---|---|
| Unsigned drafts | Never shown, to anyone. A draft is model output no clinician has taken responsibility for; putting it in a history timeline would launder it into the record by presentation alone. Only `status = 'signed'` appears. |
| Sensitive specialties | Note content from `SENSITIVE_DEPARTMENTS` (Psychiatry) is withheld from doctors outside it. **The encounter is always visible** — hiding the visit would let a colleague believe there is no history when there is. The booking note is withheld with it, being the same information by another route. |

A withheld note renders as *"Restricted — clinical content from a sensitive specialty"*,
never as an absent or empty note: "nothing was written" and "something exists and you may
not see it" must never look the same. A psychiatrist reads psychiatry notes normally — the
restriction is about disclosure *across* specialties.

**Sequencing note.** The plan put break-glass in a later phase. The restriction itself was
built here rather than deferred, because shipping the timeline without it would expose
psychiatry notes to every treating doctor until that phase landed, and retrofitting a
restriction after exposure is worse than starting closed. The *request-access flow* is
still to come; the default is already deny.

### Deviation from the plan, and why

The plan proposed an `is_sensitive` column. There is no departments table — `department` is
a text column on `doctors` — so the column would sit per-doctor, modelling sensitivity as a
property of the individual rather than the specialty. It is a code-owned frozenset instead,
matching `CANONICAL_DEPARTMENTS` and `NEVER_ROUTE_TO_DEPARTMENTS`, and should move to a
table when an administrator needs to change it without a deploy.

**Known gap, stated not buried:** this restricts note content. A document uploaded around a
psychiatry visit is still reachable through the existing document routes, which have no
concept of sensitivity. That belongs with the break-glass work.

### Performance

Four queries for a whole page, never per row, and the timeline is fetched only when the
tab is opened rather than on every patient open. The app runs one pool of ten connections
for all users and *raises* rather than queues when exhausted, so an N+1 here would fail the
workspace under a handful of doctors.

### Verified

- **33 timeline tests** (17 pure, 16 integration) — cross-doctor visibility, draft
  suppression, the sensitive restriction from both sides, patient scoping, every filter,
  and cursor paging with no repeats or gaps.
- The restriction was confirmed **load-bearing**: emptying `SENSITIVE_DEPARTMENTS` makes
  three disclosure tests fail.
- **0 axe violations** at 1366 and 1280; contrast passed on 79 nodes.
- One real UI defect found and fixed: `display: flex` on a `<summary>` suppresses the
  default `::marker` in Chromium, so the rows had **no affordance at all** — nothing said
  they opened. An explicit chevron is drawn and rotates on open.

**Verification:** **1061 passed**, 1 skipped, 1 known host-only failure.

---

## 15. Patient history — feature 4: the at-a-glance overview card

Five to eight lines at the top of a patient's page: active concerns, medications,
diagnoses, recent abnormal results, last visit and next appointment — each traceable.

### Grounding: code extracts, the model only phrases

Exactly the agreed design, with every part enforced rather than prompted:

1. **Code gathers the facts.** Each gets an id, a source and, where it matters, a label.
   The model never sees a document, a note or a transcript, so it has nothing to invent a
   medication or a diagnosis *from*.
2. **The model may only phrase that list.**
3. **Code verifies afterwards** (`verify_phrasing`): every fact id must come back, and
   every number in the prose must appear in the fact that line cites. Anything missing or
   altered discards the prose **entirely** and the plain structured list is rendered.
4. **Trends are not here at all** — they are SQL.

The card always says which it is showing: *AI drafted* or *Facts only*, with the reason
when verification failed. Presenting the fallback as the summary would hide the one signal
a doctor most needs.

### Labels that are not decoration

| Label | Means |
|---|---|
| **Patient reports** | From the patient's own free text or the triage chat. Never promoted into a diagnosis — nobody clinical has confirmed it. |
| **Reported, unverified** | A medication read off a document the patient uploaded, e.g. another clinic's prescription. **Shown, never hidden**: a drug they are actually taking matters even when this hospital did not prescribe it. It is simply never presented as ours. |

### The disclosure trap this had to avoid

The card sits directly above the timeline that withholds sensitive-specialty notes. A
psychiatry diagnosis appearing here would undo that restriction — and worse than the
timeline leaking it, because **a doctor reads the card and may never scroll**. Facts
derived from a sensitive specialty's note are excluded for doctors outside it, and there
is a test that fails if that filter is removed.

The cache is keyed by **(patient, viewing department)** for the same reason. Keyed on
patient alone it would serve one doctor's card to another and leak a restricted diagnosis
while looking like a performance optimisation.

### The cache is self-correcting

Staleness is decided by comparing the inputs the card was built from against the newest
inputs that exist now (`latest_source_change`), **not** by invalidation hooks in every
writer. A cache that needs every future writer to remember `invalidate()` goes stale the
first time one does not — silently. This is the same failure class as the undeclared graph
keys fixed earlier in this project.

Measured on a real patient: **6.2s cold, 0.01s cached**, and a newly signed note rebuilds
it without any writer knowing the cache exists.

### Verified

- **28 tests** (19 pure, 9 integration). The pure set is adversarial about phrasing: a
  dropped fact, an invented number, a number **borrowed from a different fact**, a
  citation to a fact never supplied, and an uncited line all fail.
- The sensitive-specialty filter was confirmed **load-bearing** — removing it fails two
  disclosure tests.
- A model failure still returns the facts: the card degrades, never errors.
- **0 axe violations** in both modes.

**Verification:** **1092 passed**, 1 skipped, 1 known host-only failure.
