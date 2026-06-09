import re
from datetime import date, timedelta

from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import SupervisorDecision, UserRequestUnderstanding
from app.agents.state import GraphState
from app.inference.llm import generate_router_text


parser = PydanticOutputParser(pydantic_object=SupervisorDecision)
understanding_parser = PydanticOutputParser(pydantic_object=UserRequestUnderstanding)

KNOWN_DEPARTMENTS = {
    "general physician": "General Physician",
    "general": "General Physician",
    "physician": "General Physician",
    "gastroenterology": "Gastroenterology",
    "gastro": "Gastroenterology",
    "cardiology": "Cardiology",
    "cardiologist": "Cardiology",
    "heart": "Cardiology",
    "neurology": "Neurology",
    "neurologist": "Neurology",
    "orthopedics": "Orthopedics",
    "orthopedic": "Orthopedics",
    "ortho": "Orthopedics",
    "oncology": "Oncology",
    "oncologist": "Oncology",
    "pulmonology": "Pulmonology",
    "pulmonologist": "Pulmonology",
    "psychiatry": "Psychiatry",
    "psychiatrist": "Psychiatry",
    "nephrology": "Nephrology",
    "nephrologist": "Nephrology",
    "endocrinology": "Endocrinology",
    "endocrinologist": "Endocrinology",
    "hematology": "Hematology",
    "hematologist": "Hematology",
    "dermatology": "Dermatology",
    "dermatologist": "Dermatology",
    "skin": "Dermatology",
}


def _route(next_agent: str, **updates):
    return {
        "next_agent": next_agent,
        "supervisor_checked_input": True,
        **updates,
    }


def _close_chat():
    return _route(
        "finish",
        awaiting=None,
        chat_closed=True,
        final_response="Take care. You can come back anytime if you need help.",
    )


def _clean_json(raw_output: str) -> str:
    return raw_output.replace("```json", "").replace("```", "").strip()


def _understand_user_request(state: GraphState) -> UserRequestUnderstanding | None:
    user_input = state.get("user_input") or ""
    if not user_input.strip():
        return None

    prompt = f"""
You are the natural-language understanding layer for a hospital assistant.

Classify the patient's latest message dynamically from meaning and context. Do not
force the message into the current awaiting state if the patient has changed topic.

Current date: {date.today().isoformat()}
Current state:
- awaiting: {state.get("awaiting")}
- intent: {state.get("intent")}
- symptoms: {state.get("symptoms") or []}
- target_department: {state.get("target_department")}
- selected_doctor: {state.get("selected_doctor_name")}
- patient_profile: {state.get("patient_profile") or "Unknown"}
- active_appointments: {state.get("active_appointments") or state.get("confirmed_bookings") or []}

Latest message:
{user_input}

Action meanings:
- profile_query: asks account/profile details such as name, age, blood group, health issues, phone, email, address.
- symptom_or_care: describes symptoms, asks medical help, says pain/illness is present, or changes to a new health concern.
- direct_booking: asks to see/book/consult a doctor, department, specialist, date, or named doctor.
- booking_lookup: asks to see, list, show, or check upcoming/previous bookings or appointments.
- cancel_appointment: wants to cancel an appointment.
- end_chat: wants to end/close/stop the chat.
- thanks_only: only says thanks/thank you without asking to end.
- non_medical: asks for something unrelated to healthcare or unsafe, such as weapons, explosives, bombs, crackers/fireworks construction, hacking, recipes, homework, entertainment, or general facts.
- continue_current: answers the current question/menu without changing topic.
- unclear: cannot infer.

If a department, doctor, or appointment date is explicitly requested, extract it.
If the user says today/tomorrow/next day, convert it to YYYY-MM-DD using Current date.
Appointment dates are allowed only from today through 7 days ahead.
If the user says only "doctor" without a specific doctor name, leave requested_doctor_name null.

Return only JSON:
{understanding_parser.get_format_instructions()}
""".strip()

    raw_output = generate_router_text(
        prompt,
        node_name="supervisor",
        chat_history=state.get("conversation_history"),
        chat_summary=state.get("chat_summary"),
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
    for keyword, department in KNOWN_DEPARTMENTS.items():
        if keyword in lowered:
            return department
    return None


def _looks_like_booking_or_department_request(text: str) -> bool:
    lowered = _normalise_text(text)
    return any(
        phrase in lowered
        for phrase in (
            "appointment",
            "book",
            "booking",
            "doctor",
            "dr",
            "department",
            "specialist",
            "consult",
            "see a",
            "see an",
            "want cardiology",
            "want dermatology",
            "want neurology",
            "want orthopedics",
            "want gastroenterology",
            "want pulmonology",
            "want psychiatry",
            "want nephrology",
            "want endocrinology",
            "want hematology",
            "want oncology",
        )
    )


def _looks_like_booking_lookup(text: str) -> bool:
    lowered = _normalise_text(text)
    booking_terms = (
        "upcoming booking",
        "upcoming bookings",
        "upcoming appointment",
        "upcoming appointments",
        "previous booking",
        "previous bookings",
        "previous appointment",
        "previous appointments",
        "my bookings",
        "my appointments",
        "show bookings",
        "show appointments",
        "booking history",
        "appointment history",
    )
    return any(term in lowered for term in booking_terms)


def _looks_like_non_medical_or_unsafe(text: str) -> bool:
    lowered = _normalise_text(text)
    if not lowered:
        return False

    unsafe_terms = (
        "bomb",
        "explosive",
        "explosives",
        "detonator",
        "diwali cracker",
        "firecracker",
        "firework",
        "gun",
        "weapon",
        "poison",
        "hack",
        "malware",
        "sex",
        "drug",
    )
    if any(term in lowered for term in unsafe_terms):
        return True

    off_topic_phrases = (
        "write code",
        "create website",
        "stock price",
        "weather",
        "movie",
        "recipe",
        "homework",
        "tell me a joke",
    )
    return any(phrase in lowered for phrase in off_topic_phrases)


def _non_medical_response() -> str:
    return (
        "I cannot help with that because this assistant is only for health-related "
        "support, doctor appointments, and safe wellbeing conversations. If this is "
        "urgent or could harm anyone, please contact local emergency services. "
        "Would you like help with symptoms, booking or cancelling a doctor appointment, "
        "or a general mental-health conversation?"
    )


def _format_booking_lookup_response(state: GraphState) -> str:
    bookings = state.get("active_appointments") or state.get("confirmed_bookings") or []
    if not bookings:
        return (
            "I could not find any upcoming bookings for your account right now. "
            "Would you like to book a doctor appointment or discuss symptoms?"
        )

    lines = ["Here are your upcoming bookings:"]
    for index, booking in enumerate(bookings, start=1):
        doctor = booking.get("doctor") or booking.get("doctor_name") or "Doctor"
        department = booking.get("department") or "Department not listed"
        time = booking.get("time") or booking.get("start_time") or "time not listed"
        lines.append(f"{index}. {doctor} - {department} - {time}")
    lines.append("")
    lines.append("You can also use the Upcoming bookings button to cancel or change eligible bookings.")
    return "\n".join(lines)


def _extract_requested_doctor(text: str) -> str | None:
    lowered = text.strip().lower()
    if "dr." not in lowered and "doctor" not in lowered:
        return None

    stop_words = (
        " for ",
        " in ",
        " at ",
        " on ",
        " tomorrow",
        " today",
        " appointment",
        " booking",
        " book",
    )
    doctor_text = text.strip()
    for prefix in ("book appointment with", "book with", "appointment with", "with"):
        index = doctor_text.lower().find(prefix)
        if index >= 0:
            doctor_text = doctor_text[index + len(prefix):].strip()
            break

    for marker in ("dr.", "doctor"):
        index = doctor_text.lower().find(marker)
        if index >= 0:
            doctor_text = doctor_text[index:].strip()
            break

    for stop_word in stop_words:
        index = doctor_text.lower().find(stop_word)
        if index > 0:
            doctor_text = doctor_text[:index].strip()

    doctor_text = doctor_text.strip(" .,-")
    if _normalise_text(doctor_text) in {"dr", "doctor", "a doctor", "the doctor"}:
        return None
    if len(doctor_text) < 4:
        return None
    return doctor_text or None


def _extract_requested_date(text: str) -> str | None:
    lowered = _normalise_text(text)
    today = date.today()

    if "today" in lowered:
        return today.isoformat()
    if "tomorrow" in lowered:
        return (today + timedelta(days=1)).isoformat()

    month_numbers = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12,
    }
    month_match = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
        r"(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|"
        r"aug|august|sep|sept|september|oct|october|nov|november|dec|december)\b",
        lowered,
    )
    if month_match:
        day = int(month_match.group(1))
        month = month_numbers[month_match.group(2)]
        year = today.year
        try:
            parsed = date(year, month, day)
        except ValueError:
            return None
        if parsed < today:
            try:
                parsed = date(year + 1, month, day)
            except ValueError:
                return None
        return parsed.isoformat()

    for word in lowered.split():
        try:
            return date.fromisoformat(word).isoformat()
        except ValueError:
            continue

    return None


def _normalise_requested_date(value: str | None, user_input: str) -> str | None:
    if value:
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            pass
    return _extract_requested_date(user_input)


def _looks_like_profile_query(text: str) -> bool:
    lowered = _normalise_text(text)
    if not lowered:
        return False

    profile_terms = (
        "my name",
        "my age",
        "name and age",
        "age and name",
        "blood group",
        "health issue",
        "health issues",
        "my mobile",
        "mobile number",
        "phone number",
        "my email",
        "my address",
        "my profile",
        "profile details",
        "who am i",
    )
    return any(term in lowered for term in profile_terms)


def _looks_like_simple_thanks(text: str) -> bool:
    lowered = _normalise_text(text)
    return lowered in {
        "thanks",
        "thank you",
        "thankyou",
        "thanks a lot",
        "thank you so much",
    }


def _has_active_care_context(state: GraphState) -> bool:
    return bool(
        state.get("awaiting")
        or state.get("intent")
        or state.get("symptoms")
        or state.get("target_department")
        or state.get("booking_active")
        or state.get("remedy_given")
        or state.get("persisting")
        or state.get("doctor_options")
        or state.get("slot_options")
        or state.get("confirmed_booking")
    )


def _looks_like_symptom_or_care_request(text: str) -> bool:
    lowered = _normalise_text(text)
    if not lowered:
        return False

    symptom_terms = (
        "pain",
        "ache",
        "fever",
        "cough",
        "cold",
        "nausea",
        "vomit",
        "dizzy",
        "dizziness",
        "headache",
        "injury",
        "swelling",
        "bleeding",
        "rash",
        "itching",
        "breathing",
        "breath",
        "chest",
        "leg",
        "back",
        "ear",
        "throat",
        "stomach",
        "severe",
        "mild",
        "symptom",
        "symptoms",
        "not feeling well",
        "having",
        "need help",
        "medical help",
    )
    return any(term in lowered for term in symptom_terms)


def _should_interrupt_current_menu_for_symptoms(state: GraphState, text: str) -> bool:
    if not _looks_like_symptom_or_care_request(text):
        return False

    return state.get("awaiting") in {
        "doctor_selection",
        "slot_selection",
        "cancellation_selection",
        "end_confirmation",
    }


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
        target_department=None,
        requested_department=None,
        requested_doctor_name=None,
    )


def _profile_response(state: GraphState, requested_fields: list[str] | None = None) -> str | None:
    profile = state.get("patient_profile") or {}
    if not profile:
        return "I could not find your profile details in this session. Please log in again."

    user_input = state.get("user_input") or ""
    lowered = _normalise_text(user_input)
    allowed_fields = {
        "name",
        "age",
        "blood_group",
        "health_issues",
        "mobile_number",
        "email",
        "address",
    }
    fields = [field for field in (requested_fields or []) if field in allowed_fields]

    if not fields and ("who am i" in lowered or "profile" in lowered):
        fields = ["name", "age", "blood_group", "health_issues"]
    elif not fields:
        requested = {
            "name": ("name", "my name"),
            "age": ("age", "my age"),
            "blood_group": ("blood group",),
            "health_issues": ("health issue", "health issues"),
            "mobile_number": ("mobile", "phone"),
            "email": ("email",),
            "address": ("address",),
        }
        for field, markers in requested.items():
            if any(marker in lowered for marker in markers):
                fields.append(field)

    if not fields:
        fields = ["name", "age"]

    labels = {
        "name": "name",
        "age": "age",
        "blood_group": "blood group",
        "health_issues": "health issues",
        "mobile_number": "mobile number",
        "email": "email",
        "address": "address",
    }
    values = []
    for field in fields:
        value = profile.get(field)
        if value:
            values.append(f"{labels[field]} is {value}")

    if not values:
        return "I could not find those profile details in your account."

    name = profile.get("name") or "there"
    return f"Hello {name}, your " + " and your ".join(values) + "."


def _looks_like_end_chat(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered:
        return False

    exact = {
        "bye",
        "goodbye",
        "end",
        "end chat",
        "close chat",
        "quit",
        "done",
        "that's all",
        "that is all",
        "thanks",
        "thank you",
        "no thanks",
        "no thank you",
        "nothing else",
    }
    return lowered in exact or any(
        phrase in lowered
        for phrase in (
            "end the chat",
            "stop the chat",
            "finish the chat",
            "i am done",
            "i'm done",
            "no more help",
        )
    )


def _looks_like_more_help(text: str) -> bool:
    lowered = text.strip().lower()
    return lowered in {"no", "continue", "more help", "help me"} or any(
        phrase in lowered
        for phrase in (
            "need more",
            "something else",
            "other help",
        )
    )


def _confirms_end_chat(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered:
        return False

    exact = {
        "yes",
        "y",
        "yeah",
        "yep",
        "ya",
        "sure",
        "ok",
        "okay",
        "please",
        "confirm",
        "confirmed",
    }
    return lowered in exact or _looks_like_end_chat(lowered)


def _dynamic_route(state: GraphState) -> dict | None:
    if state.get("supervisor_checked_input"):
        return None

    user_input = (state.get("user_input") or "").strip()
    if not user_input:
        return None

    understanding = _understand_user_request(state)
    action = understanding.action if understanding else None

    if action == "profile_query" or (not understanding and _looks_like_profile_query(user_input)):
        return _route(
            "finish",
            final_response=_profile_response(state, understanding.profile_fields if understanding else None),
        )

    if (
        action == "non_medical"
        or (not understanding and _looks_like_non_medical_or_unsafe(user_input))
        or _looks_like_non_medical_or_unsafe(user_input)
    ):
        return _route(
            "finish",
            awaiting=None,
            chat_closed=False,
            final_response=_non_medical_response(),
        )

    if action == "booking_lookup" or _looks_like_booking_lookup(user_input):
        return _route(
            "finish",
            awaiting=state.get("awaiting"),
            chat_closed=False,
            final_response=_format_booking_lookup_response(state),
        )

    if action == "cancel_appointment":
        return _route(
            "appointment_booker",
            intent="direct_booking",
            awaiting=None,
        )

    requested_department = (
        understanding.requested_department
        if understanding and understanding.requested_department
        else None
    )
    requested_doctor_name = (
        understanding.requested_doctor_name
        if understanding and understanding.requested_doctor_name
        else None
    )
    requested_date = _normalise_requested_date(
        understanding.requested_date if understanding else None,
        user_input,
    )

    if understanding and action == "direct_booking":
        can_override_department = _looks_like_booking_or_department_request(user_input)
        if not requested_department and can_override_department:
            requested_department = _extract_requested_department(user_input)
        if not requested_doctor_name:
            requested_doctor_name = _extract_requested_doctor(user_input)

    if not understanding:
        can_override_department = _looks_like_booking_or_department_request(user_input)
        requested_department = _extract_requested_department(user_input) if can_override_department else None
        requested_doctor_name = _extract_requested_doctor(user_input)
        requested_date = _extract_requested_date(user_input)

    if (
        action == "direct_booking"
        and not requested_department
        and not requested_doctor_name
        and state.get("symptoms")
        and not state.get("target_department")
    ):
        return _route(
            "medical_rag",
            intent="direct_booking",
            awaiting=None,
            requested_date=requested_date,
        )

    if action == "direct_booking" or requested_department or requested_doctor_name:
        updates = {
            "intent": "direct_booking",
            "awaiting": None,
            "doctor_options": [],
            "slot_options": [],
        }
        if requested_department:
            updates["target_department"] = requested_department
            updates["requested_department"] = requested_department
        if requested_doctor_name:
            updates["requested_doctor_name"] = requested_doctor_name
        if requested_date:
            updates["requested_date"] = requested_date
        return _route("appointment_booker", **updates)

    if requested_date and (
        state.get("target_department")
        or state.get("selected_doctor_id")
        or state.get("doctor_options")
        or state.get("intent") == "direct_booking"
    ):
        return _route(
            "appointment_booker",
            intent="direct_booking",
            awaiting=None,
            requested_date=requested_date,
        )

    if _should_interrupt_current_menu_for_symptoms(state, user_input):
        return _route_new_symptoms()

    if state.get("awaiting") == "end_confirmation":
        if action == "symptom_or_care":
            return _route_new_symptoms()
        if _confirms_end_chat(user_input):
            return _close_chat()
        if _looks_like_more_help(user_input):
            return _route(
                "finish",
                awaiting=None,
                chat_closed=False,
                intent=None,
                final_response=(
                    "Sure, I am still here. Tell me what you need next - symptoms, "
                    "another appointment, or appointment cancellation."
                ),
            )

    if action == "thanks_only" and not _has_active_care_context(state):
        return _route(
            "finish",
            awaiting=None,
            chat_closed=False,
            final_response=(
                "You're welcome. Tell me your symptoms, or let me know if you want "
                "to book or cancel an appointment."
            ),
        )

    if action == "end_chat" or (not understanding and _looks_like_end_chat(user_input)):
        return _route(
            "finish",
            awaiting="end_confirmation",
            chat_closed=False,
            final_response=(
                "Would you like to end the chat now? Reply yes to end, or tell me "
                "what else you need help with."
            ),
        )

    # First turn still belongs to triage; there is no existing flow to interrupt.
    if not state.get("intent") and not state.get("awaiting"):
        return None

    prompt = f"""
You are the Supervisor Router Agent for a hospital chat graph.

Your job is to decide whether the latest patient message should continue the current
agent state or interrupt/divert to a different agent.

Current state:
- awaiting: {state.get("awaiting")}
- intent: {state.get("intent")}
- symptoms: {state.get("symptoms") or []}
- severity: {state.get("severity")}
- target_department: {state.get("target_department")}
- booking_active: {state.get("booking_active")}
- confirmed_booking: {state.get("confirmed_booking")}
- confirmed_bookings: {state.get("confirmed_bookings") or []}
- patient_profile: {state.get("patient_profile") or "Unknown"}
- active_appointments: {state.get("active_appointments") or []}
- remedy_given: {state.get("remedy_given")}
- persisting: {state.get("persisting")}
- selected_doctor: {state.get("selected_doctor_name")}

Latest patient message:
{user_input}

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

Return only JSON:
{parser.get_format_instructions()}
""".strip()

    raw_output = generate_router_text(
        prompt,
        node_name="supervisor",
        chat_history=state.get("conversation_history"),
        chat_summary=state.get("chat_summary"),
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

    print(f"Supervisor router decision: {decision}")

    if decision.next_agent == "continue_current":
        return None

    next_agent = decision.next_agent
    updates = {}
    if decision.intent:
        updates["intent"] = decision.intent

    if next_agent == "remedy_agent":
        updates.update(
            {
                "awaiting": None,
                "intent": updates.get("intent") or "triage_symptoms",
                "remedy_requested": True,
                "doctor_options": [],
                "slot_options": [],
            }
        )
        if not state.get("symptoms"):
            next_agent = "triage_router"

    if next_agent in {"medical_rag", "appointment_booker"}:
        updates["intent"] = "direct_booking"
        updates["awaiting"] = None
        can_override_department = _looks_like_booking_or_department_request(user_input)
        requested_department = _extract_requested_department(user_input) if can_override_department else None
        requested_doctor_name = _extract_requested_doctor(user_input)
        requested_date = _extract_requested_date(user_input)
        if requested_department:
            updates["target_department"] = requested_department
            updates["requested_department"] = requested_department
        if requested_doctor_name:
            updates["requested_doctor_name"] = requested_doctor_name
        if requested_date:
            updates["requested_date"] = requested_date
        if next_agent == "medical_rag" and not state.get("symptoms"):
            next_agent = "triage_router"
        elif (
            next_agent == "appointment_booker"
            and state.get("symptoms")
            and not state.get("target_department")
            and not requested_department
            and not requested_doctor_name
        ):
            next_agent = "medical_rag"

    if next_agent == "triage_router":
        updates.update(
            {
                "awaiting": None,
                "intent": None,
                "remedy_requested": None,
                "booking_declined": None,
                "doctor_options": [],
                "slot_options": [],
            }
        )

    if next_agent == "finish":
        updates.update(
            {
                "awaiting": None,
                "chat_closed": True,
                "final_response": "Take care. You can come back anytime if you need help.",
            }
        )

    return _route(next_agent, **updates)


def supervisor_node(state: GraphState):
    awaiting = state.get("awaiting")

    print(
        f"SUPERVISOR | awaiting={awaiting} | intent={state.get('intent')} | "
        f"remedy_given={state.get('remedy_given')} | persisting={state.get('persisting')} | "
        f"collected={state.get('collected_info')} | "
        f"questions={len(state.get('questions_asked') or [])}"
    )

    if state.get("final_response"):
        return _route("finish")

    dynamic_route = _dynamic_route(state)
    if dynamic_route:
        return dynamic_route

    if state.get("remedy_requested") and not state.get("remedy_given"):
        return _route("remedy_agent")

    if awaiting == "conversation":
        return _route("conversation_agent")

    if awaiting == "remedy_check":
        return _route("remedy_agent")

    if awaiting == "end_confirmation":
        return _route(
            "finish",
            awaiting="end_confirmation",
            chat_closed=False,
            final_response=(
                "Please reply yes to end the chat, or tell me what else you need help with."
            ),
        )

    if awaiting in {
        "symptom_follow_up",
        "doctor_selection",
        "slot_selection",
        "cancellation_selection",
        "date_selection",
    }:
        return _route("appointment_booker")

    if not state.get("intent"):
        return _route("triage_router")

    if (
        state.get("intent") == "direct_booking"
        and state.get("symptoms")
        and not state.get("target_department")
    ):
        return _route("medical_rag")

    if state.get("intent") == "direct_booking":
        return _route("appointment_booker")

    if state.get("intent") and not _conversation_complete(state):
        return _route("conversation_agent")

    if not state.get("remedy_given"):
        return _route("remedy_agent")

    if state.get("persisting") and not state.get("target_department"):
        return _route("medical_rag")

    if state.get("persisting") and state.get("target_department"):
        return _route("appointment_booker")

    return _route("finish")


def _conversation_complete(state: GraphState) -> bool:
    if not state.get("symptoms"):
        return False

    if state.get("awaiting") == "conversation":
        return False

    collected = state.get("collected_info") or {}
    questions_asked = state.get("questions_asked") or []

    has_duration = bool(collected.get("duration"))
    has_location = bool(collected.get("location"))
    has_pattern = bool(collected.get("severity_pattern") or collected.get("pattern"))
    has_cause = bool(
        collected.get("cause")
        or collected.get("trigger")
        or collected.get("onset")
    )
    has_context = any(
        collected.get(key)
        for key in (
            "associated_symptoms",
            "existing_conditions",
            "medications",
            "allergies",
            "lifestyle",
            "daily_activity",
            "history",
        )
    )

    if len(questions_asked) >= 8:
        return True

    return has_duration and has_location and has_pattern and has_cause and has_context


def route_from_supervisor(state: GraphState):
    return state.get("next_agent", "finish")
