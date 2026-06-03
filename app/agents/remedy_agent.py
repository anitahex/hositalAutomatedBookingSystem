"""
Remedy Agent
------------
Generates a personalised remedy based on everything collected in the conversation.
After giving the remedy, asks the patient if they are improving or still struggling.
If still persisting, supervisor routes to medical_rag then booking.
"""

from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import RemedyFollowUpDecision, RemedyResponse
from app.agents.state import GraphState
from app.inference.llm import generate_text


parser = PydanticOutputParser(pydantic_object=RemedyResponse)
follow_up_parser = PydanticOutputParser(pydantic_object=RemedyFollowUpDecision)

REMEDY_FOLLOW_UP = (
    "Please try these suggestions - they may help relieve your symptoms. "
    "If the discomfort continues, worsens, or you'd like to see a doctor right away, "
    "please let me know."
)

def _clean_json(raw_output: str) -> str:
    return raw_output.replace("```json", "").replace("```", "").strip()


def _classify_follow_up(state: GraphState, user_text: str) -> RemedyFollowUpDecision | None:
    prompt = f"""
You are a hospital assistant interpreting a patient's reply after remedy advice.

Use meaning and context, not keyword matching.

Confirmed booking: {state.get("confirmed_booking")}
Patient profile: {state.get("patient_profile") or "Unknown"}
Previous remedy: {state.get("remedy_text")}
Latest patient reply: {user_text}

Classify the reply:
- improving: patient says the remedy helped or they feel better.
- persisting_or_worsening: patient says symptoms continue, worsened, did not improve, or they want doctor help now.
- agrees_to_forward_note: patient agrees to forward new symptoms to the booked doctor.
- declines_forward_note: patient declines forwarding the note.
- unclear: not enough information.

Return only JSON:
{follow_up_parser.get_format_instructions()}
""".strip()

    raw_output = generate_text(prompt)
    clean_json = _clean_json(raw_output)
    print(f"Remedy follow-up JSON: {clean_json}")

    try:
        return follow_up_parser.parse(clean_json)
    except Exception as exc:
        print(f"Remedy follow-up parser failed: {exc}")
        return None


def remedy_agent_node(state: GraphState):
    awaiting = state.get("awaiting")

    # Phase 2: patient has responded to remedy.
    if awaiting == "remedy_check":
        user_text = state.get("user_input", "")

        history = state.get("conversation_history") or []
        updated_history = list(history)
        updated_history.append({"role": "patient", "text": user_text})
        confirmed_booking = state.get("confirmed_booking")

        decision = _classify_follow_up(state, user_text)
        patient_status = decision.patient_status if decision else "unclear"

        if confirmed_booking and patient_status == "agrees_to_forward_note":
            response = (
                f"Done, I have noted these symptoms for {confirmed_booking.get('doctor', 'your doctor')} "
                "so they can review them with your appointment details."
            )
            updated_history.append({"role": "assistant", "text": response})
            return {
                "conversation_history": updated_history,
                "awaiting": None,
                "note_forwarded": True,
                "final_response": response,
            }

        if confirmed_booking and patient_status == "declines_forward_note":
            response = "No problem, I will keep the appointment as it is."
            updated_history.append({"role": "assistant", "text": response})
            return {
                "conversation_history": updated_history,
                "awaiting": None,
                "note_forwarded": False,
                "final_response": response,
            }

        if patient_status == "persisting_or_worsening":
            bridge = (
                "I am sorry to hear the remedy has not helped. "
                "Since your symptoms are persisting, let me find the right doctor for you."
            )
            updated_history.append({"role": "assistant", "text": bridge})
            return {
                "conversation_history": updated_history,
                "awaiting": None,
                "persisting": True,
            }

        if patient_status == "improving":
            closing = (
                "That is great to hear! I am glad you are feeling better. "
                "Do take care of yourself, stay hydrated, and rest well. "
                "If symptoms return or worsen at any point, do not hesitate to come back. "
                "Wishing you a speedy recovery!"
            )
            updated_history.append({"role": "assistant", "text": closing})
            return {
                "conversation_history": updated_history,
                "awaiting": None,
                "persisting": False,
                "final_response": closing,
            }

        clarification = (
            "I want to make sure I understand - are your symptoms improving with the remedy, "
            "or are they still persisting or getting worse? Please let me know."
        )
        updated_history.append({"role": "assistant", "text": clarification})
        return {
            "conversation_history": updated_history,
            "awaiting": "remedy_check",
            "final_response": clarification,
        }

    # Phase 1: generate the remedy.
    symptoms = state.get("symptoms") or []
    severity = state.get("severity") or "moderate"
    history = state.get("conversation_history") or []
    confirmed_booking = state.get("confirmed_booking")
    collected_info = state.get("collected_info") or {}
    booking_active = bool(state.get("booking_active"))
    state["symptoms"] = symptoms
    state["booking_active"] = booking_active

    if severity == "emergency":
        response = (
            "Based on what you have described, your symptoms may be serious and require "
            "immediate medical attention. Please call emergency services or go to the nearest "
            "emergency room right away. Do not attempt home remedies for this."
        )
        updated_history = list(history)
        updated_history.append({"role": "assistant", "text": response})
        return {
            "conversation_history": updated_history,
            "remedy_given": True,
            "remedy_text": response,
            "awaiting": None,
            "persisting": True,
            "final_response": response,
        }

    prompt = f"""
You are a compassionate medical assistant agent. Review the patient's symptoms and context,
then provide 2 brief, personalised care tips.

Look closely at the 'Confirmed Booking' context below.
- If 'Confirmed Booking' is empty/None, ask the user if they want to book an appointment for these new symptoms.
- If 'Confirmed Booking' contains data, DO NOT offer a new booking. Instead, close your response by asking if they would like you to forward these new symptoms as a clinical note to their upcoming doctor.

Confirmed Booking Context: {confirmed_booking}
Patient profile from hospital records: {state.get("patient_profile") or "Unknown"}
Active appointments: {state.get("active_appointments") or state.get("confirmed_bookings") or []}
Current Symptoms: {state['symptoms']}
Collected Context: {collected_info}

Return only JSON with no extra text:
{parser.get_format_instructions()}
""".strip()

    raw_output = generate_text(prompt)
    print(f"REMEDY RAW OUTPUT: {raw_output[:300]}")
    clean_json = raw_output.replace("```json", "").replace("```", "").strip()

    try:
        remedy = parser.parse(clean_json)
        remedy_text = remedy.remedy_text
        follow_up = remedy.follow_up_question
    except Exception as exc:
        print(f"Remedy parser failed: {exc}")
        remedy_text = (
            "I am having trouble generating tailored care advice right now. Please avoid "
            "anything that worsens your symptoms, rest if you can, and seek medical care "
            "promptly if symptoms are severe, unusual, or getting worse."
        )
        if confirmed_booking:
            follow_up = (
                "Would you like me to forward these new symptoms as a clinical note "
                f"to {confirmed_booking.get('doctor', 'your booked doctor')}?"
            )
        else:
            follow_up = REMEDY_FOLLOW_UP

    full_response = f"{remedy_text}\n\n{follow_up}"
    updated_history = list(history)
    updated_history.append({"role": "assistant", "text": full_response})

    return {
        "conversation_history": updated_history,
        "remedy_given": True,
        "remedy_text": remedy_text,
        "awaiting": "remedy_check",
        "final_response": full_response,
    }
