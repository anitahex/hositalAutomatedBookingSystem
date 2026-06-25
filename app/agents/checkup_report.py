from datetime import date
import json

from app.agents.intake_utils import compact_fact_summary
from app.agents.state import GraphState
from app.inference.llm import generate_text, generate_router_text
from app.services.appointments import normalize_department_name

# INTELLIGENT CLINICAL ANALYZER — Deep analysis of symptom pattern
STATIC_CLINICAL_ANALYZER_PROMPT = """You are an expert clinical analyst. Analyze the patient's symptoms, severity, triggers, and functional impact to:
1. Understand the clinical picture (not just keywords)
2. Identify the most likely clinical issue
3. Recommend the appropriate medical department
4. Provide specific, actionable home care advice

Return ONLY valid JSON:
{
  "clinical_analysis": "2-3 sentences explaining what's happening clinically based on the full symptom picture",
  "recommended_department": "Single department name from list below",
  "reasoning": "Why this department is best for this specific clinical picture",
  "home_care_advice": "3-4 specific, actionable tips tailored to their exact symptoms and triggers",
  "severity_assessment": "mild|moderate|severe|emergency"
}

DEPARTMENTS (pick ONE that best fits):
General Physician, Cardiology, Gastroenterology, Orthopedics, Neurology, Dermatology, Ophthalmology, ENT, Pediatrics, Psychiatry, Oncology, Pulmonology

CRITICAL:
- Analyze the FULL clinical picture, not just keywords
- Consider triggers, patterns, functional impact, severity together
- Provide SPECIFIC advice based on their exact symptoms
- Example: Patient with "rash on back worse when sweating" → Sports-related fungal risk → Dermatology + advice on moisture-wicking
- Different scenario: "rash all over after new medication" → Allergic reaction → General Physician + stop medication advice"""

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
    symptoms = state.get("symptoms") or []
    collected = state.get("collected_data") or state.get("collected_info") or {}
    history = list(state.get("conversation_history") or [])
    profile = state.get("patient_profile") or {}

    # STEP 1: INTELLIGENT CLINICAL ANALYSIS
    # Build comprehensive context for the analyzer
    symptoms_str = ", ".join(symptoms) if symptoms else "Not specified"
    location = collected.get('location', '')
    duration = collected.get('duration', '')
    pattern = collected.get('pattern') or collected.get('severity_pattern', '')
    triggers = collected.get('triggers') or collected.get('trigger') or collected.get('cause', '')
    functional_impact = collected.get('functional_impact') or collected.get('impact_on_daily_life', '')
    severity = state.get('severity', 'moderate')

    analyzer_prompt = (
        f"Patient: {profile.get('name', 'Patient')}, Age {profile.get('age', 'unknown')}\n"
        f"\n"
        f"SYMPTOMS & CLINICAL PICTURE:\n"
        f"Main symptoms: {symptoms_str}\n"
        f"Location: {location if location else 'Not specified'}\n"
        f"Duration: {duration if duration else 'Not specified'}\n"
        f"Pattern: {pattern if pattern else 'Not specified'}\n"
        f"Triggers/What makes it worse: {triggers if triggers else 'Not identified'}\n"
        f"Functional impact: {functional_impact if functional_impact else 'Not mentioned'}\n"
        f"Severity assessment: {severity}\n"
        f"Associated symptoms: {collected.get('associated_symptoms') or 'None'}\n"
        f"\n"
        f"Analyze the FULL clinical picture and provide intelligent, personalized recommendations."
    )

    analysis_resp = generate_text(
        system_prompt=STATIC_CLINICAL_ANALYZER_PROMPT,
        user_prompt=analyzer_prompt,
        node_name="clinical_analyzer",
        chat_summary=state.get("chat_summary"),
        include_history=False,
        history_turns=0,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    ).strip()

    # Parse the analysis — strip markdown code fences the LLM may wrap around JSON
    analysis = {}
    try:
        clean_resp = analysis_resp.replace("```json", "").replace("```", "").strip()
        analysis = json.loads(clean_resp)
    except:
        # Fallback if JSON parsing fails
        analysis = {
            "clinical_analysis": "Clinical assessment in progress",
            "recommended_department": "General Physician",
            "reasoning": "Awaiting full assessment",
            "home_care_advice": "Rest and monitor symptoms. Seek care if symptoms worsen.",
            "severity_assessment": severity
        }

    department = normalize_department_name(analysis.get("recommended_department", "General Physician"))
    clinical_analysis = analysis.get("clinical_analysis", "")
    reasoning = analysis.get("reasoning", "")
    home_care = analysis.get("home_care_advice", "")

    # STEP 2: GENERATE COMPREHENSIVE CLINICAL SUMMARY
    user_prompt = (
        f"Patient: {profile.get('name', 'Unknown')}, Age {profile.get('age', '?')}, Blood Group {profile.get('blood_group', '?')}\n"
        f"Date: {date.today().isoformat()}\n"
        f"\n"
        f"Symptoms: {symptoms_str}\n"
        f"Severity: {severity}\n"
        f"Duration: {duration}\n"
        f"Location: {location}\n"
        f"Onset/Trigger: {triggers}\n"
        f"Pattern: {pattern}\n"
        f"Associated Symptoms: {collected.get('associated_symptoms', '')}\n"
        f"Functional Impact: {functional_impact}\n"
        f"Medications Tried: {collected.get('medications', '')}\n"
        f"Allergies: {profile.get('allergies') or collected.get('allergies', '')}\n"
        f"Existing Conditions: {profile.get('health_issues') or collected.get('existing_conditions', '')}\n"
        f"Department: {department}\n"
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

    # STEP 3: BUILD STRUCTURED REPORT FOR DOCTOR
    pre_checkup_report = _build_pre_checkup_report(state, department)
    clinical_note = _format_report_as_clinical_note(pre_checkup_report)

    # STEP 4: DISPLAY INTELLIGENT ANALYSIS + REMEDY
    response = (
        f"## CLINICAL ANALYSIS\n\n"
        f"**What's happening:** {clinical_analysis}\n\n"
        f"**Why {department}:** {reasoning}\n\n"
        f"**IMMEDIATE HOME CARE (before your appointment):**\n"
        f"{home_care}\n\n"
        f"---\n\n"
        f"## DETAILED CLINICAL SUMMARY\n"
        f"{comprehensive_summary}\n\n"
        f"---\n\n"
        f"**Would you like to book an appointment with a {department} doctor?** (yes / no)"
    )

    history.append({"role": "assistant", "text": response})

    return {
        "conversation_history": history,
        "messages": history[-6:],
        "pre_checkup_report": pre_checkup_report,
        "pre_checkup_clinical_note": clinical_note,
        "pre_checkup_summary": comprehensive_summary,
        "clinical_analysis": clinical_analysis,
        "home_care_advice": home_care,
        "analysis_reasoning": reasoning,
        "checkup_summary_shown": True,
        "target_department": department,
        "candidate_departments": [],
        "active_intent": "direct_booking",
        "intent": "direct_booking",
        "awaiting": "booking_decision",
        "final_response": response,
    }
