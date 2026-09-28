"""What the assistant asks after a patient uploads a document.

Uploading a document used to end the conversation. The streaming path set
`active_intent="direct_booking"` and a `target_department` in one assignment and returned
before the graph ever ran, so no question could be asked and the department — guessed from
a regex over the model's own prose — became sticky. A patient who then asked for a
different specialty was answered with the original guess four times running.

This module replaces that with a short, adaptive conversation. It is deterministic: the
questions are templated from what the document actually said, so there is no extra LLM
call, no added latency, and every branch is directly testable.

THREE RULES, in priority order:

  1. SKIP AHEAD. A clear instruction ends the questions immediately — naming a department
     books it, "just store it" files the document and stops. The budget is a ceiling, not
     a quota, and a patient who already knows what they want is never interrogated.
  2. ASK WHAT THE DOCUMENT CANNOT ANSWER. Questions are chosen by what is missing, not
     from a fixed list. A document that states its referral is not asked about referrals.
  3. NEVER DECIDE A CONFLICT SILENTLY. When signals disagree the patient is shown both and
     chooses; that is resolve_department's job, and this module simply hands over to it.
"""
from __future__ import annotations

import re

from app.agents.state import GraphState

# Ceiling, not a quota. Rule 1 means most patients answer fewer. Deliberately separate
# from conversation_agent.MAX_INTAKE_QUESTIONS (6): that governs symptom triage from
# scratch, where there is no document to read the answers off.
MAX_DOCUMENT_FOLLOW_UP_QUESTIONS = 4

AWAITING_DOCUMENT_FOLLOW_UP = "document_follow_up"

# "File it, I don't want an appointment." Must be honoured — not everyone who uploads a
# document wants to be booked, and pushing them into a booking flow is how an assistant
# stops feeling helpful.
_JUST_STORE_PATTERNS = (
    "just store", "just save", "only store", "only save", "for my record",
    "for records", "no appointment", "don't book", "dont book", "do not book",
    "not looking to book", "just keep", "no need to book",
)

_NO_SYMPTOMS_PATTERNS = (
    "no symptom", "not having any", "nothing right now", "feeling fine", "feeling ok",
    "feeling okay", "routine", "just a check", "regular check", "no issues", "nothing",
)

# Topic keys, so a question is never repeated even though questions_asked stores prose.
TOPIC_REFERRAL = "document_referral"
TOPIC_SYMPTOMS = "document_symptoms"
TOPIC_DURATION = "document_duration"
TOPIC_CONFIRM = "document_confirm"


def _lower(text: str | None) -> str:
    return " ".join(str(text or "").lower().split())


def _matches(text: str, patterns) -> bool:
    lowered = _lower(text)
    return any(pattern in lowered for pattern in patterns)


def wants_to_only_store(text: str | None) -> bool:
    return _matches(text or "", _JUST_STORE_PATTERNS)


def reports_no_symptoms(text: str | None) -> bool:
    return _matches(text or "", _NO_SYMPTOMS_PATTERNS)


def latest_document(state: GraphState) -> dict:
    documents = state.get("analyzed_documents") or []
    return documents[-1] if documents else {}


def topics_asked(state: GraphState) -> set[str]:
    return set(state.get("document_topics_asked") or [])


def _describe_document(document: dict) -> str:
    """A short, human reference to the document, for use inside a question."""
    doc_type = str(document.get("document_type") or "").replace("_", " ").strip()
    return doc_type or "document"


def next_question(state: GraphState) -> tuple[str, str] | None:
    """The next (topic, question) to ask, or None when there is nothing worth asking.

    Chosen by what the document could NOT tell us, so the decisive question comes first
    and a patient who abandons the flow early has still answered the one that matters.
    """
    document = latest_document(state)
    asked = topics_asked(state)
    referral = document.get("referring_department")
    referring_doctor = document.get("referring_doctor")
    history = document.get("clinical_history")

    # 1. The referral. The single most useful question when one is printed: it was a
    #    Psychiatry referral being ignored that caused the incident behind this module.
    if referral and TOPIC_REFERRAL not in asked:
        who = f"Dr. {referring_doctor}" if referring_doctor and not str(referring_doctor).lower().startswith("dr") else (referring_doctor or f"the {referral} team")
        return TOPIC_REFERRAL, (
            f"I can see this was referred by {who} in {referral}. "
            "Is this a follow-up for that, or is something new going on?"
        )

    # 2. What is happening NOW. The document describes a moment in the past; only the
    #    patient knows whether it still applies.
    if TOPIC_SYMPTOMS not in asked:
        if history:
            return TOPIC_SYMPTOMS, (
                f"This mentions {str(history).strip().rstrip('.')}. "
                "Is that still the main problem, or has it changed?"
            )
        return TOPIC_SYMPTOMS, (
            f"Thanks for sharing this {_describe_document(document)}. "
            "Are you having any symptoms at the moment, or is this a routine check?"
        )

    # 3. How long / how bad — only worth asking once they have said something is wrong.
    if TOPIC_DURATION not in asked and (state.get("symptoms") or history):
        return TOPIC_DURATION, "How long has this been going on, and how severe does it feel?"

    return None


def register_question(state: GraphState, topic: str, question: str) -> dict:
    """State delta recording that a question was asked. Tracks TOPICS as well as prose:
    questions_asked holds whole sentences (and other nodes push non-questions into it),
    so counting it alone cannot tell us what has actually been covered."""
    asked_topics = list(state.get("document_topics_asked") or [])
    if topic not in asked_topics:
        asked_topics.append(topic)
    asked_questions = list(state.get("questions_asked") or [])
    asked_questions.append(question)
    return {
        "document_topics_asked": asked_topics,
        "questions_asked": asked_questions,
    }


def budget_exhausted(state: GraphState) -> bool:
    return len(topics_asked(state)) >= MAX_DOCUMENT_FOLLOW_UP_QUESTIONS


def resolve_after_followup(state: GraphState) -> dict:
    """Turn everything known — document, referral, answers — into a department decision.

    Returns a state delta. Never books on a conflict: resolve_department hands back
    "ask", and the existing department-selection menu takes it from there.
    """
    from app.services.appointments import routable_departments
    from app.services.department_resolver import (
        DepartmentSignal,
        resolve_department,
        signal_from_text,
        signals_from_document,
    )

    valid = routable_departments()
    document = latest_document(state)
    signals = signals_from_document(document, valid)

    # Anything the patient said during the follow-up outranks the document.
    explicit = state.get("requested_department")
    if explicit:
        signals.insert(0, DepartmentSignal(
            department=explicit, source="explicit_request", confidence=1.0,
            reason="you asked for this department",
        ))

    for symptom in (state.get("symptoms") or [])[:5]:
        signal = signal_from_text(symptom, "symptoms", valid, reason=f"you mentioned {symptom}")
        if signal:
            signals.append(signal)

    resolution = resolve_department(signals, valid)

    if resolution.decision == "resolved":
        return {
            "awaiting": None,
            "active_intent": "direct_booking",
            "intent": "direct_booking",
            "target_department": resolution.department,
            "requested_department": resolution.department,
            "department_match_source": "document_followup",
            "department_match_reason": resolution.reason,
            "candidate_departments": resolution.candidates,
        }

    if resolution.decision == "ask":
        return {
            "awaiting": None,
            "active_intent": "direct_booking",
            "intent": "direct_booking",
            "candidate_departments": resolution.candidates,
            "department_match_source": "document_followup",
            "department_match_reason": resolution.reason,
        }

    # Nothing usable. Hand back to normal booking rather than inventing a department.
    return {
        "awaiting": None,
        "active_intent": "direct_booking",
        "intent": "direct_booking",
        "candidate_departments": [],
        "department_match_source": "document_followup",
    }
