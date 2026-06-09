"""
Appointment Booker Agent
------------------------
Handles symptom follow-up, doctor selection, and slot booking.
Remedy logic lives in remedy_agent.py.
"""

from datetime import date, datetime, timedelta

from app.agents.state import GraphState
from app.agents.schemas import BookingMenuDecision
from app.inference.llm import generate_text
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
)


menu_parser = PydanticOutputParser(pydantic_object=BookingMenuDecision)
BOOKING_WINDOW_DAYS = 7


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


def format_numbered_options(items: list[dict], label_key: str, extra_keys: list[str]):
    lines = []
    for index, item in enumerate(items, start=1):
        extra = ", ".join(str(item[key]) for key in extra_keys if item.get(key) is not None)
        suffix = f" ({extra})" if extra else ""
        lines.append(f"{index}. {item[label_key]}{suffix}")
    return "\n".join(lines)


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


def _format_booking_options(bookings: list[dict]):
    lines = []
    for index, booking in enumerate(bookings, start=1):
        lines.append(
            f"{index}. {booking['doctor']} ({booking['department']}) at {booking['time']} "
            f"- Reference: {booking['booking_id']}"
        )
    return "\n".join(lines)


def ask_cancellation_choice(state: GraphState):
    bookings = state.get("confirmed_bookings") or []
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
        for booking in (state.get("confirmed_bookings") or [])
        if booking.get("booking_id") != cancelled["booking_id"]
        and booking.get("slot_id") != cancelled["slot_id"]
    ]

    return {
        "awaiting": "end_confirmation",
        "booking_active": False,
        "cancellation_options": [],
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

    prompt = f"""
You are an appointment booking assistant interpreting the patient's latest reply.

Use meaning and the displayed options, not keyword matching.

Current menu: {menu_type}
Doctor options: {state.get("doctor_options") or []}
Slot options: {state.get("slot_options") or []}
Latest patient reply: {state.get("user_input", "")}

Decide whether the patient selected an option, declined booking, requested symptom
care/remedy instead, asked to cancel an appointment, or gave an unclear reply.
If they selected an option, copy the number, id, name, or time they used into
selected_value.

Return only JSON:
{menu_parser.get_format_instructions()}
""".strip()

    raw_output = generate_text(
        prompt,
        node_name="appointment_booker",
        chat_history=state.get("conversation_history"),
        chat_summary=state.get("chat_summary"),
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

    return {
        "awaiting": "symptom_follow_up",
        "final_response": (
            f"I noted: {symptom_text}. To help match you with the right care, "
            "since when have you been feeling this, and is it getting better, worse, "
            "or staying about the same?"
        ),
    }


def capture_symptom_follow_up(state: GraphState):
    answer = state.get("user_input", "").strip()

    return {
        "awaiting": None,
        "follow_up_answer": answer,
        "symptom_duration": answer,
    }


def ask_preferred_doctor(state: GraphState):
    department = state.get("target_department") or "General Physician"
    requested_doctor_name = state.get("requested_doctor_name")
    requested_department = state.get("requested_department")
    requested_date = state.get("requested_date")
    severity = state.get("severity") or "moderate"
    symptoms = state.get("symptoms") or []
    symptom_text = ", ".join(symptoms) if symptoms else "your symptoms"

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
        requested_text = (
            f"matching {requested_doctor_name}"
            if requested_doctor_name
            else f"in the {department} department"
        )
        date_text = f" on {requested_date}" if requested_date else ""
        return {
            "doctor_options": [],
            **_date_selection_response(
                f"I could not find available doctors {requested_text}{date_text}. "
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
    slots = (
        available_slots_for_doctor_on_date(selected["doctor_id"], requested_date, limit=5)
        if requested_date and _valid_requested_date(requested_date)
        else available_slots_for_doctor(selected["doctor_id"], limit=5)
    )

    if not slots:
        return {
            "selected_doctor_id": selected["doctor_id"],
            "selected_doctor_name": selected["doctor_name"],
            **_date_selection_response(
                f"{selected['doctor_name']} has no open slots right now. "
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
        "selected_doctor_id": selected["doctor_id"],
        "selected_doctor_name": selected["doctor_name"],
        "slot_options": slots,
        "final_response": (
            f"Available slots for {selected['doctor_name']}"
            f"{f' on {requested_date}' if requested_date else ''}:\n{slot_lines}\n\n"
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
        "time": str(booked["start_time"]),
        "slot_id": str(booked["slot_id"]),
    }
    confirmed_bookings = list(state.get("confirmed_bookings") or [])
    confirmed_bookings.append(confirmed_booking)

    return {
        "awaiting": "end_confirmation",
        "booking_active": False,
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
            f"Date & Time: {booked['start_time']}\n"
            f"Reference ID: {booking_reference}\n\n"
            "Please arrive 10 minutes early. Would you like help with anything else, "
            "or should we end the chat?"
        ),
    }


def appointment_booker_node(state: GraphState):
    awaiting = state.get("awaiting")

    if awaiting == "cancellation_selection":
        return cancel_selected_appointment(state)

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

    if awaiting in {"doctor_selection", "slot_selection"}:
        decision = classify_booking_menu_reply(state, awaiting)

        if decision and decision.action == "request_remedy":
            return {
                "awaiting": None,
                "booking_active": False,
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

        if decision and decision.action == "select_option" and decision.selected_value:
            state = {**state, "user_input": decision.selected_value}

    if awaiting == "doctor_selection":
        return ask_preferred_slot(state)

    if awaiting == "slot_selection":
        return book_preferred_slot(state)

    collected = state.get("collected_info") or {}
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
        and state.get("intent") != "direct_booking"
    ):
        return ask_symptom_follow_up(state)

    return ask_preferred_doctor(state)
