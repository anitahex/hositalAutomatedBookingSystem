"""
Document catalog service — Postgres metadata index + blob-based retrieval.

The catalog stores routing metadata ONLY. No clinical values live here;
those are in the blob summary JSON at blob_summary_path.

Discovery scope: user_id-wide across all sessions (patient history persists).
To scope to current session only, change list_user_documents() WHERE to:
    WHERE user_id = %s AND session_id = %s AND ingestion_status = 'complete'
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.db.connection import connect_db
from app.services.blob_storage import download_blob_json

logger = logging.getLogger(__name__)


# ---- Pydantic schemas ----

class CatalogEntry(BaseModel):
    document_id: str
    user_id: str
    session_id: str
    document_type: str
    clinical_date: str | None
    created_at: datetime
    blob_summary_path: str
    findings_keys: list[str]
    ingestion_status: str


class DocumentIngestionSummary(BaseModel):
    document_type: str
    clinical_date: str | None
    overall_impression: str
    findings: dict[str, Any]


# ---- Low-level DB helpers ----

def _execute_rows(sql: str, params: tuple = ()) -> list[dict]:
    conn = connect_db()
    try:
        import psycopg2.extras
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                if cur.description:
                    return [dict(row) for row in cur.fetchall()]
                return []
    finally:
        conn.close()


def _execute_write(sql: str, params: tuple = ()) -> None:
    conn = connect_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


# ---- Document catalog operations ----

def create_catalog_row(
    *,
    document_id: str,
    user_id: str,
    session_id: str,
    blob_summary_path: str,
    ingestion_status: str = "processing",
) -> None:
    """
    Insert a catalog row before extraction begins (status='processing').
    Must be called BEFORE the blob summary write so a failed write leaves
    a 'processing' row rather than no trace at all.
    """
    sql = """
        INSERT INTO document_catalog (
            document_id, user_id, session_id, blob_summary_path,
            ingestion_status, findings_keys, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
        ON CONFLICT (document_id) DO UPDATE
            SET ingestion_status = EXCLUDED.ingestion_status,
                updated_at        = NOW()
    """
    now = datetime.now(timezone.utc)
    _execute_write(sql, (
        document_id, user_id, session_id, blob_summary_path,
        ingestion_status, "[]", now, now,
    ))
    logger.info("catalog: created row document_id=%s status=%s", document_id, ingestion_status)


def update_catalog_after_extraction(
    *,
    document_id: str,
    document_type: str,
    clinical_date: str | None,
    findings_keys: list[str],
    ingestion_status: str = "complete",
) -> None:
    """Flip the catalog row to 'complete' after the blob summary write succeeds."""
    sql = """
        UPDATE document_catalog
        SET document_type    = %s,
            clinical_date    = %s::date,
            findings_keys    = %s::jsonb,
            ingestion_status = %s,
            updated_at       = NOW()
        WHERE document_id = %s
    """
    _execute_write(sql, (
        document_type,
        clinical_date,
        json.dumps(findings_keys),
        ingestion_status,
        document_id,
    ))
    logger.info(
        "catalog: updated document_id=%s type=%s keys=%s status=%s",
        document_id, document_type, findings_keys, ingestion_status,
    )


def mark_catalog_failed(document_id: str, reason: str = "") -> None:
    """Mark a catalog row as failed; called on any ingestion exception."""
    _execute_write(
        "UPDATE document_catalog SET ingestion_status='failed', updated_at=NOW() WHERE document_id=%s",
        (document_id,),
    )
    logger.error("catalog: marked document_id=%s FAILED — %s", document_id, reason)


def list_user_documents(user_id: str) -> list[CatalogEntry]:
    """
    Return all complete catalog entries for a user (all sessions).
    Returns an empty list if none found.
    """
    sql = """
        SELECT document_id, user_id, session_id, document_type, clinical_date,
               created_at, blob_summary_path, findings_keys, ingestion_status
        FROM document_catalog
        WHERE user_id = %s AND ingestion_status = 'complete'
        ORDER BY created_at DESC
    """
    rows = _execute_rows(sql, (user_id,))
    entries: list[CatalogEntry] = []
    for row in rows:
        try:
            fk = row.get("findings_keys")
            if isinstance(fk, str):
                fk = json.loads(fk)
            entries.append(CatalogEntry(
                document_id=str(row["document_id"]),
                user_id=str(row["user_id"]),
                session_id=str(row["session_id"]),
                document_type=str(row.get("document_type") or "other"),
                clinical_date=str(row["clinical_date"]) if row.get("clinical_date") else None,
                created_at=row["created_at"],
                blob_summary_path=str(row["blob_summary_path"]),
                findings_keys=fk if isinstance(fk, list) else [],
                ingestion_status=str(row["ingestion_status"]),
            ))
        except Exception as exc:
            logger.warning("catalog: skipping malformed row document_id=%s: %s", row.get("document_id"), exc)
    return entries


def get_catalog_entry(document_id: str) -> CatalogEntry | None:
    sql = """
        SELECT document_id, user_id, session_id, document_type, clinical_date,
               created_at, blob_summary_path, findings_keys, ingestion_status
        FROM document_catalog WHERE document_id = %s
    """
    rows = _execute_rows(sql, (document_id,))
    if not rows:
        return None
    row = rows[0]
    fk = row.get("findings_keys")
    if isinstance(fk, str):
        try:
            fk = json.loads(fk)
        except Exception:
            fk = []
    return CatalogEntry(
        document_id=str(row["document_id"]),
        user_id=str(row["user_id"]),
        session_id=str(row["session_id"]),
        document_type=str(row.get("document_type") or "other"),
        clinical_date=str(row["clinical_date"]) if row.get("clinical_date") else None,
        created_at=row["created_at"],
        blob_summary_path=str(row["blob_summary_path"]),
        findings_keys=fk if isinstance(fk, list) else [],
        ingestion_status=str(row["ingestion_status"]),
    )


# ---- Pending upload operations ----

def save_pending_upload(
    *,
    document_token: str,
    user_id: str,
    session_id: str,
    document_id: str,
    blob_path: str,
    original_filename: str,
) -> None:
    sql = """
        INSERT INTO pending_uploads (
            document_token, user_id, session_id, document_id,
            blob_path, original_filename, created_at, consumed
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
        ON CONFLICT (document_token) DO NOTHING
    """
    _execute_write(sql, (
        document_token, user_id, session_id, document_id,
        blob_path, original_filename, datetime.now(timezone.utc),
    ))
    logger.info("pending_uploads: saved token=%s document_id=%s", document_token, document_id)


def consume_pending_upload(document_token: str) -> dict | None:
    """
    Atomically mark a token consumed and return its record.
    Returns None for missing, expired (>30 min), or already-consumed tokens.
    Idempotent: a duplicate request returns None and triggers no second ingestion.
    """
    sql = """
        UPDATE pending_uploads
        SET consumed = TRUE
        WHERE document_token = %s
          AND consumed = FALSE
          AND created_at > NOW() - INTERVAL '30 minutes'
        RETURNING user_id, session_id, document_id, blob_path, original_filename
    """
    rows = _execute_rows(sql, (document_token,))
    if not rows:
        logger.warning("pending_uploads: token not found/expired/consumed: %s", document_token)
        return None
    logger.info("pending_uploads: consumed token=%s", document_token)
    return dict(rows[0])


# ---- Retrieval: HF-model relevance selection ----

def select_relevant_documents(
    question: str,
    catalog: list[CatalogEntry],
    *,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> list[str]:
    """
    Use the HF router model to decide which document_id(s) are relevant.
    Returns an empty list if no documents are relevant or the catalog is empty.

    Disambiguation rule: for multiple same-type documents the model should
    pick the most-recent by clinical_date. If genuinely ambiguous the model
    returns 'CLARIFY', which also maps to an empty list so the caller can
    ask the user to be more specific.
    """
    if not catalog:
        return []

    from app.inference.llm import generate_router_text

    catalog_lines = "\n".join(
        f"- document_id={e.document_id}, type={e.document_type}, "
        f"date={e.clinical_date or 'unknown'}, findings_keys={e.findings_keys}"
        for e in catalog
    )

    system_prompt = (
        "You are a document routing assistant. Given a patient's question and a list of "
        "available medical documents, decide which document_id(s) are relevant.\n\n"
        "Rules:\n"
        "- If multiple documents of the same type exist, prefer the most recent by clinical_date "
        "unless the question specifies otherwise.\n"
        "- If the question is genuinely ambiguous across documents with close dates, output exactly: CLARIFY\n"
        "- If no document is relevant, output exactly: NONE\n"
        "- Otherwise output ONLY a comma-separated list of document_id values, nothing else.\n\n"
        "Example outputs: NONE | CLARIFY | abc-uuid-1 | abc-uuid-1,abc-uuid-2"
    )

    user_prompt = (
        f"Available documents:\n{catalog_lines}\n\n"
        f"Patient question: {question}\n\n"
        "Which document_id(s) are relevant? Output ONLY the document_id(s), NONE, or CLARIFY."
    )

    raw = generate_router_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        node_name="document_relevance_selector",
        include_history=False,
        patient_id=patient_id,
        chat_session_id=chat_session_id,
    )

    raw = (raw or "").strip()
    logger.info("document_relevance_selector: raw=%r", raw)

    if raw.upper() in ("NONE", "CLARIFY", ""):
        return []

    valid_ids = {e.document_id for e in catalog}
    selected = [part.strip() for part in raw.split(",") if part.strip() in valid_ids]
    logger.info("document_relevance_selector: selected=%s", selected)
    return selected


# ---- Retrieval: blob fetch + answer composition ----

async def get_document_summary(blob_summary_path: str) -> dict[str, Any]:
    """Fetch a document's full summary JSON from blob storage."""
    return await download_blob_json(blob_summary_path)


def _is_macro_question(question: str) -> bool:
    lowered = (question or "").lower()
    return any(phrase in lowered for phrase in (
        "how do my reports look", "overall", "summary of my",
        "how are my results", "general impression", "what do my documents",
    ))


CLINICAL_GROUNDING_SYSTEM = """\
You are a hospital assistant answering a patient's question using extracted medical document data.

Clinical grounding rules (MANDATORY — applies regardless of document type):
1. Transcribe dosages, measurements, and findings EXACTLY as written in the document data. \
Do not paraphrase numeric values.
2. If a field reads as illegible or ambiguous in the document data, output \
'[Incomplete/Illegible text in document]' for that item specifically.
3. Do NOT calculate dose modifications, alternate schedules, or derive values not \
explicitly present in the provided document data.
4. Keep the answer concise, clear, and in plain language the patient can understand.
5. If the document does not contain the requested information, say so directly.\
"""


async def answer_from_documents(
    question: str,
    selected_document_ids: list[str],
    catalog: list[CatalogEntry],
    *,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
    session_summary_cache: dict[str, dict] | None = None,
) -> str:
    """
    Fetch selected document summaries from blob storage and compose an answer
    via the HF chat model.

    Uses a per-session in-memory cache (session_summary_cache) to avoid
    redundant blob round-trips within one conversation.
    Fetched summaries are NOT persisted into LangGraph state.
    """
    from app.inference.llm import generate_text

    if not selected_document_ids:
        return ""

    catalog_map = {e.document_id: e for e in catalog}
    cache: dict[str, dict] = session_summary_cache if session_summary_cache is not None else {}
    is_macro = _is_macro_question(question)

    context_parts: list[str] = []
    for doc_id in selected_document_ids:
        entry = catalog_map.get(doc_id)
        if not entry:
            logger.warning("answer_from_documents: doc_id=%s not in catalog", doc_id)
            continue

        if doc_id not in cache:
            try:
                cache[doc_id] = await get_document_summary(entry.blob_summary_path)
            except FileNotFoundError:
                logger.error("answer_from_documents: blob missing for doc_id=%s", doc_id)
                continue
            except Exception as exc:
                logger.error("answer_from_documents: fetch failed doc_id=%s: %s", doc_id, exc)
                continue

        summary = cache[doc_id]
        header = f"Document ({entry.document_type}, date: {entry.clinical_date or 'unknown'}):"

        if is_macro:
            snippet = (
                f"{header}\n"
                f"Impression: {summary.get('overall_impression') or '[Not available]'}"
            )
        else:
            snippet = (
                f"{header}\n"
                f"Impression: {summary.get('overall_impression') or ''}\n"
                f"Findings: {json.dumps(summary.get('findings') or {}, ensure_ascii=False)}"
            )
        context_parts.append(snippet)

    if not context_parts:
        return "I could not retrieve the relevant document content at this time. Please try again shortly."

    context = "\n\n".join(context_parts)
    user_prompt = (
        f"Patient question: {question}\n\n"
        f"Relevant document data:\n{context}\n\n"
        "Answer the patient's question based solely on the document data above."
    )

    response = generate_text(
        system_prompt=CLINICAL_GROUNDING_SYSTEM,
        user_prompt=user_prompt,
        node_name="document_answer_composer",
        include_history=False,
        patient_id=patient_id,
        chat_session_id=chat_session_id,
    )
    return (response or "").strip()
