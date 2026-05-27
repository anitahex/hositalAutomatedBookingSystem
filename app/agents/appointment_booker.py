"""
Appointment Booker Agent
------------------------
Handles symptom follow-up, doctor selection, and slot booking.
Remedy logic lives in remedy_agent.py.
"""

from app.agents.state import GraphState
from app.services.appointments import (
    available_doctors_for_department,
    available_slots_for_doctor,
    book_selected_slot,
)


DECLINE_WORDS = {"no", "nope", "deny", "decline", "cancel", "not now", "later"}
REMEDY_REQUEST_WORDS = {
    "remedy",
    "remedies",
    "suggestion",
    "suggestions",
    "relief",
    "home care",
    "what can i do",
}


def patient_declined(text: str) -> bool:
    normalized = text.strip().lower()
    return any(word in normalized for word in DECLINE_WORDS)


def patient_wants_remedy(text: str) -> bool:
    normalized = text.strip().lower()
    return any(word in normalized for word in REMEDY_REQUEST_WORDS)


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
        if text in str(option[name_key]).lower():
            return option

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
    severity = state.get("severity") or "moderate"
    symptoms = state.get("symptoms") or []
    symptom_text = ", ".join(symptoms) if symptoms else "your symptoms"

    doctors = available_doctors_for_department(department=department, limit=5)

    if not doctors:
        return {
            "awaiting": None,
            "doctor_options": [],
            "final_response": (
                f"Based on your symptoms ({symptom_text}), I recommend the {department} department. "
                "Unfortunately, no doctors in this department have available slots right now. "
                "Please call the hospital directly or check back later."
            ),
        }

    doctor_lines = format_numbered_options(
        doctors,
        label_key="doctor_name",
        extra_keys=["experience_years", "next_available_time"],
    )

    severity_note = ""
    if severity in {"severe", "emergency"}:
        severity_note = (
            " Given the severity of your symptoms, I recommend seeing a doctor as soon as possible."
        )

    return {
        "awaiting": "doctor_selection",
        "booking_active": True,
        "doctor_options": doctors,
        "final_response": (
            f"Since your symptoms are persisting, I recommend the **{department}** department."
            f"{severity_note}\n\n"
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

    slots = available_slots_for_doctor(selected["doctor_id"], limit=5)

    if not slots:
        return {
            "awaiting": "doctor_selection",
            "selected_doctor_id": selected["doctor_id"],
            "selected_doctor_name": selected["doctor_name"],
            "final_response": (
                f"{selected['doctor_name']} has no open slots right now. "
                "Please choose another doctor from the list."
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
            f"Available slots for {selected['doctor_name']}:\n{slot_lines}\n\n"
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

    return {
        "awaiting": None,
        "booking_active": False,
        "confirmed_booking": {
            "doctor": str(booked["doctor_name"]),
            "department": str(booked["department"]),
            "time": str(booked["start_time"]),
            "slot_id": str(booked["slot_id"]),
        },
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
            f"Reference ID: {booked['slot_id']}\n\n"
            "Please arrive 10 minutes early. Take care and feel better soon!"
        ),
    }


def appointment_booker_node(state: GraphState):
    awaiting = state.get("awaiting")

    if awaiting == "symptom_follow_up":
        return capture_symptom_follow_up(state)

    if awaiting in {"doctor_selection", "slot_selection"} and patient_wants_remedy(state["user_input"]):
        return {
            "awaiting": None,
            "booking_active": False,
            "intent": "triage_symptoms",
            "remedy_requested": True,
            "doctor_options": [],
            "slot_options": [],
        }

    if awaiting in {"doctor_selection", "slot_selection"} and patient_declined(state["user_input"]):
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
