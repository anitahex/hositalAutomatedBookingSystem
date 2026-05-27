"""
Remedy Agent
------------
Generates a personalised remedy based on everything collected in the conversation.
After giving the remedy, asks the patient if they are improving or still struggling.
If still persisting, supervisor routes to medical_rag then booking.
"""

from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import RemedyResponse
from app.agents.state import GraphState
from app.inference.llm import generate_text


parser = PydanticOutputParser(pydantic_object=RemedyResponse)

REMEDY_FOLLOW_UP = (
    "Please try these suggestions - they may help relieve your symptoms. "
    "If the discomfort continues, worsens, or you'd like to see a doctor right away, "
    "please let me know."
)

PERSISTING_WORDS = {
    "no", "not better", "still", "worse", "worsening", "persisting", "persist",
    "same", "no improvement", "not improving", "not helping", "didn't help",
    "doesnt help", "doesn't help", "bad", "getting worse", "no change",
    "doctor", "appointment", "book", "hospital", "clinic", "specialist",
}

IMPROVING_WORDS = {
    "yes", "better", "improving", "improved", "good", "fine", "okay", "ok",
    "feeling better", "much better", "great", "relief", "relieved", "helped",
    "it helped", "working", "it worked",
}


def patient_is_persisting(text: str) -> bool:
    normalized = text.strip().lower()
    return any(word in normalized for word in PERSISTING_WORDS)


def patient_is_improving(text: str) -> bool:
    normalized = text.strip().lower()
    return any(word in normalized for word in IMPROVING_WORDS)


def patient_agrees(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {"yes", "y", "sure", "ok", "okay", "please do", "do it"}


def patient_declines_note(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {"no", "nope", "not now", "don't", "dont"}


def _fallback_remedy(symptoms: list[str]) -> str:
    symptom_text = " ".join(symptoms).lower()

    if any(word in symptom_text for word in ["rash", "skin", "itch", "hives", "allergy"]):
        return (
            "For the skin rash, avoid scratching and avoid any new soaps, creams, foods, "
            "or medicines that may have triggered it. Use a cool compress and keep the "
            "area clean and dry. If you develop swelling of the lips or face, breathing "
            "trouble, fever, spreading redness, pus, or severe pain, seek urgent medical care."
        )

    if any(word in symptom_text for word in ["leg pain", "knee pain", "joint pain", "sprain", "injury"]):
        return (
            "For the pain, rest the affected area, avoid putting strain on it, and use a "
            "cold pack wrapped in cloth for 15-20 minutes at a time. If there is severe "
            "pain, swelling, deformity, numbness, or you cannot bear weight, please see a doctor urgently."
        )

    if any(word in symptom_text for word in ["chest pain", "heart pain", "chest tightness"]):
        return (
            "Chest pain or tightness should be checked urgently. Please avoid exertion and "
            "seek medical care right away, especially if there is sweating, breathlessness, "
            "dizziness, pain spreading to the arm or jaw, or worsening discomfort."
        )

    return (
        "Based on your symptoms, I recommend rest, staying well hydrated, and avoiding "
        "any activities that aggravate the problem. Monitor closely for any worsening."
    )


def remedy_agent_node(state: GraphState):
    awaiting = state.get("awaiting")

    # Phase 2: patient has responded to remedy.
    if awaiting == "remedy_check":
        user_text = state.get("user_input", "")

        history = state.get("conversation_history") or []
        updated_history = list(history)
        updated_history.append({"role": "patient", "text": user_text})
        confirmed_booking = state.get("confirmed_booking")

        if confirmed_booking and patient_agrees(user_text):
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

        if confirmed_booking and patient_declines_note(user_text):
            response = "No problem, I will keep the appointment as it is."
            updated_history.append({"role": "assistant", "text": response})
            return {
                "conversation_history": updated_history,
                "awaiting": None,
                "note_forwarded": False,
                "final_response": response,
            }

        if patient_is_persisting(user_text):
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

        if patient_is_improving(user_text):
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
You are a medical assistant agent. Review the user's new symptom and provide 2 brief care tips.

Look closely at the 'Confirmed Booking' context below.
- If 'Confirmed Booking' is empty/None, ask the user if they want to book an appointment for these new symptoms.
- If 'Confirmed Booking' contains data, DO NOT offer a new booking. Instead, close your response by asking if they would like you to forward these new symptoms as a clinical note to their upcoming doctor.

Confirmed Booking Context: {confirmed_booking}
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
        remedy_text = _fallback_remedy(symptoms)
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
