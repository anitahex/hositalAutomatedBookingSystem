# Plan — document follow-up, retained context, and department reconciliation

Planning only. Nothing here is implemented. P1 (the frontend timeout) is queued to start
after this is approved.

---

## 1. Why this is needed — the current behaviour

Uploading a document does **not** enter the agent graph at all. `chat.py`'s document
fast-path streams the analysis and then, in one assignment, decides everything:

```python
state.update({
    "target_department": dept,          # regex over the model's own prose
    "awaiting": "user_input",
    "active_intent": "direct_booking",  # ← jumps straight to booking
    "intent": "direct_booking",
    "analyzed_documents": doc_log,
})
return                                   # graph never runs
```

Four consequences, all observed in the real transcript:

1. **No follow-up is possible.** Triage and intake are skipped entirely — the graph, which
   owns question-asking, is never invoked.
2. **Booking intent is forced** the instant a file is uploaded, before the patient has
   said what they want.
3. **A department is committed**, not proposed — and it becomes the sticky
   `requested_department` that later turns cannot dislodge.
4. **The document is forgotten.** Only `full_text[:150] + "…"` is kept in state
   (`chat.py:530`). Every lab value is discarded from the conversation's memory.

`awaiting="user_input"` is written by the document paths but is **never consumed** as a
routing state in the supervisor, so the following turn falls through to generic routing.

---

## 2. Target behaviour

```
upload → analysis → 1-3 follow-up questions (document-aware)
                         ↓
              symptom signal   vs   document signal   vs   referral on the document
                         ↓
         agree? → proceed        conflict? → SHOW BOTH, ASK the patient
                         ↓
                   patient chooses → book
```

**The department is never silently decided from a document again.** It becomes a
*proposal* that the patient confirms or overrides.

---

## 3. Design

### 3.1 Stop hijacking the intent

Replace the forced `direct_booking` with a dedicated post-document state:

| field | now | proposed |
|---|---|---|
| `active_intent` | `direct_booking` | `document_review` |
| `awaiting` | `user_input` (inert) | `document_follow_up` (routed) |
| `target_department` | set from prose | **not set** |
| — | — | `document_department` (proposal + provenance) |

`target_department` is only set once a human signal confirms it.

### 3.2 Keep three department signals apart, with provenance

Today one `target_department` is overwritten by whoever writes last. Instead:

```python
department_signals = {
  "referral":  {"value": "Psychiatry",     "source": "document_referral", "confidence": ...},
  "document":  {"value": "Endocrinology",  "source": "lab_findings",      "confidence": ...},
  "symptoms":  {"value": "Psychiatry",     "source": "intake",            "confidence": ...},
}
```

Nothing collapses them. The reconciler reads all three and decides what to *ask*.

### 3.3 Extract the referral — and degrade cleanly when there isn't one

`gpt4o_structured_extraction` returns only `document_type, clinical_date,
overall_impression, findings`. Add `referring_doctor` and `referring_department`.

**This needs a prompt change, not just a schema field.** Checked against the real
analysis of the reported document: in 3,914 characters the model mentioned `Panday`,
`Referr`, `Psychiatr` and `Consultant` **zero times each**. The extraction prompt is
oriented at test results, so the referring physician on the letterhead was never read.
Adding a field to the schema without telling the model to look for it would return null
forever and look like the feature was working.

**Referral evidence has three tiers, and most documents will not reach tier 1:**

| Tier | Present on document | Resolution |
|---|---|---|
| 1 | Referring **department** ("Referred by: Psychiatry OPD") | use directly |
| 2 | Referring **doctor name** only ("Dr. Sunita Panday") | look up via the existing `available_doctors_by_name()` → department. Works for this case: she is in `doctors` as Psychiatry |
| 3 | Neither | **no referral signal** — see below |

Tier 2 is worth building: a name with no specialty is common on lab letterheads, and we
already have the lookup. A name that matches no doctor in our table yields nothing — it
is never guessed at.

### 3.3b Document types are not interchangeable

A document may be a prescription, lab report, X-ray, MRI, CT, ultrasound, ECG or
discharge summary. Each carries a *different* routing signal, and treating them alike is
how the current code goes wrong.

**The core error: confusing the service that PRODUCED the document with the department
that should TREAT the patient.** `_extract_dept_from_text` maps imaging keywords
(`mri`, `ct scan`, `x-ray`, `ultrasound`) → **Radiology**, and lab keywords (`cbc`,
`haemoglobin`, `platelet`) → **Pathology**. Neither exists in this hospital — and even if
they did, both would be wrong: you do not book a follow-up with the radiologist who read
your scan or the lab that ran your blood. You follow up with whoever *ordered* it.

So `Radiology`, `Pathology` and `Laboratory` go on an explicit **never-route-to** list,
not merely "absent from the canonical list".

| Document | Primary routing signal | Fallback | Never route to |
|---|---|---|---|
| Prescription | prescribing doctor → their department | medication class | — |
| Lab report | referring doctor | abnormal findings | Pathology |
| Imaging (X-ray/MRI/CT/US) | **referring** doctor, not the reporting radiologist | body region | Radiology |
| ECG | referring doctor | Cardiology | — |
| Discharge summary | treating department | — | — |

**Body region → department**, for imaging with no referrer: spine / lumbar / cervical /
knee / shoulder / fracture → Orthopedics; brain / head → Neurology; chest / lung →
Pulmonology; cardiac → Cardiology; abdomen / liver → Gastroenterology; kidney / renal →
Nephrology.

**Extract the clinical history / indication.** Most reports state why the test was
ordered — *"Clinical history: low back pain × 3 months"*. That is the patient's symptoms
in clinical language, frequently better than what they type, and it is currently thrown
away. Add `clinical_history` to extraction and use it to seed the symptom signal **and**
to make the first question specific:

> Your MRI mentions low back pain for about 3 months — is that still the main problem?

**A prescription usually means follow-up, not a new booking.** If the prescriber is in
our `doctors` table, offer them directly rather than routing by department:

> This is from **Dr. Sunita Panday (Psychiatry)**. Book a follow-up with her, or see
> someone else?

**Questions adapt to type:** prescription → "refill/follow-up with Dr X, or a new
problem?"; imaging → "did a doctor ask you to come back with this scan?"; lab → as §3.3a.

`document_catalog.document_type` currently holds only `blood_report`, so this taxonomy is
new work, not a migration.

### 3.3a When there is no referral at all

The referral is one signal among several, never a requirement. With it absent the
resolver simply skips that rung — `explicit request → (referral absent) → current
symptoms → document findings → General Physician` — and the **question budget re-spends**
rather than wasting a turn asking about a referral that does not exist:

| | With a referral | Without |
|---|---|---|
| Q1 | "Is this follow-up for Dr. Panday, or something new?" | "Are you having symptoms at the moment, or is this a routine check?" |
| Q2 | current symptoms | how long / how severe |
| Q3 | severity / duration | reconcile if symptoms and findings disagree |
| Q4 | timing preference | timing preference |

**Edge case — no referral and no symptoms** (someone uploading a routine annual panel):
the document finding is then the *only* signal. Still confirm rather than auto-book, but
the question collapses to one: *"Your report shows raised cortisol and low vitamin D.
Would you like to book with Endocrinology, or is this just for your records?"* — note
"just for my records" must be a valid answer that books nothing.

**This path is where the fabricated-department bug bites hardest.** A blood report with
no referral and no symptoms keyword-matches `Pathology` in `_extract_dept_from_text` —
a department that **does not exist** in this hospital. With no other signal to correct it,
that becomes the recommendation. Validating every resolved department against the live
`doctors` table (§3.7) is what stops it, falling back to General Physician.

### 3.4 Retain real document context

Keep a structured reference instead of a 150-char string:

```python
analyzed_documents: [{
  "document_id": "...",          # full summary already lives in blob storage
  "document_type": "Blood Report",
  "clinical_date": "2026-09-20",
  "key_findings": [ ... ],       # abnormal values only, bounded (say 10)
  "referring_department": "Psychiatry",
  "department_signal": {"value": "Endocrinology", "confidence": ...},
}]
```

Full text stays in blob storage (`summary_blob_path`) and is fetched on demand, so chat
state stays small. Follow-up questions and the reconciler read `key_findings`, so the
assistant can actually refer to *"your cortisol and vitamin D"* in a later turn.

### 3.5 Follow-up questions

Reuse the existing intake machinery rather than inventing a second one:
`conversation_agent`, `questions_asked`, `collected_data`, `MAX_INTAKE_QUESTIONS`,
`next_missing_intake_question`.

Seed it with document context so questions are specific, and cap at **2–3** so upload does
not become an interrogation. Examples grounded in this report:

- "Your report shows raised morning cortisol and low vitamin D. Are you having symptoms
  right now — tiredness, low mood, sleep trouble?"
- "It mentions a referral from Dr. Sunita Panday in Psychiatry. Is this follow-up for
  that, or something new?"

The second question would have resolved this entire incident in one turn.

### 3.6 Reconciliation rules — deterministic, then ask

Priority when signals **agree or are absent**:

1. **Explicit request this turn** — the patient names a department → always wins
2. **Referral on the document** — a named referring department
3. **Current symptoms** from follow-up
4. **Document findings**
5. General Physician

When signals **conflict** — do **not** silently pick. Show both and ask:

> Your report points to **Endocrinology** (raised cortisol), and it was referred by
> **Dr. Sunita Panday, Psychiatry**. You mentioned anxiety and trouble sleeping.
> Which would you like to book — Psychiatry, Endocrinology, or shall I explain the
> difference?

**I recommend "ask" over "current symptoms wins", and this is the one place I'd push back
on the brief.** Current symptoms *should* outrank a document — but silently is wrong
here. Anxiety and insomnia are genuine symptoms of hypercortisolism; routing on symptoms
alone would send this patient away from the abnormal lab result that may be causing them.
The patient chooses, and the finding is never hidden. This is also consistent with the
rest of the codebase, which never lets a model's output take a clinical action
unreviewed. Deterministic rules decide *what to ask*; the patient decides *what to book*.

### 3.7 Never fabricate a department

Two fabrication sources found during the investigation, both in scope here:

- `normalize_department_name` title-cases unmatched input → `'Physcologist'`,
  `'Mental Health'`. Should return `None`.
- `_extract_dept_from_text`'s hard-coded map can emit **Pathology, Radiology, Gynecology,
  Urology** (none exist) and can **never** emit **Psychiatry, Nephrology, Hematology**.
  Should be generated from the departments table.

Every resolved department is validated against the live table before it reaches state.

---

## 4. Files

| File | Change |
|---|---|
| `app/api/routes/chat.py` | doc fast-path: stop forcing `direct_booking`/`target_department`; set `document_review` + `document_follow_up`; store structured `analyzed_documents` |
| `app/inference/azure_client.py` | add `referring_doctor`, `referring_department` to extraction |
| `app/agents/supervisor.py` | route `awaiting="document_follow_up"`; re-run department extraction every turn so an explicit request always wins |
| `app/agents/conversation_agent.py` | document-aware follow-up questions |
| `app/services/department_resolver.py` | **new** — single source of truth: signals in, decision or clarifying question out. Pure, no DB, unit-testable |
| `app/services/appointments.py` | `normalize_department_name` returns `None` on no match |
| `app/agents/appointment_booker.py` | consume the resolver instead of `requested_department` directly |

---

## 5. Test plan

**Unit** (`department_resolver`, no DB, no LLM):
- referral beats document findings
- explicit request beats everything
- conflict → returns "ask", never a silent pick
- unknown department → `None`, never fabricated
- **the real transcript as a fixture**: cortisol + anxiety/insomnia + Psychiatry referral
  → must offer Psychiatry, must not silently book Endocrinology

**Integration:** upload → follow-up asked → answer → correct department; explicit
"psychiatrist" mid-menu escapes the booking state; every resolved department exists in the
DB.

**Regression:** the existing chat/booking suites must stay green — this changes routing,
so that is the main risk surface.

---

## 6. Risks

1. **This changes clinical routing.** Highest-consequence change discussed so far.
   Mitigated by the resolver being pure and directly unit-tested against the real case.
2. **Upload becomes slower to act on** — 2–3 questions before booking. Mitigated by the
   cap and by letting "book me with X" skip straight through.
3. **Existing sessions** hold `active_intent="direct_booking"` from the old path; the new
   states must not break them.
4. **Prompt/extraction change** — adding referral fields alters the vision prompt; the
   existing extraction tests must still pass.
5. **Scope.** This touches the triage path, which is the core of the product. I'd do it
   strictly after P1, in reviewable steps: resolver + tests → extraction → follow-up →
   supervisor wiring.

---

## 7. Decisions — SETTLED 2026-09-23

1. **Conflict handling → ASK the patient.** On disagreement the assistant shows every
   signal and lets the patient choose; priority rules decide what to ask, never what to
   silently book. (§3.6)
2. **Question budget → 3–4, adaptive.** Higher than the 2 originally proposed. It is a
   ceiling, not a quota: questions stop as soon as the department is unambiguous, and an
   explicit "book me with X" skips straight to booking. With 3–4 available, the budget
   should be spent in this order — referral confirmation, current symptoms, severity/
   duration, then timing preference — so the decisive question is always asked first even
   if the patient abandons the flow early.
3. **Scope → minimal slice first.** `department_resolver` + tests, then referral
   extraction. Follow-up questions and the intent-hijack fix land in the next slice.

---

## 8. Order of work

1. **P1 — frontend timeout** (already approved, starts next; independent)
2. `department_resolver` + unit tests, including the real transcript
3. Referral extraction
4. Stop the doc fast-path forcing intent/department
5. Document-aware follow-up questions
6. Supervisor wiring + the sticky-department escape hatch
