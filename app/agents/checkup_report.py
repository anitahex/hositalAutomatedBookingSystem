from datetime import date

from app.agents.intake_utils import compact_fact_summary
from app.agents.state import GraphState
from app.inference.llm import generate_text
from app.services.rag import match_department_details

STATIC_CHECKUP_PROMPT = """You are a hospital AI pre-screening assistant. A patient has just completed their symptom intake. \
Generate a clear, professional, patient-facing pre-appointment summary using the markdown format below.

Output EXACTLY this structure (use markdown — **bold labels**, ## heading, bullet lists):

## Pre-Appointment Summary

**Symptoms:** <comma-separated list>
**Duration:** <how long / since when>
**Location:** <body area — omit if unknown>
**Pattern:** <intermittent / constant / worsening — omit if unknown>
**Medications taken:** <medications mentioned, or "None reported">

---

**Immediate care tip:** <1 specific sentence tailored to these symptoms>

**Recommended next step:** See a doctor in the **<Department>** department for a proper evaluation.

---

Would you like me to find available appointment slots for you?

Rules:
- Omit any line whose data is unknown (do not write "Unknown" or "N/A")
- Do not invent facts not stated by the patient
- Bold all field labels exactly as shown
- Do not add extra sections or preamble"""


def _build_pre_checkup_report(state: GraphState, department: str | None) -> dict:
    """Structured report stored in state and forwarded to the doctor as booking note."""
    symptoms = state.get("symptoms") or []
    collected = state.get("collected_data") or state.get("collected_info") or {}
    profile = state.get("patient_profile") or {}

    report: dict = {
        "report_type": "pre_ai_checkup",
        "report_date": date.today().isoformat(),
        "patient_name": profile.get("name", "Unknown"),
        "symptoms": symptoms,
        "recommended_department": department,
    }
    for key, aliases in (
        ("duration", ("duration",)),
        ("location", ("location",)),
        ("cause_or_trigger", ("cause", "trigger", "onset")),
        ("pattern", ("severity_pattern", "pattern")),
        ("associated_symptoms", ("associated_symptoms",)),
        ("medications_taken", ("medications",)),
        ("existing_conditions", ("history", "existing_conditions")),
        ("allergies", ("allergies",)),
    ):
        value = next((collected.get(a) for a in aliases if collected.get(a)), None)
        if value:
            report[key] = value

    if state.get("severity"):
        report["severity"] = state["severity"]

    return report


def _format_report_as_note(report: dict) -> str:
    """Convert the structured report into a human-readable clinical note string."""
    parts = ["Pre-AI Checkup Report (auto-generated from intake chat)"]
    if report.get("patient_name") and report["patient_name"] != "Unknown":
        parts.append(f"Patient: {report['patient_name']}")
    parts.append(f"Date: {report.get('report_date', date.today().isoformat())}")
    if report.get("symptoms"):
        parts.append(f"Reported symptoms: {', '.join(report['symptoms'])}")
    for label, key in (
        ("Duration", "duration"),
        ("Location", "location"),
        ("Cause/trigger", "cause_or_trigger"),
        ("Pattern", "pattern"),
        ("Associated symptoms", "associated_symptoms"),
        ("Medications taken", "medications_taken"),
        ("Existing conditions", "existing_conditions"),
        ("Allergies", "allergies"),
        ("Severity", "severity"),
    ):
        if report.get(key):
            parts.append(f"{label}: {report[key]}")
    if report.get("recommended_department"):
        parts.append(f"Recommended department: {report['recommended_department']}")
    return "; ".join(parts)


def checkup_report_node(state: GraphState):
    # Idempotency guard — if summary was already shown (e.g. routed here a second
    # time due to state drift), just re-ask the booking question without regenerating
    # the full report so the patient doesn't see a duplicate wall of text.
    if state.get("checkup_summary_shown"):
        history = list(state.get("conversation_history") or [])
        response = "Would you like me to find available appointment slots for you? (yes / no)"
        history.append({"role": "assistant", "text": response})
        return {
            "conversation_history": history,
            "messages": history[-6:],
            "awaiting": "booking_decision",
            "active_intent": "direct_booking",
            "intent": "direct_booking",
            "final_response": response,
        }

    symptoms = state.get("symptoms") or []
    collected = state.get("collected_data") or state.get("collected_info") or {}
    history = list(state.get("conversation_history") or [])

    # Department matching
    match = match_department_details(
        symptoms,
        collected,
        chat_history=state.get("conversation_history"),
        chat_summary=state.get("chat_summary"),
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    department = match.department

    # Build structured report
    pre_checkup_report = _build_pre_checkup_report(state, department)
    booking_note_text = _format_report_as_note(pre_checkup_report)

    # Generate patient-facing summary
    profile = state.get("patient_profile") or {}
    user_prompt = (
        f"Current date: {date.today().isoformat()}\n"
        f"Patient name: {profile.get('name', 'the patient')}\n"
        f"Reported symptoms: {', '.join(symptoms) if symptoms else 'not specified'}\n"
        f"Collected intake facts: {compact_fact_summary(collected)}\n"
        f"Severity: {state.get('severity') or 'not assessed'}\n"
        f"Matched department: {department or 'General Medicine'}\n"
    )

    response = generate_text(
        system_prompt=STATIC_CHECKUP_PROMPT,
        user_prompt=user_prompt,
        node_name="checkup_report",
        chat_summary=state.get("chat_summary"),
        include_history=False,
        history_turns=0,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    ).strip()

    if not response:
        dept_name = department or "General Medicine"
        sym_text = ", ".join(symptoms) if symptoms else "your reported symptoms"
        response = (
            f"Based on what you've shared ({sym_text}), I recommend you see a doctor "
            f"in the {dept_name} department.\n\n"
            "Would you like me to find available appointment slots for you?"
        )

    history.append({"role": "assistant", "text": response})

    return {
        "conversation_history": history,
        "messages": history[-6:],
        "pre_checkup_report": pre_checkup_report,
        "pre_checkup_note": booking_note_text,
        "checkup_summary_shown": True,
        "target_department": department,
        "candidate_departments": list(match.candidate_departments or []),
        "department_match_source": match.source,
        "department_match_confidence": match.confidence,
        "department_match_reason": match.reason,
        "active_intent": "direct_booking",
        "intent": "direct_booking",
        "awaiting": "booking_decision",
        "final_response": response,
    }
