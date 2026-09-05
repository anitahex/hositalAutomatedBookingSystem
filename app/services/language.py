"""Language identification and conversation-language state helpers.

This is intentionally deterministic and local: language control must not depend
on a second LLM call, and detector failures must never block a chat turn.
"""

from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil",
    "kn": "Kannada", "mr": "Marathi", "bn": "Bengali", "gu": "Gujarati",
    # Validated global and Asian expansion set.
    "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
    "pt": "Portuguese", "ru": "Russian", "pl": "Polish", "nl": "Dutch",
    "tr": "Turkish", "ar": "Arabic", "he": "Hebrew", "fa": "Persian",
    "sw": "Swahili", "el": "Greek", "zh": "Chinese", "ja": "Japanese",
    "ko": "Korean", "th": "Thai", "vi": "Vietnamese", "id": "Indonesian",
    "ms": "Malay", "tl": "Filipino", "my": "Burmese", "km": "Khmer",
    "si": "Sinhala",
    # Reserved for easy Wave 2-4 expansion.
    "pa": "Punjabi", "ml": "Malayalam", "or": "Odia", "ur": "Urdu",
    "as": "Assamese", "mai": "Maithili", "kok": "Konkani", "ne": "Nepali",
    "sd": "Sindhi", "brx": "Bodo", "doi": "Dogri", "ks": "Kashmiri",
    "mni": "Manipuri", "sa": "Sanskrit", "sat": "Santali",
}
WAVE_1 = frozenset({"en", "hi", "te", "ta", "kn", "mr", "bn", "gu"})

FASTTEXT_MIN_CONFIDENCE = float(os.getenv("LANGUAGE_ID_MIN_CONFIDENCE", "0.55"))
FASTTEXT_MODEL_PATH = Path(os.getenv(
    "LANGUAGE_ID_MODEL_PATH",
    str(Path(__file__).resolve().parents[2] / "models" / "lid.176.bin"),
))


@lru_cache(maxsize=1)
def _fasttext_model():
    try:
        import fasttext
        if not FASTTEXT_MODEL_PATH.exists():
            logger.warning("language_id: fastText model not found at %s; using script fallback", FASTTEXT_MODEL_PATH)
            return None
        return fasttext.load_model(str(FASTTEXT_MODEL_PATH))
    except Exception as exc:
        logger.warning("language_id: fastText unavailable; using script fallback: %s", exc)
        return None


def _detect_with_fasttext(text: str) -> tuple[str | None, float] | None:
    model = _fasttext_model()
    if model is None:
        return None
    try:
        labels, probabilities = model.predict(text.replace("\n", " "), k=1)
        if not labels or not probabilities:
            return None
        language = normalize_language(labels[0].removeprefix("__label__"))
        confidence = float(probabilities[0])
        if language and confidence >= FASTTEXT_MIN_CONFIDENCE:
            return language, confidence
    except Exception as exc:
        logger.warning("language_id: fastText prediction failed; using script fallback: %s", exc)
    return None

_SCRIPT_RANGES = {
    "te": (0x0C00, 0x0C7F), "ta": (0x0B80, 0x0BFF), "kn": (0x0C80, 0x0CFF),
    "bn": (0x0980, 0x09FF), "gu": (0x0A80, 0x0AFF),
}
_DEVANAGARI = (0x0900, 0x097F)
_EXPLICIT_PATTERNS = (
    ("te", r"(?:switch|reply|respond|answer|speak|talk).{0,20}(?:telugu)|తెలుగులో\s*(?:సమాధానం|మాట్లాడ)|తెలుగు\s*(?:లో|భాష)"),
    ("hi", r"(?:switch|reply|respond|answer|speak|talk).{0,20}(?:hindi)|हिंदी\s*में\s*(?:जवाब|उत्तर|बात)|हिन्दी\s*में"),
    ("ta", r"(?:switch|reply|respond|answer|speak|talk).{0,20}(?:tamil)|தமிழில்\s*(?:பதில்|பேச)"),
    ("kn", r"(?:switch|reply|respond|answer|speak|talk).{0,20}(?:kannada)|ಕನ್ನಡದಲ್ಲಿ\s*(?:ಉತ್ತರ|ಮಾತನಾಡ)"),
    ("mr", r"(?:switch|reply|respond|answer|speak|talk).{0,20}(?:marathi)|मराठीत\s*(?:उत्तर|बोला)"),
    ("bn", r"(?:switch|reply|respond|answer|speak|talk).{0,20}(?:bengali)|বাংলায়\s*(?:উত্তর|বলুন)"),
    ("gu", r"(?:switch|reply|respond|answer|speak|talk).{0,20}(?:gujarati)|ગુજરાતીમાં\s*(?:જવાબ|બોલ)"),
    ("en", r"(?:switch|reply|respond|answer|speak|talk).{0,20}english|in\s+english|અંગ્રેજીમાં|अंग्रेज़ी में"),
)
_AMBIGUOUS = frozenset({"ok", "okay", "yes", "no", "thanks", "thank you", "fine", "haan", "han", "theek hai", "ठीक है", "हाँ", "नहीं"})
_MARATHI_HINTS = ("मला", "आहे", "झाला", "झाली", "काय", "माझे", "पासून")


_ROMANIZED_HINDI_HINTS = frozenset({
    "mujhe", "mujh", "aapko", "tumhe", "pet", "sar", "dard", "bukhar",
    "gala", "khansi", "seene", "se", "mai", "mein", "hai", "ho", "raha",
    "rahi", "hua", "bahut", "abhi", "kal", "subah",
})


def normalize_language(value: str | None) -> str | None:
    value = (value or "").strip().lower().replace("_", "-")
    value = value.split("-", 1)[0]
    return value if value in SUPPORTED_LANGUAGES else None


def is_ambiguous_short_message(text: str | None) -> bool:
    normalized = " ".join((text or "").strip().lower().split())
    return normalized in _AMBIGUOUS or len(normalized.split()) <= 1 and normalized.isascii() and len(normalized) <= 5


def detect_language(text: str | None) -> tuple[str | None, float]:
    text = (text or "").strip()
    if not text or is_ambiguous_short_message(text):
        return None, 0.0
    fasttext_result = _detect_with_fasttext(text)
    if fasttext_result:
        romanized_tokens = set(re.findall(r"[a-z]+", text.lower()))
        if fasttext_result[0] == "en" and len(romanized_tokens & _ROMANIZED_HINDI_HINTS) >= 3:
            return "hi", max(0.80, min(0.90, fasttext_result[1]))
        return fasttext_result

    romanized_tokens = set(re.findall(r"[a-z]+", text.lower()))
    if len(romanized_tokens & _ROMANIZED_HINDI_HINTS) >= 3:
        return "hi", 0.84

    # Fallback for environments without the model and low-confidence output.
    for language, start_end in _SCRIPT_RANGES.items():
        count = sum(start_end[0] <= ord(ch) <= start_end[1] for ch in text)
        if count >= 2:
            return language, min(0.99, 0.78 + count / max(len(text), 1) * 0.2)
    devanagari = sum(_DEVANAGARI[0] <= ord(ch) <= _DEVANAGARI[1] for ch in text)
    if devanagari >= 2:
        language = "mr" if any(hint in text for hint in _MARATHI_HINTS) else "hi"
        return language, min(0.96, 0.78 + devanagari / max(len(text), 1) * 0.2)
    latin = sum(ch.isascii() and ch.isalpha() for ch in text)
    if latin >= 3:
        return "en", min(0.95, 0.70 + latin / max(len(text), 1) * 0.2)
    return None, 0.0


def explicit_language_switch(text: str | None) -> str | None:
    for language, pattern in _EXPLICIT_PATTERNS:
        if re.search(pattern, text or "", flags=re.IGNORECASE | re.DOTALL):
            return language
    # Keep switch handling extensible without duplicating one regex per language.
    switch = r"(?:switch|reply|respond|answer|speak|talk).{0,30}(?:to|in|using)?\s*"
    for language, name in SUPPORTED_LANGUAGES.items():
        if re.search(switch + re.escape(name), text or "", flags=re.IGNORECASE | re.DOTALL):
            return language
    return None


def language_name(code: str | None) -> str:
    return SUPPORTED_LANGUAGES.get(normalize_language(code) or "en", "English")


def switch_confirmation(language: str) -> str:
    messages = {
        "en": "Okay. I will respond in English from now on.",
        "hi": "ठीक है। अब से मैं हिंदी में जवाब दूंगा।",
        "te": "సరే. ఇకపై నేను తెలుగులో స్పందిస్తాను.",
        "ta": "சரி. இனிமேல் நான் தமிழில் பதிலளிப்பேன்.",
        "kn": "ಸರಿ. ಇನ್ನು ಮುಂದೆ ನಾನು ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸುತ್ತೇನೆ.",
        "mr": "ठीक आहे. आता मी मराठीत उत्तर देईन.",
        "bn": "ঠিক আছে। এখন থেকে আমি বাংলায় উত্তর দেব।",
        "gu": "ઠીક છે. હવે પછી હું ગુજરાતીમાં જવાબ આપીશ.",
    }
    return messages.get(language, messages["en"])


def apply_language_turn(state: dict, text: str) -> dict:
    """Return state updates for one turn; never raises on detector problems."""
    profile = state.get("patient_profile") or {}
    preferred = normalize_language(state.get("preferred_language") or profile.get("preferred_language")) or "en"
    current = normalize_language(state.get("active_language"))
    explicit = explicit_language_switch(text)
    detected, confidence = detect_language(text)
    updates = {"preferred_language": preferred, "detected_language": detected, "language_confidence": confidence}
    if explicit:
        updates.update({"active_language": explicit, "language_switch_candidate": None, "language_switch_count": 0,
                        "language_changed": explicit != current, "language_control_response": switch_confirmation(explicit)})
        return updates
    if not current:
        updates["active_language"] = detected or preferred or "en"
        updates["language_changed"] = bool(detected)
        return updates
    # The first meaningful patient message establishes the conversation
    # language immediately. The two-turn confirmation rule applies only when
    # changing an already-established conversation language.
    history = state.get("conversation_history") or state.get("messages") or []
    has_user_turn = any(isinstance(item, dict) and item.get("role") == "user" for item in history)
    if not has_user_turn and detected and detected != current and confidence >= 0.78:
        updates.update({"active_language": detected, "language_changed": True,
                        "language_switch_candidate": None, "language_switch_count": 0})
        logger.info("language_turn initial_language=%s confidence=%.2f active_language=%s language_changed=true",
                    detected, confidence, detected)
        return updates
    updates["active_language"] = current
    updates["language_changed"] = False
    if detected and detected != current and confidence >= 0.78:
        candidate = normalize_language(state.get("language_switch_candidate"))
        count = int(state.get("language_switch_count") or 0) + 1 if candidate == detected else 1
        updates.update({"language_switch_candidate": detected, "language_switch_count": count})
        if count >= 2:
            updates.update({"active_language": detected, "language_changed": True, "language_switch_candidate": None, "language_switch_count": 0})
    else:
        updates.update({"language_switch_candidate": None, "language_switch_count": 0})
    logger.info("language_turn detected_language=%s confidence=%.2f active_language=%s language_changed=%s", detected, confidence, updates["active_language"], updates["language_changed"])
    return updates


def language_prompt_context(state: dict) -> str:
    return f"""

CURRENT ACTIVE LANGUAGE: {normalize_language(state.get('active_language')) or 'en'}
PATIENT PREFERRED LANGUAGE: {normalize_language(state.get('preferred_language')) or 'en'}

You are a multilingual healthcare assistant.
Respond naturally in the active language. Infer the patient's language from
the latest message as well, including Roman-script and code-mixed language
such as "mujhe pet mein dard hai" or "naaku fever undi". If the latest
message is a clear, meaningful signal for another language, respond in that
language even when the detector metadata is uncertain. For ambiguous or
short acknowledgements such as ok, yes, no, thanks, haan, or theek hai,
keep the current active language and do not switch.
Do not unnecessarily mix languages. Preserve clinical meaning and precise
medical terminology. Do not incorrectly translate medication names, dosages,
units, dates, times, laboratory values, or numbers. Do not change clinical
reasoning or safety behavior based on language. Do not invent medical
information because the patient uses a regional language.
""".strip()
