# Hospital Automated Booking System — End-to-End Project Guide

This is a from-the-code explainer of how this system actually works today, including every
guardrail, edge case, and known rough edge that was found while reading the source. It is not
a spec of what was intended — it describes verified, current behavior, with `file:line`
references so you can jump straight to the code. Where the code and `README.md` disagree, that
is called out explicitly rather than silently resolved.

---

## 1. What this system is

A hospital patient-facing chat assistant plus a doctor/admin backend, built as:

- **FastAPI** backend (`app/api/`) serving a JSON/WebSocket API and a small vanilla-JS SPA.
- A **LangGraph** state machine (`app/agents/`) that runs the conversational AI — triage,
  intake questioning, department routing (RAG), home-care remedies, appointment booking,
  document analysis.
- **PostgreSQL** for all relational data (users, doctors, slots, bookings, chat history,
  consults/SOAP notes, tokens, audit logs).
- **Qdrant** for vector search over a clinical symptom→department knowledge base.
- **Azure Blob Storage** for uploaded medical documents.
- **Nginx + certbot** in front, for TLS and reverse-proxying to the backend.
- **Twilio WhatsApp** and a doctor-facing **consult/SOAP-note** subsystem with live audio
  transcription (Deepgram) as secondary channels into the same booking core.

Three personas share one codebase: **patient** (chat + booking), **doctor** (MFA-gated
dashboard, consult recording, SOAP notes), **admin** (doctor/slot/holiday management, analytics).

---

## 2. Request flow, top to bottom

```
Browser / WhatsApp
        |
        v
   Nginx (:8010 today; :80/:443 once HTTPS is redeployed — see the gaps section)
        |
        v
   FastAPI (app/api/main.py)
        |
        +-- /auth, /chat, /appointments, /admin, /doctor, /doctor/consult, /webhooks/whatsapp
        +-- /ws/status/{session_id}   (document-ingestion push)
        |
        v
   LangGraph workflow (app/agents/graph.py) — patient chat only
        |
   supervisor <--> triage_router / conversation_agent / medical_rag / remedy_agent /
                   checkup_report / appointment_booker / document_analyzer / general_qa
        |
        v
   Postgres (source of truth) + Qdrant (department matching) + Azure Blob (documents)
```

Doctor/admin routes talk to Postgres directly through `app/services/*` — they do **not** go
through the LangGraph agent layer at all.

---

## 3. Directory map (what to read for what)

| Area | Path | Approx. lines |
|---|---|---|
| AI agents / LangGraph | `app/agents/` | ~7,700 |
| API routes | `app/api/routes/` | ~2,700 |
| Business logic / data access | `app/services/` | ~6,700 |
| LLM + vision clients | `app/inference/` | ~1,000 |
| DB bootstrap / migrations | `app/db/`, `alembic/` | — |
| Frontend SPA | `app/api/static/` | — |
| Deployment | `Dockerfile*`, `docker-compose.yml`, `nginx.conf`, `*-entrypoint.sh` | — |
| Tests | `test_*.py` (repo root) | 40+ files |

The single biggest files, in order, are `appointment_booker.py` (1,799 lines — the booking
state machine), `appointments.py` (1,491 — all booking SQL), `supervisor.py` (1,386 — routing
brain), `chat.py` (1,154 — streaming + upload endpoints), `consults.py` (1,039).

---

## 4. The LangGraph agent layer

### 4.1 State — `app/agents/state.py`

`GraphState` is a `TypedDict, total=False` — every field optional, **no runtime validation** on
any field. Only one field has a real LangGraph reducer:

```python
# rolling_message_reducer, state.py:6-23
merged = merged[-6:]
if system_messages:
    return [system_messages[0], *merged][-6:]
return merged
```

`messages` is capped at 6 entries and keeps only the *first* system message ever seen. (Subtle
bug: re-slicing `[system, *merged][-6:]` can drop the system message back off once the list
fills up.)

Every other field is "last writer wins." The state carries roughly 60 fields across seven
groups: identity, language, rolling context, routing (`awaiting`, `next_agent`,
`supervisor_checked_input`), clinical intake, remedy, booking, and documents. A handful of keys
that nodes return are **not declared in `GraphState` at all** (`intake_complete`,
`pre_checkup_summary`, `pre_checkup_clinical_note`, `clinical_analysis`, `home_care_advice`,
`report_forwarding_booking_id`, `user_action_summary`, `appointment_resolver_options`) — the
code visibly compensates for this unreliability, e.g. `supervisor.py:966-968` checks **both**
`intake_complete` and a raw question count "to handle state merging issues."

### 4.2 Graph topology — `app/agents/graph.py`

- Entry point: `language_identification` → fixed edge → `supervisor`.
- `supervisor` routes via `route_from_supervisor` (just `state.get("next_agent", "finish")`) to
  any of: `triage_router`, `conversation_agent`, `remedy_agent`, `medical_rag`,
  `checkup_report`, `general_qa`, `appointment_booker`, `appointment_resolver`,
  `continue_current`, `document_analyzer`, or `END`.
- `triage_router` has one **fixed** edge straight to `conversation_agent` — it never returns to
  the supervisor first.
- Every other node returns to `supervisor`.
- `appointment_booker` and `appointment_resolver` are the **same function**, dispatched
  internally on `awaiting == "appointment_resolver"`.
- Compiled with a custom `SQLiteCheckpointer`. **No `recursion_limit` is set**, so LangGraph's
  default cap of 25 super-steps per turn is the outer loop guard.
- Checkpoint `thread_id` is namespaced by patient id (`graph.py:230-235`) specifically to
  prevent cross-user state leakage if `session_id` ever falls back to a shared value.

### 4.3 Supervisor decision order — `supervisor.py:1235-1379`

1. Language-control short-circuit (a switch-confirmation message, no other node runs).
2. **Return-trip guard**: if `supervisor_checked_input` is already `True` this turn, heuristics
   and the LLM router are both skipped — only `_fallback_route_after_node` decides. This is the
   single most important loop-prevention mechanism in the whole graph; it exists because,
   without it, `medical_rag` could re-route to itself forever (a heuristic still seeing "book
   appointment" in the stale `user_input` after the department was already found).
3. Deterministic heuristics (`_heuristic_supervisor_route`, 22 ordered rules — see §6.1).
4. A few fixed special cases (end-chat-after-note-forwarded, pending file → document_analyzer,
   multi-booking → resolver, affirmative remedy-check).
5. Only if nothing above matched: one LLM call (`_generate_supervisor_decision`).

### 4.4 The eight worker nodes

| Node | Fires when | LLM calls | Parse-failure fallback |
|---|---|---|---|
| `language_identification` | every turn, first | **none** — deterministic fastText + script-range detector | falls through to script heuristics, never blocks the turn |
| `triage_router` | new symptoms/illness | 1 (`PatientExtraction`) | `intent="unclear"`, keeps existing symptoms, asks to clarify |
| `conversation_agent` | mid-intake follow-up | 1 (`ConversationDecision`) | scripted next unasked question |
| `medical_rag` | department unknown | 0 direct (RAG service makes its own) | escalates through heuristic → LLM internally |
| `checkup_report` | intake complete, first visit | 2 (clinical analysis + patient-facing summary) | hard-coded "General Physician" + generic advice, via a bare `except:` |
| `remedy_agent` | patient wants home care, or is being asked "did it help?" | 0-1 (deterministic yes/no phrase match tried first) | "Please rest and seek medical care if symptoms are getting worse." |
| `general_qa` | off-topic-but-plausible question | 1 (`GeneralQaDecision`) | **never echoes model text** — fixed out-of-scope string only |
| `appointment_booker` / `appointment_resolver` | any booking menu state | 0-1 (digit/decline matched locally first) | 3-strike retry ladder, then hands off to staff |
| `document_analyzer` | uploaded file pending | 1 (Azure structured extraction, vision fallback) | safe-default JSON, twice-layered |

Every one of these degrades to a **fixed, safe string** rather than propagating an exception to
the user — this is the load-bearing safety property of the whole agent layer.

---

## 5. Guardrails and edge cases — the important part

### 5.1 Turn / iteration caps

| Cap | Value | Where |
|---|---|---|
| Max intake questions | **6** | `conversation_agent.py:57` |
| Max irrelevant-reply streak before moving on anyway | **2** | `conversation_agent.py:58` |
| Booking menu retries before escalating to staff | **3** ("select" → "retry_1" → "retry_2" → escalate) | `appointment_booker.py:1615-1760` |
| Rolling chat window kept in state | **6 messages** | `state.py:20-23` |
| Memory-compaction window | **5 patient turns** (env-overridable) | `memory_policy.py` |
| LangGraph super-steps per turn | **25** (LangGraph default, not overridden) | `graph.py` |
| Booking date-picker window | **7 days**, 8 date options, 24-day internal safety cap | `appointment_booker.py:44,62,71` |

The 6-question cap is enforced **twice** — a no-LLM fast path once the count is hit
(`conversation_agent.py:126-144`) and again as the actual definition of "intake complete"
(`:95-102`), with an explicit code comment: *"MUST ask at least 6 to get thorough clinical
details — do NOT allow early exit based on field collection alone."*

### 5.2 Loop prevention (7 independent mechanisms)

1. `supervisor_checked_input` — the master loop breaker described in §4.3.
2. `final_response` and `next_agent` are **popped every turn** so a stale value can't
   short-circuit the next turn.
3. Any booking-menu state routes straight to `finish` after a node runs, so the same menu is
   never rendered twice in one super-step.
4. Triage has a mid-intake guard that skips the LLM and skips resetting `collected_data` /
   `questions_asked` once intake has already started.
5. The heuristic only re-triages when `questions_asked` is genuinely empty — otherwise a plain
   greeting mid-conversation would wipe collected intake data.
6. The crisis gate (§5.4) deliberately resets `awaiting=None` so the very next message routes
   fresh instead of being swallowed as an answer to an intake question — this fixed a real,
   previously-observed bug where the bot repeated an empathetic response for several turns.
7. An "irrelevant reply streak" safety valve moves on to the next scripted question after 2
   consecutive off-topic replies rather than looping forever.

### 5.3 Repeated-topic avoidance in intake

- Every asked question is bucketed into one of 8 topics (`intake_utils.py:9-41`); the prompt is
  told which topics are already covered, built from **every** question asked so far, not just
  recent ones.
- Independent of what the model outputs, code overrides a duplicate-topic question with the
  next scripted unasked question (`conversation_agent.py:273-279`) — i.e. "if the model returns
  a duplicate-topic question, silently substitute the correct one instead of asking the model
  to fix it."

### 5.4 Severity and crisis escalation

- Triage classifies severity as `mild | moderate | severe | emergency` against 10 listed red
  flags in the prompt.
- **Crisis/self-harm detection is a hard, pre-LLM, phrase-based gate** applied at two separate
  layers (the supervisor heuristic *and* the HTTP streaming boundary in `chat.py`, so no
  streaming fast-path can bypass it). It never depends on the model's own judgment. It is
  deliberately phrase-based rather than matching a bare word like "kill", specifically to avoid
  misfiring on hyperbole like "this pain is killing me." The response names India's KIRAN
  helpline (1800-599-0019) and 112 — **this is India-scoped and must be replaced/extended for
  any deployment covering other regions** (an explicit code comment flags this).
- Severe/emergency severity adds an explicit "see a doctor as soon as possible" note into the
  booking flow.

### 5.5 Schema validation of every LLM output

Every agent parses its LLM's JSON output through a Pydantic model (`PatientExtraction`,
`ConversationDecision`, `RemedyResponse`, `BookingMenuDecision`, `DepartmentDecision`,
`CombinedSupervisorDecision`, `GeneralQaDecision`, `DocumentAnalysisDecision`) — **except** the
`checkup_report` clinical-analysis call, which uses a bare `json.loads` inside a bare `except:`
with a hard-coded fallback dict. Every parser failure has a defined, safe fallback (see the
per-node table in §4.4) — nothing ever surfaces a raw parse error to the patient.

### 5.6 Medical-relevance / scope guardrails

- A 30-term "obviously an inanimate object" filter (`looks_like_non_medical_subject`) strips
  extracted "symptoms" that are actually about a car, wifi, etc. — applied as a backstop after
  the primary defense, which is the triage prompt itself explicitly stating *"a symptom always
  belongs to a living person, never to an object."*
- `general_qa` has a triple fail-safe: if the decision is unparseable, or `in_scope` is false,
  or the answer text is empty, the **only** thing ever shown is a fixed out-of-scope string —
  deliberately never the model's own "let me explain why I can't help," because that text was
  observed in testing to still leak real off-topic content.
- Unsafe non-medical requests (bomb/weapon/hack/kill/poison-making) get a fixed refusal without
  an LLM call.
- Billing/insurance questions get a help-desk redirect, not an LLM answer.

### 5.7 RAG empty/low-confidence handling — `app/services/rag.py`

- No symptoms → immediate `needs_clarification` with no vector search attempted.
- Vector store exception, or zero Qdrant matches, both fall through the **same** chain:
  heuristic-multi-department check → plain heuristic → LLM-over-context.
- `MIN_CONFIDENT_SCORE = 0.65` — anything below this cosine score also escalates through that
  chain, and so does a confident hit that happens to land on the generic "General Physician"
  department (deliberately never "good enough" on its own).
- If two departments both score reasonably close by the rule-based heuristic, the system
  **always** asks the patient to disambiguate rather than picking one silently.
- The optional cross-encoder reranker (`BAAI/bge-reranker-base`) degrades to an unreranked
  top-3 if the library is missing or `predict()` throws — never blocks routing.
- **Known drift**: `rag.py`'s symptom rules can route to Ophthalmology, ENT, and Urology, but
  those three departments are absent from `appointments.py`'s canonical department list — a RAG
  match to one of them will find zero doctors and show an empty list.

### 5.8 Language handling

- Deterministic and local — **never depends on an LLM call**, so a detector failure can never
  block a chat turn (explicit module-level design contract in `language.py`).
- A language switch requires **two consecutive confident detections** once a language is
  already established — a single ambiguous message can't flip the conversation language.
  Exceptions: an explicit "reply in Telugu" request applies immediately, and the very first
  message of a session sets the language immediately at confidence ≥ 0.78.
- Ambiguous short replies ("ok", "yes", "haan") never trigger language detection at all.
- Clinical artifacts (the doctor-facing checkup summary, the clinical note) are **deliberately
  kept in English regardless of conversation language** — two explicit prompt suffixes enforce
  this.
- The localization boundary (`_ensure_patient_response_language`) is explicitly told never to
  translate doctor names, department names, dates, times, numbers, IDs, or markdown structure,
  and if the localizer ever returns an empty string, the original English response is kept
  rather than shown blank.

### 5.9 Prompt-injection / untrusted-input defenses

- **Booking notes are treated as untrusted, LLM-and-patient-sourced text**: control characters
  are stripped, length capped at 4000 characters, and — because forwarding a note can append to
  an existing one — the cap is **re-applied after every append** so repeated forwarding can't
  grow the field unboundedly.
- The highest-consequence transitions (crisis detection, unsafe-content refusal, end-chat
  detection, digit-based menu selection, localized yes/no) are all deterministic pre-LLM
  pattern matches — they do not depend on model output at all.
- `general_qa`'s refusal never echoes model text (§5.6) — the one place a "why can't you help
  me" explanation could otherwise leak an injected instruction back to the user.
- There is **no dedicated instruction-injection detector** for free text fed into the document
  analyzer or summarizer — flagged here as a real gap, not mitigated anywhere in the code.

### 5.10 Token / cost caps on the LLM layer — `app/inference/llm.py`

- Hard token ceilings: 1024 completion tokens for normal generation, 512 for routing/summary
  calls, 120-second timeout per call.
- History is trimmed by *patient* turns, not raw message count, and a rolling `chat_summary` is
  injected as a separate system message instead of raw history — this is what actually bounds
  prompt growth over a long conversation.
- Every call is logged (model, node, latency, status) through a usage-tracking hook — **but
  there is no hard spend/budget cutoff anywhere in this layer.** A cost runaway is only
  detectable after the fact via the usage tables, never prevented in real time.
- When the LLM is fully unavailable (`OPENAI_API_KEY` unset, or every call fails), every agent
  falls back to a canned response rather than raising — but the fingerprint-matching fallback
  table in `llm.py` (`_local_fallback`) is **stale**: most of its prompt-text fingerprints no
  longer match the current prompt wording, so in practice an LLM outage falls through to one
  generic "I am having trouble reaching the language model right now" string, which then fails
  each node's own Pydantic parser and lands in that node's *parse-failure* fallback instead of
  the intended dedicated one. End behavior is still safe, just not the originally-intended path
  — worth fixing if this ever needs to be relied on.

---

## 6. Booking, the database, and concurrency

### 6.1 `appointment_slots` vs `appointment_bookings` — which one is real

**`appointment_bookings` is the single source of truth.** Every availability query in the
codebase checks only:

```sql
AND NOT EXISTS (
    SELECT 1 FROM appointment_bookings b
    WHERE b.slot_id = s.slot_id AND b.status = 'booked' AND b.end_time > NOW()
)
```

`appointment_slots.is_booked` / `booked_by_patient_id` are a **write-only denormalized mirror**
kept in sync after every booking/cancel/reschedule, purely for the admin Slots inventory screen
to read cheaply. `ensure_booking_schema()` (`appointments.py:199-343`, re-run at the top of
essentially every booking function) self-heals this mirror on both sides:

- Backfills a missing `appointment_bookings` row for any slot that's `is_booked=TRUE` with no
  booking row at all (guarding on **any** existing booking row, not just a `'booked'`-status
  one — a subtlety the code comments explain in detail: a slot left `is_booked=TRUE` whose
  booking already completed or was cancelled would otherwise get a spurious duplicate booking).
- Resets `is_booked` back to `FALSE` wherever no live `'booked'` row actually exists.

This mirror-write pattern is also exactly why `app/db/ingest_relational.py`'s CSV re-seed had to
be fixed to **exclude** `is_booked`/`booked_by_patient_id` from its `ON CONFLICT DO UPDATE`
clause — see §8.3.

### 6.2 Booking lifecycle rules

| Rule | Value | Enforced |
|---|---|---|
| Earliest bookable slot | 30 minutes from now | SQL, every availability query |
| Booking window | next 7 days | SQL + re-checked in Python (`_requested_date_within_booking_window`) |
| Cancel / reschedule cutoff | more than 24 hours before start | SQL, on every modify path |
| Reschedule target floor | 24 hours (not 30 min) — you cannot reschedule into the next day | `appointments.py:1121-1122` |
| Sunday closure | no slots generated/offered for Sundays | 3 separate call sites |

`book_selected_slot` **re-validates the entire availability predicate at write time** — the
slot list a patient saw seconds earlier is never trusted. It locks the row with
`FOR UPDATE OF s SKIP LOCKED`: the loser of a race gets zero rows back immediately (no waiting,
no deadlock) and the caller shows "that slot was just taken." A real two-thread race against a
live Postgres instance is covered by `test_appointments_rest_e2e.py`.

Reschedule **updates the existing booking row in place** — the `booking_id` never changes
across a reschedule, and the note is carried over untouched.

Cancellation has **two different code paths** with different strictness:
- `cancel_patient_booking` (used by the patient-facing route) always requires the calling
  patient to own the booking.
- The older `cancel_booking(reference, patient_id=None)` accepts either a booking id or a slot
  id and makes the patient check **optional** — called with no patient id, it can cancel *any*
  patient's booking. This is a real IDOR risk that depends entirely on every caller remembering
  to pass a patient id; flagged as a known gap in §8.

### 6.3 Timezone handling — read this before touching any date/time code

This is the most fragile area in the codebase and **contradicts the README**. All timestamps
are stored as naive `TIMESTAMP` (no timezone) and every SQL comparison uses bare `NOW()` — i.e.
whatever the Postgres server's own clock/timezone happens to be. There is no `AT TIME ZONE`
anywhere, and no `TZ=Asia/Kolkata` set in the Dockerfile, compose file, or entrypoint. The code
comments in `appointment_booker.py` (lines 283 and 338) are explicit that stored values are
*already India-local* and are merely **labeled** `+05:30` for the frontend, not converted.
`README.md:396`'s claim ("timestamps stored in UTC, converted to IST before sending to the
frontend") is **incorrect** as of the current code — this only works correctly if the Postgres
server's own clock is genuinely IST and the seed CSV's times are IST. Date parsing elsewhere
assumes DD/MM/YYYY (India convention), and Python-side date comparisons use the **application
process's** local date rather than the database's, which can disagree by up to 5.5 hours around
midnight IST.

### 6.4 Concurrency — what's handled and what isn't

**Handled**, each independently verifiable in the code:
- Double-booking the same slot (a Postgres partial unique index — at most one `'booked'` row
  per slot, ever — plus row locking plus a re-validated `NOT EXISTS` check).
- Double-consuming a document-upload token (single atomic `UPDATE ... WHERE consumed=FALSE
  RETURNING`).
- Concurrent cancel/reschedule of the same booking (`FOR UPDATE OF b`).
- Concurrent consult start for the same booking (a partial unique index on active-status
  consults).

**Not handled / partial**, worth knowing before scaling this up:
- `ensure_booking_schema` re-runs its full DDL-convergence + full-table reconciliation UPDATE on
  **every single call to almost any booking function** — an O(table) cost paid on every
  request, not just at startup. Under real load this is a genuine bottleneck and a documented
  prior source of a production deadlock (the connection-pool nesting hazard described in
  `app/db/connection.py`'s docstring: calling `connect_db()` again on the same thread while
  already inside one returns the *same* physical connection, and the inner block's exit commits
  and releases it out from under the outer block).
- `first_available_slots` loops one query per doctor (N+1).
- The in-memory rate limiter (§7.2) and the in-memory document-analysis cache (§9) are both
  process-local, unbounded, and reset on restart — they silently stop being correct the moment
  the app runs with more than one worker process/replica.
- `persist_token_log`'s fire-and-forget logging (a background asyncio task or a daemon thread
  per log line) retains no reference and handles no exception — failures are invisible and,
  under load, this spawns unbounded threads in the no-event-loop branch.

---

## 7. Authentication, authorization, and API surface

### 7.1 Three identities, one JWT scheme

Hand-rolled HS256 JWTs (`app/services/tokens.py`, no PyJWT dependency). All three roles share
one verification function; they differ only in claims:

| | Patient | Doctor | Admin |
|---|---|---|---|
| `sub` claim | `users.user_id` | `doctors.doctor_id` | `admin_accounts.admin_id` |
| `role` claim | `"patient"` or absent (legacy) | `"doctor"` | `"admin"` |
| Extra claims | — | `token_kind`, `doctor_id`, `account_id` | — |
| MFA | none | **mandatory** — login cannot complete without it | none |
| Account lockout | yes | yes | yes |

A doctor session token is additionally checked for `token_kind == "doctor_session"` and
`sub == doctor_id`, specifically so an MFA-pending or MFA-enrollment token (which have their
own `token_kind`s and short TTLs — 5 and 30 minutes respectively) can never be used as a full
session token.

**JWT_SECRET has an insecure fallback**: if unset, the app boots anyway using a public,
hard-coded string and logs a loud warning every startup — *"the one remaining real risk"* per
the code's own comment. Treat that warning as a deploy blocker. `JWT_LEGACY_SECRET` supports a
deliberate rotation window (old secret still verifies until tokens issued under it expire).
Tokens are individually revocable by `jti` (a DB table, self-pruning of expired entries on every
insert) — but logout only revokes the **one presented token**, not every session for that
account.

### 7.2 Rate limiting and lockout

- Login/MFA rate limiting is a hand-rolled in-memory sliding window (300 seconds, default 10
  attempts), keyed on **both** client IP and account identifier. It is **per-process** — under
  multiple workers or replicas the effective limit multiplies, and it resets on every restart.
  `/auth/unified-login` keys on account id; `/doctor/auth/login` keys on email — two disjoint
  key spaces, so an attacker effectively gets 10 attempts against each path independently.
  `POST /auth/login` (the legacy patient-only path) and `POST /auth/signup` have **no rate
  limiting at all**, and an unrecognized email in the unified login path never reaches the
  limiter either.
- Account lockout (5 failed attempts → 30-minute lock) is implemented three times — once each
  for patients, doctors, and admins — using `SELECT ... FOR UPDATE` to serialize concurrent
  attempts, deliberately duplicated rather than shared to avoid a circular import.
- Unknown-email login attempts run a dummy password verification anyway so response timing
  doesn't reveal whether the account exists.

### 7.3 MFA (doctors only)

TOTP (30-second interval), Fernet-encrypted secret at rest, QR enrollment, 10 single-use
recovery codes (PBKDF2-hashed). Login replay protection accepts a ±1 time-step clock skew window
but **monotonically consumes** the matched step so the same code can't be replayed even within
its own valid window. A doctor account cannot complete login at all until MFA is enrolled — this
is a hard gate, not a soft nudge.

### 7.4 Notable IDOR defenses (and the two known gaps)

Every patient-facing route resolves `patient_id` from the verified JWT, never from the request
body — this is the core defense against one patient reaching another's data, applied
consistently in appointments, chat history, document status, and upload-token consumption.
Doctors can only ever see patients they have an actual booking history with (`doctor_patient_*`
functions explicitly return `None` → 404 otherwise, "must never see a patient they haven't
treated"). Chat state deliberately never merges client-supplied booking data into the graph
state — only the database is trusted — specifically to prevent one patient's bookings leaking
into a different account's browser session.

The two known exceptions, both because an optional parameter defaults permissively:
- `cancel_booking(reference, patient_id=None)` — omit the patient id and it cancels anyone's
  booking (§6.2).
- `active_bookings_for_patient(patient_id=None)` — omit it and you get every patient's bookings.

Neither is reachable from a current HTTP route with an attacker-controlled missing parameter as
far as the research pass could confirm, but both are foot-guns for any future caller.

### 7.5 Other guardrails worth knowing about

- `/docs`, `/redoc`, `/openapi.json` are disabled unless `ENABLE_API_DOCS=true` — full schema
  (including admin-only models) would otherwise be publicly reachable.
- The Twilio WhatsApp webhook validates an HMAC-SHA1 signature and **fails closed** (missing
  token or header → 403) — but the whole check is disableable via
  `VALIDATE_TWILIO_WEBHOOK=false`, and its URL-reconstruction step trusts `X-Forwarded-*` headers
  unless `PUBLIC_BASE_URL` is explicitly set, which is the load-bearing config for this check in
  production.
- There is **no CORS middleware configured anywhere** — this works today only because the SPA
  is served same-origin; a separately-hosted frontend would need it added explicitly.
- `/ws/status/{session_id}` (the document-ingestion push channel) has **no authentication at
  all** — anyone who obtains a session UUID can read that patient's ingestion events, including
  raw exception text on failure. The UUID's unguessability is the only protection.
- Admin bootstrap (`ADMIN_BOOTSTRAP_ENABLED=true` + `ADMIN_EMAIL`/`ADMIN_PASSWORD`) is
  deliberately opt-in on every boot specifically so a stale value left in an environment can't
  silently reset a real admin's password on a later restart.
- There is **no patient password-reset flow anywhere in the codebase** — a locked-out or
  forgot-password patient has no self-service recovery path today.

---

## 8. Deployment, data seeding, and the fixes made this session

### 8.1 What runs where

`docker-compose.yml` brings up `postgres`, `qdrant`, `backend`, `frontend` (nginx), and
`certbot`. `docker-entrypoint.sh` runs, **on every single container boot, not just the first**:
Alembic migrations → CSV re-seed (doctors + slots) → Qdrant hydration check → start the server.
This was a deliberate move away from a one-time "flag file" gate, because that flag lived in a
different Docker volume than the actual database and could silently desync from it (see the
in-code incident writeup this session's own commits reference).

### 8.2 The three sources of schema truth

Alembic migrations, `app/db/schema.sql` (used only by the full drop/recreate
`rebuild_database.py`), and the `ensure_*_schema()` functions re-run on every request are all
supposed to converge to the same schema, and mostly do — but `schedule_holidays`,
`doctors.is_active`, `appointment_slots.is_active/created_at/updated_at`, and
`appointment_bookings.booking_note` exist only in the runtime DDL and `schema.sql`, in **no**
Alembic migration. A migrations-only deployment path would only get these on the first request
that happens to call `ensure_booking_schema`.

### 8.3 The booking-clobber bug found and fixed this session

Because `ingest_relational_data()` (the CSV re-seed) now runs on every boot instead of once, its
original `appointment_slots` upsert unconditionally overwrote `is_booked` and
`booked_by_patient_id` from the static seed CSV (which has `is_booked=False` for every row) —
meaning **every container restart would silently un-book every live appointment** in the admin's
Slots view, even though the real booking (in `appointment_bookings`) was untouched and still
correctly blocked re-booking. This was fixed by excluding those two columns from the
`ON CONFLICT DO UPDATE SET` clause (`app/db/ingest_relational.py`) — a brand-new slot still gets
seeded correctly on first insert, but re-running the seed against an existing slot no longer
touches its live-mutated booking columns. A regression test
(`test_ingest_relational_preserves_bookings.py`) locks this in against a real database. One
residual risk noted during the fix: `start_time`/`end_time` are still overwritten by the CSV on
every re-seed, and `appointment_bookings.start_time` is a denormalized copy that is **not**
similarly updated — editing the CSV's time for an already-booked slot would desync the two.

### 8.4 HTTPS / nginx / certbot — current state and open risk

The HTTPS/certbot work has landed in this repo (nginx terminates TLS for
`https://165-232-178-215.sslip.io`, an IP-literal sslip.io hostname tied to a specific server
IP) but had **not yet been deployed** to the live server as of this session — confirmed by
direct `curl` probes showing the live server still answering plain HTTP on port 8010 only, with
no redirect. This is very likely why microphone access (which requires a secure browser context)
doesn't work in production yet.

Two things must be resolved before that redeploy, both discovered this session and **not yet
resolved**:
1. An **unrecognized host-level nginx** (`nginx/1.18.0`, the Ubuntu apt package — not the
   Dockerized frontend, which reports `nginx/1.31.5`) is already bound to ports 80 and 443 on
   the live server, returning 404/502 respectively. The new compose file wants the Docker
   `frontend` container to bind those same ports directly — this will conflict until it's
   understood what that host nginx is for.
2. The certbot bootstrap has no retry/restart safety net if the very first certificate request
   fails (nginx not yet listening, DNS not settled, a rate limit, etc.) — see §8.5.

### 8.5 Other known gaps surfaced by code review, not yet fixed

These were found but intentionally left alone this session (out of scope for the immediate
HTTPS fix) — listed here so they aren't lost:

- `_collection_already_hydrated` (Qdrant hydration skip-check) compares **row count only**, not
  content — editing the clinical CSV's text without changing its row count is invisible, and
  stale embeddings are served indefinitely with no warning.
- The bootstrap self-signed placeholder TLS certificate is generated with a 24-hour validity and
  is never regenerated after container start — if certbot never succeeds, nginx serves an
  **expired** certificate indefinitely with no automatic recovery.
- `nginx.conf`'s port-80 redirect target is hardcoded to the production sslip.io hostname rather
  than `$host`, which silently breaks the README's own documented local-dev health-check flow
  on any non-production checkout.
- `LETSENCRYPT_EMAIL` has no fail-fast validation, unlike `POSTGRES_PASSWORD` (which the same
  changeset hardened with a `:?` guard in `docker-compose.yml`).
- The CSV re-seed's full-table `UPSERT` sets `updated_at = NOW()` unconditionally on every boot,
  even when nothing changed — real WAL/autovacuum churn on every restart, and a misleading
  `updated_at` for anything downstream that treats it as "last genuinely modified."
- `FULL_SYSTEM_AUDIT.md` and `TECH_DEBT.md` are referenced by name in roughly a dozen code
  comments across the codebase but **do not exist in this repository** — whoever wrote those
  comments had them at the time; they should either be recovered or the references removed.

---

## 9. Document upload pipeline (the other AI-heavy feature)

Two separate ingestion paths exist and are easy to conflate:

1. **Inline chat-turn uploads** (`app/services/document_pipeline.py`) — extracted synchronously
   during a `/chat/stream` multipart request, cached in memory
   (`_doc_analysis_cache`, an unbounded, process-local, no-TTL dict — a real gap under a
   multi-worker deployment or an abandoned session), analyzed immediately.
2. **Consent-gated vault uploads** (`POST /chat/upload` → `/chat/confirm-processing`) — staged
   to Azure Blob, held behind a single-use 30-minute token, only moved into the permanent vault
   and processed in the background **after** explicit patient consent. A GPT-4o relevance check
   gates this path and **fails closed** — if the verifier is unreachable, the upload is rejected
   outright rather than silently accepted.

Both paths share: a 15 MB size cap and an MIME allowlist (PDF/JPEG/PNG) that trusts the
client-declared content type (no magic-byte sniffing); a keyword-based "does this look medical"
gate for text-bearing PDFs (image-only scanned PDFs slip past this specific check, relying on
the GPT-4o gate instead where that path applies); path-traversal-safe filename sanitization; and
a clinical-grounding system prompt for question-answering over documents that mandates exact
transcription of numeric values and forbids inventing or adjusting doses.

---

## 10. Glossary of the files you'll touch most often

| File | What it's for |
|---|---|
| `app/agents/supervisor.py` | The routing brain — read this first for "why did it do X instead of Y" |
| `app/agents/state.py` | Every field the conversation carries between turns |
| `app/services/appointments.py` | All booking SQL — availability, book, cancel, reschedule |
| `app/services/rag.py` | Symptom → department matching |
| `app/api/routes/chat.py` | Streaming chat endpoint, uploads, the WebSocket/NDJSON transport |
| `app/api/dependencies.py` | The three `current_user`/`current_admin`/`get_current_doctor` guards |
| `app/services/tokens.py` | JWT issue/verify/revoke |
| `app/db/ingest_relational.py` | CSV seed data → Postgres (fixed this session, see §8.3) |
| `docker-entrypoint.sh` | What actually happens on every container boot |
| `nginx.conf` | Reverse proxy + TLS termination rules |

---

*Generated from a direct, file-by-file reading of the codebase as of this session — not from
README claims alone. Where README.md and the code disagreed (the IST/UTC storage claim in
§6.3), the code's behavior is what's documented here.*
