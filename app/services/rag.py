from collections import defaultdict
from dataclasses import dataclass, field

from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import DepartmentDecision
from app.inference.llm import generate_text
from app.services.embeddings import embed_query
from app.services.memory_policy import get_memory_policy
from app.services.vector_store import search_clinical_knowledge

try:
    from sentence_transformers import CrossEncoder
except ModuleNotFoundError:
    CrossEncoder = None


DEFAULT_DEPARTMENT = "General Physician"
RAG_MATCH_LIMIT = 20
RAG_RERANK_LIMIT = 3
MIN_CONFIDENT_SCORE = 0.65
RERANKER_MODEL = "BAAI/bge-reranker-base"

DEPARTMENT_SYMPTOM_RULES: dict[str, tuple[str, ...]] = {
    "Cardiology": (
        "chest pain", "chest tightness", "palpitation", "heart", "left arm pain",
        "rapid heartbeat", "irregular heartbeat", "chest pressure",
    ),
    "Dermatology": (
        "rash", "itch", "skin", "hives", "acne", "eczema", "psoriasis",
        "skin infection", "skin lesion", "itching",
    ),
    "Neurology": (
        "leg pain", "calf", "calves", "throbbing", "tingling", "numbness", "seizure",
        "loss of speech", "paralysis", "migraine", "severe headache", "tremor",
        "balance problem", "memory loss", "confusion",
    ),
    "Orthopedics": (
        "back pain", "lower back", "spine", "joint", "knee", "shoulder", "fracture",
        "sprain", "lifting", "gym", "muscle pain", "bone", "hip", "wrist", "ankle",
        "neck pain", "stiff neck", "joint swelling",
    ),
    "Gastroenterology": (
        "stomach", "abdominal", "vomiting", "diarrhea", "constipation", "loss of appetite",
        "nausea", "loose motion", "loose stool", "stomach pain", "acid reflux",
        "heartburn", "bloating", "indigestion", "stomach cramps",
    ),
    "Pulmonology": (
        "cough", "breath", "asthma", "wheezing", "lungs", "shortness of breath",
        "chest congestion", "respiratory", "sputum", "breathless",
    ),
    "Ophthalmology": (
        "eye pain", "eye redness", "blurry vision", "vision loss", "eye discharge",
        "eye infection", "watery eyes", "double vision", "eye swelling",
    ),
    "ENT": (
        "ear pain", "ear infection", "hearing loss", "sore throat", "throat pain",
        "tonsil", "nasal congestion", "sinus", "sneezing", "runny nose",
        "hoarse voice", "difficulty swallowing",
    ),
    "Psychiatry": (
        "anxiety", "depression", "panic attack", "mental health", "mood swings",
        "suicidal", "sleep disorder", "bipolar", "hallucination", "phobia",
        "obsessive", "compulsive",
    ),
    "Urology": (
        "urinary", "burning urination", "frequent urination", "kidney stone",
        "bladder", "prostate", "urine color", "blood in urine",
    ),
    "Endocrinology": (
        "diabetes", "thyroid", "blood sugar", "insulin", "hormone imbalance",
        "unexplained weight gain", "unexplained weight loss",
    ),
    "General Physician": (
        "fatigue", "exhaustion", "general weakness", "malaise", "body ache",
        "flu", "cold", "viral", "general checkup", "mild fever",
    ),
}

department_parser = PydanticOutputParser(pydantic_object=DepartmentDecision)
_reranker = None
MEMORY_POLICY = get_memory_policy("medical_rag")

# 100% STATIC CACHEABLE PREFIX
STATIC_DEPARTMENT_PROMPT = f"""You are a hospital department routing assistant.

Choose the most appropriate department from the symptoms and any retrieved clinical context. Use clinical meaning, not hardcoded keyword matching. Prefer a specific department when the symptoms clearly point there; otherwise ask for clarification.

Default fallback department: {DEFAULT_DEPARTMENT}

Return ONLY valid JSON matching this exact structure:
{{"department":"string or null","confidence":float,"needs_clarification":true|false,"reason":"string"}}"""

@dataclass
class DepartmentMatch:
    department: str | None
    confidence: float
    source: str
    needs_clarification: bool = False
    reason: str = ""
    retrieval_attempted: bool = False
    retrieval_confidence: float = 0.0
    candidate_departments: list[dict[str, object]] = field(default_factory=list)


def _clean_json(raw_output: str) -> str:
    return raw_output.replace("```json", "").replace("```", "").strip()


def _flatten_context(symptoms: list[str], collected_info: dict | None = None) -> str:
    parts = list(symptoms)
    for value in (collected_info or {}).values():
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).lower()


def _heuristic_department(
    symptoms: list[str],
    collected_info: dict | None = None,
) -> DepartmentMatch | None:
    candidates = _heuristic_department_candidates(symptoms, collected_info)
    if not candidates:
        return None

    top = candidates[0]
    return DepartmentMatch(
        department=str(top["department"]),
        confidence=float(top["confidence"]),
        source="heuristic",
        reason=str(top["reason"]),
        candidate_departments=candidates,
    )


def _heuristic_department_candidates(
    symptoms: list[str],
    collected_info: dict | None = None,
) -> list[dict[str, object]]:
    text = _flatten_context(symptoms, collected_info)

    if not text.strip():
        return []

    scores: dict[str, float] = defaultdict(float)
    evidence: dict[str, list[str]] = defaultdict(list)

    # PRIORITY: Check for exact/high-confidence symptom matches first
    for department, terms in DEPARTMENT_SYMPTOM_RULES.items():
        for term in terms:
            if term in text:
                scores[department] += 1.0
                evidence[department].append(term)

    # If no matches, return empty
    if not scores:
        return []

    candidates = sorted(
        (
            {
                "department": department,
                "confidence": min(0.99, 0.60 + (scores[department] * 0.15)),  # Increased confidence for strong matches
                "matched_terms": evidence[department][:4],
                "reason": f"Matched {', '.join(evidence[department][:3])}.",
            }
            for department in scores
            if department != DEFAULT_DEPARTMENT  # Prioritize specific departments
        ),
        key=lambda item: float(item["confidence"]),
        reverse=True,
    )

    # Append default department as fallback only if no specific matches found above
    if not candidates and scores.get(DEFAULT_DEPARTMENT):
        candidates.append({
            "department": DEFAULT_DEPARTMENT,
            "confidence": 0.55,
            "matched_terms": evidence[DEFAULT_DEPARTMENT][:4],
            "reason": f"Matched {', '.join(evidence[DEFAULT_DEPARTMENT][:3])}.",
        })

    return candidates


def _llm_department(
    symptoms: list[str],
    vector_context: list[dict] | None = None,
    collected_info: dict | None = None,
    *,
    node_name: str = "medical_rag",
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> DepartmentMatch:
    
    dynamic_user_prompt = f"""Symptoms: {symptoms}
Collected patient context: {collected_info or {}}
Retrieved clinical context: {vector_context or []}"""

    raw_output = generate_text(
        system_prompt=STATIC_DEPARTMENT_PROMPT,
        user_prompt=dynamic_user_prompt,
        node_name=node_name,
        chat_summary=chat_summary,
        include_history=True,
        history_turns=MEMORY_POLICY.prompt_window_turns,
        patient_id=patient_id,
        chat_session_id=chat_session_id,
    )
    clean_json = _clean_json(raw_output)
    print(f"Department decision JSON: {clean_json}")

    try:
        decision = department_parser.parse(clean_json)
    except Exception as exc:
        print(f"Department decision parser failed: {exc}")
        return DepartmentMatch(
            department=None,
            confidence=0,
            source="llm_parse_error",
            needs_clarification=True,
            reason="Could not parse department decision.",
        )

    # When the LLM says clarification is needed, the department is uncertain —
    # return None so downstream code always triggers a clarifying question.
    department = None if decision.needs_clarification else decision.department
    return DepartmentMatch(
        department=department,
        confidence=decision.confidence,
        source="llm",
        needs_clarification=decision.needs_clarification,
        reason=decision.reason,
        retrieval_attempted=bool(vector_context),
        retrieval_confidence=max(
            (float(item.get("score", 0.0) or 0.0) for item in (vector_context or [])),
            default=0.0,
        ),
    )


def _get_reranker():
    global _reranker
    if _reranker is not None or CrossEncoder is None:
        return _reranker

    try:
        _reranker = CrossEncoder(RERANKER_MODEL)
    except Exception as exc:
        print(f"[RAG Notice] Cross-encoder reranker unavailable: {exc}")
        _reranker = None
    return _reranker


def _rerank_matches(query_text: str, matches, limit: int = RAG_RERANK_LIMIT):
    if not matches:
        return []

    reranker = _get_reranker()
    if not reranker:
        return list(matches[:limit])

    pairs = []
    for match in matches:
        payload = match.payload or {}
        chunk_text = payload.get("chunk_text") or payload.get("text") or ""
        pairs.append((query_text, str(chunk_text)))

    try:
        scores = reranker.predict(pairs)
    except Exception as exc:
        print(f"[RAG Notice] Cross-encoder rerank failed: {exc}")
        return list(matches[:limit])

    scored = sorted(
        zip(matches, scores),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    return [match for match, _ in scored[:limit]]


def _vector_department(matches) -> DepartmentMatch:
    best_scores = defaultdict(float)

    for match in matches:
        payload = match.payload or {}
        department = str(payload.get("department") or "").strip()
        if not department:
            continue

        raw_score = getattr(match, "score", None)
        if raw_score is None:
            score = 1.0
        else:
            score = float(raw_score or 0)

        best_scores[department] = max(best_scores[department], score)

    if not best_scores:
        return DepartmentMatch(
            department=None,
            confidence=0,
            source="vector",
            needs_clarification=True,
            reason="No vector result had a department payload.",
            retrieval_attempted=True,
            retrieval_confidence=0.0,
        )

    department = max(best_scores, key=best_scores.get)
    confidence = best_scores[department]
    reason = f"Best vector score for the reranked chunk was {confidence:.2f}."

    return DepartmentMatch(
        department=department,
        confidence=confidence,
        source="vector",
        needs_clarification=confidence < MIN_CONFIDENT_SCORE,
        reason=reason,
        retrieval_attempted=True,
        retrieval_confidence=confidence,
    )


def _vector_context(matches) -> list[dict]:
    context = []
    for match in matches:
        payload = match.payload or {}
        context.append(
            {
                "department": payload.get("department"),
                "text": payload.get("chunk_text") or payload.get("text"),
                "score": float(getattr(match, "score", 0) or 0),
            }
        )
    return context


def _multi_department_match_from_candidates(
    candidates: list[dict[str, object]],
    *,
    retrieval_attempted: bool,
    retrieval_confidence: float,
) -> DepartmentMatch | None:
    if len(candidates) < 2:
        return None

    top = candidates[:2]
    if float(top[1]["confidence"]) < 0.6:
        return None

    return DepartmentMatch(
        department=None,
        confidence=float(top[0]["confidence"]),
        source="heuristic_multi",
        needs_clarification=True,
        reason=f"The symptoms appear to span both {top[0]['department']} and {top[1]['department']}.",
        retrieval_attempted=retrieval_attempted,
        retrieval_confidence=retrieval_confidence,
        candidate_departments=top,
    )


def match_department_details(
    symptoms: list[str],
    collected_info: dict | None = None,
    *,
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> DepartmentMatch:
    """
    Uses vector retrieval first, then asks the LLM to reason over the symptoms and
    retrieved context when confidence is low or vector search is unavailable.
    """
    if not symptoms:
        return DepartmentMatch(
            department=None,
            confidence=0,
            source="empty",
            needs_clarification=True,
            reason="No symptoms were provided.",
            retrieval_attempted=False,
            retrieval_confidence=0.0,
        )

    cleaned_symptoms = [s.strip() for s in symptoms if s and s.strip()]
    heuristic_match = _heuristic_department(cleaned_symptoms, collected_info)
    heuristic_candidates = list(heuristic_match.candidate_departments if heuristic_match else [])

    try:
        query_parts = [f"symptoms: {', '.join(cleaned_symptoms)}"]
        if collected_info:
            query_parts.append(f"context: {collected_info}")
        query_string = " | ".join(query_parts)
        query_vector = embed_query(query_string)
        matches = search_clinical_knowledge(query_vector, limit=RAG_MATCH_LIMIT)
    except Exception as exc:
        print(f"[RAG Error] Vector search connection failed: {exc}")
        if (heuristic_multi := _multi_department_match_from_candidates(
            heuristic_match.candidate_departments if heuristic_match else [],
            retrieval_attempted=False,
            retrieval_confidence=0.0,
        )):
            return heuristic_multi
        return heuristic_match or _llm_department(
            cleaned_symptoms,
            collected_info=collected_info,
            chat_history=chat_history,
            chat_summary=chat_summary,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )

    if not matches:
        print("[RAG Notice] Qdrant returned 0 matches. Asking LLM for department routing.")
        if (heuristic_multi := _multi_department_match_from_candidates(
            heuristic_match.candidate_departments if heuristic_match else [],
            retrieval_attempted=True,
            retrieval_confidence=0.0,
        )):
            return heuristic_multi
        fallback_match = heuristic_match or _llm_department(
            cleaned_symptoms,
            collected_info=collected_info,
            chat_history=chat_history,
            chat_summary=chat_summary,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
        fallback_match.retrieval_attempted = True
        fallback_match.retrieval_confidence = 0.0
        return fallback_match

    reranked_matches = _rerank_matches(query_string, matches, limit=RAG_RERANK_LIMIT)
    vector_match = _vector_department(reranked_matches)
    context = _vector_context(reranked_matches)

    if (
        not vector_match.department
        or vector_match.needs_clarification
        or vector_match.department == DEFAULT_DEPARTMENT
    ):
        if (heuristic_multi := _multi_department_match_from_candidates(
            heuristic_candidates,
            retrieval_attempted=True,
            retrieval_confidence=vector_match.confidence,
        )):
            return heuristic_multi
        print("[RAG Notice] Vector confidence low. Asking LLM to reason over context.")
        llm_match = _llm_department(
            cleaned_symptoms,
            context,
            collected_info,
            chat_history=chat_history,
            chat_summary=chat_summary,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
        if llm_match.department and not llm_match.needs_clarification:
            return llm_match
        if heuristic_match:
            heuristic_match.retrieval_attempted = True
            heuristic_match.retrieval_confidence = vector_match.confidence
            if heuristic_candidates:
                heuristic_match.candidate_departments = heuristic_candidates
            return heuristic_match
        llm_match.retrieval_attempted = True
        llm_match.retrieval_confidence = vector_match.confidence
        return llm_match

    print(
        f"[RAG Success] Vector matched to: '{vector_match.department}' "
        f"(Score: {vector_match.confidence:.2f})"
    )
    if heuristic_candidates and not vector_match.candidate_departments:
        vector_match.candidate_departments = heuristic_candidates
    return vector_match


def match_department(symptoms: list[str], collected_info: dict | None = None) -> str:
    match = match_department_details(symptoms, collected_info)
    return match.department or DEFAULT_DEPARTMENT
