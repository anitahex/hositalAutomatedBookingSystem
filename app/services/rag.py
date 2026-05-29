from collections import defaultdict
from dataclasses import dataclass

from langchain_core.output_parsers import PydanticOutputParser

from app.agents.schemas import DepartmentDecision
from app.inference.llm import generate_text
from app.services.embeddings import embed_query
from app.services.vector_store import search_clinical_knowledge


DEFAULT_DEPARTMENT = "General Physician"
RAG_MATCH_LIMIT = 5
MIN_CONFIDENT_SCORE = 0.65

department_parser = PydanticOutputParser(pydantic_object=DepartmentDecision)


@dataclass
class DepartmentMatch:
    department: str | None
    confidence: float
    source: str
    needs_clarification: bool = False
    reason: str = ""


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
    text = _flatten_context(symptoms, collected_info)

    if not text.strip():
        return None

    if any(
        term in text
        for term in (
            "chest pain",
            "chest tightness",
            "palpitation",
            "heart",
            "left arm pain",
        )
    ):
        return DepartmentMatch(
            department="Cardiology",
            confidence=0.85,
            source="heuristic",
            reason="Symptoms suggest a heart or chest-related concern.",
        )

    if any(term in text for term in ("rash", "itch", "skin", "hives", "acne")):
        return DepartmentMatch(
            department="Dermatology",
            confidence=0.85,
            source="heuristic",
            reason="Symptoms suggest a skin-related concern.",
        )

    if any(
        term in text
        for term in (
            "back pain",
            "lower back",
            "spine",
            "joint",
            "knee",
            "shoulder",
            "fracture",
            "sprain",
            "lifting",
            "gym",
            "muscle pain",
        )
    ):
        return DepartmentMatch(
            department="Orthopedics",
            confidence=0.82,
            source="heuristic",
            reason="Symptoms suggest a musculoskeletal or spine-related concern.",
        )

    if any(
        term in text
        for term in (
            "weakness in legs",
            "numbness",
            "tingling",
            "seizure",
            "loss of speech",
            "paralysis",
            "migraine",
            "severe headache",
        )
    ):
        return DepartmentMatch(
            department="Neurology",
            confidence=0.82,
            source="heuristic",
            reason="Symptoms suggest a nerve or neurological concern.",
        )

    if any(
        term in text
        for term in (
            "stomach",
            "abdominal",
            "vomiting",
            "diarrhea",
            "constipation",
            "loss of appetite",
            "nausea",
        )
    ):
        return DepartmentMatch(
            department="Gastroenterology",
            confidence=0.82,
            source="heuristic",
            reason="Symptoms suggest a digestive concern.",
        )

    if any(term in text for term in ("cough", "breath", "asthma", "wheezing", "lungs")):
        return DepartmentMatch(
            department="Pulmonology",
            confidence=0.82,
            source="heuristic",
            reason="Symptoms suggest a breathing or lung-related concern.",
        )

    return None


def _llm_department(
    symptoms: list[str],
    vector_context: list[dict] | None = None,
    collected_info: dict | None = None,
) -> DepartmentMatch:
    prompt = f"""
You are a hospital department routing assistant.

Choose the most appropriate department from the symptoms and any retrieved clinical
context. Use clinical meaning, not hardcoded keyword matching. Prefer a specific
department when the symptoms clearly point there; otherwise ask for clarification.

Symptoms: {symptoms}
Collected patient context: {collected_info or {}}
Retrieved clinical context: {vector_context or []}
Default fallback department: {DEFAULT_DEPARTMENT}

Return only JSON:
{department_parser.get_format_instructions()}
""".strip()

    raw_output = generate_text(prompt)
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

    return DepartmentMatch(
        department=decision.department,
        confidence=decision.confidence,
        source="llm",
        needs_clarification=decision.needs_clarification,
        reason=decision.reason,
    )


def _vector_department(matches) -> DepartmentMatch:
    department_scores = defaultdict(float)
    best_scores = defaultdict(float)
    has_scores = False

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
            has_scores = True

        department_scores[department] += score
        best_scores[department] = max(best_scores[department], score)

    if not department_scores:
        return DepartmentMatch(
            department=None,
            confidence=0,
            source="vector",
            needs_clarification=True,
            reason="No vector result had a department payload.",
        )

    department = max(department_scores, key=department_scores.get)
    confidence = best_scores[department]
    reason = (
        f"Best vector score was {confidence:.2f}."
        if has_scores
        else "Vector result had a department payload but no explicit score."
    )

    return DepartmentMatch(
        department=department,
        confidence=confidence,
        source="vector",
        needs_clarification=confidence < MIN_CONFIDENT_SCORE,
        reason=reason,
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


def match_department_details(
    symptoms: list[str],
    collected_info: dict | None = None,
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
        )

    cleaned_symptoms = [s.strip() for s in symptoms if s and s.strip()]
    heuristic_match = _heuristic_department(cleaned_symptoms, collected_info)

    try:
        query_parts = [f"symptoms: {', '.join(cleaned_symptoms)}"]
        if collected_info:
            query_parts.append(f"context: {collected_info}")
        query_string = " | ".join(query_parts)
        query_vector = embed_query(query_string)
        matches = search_clinical_knowledge(query_vector, limit=RAG_MATCH_LIMIT)
    except Exception as exc:
        print(f"[RAG Error] Vector search connection failed: {exc}")
        return heuristic_match or _llm_department(cleaned_symptoms, collected_info=collected_info)

    if not matches:
        print("[RAG Notice] Qdrant returned 0 matches. Asking LLM for department routing.")
        return heuristic_match or _llm_department(cleaned_symptoms, collected_info=collected_info)

    vector_match = _vector_department(matches)
    context = _vector_context(matches)

    if (
        not vector_match.department
        or vector_match.needs_clarification
        or vector_match.department == DEFAULT_DEPARTMENT
    ):
        print("[RAG Notice] Vector confidence low. Asking LLM to reason over context.")
        llm_match = _llm_department(cleaned_symptoms, context, collected_info)
        if llm_match.department and not llm_match.needs_clarification:
            return llm_match
        if heuristic_match:
            return heuristic_match
        return llm_match

    print(
        f"[RAG Success] Vector matched to: '{vector_match.department}' "
        f"(Score: {vector_match.confidence:.2f})"
    )
    return vector_match


def match_department(symptoms: list[str], collected_info: dict | None = None) -> str:
    match = match_department_details(symptoms, collected_info)
    return match.department or DEFAULT_DEPARTMENT
