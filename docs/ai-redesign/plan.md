# AI-driven Doctor Workspace redesign — implementation plan

Status: **awaiting approval. Nothing below has been implemented.**

Baseline established first: `feature-inventory.md` (605 passed / 1 pre-existing
environmental failure / 1 skipped).

---

## 0. Decisions I need from you before starting

These are the points where the standards (`Claude Standards/engineering-standards.md`
§"Requirements & ambiguity" — *stop and ask*) say I must not guess. Numbered so you can
answer by number.

### D1 — The standards' Repository Commands are blank

`Claude Standards/CLAUDE.md` lists Install / Tests / Lint / Format / Type check / Security
scan / Migrations / Build as `TBD`, and says: *"Rule 7 and the Definition of Done are
unenforceable without them. If a command is missing or fails, say so rather than
substituting a guess."* I am saying so.

What actually exists in this repo: **pytest only.** There is no `package.json`, no ruff,
flake8, mypy, black, pre-commit, eslint, Playwright, Selenium or axe, and no build step
(the frontend is served as static files, never compiled).

So the task's §6 requirement to *"run the full existing suite together with the linter, the
type checker and the build"* cannot be satisfied as written — those three do not exist.

**Options:**
- **D1-a (recommended).** Keep the change to the app itself. Fill in the standards'
  Repository Commands with the real ones (`Tests:` the pytest line below; `Lint/Type
  check/Build:` "none configured"). I report lint/types/build as *not available*, which
  is what the testing standard §Verification explicitly asks for.
- **D1-b.** I additionally introduce ruff + mypy as dev dependencies and get the existing
  ~600-test codebase clean under them. That is a large, unrelated diff across the whole
  repo and directly contradicts "do not touch unrelated code" — I do not recommend it as
  part of this task.

### D2 — There is no e2e or accessibility tooling

§6 asks for browser e2e flows, an axe accessibility check, and 1280px comparison
screenshots. All three need a browser driver this repo has never had.

Note that "e2e" in *this* codebase means something specific and different: the existing
`test_*_e2e.py` files are pytest + `TestClient`/httpx tests against the FastAPI app
(see `test_soap_note_e2e.py`'s header). That is "the project's existing e2e tool".

**Options:**
- **D2-a (recommended).** Write the five §6 flows as API-level e2e tests in the existing
  pytest style — they genuinely prove the *behaviour* and the safety invariants (sign,
  regenerate, approve/lock, share, per-doctor isolation). Accept that no automated check
  covers rendering, axe or screenshots; I build accessibility in by construction
  (semantic buttons/links, labels, `aria-label`, focus states, 44px targets) and state
  plainly in the verification report that it was **not** automatically verified.
- **D2-b.** Add Playwright + `axe-core` as a new dev dependency, which brings a Node
  toolchain into a repo that has none. This is a real, defensible addition (it is the only
  way to satisfy §6 literally) but it is a significant new dependency surface on a
  clinical app and a decision that is yours, not mine.

I will do whichever you pick. I will **not** claim a browser/axe/screenshot check ran if
it did not.

### D3 — Web fonts (Bricolage Grotesque / Geist / Geist Mono)

The app currently loads **zero** external resources — no CDN, no Google Fonts, system font
stacks only (`styles.css:51`). The design files pull all three families from
`fonts.googleapis.com`.

Adding that makes every doctor's browser call Google on every page load: a third-party
dependency and a privacy signal on a clinical app, and it breaks on an offline/restricted
network. Against `security.md` §Privacy and §Third-party integrations, I will not add it
silently.

**Options:**
- **D3-a (recommended).** Self-host the three families as woff2 under
  `app/api/static/vendor/fonts/` (~150–250 KB subset). No external calls, works offline,
  exact design typography.
- **D3-b.** Load from Google Fonts CDN (matches the design file literally; external
  dependency + privacy leak).
- **D3-c.** Keep system stacks and apply the design's *roles* (display / body / mono)
  without the specific families. Zero cost, visibly different from the design.

### D4 — Does Sign block on unresolved flags, or only warn? (§4.6)

You asked me to recommend and then ask.

**Recommendation: warn, do not block** — with blocked (`stale`) notes staying hard-blocked
regardless, which is already enforced in the service layer at `soap_notes.py:557` and is
not negotiable.

Why warn rather than block:
- `confidence_flags` is *model self-assessment*, not a clinical fact. A doctor who has
  read the transcript and is satisfied is the higher authority; a hard block would make
  the model's uncertainty override a clinician's judgement, which inverts the "AI drafts,
  you decide" principle the whole redesign is built on.
- It is trivially gameable: blocking on flags pushes doctors to clear flags to get the
  button back, which is worse than an honest warning.
- A flagged-but-correct field is common; an unsignable note would strand real work.

So: Sign stays enabled, the confirm step names the unresolved flags explicitly
("2 sections still flagged — sign anyway?"), and the count is recorded in the audit row.
**Please confirm D4, or tell me to block instead.**

### D5 — Ask AI (§4.8) scope

Honest assessment: a safe "ask anything about your patients" endpoint needs
authorization-filtered retrieval (`security.md` §RAG: *"Retrieval never bypasses
authorization… enforce access rights inside the retrieval query via metadata filtering"*),
per-doctor cost/rate caps, prompt-injection defence against hostile document content, and
source attribution on every claim. That is its own project, not a sub-bullet.

**Recommendation:** build the command bar UI (⌘K, focus trap, keyboard nav, empty/error
states) behind a feature flag **default-off**, wired to nothing. Ship the real retrieval
as separate work. §4.8 explicitly permits this. Confirm and I will do that.

### D6 — Two small design/palette conflicts

- `ai-theme.css` uses `--border:#E6E0FB` with a separate `--border-strong:#DDD6FE`. Your
  §3 instruction says keep `border #DDD6FE`. **I will keep the existing `--border:#DDD6FE`**
  (your instruction + the existing token) and add `--border-strong` only if a component
  needs it. Say if you want the design file's softer border instead.
- `ai-theme.css` has `--muted-fg:#5F6488`; the app has `#6B7094`. §3 says keep the existing
  palette exactly, so **I keep `#6B7094`.**

---

## 1. What the architecture actually is (and what that means)

The doctor workspace is **not** a component framework. It is:

- `app/api/static/index.html` — one 92 KB document; the doctor workspace is a `<section>`
  of `admin-view-pane` panes (lines 174–560)
- `app/api/static/app.js` — one 326 KB IIFE; doctor logic is roughly lines 1095–3050,
  plain `render*()` functions doing direct DOM manipulation
- `app/api/static/styles.css` — 82 KB, already has the exact palette as `:root` custom
  properties (lines 6–45)

Consequences that shape everything below:
- "Component tests for every new and redesigned screen" (§6) has no framework to hang on.
  Covered by D2.
- Per `engineering-standards.md` §"Existing architecture first", I will **follow this
  structure** — new panes in `index.html`, new `render*()` functions in `app.js`, new
  tokens in the existing `:root`. I will not introduce React/Vue/a build step to a
  clinical app as a side effect of a redesign.
- The redesign is therefore *substantial but conventional*: new markup + new render
  functions + new CSS, reusing the existing auth/fetch helpers (`doctorAuthedJson`,
  `app.js:1099`).

---

## 2. New features: what each needs

Legend: **[E]** buildable entirely from existing data · **[B]** needs new backend work.

| § | Feature | Data source | Verdict |
|---|---------|-------------|---------|
| 4.1 | AI activity summary | `consult_audit_log` (`consult_soap_note_generated`), `patient_documents` (`ingestion_status='complete'`), `confidence_flags`, `status='stale'` | **[B]** — data exists; needs a *previous* login timestamp (see S1) + a new endpoint |
| 4.2 | Prioritised next actions | `list_reviews_for_doctor` already returns `is_stale`, `low_confidence_fields`, `low_quality_transcript`, `appointment_start`, `item_type` | **[E]** — pure ranking function over an existing payload |
| 4.3 | AI activity log | `consult_audit_log` — **already exists** (`consults.py:98`), written by every note/item action | **[B]** — needs a doctor-scoped query + index (S2); no new event source required |
| 4.4 | Today's schedule + AI status | `/doctor/appointments` already joins `consult_status`; note status from the reviews payload | **[E]** |
| 4.5 | Review inbox lanes | Same three flags as 4.2 | **[E]** for lanes/chips; **[B]** for "Draft all missing notes" bulk action (S3) |
| 4.6 | Note verification workflow | `field_citations`, `confidence_flags` exist; "verified" per section does not | **[B]** — new persistence (S4) |
| 4.7 | AI assistant side panel | `ai_model`, `ai_prompt_version`, `generated_at`, `confidence_flags` all exist | **[E]** except the "Ask about this consultation" input → D5 |
| 4.8 | Ask AI command bar | — | **[B]**, feature-flagged off → D5 |
| 4.9 | AI patient brief | Signed notes + document summaries, both already doctor-scoped | **[B]** — new compose endpoint (S5) |
| 4.10 | Insert from plan | Signed note's `plan` text, client-side parse into the textarea | **[E]** |
| 4.11 | Audit trail (Signed & shared) | `consult_audit_log` rows + `generated_at`/`signed_at`/`shared_with_patient_at` | **[E]** given S2's doctor-scoped read |

### Schema changes

One migration, `alembic/versions/0022_doctor_workspace_ai.py`
(`down_revision = "0021_soap_ai_provenance_and_clinical_items"`). All additive and
reversible — no data loss, no column drops, safe under rolling deploy. Mirrored in the
runtime `ensure_*_schema()` helpers, matching this repo's existing dual-source convention
(`soap_notes.py:71–76`).

- **S1** `doctor_accounts.previous_login_at TIMESTAMP NULL`.
  `last_login_at` exists but is overwritten *during* login, so by the time the overview
  renders it already says "now" — it cannot answer "since your last session". The MFA
  challenge (`doctor_auth.py:289`/`297`) will copy the old `last_login_at` into
  `previous_login_at` in the same UPDATE. Null (first ever login) falls back to 24h, as
  §4.1 specifies.
- **S2** `CREATE INDEX idx_consult_audit_doctor ON consult_audit_log(doctor_id, created_at DESC)`.
  The only index today is on `(consultation_id, created_at)` (`consults.py:106`); a
  doctor-scoped feed would full-scan without this.
- **S3** `soap_note_section_verifications` — `(soap_note_id, section CHECK IN (s,o,a,p),
  verified_by, verified_at)`, unique on `(soap_note_id, section)`. Separate table, not four
  columns on `soap_notes`: it is per-section, per-doctor, append-only audit-shaped data,
  and it must never touch the signed clinical content.
- **S4** `doctor_bulk_actions` — `(doctor_id, action, window_start, count)` for the §4.5
  bulk-draft rate limit. *Alternative:* reuse the existing `rate_limit_events` table +
  `check_rate_limit()` (`doctor_auth.py`) with a new `"bulk_draft"` scope — **this is what
  I recommend**, since it reuses a proven, multi-worker-correct limiter and adds no table.
  Then S4 is dropped entirely.

### New endpoints (all behind `get_current_doctor`, all doctor-scoped in SQL)

| Endpoint | Purpose | Notes |
|---|---|---|
| `GET /doctor/ai/activity-summary` | §4.1 counts + headline | Window = `previous_login_at` or `now()-24h` |
| `GET /doctor/ai/activity-log?limit=` | §4.3 feed | From `consult_audit_log`, `doctor_id` in the WHERE, limit clamped (default 25, max 100) per this repo's `REVIEW_*_LIMIT` convention |
| `POST /consult/{id}/soap/sections/{section}/verify` | §4.6 | Rejects if note is `signed`; idempotent |
| `POST /doctor/reviews/draft-all` | §4.5 bulk | Rate-limited + **idempotent**: skips any consult that already has a note, caps the batch, returns per-item results |
| `GET /doctor/patients/{id}/ai-brief` | §4.9 | Signed notes + document summaries only; **never** unsigned drafts |
| `POST /doctor/ai/ask` | §4.8 | **Not built** unless D5 says otherwise |

Ranking (§4.2), lane grouping (§4.5), brief source selection (§4.9) and plan parsing
(§4.10) go in a new pure-Python module `app/services/doctor_workspace.py` so they are
unit-testable without a database — matching how `_low_confidence_count` is already tested
in isolation.

**Ranking rule (deterministic, documented, as §4.2 requires).** Sort key, ascending:

```
(0 if is_stale else 1,                      # 1. blocked first
 -(low_confidence_fields + (2 if low_quality_transcript else 0)),   # 2. most flags
 appointment_start,                          # 3. oldest waiting
 0 if item_type != 'not_generated' else 1,   # 4. undrafted last
 consultation_id)                            # deterministic tie-break
```

The final `consultation_id` term guarantees a total order, so the list never reshuffles
between identical loads.

---

## 3. Files

**Changed**
- `app/api/static/styles.css` — add `--ok/--ok-bg/--warn/--warn-bg/--bad/--bad-bg`,
  `--r-18`, font-role tokens to the existing `:root`; new component classes; responsive
  rules to tablet
- `app/api/static/index.html` — rebuild the doctor panes (dark sidebar, top bar, new
  Overview / Reviews / Note / Patient panes)
- `app/api/static/app.js` — new `render*()` functions; rework existing doctor renderers
- `app/api/routes/doctor.py` — the new doctor endpoints
- `app/api/routes/consult.py` — the section-verify endpoint
- `app/services/doctor_auth.py` — carry `previous_login_at` (S1)
- `app/services/consults.py` — `ensure_consult_schema` gains the S2 index

**Added**
- `app/services/doctor_workspace.py` — ranking, lanes, activity counts, brief composition, plan parsing
- `app/services/soap_sections.py` — section verification persistence
- `alembic/versions/0022_doctor_workspace_ai.py`
- `app/api/static/vendor/fonts/` (D3-a)

**Untouched:** every existing service's clinical logic. The redesign adds read models and
UI; it does not rewrite `soap_notes.py`'s or `clinical_items.py`'s state machines.

---

## 4. Test plan

**Unit** (no DB, `app/services/doctor_workspace.py`): ranking order incl. every tie-break
and total-order determinism; lane grouping incl. an item that qualifies for two lanes;
activity counts incl. the null-`previous_login_at` 24h fallback; verification progress
(0/4 … 4/4); brief source selection — **asserting an unsigned draft is excluded**; plan
parsing incl. empty plan, no medication lines, and malformed input.

**Integration/API** (real Postgres, existing convention): each new endpoint's happy path,
empty state, and **doctor A cannot read doctor B's** activity log / brief / verification
state; bulk-draft idempotency (running twice drafts nothing the second time) and its rate
limit; section-verify rejected on a signed note.

**Safety invariants (§5) — one named test each:**

| Invariant | Test |
|---|---|
| AI output never reaches record/patient unsigned | extends `test_soap_note_sharing_integration.py::test_an_unsigned_note_can_never_be_shared` |
| Patient view shows no clinician-only signals | existing `::test_patient_projection_never_carries_clinician_only_signals` + a new assertion that the brief/verification fields never enter that projection |
| Blocked notes unsignable via UI **and** API | existing `::test_sign_soap_note_rejected_when_stale` + a new route-level test |
| Approved clinical actions read-only both layers | existing `::test_approval_is_one_way_and_locks_the_record` |
| Doctors see only their own data (incl. new endpoints) | new per-endpoint cross-doctor tests |
| AI never generates dosing/interaction/formulary advice | existing `test_clinical_items.py::test_detailed_style_still_forbids_inventing_content` + a test that Insert-from-plan **copies without validating** |
| Everything AI-generated is labelled | assert the AI-labelling flags on every new payload |

**Regression:** the full suite must stay at 605 passed. No existing test is weakened,
skipped or deleted; if one legitimately must change I stop and ask first (§6).

---

## 5. Risks

1. **Single-file frontend.** ~2 000 lines of doctor JS in a 326 KB shared file with no test
   safety net. A careless edit silently breaks the patient or admin experience.
   *Mitigation:* additive render functions, keep existing element IDs where behaviour is
   unchanged, commit per screen so any break bisects cleanly.
2. **No UI test coverage at all** (D2). The single largest risk in this task and the reason
   D2 matters — without it, "every existing feature still works" rests on manual checking.
3. **`ensure_*_schema()` + Alembic dual source.** This repo maintains both. Getting them out
   of step would make a fresh database diverge from a migrated one. *Mitigation:* write both
   in the same commit, exactly as revision 0021 did.
4. **Connection-pool reentrancy.** `soap_notes.py:519–528` documents a real incident: a
   nested `connect_db()` inside an open block returns the *same* physical connection and
   commits it early. Every new service function must take a cursor or open exactly one block.
5. **Bulk draft cost.** "Draft all missing notes" triggers N LLM calls. Uncapped, that is a
   cost and latency incident. *Mitigation:* hard batch cap, rate limit, idempotency, bounded
   concurrency (`engineering-standards.md` §Scalability).
6. **Activity-log disclosure.** `consult_audit_log.metadata` is free-form JSONB written by
   several call sites. Surfacing it raw could leak more than intended. *Mitigation:*
   project an explicit allowlist of fields per `action_type`, never `SELECT metadata` into
   the response wholesale.
7. **Timezone.** The stack is pinned to `Asia/Kolkata` with naive timestamps by deliberate
   design (`docker-compose.yml:4–11`). "Since last login" and "today" must use the same
   convention or counts will be silently wrong by 5.5 hours.

---

## 6. Delivery

Feature branch `feat/doctor-ai-workspace` off `dev`. The standards say nothing about PR
splitting, so per §7: tokens/theme → shell/navigation → Overview → Reviews → Note →
Patient detail → Clinical actions → Signed & shared → each new feature, each commit
self-contained with its tests.

**Note:** the working tree currently has 11 modified and 12 untracked files from prior
work (new `clinical_items`/`document_storage` services, migration 0021, six test files).
I have not touched them. Tell me whether to branch on top of them as-is or have you commit
them first — I would rather not fold someone else's in-progress work into my commits.

## 7. Proposed Repository Commands (for D1)

```
Install:    .venv/Scripts/pip.exe install -r requirements.txt
Tests:      DATABASE_URL=postgresql://postgres:<pw>@127.0.0.1:5433/hospital_db \
              .venv/Scripts/python.exe -m pytest tests -q
Migrations: .venv/Scripts/alembic.exe upgrade head
Lint/Format/Type check/Build/Security scan: none configured (see D1)
Known landmines:
  - Host :5432 is an unrelated native Postgres. The app's DB is the container's, on :5433.
    Without the DATABASE_URL override every DB test skips silently and green means nothing.
  - tests/test_multilingual.py fails on the host: models/lid.176.bin (131 MB) exists only
    in the container.
  - Never nest connect_db() inside an open connect_db() block (soap_notes.py:519).
  - Schema lives in BOTH Alembic and runtime ensure_*_schema() helpers. Change both.
```
