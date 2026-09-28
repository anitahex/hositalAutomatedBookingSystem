"""Decides which department a patient should be offered — and when to ask instead.

PURE. No database, no LLM, no network. The valid department list is injected by the
caller (normally read from the doctors table) so this module cannot drift from reality,
and every rule in it is directly unit-testable against the incident that motivated it.

WHY THIS EXISTS. A patient uploaded a blood report referred by a psychiatrist, reported
anxiety and insomnia, and was offered Endocrinology four times because a single
`target_department` field was set from a regex over the model's prose and then never
reconsidered. Three separate signals disagreed and the code had nowhere to put that
disagreement, so the last writer won silently.

THE RULE THIS MODULE ENFORCES. Priority decides what to ASK. It never decides what to
book. When the strongest two signals disagree, the answer is a question, not a winner —
the patient chooses. Deterministic ranking in, a decision or a question out.

WHAT IT NEVER DOES:
  - invent a department (an unmatched string resolves to None, not to itself title-cased)
  - route to a service that PRODUCED a document rather than one that treats a patient
    (you do not follow up with the radiologist who read your scan)
  - act on a low-confidence match from a typo, where "physiatrist" and "psychiatrist" sit
    one edit apart and mean entirely different specialties
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.appointments import (
    NEVER_ROUTE_TO_DEPARTMENTS,
    STRICT_MATCH_CONFIDENCE,
    match_department_scored,
)

DEFAULT_DEPARTMENT = "General Physician"

# Ranked strongest first. A signal's source is what decides its rank, not its confidence:
# a patient saying "I want a psychiatrist" outranks any inference we make about them.
SIGNAL_PRIORITY = (
    "explicit_request",   # the patient named it, this turn
    "referral",           # a referring department stated on the document
    "prescriber",         # the specialty of whoever wrote a prescription
    "symptoms",           # what the patient says they are experiencing now
    "findings",           # abnormal results in the document
    "body_region",        # imaging of a body part, when nothing better exists
)
_PRIORITY_RANK = {source: index for index, source in enumerate(SIGNAL_PRIORITY)}

# Imaging with no referring doctor: the body part is the only routing evidence there is.
# Ordered longest-first at match time so "lower back" beats "back".
BODY_REGION_DEPARTMENTS = {
    "lumbar": "Orthopedics", "spine": "Orthopedics", "spinal": "Orthopedics",
    "cervical": "Orthopedics", "vertebra": "Orthopedics", "knee": "Orthopedics",
    "shoulder": "Orthopedics", "hip": "Orthopedics", "ankle": "Orthopedics",
    "wrist": "Orthopedics", "fracture": "Orthopedics", "joint": "Orthopedics",
    "back": "Orthopedics",
    "brain": "Neurology", "head": "Neurology", "skull": "Neurology",
    "cranial": "Neurology", "nerve": "Neurology",
    "chest": "Pulmonology", "lung": "Pulmonology", "thorax": "Pulmonology",
    "pulmonary": "Pulmonology",
    "cardiac": "Cardiology", "heart": "Cardiology", "coronary": "Cardiology",
    "abdomen": "Gastroenterology", "abdominal": "Gastroenterology",
    "liver": "Gastroenterology", "bowel": "Gastroenterology",
    "kidney": "Nephrology", "renal": "Nephrology",
    "skin": "Dermatology",
}

# Which signal a document type is allowed to contribute, and what it must never route to.
# The "never" column is the point: a lab report is produced by Pathology and an MRI by
# Radiology, and neither is where the patient goes next.
DOCUMENT_TYPE_RULES = {
    "prescription":      {"fallback": "prescriber",   "never": ()},
    "blood_report":      {"fallback": "findings",     "never": ("pathology", "laboratory")},
    "pathology_report":  {"fallback": "findings",     "never": ("pathology", "laboratory")},
    "mri_report":        {"fallback": "body_region",  "never": ("radiology", "imaging")},
    "ct_report":         {"fallback": "body_region",  "never": ("radiology", "imaging")},
    "xray_report":       {"fallback": "body_region",  "never": ("radiology", "imaging")},
    "ultrasound_report": {"fallback": "body_region",  "never": ("radiology", "imaging")},
    "ecg_report":        {"fallback": "findings",     "never": ()},
    "discharge_summary": {"fallback": "findings",     "never": ()},
    "other":             {"fallback": "findings",     "never": ()},
}


@dataclass(frozen=True)
class DepartmentSignal:
    """One piece of evidence about where the patient should go."""
    department: str
    source: str
    confidence: float
    reason: str

    @property
    def rank(self) -> int:
        return _PRIORITY_RANK.get(self.source, len(SIGNAL_PRIORITY))


@dataclass(frozen=True)
class Resolution:
    """The outcome. `decision` is the part callers must branch on.

    resolved — one department, confident enough to offer directly
    ask      — signals disagree, or the best is a weak typo match; ASK, do not book
    none     — nothing usable; fall back to General Physician or ask openly
    """
    decision: str
    department: str | None
    candidates: list[dict] = field(default_factory=list)
    reason: str = ""

    @property
    def should_ask(self) -> bool:
        return self.decision == "ask"


def _candidate(signal: DepartmentSignal) -> dict:
    """Projected into the shape appointment_booker.ask_department_choice already consumes
    ({department, confidence, matched_terms, reason}), plus an additive `source` so the UI
    can say WHERE a suggestion came from. Reusing that shape is deliberate — the
    disambiguation menu already exists and does not need a second implementation."""
    return {
        "department": signal.department,
        "confidence": round(signal.confidence, 3),
        "matched_terms": [],
        "reason": signal.reason,
        "source": signal.source,
    }


def _is_producer(name: str | None) -> bool:
    return bool(name) and " ".join(str(name).lower().split()) in NEVER_ROUTE_TO_DEPARTMENTS


def signal_from_text(
    text: str | None,
    source: str,
    valid_departments: list[str] | None = None,
    *,
    reason: str = "",
) -> DepartmentSignal | None:
    """Builds one signal from free text, or None if nothing real matched.

    Never fabricates: unmatched text yields no signal at all rather than a department
    named after the patient's typo.
    """
    department, score = match_department_scored(text, valid_departments)
    if not department:
        return None
    return DepartmentSignal(
        department=department,
        source=source,
        confidence=score,
        reason=reason or f"matched “{str(text).strip()}”",
    )


def body_region_department(text: str | None) -> tuple[str | None, str]:
    """Maps an imaging body region to the department that treats it. Longest key first so
    a multi-word region is not beaten by a substring of itself."""
    if not text:
        return None, ""
    lowered = " ".join(str(text).lower().split())
    for region in sorted(BODY_REGION_DEPARTMENTS, key=len, reverse=True):
        if region in lowered:
            return BODY_REGION_DEPARTMENTS[region], region
    return None, ""


def signals_from_document(
    document: dict | None, valid_departments: list[str] | None = None
) -> list[DepartmentSignal]:
    """Every routing signal a single analysed document can honestly contribute.

    Reads the structured extraction fields, NOT the model's prose. Anything the document
    type forbids (Radiology for a scan, Pathology for a lab report) is dropped even if the
    model named it.
    """
    if not document:
        return []

    doc_type = str(document.get("document_type") or "other").strip().lower()
    rules = DOCUMENT_TYPE_RULES.get(doc_type, DOCUMENT_TYPE_RULES["other"])
    forbidden = set(rules["never"])
    signals: list[DepartmentSignal] = []

    def _blocked(name: str | None) -> bool:
        return _is_producer(name) or (
            bool(name) and " ".join(str(name).lower().split()) in forbidden
        )

    # 1. An explicit referring department is the strongest thing a document can say.
    referral = document.get("referring_department")
    if referral and not _blocked(referral):
        signal = signal_from_text(
            referral, "referral", valid_departments,
            reason=f"referred to {referral} on this document",
        )
        if signal:
            signals.append(signal)

    # 2. A prescriber's specialty. Often from another hospital, so this routes to the
    #    closest department WE have and is always confirmed, never booked outright.
    prescriber_specialty = document.get("prescriber_specialty") or document.get("referring_doctor_specialty")
    if prescriber_specialty and not _blocked(prescriber_specialty):
        signal = signal_from_text(
            prescriber_specialty, "prescriber", valid_departments,
            reason=f"prescribed by a {prescriber_specialty} specialist",
        )
        if signal:
            signals.append(signal)

    # 3. Clinical history / indication — why the test was ordered. Usually the patient's
    #    own symptoms in clinical language, and frequently better evidence than the
    #    findings themselves.
    history = document.get("clinical_history")
    if history:
        signal = signal_from_text(
            history, "symptoms", valid_departments,
            reason=f"clinical history: {str(history).strip()[:80]}",
        )
        if signal:
            signals.append(signal)

    # 4. Whatever the analysis recommended — untrusted model output, so it is re-matched
    #    against real departments and dropped if it names a producing service.
    recommended = document.get("recommended_department") or document.get("department")
    if recommended and not _blocked(recommended):
        signal = signal_from_text(
            recommended, "findings", valid_departments,
            reason="based on the findings in this document",
        )
        if signal:
            signals.append(signal)

    # 5. Body region, for imaging with nothing better.
    if rules["fallback"] == "body_region":
        region_dept, region = body_region_department(
            document.get("body_region") or document.get("overall_impression")
        )
        if region_dept and not _blocked(region_dept):
            if valid_departments is None or region_dept in valid_departments:
                signals.append(DepartmentSignal(
                    department=region_dept,
                    source="body_region",
                    # A deterministic table lookup, not a fuzzy guess: "lumbar" maps to
                    # Orthopedics with certainty. Confidence here measures how sure the
                    # MATCH is, not how strong the evidence is — the evidence strength is
                    # already expressed by body_region being last in SIGNAL_PRIORITY.
                    confidence=1.0,
                    reason=f"imaging of the {region}",
                ))

    return signals


def resolve_department(
    signals: list[DepartmentSignal] | None,
    valid_departments: list[str] | None = None,
) -> Resolution:
    """Rank the signals and either resolve or ask.

    Asks — rather than picking — in exactly two situations:
      1. the two highest-ranked signals name DIFFERENT departments
      2. the best signal is only a weak (typo-level) match

    Both are cases where picking silently is how the original incident happened.
    """
    usable = [
        s for s in (signals or [])
        if s and s.department and not _is_producer(s.department)
        and (valid_departments is None or s.department in valid_departments)
    ]
    if not usable:
        return Resolution(decision="none", department=None, candidates=[],
                          reason="no usable department signal")

    # Strongest source first; within a source, the more confident match.
    usable.sort(key=lambda s: (s.rank, -s.confidence))

    # One candidate per department, keeping its best-ranked signal.
    seen: dict[str, DepartmentSignal] = {}
    for signal in usable:
        if signal.department not in seen:
            seen[signal.department] = signal
    distinct = list(seen.values())
    candidates = [_candidate(s) for s in distinct]

    best = distinct[0]

    # 0. The patient said it themselves, this turn. That outranks every inference we could
    #    make about them and short-circuits the rest — it is also the "skip ahead" path,
    #    and its absence is what let the original transcript swallow the same request four
    #    times running.
    if best.source == "explicit_request":
        return Resolution(
            decision="resolved", department=best.department,
            candidates=candidates, reason=best.reason,
        )

    # 1. Disagreement between the top two — the patient decides.
    if len(distinct) > 1:
        runner_up = distinct[1]
        return Resolution(
            decision="ask",
            department=None,
            candidates=candidates,
            reason=(
                f"{best.department} ({best.reason}) and {runner_up.department} "
                f"({runner_up.reason}) both apply"
            ),
        )

    # 2. Single department, but only a weak match — confirm rather than assume a typo.
    if best.confidence < STRICT_MATCH_CONFIDENCE and best.source != "explicit_request":
        return Resolution(
            decision="ask", department=None, candidates=candidates,
            reason=f"{best.department} is only a possible match ({best.reason})",
        )

    return Resolution(
        decision="resolved", department=best.department,
        candidates=candidates, reason=best.reason,
    )
