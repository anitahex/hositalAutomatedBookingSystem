import json
import asyncio
import os
import time

from dotenv import load_dotenv

from app.services.llm_usage import record_llm_usage

try:
    from huggingface_hub import AsyncInferenceClient, InferenceClient
except ModuleNotFoundError:
    AsyncInferenceClient = None
    InferenceClient = None

from app.inference.vision import HF_VISION_MODEL

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen3.6-35B-A3B")
HF_ROUTER_MODEL = os.getenv("HF_ROUTER_MODEL", HF_MODEL)
HF_SUMMARY_MODEL = os.getenv("HF_SUMMARY_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
HF_TIMEOUT_SECONDS = float(os.getenv("HF_TIMEOUT_SECONDS", "30"))
HF_ROUTER_TIMEOUT_SECONDS = float(os.getenv("HF_ROUTER_TIMEOUT_SECONDS", "8"))
HF_SUMMARY_TIMEOUT_SECONDS = float(os.getenv("HF_SUMMARY_TIMEOUT_SECONDS", "12"))
HF_MAX_TOKENS = int(os.getenv("HF_MAX_TOKENS", "512"))
HF_ROUTER_MAX_TOKENS = int(os.getenv("HF_ROUTER_MAX_TOKENS", "180"))
HF_SUMMARY_MAX_TOKENS = int(os.getenv("HF_SUMMARY_MAX_TOKENS", "256"))
HF_HISTORY_TURNS = int(os.getenv("HF_HISTORY_TURNS", "4"))
HF_PROMPT_WINDOW_TURNS = int(os.getenv("HF_PROMPT_WINDOW_TURNS", "2"))
HF_SYSTEM_PROMPT = os.getenv(
    "HF_SYSTEM_PROMPT",
    "You are a careful hospital assistant. Follow the user instructions exactly.",
)

if HF_TOKEN and InferenceClient:
    llm = InferenceClient(
        model=HF_MODEL,
        token=HF_TOKEN,
        timeout=HF_TIMEOUT_SECONDS,
    )
    router_llm = InferenceClient(
        model=HF_ROUTER_MODEL,
        token=HF_TOKEN,
        timeout=HF_ROUTER_TIMEOUT_SECONDS,
    )
    summary_llm = InferenceClient(
        model=HF_SUMMARY_MODEL,
        token=HF_TOKEN,
        timeout=HF_SUMMARY_TIMEOUT_SECONDS,
    )
    async_llm = AsyncInferenceClient(
        model=HF_MODEL,
        token=HF_TOKEN,
        timeout=HF_TIMEOUT_SECONDS,
    ) if AsyncInferenceClient else None
    async_router_llm = AsyncInferenceClient(
        model=HF_ROUTER_MODEL,
        token=HF_TOKEN,
        timeout=HF_ROUTER_TIMEOUT_SECONDS,
    ) if AsyncInferenceClient else None
    async_summary_llm = AsyncInferenceClient(
        model=HF_SUMMARY_MODEL,
        token=HF_TOKEN,
        timeout=HF_SUMMARY_TIMEOUT_SECONDS,
    ) if AsyncInferenceClient else None
    vision_llm = InferenceClient(
        model=HF_VISION_MODEL,
        token=HF_TOKEN,
        timeout=HF_TIMEOUT_SECONDS,
    )
    async_vision_llm = AsyncInferenceClient(
        model=HF_VISION_MODEL,
        token=HF_TOKEN,
        timeout=HF_TIMEOUT_SECONDS,
    ) if AsyncInferenceClient else None
else:
    llm = None
    router_llm = None
    summary_llm = None
    async_llm = None
    async_router_llm = None
    async_summary_llm = None
    vision_llm = None
    async_vision_llm = None


def _trim_chat_history(chat_history: list[dict] | None, max_patient_turns: int | None = None) -> list[dict]:
    if not chat_history:
        return []

    if max_patient_turns is None:
        max_patient_turns = HF_PROMPT_WINDOW_TURNS
    if max_patient_turns <= 0:
        return []

    kept = []
    patient_turns = 0
    for turn in reversed(chat_history):
        kept.append(turn)
        role = str(turn.get("role") or "user").strip().lower()
        if role == "patient":
            patient_turns += 1
            if patient_turns >= max_patient_turns:
                break

    return list(reversed(kept))


def _chat_completion(
    client,
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int,
    temperature: float,
    model: str,
    call_type: str,
    node_name: str,
    chat_history: list[dict] | None = None,
    chat_summary: str | None = None,
    include_history: bool = True,
    history_turns: int | None = None,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    # 1. Block 1: 100% Static System Prompt (For Prefix Caching)
    messages = [{"role": "system", "content": system_prompt}]
    
    # 2. Block 2: Append Chat History
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
        messages.append(
            {
                "role": "system",
                "content": "Conversation summary so far:\n" + chat_summary.strip(),
            }
        )
        
    # 3. Block 3: Dynamic User Payload
    messages.append({"role": "user", "content": user_prompt})
    
    print(f"--- [LLM INPUT PAYLOAD: {node_name.upper()}] ---")
    print(json.dumps({"model": model, "messages": messages}, ensure_ascii=False, indent=2))

    started_at = time.perf_counter()
    response = None
    content = ""
    status = "ERROR"
    try:
        response = client.chat.completions.create(
            messages=messages,
            max_tokens=max_tokens,
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
            raise RuntimeError(f"Model {model} returned an empty response.")
        status = "SUCCESS"
        return content
    finally:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        
        # We record the full prompt string for the logs
        full_prompt_log = f"{system_prompt}\n\n{user_prompt}"
        
        record_llm_usage(
            model=model,
            call_type=call_type,
            prompt=full_prompt_log,
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


def _multimodal_completion(
    client,
    messages: list[dict],
    *,
    max_tokens: int,
    temperature: float,
    model: str,
    call_type: str,
    node_name: str,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    print(f"--- [LLM INPUT PAYLOAD: {node_name.upper()}] ---")
    print(json.dumps({"model": model, "messages": messages}, ensure_ascii=False, indent=2))

    started_at = time.perf_counter()
    response = None
    content = ""
    status = "ERROR"
    prompt_log = json.dumps(messages, ensure_ascii=False)
    try:
        response = client.chat.completions.create(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = _normalize_completion_content(response.choices[0].message.content)
        if not content:
            raise RuntimeError(f"Model {model} returned an empty response.")
        status = "SUCCESS"
        return content
    finally:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        record_llm_usage(
            model=model,
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
    client,
    messages: list[dict],
    *,
    max_tokens: int,
    temperature: float,
    model: str,
    call_type: str,
    node_name: str,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    print(f"--- [LLM INPUT PAYLOAD: {node_name.upper()}] ---")
    print(json.dumps({"model": model, "messages": messages}, ensure_ascii=False, indent=2))

    started_at = time.perf_counter()
    response = None
    content = ""
    status = "ERROR"
    prompt_log = json.dumps(messages, ensure_ascii=False)
    try:
        response = await client.chat.completions.create(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = _normalize_completion_content(response.choices[0].message.content)
        if not content:
            raise RuntimeError(f"Model {model} returned an empty response.")
        status = "SUCCESS"
        return content
    finally:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        record_llm_usage(
            model=model,
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


def _build_multimodal_messages(system_prompt: str, user_parts: list[dict]) -> list[dict]:
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": user_parts})
    return messages


def _format_image_message(image_data_url: str) -> dict:
    return {"type": "image_url", "image_url": {"url": image_data_url}}


async def _achat_completion(
    client,
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int,
    temperature: float,
    model: str,
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
    print(json.dumps({"model": model, "messages": messages}, ensure_ascii=False, indent=2))

    started_at = time.perf_counter()
    response = None
    content = ""
    status = "ERROR"
    try:
        response = await client.chat.completions.create(
            messages=messages,
            max_tokens=max_tokens,
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
            raise RuntimeError(f"Model {model} returned an empty response.")
        status = "SUCCESS"
        return content
    finally:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        full_prompt_log = f"{system_prompt}\n\n{user_prompt}"
        record_llm_usage(
            model=model,
            call_type=call_type,
            prompt=full_prompt_log,
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
        if not llm:
            raise RuntimeError("Hugging Face LLM client is not configured.")
        content = _chat_completion(
            llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=HF_MAX_TOKENS,
            temperature=0.1,
            model=HF_MODEL,
            call_type="generation",
            node_name=node_name,
            chat_history=chat_history,
            chat_summary=chat_summary,
            include_history=include_history,
            history_turns=history_turns,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
        return content
    except Exception as exc:
        print(f"LLM call failed for {HF_MODEL}: {exc}")
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
        if not async_llm:
            raise RuntimeError("Async Hugging Face LLM client is not configured.")
        return await _achat_completion(
            async_llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=HF_MAX_TOKENS,
            temperature=0.1,
            model=HF_MODEL,
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
        print(f"Async LLM call failed for {HF_MODEL}: {exc}")
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
    """
    Async generator — yields string tokens from HF with stream=True.
    Uses the main async_llm client (same model as agenerate_text).
    Falls back to yielding the full response in one chunk if streaming fails.
    """
    if not async_llm:
        raise RuntimeError("Async HF LLM client not configured.")

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
    print(json.dumps({"model": HF_MODEL, "messages": messages}, ensure_ascii=False, indent=2))

    try:
        stream = await async_llm.chat.completions.create(
            messages=messages,
            max_tokens=HF_MAX_TOKENS,
            temperature=0.1,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
    except Exception as exc:
        print(f"astream_text failed for {HF_MODEL}, falling back to full response: {exc}")
        # Fall back: yield the full response as one token so the caller still works
        try:
            fallback = await _achat_completion(
                async_llm,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=HF_MAX_TOKENS,
                temperature=0.1,
                model=HF_MODEL,
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
    max_tokens: int = HF_MAX_TOKENS,
    temperature: float = 0.1,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    try:
        if not vision_llm:
            raise RuntimeError("Hugging Face vision client is not configured.")
        messages = _build_multimodal_messages(system_prompt, user_parts)
        return _multimodal_completion(
            vision_llm,
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            model=HF_VISION_MODEL,
            call_type="vision",
            node_name=node_name,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
    except Exception as exc:
        print(f"Vision LLM call failed for {HF_VISION_MODEL}: {exc}")
        return _local_fallback(system_prompt, json.dumps(user_parts, ensure_ascii=False))


async def agenerate_multimodal_text(
    system_prompt: str,
    user_parts: list[dict],
    *,
    node_name: str = "vision",
    max_tokens: int = HF_MAX_TOKENS,
    temperature: float = 0.1,
    patient_id: str | None = None,
    chat_session_id: str | None = None,
) -> str:
    try:
        if not async_vision_llm:
            raise RuntimeError("Async Hugging Face vision client is not configured.")
        messages = _build_multimodal_messages(system_prompt, user_parts)
        return await _amultimodal_completion(
            async_vision_llm,
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            model=HF_VISION_MODEL,
            call_type="vision",
            node_name=node_name,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
    except Exception as exc:
        print(f"Async vision LLM call failed for {HF_VISION_MODEL}: {exc}")
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
        if not router_llm:
            raise RuntimeError("Hugging Face router LLM client is not configured.")
        content = _chat_completion(
            router_llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=HF_ROUTER_MAX_TOKENS,
            temperature=0,
            model=HF_ROUTER_MODEL,
            call_type="router",
            node_name=node_name,
            chat_history=chat_history,
            chat_summary=chat_summary,
            include_history=include_history,
            history_turns=history_turns,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
        return content
    except Exception as exc:
        print(f"Router LLM call failed for {HF_ROUTER_MODEL}: {exc}")
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
        if not async_router_llm:
            raise RuntimeError("Async Hugging Face router client is not configured.")
        return await _achat_completion(
            async_router_llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=HF_ROUTER_MAX_TOKENS,
            temperature=0,
            model=HF_ROUTER_MODEL,
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
        print(f"Async router LLM call failed for {HF_ROUTER_MODEL}: {exc}")
        if raise_on_error:
            raise
        return _local_fallback(system_prompt, user_prompt)


def summarize_chat_history(
    prompt: str, # Keeping this as a single string since it's just a summary task
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
        if not summary_llm:
            raise RuntimeError("Hugging Face summary LLM client is not configured.")
        
        # The summary prompt can remain a single user prompt since it runs infrequently
        content = _chat_completion(
            summary_llm,
            system_prompt=HF_SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=HF_SUMMARY_MAX_TOKENS,
            temperature=0,
            model=HF_SUMMARY_MODEL,
            call_type="summary",
            node_name=node_name,
            chat_history=chat_history,
            chat_summary=chat_summary,
            include_history=include_history,
            history_turns=history_turns,
            patient_id=patient_id,
            chat_session_id=chat_session_id,
        )
        return content
    except Exception as exc:
        print(f"Summary LLM call failed for {HF_SUMMARY_MODEL}: {exc}")
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
        if not async_summary_llm:
            raise RuntimeError("Async Hugging Face summary client is not configured.")
        return await _achat_completion(
            async_summary_llm,
            system_prompt=HF_SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=HF_SUMMARY_MAX_TOKENS,
            temperature=0,
            model=HF_SUMMARY_MODEL,
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
        print(f"Async summary LLM call failed for {HF_SUMMARY_MODEL}: {exc}")
        return chat_summary or ""


def _local_fallback(system_prompt: str, user_prompt: str) -> str:
    lowered = user_prompt.lower()
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
        return json.dumps(
            {
                "user_action_summary": "Fallback supervisor routing",
                "next_agent": "continue_current",
                "update_active_intent": None,
                "extracted_facts": {},
            }
        )

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
