"""
Appointment Booker Agent
------------------------
Handles symptom follow-up, doctor selection, and slot booking.
Remedy logic lives in remedy_agent.py.
"""

import re
from datetime import date, datetime, timedelta, timezone

from app.agents.state import GraphState
from app.agents.schemas import BookingMenuDecision
from app.agents.intake_utils import (
    compact_booking_summary,
    compact_fact_summary,
    compact_option_summary,
    compact_state_summary,
    extract_local_intake_info,
    next_missing_intake_question,
)
from app.inference.llm import generate_text
from app.services.memory_policy import get_memory_policy
from langchain_core.output_parsers import PydanticOutputParser
from app.services.appointments import (
    active_bookings_for_patient,
    available_doctors_by_name,
    available_doctors_by_name_on_date,
    available_doctors_for_department,
    available_doctors_for_department_on_date,
    available_slots_for_doctor,
    available_slots_for_doctor_on_date,
    book_selected_slot,
    cancel_booking,
    normalize_department_name,
    upcoming_bookings_for_patient,
    reschedule_options_for_booking,
    reschedule_patient_booking,
)

menu_parser = PydanticOutputParser(pydantic_object=BookingMenuDecision)
BOOKING_WINDOW_DAYS = 7
MEMORY_POLICY = get_memory_policy("appointment_booker")

# 100% STATIC CACHEABLE PREFIX
STATIC_MENU_PROMPT = """You are an appointment booking assistant interpreting the patient's latest reply.
Use meaning and the displayed options, not keyword matching.

Decide whether the patient selected an option, declined booking, requested symptom care/remedy instead, asked to cancel an appointment, or gave an unclear reply.
If they selected an option, copy the number, id, name, or time they used into selected_value.

Return ONLY valid JSON matching this exact structure:
{"action":"select_option|decline_booking|request_remedy|cancel_appointment|unclear","selected_value":"string or null","reason":"string"}"""


def _clean_json(raw_output: str) -> str:
    return raw_output.replace("```json", "").replace("```", "").strip()


def _date_options() -> list[dict[str, str]]:
    today = date.today()
    options = []
    for offset in range(BOOKING_WINDOW_DAYS + 1):
        day = today + timedelta(days=offset)
        if offset == 0:
            label = f"Today ({day.isoformat()})"
        elif offset == 1:
            label = f"Tomorrow ({day.isoformat()})"
        else:
            label = day.strftime("%a %d %b (%Y-%m-%d)")
        options.append({"label": label, "value": day.isoformat()})
    return options


def _valid_requested_date(value: str | None) -> bool:
    if not value:
        return False
    try:
        requested = date.fromisoformat(value)
    except ValueError:
        return False

    today = date.today()
    return today <= requested <= today + timedelta(days=BOOKING_WINDOW_DAYS)


def _date_selection_response(prefix: str | None = None):
    options = _date_options()
    option_lines = "\n".join(f"{index}. {option['label']}" for index, option in enumerate(options, start=1))
    message = (
        f"{prefix}\n\n" if prefix else ""
    ) + (
        "Which day would you prefer? You can choose one of these dates:\n"
        f"{option_lines}"
    )
    return {
        "awaiting": "date_selection",
        "date_options": options,
        "final_response": message,
    }


def _choose_date_option(user_input: str, options: list[dict]) -> str | None:
    text = user_input.strip().lower()
    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(options):
            return options[index]["value"]

    for option in options:
        label = str(option.get("label", "")).lower()
        value = str(option.get("value", "")).lower()
        if text == value or text in label:
            return option["value"]

    return None


_IST = timedelta(hours=5, minutes=30)


def _fmt_time(iso_str: str) -> str:
    """Format an already-IST naive timestamp for display: 'Today 2:30 PM' / 'Jun 27 9 AM'."""
    try:
        dt_ist = datetime.fromisoformat(str(iso_str))
        now_ist = datetime.now(timezone.utc).replace(tzinfo=None) + _IST
        today_ist = now_ist.date()
        tomorrow_ist = today_ist + timedelta(days=1)
        hour = dt_ist.hour % 12 or 12
        ampm = "AM" if dt_ist.hour < 12 else "PM"
        time_str = f"{hour}:{dt_ist.minute:02d} {ampm}" if dt_ist.minute else f"{hour} {ampm}"
        if dt_ist.date() == today_ist:
            return f"Today {time_str}"
        elif dt_ist.date() == tomorrow_ist:
            return f"Tomorrow {time_str}"
        else:
            return f"{dt_ist.strftime('%b %d')} {time_str}"
    except Exception:
        return str(iso_str)


def format_numbered_options(items: list[dict], label_key: str, extra_keys: list[str], bold_label: bool = False):
    _TIME_KEYS = {"next_available_time", "start_time", "end_time"}
    lines = []
    for index, item in enumerate(items, start=1):
        extra_parts = []
        for key in extra_keys:
            value = item.get(key)
            if value is None:
                continue
            if key == "experience_years":
                try:
                    years = int(value)
                except (TypeError, ValueError):
                    years = value
                if isinstance(years, int):
                    suffix = "year" if years == 1 else "years"
                    extra_parts.append(f"{years} {suffix} experience")
                else:
                    extra_parts.append(f"{years} years experience")
            elif key in _TIME_KEYS:
                extra_parts.append(_fmt_time(str(value)))
            else:
                extra_parts.append(str(value))
        extra = ", ".join(extra_parts)
        suffix = f" ({extra})" if extra else ""
        raw_label = item[label_key]
        label = _fmt_time(str(raw_label)) if label_key in _TIME_KEYS else str(raw_label)
        if bold_label:
            label = f"**{label}**"
        lines.append(f"{index}. {label}{suffix}")
    return "\n".join(lines)


def format_slot_options(slots: list[dict]) -> str:
    """Format a slot list as '1. Today 2:30 PM – 3 PM'.
    start_time/end_time are stored already in IST (naive), so no conversion is applied here."""
    now_ist = datetime.now(timezone.utc).replace(tzinfo=None) + _IST
    today_ist = now_ist.date()
    tomorrow_ist = today_ist + timedelta(days=1)

    def _hm(dt: datetime) -> str:
        h = dt.hour % 12 or 12
        ampm = "AM" if dt.hour < 12 else "PM"
        return f"{h}:{dt.minute:02d} {ampm}" if dt.minute else f"{h} {ampm}"

    lines = []
    for index, slot in enumerate(slots, start=1):
        try:
            s = datetime.fromisoformat(str(slot.get("start_time", "")))
            e = datetime.fromisoformat(str(slot["end_time"]))
            day = "Today" if s.date() == today_ist else ("Tomorrow" if s.date() == tomorrow_ist else s.strftime("%b %d"))
            lines.append(f"{index}. {day} {_hm(s)} – {_hm(e)}")
        except Exception:
            lines.append(f"{index}. {slot.get('start_time', '')}")
    return "\n".join(lines)


def _booking_list(state: GraphState) -> list[dict]:
    return list(state.get("upcoming_bookings") or state.get("confirmed_bookings") or [])


def choose_option(user_input: str, options: list[dict], id_key: str, name_key: str):
    text = user_input.strip().lower()

    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(options):
            return options[index]

    for option in options:
        if text == str(option[id_key]).lower():
            return option
        if name_key in option and text in str(option[name_key]).lower():
            return option

    return None


def _looks_like_cancellation(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in ("cancel", "cancell", "delete appointment", "remove appointment"))


def _looks_like_reschedule_request(text: str) -> bool:
    lowered = " ".join((text or "").lower().split())
    return any(
        phrase in lowered
        for phrase in (
            "reschedule",
            "change my appointment",
            "change appointment",
            "change the date",
            "change date",
            "modify appointment",
            "modify the appointment",
            "update appointment",
            "update the appointment",
            "move appointment",
            "postpone appointment",
            "shift appointment",
            "book another date",
            "another date",
        )
    )


def _looks_like_specific_doctor_name(value: str | None) -> bool:
    if not value:
        return False

    lowered = " ".join(str(value).strip().lower().split())
    if not lowered:
        return False

    if any(
        phrase in lowered
        for phrase in (
            "who is",
            "any doctor",
            "any physician",
            "a doctor",
            "the doctor",
            "available doctor",
            "available physician",
            "doctor in",
            "doctor for",
            "doctor at",
            "doctor from",
            "doctor department",
            "doctor specialist",
            "physician",
            "specialist",
            "psychiatrist",
            "cardiologist",
            "neurologist",
            "dermatologist",
            "gastroenterologist",
            "orthopedic",
            "orthopedics",
        )
    ):
        return False

    tokens = [token for token in re.split(r"\s+", str(value).strip()) if re.search(r"[a-z]", token, flags=re.IGNORECASE)]
    return len(tokens) >= 2


def _format_booking_options(bookings: list[dict]):
    lines = []
    for index, booking in enumerate(bookings, start=1):
        time_str = booking.get("time") or booking.get("start_time") or "Unknown time"
        lines.append(
            f"{index}. {booking['doctor']} ({booking['department']}) at {time_str} "
            f"- Reference: {booking['booking_id']}"
        )
    return "\n".join(lines)


def _format_department_options(departments: list[dict]) -> str:
    lines = []
    for index, item in enumerate(departments, start=1):
        department = item.get("department") or "Unknown department"
        matched_terms = item.get("matched_terms") or []
        hint = ", ".join(str(term) for term in matched_terms[:2] if term)
        suffix = f" ({hint})" if hint else ""
        lines.append(f"{index}. {department}{suffix}")
    return "\n".join(lines)


def _document_booking_note(state: GraphState) -> str | None:
    # Priority 1: Pre-checkup clinical note from AI intake (most comprehensive)
    if state.get("pre_checkup_clinical_note"):
        return str(state["pre_checkup_clinical_note"])

    # Priority 2: Pre-checkup note (legacy)
    if state.get("pre_checkup_note"):
        return str(state["pre_checkup_note"])

    # Priority 3: Pre-checkup summary
    if state.get("pre_checkup_summary"):
        return str(state["pre_checkup_summary"])

    # Fallback: Build from collected data (document uploads, etc.)
    collected = state.get("collected_facts") or state.get("collected_data") or state.get("collected_info") or {}
    if not isinstance(collected, dict):
        collected = {}

    parts: list[str] = []
    summary = collected.get("document_summary") or collected.get("document_note")
    relief = collected.get("document_temporary_relief")
    advice = collected.get("document_specialist_advice")
    context = state.get("file_clarification_context")

    for value in (summary, relief, advice, context):
        if value and str(value).strip():
            parts.append(str(value).strip())

    if not parts:
        return None

    return " | ".join(dict.fromkeys(parts))


def ask_cancellation_choice(state: GraphState):
    bookings = _booking_list(state)
    if not bookings:
        bookings = active_bookings_for_patient(state.get("patient_id"))

    if not bookings:
        return {
            "awaiting": None,
            "cancellation_options": [],
            "final_response": (
                "I could not find any active appointments to cancel. "
                "You can send the appointment reference if you have one."
            ),
        }

    return {
        "awaiting": "cancellation_selection",
        "cancellation_options": bookings,
        "final_response": (
            "Which appointment would you like to cancel?\n"
            f"{_format_booking_options(bookings)}\n\n"
            "Please reply with the appointment number or reference ID."
        ),
    }


def _format_reschedule_booking_options(bookings: list[dict]):
    lines = []
    for index, booking in enumerate(bookings, start=1):
        change_state = "can change date" if booking.get("can_modify", True) else "locked"
        time_str = booking.get("time") or booking.get("start_time") or "Unknown time"
        lines.append(
            f"{index}. {booking['doctor']} ({booking['department']}) at {time_str} "
            f"- Reference: {booking['booking_id']} [{change_state}]"
        )
    return "\n".join(lines)


def ask_reschedule_choice(state: GraphState):
    bookings = _booking_list(state)
    if not bookings:
        bookings = upcoming_bookings_for_patient(state.get("patient_id"))

    if not bookings:
        return {
            "awaiting": None,
            "reschedule_options": [],
            "final_response": (
                "I could not find any active appointments to change. "
                "You can send the appointment reference if you have one."
            ),
        }

    return {
        "awaiting": "reschedule_selection",
        "reschedule_options": bookings,
        "final_response": (
            "Which appointment would you like to change?\n"
            f"{_format_reschedule_booking_options(bookings)}\n\n"
            "Please reply with the appointment number or reference ID."
        ),
    }


def ask_department_choice(state: GraphState):
    departments = list(state.get("candidate_departments") or [])
    if not departments:
        return ask_preferred_doctor(state)

    return {
        "awaiting": "department_selection",
        "candidate_departments": departments,
        "final_response": (
            "I can see more than one possible department for your symptoms.\n"
            f"{_format_department_options(departments)}\n\n"
            "Please reply with the department number or name you want to book first."
        ),
    }


def appointment_resolver_node(state: GraphState):
    bookings = _booking_list(state)
    if not bookings:
        bookings = active_bookings_for_patient(state.get("patient_id"))

    if not bookings:
        return {
            "awaiting": None,
            "appointment_resolver_options": [],
            "final_response": "I could not find any active appointments to modify.",
        }

    user_text = " ".join((state.get("user_input") or "").lower().split())
    if user_text:
        selected = choose_option(state.get("user_input", ""), bookings, id_key="booking_id", name_key="doctor")
        if selected:
            base_state = {
                **state,
                "selected_booking_id": selected.get("booking_id"),
                "selected_doctor_name": selected.get("doctor") or selected.get("doctor_name"),
                "target_department": selected.get("department"),
                "appointment_resolver_options": bookings,
            }
            if any(term in user_text for term in ("cancel", "delete")):
                return ask_cancellation_choice(base_state)
            if any(term in user_text for term in ("change", "resched", "reschedule", "modify")):
                return ask_reschedule_choice(base_state)
            return {
                "awaiting": "appointment_resolver",
                "selected_booking_id": selected.get("booking_id"),
                "appointment_resolver_options": bookings,
                "final_response": (
                    f"You picked {selected.get('doctor') or selected.get('doctor_name')} on {selected.get('time') or selected.get('start_time')}."
                    " Please say cancel or change to continue."
                ),
            }

    lines = _format_booking_options(bookings)
    return {
        "awaiting": "appointment_resolver",
        "appointment_resolver_options": bookings,
        "final_response": (
            "I found more than one upcoming appointment. Which one would you like to modify?\n"
            f"{lines}\n\n"
            "Please reply with the appointment number or reference ID."
        ),
    }


def cancel_selected_appointment(state: GraphState):
    selected = choose_option(
        state["user_input"],
        state.get("cancellation_options") or [],
        id_key="booking_id",
        name_key="doctor",
    )

    reference = None
    if selected:
        reference = selected["booking_id"]
    else:
        text = state["user_input"].strip()
        if text:
            reference = text

    if not reference:
        return {
            "awaiting": "cancellation_selection",
            "final_response": "Please reply with the appointment number or reference ID to cancel.",
        }

    cancelled = cancel_booking(reference=reference, patient_id=state.get("patient_id"))
    if not cancelled:
        return {
            "awaiting": "cancellation_selection",
            "final_response": (
                "I could not find an active appointment with that reference. "
                "Please check the ID or choose one of the listed appointments."
            ),
        }

    remaining = [
        booking
        for booking in _booking_list(state)
        if booking.get("booking_id") != cancelled["booking_id"]
        and booking.get("slot_id") != cancelled["slot_id"]
    ]

    return {
        "awaiting": "end_confirmation",
        "booking_active": False,
        "cancellation_options": [],
        "upcoming_bookings": remaining,
        "confirmed_bookings": remaining,
        "confirmed_booking": remaining[-1] if remaining else None,
        "final_response": (
            "Your appointment has been cancelled.\n\n"
            f"Doctor: {cancelled['doctor']}\n"
            f"Department: {cancelled['department']}\n"
            f"Date & Time: {cancelled['time']}\n\n"
            "Would you like help with anything else, or should we end the chat?"
        ),
    }


def ask_reschedule_date(state: GraphState):
    selected = choose_option(
        state["user_input"],
        state.get("reschedule_options") or [],
        id_key="booking_id",
        name_key="doctor",
    )

    reference = None
    if selected:
        reference = selected["booking_id"]
    else:
        text = state["user_input"].strip()
        if text:
            reference = text

    if not reference:
        return {
            "awaiting": "reschedule_selection",
            "final_response": "Please reply with the appointment number or reference ID to change.",
        }

    booking = next(
        (
            item
            for item in (state.get("reschedule_options") or [])
            if item.get("booking_id") == reference or item.get("slot_id") == reference
        ),
        None,
    )
    if booking and booking.get("can_modify") is False:
        return {
            "awaiting": None,
            "reschedule_options": [],
            "final_response": (
                "That appointment is within 24 hours, so it cannot be changed right now."
            ),
        }

    date_options = _date_options()
    option_lines = "\n".join(f"{index}. {option['label']}" for index, option in enumerate(date_options, start=1))
    return {
        "awaiting": "reschedule_date_selection",
        "reschedule_options": state.get("reschedule_options") or [],
        "selected_booking_id": reference,
        "reschedule_date_options": date_options,
        "final_response": (
            "Which day would you prefer for the new appointment date?\n"
            f"{option_lines}\n\n"
            "Please reply with the date number."
        ),
    }


def choose_department_candidate(state: GraphState):
    candidates = list(state.get("candidate_departments") or [])
    if not candidates:
        return ask_preferred_doctor(state)

    text = state.get("user_input", "").strip().lower()
    selected_index = None
    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(candidates):
            selected_index = index

    selected = None
    if selected_index is not None:
        selected = candidates[selected_index]
    else:
        for candidate in candidates:
            department = str(candidate.get("department") or "").lower()
            if department and department in text:
                selected = candidate
                break

    if not selected:
        return {
            "awaiting": "department_selection",
            "candidate_departments": candidates,
            "final_response": (
                "Please reply with one of the listed department numbers or names."
            ),
        }

    remaining = [
        candidate
        for candidate in candidates
        if candidate.get("department") != selected.get("department")
    ]
    return {
        "awaiting": None,
        "candidate_departments": remaining,
        "requested_department": selected.get("department"),
        "target_department": selected.get("department"),
    }


def ask_reschedule_slot(state: GraphState):
    selected_date = _choose_date_option(
        state.get("user_input", ""),
        state.get("reschedule_date_options") or [],
    )
    if selected_date:
        state = {**state, "requested_date": selected_date}

    booking_id = state.get("selected_booking_id")
    if not booking_id:
        return {
            "awaiting": "reschedule_selection",
            "final_response": "Please choose the appointment you want to change first.",
        }

    requested_date = state.get("requested_date")
    if not requested_date or not _valid_requested_date(requested_date):
        return {
            "awaiting": "reschedule_date_selection",
            "reschedule_date_options": state.get("reschedule_date_options") or _date_options(),
            "final_response": "Appointments can be changed only from today up to 7 days ahead.",
        }

    slots = reschedule_options_for_booking(
        booking_id=booking_id,
        patient_id=state.get("patient_id"),
        requested_date=requested_date,
        limit=8,
    )
    if not slots:
        return {
            "awaiting": "reschedule_date_selection",
            "reschedule_date_options": _date_options(),
            "final_response": (
                f"I could not find any open slots on {requested_date}. "
                "Please choose another date."
            ),
        }

    slot_lines = format_numbered_options(
        slots,
        label_key="start_time",
        extra_keys=["end_time"],
    )
    return {
        "awaiting": "reschedule_slot_selection",
        "selected_booking_id": booking_id,
        "requested_date": requested_date,
        "reschedule_slot_options": slots,
        "final_response": (
            f"Available slots on {requested_date}:\n{slot_lines}\n\n"
            "Please reply with the slot number you prefer."
        ),
    }


def apply_reschedule_slot(state: GraphState):
    selected = choose_option(
        state["user_input"],
        state.get("reschedule_slot_options") or [],
        id_key="slot_id",
        name_key="start_time",
    )

    if not selected:
        return {
            "awaiting": "reschedule_slot_selection",
            "final_response": "I could not match that slot. Please reply with one of the listed slot numbers.",
        }

    booking_id = state.get("selected_booking_id")
    if not booking_id:
        return {
            "awaiting": "reschedule_selection",
            "final_response": "Please choose the appointment you want to change first.",
        }

    booked = reschedule_patient_booking(
        booking_id=booking_id,
        patient_id=state.get("patient_id"),
        new_slot_id=selected["slot_id"],
    )

    if not booked:
        return {
            "awaiting": "reschedule_slot_selection",
            "final_response": "That slot is no longer available. Please choose another slot.",
        }

    confirmed_booking = {
        "booking_id": str(booked.get("booking_id") or booking_id),
        "doctor": str(booked["doctor"]),
        "department": str(booked["department"]),
        "time": str(booked["time"]),
        "slot_id": str(booked["slot_id"]),
        "can_modify": bool(booked.get("can_modify", True)),
    }
    remaining = _booking_list(state)
    for index, booking in enumerate(remaining):
        if booking.get("booking_id") == confirmed_booking["booking_id"] or booking.get("slot_id") == confirmed_booking["slot_id"]:
            remaining[index] = confirmed_booking
            break
    else:
        remaining.append(confirmed_booking)

    return {
        "awaiting": "end_confirmation",
        "booking_active": False,
        "upcoming_bookings": remaining,
        "confirmed_booking": confirmed_booking,
        "confirmed_bookings": remaining,
        "reschedule_options": [],
        "reschedule_date_options": [],
        "reschedule_slot_options": [],
        "final_response": (
            "Your appointment has been updated.\n\n"
            f"Doctor: {booked['doctor']}\n"
            f"Department: {booked['department']}\n"
            f"Date & Time: {booked['time']}\n"
            f"Reference ID: {confirmed_booking['booking_id']}\n\n"
            "Would you like help with anything else, or should we end the chat?"
        ),
    }


def classify_booking_menu_reply(state: GraphState, menu_type: str) -> BookingMenuDecision | None:
    lowered = " ".join((state.get("user_input") or "").lower().replace("'", "").split())
    decline_phrases = (
        "no",
        "no appointment",
        "i dont want",
        "i do not want",
        "dont want to see a doctor",
        "do not want to see a doctor",
        "skip booking",
        "cancel booking",
        "not now",
    )
    if any(phrase in lowered for phrase in decline_phrases):
        return BookingMenuDecision(
            action="decline_booking",
            selected_value=None,
            reason="Patient declined booking from the displayed menu.",
        )

    dynamic_user_prompt = f"""Current state: {compact_state_summary(state)}
Current menu: {menu_type}
Doctor options: {compact_option_summary(state.get('doctor_options'), 'doctor_name', ['department', 'experience_years', 'next_available_time'])}
Slot options: {compact_option_summary(state.get('slot_options'), 'start_time', ['end_time'])}
Booked context: {compact_booking_summary(state.get('upcoming_bookings') or state.get('confirmed_bookings'))}
Collected facts: {compact_fact_summary(state.get('collected_data') or state.get('collected_info'))}
Latest reply: {state.get('user_input', '')}"""

    raw_output = generate_text(
        system_prompt=STATIC_MENU_PROMPT,
        user_prompt=dynamic_user_prompt,
        node_name="appointment_booker",
        chat_summary=state.get("chat_summary"),
        include_history=True,
        history_turns=min(4, MEMORY_POLICY.prompt_window_turns),
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )
    
    clean_json = _clean_json(raw_output)
    print(f"Booking menu decision JSON: {clean_json}")

    try:
        return menu_parser.parse(clean_json)
    except Exception as exc:
        print(f"Booking menu parser failed: {exc}")
        return None


def ask_symptom_follow_up(state: GraphState):
    symptoms = state.get("symptoms") or []
    symptom_text = ", ".join(symptoms) if symptoms else "your symptoms"
    collected = state.get("collected_info") or {}
    questions_asked = state.get("questions_asked") or []
    history = list(state.get("conversation_history") or [])
    question = next_missing_intake_question(
        collected,
        questions_asked,
        "What feels most important about these symptoms right now?",
    )
    follow_up = question.strip()
    if follow_up and follow_up[0].isupper():
        follow_up = follow_up[0].lower() + follow_up[1:]
    response = (
        f"I noted: {symptom_text}. To help match the right department, "
        f"{follow_up.rstrip('.')}"
    )
    if not response.endswith("?"):
        response = response.rstrip(".") + "?"
    history.append({"role": "assistant", "text": response})

    return {
        "awaiting": "symptom_follow_up",
        "booking_active": False,
        "conversation_history": history,
        "questions_asked": questions_asked + [response],
        "final_response": response,
    }


def capture_symptom_follow_up(state: GraphState):
    answer = state.get("user_input", "").strip()
    local_info = extract_local_intake_info(answer)
    collected = {**(state.get("collected_info") or {}), **local_info}
    if answer and not local_info.get("duration"):
        collected.setdefault("duration", answer)

    return {
        "awaiting": None,
        "booking_active": False,
        "follow_up_answer": answer,
        "symptom_duration": answer,
        "collected_info": collected,
    }


def ask_preferred_doctor(state: GraphState):
    requested_department_text = state.get("requested_department") or state.get("target_department")
    requested_doctor_name = state.get("requested_doctor_name")
    has_explicit_department = bool(requested_department_text)
    if not _looks_like_specific_doctor_name(requested_doctor_name):
        requested_doctor_name = None
    requested_department = state.get("requested_department")
    requested_date = state.get("requested_date")
    severity = state.get("severity") or "moderate"
    symptoms = state.get("symptoms") or []
    symptom_text = ", ".join(symptoms) if symptoms else "your symptoms"

    if not has_explicit_department and not requested_doctor_name:
        if symptoms:
            return ask_symptom_follow_up({
                **state,
                "intent": state.get("intent") or "triage_symptoms",
                "booking_active": False,
            })
        return {
            "awaiting": "conversation",
            "booking_active": False,
            "intent": state.get("intent") or "triage_symptoms",
            "doctor_options": [],
            "slot_options": [],
            "final_response": "Please tell me what symptoms you are having so I can match the right department before booking.",
        }

    department = normalize_department_name(requested_department_text)
    department_context = {
        "requested_department": requested_department or department,
        "target_department": department,
    }

    if requested_date and not _valid_requested_date(requested_date):
        return _date_selection_response(
            "Appointments can be booked only from today up to 7 days ahead."
        )

    if requested_doctor_name and requested_date:
        doctors = available_doctors_by_name_on_date(requested_doctor_name, requested_date, limit=5)
    elif requested_doctor_name:
        doctors = available_doctors_by_name(requested_doctor_name, limit=5)
    elif requested_date:
        doctors = available_doctors_for_department_on_date(department, requested_date, limit=5)
    else:
        doctors = available_doctors_for_department(department=department, limit=5)

    if not doctors:
        fallback_department = "General Physician"
        fallback_doctors = []
        if department != fallback_department:
            if requested_date:
                fallback_doctors = available_doctors_for_department_on_date(
                    fallback_department,
                    requested_date,
                    limit=5,
                )
            else:
                fallback_doctors = available_doctors_for_department(
                    department=fallback_department,
                    limit=5,
                )

        requested_text = (
            f"matching {requested_doctor_name}"
            if requested_doctor_name
            else f"in the {requested_department_text or department} department"
        )
        date_text = f" on {requested_date}" if requested_date else ""
        if fallback_doctors:
            doctor_lines = format_numbered_options(
                fallback_doctors,
                label_key="doctor_name",
                extra_keys=["experience_years", "next_available_time"],
            )
            fallback_intro = (
                f"We do not currently have doctors available {requested_text}{date_text}. "
                f"I can show the available {fallback_department} doctors instead."
            )
            if requested_department:
                fallback_intro = (
                    f"We do not currently have doctors available in the {requested_department_text or department} department{date_text}. "
                    f"I can show the available {fallback_department} doctors instead."
                )
            return {
                "awaiting": "doctor_selection",
                "booking_active": True,
                **department_context,
                "target_department": fallback_department,
                "requested_department": requested_department or department,
                "doctor_options": fallback_doctors,
                "final_response": (
                    f"{fallback_intro}\n\n"
                    f"Here are the available {fallback_department} doctors:\n{doctor_lines}\n\n"
                    "Please reply with the doctor number or name you prefer."
                ),
            }

        return {
            "doctor_options": [],
            **department_context,
            **_date_selection_response(
                f"I could not find available doctors {requested_text}{date_text}. "
                f"I also could not find any available {fallback_department} doctors right now. "
            ),
        }

    if requested_doctor_name and len(doctors) == 1:
        doctor = doctors[0]
        slots = (
            available_slots_for_doctor_on_date(doctor["doctor_id"], requested_date, limit=5)
            if requested_date
            else available_slots_for_doctor(doctor["doctor_id"], limit=5)
        )
        if not slots:
            return {
                "doctor_options": [],
                "slot_options": [],
                **_date_selection_response(
                    f"{doctor['doctor_name']} has no open slots"
                    f"{f' on {requested_date}' if requested_date else ''}."
                ),
            }

        slot_lines = format_numbered_options(
            slots,
            label_key="start_time",
            extra_keys=["end_time"],
        )
        return {
            "awaiting": "slot_selection",
            "booking_active": True,
            **department_context,
            "target_department": doctor.get("department") or department,
            "doctor_options": [doctor],
            "selected_doctor_id": doctor["doctor_id"],
            "selected_doctor_name": doctor["doctor_name"],
            "slot_options": slots,
            "final_response": (
                f"I found {doctor['doctor_name']} in {doctor.get('department') or department}.\n\n"
                f"Available slots{f' on {requested_date}' if requested_date else ''}:\n{slot_lines}\n\n"
                "Please reply with the slot number you prefer. "
                "If you would like to skip booking for now, reply 'no'."
            ),
        }

    doctor_lines = format_numbered_options(
        doctors,
        label_key="doctor_name",
        extra_keys=["department", "experience_years", "next_available_time"]
        if requested_doctor_name
        else ["experience_years", "next_available_time"],
        bold_label=True,
    )

    severity_note = ""
    if severity in {"severe", "emergency"}:
        severity_note = (
            " Given the severity of your symptoms, I recommend seeing a doctor as soon as possible."
        )

    if requested_doctor_name:
        intro = f"I found these matching doctors for {requested_doctor_name}."
    elif requested_department:
        intro = f"You asked for the **{department}** department."
    else:
        intro = f"Based on your symptoms ({symptom_text}), I recommend the **{department}** department."
    if requested_date:
        intro = f"{intro} Showing availability for {requested_date}."

    return {
        "awaiting": "doctor_selection",
        "booking_active": True,
        **department_context,
        "doctor_options": doctors,
        "final_response": (
            f"{intro}{severity_note}\n\n"
            f"Here are the available doctors:\n{doctor_lines}\n\n"
            "Please reply with the doctor number or name you prefer."
        ),
    }


def ask_preferred_slot(state: GraphState):
    selected = choose_option(
        state["user_input"],
        state.get("doctor_options") or [],
        id_key="doctor_id",
        name_key="doctor_name",
    )

    if not selected:
        return {
            "final_response": (
                "I could not match that selection. Please reply with one of the listed "
                "doctor numbers or names."
            )
        }

    requested_date = state.get("requested_date")
    department_context = {
        "requested_department": state.get("requested_department") or state.get("target_department"),
        "target_department": state.get("target_department"),
    }
    slots = (
        available_slots_for_doctor_on_date(selected["doctor_id"], requested_date, limit=5)
        if requested_date and _valid_requested_date(requested_date)
        else available_slots_for_doctor(selected["doctor_id"], limit=5)
    )

    if not slots:
        return {
            "selected_doctor_id": selected["doctor_id"],
            "selected_doctor_name": selected["doctor_name"],
            **department_context,
            **_date_selection_response(
                f"{selected['doctor_name']} has no open slots right now. "
            ),
        }

    slot_lines = format_slot_options(slots)

    return {
        "awaiting": "slot_selection",
        "booking_active": True,
        **department_context,
        "selected_doctor_id": selected["doctor_id"],
        "selected_doctor_name": selected["doctor_name"],
        "slot_options": slots,
        "final_response": (
            f"Available slots for **{selected['doctor_name']}**"
            f"{f' on {requested_date}' if requested_date else ''}:\n\n{slot_lines}\n\n"
            "Please reply with the slot number you prefer. "
            "If you would like to skip booking for now, reply 'no'."
        ),
    }


def book_preferred_slot(state: GraphState):
    selected = choose_option(
        state["user_input"],
        state.get("slot_options") or [],
        id_key="slot_id",
        name_key="start_time",
    )

    if not selected:
        return {
            "final_response": (
                "I could not match that slot. Please reply with one of the listed slot numbers."
            )
        }

    booking_note = _document_booking_note(state)
    try:
        booked = book_selected_slot(
            slot_id=selected["slot_id"],
            patient_id=state.get("patient_id"),
            booking_note=booking_note,
        )
    except TypeError:
        booked = book_selected_slot(
            slot_id=selected["slot_id"],
            patient_id=state.get("patient_id"),
        )

    if not booked:
        return {
            "awaiting": "slot_selection",
            "final_response": (
                "That slot was just taken. Please choose another slot from the list."
            ),
        }

    booking_reference = str(booked.get("booking_id") or booked["slot_id"])
    confirmed_booking = {
        "booking_id": booking_reference,
        "doctor": str(booked["doctor_name"]),
        "department": str(booked["department"]),
        "time": _fmt_time(str(booked["start_time"])),
        "slot_id": str(booked["slot_id"]),
    }
    confirmed_bookings = _booking_list(state)
    confirmed_bookings.append(confirmed_booking)
    remaining_departments = [
        candidate
        for candidate in (state.get("candidate_departments") or [])
        if str(candidate.get("department") or "") != confirmed_booking["department"]
    ]

    # Build confirmation message with clinical summary notice
    clinical_note_suffix = (
        "\n✓ Your clinical intake summary has been attached to this appointment "
        "and will be available to the doctor before you arrive."
    ) if state.get("pre_checkup_clinical_note") or state.get("pre_checkup_summary") else ""

    if remaining_departments:
        next_departments = _format_department_options(remaining_departments)
        return {
            "awaiting": "department_selection",
            "booking_active": False,
            "candidate_departments": remaining_departments,
            "upcoming_bookings": confirmed_bookings,
            "confirmed_booking": confirmed_booking,
            "confirmed_bookings": confirmed_bookings,
            "doctor_options": [],
            "slot_options": [],
            "selected_doctor_id": None,
            "selected_doctor_name": None,
            "selected_slot_id": str(booked["slot_id"]),
            "final_response": (
                "Your appointment is booked and confirmed!\n\n"
                f"Doctor: {booked['doctor_name']}\n"
                f"Department: {booked['department']}\n"
                f"Date & Time: {_fmt_time(str(booked['start_time']))}\n"
                f"Reference ID: {booking_reference}\n"
                f"{clinical_note_suffix}\n\n"
                "I can also help with the other department(s) we identified.\n"
                f"{next_departments}\n\n"
                "Please reply with the department number or name you want to book next, or say no to stop here."
            ),
        }

    return {
        "awaiting": "report_forwarding_decision",
        "booking_active": False,
        "upcoming_bookings": confirmed_bookings,
        "confirmed_booking": confirmed_booking,
        "confirmed_bookings": confirmed_bookings,
        "doctor_options": [],
        "slot_options": [],
        "selected_doctor_id": None,
        "selected_doctor_name": None,
        "selected_slot_id": str(booked["slot_id"]),
        "final_response": (
            "✓ Your appointment is booked and confirmed!\n\n"
            f"**Doctor:** {booked['doctor_name']}\n"
            f"**Department:** {booked['department']}\n"
            f"**Date & Time:** {_fmt_time(str(booked['start_time']))}\n"
            f"**Reference ID:** {booking_reference}\n\n"
            "---\n\n"
            f"**Should I forward your detailed clinical report to {booked['doctor_name']} before your appointment?**\n\n"
            "This will include all the symptoms, their patterns, triggers, and recommendations we discussed. "
            "It helps the doctor prepare better for your visit. (yes / no)"
        ),
    }


def appointment_booker_node(state: GraphState):
    awaiting = state.get("awaiting")

    if awaiting == "appointment_resolver":
        return appointment_resolver_node(state)

    if awaiting == "department_selection":
        choice = choose_department_candidate(state)
        if choice.get("awaiting") == "department_selection":
            return choice
        state = {**state, **choice}

    if awaiting == "cancellation_selection":
        return cancel_selected_appointment(state)

    if awaiting == "reschedule_selection":
        return ask_reschedule_date(state)

    if awaiting == "reschedule_date_selection":
        return ask_reschedule_slot(state)

    if awaiting == "reschedule_slot_selection":
        return apply_reschedule_slot(state)

    if _looks_like_reschedule_request(state.get("user_input", "")):
        return ask_reschedule_choice(state)

    if _looks_like_cancellation(state.get("user_input", "")):
        return ask_cancellation_choice(state)

    if awaiting == "date_selection":
        selected_date = _choose_date_option(
            state.get("user_input", ""),
            state.get("date_options") or [],
        )
        if selected_date:
            state = {**state, "requested_date": selected_date}
        if not state.get("requested_date") or not _valid_requested_date(state.get("requested_date")):
            return _date_selection_response(
                "Appointments can be booked only from today up to 7 days ahead."
            )
        return ask_preferred_doctor(state)

    if awaiting == "symptom_follow_up":
        return capture_symptom_follow_up(state)

    if awaiting in {"doctor_selection", "doctor_selection_retry_1", "doctor_selection_retry_2", "slot_selection", "slot_selection_retry_1", "slot_selection_retry_2"}:
        decision = classify_booking_menu_reply(state, awaiting)

        if decision and decision.action == "request_remedy":
            return {
                "awaiting": None,
                "booking_active": False,
                "active_intent": "triage_symptoms",
                "intent": "triage_symptoms",
                "remedy_requested": True,
                "doctor_options": [],
                "slot_options": [],
            }

        if decision and decision.action == "cancel_appointment":
            return ask_cancellation_choice(state)

        if decision and decision.action == "decline_booking":
            department = state.get("target_department") or "a relevant specialist"
            return {
                "awaiting": None,
                "booking_active": False,
                "active_intent": "triage_symptoms",
                "intent": "triage_symptoms",
                "booking_declined": True,
                "doctor_options": [],
                "slot_options": [],
                "final_response": (
                    "No appointment has been booked. "
                    f"If symptoms continue or worsen, please see a {department} doctor. "
                    "If you change your mind, feel free to come back. Take care of yourself!"
                ),
            }

        # Handle unclear responses in menus with escalation after 2 attempts
        # Use awaiting state value itself to track attempts (no custom state key persistence)
        if decision and decision.action == "unclear":
            # Check which attempt we're on based on awaiting state
            if awaiting == "doctor_selection_retry_2":
                # Third attempt (escalate)
                return {
                    "awaiting": None,
                    "booking_active": False,
                    "final_response": (
                        "I'm having trouble understanding your choice. "
                        "Let me connect you with a specialist who can help with your appointment."
                    ),
                }
            elif awaiting == "doctor_selection_retry_1":
                # Second attempt (clarify again)
                doctors = state.get("doctor_options", [])
                if doctors:
                    options_text = format_numbered_options(doctors, "doctor_name", ["experience_years", "next_available_time"])
                    return {
                        "awaiting": "doctor_selection_retry_2",
                        "doctor_options": doctors,
                        "final_response": (
                            "I still need you to pick a doctor. Which one would you like to book with?\n"
                            f"{options_text}\n\n"
                            "Please reply with the doctor number (1, 2, 3, etc.)"
                        ),
                    }
                else:
                    return {
                        "awaiting": "doctor_selection_retry_2",
                        "final_response": "I still need you to select a doctor. Please reply with a doctor number (1, 2, 3, etc.)",
                    }
            elif awaiting == "slot_selection_retry_2":
                # Third attempt (escalate)
                return {
                    "awaiting": None,
                    "booking_active": False,
                    "final_response": (
                        "I'm having trouble understanding your time slot choice. "
                        "Let me help you differently."
                    ),
                }
            elif awaiting == "slot_selection_retry_1":
                # Second attempt (clarify again)
                slots = state.get("slot_options", [])
                if slots:
                    options_text = format_slot_options(slots)
                    return {
                        "awaiting": "slot_selection_retry_2",
                        "slot_options": slots,
                        "final_response": (
                            "I still need you to pick a time slot. Which one works for you?\n"
                            f"{options_text}\n\n"
                            "Please reply with the slot number (1, 2, 3, etc.)"
                        ),
                    }
                else:
                    return {
                        "awaiting": "slot_selection_retry_2",
                        "final_response": "I still need you to select a time slot. Please reply with a slot number (1, 2, 3, etc.)",
                    }
            elif awaiting == "doctor_selection":
                # First attempt (initial clarification)
                doctors = state.get("doctor_options", [])
                if doctors:
                    options_text = format_numbered_options(doctors, "doctor_name", ["experience_years", "next_available_time"])
                    return {
                        "awaiting": "doctor_selection_retry_1",
                        "doctor_options": doctors,
                        "final_response": (
                            "I need you to pick a doctor. Which one would you like to book with?\n"
                            f"{options_text}\n\n"
                            "Please reply with the doctor number (1, 2, 3, etc.)"
                        ),
                    }
                else:
                    return {
                        "awaiting": "doctor_selection_retry_1",
                        "final_response": "I need you to select a doctor. Please reply with a doctor number (1, 2, 3, etc.)",
                    }
            elif awaiting == "slot_selection":
                # First attempt (initial clarification)
                slots = state.get("slot_options", [])
                if slots:
                    options_text = format_slot_options(slots)
                    return {
                        "awaiting": "slot_selection_retry_1",
                        "slot_options": slots,
                        "final_response": (
                            "I need you to pick a time slot. Which one works for you?\n"
                            f"{options_text}\n\n"
                            "Please reply with the slot number (1, 2, 3, etc.)"
                        ),
                    }
                else:
                    return {
                        "awaiting": "slot_selection_retry_1",
                        "final_response": "I need you to select a time slot. Please reply with a slot number (1, 2, 3, etc.)",
                    }

        # Handle parse failures (decision is None) - treat as unclear
        if decision is None and awaiting in {"doctor_selection", "doctor_selection_retry_1", "doctor_selection_retry_2", "slot_selection", "slot_selection_retry_1", "slot_selection_retry_2"}:
            if awaiting in {"doctor_selection_retry_2", "slot_selection_retry_2"}:
                # Third attempt failed - escalate
                return {
                    "awaiting": None,
                    "booking_active": False,
                    "final_response": "I'm having trouble processing your response. Let me help you differently.",
                }
            elif awaiting in {"doctor_selection", "slot_selection"}:
                # First attempt - move to retry_1
                if awaiting == "doctor_selection":
                    return {
                        "awaiting": "doctor_selection_retry_1",
                        "final_response": "Sorry, I didn't understand. Please reply with a doctor number (1, 2, 3, etc.)",
                    }
                else:
                    return {
                        "awaiting": "slot_selection_retry_1",
                        "final_response": "Sorry, I didn't understand. Please reply with a slot number (1, 2, 3, etc.)",
                    }
            else:
                # Second attempt (retry_1) failed - move to retry_2
                if awaiting == "doctor_selection_retry_1":
                    return {
                        "awaiting": "doctor_selection_retry_2",
                        "final_response": "Sorry, I still didn't understand. Please reply with a doctor number (1, 2, 3, etc.)",
                    }
                elif awaiting == "doctor_selection_retry_2":
                    # Final attempt failed - escalate and give up
                    return {
                        "awaiting": None,
                        "booking_active": False,
                        "final_response": "I couldn't process your selection. A hospital staff member will help you book an appointment. Thank you for your patience.",
                    }
                elif awaiting == "slot_selection_retry_1":
                    return {
                        "awaiting": "slot_selection_retry_2",
                        "final_response": "Sorry, I still didn't understand. Please reply with a slot number (1, 2, 3, etc.)",
                    }
                else:  # slot_selection_retry_2
                    # Final attempt failed - escalate and give up
                    return {
                        "awaiting": None,
                        "booking_active": False,
                        "final_response": "I couldn't process your slot selection. A hospital staff member will help you book an appointment. Thank you for your patience.",
                    }

        if decision and decision.action == "select_option" and decision.selected_value:
            state = {**state, "user_input": decision.selected_value}

    # If escalation happened (awaiting=None after retry_2) with no actionable
    # booking context, stop. If target_department / requested_department /
    # requested_doctor_name is set this is a fresh valid entry — fall through
    # to ask_preferred_doctor below.
    if not awaiting and not state.get("target_department") and not state.get("requested_department") and not state.get("requested_doctor_name") and not state.get("candidate_departments"):
        return {"awaiting": None, "booking_active": False}

    if awaiting == "doctor_selection":
        return ask_preferred_slot(state)

    if awaiting == "slot_selection":
        return book_preferred_slot(state)

    collected = state.get("collected_info") or {}
    candidate_departments = state.get("candidate_departments") or []
    if candidate_departments and not state.get("requested_department") and not state.get("target_department") and not state.get("requested_doctor_name"):
        return ask_department_choice(state)

    has_conversation_context = bool(
        collected.get("duration")
        or collected.get("cause")
        or collected.get("trigger")
        or collected.get("onset")
    )

    if (
        state.get("symptoms")
        and not state.get("follow_up_answer")
        and not has_conversation_context
        and not state.get("remedy_given")
        and (state.get("active_intent") or state.get("intent")) != "direct_booking"
    ):
        return ask_symptom_follow_up(state)

    return ask_preferred_doctor(state)
