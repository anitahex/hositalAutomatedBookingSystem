from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import SupervisorDecision
from app.agents.state import GraphState
from app.inference.llm import generate_router_text


parser = PydanticOutputParser(pydantic_object=SupervisorDecision)


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

    if state.get("awaiting") == "end_confirmation":
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

    if _looks_like_end_chat(user_input):
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

    raw_output = generate_router_text(prompt)
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
        if next_agent == "medical_rag" and not state.get("symptoms"):
            next_agent = "triage_router"
        elif next_agent == "appointment_booker" and state.get("symptoms") and not state.get("target_department"):
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

    if awaiting in {"symptom_follow_up", "doctor_selection", "slot_selection", "cancellation_selection"}:
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
