import json
import os
import time

from dotenv import load_dotenv
from openai import AzureOpenAI, AsyncAzureOpenAI

from app.services.llm_usage import record_llm_usage

load_dotenv()

# ---- Azure OpenAI config ----
AZURE_ENDPOINT = os.getenv("AZURE_CONV_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_API_KEY = os.getenv("AZURE_CONV_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_API_VERSION = os.getenv("AZURE_CONV_API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION", "2024-07-18")

CONV_DEPLOYMENT = os.getenv("AZURE_CONV_DEPLOYMENT", "gpt-4o")
ROUTER_DEPLOYMENT = os.getenv("AZURE_ROUTER_DEPLOYMENT", "gpt-4o")
SUMMARY_DEPLOYMENT = os.getenv("AZURE_SUMMARY_DEPLOYMENT", "gpt-4o")
VISION_DEPLOYMENT = os.getenv("AZURE_VISION_DEPLOYMENT", "gpt-4o")

MAX_TOKENS = int(os.getenv("AZURE_MAX_TOKENS", "1024"))
ROUTER_MAX_TOKENS = int(os.getenv("AZURE_ROUTER_MAX_TOKENS", "512"))
SUMMARY_MAX_TOKENS = int(os.getenv("AZURE_SUMMARY_MAX_TOKENS", "512"))
PROMPT_WINDOW_TURNS = int(os.getenv("AZURE_PROMPT_WINDOW_TURNS", "2"))
SYSTEM_PROMPT = os.getenv(
    "AZURE_SYSTEM_PROMPT",
    "You are a clinical AI assistant for a hospital triage and intake system. You are knowledgeable about medical symptoms, anatomy, and appropriate clinical referrals. Always prioritize patient safety. Provide clear, evidence-based guidance and always recommend professional medical evaluation when appropriate.",
)

# Aliases so any module that imports these names keeps working
HF_MAX_TOKENS = MAX_TOKENS
HF_ROUTER_MAX_TOKENS = ROUTER_MAX_TOKENS
HF_SUMMARY_MAX_TOKENS = SUMMARY_MAX_TOKENS
HF_PROMPT_WINDOW_TURNS = PROMPT_WINDOW_TURNS
HF_SYSTEM_PROMPT = SYSTEM_PROMPT

_TIMEOUT = float(os.getenv("AZURE_TIMEOUT_SECONDS", "120"))

_sync_client: AzureOpenAI | None = None
_async_client: AsyncAzureOpenAI | None = None
if AZURE_ENDPOINT and AZURE_API_KEY:
    _sync_client = AzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION,
        timeout=_TIMEOUT,
    )
    _async_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION,
        timeout=_TIMEOUT,
    )


def _trim_chat_history(chat_history: list[dict] | None, max_patient_turns: int | None = None) -> list[dict]:
    if not chat_history:
        return []
    if max_patient_turns is None:
        max_patient_turns = PROMPT_WINDOW_TURNS
    if max_patient_turns <= 0:
        return []
    kept = []
    patient_turns = 0
    for turn in reversed(chat_history):
        kept.append(turn)
        if str(turn.get("role") or "user").strip().lower() == "patient":
            patient_turns += 1
            if patient_turns >= max_patient_turns:
                break
    return list(reversed(kept))


def _chat_completion(
    client: AzureOpenAI,
    system_prompt: str,
    user_prompt: str,
    *,
    deployment: str,
    max_tokens: int,
    temperature: float,
    call_type: str,
    node_name: str,
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    include_history: bool = True,
    history_turns: int | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    if include_history:
        for turn in _trim_chat_history(chat_history, history_turns):
            role = str(turn.get("role") or "user").strip().lower()
            if role == "patient":
                role = "user"
            elif role not in {"system", "user", "assistant", "tool"}:
                role = "user"
            content = turn.get("content")
            if content is None:
                content = turn.get("text", "")
            messages.append({"role": role, "content": str(content)})
    if chat_summary and chat_summary.strip():
        messages.append({"role": "system", "content": "Conversation summary so far:\n" + chat_summary.strip()})
    messages.append({"role": "user", "content": user_prompt})

    print(f"--- [LLM INPUT PAYLOAD: {node_name.upper()}] ---")
    print(json.dumps({"model": deployment, "messages": messages}, ensure_ascii=False, indent=2))

    started_at = time.perf_counter()
    response = None
    content = ""
    status = "ERROR"
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        content = (content or "").strip()
        if not content:
            raise RuntimeError(f"Model {deployment} returned an empty response.")
        status = "SUCCESS"
        return content
    finally:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        record_llm_usage(
            model=deployment,
            call_type=call_type,
            prompt=f"{system_prompt}\n\n{user_prompt}",
            completion=content,
            response=response,
            node_name=node_name,
            session_id=chat_session_id,
            patient_id=patient_id,
            status=status,
            latency_ms=latency_ms,
        )


async def _achat_completion(
    client: AsyncAzureOpenAI,
    system_prompt: str,
    user_prompt: str,
    *,
    deployment: str,
    max_tokens: int,
    temperature: float,
    call_type: str,
    node_name: str,
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    include_history: bool = True,
    history_turns: int | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    if include_history:
        for turn in _trim_chat_history(chat_history, history_turns):
            role = str(turn.get("role") or "user").strip().lower()
            if role == "patient":
                role = "user"
            elif role not in {"system", "user", "assistant", "tool"}:
                role = "user"
            content = turn.get("content")
            if content is None:
                content = turn.get("text", "")
            messages.append({"role": role, "content": str(content)})
    if chat_summary and chat_summary.strip():
        messages.append({"role": "system", "content": "Conversation summary so far:\n" + chat_summary.strip()})
    messages.append({"role": "user", "content": user_prompt})

    print(f"--- [LLM INPUT PAYLOAD: {node_name.upper()}] ---")
    print(json.dumps({"model": deployment, "messages": messages}, ensure_ascii=False, indent=2))

    started_at = time.perf_counter()
    response = None
    content = ""
    status = "ERROR"
    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        content = (content or "").strip()
        if not content:
            raise RuntimeError(f"Model {deployment} returned an empty response.")
        status = "SUCCESS"
        return content
    finally:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        record_llm_usage(
            model=deployment,
            call_type=call_type,
            prompt=f"{system_prompt}\n\n{user_prompt}",
            completion=content,
            response=response,
            node_name=node_name,
            session_id=chat_session_id,
            patient_id=patient_id,
            status=status,
            latency_ms=latency_ms,
        )


def _normalize_completion_content(content) -> str:
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        ).strip()
    return str(content or "").strip()


def _build_multimodal_messages(system_prompt: str, user_parts: list[dict]) -> list[dict]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_parts},
    ]


def _multimodal_completion(
    client: AzureOpenAI,
    messages: list[dict],
    *,
    deployment: str,
    max_tokens: int,
    temperature: float,
    call_type: str,
    node_name: str,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    print(f"--- [LLM INPUT PAYLOAD: {node_name.upper()}] ---")
    print(json.dumps({"model": deployment, "messages": messages}, ensure_ascii=False, indent=2))

    started_at = time.perf_counter()
    response = None
    content = ""
    status = "ERROR"
    prompt_log = json.dumps(messages, ensure_ascii=False)
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
        content = _normalize_completion_content(response.choices[0].message.content)
        if not content:
            raise RuntimeError(f"Model {deployment} returned an empty response.")
        status = "SUCCESS"
        return content
    finally:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        record_llm_usage(
            model=deployment,
            call_type=call_type,
            prompt=prompt_log,
            completion=content,
            response=response,
            node_name=node_name,
            session_id=chat_session_id,
            patient_id=patient_id,
            status=status,
            latency_ms=latency_ms,
        )


async def _amultimodal_completion(
    client: AsyncAzureOpenAI,
    messages: list[dict],
    *,
    deployment: str,
    max_tokens: int,
    temperature: float,
    call_type: str,
    node_name: str,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    print(f"--- [LLM INPUT PAYLOAD: {node_name.upper()}] ---")
    print(json.dumps({"model": deployment, "messages": messages}, ensure_ascii=False, indent=2))

    started_at = time.perf_counter()
    response = None
    content = ""
    status = "ERROR"
    prompt_log = json.dumps(messages, ensure_ascii=False)
    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
        content = _normalize_completion_content(response.choices[0].message.content)
        if not content:
            raise RuntimeError(f"Model {deployment} returned an empty response.")
        status = "SUCCESS"
        return content
    finally:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        record_llm_usage(
            model=deployment,
            call_type=call_type,
            prompt=prompt_log,
            completion=content,
            response=response,
            node_name=node_name,
            session_id=chat_session_id,
            patient_id=patient_id,
            status=status,
            latency_ms=latency_ms,
        )


def generate_text(
    system_prompt: str,
    user_prompt: str,
    *,
    node_name: str = "general",
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    include_history: bool = True,
    history_turns: int | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    try:
        if not _sync_client:
            raise RuntimeError("Azure OpenAI client is not configured.")
        return _chat_completion(
            _sync_client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            deployment=CONV_DEPLOYMENT,
            max_tokens=MAX_TOKENS,
            temperature=0.1,
            call_type="generation",
            node_name=node_name,
            chat_history=chat_history,
            chat_summary=chat_summary,
            include_history=include_history,
            history_turns=history_turns,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
    except Exception as exc:
        print(f"LLM call failed for {CONV_DEPLOYMENT}: {exc}")
        return _local_fallback(system_prompt, user_prompt)


async def agenerate_text(
    system_prompt: str,
    user_prompt: str,
    *,
    node_name: str = "general",
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    include_history: bool = True,
    history_turns: int | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    try:
        if not _async_client:
            raise RuntimeError("Azure OpenAI async client is not configured.")
        return await _achat_completion(
            _async_client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            deployment=CONV_DEPLOYMENT,
            max_tokens=MAX_TOKENS,
            temperature=0.1,
            call_type="generation",
            node_name=node_name,
            chat_history=chat_history,
            chat_summary=chat_summary,
            include_history=include_history,
            history_turns=history_turns,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
    except Exception as exc:
        print(f"Async LLM call failed for {CONV_DEPLOYMENT}: {exc}")
        return _local_fallback(system_prompt, user_prompt)


async def astream_text(
    system_prompt: str,
    user_prompt: str,
    *,
    node_name: str = "stream",
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    include_history: bool = False,
    history_turns: int | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
):
    if not _async_client:
        raise RuntimeError("Azure OpenAI async client is not configured.")

    messages = [{"role": "system", "content": system_prompt}]
    if include_history and chat_history:
        for turn in _trim_chat_history(chat_history, history_turns):
            role = str(turn.get("role") or "user").strip().lower()
            if role == "patient":
                role = "user"
            elif role not in {"system", "user", "assistant", "tool"}:
                role = "user"
            content = turn.get("content") or turn.get("text", "")
            messages.append({"role": role, "content": str(content)})
    if chat_summary and chat_summary.strip():
        messages.append({"role": "system", "content": "Conversation summary:\n" + chat_summary.strip()})
    messages.append({"role": "user", "content": user_prompt})

    print(f"--- [LLM STREAM: {node_name.upper()}] ---")
    print(json.dumps({"model": CONV_DEPLOYMENT, "messages": messages}, ensure_ascii=False, indent=2))

    try:
        stream = await _async_client.chat.completions.create(
            model=CONV_DEPLOYMENT,
            messages=messages,
            max_completion_tokens=MAX_TOKENS,
            temperature=0.1,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
    except Exception as exc:
        print(f"astream_text failed for {CONV_DEPLOYMENT}, falling back to full response: {exc}")
        try:
            fallback = await _achat_completion(
                _async_client,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                deployment=CONV_DEPLOYMENT,
                max_tokens=MAX_TOKENS,
                temperature=0.1,
                call_type="stream_fallback",
                node_name=node_name,
                chat_history=chat_history,
                chat_summary=chat_summary,
                include_history=include_history,
                history_turns=history_turns,
                patient_id=patient_id,
                chat_session_id=chat_session_id,
            )
            yield fallback
        except Exception as exc2:
            print(f"astream_text fallback also failed: {exc2}")
            yield _local_fallback(system_prompt, user_prompt)


def generate_multimodal_text(
    system_prompt: str,
    user_parts: list[dict],
    *,
    node_name: str = "vision",
    max_tokens: int = MAX_TOKENS,
    temperature: float = 0.1,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    try:
        if not _sync_client:
            raise RuntimeError("Azure OpenAI client is not configured.")
        messages = _build_multimodal_messages(system_prompt, user_parts)
        return _multimodal_completion(
            _sync_client,
            messages,
            deployment=VISION_DEPLOYMENT,
            max_tokens=max_tokens,
            temperature=temperature,
            call_type="vision",
            node_name=node_name,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
    except Exception as exc:
        print(f"Vision LLM call failed for {VISION_DEPLOYMENT}: {exc}")
        return _local_fallback(system_prompt, json.dumps(user_parts, ensure_ascii=False))


async def agenerate_multimodal_text(
    system_prompt: str,
    user_parts: list[dict],
    *,
    node_name: str = "vision",
    max_tokens: int = MAX_TOKENS,
    temperature: float = 0.1,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    try:
        if not _async_client:
            raise RuntimeError("Azure OpenAI async client is not configured.")
        messages = _build_multimodal_messages(system_prompt, user_parts)
        return await _amultimodal_completion(
            _async_client,
            messages,
            deployment=VISION_DEPLOYMENT,
            max_tokens=max_tokens,
            temperature=temperature,
            call_type="vision",
            node_name=node_name,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
    except Exception as exc:
        print(f"Async vision LLM call failed for {VISION_DEPLOYMENT}: {exc}")
        return _local_fallback(system_prompt, json.dumps(user_parts, ensure_ascii=False))


def generate_router_text(
    system_prompt: str,
    user_prompt: str,
    *,
    node_name: str = "router",
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    include_history: bool = True,
    history_turns: int | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
    raise_on_error: bool = False,
) -> str:
    try:
        if not _sync_client:
            raise RuntimeError("Azure OpenAI client is not configured.")
        return _chat_completion(
            _sync_client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            deployment=ROUTER_DEPLOYMENT,
            max_tokens=ROUTER_MAX_TOKENS,
            temperature=0,
            call_type="router",
            node_name=node_name,
            chat_history=chat_history,
            chat_summary=chat_summary,
            include_history=include_history,
            history_turns=history_turns,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
    except Exception as exc:
        print(f"Router LLM call failed for {ROUTER_DEPLOYMENT}: {exc}")
        if raise_on_error:
            raise
        return _local_fallback(system_prompt, user_prompt)


async def agenerate_router_text(
    system_prompt: str,
    user_prompt: str,
    *,
    node_name: str = "router",
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    include_history: bool = True,
    history_turns: int | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
    raise_on_error: bool = False,
) -> str:
    try:
        if not _async_client:
            raise RuntimeError("Azure OpenAI async client is not configured.")
        return await _achat_completion(
            _async_client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            deployment=ROUTER_DEPLOYMENT,
            max_tokens=ROUTER_MAX_TOKENS,
            temperature=0,
            call_type="router",
            node_name=node_name,
            chat_history=chat_history,
            chat_summary=chat_summary,
            include_history=include_history,
            history_turns=history_turns,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
    except Exception as exc:
        print(f"Async router LLM call failed for {ROUTER_DEPLOYMENT}: {exc}")
        if raise_on_error:
            raise
        return _local_fallback(system_prompt, user_prompt)


def summarize_chat_history(
    prompt: str,
    *,
    node_name: str = "memory_compactor",
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    include_history: bool = True,
    history_turns: int | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    try:
        if not _sync_client:
            raise RuntimeError("Azure OpenAI client is not configured.")
        return _chat_completion(
            _sync_client,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            deployment=SUMMARY_DEPLOYMENT,
            max_tokens=SUMMARY_MAX_TOKENS,
            temperature=0,
            call_type="summary",
            node_name=node_name,
            chat_history=chat_history,
            chat_summary=chat_summary,
            include_history=include_history,
            history_turns=history_turns,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
    except Exception as exc:
        print(f"Summary LLM call failed for {SUMMARY_DEPLOYMENT}: {exc}")
        return chat_summary or ""


async def asummarize_chat_history(
    prompt: str,
    *,
    node_name: str = "memory_compactor",
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    include_history: bool = True,
    history_turns: int | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    try:
        if not _async_client:
            raise RuntimeError("Azure OpenAI async client is not configured.")
        return await _achat_completion(
            _async_client,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            deployment=SUMMARY_DEPLOYMENT,
            max_tokens=SUMMARY_MAX_TOKENS,
            temperature=0,
            call_type="summary",
            node_name=node_name,
            chat_history=chat_history,
            chat_summary=chat_summary,
            include_history=include_history,
            history_turns=history_turns,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
    except Exception as exc:
        print(f"Async summary LLM call failed for {SUMMARY_DEPLOYMENT}: {exc}")
        return chat_summary or ""


def _local_fallback(system_prompt: str, user_prompt: str) -> str:
    latest_message = user_prompt
    marker = "Latest message:"
    if marker in user_prompt:
        latest_message = user_prompt.split(marker, 1)[1].strip()
        if "\n" in latest_message:
            latest_message = latest_message.splitlines()[0].strip()
    latest_lowered = latest_message.lower()

    if "natural-language understanding layer" in system_prompt:
        if any(term in latest_lowered for term in ("my name", "my age", "my profile", "blood group", "health issues", "email", "address")):
            return json.dumps({"action": "profile_query", "profile_fields": ["name", "age"], "requested_department": None, "requested_doctor_name": None, "requested_date": None, "reason": "local profile fallback"})
        if any(term in latest_lowered for term in ("bomb", "explosive", "diwali cracker", "firecracker", "firework", "weapon")):
            return json.dumps({"action": "non_medical", "profile_fields": [], "requested_department": None, "requested_doctor_name": None, "requested_date": None, "reason": "local non-medical safety fallback"})
        if any(term in latest_lowered for term in ("upcoming booking", "upcoming appointment", "previous booking", "previous appointment", "my bookings", "my appointments")):
            return json.dumps({"action": "booking_lookup", "profile_fields": [], "requested_department": None, "requested_doctor_name": None, "requested_date": None, "reason": "local booking lookup fallback"})
        if "tomorrow" in latest_lowered:
            return json.dumps({"action": "direct_booking", "profile_fields": [], "requested_department": None, "requested_doctor_name": None, "requested_date": None, "reason": "local date booking fallback"})
        if any(term in latest_lowered for term in ("doctor", "appointment", "book", "department")):
            return json.dumps({"action": "direct_booking", "profile_fields": [], "requested_department": None, "requested_doctor_name": None, "requested_date": None, "reason": "local booking fallback"})
        if any(term in latest_lowered for term in ("pain", "symptom", "need help", "having", "ache", "fever", "swelling")):
            return json.dumps({"action": "symptom_or_care", "profile_fields": [], "requested_department": None, "requested_doctor_name": None, "requested_date": None, "reason": "local symptom fallback"})
        if "thank" in latest_lowered:
            return json.dumps({"action": "thanks_only", "profile_fields": [], "requested_department": None, "requested_doctor_name": None, "requested_date": None, "reason": "local thanks fallback"})
        return json.dumps({"action": "continue_current", "profile_fields": [], "requested_department": None, "requested_doctor_name": None, "requested_date": None, "reason": "local understanding fallback"})

    if "Master Supervisor for a hospital AI assistant" in system_prompt:
        return json.dumps({"user_action_summary": "Fallback supervisor routing", "next_agent": "continue_current", "update_active_intent": None, "extracted_facts": {}})

    if "Supervisor Router Agent" in system_prompt:
        return json.dumps({"next_agent": "continue_current", "intent": None, "reason": "router fallback"})

    if "Triage Router Agent" in system_prompt:
        return json.dumps({"intent": "unclear", "symptoms": [], "severity": "mild"})

    if "hospital intake assistant" in system_prompt:
        return json.dumps({"intent": "continue_intake", "has_enough_info": False, "next_question": "Could you tell me a little more about what you are feeling and when it started?", "collected_info": {}})

    if "compassionate medical assistant" in system_prompt:
        return json.dumps({"remedy_text": "Based on what you described, please rest, stay hydrated, and avoid anything that makes the symptoms worse. If symptoms are severe, worsening, or unusual for you, it is best to speak with a doctor promptly.", "follow_up_question": "Please try this and let me know how you feel. Are your symptoms improving, or are they still persisting or getting worse?"})

    if "interpreting a patient's reply after remedy advice" in system_prompt:
        return json.dumps({"patient_status": "unclear", "reason": "The language model was unavailable."})

    if "appointment booking assistant interpreting" in system_prompt:
        return json.dumps({"action": "unclear", "selected_value": None, "reason": "The language model was unavailable."})

    if "hospital department routing assistant" in system_prompt:
        return json.dumps({"department": None, "confidence": 0, "needs_clarification": True, "reason": "The language model was unavailable."})

    return "I am having trouble reaching the language model right now. Please try again shortly."
