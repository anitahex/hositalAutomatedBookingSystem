from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import SupervisorDecision
from app.agents.state import GraphState
from app.inference.llm import generate_router_text


parser = PydanticOutputParser(pydantic_object=SupervisorDecision)

EXIT_WORDS = {
    "bye",
    "goodbye",
    "end",
    "end chat",
    "exit",
    "quit",
    "stop",
    "done",
    "that's all",
    "thats all",
}


def _route(next_agent: str, **updates):
    return {
        "next_agent": next_agent,
        "supervisor_checked_input": True,
        **updates,
    }


def _clean_json(raw_output: str) -> str:
    return raw_output.replace("```json", "").replace("```", "").strip()


def _patient_wants_exit(state: GraphState) -> bool:
    user_input = (state.get("user_input") or "").strip().lower()
    return user_input in EXIT_WORDS


def _dynamic_route(state: GraphState) -> dict | None:
    if state.get("supervisor_checked_input"):
        return None

    user_input = (state.get("user_input") or "").strip()
    if not user_input:
        return None

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
- appointment_booker: patient wants booking, appointment, doctor selection, slot selection, or declines booking.
- finish: patient clearly ends the chat or says they are done/better.

Rules:
- If the patient asks for something new, do not trap them in the old awaiting state.
- Numeric doctor/slot choices, doctor names, slot choices, and booking declines should continue_current.
- If the patient asks for a remedy while in a booking menu, route to remedy_agent.
- If the patient asks for a doctor and symptoms are known but department is unknown, route to medical_rag.
- If the patient asks for a doctor and department/options are already known, route to appointment_booker.

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

    if _patient_wants_exit(state):
        return _route(
            "finish",
            awaiting=None,
            final_response="Take care. You can come back anytime if you need help.",
        )

    dynamic_route = _dynamic_route(state)
    if dynamic_route:
        return dynamic_route

    if awaiting == "conversation":
        return _route("conversation_agent")

    if awaiting == "remedy_check":
        return _route("remedy_agent")

    if awaiting in {"symptom_follow_up", "doctor_selection", "slot_selection"}:
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

    if state.get("confirmed_booking") and state.get("symptoms") and not state.get("remedy_given"):
        return _route("remedy_agent")

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
    has_cause = bool(
        collected.get("cause")
        or collected.get("trigger")
        or collected.get("onset")
    )

    if len(questions_asked) >= 3:
        return True

    return has_duration and has_cause


def route_from_supervisor(state: GraphState):
    return state.get("next_agent", "finish")
