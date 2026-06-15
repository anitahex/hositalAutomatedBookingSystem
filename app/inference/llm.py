import json
import os
import time

from dotenv import load_dotenv

from app.services.llm_usage import record_llm_usage

try:
    from huggingface_hub import InferenceClient
except ModuleNotFoundError:
    InferenceClient = None

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
else:
    llm = None
    router_llm = None
    summary_llm = None


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
