import json
import os

from dotenv import load_dotenv

try:
    from huggingface_hub import InferenceClient
except ModuleNotFoundError:
    InferenceClient = None

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen3.6-35B-A3B")
HF_ROUTER_MODEL = os.getenv("HF_ROUTER_MODEL", HF_MODEL)
HF_TIMEOUT_SECONDS = float(os.getenv("HF_TIMEOUT_SECONDS", "30"))
HF_ROUTER_TIMEOUT_SECONDS = float(os.getenv("HF_ROUTER_TIMEOUT_SECONDS", "8"))
HF_MAX_TOKENS = int(os.getenv("HF_MAX_TOKENS", "512"))
HF_ROUTER_MAX_TOKENS = int(os.getenv("HF_ROUTER_MAX_TOKENS", "180"))

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
else:
    llm = None
    router_llm = None


def _chat_completion(client, prompt: str, *, max_tokens: int, temperature: float) -> str:
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    content = response.choices[0].message.content
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )

    return (content or "").strip()


def generate_text(prompt: str) -> str:
    try:
        if not llm:
            raise RuntimeError("Hugging Face LLM client is not configured.")
        content = _chat_completion(
            llm,
            prompt,
            max_tokens=HF_MAX_TOKENS,
            temperature=0.1,
        )
        if not content:
            raise RuntimeError(f"Model {HF_MODEL} returned an empty response.")
        return content
    except Exception as exc:
        print(f"LLM call failed for {HF_MODEL}: {exc}")
        return _local_fallback(prompt)


def generate_router_text(prompt: str) -> str:
    try:
        if not router_llm:
            raise RuntimeError("Hugging Face router LLM client is not configured.")
        content = _chat_completion(
            router_llm,
            prompt,
            max_tokens=HF_ROUTER_MAX_TOKENS,
            temperature=0,
        )
        if not content:
            raise RuntimeError(f"Router model {HF_ROUTER_MODEL} returned empty response.")
        return content
    except Exception as exc:
        print(f"Router LLM call failed for {HF_ROUTER_MODEL}: {exc}")
        return _local_fallback(prompt)


def _local_fallback(prompt: str) -> str:
    if "Supervisor Router Agent" in prompt:
        return json.dumps(
            {
                "next_agent": "continue_current",
                "intent": None,
                "reason": "router fallback",
            }
        )

    if "Triage Router Agent" in prompt:
        return json.dumps(
            {
                "intent": "unclear",
                "symptoms": [],
                "severity": "mild",
            }
        )

    if "hospital intake assistant" in prompt:
        return json.dumps(
            {
                "intent": "continue_intake",
                "has_enough_info": False,
                "next_question": (
                    "Could you tell me a little more about what you are feeling and when it started?"
                ),
                "collected_info": _structured_info(prompt),
            }
        )

    if "compassionate medical assistant" in prompt:
        return json.dumps(
            {
                "remedy_text": (
                    "Based on what you described, please rest, stay hydrated, and avoid anything "
                    "that makes the symptoms worse. If symptoms are severe, worsening, or unusual "
                    "for you, it is best to speak with a doctor promptly."
                ),
                "follow_up_question": (
                    "Please try this and let me know how you feel. Are your symptoms improving, "
                    "or are they still persisting or getting worse?"
                ),
            }
        )

    if "interpreting a patient's reply after remedy advice" in prompt:
        return json.dumps(
            {
                "patient_status": "unclear",
                "reason": "The language model was unavailable.",
            }
        )

    if "appointment booking assistant interpreting" in prompt:
        return json.dumps(
            {
                "action": "unclear",
                "selected_value": None,
                "reason": "The language model was unavailable.",
            }
        )

    if "hospital department routing assistant" in prompt:
        return json.dumps(
            {
                "department": None,
                "confidence": 0,
                "needs_clarification": True,
                "reason": "The language model was unavailable.",
            }
        )

    return "I am having trouble reaching the language model right now. Please try again shortly."


def _structured_info(prompt: str) -> dict:
    marker = "Structured info collected so far:"
    end_marker = "Questions already asked:"
    if marker not in prompt or end_marker not in prompt:
        return {}

    raw_json = prompt.split(marker, 1)[1].split(end_marker, 1)[0].strip()
    try:
        value = json.loads(raw_json)
    except json.JSONDecodeError:
        return {}

    return value if isinstance(value, dict) else {}
