# Triage chat investigation — wrong department, ignored request, stuck turn

Investigation only. **No production code has been changed.**

Evidence sources: source reading, the live `chat_messages` table, the LangGraph
checkpoint store (`/app/data/checkpoints.sqlite`), the doctors table, and direct
execution of the matching functions against the exact strings typed.

Container logs for the incident are **gone** — `docker compose up --build` recreated the
container. Where that matters, it is stated rather than guessed around.

---

## 0. Headline

| # | Issue | Verdict |
|---|---|---|
| A | The "stuck" turn | **The backend answered it.** The reply was generated and saved. The browser never showed it. Not a loop, not a crash. |
| B | Psychiatrist request ignored | `requested_department = "Endocrinology"` is **sticky in session state** and nothing the user typed could dislodge it. |
| C | Misspellings | Matching never even reached the fuzzy matcher. Correctly-spelled **"psychiatrist" also fails.** |
| D | "anxiety, insomnia" | **Not hallucinated.** The patient typed them at 15:55:25. |
| E | "direct booking" label | **Label was right.** The booking code prints a triage-style sentence. |

The system *did* identify Psychiatry. Checkpoint 92 contains
`candidate_departments … department Psychiatry confidence …` while
`target_department = Endocrinology`. The right answer was computed and discarded.

There **is** a Psychiatry department, with exactly one doctor: **Dr. Sunita Panday** —
the physician who referred the patient. There is **no** Psychology department.

---

## 1. Flow map

```
app/api/static/app.js
  sendMessage()                    ~6866   raw fetch("/chat/stream") — NO timeout
  readChatStream()                 ~4090   handles start_response | token | final | error
        │
app/api/routes/chat.py
  chat_stream()                    ~POST /stream
    event_stream()
      ├─ fast path: cached document  → gpt4o_stream_analysis (bypasses the graph)
      ├─ crisis gate                 → looks_like_crisis_or_harm
      ├─ Path A: awaiting=conversation → conversation_agent_stream
      ├─ Path B: new symptoms          → triage_intake_stream
      └─ Path C: everything else       → _run_chat_with_usage()      :231
                                          └─ arun_patient_chat()     :262
        │
app/agents/graph.py
  language_identification → supervisor → (conditional) → node → supervisor → END
  compiled with SQLiteCheckpointer; ainvoke() called with NO recursion_limit  :192-247
        │
app/agents/supervisor.py
  _heuristic_supervisor_route()    :352   pre-LLM fast paths
  awaiting ∈ {doctor_selection,…}  :613   → appointment_booker, NO LLM, NO intent check
  _extract_requested_department()  :139   free-text → department
        │
app/services/appointments.py
  DEPARTMENT_ALIASES               :11
  CANONICAL_DEPARTMENTS            :36
  normalize_department_name()      :75    fuzzy, cutoff 0.78
        │
app/agents/appointment_booker.py
  appointment_booker_node()        :1509  (sync def)
  menu parser → generate_text()    :1009  1 LLM call per menu turn
  retry ladder                     :1715  doctor_selection → retry_1 → retry_2 → escalate
  "Based on your symptoms (…)"     :1243
  no-doctors fallback              :1124  → General Physician
```

---

## 2. Root causes

### A. The stuck turn — the backend answered; the browser never showed it

**The turn completed successfully.** From `chat_messages`:

```
16:13:48 [patient  ] But I want to see a physcologist
16:13:48 [assistant] You asked for the **Endocrinology** department.
                     Here are the available doctors: …
```

And checkpoint `rowid=85` for that turn shows `next_agent = finish`, `awaiting =
doctor_selection`, with a populated `final_response`. The graph ran to `END`, produced
text, and persisted it.

So the three hypotheses in the brief are all **disproved**:

- **Not an infinite loop.** The retry ladder terminates: `doctor_selection → retry_1 →
  retry_2 → escalate` with `awaiting=None` (`appointment_booker.py:1715-1740`). The
  preceding turn ran the identical path in **2.5 seconds** (checkpoints 81→84,
  ts 208.68→211.16).
- **Not a swallowed exception.** Path C wraps the graph call and emits
  `_stream_event("error", …)`; `readChatStream` throws on `type === "error"`. An
  exception would have surfaced as a visible message.
- **Not the missing Psychology department.** An unmatched department degrades gracefully
  to General Physician with an explanatory message (`appointment_booker.py:1124-1172`).

**What actually failed** is delivery between the server finishing and the browser
rendering — the NDJSON stream, the connection, or the final event. **I cannot identify
which, because the container logs were destroyed by the rebuild.** I am not going to
invent a mechanism.

**What makes it permanent is certain, though.** `sendMessage` calls `fetch("/chat/stream")`
with **no `AbortController` and no timeout** — unlike `authedJson` and `doctorAuthedJson`,
which both use 15s. So any delivery failure leaves the typing indicator spinning forever
with no error and no recovery. That is a genuine defect independent of the trigger.

Worth noting for worst-case latency: `_TIMEOUT = 120s` per OpenAI call
(`llm.py:36`), the OpenAI SDK retries by default, and `ainvoke` is called with **no
`recursion_limit`** so LangGraph's default of 25 applies. A pathological turn could
legitimately take many minutes — and the UI would show dots throughout.

### B. Why "psychiatrist" was answered with Endocrinology

Two independent mechanisms, both confirmed.

**1. `requested_department` is sticky.** Checkpoint 92:

```
target_department    : Endocrinology
requested_department : Endocrinology   (department_match_source: llm)
candidate_departments: … Psychiatry …  ← correctly identified, then ignored
active_intent        : direct_booking
awaiting             : doctor_selection
```

Set once from the lab report (high cortisol → Endocrinology), it persists across turns.
Nothing the user typed overwrote it, because (C) extraction returned `None` every time.
The proof is in the final reply's wording — `"You asked for the **Endocrinology**
department"` is the `elif requested_department:` branch at
`appointment_booker.py:1241`. The system believed Endocrinology was the user's *own
request*.

**2. The supervisor never looked.** `supervisor.py:613` — when `awaiting` is
`doctor_selection` (or any menu sub-state), it returns `_route("appointment_booker")`
immediately, **skipping the LLM intent check entirely**. The comment says this is to
"skip the LLM when the user is simply picking from a menu we showed them." But the user
wasn't picking from the menu — they were rejecting it. There is no escape hatch for a
user who changes their mind mid-menu.

### C. Misspellings — the fuzzy matcher is unreachable

Executed directly against the real functions:

```
_extract_requested_department("can i see a phyciatrist ?")       -> None
_extract_requested_department("But I want to see a physcologist")-> None
_extract_requested_department("i want to consult with physcitarist") -> None
_extract_requested_department("can i see a psychiatrist?")       -> None   ← correctly spelled
_extract_requested_department("I want the Psychiatry department")-> 'Psychiatry'
```

**Correctly-spelled "psychiatrist" fails too.** This is not a spelling problem; it is a
matching problem that spelling merely exposed. `_extract_requested_department`
(`supervisor.py:139`) does only two things:

1. four regexes that **all require the literal word "department"**
2. a substring check for exact canonical names — and `"psychiatry"` is **not a substring
   of `"psychiatrist"`** (…t-r-**y** vs …t-r-**i**-s-t)

`normalize_department_name` *does* have fuzzy matching (`get_close_matches`, cutoff 0.78)
and handles the word correctly — but it is only called on text the regexes already
captured, so free-text phrasing never reaches it:

```
normalize_department_name("psychiatrist") -> 'Psychiatry'   ✓ works, never called
normalize_department_name("phyciatry")    -> 'Psychiatry'   ✓ fuzzy catches this
normalize_department_name("phyciatrist")  -> 'Phyciatrist'  ✗ just below cutoff
```

**It also fabricates departments.** For unmatched input it title-cases the user's words
and returns them as if they were real:

```
"physcologist" -> 'Physcologist'     "physiatrist" -> 'Physiatrist'
"psycologist"  -> 'Psycologist'      "mental health" -> 'Mental Health'
"therapist"    -> 'Therapist'        "counsellor"  -> 'Counsellor'
```

None of these exist. `DEPARTMENT_ALIASES` (`appointments.py:11`) has **no** entry for
`psychiatrist`, `psychologist`, `physiatrist`, `mental health`, `therapist` or
`counsellor` — only `"psych": "Psychiatry"`.

On **"physiatrist"** specifically: it is not mapped to anything, and the assistant
explaining physical-medicine-and-rehab was the general QA path answering the question as
asked. Given the referral was *from a psychiatrist* and the symptoms were anxiety and
insomnia, context should have overridden the literal reading — but no department matcher
consults conversation context at all.

### D. "anxiety, insomnia" — not invented

From `chat_messages`, 18 minutes before the Endocrinology reply:

```
15:55:25 [patient] I am feeling anxiety from past few days and unable to sleep
```

The symptoms were extracted from the patient's own words, stored in `state["symptoms"]`,
and rendered by `appointment_booker.py:1243`:

```python
intro = f"Based on your symptoms ({symptom_text}), I recommend the **{department}** department."
```

where `symptom_text = ", ".join(symptoms)` (`:1031`). **The model did not fabricate
this.** The real fault is that anxiety + insomnia → Endocrinology, when the same state
already held Psychiatry as a candidate.

I could not capture the exact prompt sent for that turn — it is not persisted, and the
logs are gone. Reproducing with temporary prompt logging would be needed for that.

### E. Intent label — correct, but the copy contradicts it

`active_intent = "direct_booking"` in the checkpoint, and the header renders
`activeIntent.replaceAll("_"," ")` (`app.js:6346`). The label was accurate.

The confusion is that the **booking** node emits a **triage-style** sentence — "Based on
your symptoms (…), I recommend the … department" — so it reads like triage while the
system is in booking. Intents transition via `update_active_intent` in the supervisor's
LLM JSON (`supervisor.py:60`), but as shown in (B) that LLM never ran for these turns.

---

## 3. Are they connected?

**B, C and D are one failure chain.** The lab report set Endocrinology → it stuck as
`requested_department` → every attempt to change it failed extraction (C) → the booker,
seeing a "requested" department, re-offered Endocrinology and justified it with the
patient's real symptoms (D). The user's correction was structurally incapable of landing.

**A is separate.** The hung turn ran the same path as the one before it and succeeded on
the server. Its cause is in delivery, not in the agent. The two coincide only in that the
delivery failure hid a reply that would itself have been wrong.

---

## 4. Proposed fixes, ranked

Nothing below is implemented. Awaiting your approval.

**P1 — Frontend timeout on `/chat/stream`.** Add an `AbortController` (matching the 15s
pattern used elsewhere, longer for streaming) plus a watchdog if no token arrives within
N seconds. Fixes the permanent-dots class of failure regardless of cause. *Smallest
change, highest user impact.*

**P2 — Let an explicit request override a sticky one.** Re-run department extraction on
every turn; when it yields a department that differs from `requested_department`, clear
the menu state and re-resolve. Add an escape hatch to the `supervisor.py:613` fast-path
so a menu sub-state is not a trap.

**P3 — Make matching actually work.** Route free text through
`normalize_department_name` rather than gating it behind "department"-keyword regexes;
add practitioner→specialty aliases (`psychiatrist`, `psychologist`, `therapist`,
`counsellor`, `mental health` → Psychiatry; `physiatrist` → explicitly unavailable);
and **stop fabricating department names** — return `None` on no match so callers can ask
a clarifying question.

**P4 — Use `candidate_departments`.** Psychiatry was already computed with a confidence
score and discarded. When a candidate conflicts with the document-derived department,
ask: *"Your report suggests Endocrinology, but you mentioned anxiety and sleep — would
you prefer Psychiatry?"*

**P5 — Observability.** Set an explicit `recursion_limit` on `ainvoke`; add a timeout to
the `AsyncOpenAI` client in `azure_client.py:47` (it has none, unlike `llm.py`); log
per-turn intent, resolved department and match source so this is diagnosable without
archaeology.

**P6 — Copy.** Don't say "Based on your symptoms, I recommend X" while in booking intent
with a department the user never asked for.

---

## 5. What I could not determine

- **The exact delivery failure in A.** The backend's reply exists in the database; why it
  never rendered is not recoverable from surviving artefacts.
- **The exact prompt/response for the Endocrinology decision (D).** Not persisted.

Both need a reproduction with temporary logging. `docker compose logs -f backend | tee`
before reproducing would capture it.
