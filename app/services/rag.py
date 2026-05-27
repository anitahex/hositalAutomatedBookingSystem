from collections import defaultdict
from dataclasses import dataclass

from app.services.embeddings import embed_query
from app.services.vector_store import search_clinical_knowledge

DEFAULT_DEPARTMENT = "General Physician"
RAG_MATCH_LIMIT = 5
MIN_CONFIDENT_SCORE = 0.65
KEYWORD_BOOST = 0.2

# Hardcoded keyword fallback dictionary for safety guardrails
DEPARTMENT_KEYWORDS = {
    "Cardiology": {
        "chest pain",
        "chest tightness",
        "heart",
        "palpitation",
        "shortness of breath",
    },
    "Pulmonology": {
        "breath",
        "breathlessness",
        "cough",
        "wheezing",
        "asthma",
    },
    "Neurology": {
        "dizziness",
        "headache",
        "migraine",
        "seizure",
        "stroke",
        "numbness",
    },
    "Orthopedics": {
        "fall",
        "fell",
        "injury",
        "fracture",
        "sprain",
        "back pain",
        "joint pain",
        "knees",
        "knee",
        "hurt too",
    },
    "Dermatology": {
        "rash",
        "itch",
        "allergy",
        "skin",
        "hives",
    },
    "Gastroenterology": {
        "nausea",
        "vomiting",
        "stomach",
        "abdominal",
        "diarrhea",
    },
}


@dataclass
class DepartmentMatch:
    department: str | None
    confidence: float
    source: str
    needs_clarification: bool = False
    reason: str = ""


def _keyword_department(symptoms: list[str]) -> str | None:
    """
    Fallback method that uses exact string matching to find a department
    if Qdrant vector search is unavailable or returns no hits.
    """
    symptom_text = " ".join(symptoms).lower()
    for department, keywords in DEPARTMENT_KEYWORDS.items():
        if any(keyword in symptom_text for keyword in keywords):
            print(f"[RAG Fallback] Keyword matched department: '{department}'")
            return department
    return None


def _department_keyword_match(department: str, symptom_text: str) -> bool:
    return any(keyword in symptom_text for keyword in DEPARTMENT_KEYWORDS.get(department, set()))


def _vector_department(matches, symptom_text: str) -> DepartmentMatch:
    department_scores = defaultdict(float)
    best_scores = defaultdict(float)

    for match in matches:
        payload = match.payload or {}
        department = str(payload.get("department") or "").strip()
        if not department:
            continue

        score = getattr(match, "score", 0) or 0
        score = float(score)
        department_scores[department] += score
        best_scores[department] = max(best_scores[department], score)

    for department in list(department_scores):
        if department != DEFAULT_DEPARTMENT and _department_keyword_match(department, symptom_text):
            department_scores[department] += KEYWORD_BOOST

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
    keyword_supported = department != DEFAULT_DEPARTMENT and _department_keyword_match(
        department, symptom_text
    )

    return DepartmentMatch(
        department=department,
        confidence=confidence,
        source="vector_rerank",
        needs_clarification=confidence < MIN_CONFIDENT_SCORE and not keyword_supported,
        reason=f"Best vector score was {confidence:.2f}.",
    )


def match_department_details(symptoms: list[str]) -> DepartmentMatch:
    """
    Takes a list of symptoms, formats them to match the database chunk schema,
    performs a 384-dimension vector similarity search in Qdrant, and returns 
    the matched hospital department.
    """
    if not symptoms:
        return DepartmentMatch(
            department=None,
            confidence=0,
            source="empty",
            needs_clarification=True,
            reason="No symptoms were provided.",
        )

    # Normalize symptom strings (lowercase and strip whitespace)
    cleaned_symptoms = [s.strip().lower() for s in symptoms]
    symptom_text = " ".join(cleaned_symptoms)
    keyword_department = _keyword_department(cleaned_symptoms)

    try:
        # FIX: Formatted to mirror your Qdrant 'chunk_text' layout exactly:
        # Example output string: "- symp: headache, knee pain"
        query_string = f"- symp: {', '.join(cleaned_symptoms)}"

        # Generate the 384-dimensional embedding vector
        query_vector = embed_query(query_string)

        # Search the 'clinical_knowledge_base' collection via your vector store service
        matches = search_clinical_knowledge(query_vector, limit=RAG_MATCH_LIMIT)

    except Exception as exc:
        print(f"[RAG Error] Vector search connection failed: {exc}")
        if keyword_department:
            return DepartmentMatch(
                department=keyword_department,
                confidence=1,
                source="keyword_after_vector_error",
                reason="Vector search failed, keyword fallback matched.",
            )
        return DepartmentMatch(
            department=None,
            confidence=0,
            source="vector_error",
            needs_clarification=True,
            reason="Vector search failed and no keyword fallback matched.",
        )

    # Handle cases where Qdrant returned an empty list of results
    if not matches:
        print("[RAG Notice] Qdrant returned 0 matches. Trying keyword fallback...")
        if keyword_department:
            return DepartmentMatch(
                department=keyword_department,
                confidence=1,
                source="keyword_after_no_vector_matches",
                reason="Vector returned no matches, keyword fallback matched.",
            )
        return DepartmentMatch(
            department=None,
            confidence=0,
            source="no_vector_matches",
            needs_clarification=True,
            reason="Vector returned no matches and no keyword fallback matched.",
        )

    match = _vector_department(matches, symptom_text)

    # If vector retrieval did not produce a usable specialist, try keyword fallback.
    if not match.department:
        print("[RAG Notice] Vector matched, but payload field 'department' was empty.")
        if keyword_department:
            return DepartmentMatch(
                department=keyword_department,
                confidence=1,
                source="keyword_after_empty_payload",
                reason="Vector payload was empty, keyword fallback matched.",
            )
        return match

    if match.department == DEFAULT_DEPARTMENT and keyword_department:
        print(
            f"[RAG Notice] Vector returned broad department '{DEFAULT_DEPARTMENT}'. "
            f"Using keyword fallback '{keyword_department}'."
        )
        return DepartmentMatch(
            department=keyword_department,
            confidence=1,
            source="keyword_over_broad_vector",
            reason="Vector returned General Physician, keyword fallback matched a specialist.",
        )

    if match.needs_clarification and not keyword_department:
        print(
            f"[RAG Notice] Low-confidence vector match '{match.department}' "
            f"({match.confidence:.2f}). Asking for clarification."
        )
        return DepartmentMatch(
            department=None,
            confidence=match.confidence,
            source=match.source,
            needs_clarification=True,
            reason=match.reason,
        )

    # Successfully extracted department value from Qdrant vector context
    print(f"[RAG Success] Vector matched to: '{match.department}' (Score: {match.confidence:.2f})")
    return match


def match_department(symptoms: list[str]) -> str:
    match = match_department_details(symptoms)
    return match.department or DEFAULT_DEPARTMENT
