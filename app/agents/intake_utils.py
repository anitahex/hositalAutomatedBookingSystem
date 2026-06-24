import re
from functools import lru_cache

from app.agents.state import GraphState


# These are lightweight follow-up topics used to prevent repetitive questions.
# They are intentionally generic intake heuristics, not a fixed stomach-only taxonomy.
QUESTION_TOPIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "duration": ("how long", "when did", "since when", "when started", "when did this start"),
    "location": ("where", "which part", "exact area", "specific area", "body part", "area of", "location", "side of", "region of"),
    "pattern": ("constant", "comes and goes", "on and off", "pattern", "severity", "how bad"),
    "cause": ("trigger", "cause", "onset", "allergy", "food", "ate", "meal", "activity", "injury", "medicine", "exercise", "stress"),
    "associated_symptoms": (
        "nausea",
        "vomit",
        "vomiting",
        "fever",
        "diarrhea",
        "blood",
        "loose stool",
        "stool",
        "cramp",
        "pain",
        "ache",
        "swelling",
        "rash",
        "itch",
        "cough",
        "breath",
        "weakness",
        "numbness",
        "dizziness",
        "headache",
        "bleeding",
        "burning",
    ),
    "history": ("before", "previous", "earlier", "past", "history", "ever had"),
    "medications": ("medicine", "medication", "medications", "drug", "tablet", "pill"),
    "severity": ("mild", "moderate", "severe", "worse", "better", "getting worse", "getting better"),
}

# Sorted longest-first so "lower back" is preferred over plain "back"
BODY_AREA_HINTS = (
    "lower back", "upper back", "lower abdomen", "upper abdomen",
    "head", "neck", "chest", "heart", "back",
    "shoulder", "arm", "wrist", "hand", "finger",
    "leg", "thigh", "knee", "calves", "calf", "ankle", "foot", "toe",
    "stomach", "abdomen", "belly", "skin",
    "eye", "ear", "nose", "mouth", "throat", "pelvis", "groin", "hip",
)

# Pre-compiled word-boundary patterns for each hint (avoids false positives like
# "ear" inside "year" or "arm" inside "warm").
@lru_cache(maxsize=None)
def _body_area_patterns() -> tuple[tuple[str, re.Pattern], ...]:
    return tuple(
        (hint, re.compile(r"\b" + re.escape(hint) + r"\b"))
        for hint in BODY_AREA_HINTS
    )


def normalize_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def extract_json_object(raw_output: str) -> str:
    cleaned = (raw_output or "").replace("```json", "").replace("```", "").strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    return match.group(0).strip() if match else cleaned


def question_topic(question: str) -> str | None:
    lowered = normalize_text(question)
    if not lowered:
        return None
    for topic, patterns in QUESTION_TOPIC_PATTERNS.items():
        if any(pattern in lowered for pattern in patterns):
            return topic
    return None


def topic_already_asked(topic: str | None, questions_asked: list[str]) -> bool:
    if not topic:
        return False
    return any(question_topic(previous) == topic for previous in questions_asked)


def extract_local_intake_info(user_text: str) -> dict:
    lowered = normalize_text(user_text)
    info: dict[str, str] = {}

    if not lowered:
        return info

    duration_patterns = (
        # Weekday references: "since last friday", "since monday"
        r"\bsince\s+(?:last\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        # "past few days", "past 3 days", "past couple of weeks"
        r"\bpast\s+(?:few|couple\s+of|several|a\s+few)?\s*\d*\s*(?:day|days|week|weeks)\b",
        r"\bpast\s+(?:few|couple|several|a\s+few)\s+(?:days|weeks)\b",
        # "a few days ago", "a week ago", "couple of days ago"
        r"\b(?:a\s+few|few|couple\s+of)\s+(?:days|weeks)(?:\s+ago)?\b",
        # "3 days ago", "2 weeks back"
        r"\b\d+\s+(?:day|days|week|weeks)\s+(?:ago|back)\b",
        # "about 3 days", "about a week"
        r"\babout\s+(?:a\s+)?\d+\s+(?:day|days|week|weeks)\b",
        r"\babout\s+a\s+(?:day|week|month)\b",
        # "last week", "last month", "last year"
        r"\blast\s+(?:week|month|year)\b",
        # "more than a year", "more than 6 months", "over a year", "over 3 weeks"
        r"\bmore\s+than\s+(?:a|an|\d+)\s+(?:day|days|week|weeks|month|months|year|years)\b",
        r"\bover\s+(?:a|an|\d+)\s+(?:day|days|week|weeks|month|months|year|years)\b",
        r"\bfor\s+more\s+than\s+(?:a|an|\d+)\s+(?:day|days|week|weeks|month|months|year|years)\b",
        r"\bfor\s+over\s+(?:a|an|\d+)\s+(?:day|days|week|weeks|month|months|year|years)\b",
        # "almost a year", "nearly 2 weeks"
        r"\b(?:almost|nearly)\s+(?:a|an|\d+)\s+(?:day|days|week|weeks|month|months|year|years)\b",
        # Original precise patterns
        r"\bsince\s+(?:last\s+night|this\s+morning|this\s+afternoon|this\s+evening|yesterday)\b",
        r"\bsince\s+(?:a|an)?\s*\d+(?:\s*-\s*\d+)?\s+(?:minute|minutes|hour|hours|day|days|week|weeks|month|months)\b",
        r"\bsince\s+(?:a|an)\s+(?:minute|minutes|hour|hours|day|days|week|weeks|month|months)\b",
        r"\bon and off for\s+\d+(?:\s*-\s*\d+)?\s+(?:minute|minutes|hour|hours|day|days|week|weeks|month|months)\b",
        r"\bfor\s+\d+(?:\s*-\s*\d+)?\s+(?:minute|minutes|hour|hours|day|days|week|weeks|month|months)\b",
        r"\bfor\s+(?:a|an)\s+(?:minute|minutes|hour|hours|day|days|week|weeks|month|months)\b",
    )
    for pattern in duration_patterns:
        match = re.search(pattern, lowered)
        if match:
            info["duration"] = match.group(0)
            break

    for hint, pattern in _body_area_patterns():
        if pattern.search(lowered):
            info.setdefault("location", hint)
            break

    if any(term in lowered for term in ("comes and goes", "on and off", "constant", "cramp", "cramps", "painful", "pain", "sharp", "dull", "burning", "throbbing")):
        info.setdefault("severity_pattern", "symptoms fluctuate")

    if any(phrase in lowered for phrase in ("no nausea", "no vomiting", "no vomit", "no fever", "no blood")):
        negatives = []
        if "no nausea" in lowered:
            negatives.append("nausea")
        if "no vomiting" in lowered or "no vomit" in lowered:
            negatives.append("vomiting")
        if "no fever" in lowered:
            negatives.append("fever")
        if "no blood" in lowered:
            negatives.append("blood")
        if negatives:
            info["associated_symptoms"] = f"denies {', '.join(negatives)}"

    if any(phrase in lowered for phrase in ("after eating", "after food", "after a meal", "after lunch", "after breakfast", "after dinner")):
        info["cause"] = "after eating"

    if any(phrase in lowered for phrase in ("when i lift", "whenever i lift", "after lifting", "heavy lifting", "while lifting", "when lifting", "lift something", "lifting something", "lifting heavy", "sit for", "sitting for", "after sitting", "while sitting", "long sitting", "sitting too long", "sit too long", "after driving", "long drive", "driving for", "poor posture", "bad posture", "forward bend", "bending forward", "standing for", "after standing", "walking for", "after walking")):
        info.setdefault("cause", "physical activity or posture")

    if any(phrase in lowered for phrase in ("overthinking", "anxiety", "stress", "alone", "not busy", "lonely")):
        info.setdefault("cause", "stress or anxiety")

    if any(
        phrase in lowered
        for phrase in (
            "sleep very late",
            "sleep late",
            "slept properly",
            "have not slept",
            "haven't slept",
            "havent slept",
            "not sleeping",
            "woke up in between",
            "wake up in between",
            "sleep disturbances",
            "trouble sleeping",
            "trouble falling asleep",
            "trouble falling",
            "hard to fall asleep",
            "cant fall asleep",
            "cant sleep",
            "difficulty sleeping",
            "difficulty falling",
            "poor sleep",
            "bad sleep",
            "not slept",
            "insomnia",
        )
    ):
        info.setdefault("pattern", "sleep disturbance")

    if any(phrase in lowered for phrase in ("worse", "getting worse", "severe", "very bad", "intense", "can not tolerate", "cannot tolerate")):
        info.setdefault("severity", "worse")

    return info


def looks_like_intake_wrapup(user_text: str) -> bool:
    lowered = normalize_text(user_text)
    if not lowered:
        return False
    return any(
        phrase in lowered
        for phrase in (
            "i have mentioned everything",
            "i have mentioned all",
            "i have summarized everything",
            "i have summarised everything",
            "i have summarize everything",
            "i have summarise everything",
            "that is all",
            "thats all",
            "that's all",
            "i am done",
            "no more",
            "nothing else",
            "i have said everything",
        )
    )


def compact_state_summary(state: GraphState) -> str:
    collected = state.get("collected_data") or state.get("collected_info") or {}
    compact_collected = "None" if not collected else " | ".join([f"{k}={v}" for k, v in collected.items() if v])
    bookings = state.get("upcoming_bookings") or state.get("confirmed_bookings") or []
    compact_bookings = "None"
    if bookings:
        booking_parts = []
        for booking in bookings[:3]:
            if not isinstance(booking, dict):
                continue
            doctor = booking.get("doctor") or booking.get("doctor_name") or "Doctor"
            time = booking.get("time") or booking.get("start_time")
            if doctor and time:
                booking_parts.append(f"{doctor} @ {time}")
            elif doctor:
                booking_parts.append(str(doctor))
        if booking_parts:
            compact_bookings = " | ".join(booking_parts)

    # Build a brief history of analyzed documents so the supervisor never forgets
    doc_history = state.get("analyzed_documents") or []
    compact_docs = "None"
    if doc_history:
        doc_parts = []
        for doc in doc_history[-4:]:  # keep last 4 to avoid bloating prompt
            if not isinstance(doc, dict):
                continue
            dtype = doc.get("document_type") or "document"
            dept = doc.get("department") or "?"
            fname = doc.get("file_name") or "file"
            short_summary = (doc.get("summary") or "")[:80]
            doc_parts.append(f"{dtype}({fname}→{dept}): {short_summary}")
        compact_docs = " || ".join(doc_parts)

    return (
        f"awaiting={state.get('awaiting')} | intent={state.get('active_intent') or state.get('intent')} | "
        f"collected={compact_collected} | doctors={compact_bookings} | "
        f"analyzed_docs=[{compact_docs}]"
    )


def compact_fact_summary(data: dict | None) -> str:
    if not data:
        return "None"
    parts = []
    for key, value in data.items():
        if value in (None, "", [], {}):
            continue
        parts.append(f"{key}={value}")
    return "; ".join(parts) if parts else "None"


def compact_booking_summary(bookings: list[dict] | None, limit: int = 3) -> str:
    if not bookings:
        return "None"

    parts = []
    for booking in bookings[:limit]:
        if not isinstance(booking, dict):
            continue
        doctor = booking.get("doctor") or booking.get("doctor_name") or "Doctor"
        department = booking.get("department")
        time = booking.get("time") or booking.get("start_time")
        chunk = doctor
        details = []
        if department:
            details.append(str(department))
        if time:
            details.append(str(time))
        if details:
            chunk = f"{chunk} ({', '.join(details)})"
        parts.append(chunk)
    return " | ".join(parts) if parts else "None"


def compact_option_summary(
    items: list[dict] | None,
    label_key: str,
    extra_keys: list[str] | None = None,
    limit: int = 3,
) -> str:
    if not items:
        return "None"

    extra_keys = extra_keys or []
    parts = []
    for index, item in enumerate(items[:limit], start=1):
        if not isinstance(item, dict):
            continue
        label = item.get(label_key) or "Unknown"
        extras = []
        for key in extra_keys:
            value = item.get(key)
            if value in (None, "", [], {}):
                continue
            if key == "experience_years":
                try:
                    years = int(value)
                except (TypeError, ValueError):
                    years = value
                if isinstance(years, int):
                    suffix = "year" if years == 1 else "years"
                    extras.append(f"{years} {suffix} experience")
                else:
                    extras.append(f"{years} years experience")
            else:
                extras.append(f"{key}={value}")
        suffix = f" ({'; '.join(extras)})" if extras else ""
        parts.append(f"{index}. {label}{suffix}")
    return " | ".join(parts) if parts else "None"


def next_missing_intake_question(collected: dict | None, questions_asked: list[str] | None, default_question: str) -> str:
    collected = collected or {}
    questions_asked = questions_asked or []
    asked_topics = {topic for topic in (question_topic(question) for question in questions_asked) if topic}

    fallback_questions = [
        ("duration", "How long have you been feeling this way?"),
        ("location", "Can you point to the exact area of your body that feels affected, if there is one?"),
        ("pattern", "Does the discomfort feel constant, or does it come and go?"),
        ("cause", "Did anything seem to trigger this, like a meal, activity, stress, or new medicine?"),
        ("associated_symptoms", "Have you noticed any other symptoms such as fever, vomiting, rash, cough, weakness, or swelling?"),
        ("history", "Have you had anything like this before?"),
        ("medications", "Are you taking any medicines or tablets right now?"),
        ("severity", "Is it getting better, worse, or staying about the same?"),
    ]

    for topic, question in fallback_questions:
        if topic in asked_topics:
            continue
        if topic == "duration" and collected.get("duration"):
            continue
        if topic == "location" and collected.get("location"):
            continue
        if topic == "pattern" and (collected.get("severity_pattern") or collected.get("pattern")):
            continue
        if topic == "cause" and (collected.get("cause") or collected.get("trigger") or collected.get("onset")):
            continue
        if topic == "associated_symptoms" and collected.get("associated_symptoms"):
            continue
        if topic == "history" and collected.get("history"):
            continue
        if topic == "medications" and collected.get("medications"):
            continue
        return question

    return default_question
