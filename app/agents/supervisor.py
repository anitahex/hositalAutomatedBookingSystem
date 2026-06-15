import re
from datetime import date, timedelta

from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import SupervisorDecision, UserRequestUnderstanding
from app.agents.state import GraphState
from app.inference.llm import generate_router_text
from app.services.appointments import normalize_department_name
from app.services.memory_policy import get_memory_policy


parser = PydanticOutputParser(pydantic_object=SupervisorDecision)
understanding_parser = PydanticOutputParser(pydantic_object=UserRequestUnderstanding)
MEMORY_POLICY = get_memory_policy("supervisor")

# 100% STATIC CACHEABLE PREFIXES
STATIC_UNDERSTANDING_PROMPT = """You are the natural-language understanding layer for a hospital assistant.
Classify the latest patient message using the conversation history already provided.

Action meanings:
- profile_query: asks account/profile details such as name, age, blood group, health issues, phone, email, address.
- symptom_or_care: describes symptoms, asks medical help, says pain/illness is present, or changes to a new health concern.
- direct_booking: asks to see/book/consult a doctor, department, specialist, date, or named doctor.
- booking_lookup: asks to see, list, show, or check upcoming/previous bookings or appointments.
- cancel_appointment: wants to cancel an appointment.
- end_chat: wants to end/close/stop the chat.
- thanks_only: only says thanks/thank you without asking to end.
- non_medical: asks for something unrelated to healthcare or unsafe, such as weapons, explosives, bombs, crackers, hacking, recipes, homework.
- continue_current: answers the current question/menu without changing topic.
- unclear: cannot infer.

If a department, doctor, or appointment date is explicitly requested, extract it.
If the user says today/tomorrow/next day, convert it to YYYY-MM-DD.
Appointment dates are allowed only from today through 7 days ahead.
If the user says only "doctor" without a specific doctor name, leave requested_doctor_name null.

Return ONLY valid JSON matching this exact structure:
{"action":"string","profile_fields":["string"],"requested_department":"string or null","requested_doctor_name":"string or null","requested_date":"YYYY-MM-DD or null","reason":"string"}"""

STATIC_SUPERVISOR_PROMPT = """You are the Supervisor Router Agent for a hospital chat graph.
Your job is to decide whether the latest patient message should continue the current agent state or interrupt/divert to a different agent.

Agent choices:
- continue_current: patient is answering the current question/menu.
- triage_router: patient gives new symptoms or changes the medical problem.
- conversation_agent: patient is providing/needs intake details before remedy.
- remedy_agent: patient asks for remedy, suggestions, relief, home care, or responds to remedy follow-up.
- medical_rag: symptoms are known and the patient wants the right department/doctor.
- appointment_booker: patient wants booking, appointment, doctor selection, slot selection, declines booking, or wants to cancel an appointment.
- finish: patient clearly ends the chat or says they are done/better.

Rules:
- If the patient asks for something new, do not trap them in the old awaiting state.
- Numeric doctor/slot choices, doctor names, slot choices, and booking declines should continue_current.
- If the patient asks for a remedy while in a booking menu, route to remedy_agent.
- If the patient asks for a doctor and symptoms are known but department is unknown, route to medical_rag.
- If the patient asks for a doctor and department/options are already known, route to appointment_booker.
- If the patient wants to cancel an appointment, route to appointment_booker.
- If the assistant just asked whether to end the chat, only finish when the patient confirms ending.

Return ONLY valid JSON matching this exact structure:
{"next_agent":"continue_current|triage_router|conversation_agent|remedy_agent|medical_rag|appointment_booker|finish","intent":"triage_symptoms|direct_booking|null","reason":"string"}"""

KNOWN_DEPARTMENTS = {
    "general physician": "General Physician", "general": "General Physician", "physician": "General Physician",
    "gastroenterology": "Gastroenterology", "gastro": "Gastroenterology",
    "cardiology": "Cardiology", "cardiologist": "Cardiology", "heart": "Cardiology",
    "neurology": "Neurology", "neurologist": "Neurology",
    "orthopedics": "Orthopedics", "orthopedic": "Orthopedics", "ortho": "Orthopedics",
    "oncology": "Oncology", "oncologist": "Oncology",
    "pulmonology": "Pulmonology", "pulmonologist": "Pulmonology",
    "psychiatry": "Psychiatry", "psychiatrist": "Psychiatry",
    "nephrology": "Nephrology", "nephrologist": "Nephrology",
    "endocrinology": "Endocrinology", "endocrinologist": "Endocrinology",
    "hematology": "Hematology", "hematologist": "Hematology",
    "dermatology": "Dermatology", "dermatologist": "Dermatology", "skin": "Dermatology",
}

_DEPARTMENT_HINT_WORDS = {
    "department",
    "dept",
    "doctor",
    "dr",
    "specialist",
    "specialists",
    "clinic",
    "consult",
}

def _route(next_agent: str, **updates):
    return {"next_agent": next_agent, "supervisor_checked_input": True, **updates}

def _close_chat():
    return _route("finish", awaiting=None, chat_closed=True, final_response="Take care. You can come back anytime if you need help.")

def _clean_json(raw_output: str) -> str:
    return raw_output.replace("```json", "").replace("```", "").strip()

def _get_minimal_profile(profile: dict | None) -> str:
    if not isinstance(profile, dict) or not profile:
        return "Unknown"
    return f"Name: {profile.get('name', 'Unknown')}, Age: {profile.get('age', 'Unknown')}, Health Issues: {profile.get('health_issues', 'None')}"

def _summarise_appointments(appointments: list[dict] | None, limit: int = 2) -> str:
    if not appointments: return "None"
    return "; ".join([f"{a.get('doctor', 'Doctor')} ({a.get('department', 'Dept')}) at {a.get('time', a.get('start_time', 'Unknown'))}" for a in appointments[:limit]])

def _summarise_booking(booking: dict | None) -> str:
    if not booking: return "None"
    return f"{booking.get('doctor', 'Doctor')} ({booking.get('department', 'Dept')}) at {booking.get('time', booking.get('start_time', 'Unknown'))}"

def _compact_state_summary(state: GraphState) -> str:
    parts = [
        f"awaiting={state.get('awaiting') or 'None'}",
        f"intent={state.get('intent') or 'None'}",
        f"symptoms={', '.join(state.get('symptoms') or []) or 'None'}",
        f"target_department={state.get('target_department') or 'None'}",
        f"selected_doctor={state.get('selected_doctor_name') or 'None'}",
        f"booking_active={bool(state.get('booking_active'))}",
        f"remedy_given={bool(state.get('remedy_given'))}",
        f"persisting={bool(state.get('persisting'))}",
        f"chat_closed={bool(state.get('chat_closed'))}",
        f"confirmed_booking={_summarise_booking(state.get('confirmed_booking'))}"
    ]
    return " | ".join(parts)

def _understand_user_request(state: GraphState) -> UserRequestUnderstanding | None:
    user_input = state.get("user_input") or ""
    if not user_input.strip():
        return None

    dynamic_user_prompt = f"""Current date: {date.today().isoformat()}
Current state: {_compact_state_summary(state)}
Minimal profile: {_get_minimal_profile(state.get("patient_profile"))}
Latest message: {user_input}"""

    raw_output = generate_router_text(
        system_prompt=STATIC_UNDERSTANDING_PROMPT,
        user_prompt=dynamic_user_prompt,
        node_name="supervisor",
        chat_summary=state.get("chat_summary"),
        include_history=True,
        history_turns=MEMORY_POLICY.prompt_window_turns,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    
    clean_json = _clean_json(raw_output)
    print(f"User request understanding JSON: {clean_json}")

    try:
        return understanding_parser.parse(clean_json)
    except Exception as exc:
        print(f"User request understanding parse failed: {exc}")
        return None

def _normalise_text(text: str) -> str:
    return " ".join(text.strip().lower().replace("?", " ").replace(",", " ").split())

def _extract_requested_department(text: str) -> str | None:
    lowered = _normalise_text(text)
    if not lowered:
        return None
    for keyword, department in KNOWN_DEPARTMENTS.items():
        if keyword in lowered:
            return department

    known_departments = set(KNOWN_DEPARTMENTS.values())
    words = [word for word in re.findall(r"[a-z]+", lowered) if word not in _DEPARTMENT_HINT_WORDS]
    for size in range(3, 0, -1):
        for index in range(len(words) - size + 1):
            candidate = " ".join(words[index:index + size])
            normalised = normalize_department_name(candidate)
            if normalised in known_departments:
                return normalised

    for marker in ("department", "dept", "specialist", "doctor"):
        if marker in lowered:
            prefix = lowered.split(marker, 1)[0].strip()
            prefix_words = [word for word in re.findall(r"[a-z]+", prefix) if word not in _DEPARTMENT_HINT_WORDS]
            for size in range(min(3, len(prefix_words)), 0, -1):
                candidate = " ".join(prefix_words[-size:])
                normalised = normalize_department_name(candidate)
                if normalised in known_departments:
                    return normalised
    return None

def _looks_like_generic_doctor_request(text: str) -> bool:
    lowered = _normalise_text(text)
    if not lowered: return False
    generic_phrases = ("a doctor", "the doctor", "any doctor", "see a doctor", "see doctor", "see a physician", "need a doctor", "want a doctor", "who is doctor", "doctor in", "doctor for", "specialist")
    return any(phrase in lowered for phrase in generic_phrases)

def _looks_like_booking_or_department_request(text: str) -> bool:
    lowered = _normalise_text(text)
    return any(
        phrase in lowered
        for phrase in (
            "appointment",
            "book",
            "doctor",
            "dr",
            "department",
            "specialist",
            "consult",
            "see a",
            "reschedule",
            "change date",
            "change appointment",
            "modify appointment",
            "update appointment",
        )
    )


def _looks_like_reschedule_request(text: str) -> bool:
    lowered = _normalise_text(text)
    return any(
        phrase in lowered
        for phrase in (
            "reschedule",
            "change date",
            "change my appointment",
            "change appointment",
            "modify appointment",
            "update appointment",
            "move appointment",
            "postpone appointment",
            "another date",
        )
    )

def _looks_like_booking_lookup(text: str) -> bool:
    lowered = _normalise_text(text)
    return any(term in lowered for term in ("upcoming booking", "upcoming appointment", "previous booking", "my bookings", "show appointments", "booking history"))

def _looks_like_clinical_note_query(text: str) -> bool:
    lowered = _normalise_text(text)
    return any(
        phrase in lowered
        for phrase in (
            "clinical note",
            "forwarded symptoms",
            "forwarded these symptoms",
            "what did you send",
            "what symptoms were forwarded",
            "what was forwarded",
            "symptoms forwarded",
            "symptoms sent",
            "note attached",
            "message to dr",
            "message to doctor",
            "tell me about those symptoms",
            "those symptoms",
            "that note",
            "summarize the note",
            "summarise the note",
            "summarize what you sent",
            "summarise what you sent",
        )
    )

def _looks_like_non_medical_or_unsafe(text: str) -> bool:
    lowered = _normalise_text(text)
    if not lowered: return False
    unsafe_terms = ("bomb", "explosive", "detonator", "firecracker", "gun", "weapon", "poison", "hack", "malware", "sex", "drug")
    if any(term in lowered for term in unsafe_terms): return True
    off_topic_phrases = ("write code", "create website", "stock price", "weather", "movie", "recipe", "homework", "tell me a joke")
    return any(phrase in lowered for phrase in off_topic_phrases)

def _non_medical_response() -> str:
    return ("I cannot help with that because this assistant is only for health-related support and doctor appointments. "
            "If this is urgent, please contact local emergency services. Would you like help with symptoms or booking?")

def _format_booking_lookup_response(state: GraphState) -> str:
    bookings = state.get("active_appointments") or state.get("confirmed_bookings") or []
    if not bookings:
        return "I could not find any upcoming bookings for your account right now. Would you like to book an appointment?"
    lines = ["Here are your upcoming bookings:"]
    for index, booking in enumerate(bookings, start=1):
        doctor = booking.get("doctor") or booking.get("doctor_name") or "Doctor"
        department = booking.get("department") or "Department not listed"
        time = booking.get("time") or booking.get("start_time") or "time not listed"
        can_modify = booking.get("can_modify")
        suffix = " - can change or cancel" if can_modify else " - locked within 24 hours"
        note = booking.get("booking_note")
        note_text = f" - clinical note: {note}" if note else ""
        lines.append(f"{index}. {doctor} - {department} - {time}{suffix}{note_text}")
    lines.append("")
    lines.append("If you want to change an appointment, tell me which one and I will guide you through it.")
    return "\n".join(lines)

def _format_clinical_note_response(state: GraphState) -> str:
    bookings = state.get("active_appointments") or state.get("confirmed_bookings") or []
    latest_booking = state.get("confirmed_booking")
    if isinstance(latest_booking, dict) and latest_booking.get("booking_note"):
        note = latest_booking.get("booking_note")
        doctor = latest_booking.get("doctor") or latest_booking.get("doctor_name") or "your doctor"
        time = latest_booking.get("time") or latest_booking.get("start_time") or "your appointment"
        return (
            f"I forwarded a clinical note to {doctor} for {time}.\n\n"
            f"Clinical note:\n{note}\n\n"
            "You can also see it in your upcoming appointment card."
        )

    for booking in reversed(bookings):
        if booking.get("booking_note"):
            doctor = booking.get("doctor") or booking.get("doctor_name") or "your doctor"
            time = booking.get("time") or booking.get("start_time") or "your appointment"
            note = booking.get("booking_note")
            return (
                f"I forwarded a clinical note to {doctor} for {time}.\n\n"
                f"Clinical note:\n{note}\n\n"
                "You can also see it in your upcoming appointment card."
            )

    if state.get("note_forwarded"):
        return "I've already forwarded your symptoms, but I could not find the saved clinical note in the current booking context."

    return "I do not see a forwarded clinical note on this booking yet. If you'd like, I can help forward the latest symptoms now."

def _extract_requested_doctor(text: str) -> str | None:
    original = text.strip()
    lowered = _normalise_text(original)
    if "dr" not in lowered and "doctor" not in lowered: return None
    if _looks_like_generic_doctor_request(original): return None
    
    doctor_text = original
    for prefix in ("book appointment with", "book with", "appointment with", "with"):
        index = doctor_text.lower().find(prefix)
        if index >= 0:
            doctor_text = doctor_text[index + len(prefix):].strip()
            break

    marker_match = re.search(r"\b(?:dr\.?|doctor)\b", doctor_text, flags=re.IGNORECASE)
    if marker_match:
        doctor_text = doctor_text[marker_match.start():].strip()
        doctor_text = re.sub(r"^\s*(?:dr\.?|doctor)\s+", "", doctor_text, flags=re.IGNORECASE)

    for stop_word in (" for ", " in ", " at ", " on ", " tomorrow", " today", " appointment", " booking", " department", " specialist"):
        index = doctor_text.lower().find(stop_word)
        if index > 0: doctor_text = doctor_text[:index].strip()

    doctor_text = doctor_text.strip(" .,-")
    compact = _normalise_text(doctor_text)
    if not compact or compact in {"dr", "doctor"}: return None
    if _looks_like_generic_doctor_request(doctor_text): return None
    doctor_tokens = [token for token in re.split(r"\s+", doctor_text) if re.search(r"[a-z]", token, flags=re.IGNORECASE)]
    if len(doctor_tokens) < 2: return None
    return " ".join(doctor_tokens) or None

def _extract_requested_date(text: str) -> str | None:
    lowered = _normalise_text(text)
    today = date.today()
    if "today" in lowered: return today.isoformat()
    if "tomorrow" in lowered: return (today + timedelta(days=1)).isoformat()
    
    month_match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b", lowered)
    month_numbers = {"jan":1,"january":1,"feb":2,"february":2,"mar":3,"march":3,"apr":4,"april":4,"may":5,"jun":6,"june":6,"jul":7,"july":7,"aug":8,"august":8,"sep":9,"sept":9,"september":9,"oct":10,"october":10,"nov":11,"november":11,"dec":12,"december":12}
    
    if month_match:
        day = int(month_match.group(1))
        month = month_numbers[month_match.group(2)]
        try:
            parsed = date(today.year, month, day)
            if parsed < today: parsed = date(today.year + 1, month, day)
            return parsed.isoformat()
        except ValueError:
            return None

    for word in lowered.split():
        try:
            return date.fromisoformat(word).isoformat()
        except ValueError:
            continue
    return None

def _normalise_requested_date(value: str | None, user_input: str) -> str | None:
    if value:
        try: return date.fromisoformat(value).isoformat()
        except ValueError: pass
    return _extract_requested_date(user_input)

def _looks_like_profile_query(text: str) -> bool:
    lowered = _normalise_text(text)
    return any(term in lowered for term in ("my name", "my age", "blood group", "health issue", "mobile number", "my email", "my address", "my profile", "who am i"))

def _looks_like_simple_thanks(text: str) -> bool:
    return _normalise_text(text) in {"thanks", "thank you", "thankyou", "thanks a lot", "thank you so much"}

def _has_active_care_context(state: GraphState) -> bool:
    return bool(state.get("awaiting") or state.get("intent") or state.get("symptoms") or state.get("target_department") or state.get("booking_active") or state.get("remedy_given"))

def _looks_like_symptom_or_care_request(text: str) -> bool:
    lowered = _normalise_text(text)
    return any(term in lowered for term in ("pain", "ache", "fever", "cough", "cold", "nausea", "vomit", "dizzy", "headache", "injury", "swelling", "bleeding", "rash", "itching", "chest", "leg", "back", "symptom", "not feeling well", "medical help"))

def _should_interrupt_current_menu_for_symptoms(state: GraphState, text: str) -> bool:
    if not _looks_like_symptom_or_care_request(text): return False
    return state.get("awaiting") in {"doctor_selection", "slot_selection", "cancellation_selection", "end_confirmation"}

def _route_new_symptoms():
    return _route(
        "triage_router",
        awaiting=None,
        intent=None,
        remedy_requested=None,
        booking_declined=None,
        doctor_options=[],
        slot_options=[],
        cancellation_options=[],
        reschedule_options=[],
        reschedule_date_options=[],
        reschedule_slot_options=[],
        selected_booking_id=None,
        target_department=None,
        requested_department=None,
        requested_doctor_name=None,
    )

def _profile_response(state: GraphState, requested_fields: list[str] | None = None) -> str | None:
    profile = state.get("patient_profile") or {}
    if not profile: return "I could not find your profile details in this session. Please log in again."
    return f"Hello {profile.get('name', 'there')}, your age is {profile.get('age', 'unknown')} and known health issues are {profile.get('health_issues', 'none')}."

def _looks_like_end_chat(text: str) -> bool:
    lowered = text.strip().lower()
    return lowered in {"bye", "goodbye", "end", "end chat", "close chat", "quit", "done", "that's all", "nothing else"} or any(phrase in lowered for phrase in ("end the chat", "stop the chat", "finish the chat", "i am done"))

def _looks_like_more_help(text: str) -> bool:
    lowered = text.strip().lower()
    return lowered in {"no", "continue", "more help", "help me"} or any(phrase in lowered for phrase in ("need more", "something else", "other help"))

def _confirms_end_chat(text: str) -> bool:
    lowered = text.strip().lower()
    return lowered in {"yes", "y", "yeah", "yep", "sure", "ok", "okay", "confirm"} or _looks_like_end_chat(lowered)

def _dynamic_route(state: GraphState) -> dict | None:
    if state.get("supervisor_checked_input"): return None
    user_input = (state.get("user_input") or "").strip()
    if not user_input: return None

    understanding = _understand_user_request(state)
    action = understanding.action if understanding else None

    if action == "profile_query" or (not understanding and _looks_like_profile_query(user_input)):
        return _route("finish", final_response=_profile_response(state, understanding.profile_fields if understanding else None))

    if action == "non_medical" or _looks_like_non_medical_or_unsafe(user_input):
        return _route("finish", awaiting=None, chat_closed=False, final_response=_non_medical_response())

    if action == "booking_lookup" or _looks_like_booking_lookup(user_input):
        return _route("finish", awaiting=state.get("awaiting"), chat_closed=False, final_response=_format_booking_lookup_response(state))

    if _looks_like_clinical_note_query(user_input):
        return _route("finish", awaiting=state.get("awaiting"), chat_closed=False, final_response=_format_clinical_note_response(state))

    if action == "cancel_appointment":
        return _route("appointment_booker", intent="direct_booking", awaiting=None)

    if _looks_like_reschedule_request(user_input):
        return _route("appointment_booker", intent="direct_booking", awaiting=None)

    requested_department = understanding.requested_department if understanding else None
    requested_doctor_name = understanding.requested_doctor_name if understanding else None
    requested_date = _normalise_requested_date(understanding.requested_date if understanding else None, user_input)

    if understanding and action == "direct_booking":
        can_override_department = _looks_like_booking_or_department_request(user_input)
        if not requested_department and can_override_department: requested_department = _extract_requested_department(user_input)
        if not requested_doctor_name: requested_doctor_name = _extract_requested_doctor(user_input)

    if not understanding:
        requested_department = _extract_requested_department(user_input) if _looks_like_booking_or_department_request(user_input) else None
        requested_doctor_name = _extract_requested_doctor(user_input)
        requested_date = _extract_requested_date(user_input)

    if action == "direct_booking" and not requested_department and not requested_doctor_name and state.get("symptoms") and not state.get("target_department"):
        return _route("medical_rag", intent="direct_booking", awaiting=None, requested_date=requested_date)

    if action == "direct_booking" or requested_department or requested_doctor_name:
        updates = {"intent": "direct_booking", "awaiting": None, "doctor_options": [], "slot_options": [], "department_match_source": "direct_request", "department_match_confidence": 1.0, "department_match_reason": "User explicitly requested a department or doctor.", "retrieval_attempted": False, "retrieval_confidence": 0.0}
        if requested_department:
            updates["target_department"] = requested_department
            updates["requested_department"] = requested_department
        if requested_doctor_name: updates["requested_doctor_name"] = requested_doctor_name
        if requested_date: updates["requested_date"] = requested_date
        return _route("appointment_booker", **updates)

    if requested_date and (state.get("target_department") or state.get("selected_doctor_id") or state.get("doctor_options") or state.get("intent") == "direct_booking"):
        return _route("appointment_booker", intent="direct_booking", awaiting=None, requested_date=requested_date)

    if _should_interrupt_current_menu_for_symptoms(state, user_input):
        return _route_new_symptoms()

    if state.get("awaiting") == "end_confirmation":
        if action == "symptom_or_care": return _route_new_symptoms()
        if _looks_like_reschedule_request(user_input):
            return _route("appointment_booker", intent="direct_booking", awaiting=None)
        if _confirms_end_chat(user_input): return _close_chat()
        if _looks_like_more_help(user_input):
            return _route("finish", awaiting=None, chat_closed=False, intent=None, final_response="Sure, I am still here. Tell me what you need next - symptoms, another appointment, or appointment cancellation.")

    if action == "thanks_only" and not _has_active_care_context(state):
        return _route("finish", awaiting=None, chat_closed=False, final_response="You're welcome. Tell me your symptoms, or let me know if you want to book or cancel an appointment.")

    if action == "end_chat" or (not understanding and _looks_like_end_chat(user_input)):
        return _route("finish", awaiting="end_confirmation", chat_closed=False, final_response="Would you like to end the chat now? Reply yes to end, or tell me what else you need help with.")

    if not state.get("intent") and not state.get("awaiting"):
        return None

    dynamic_user_prompt = f"""Current date: {date.today().isoformat()}
Current state: {_compact_state_summary(state)}
Minimal profile: {_get_minimal_profile(state.get("patient_profile"))}
Latest patient message: {user_input}"""

    raw_output = generate_router_text(
        system_prompt=STATIC_SUPERVISOR_PROMPT,
        user_prompt=dynamic_user_prompt,
        node_name="supervisor",
        chat_summary=state.get("chat_summary"),
        include_history=True,
        history_turns=MEMORY_POLICY.prompt_window_turns,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    
    clean_json = _clean_json(raw_output)
    print(f"Supervisor router JSON: {clean_json}")

    try:
        decision = parser.parse(clean_json)
    except Exception as exc:
        print(f"Supervisor router parse failed: {exc}")
        return None

    if decision.next_agent == "continue_current":
        return None

    next_agent = decision.next_agent
    updates = {}
    if decision.intent: updates["intent"] = decision.intent

    if next_agent == "remedy_agent":
        updates.update({"awaiting": None, "intent": updates.get("intent") or "triage_symptoms", "remedy_requested": True, "doctor_options": [], "slot_options": []})
        if not state.get("symptoms"): next_agent = "triage_router"

    if next_agent in {"medical_rag", "appointment_booker"}:
        updates["intent"] = "direct_booking"
        updates["awaiting"] = None
        can_override_department = _looks_like_booking_or_department_request(user_input)
        requested_department = _extract_requested_department(user_input) if can_override_department else None
        requested_doctor_name = _extract_requested_doctor(user_input)
        requested_date = _extract_requested_date(user_input)
        updates["department_match_source"] = "direct_request"
        updates["department_match_confidence"] = 1.0
        updates["department_match_reason"] = "User explicitly requested a department or doctor."
        updates["retrieval_attempted"] = False
        updates["retrieval_confidence"] = 0.0
        if requested_department:
            updates["target_department"] = requested_department
            updates["requested_department"] = requested_department
        if requested_doctor_name: updates["requested_doctor_name"] = requested_doctor_name
        if requested_date: updates["requested_date"] = requested_date
        
        if next_agent == "medical_rag" and not state.get("symptoms"):
            next_agent = "triage_router"
        elif next_agent == "appointment_booker" and state.get("symptoms") and not state.get("target_department") and not requested_department and not requested_doctor_name:
            next_agent = "medical_rag"

    if next_agent == "triage_router":
        updates.update({
            "awaiting": None,
            "intent": None,
            "remedy_requested": None,
            "booking_declined": None,
            "doctor_options": [],
            "slot_options": [],
            "reschedule_options": [],
            "reschedule_date_options": [],
            "reschedule_slot_options": [],
            "selected_booking_id": None,
        })

    if next_agent == "finish":
        updates.update({"awaiting": None, "chat_closed": True, "final_response": "Take care. You can come back anytime if you need help."})

    return _route(next_agent, **updates)

def supervisor_node(state: GraphState):
    awaiting = state.get("awaiting")
    print(f"SUPERVISOR | awaiting={awaiting} | intent={state.get('intent')} | collected={state.get('collected_info')}")

    if state.get("final_response"): return _route("finish")

    dynamic_route = _dynamic_route(state)
    if dynamic_route: return dynamic_route

    if state.get("remedy_requested") and not state.get("remedy_given"): return _route("remedy_agent")
    if awaiting == "conversation": return _route("conversation_agent")
    if awaiting == "remedy_check": return _route("remedy_agent")
    if awaiting == "end_confirmation": return _route("finish", awaiting="end_confirmation", chat_closed=False, final_response="Please reply yes to end the chat, or tell me what else you need help with.")
    if awaiting in {"symptom_follow_up", "doctor_selection", "slot_selection", "cancellation_selection", "date_selection", "reschedule_selection", "reschedule_date_selection", "reschedule_slot_selection"}: return _route("appointment_booker")
    if not state.get("intent"): return _route("triage_router")
    if state.get("intent") == "direct_booking" and state.get("symptoms") and not state.get("target_department"): return _route("medical_rag")
    if state.get("intent") == "direct_booking": return _route("appointment_booker")
    if state.get("intent") and not _conversation_complete(state): return _route("conversation_agent")
    if not state.get("remedy_given"): return _route("remedy_agent")
    if state.get("persisting") and not state.get("target_department"): return _route("medical_rag")
    if state.get("persisting") and state.get("target_department"): return _route("appointment_booker")

    return _route("finish")

def _conversation_complete(state: GraphState) -> bool:
    if not state.get("symptoms") or state.get("awaiting") == "conversation": return False
    collected = state.get("collected_info") or {}
    questions_asked = state.get("questions_asked") or []
    if len(questions_asked) >= 8: return True
    return bool(collected.get("duration") and collected.get("location") and (collected.get("severity_pattern") or collected.get("pattern")) and (collected.get("cause") or collected.get("trigger") or collected.get("onset")))

def route_from_supervisor(state: GraphState):
    return state.get("next_agent", "finish")
