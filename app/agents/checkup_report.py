from datetime import date

from app.agents.intake_utils import compact_fact_summary
from app.agents.state import GraphState
from app.inference.llm import generate_text
from app.services.appointments import normalize_department_name

# OPTIMIZED FOR GPT-4o — CONCISE CLINICAL SUMMARY
STATIC_CHECKUP_PROMPT = """You are a hospital clinical documentation specialist. Generate a CONCISE yet COMPREHENSIVE pre-appointment summary (max 10-12 lines).

## PRE-APPOINTMENT CLINICAL SUMMARY

**Patient:** [Name], [Age], [Blood Group] | **Date:** [Date]

**Chief Complaint:**
[1 sentence with patient's main complaint, severity, and functional impact - e.g., "Severe lower back pain (8/10) for 5 days, unable to sit for extended periods"]

**History:**
- Duration: [timeline] | Onset: [sudden/gradual] | Pattern: [constant/intermittent]
- Location: [anatomical area] | Associated: [other symptoms or "None"]
- Trigger: [cause or "Unknown"] | Medications tried: [list or "None"]

**Medical Background:**
[Allergies, existing conditions, relevant history - or "None reported"]

**Clinical Note for Doctor:**
[2-3 sentences: Why this department is appropriate, what to assess, any red flags. Example: "Acute lower back pain with leg radiation suggests possible nerve involvement. Assess range of motion, reflexes, neurological function. Rule out structural abnormalities."]

**Recommended Department:** [Department]

**Home Care Recommendations:**
[2-3 specific, actionable care tips - e.g., "Rest with proper support, apply heat to lower back, avoid heavy lifting, maintain good posture. If pain worsens or numbness develops, seek immediate care."]

---

CRITICAL:
- Capture EXACT details patient mentioned (severity, duration, location, medications)
- Be SPECIFIC, not generic
- Include FUNCTIONAL IMPACT in chief complaint
- Max 10-12 lines total, no repetition
- Include HOME CARE advice for patient
- Omit fields where patient didn't provide data (don't say "unknown")"""


def _build_pre_checkup_report(state: GraphState, department: str | None) -> dict:
    """Structured report stored in state and forwarded to the doctor as booking note."""
    symptoms = state.get("symptoms") or []
    collected = state.get("collected_data") or state.get("collected_info") or {}
    profile = state.get("patient_profile") or {}

    report: dict = {
        "report_type": "pre_ai_checkup",
        "report_date": date.today().isoformat(),
        "patient_name": profile.get("name", "Unknown"),
        "patient_age": profile.get("age"),
        "patient_blood_group": profile.get("blood_group"),
        "symptoms": symptoms,
        "severity": state.get("severity"),
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
        ("health_issues", ("health_issues",)),
    ):
        value = next((collected.get(a) for a in aliases if collected.get(a)), None)
        if value:
            report[key] = value

    return report


def _format_report_as_clinical_note(report: dict) -> str:
    """Convert structured report into detailed clinical note for doctor (not patient-facing)."""
    lines = [
        "═════════════════════════════════════════════════════════════",
        "PRE-AI INTAKE CHECKUP REPORT (Auto-generated from patient chat)",
        "═════════════════════════════════════════════════════════════",
        "",
    ]

    if report.get("patient_name") and report["patient_name"] != "Unknown":
        lines.append(f"Patient Name: {report['patient_name']}")
    if report.get("patient_age"):
        lines.append(f"Age: {report['patient_age']}")
    if report.get("patient_blood_group"):
        lines.append(f"Blood Group: {report['patient_blood_group']}")

    lines.append(f"Report Date: {report.get('report_date', date.today().isoformat())}")
    lines.append(f"Recommended Department: {report.get('recommended_department', 'General Medicine')}")
    lines.append("")

    lines.append("CHIEF COMPLAINT & CLINICAL PRESENTATION:")
    lines.append("─" * 50)
    if report.get("symptoms"):
        lines.append(f"Reported Symptoms: {', '.join(report['symptoms'])}")
    if report.get("severity"):
        lines.append(f"Severity: {report['severity'].upper()}")
    if report.get("duration"):
        lines.append(f"Duration: {report['duration']}")
    if report.get("location"):
        lines.append(f"Location: {report['location']}")
    if report.get("cause_or_trigger"):
        lines.append(f"Trigger/Cause/Onset: {report['cause_or_trigger']}")
    if report.get("pattern"):
        lines.append(f"Pattern: {report['pattern']}")
    if report.get("associated_symptoms"):
        lines.append(f"Associated Symptoms: {report['associated_symptoms']}")

    lines.append("")
    lines.append("RELEVANT MEDICAL HISTORY:")
    lines.append("─" * 50)
    if report.get("medications_taken"):
        lines.append(f"Current/Recent Medications: {report['medications_taken']}")
    else:
        lines.append("Current/Recent Medications: None reported")
    if report.get("allergies"):
        lines.append(f"Known Allergies: {report['allergies']}")
    else:
        lines.append("Known Allergies: None reported")
    if report.get("existing_conditions"):
        lines.append(f"Existing Conditions: {report['existing_conditions']}")
    if report.get("health_issues"):
        lines.append(f"Pre-existing Health Issues: {report['health_issues']}")

    lines.append("")
    lines.append("═════════════════════════════════════════════════════════════")

    return "\n".join(lines)


def checkup_report_node(state: GraphState):
    # Idempotency guard — if summary was already shown, skip regeneration
    if state.get("checkup_summary_shown"):
        history = list(state.get("conversation_history") or [])
        response = (
            "Your clinical summary has been prepared and will be shared with your doctor. "
            "Would you like me to find available appointment slots for you? (yes / no)"
        )
        if response not in [h.get("text") for h in history[-2:]]:
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

    # Department routing - Pure LLM (skip RAG for speed)
    from app.inference.llm import generate_router_text

    symptoms_str = ", ".join(symptoms) if symptoms else "Not specified"
    location = collected.get('location', '')
    duration = collected.get('duration', '')
    pattern = collected.get('pattern') or collected.get('severity_pattern', '')
    associated = collected.get('associated_symptoms', '')

    router_prompt = (
        f"Patient symptoms: {symptoms_str}\n"
        f"Location: {location}\n"
        f"Duration: {duration}\n"
        f"Pattern: {pattern}\n"
        f"Associated symptoms: {associated}\n"
        f"Severity: {state.get('severity', 'moderate')}\n\n"
        f"Recommend the SINGLE best department from these options:\n"
        f"General Physician, Cardiology, Gastroenterology, Orthopedics, Neurology, Dermatology, Ophthalmology, ENT, Pediatrics, Psychiatry, Oncology, Pulmonology\n\n"
        f"Output ONLY the exact department name from the list above, nothing else."
    )

    router_resp = generate_router_text(
        system_prompt="You are a clinical department router. Match patients to the most appropriate medical department based on their symptoms. Be decisive and specific.",
        user_prompt=router_prompt,
        node_name="checkup_report_router",
        include_history=False,
        history_turns=0,
    )
    department = router_resp.strip() if router_resp else "General Physician"

    # Clean up response and normalize to match database departments
    department = department.split('\n')[0].strip() if department else "General Physician"
    department = normalize_department_name(department)

    # Build structured report
    pre_checkup_report = _build_pre_checkup_report(state, department)
    clinical_note = _format_report_as_clinical_note(pre_checkup_report)

    # Generate comprehensive clinical summary for doctor
    profile = state.get("patient_profile") or {}

    # Build concise context with ALL collected information
    user_prompt = (
        f"Patient: {profile.get('name', 'Unknown')}, Age {profile.get('age', '?')}, Blood Group {profile.get('blood_group', '?')}\n"
        f"Date: {date.today().isoformat()}\n"
        f"\n"
        f"Symptoms: {', '.join(symptoms) if symptoms else 'None'}\n"
        f"Severity: {state.get('severity', 'Moderate')}\n"
        f"Duration: {collected.get('duration', '')}\n"
        f"Location: {collected.get('location', '')}\n"
        f"Onset: {collected.get('cause') or collected.get('trigger') or collected.get('onset', '')}\n"
        f"Pattern: {collected.get('pattern') or collected.get('severity_pattern', '')}\n"
        f"Associated Symptoms: {collected.get('associated_symptoms', '')}\n"
        f"Medications Tried: {collected.get('medications', '')}\n"
        f"Allergies: {profile.get('allergies') or collected.get('allergies', '')}\n"
        f"Existing Conditions: {profile.get('health_issues') or collected.get('existing_conditions', '')}\n"
        f"Medical History: {collected.get('history', '')}\n"
        f"Department: {department or 'General Medicine'}\n"
    )

    comprehensive_summary = generate_text(
        system_prompt=STATIC_CHECKUP_PROMPT,
        user_prompt=user_prompt,
        node_name="checkup_report",
        chat_summary=state.get("chat_summary"),
        include_history=False,
        history_turns=0,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    ).strip()

    if not comprehensive_summary:
        dept_name = department or "General Medicine"
        sym_text = ", ".join(symptoms) if symptoms else "your reported symptoms"
        comprehensive_summary = (
            f"## Pre-Appointment Clinical Summary\n\n"
            f"**Chief Complaint:** {sym_text}\n"
            f"**Severity:** {state.get('severity') or 'Moderate'}\n"
            f"**Recommended Department:** {dept_name}\n\n"
            f"Your clinical information will be shared with the {dept_name} doctor to ensure they have full context about your symptoms."
        )

    # Add consent message
    response = (
        f"{comprehensive_summary}\n\n"
        f"---\n\n"
        f"**This clinical summary will be attached to your appointment and shared with your doctor before you arrive.**\n\n"
        f"Would you like me to find available appointment slots for you? (yes / no)"
    )

    history.append({"role": "assistant", "text": response})

    return {
        "conversation_history": history,
        "messages": history[-6:],
        "pre_checkup_report": pre_checkup_report,
        "pre_checkup_clinical_note": clinical_note,
        "pre_checkup_summary": comprehensive_summary,
        "checkup_summary_shown": True,
        "target_department": department,
        "candidate_departments": [],
        "active_intent": "direct_booking",
        "intent": "direct_booking",
        "awaiting": "booking_decision",
        "final_response": response,
    }
