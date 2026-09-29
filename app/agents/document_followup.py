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

import json
import logging
import re

from app.agents.state import GraphState

logger = logging.getLogger(__name__)

# Ceiling, not a quota. Rule 1 means most patients answer fewer. Deliberately separate
# from conversation_agent.MAX_INTAKE_QUESTIONS (6): that governs symptom triage from
# scratch, where there is no document to read the answers off.
MAX_DOCUMENT_FOLLOW_UP_QUESTIONS = 4
# The floor for a patient who does not skip ahead: a document alone rarely says enough
# for a doctor, so at least this many questions are asked before the summary. Only the
# model can supply them; when it is unavailable the templates may run out sooner.
MIN_DOCUMENT_FOLLOW_UP_QUESTIONS = 3

# Bounds on what one document can contribute to a prompt or a note.
MAX_KEY_FINDINGS = 8
MAX_FINDING_CHARS = 300
MAX_QUESTION_CHARS = 300

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
        # The printed referral often names the specialty already ("Dr. Panday (Psychiatry)");
        # saying it twice read as "referred by Dr. Panday (Psychiatry) in Psychiatry".
        where = "" if str(referral).lower() in str(who).lower() else f" in {referral}"
        return TOPIC_REFERRAL, (
            f"I can see this was referred by {who}{where}. "
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
    qa = list(state.get("document_followup_qa") or [])
    qa.append({"topic": topic, "question": question, "answer": None})
    return {
        "document_topics_asked": asked_topics,
        "questions_asked": asked_questions,
        "document_followup_qa": qa,
    }


def record_answer(state: GraphState, answer: str | None) -> dict:
    """State delta filling in the answer to the question asked last.

    Only the latest unanswered question takes the answer, so a message that arrives with
    nothing outstanding changes nothing.
    """
    text = " ".join(str(answer or "").split())[:500]
    qa = [dict(item) for item in (state.get("document_followup_qa") or []) if isinstance(item, dict)]
    if not text or not qa or qa[-1].get("answer") is not None:
        return {}
    qa[-1]["answer"] = text
    return {"document_followup_qa": qa}


def questions_asked_this_round(state: GraphState) -> int:
    return len(topics_asked(state))


def round_documents(state: GraphState) -> list[dict]:
    """The documents uploaded in the current round, or every document when none is marked.

    Questions are about what was just uploaded; the summary covers every document.
    """
    documents = [d for d in (state.get("analyzed_documents") or []) if isinstance(d, dict)]
    current = state.get("document_followup_round")
    if current is None:
        return documents
    in_round = [d for d in documents if d.get("followup_round") == current]
    return in_round or documents


def start_round(state: GraphState) -> dict:
    """State delta for a new upload: its own questions, and a summary rebuilt to cover it.

    Answers from an earlier round are kept, so the model can see them and not ask again.
    """
    return {
        "document_followup_round": int(state.get("document_followup_round") or 0) + 1,
        "document_topics_asked": [],
        "checkup_summary_shown": False,
    }


# ---- what a document found ----

# Analysis headings whose content IS the finding. Everything else in the analysis is
# demographics, technique or advice.
_FINDING_SECTIONS = {"key findings", "findings", "impression", "clinical assessment"}
_ABNORMAL_STATUS = re.compile(r"high|low|abnormal|critical|⚠", re.IGNORECASE)


def _plain(text: str) -> str:
    cleaned = re.sub(r"[*_`]+", "", str(text or ""))
    return " ".join(cleaned.split()).strip(" -•")


def _clip(text: str, limit: int) -> str:
    """At most `limit` characters, cut at a word and marked, never mid-word."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return f"{cut}…"


def parse_key_findings(analysis_text: str | None) -> list[str]:
    """What the document found, read by code out of the analysis the patient was shown.

    Two sources, abnormal results first:
      - rows of a results table whose status says High, Low, Abnormal or Critical;
      - the bullets or paragraph under Key Findings, Findings, Impression or Clinical
        Assessment.
    Deduplicated and bounded, so one long report cannot crowd out the others.
    """
    abnormal: list[str] = []
    stated: list[str] = []
    section = None
    for raw in str(analysis_text or "").splitlines():
        line = raw.strip()
        heading = re.match(r"^#{2,4}\s+(.+)$", line)
        if heading:
            section = _plain(heading.group(1)).lower()
            continue
        if line.startswith("|"):
            cells = [_plain(c) for c in line.strip("|").split("|")]
            if len(cells) < 3 or all(set(c) <= set("-: ") for c in cells):
                continue
            status = cells[-1]
            if cells[0].lower() in {"test", "parameter", "investigation"}:
                continue
            if _ABNORMAL_STATUS.search(status):
                name, value = cells[0], cells[1]
                reference = cells[2] if len(cells) >= 4 else ""
                flag = re.sub(r"[^A-Za-z ]", "", status).strip() or "Abnormal"
                entry = f"{name}: {value}" + (f" (normal {reference})" if reference else "") + f" — {flag}"
                abnormal.append(entry)
            continue
        if section in _FINDING_SECTIONS and line:
            text = _plain(line)
            if text:
                stated.append(text)

    findings: list[str] = []
    seen: set[str] = set()
    for item in abnormal + stated:
        clipped = _clip(item, MAX_FINDING_CHARS)
        key = clipped.lower()
        if key in seen:
            continue
        seen.add(key)
        findings.append(clipped)
        if len(findings) >= MAX_KEY_FINDINGS:
            break
    return findings


def describe_documents_for_prompt(documents: list[dict]) -> str:
    """The documents as a prompt block: name, type, referral, stated history, findings."""
    blocks = []
    for index, document in enumerate(documents, start=1):
        lines = [f"Document {index}: {document.get('file_name') or 'document'} ({_describe_document(document)})"]
        if document.get("referring_doctor") or document.get("referring_department"):
            lines.append(f"  Referred by: {document.get('referring_doctor') or ''} {document.get('referring_department') or ''}".rstrip())
        if document.get("clinical_history"):
            lines.append(f"  Reason for the test: {document['clinical_history']}")
        findings = document.get("key_findings") or []
        if findings:
            lines.append("  Findings:")
            lines.extend(f"   - {finding}" for finding in findings[:MAX_KEY_FINDINGS])
        else:
            lines.append("  Findings: none could be read from the analysis")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) or "No documents."


def describe_qa_for_prompt(state: GraphState) -> str:
    rows = []
    for item in state.get("document_followup_qa") or []:
        if not isinstance(item, dict):
            continue
        rows.append(f"Q: {item.get('question')}\nA: {item.get('answer') or '(not answered yet)'}")
    return "\n".join(rows) or "None yet."


# ---- choosing the next question ----

_QUESTION_SYSTEM_PROMPT = """You are the intake assistant in a hospital chat. The patient has just shared medical documents. Your job is to ask the NEXT single follow-up question that will most help the doctor who sees them.

Rules:
- Ask about something a specific finding raises (an abnormal value, an impression, a stated diagnosis), or about the patient's current symptoms, duration, severity, medicines or history that the documents cannot answer.
- Mention the finding in plain words when you ask about it, e.g. "Your HbA1c is 8.1%, which is high. Have you been told you have diabetes, or noticed more thirst or urination?"
- ONE question only, under 40 words, friendly and simple. No diagnosis, no reassurance, no medicine or dose advice.
- Never repeat a question already asked, and never ask for something the patient already answered.
- If at least {minimum} questions have been asked and nothing important is left, set done to true.

Return ONLY valid JSON:
{{"done": false, "topic": "short_snake_case_topic", "question": "the question", "symptoms_mentioned": ["symptoms the patient's latest answer mentions, in plain words"]}}"""


def _ask_model(system_prompt: str, user_prompt: str, state: GraphState) -> str:
    """The one model call. Separate so tests replace it and never reach the network."""
    from app.inference.llm import generate_text

    return generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        node_name="document_followup_question",
        include_history=False,
        history_turns=0,
        patient_id=str(state.get("patient_id") or ""),
        chat_session_id=str(state.get("chat_session_id") or ""),
    )


def _normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", " ".join(str(text or "").lower().split()))


def validate_model_question(raw: str | None, state: GraphState) -> dict | None:
    """The model's answer checked by code, or None when it is not JSON at all.

    Returns {"done", "topic", "question", "symptoms", "problem"}. A question must end in
    "?", may carry one short clarifier ("…your leg? Is it sharp or burning?"), is bounded
    in length, and is new — neither its topic nor its text asked before. When it breaks a
    rule, "question" is None and "problem" says which; the symptoms are kept either way,
    since they come from the patient's answer, not from the question.
    """
    text = str(raw or "").strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    symptoms = [
        " ".join(str(s).split())[:80]
        for s in (data.get("symptoms_mentioned") or [])
        if isinstance(s, str) and s.strip()
    ][:5]
    if data.get("done") is True:
        return {"done": True, "topic": None, "question": None, "symptoms": symptoms, "problem": None}

    def refused(problem: str) -> dict:
        return {"done": False, "topic": None, "question": None, "symptoms": symptoms, "problem": problem}

    question = " ".join(str(data.get("question") or "").split())
    topic = re.sub(r"[^a-z0-9_]", "", str(data.get("topic") or "").lower())[:40] or "finding"
    if not question or not question.endswith("?"):
        return refused("the question must end with a question mark")
    # A question and one clarifier at most; three question marks is a questionnaire.
    if question.count("?") > 2:
        return refused("ask one question, not several")
    if len(question) > MAX_QUESTION_CHARS:
        return refused(f"keep the question under {MAX_QUESTION_CHARS} characters")
    topic_key = f"doc_{topic}"
    earlier = {_normalized(q.get("question")) for q in (state.get("document_followup_qa") or []) if isinstance(q, dict)}
    if topic_key in topics_asked(state) or _normalized(question) in earlier:
        return refused("that topic was already asked about; ask about something else")
    return {"done": False, "topic": topic_key, "question": question, "symptoms": symptoms, "problem": None}


def model_question(state: GraphState, latest_answer: str | None = None) -> dict | None:
    """Asks the model for the next question, once more if its first answer broke a rule.

    None when the call fails or returns something that is not JSON; otherwise the checked
    result, whose "question" is None if both answers broke a rule.
    """
    from app.services.language import language_prompt_context

    documents = round_documents(state)
    asked = questions_asked_this_round(state)
    symptoms = ", ".join(state.get("symptoms") or []) or "none stated yet"
    user_prompt = (
        f"DOCUMENTS:\n{describe_documents_for_prompt(documents)}\n\n"
        f"PATIENT'S SYMPTOMS SO FAR: {symptoms}\n\n"
        f"QUESTIONS AND ANSWERS SO FAR:\n{describe_qa_for_prompt(state)}\n\n"
        f"PATIENT'S LATEST MESSAGE: {latest_answer or '(they have just uploaded the documents)'}\n\n"
        f"Questions asked so far: {asked}. Ask at least {MIN_DOCUMENT_FOLLOW_UP_QUESTIONS}, "
        f"at most {MAX_DOCUMENT_FOLLOW_UP_QUESTIONS}."
    )
    system_prompt = _QUESTION_SYSTEM_PROMPT.format(minimum=MIN_DOCUMENT_FOLLOW_UP_QUESTIONS) + language_prompt_context(state)
    result = None
    for attempt in range(2):
        prompt = user_prompt if attempt == 0 else (
            f"{user_prompt}\n\nYour previous answer was not usable: {result['problem']}. Try again."
        )
        try:
            raw = _ask_model(system_prompt, prompt, state)
        except Exception as exc:  # the model is optional here; the templates are the floor
            logger.warning("document_followup: question model failed: %s", exc)
            return result
        checked = validate_model_question(raw, state)
        if checked is None:
            return result
        if result and not checked["symptoms"]:
            checked["symptoms"] = result["symptoms"]
        result = checked
        if result["done"] and asked < MIN_DOCUMENT_FOLLOW_UP_QUESTIONS:
            result["problem"] = (
                f"at least {MIN_DOCUMENT_FOLLOW_UP_QUESTIONS} questions must be asked before you are done"
            )
        if not result["problem"]:
            return result
        logger.info("document_followup: model question refused (%s)", result["problem"])
    return result


def _referral_in_round(state: GraphState) -> dict | None:
    for document in round_documents(state):
        if document.get("referring_department"):
            return document
    return None


def choose_next_question(state: GraphState, latest_answer: str | None = None) -> dict:
    """What to do next: {"question": (topic, text) | None, "symptoms": [...]}.

    In order:
      1. A printed referral, asked with the fixed question — the decisive one.
      2. A question the model grounds in the findings, if it passes the checks.
      3. The fixed templates, when the model is unavailable or its answer failed a check.
    A question of None means the questions are over.
    """
    if budget_exhausted(state):
        return {"question": None, "symptoms": []}

    referral_document = _referral_in_round(state)
    if referral_document and TOPIC_REFERRAL not in topics_asked(state):
        return {"question": next_question({**state, "analyzed_documents": [referral_document]}), "symptoms": []}

    result = model_question(state, latest_answer)
    symptoms = (result or {}).get("symptoms") or []
    if result and result["question"]:
        return {"question": (result["topic"], result["question"]), "symptoms": symptoms}
    if result and result["done"] and questions_asked_this_round(state) >= MIN_DOCUMENT_FOLLOW_UP_QUESTIONS:
        return {"question": None, "symptoms": symptoms}
    return {"question": next_question(state), "symptoms": symptoms}


def merge_symptoms(state: GraphState, mentioned: list[str]) -> dict:
    """State delta adding newly mentioned symptoms, without duplicates."""
    existing = list(state.get("symptoms") or [])
    known = {s.lower() for s in existing}
    added = [s for s in mentioned if s.lower() not in known]
    return {"symptoms": existing + added} if added else {}


def findings_note(state: GraphState) -> str | None:
    """A doctor-facing note built by code from the documents and the answers.

    Used when the patient agrees to send a note but no summary was made — they named a
    department and skipped the questions — so the findings still reach the doctor. Written
    in the markdown the doctor's screens render (heading, bold, flat bullets), not as a
    plain-text block.
    """
    documents = [d for d in (state.get("analyzed_documents") or []) if isinstance(d, dict)]
    if not documents:
        return None
    lines = [
        "## Documents shared in the booking chat",
        "Findings read by AI from the uploaded documents — check the originals.",
    ]
    for document in documents:
        lines.append("")
        lines.append(f"**{document.get('file_name') or 'document'}** · {_describe_document(document)}")
        findings = (document.get("key_findings") or [])[:MAX_KEY_FINDINGS]
        lines.extend(f"- {finding}" for finding in findings)
        if not findings:
            lines.append("- No findings could be read; see the document.")
    answered = [q for q in (state.get("document_followup_qa") or []) if isinstance(q, dict) and q.get("answer")]
    if answered:
        lines.append("")
        lines.append("**Patient's answers**")
        lines.extend(f"- {item['question']} — {item['answer']}" for item in answered)
    return "\n".join(lines)


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
    # Every document in the round, not only the latest: a referral on the first of three
    # reports is still a referral.
    signals = []
    for document in round_documents(state):
        signals.extend(signals_from_document(document, valid))

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

    # target_department is cleared on both branches below: a value left from earlier in
    # the chat would otherwise read as this decision.
    if resolution.decision == "ask":
        return {
            "awaiting": None,
            "active_intent": "direct_booking",
            "intent": "direct_booking",
            "target_department": None,
            "candidate_departments": resolution.candidates,
            "department_match_source": "document_followup",
            "department_match_reason": resolution.reason,
        }

    # Nothing usable. Hand back to normal booking rather than inventing a department.
    return {
        "awaiting": None,
        "active_intent": "direct_booking",
        "intent": "direct_booking",
        "target_department": None,
        "candidate_departments": [],
        "department_match_source": "document_followup",
    }
