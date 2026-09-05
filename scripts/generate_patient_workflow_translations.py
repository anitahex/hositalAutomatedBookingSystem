"""Generate static patient workflow translations in JSON using the configured OpenAI model."""

from __future__ import annotations

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LANGUAGES = {
    "en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil", "kn": "Kannada",
    "mr": "Marathi", "bn": "Bengali", "gu": "Gujarati", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian", "pl": "Polish",
    "nl": "Dutch", "tr": "Turkish", "ar": "Arabic", "he": "Hebrew", "fa": "Persian",
    "sw": "Swahili", "el": "Greek", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
    "th": "Thai", "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay", "tl": "Filipino",
    "my": "Burmese", "km": "Khmer", "si": "Sinhala", "pa": "Punjabi", "ml": "Malayalam",
    "or": "Odia", "ur": "Urdu", "as": "Assamese", "mai": "Maithili", "kok": "Konkani",
    "ne": "Nepali", "sd": "Sindhi", "brx": "Bodo", "doi": "Dogri", "ks": "Kashmiri",
    "mni": "Manipuri", "sa": "Sanskrit", "sat": "Santali",
}

KEYS = {
    "department_booking_prompt": "Would you like to book an appointment with a {department} doctor? ({yes} / {no})",
    "booking_prompt": "Would you like me to find available appointment slots for you? ({yes} / {no})",
    "report_forward_prompt": "Should I forward your detailed clinical report to {doctor} before your appointment? This will include the symptoms, patterns, triggers, and recommendations we discussed. ({yes} / {no})",
    "appointment_confirmed": "Your appointment with {doctor} is confirmed for {date_time}. Reference ID: {reference}.",
    "report_sent": "Your clinical report has been sent to {doctor}.",
    "cancellation_prompt": "Would you like to cancel your appointment with {doctor} on {date_time}? ({yes} / {no})",
    "cancellation_confirmed": "Your appointment with {doctor} on {date_time} has been cancelled.",
    "reschedule_prompt": "Would you like to reschedule your appointment with {doctor}? ({yes} / {no})",
    "slot_error": "That appointment slot is no longer available. Please choose another slot.",
    "selection_error": "I could not understand that selection. Please choose one of the displayed options.",
}


def main() -> None:
    load_dotenv()
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    codes = list(LANGUAGES)[start:start + 8]
    model = os.getenv("OPENAI_TRANSLATION_MODEL") or os.getenv("OPENAI_SUMMARY_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o"
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = {
        "languages": {code: LANGUAGES[code] for code in codes},
        "messages": KEYS,
        "instructions": [
            "Translate every message naturally for patient-facing hospital appointment UI.",
            "Return JSON only: an object keyed by language code, then message key.",
            "Preserve every placeholder exactly: {department}, {yes}, {no}, {doctor}, {date_time}, {reference}.",
            "Do not add medical claims. Use a polite, concise register.",
            "Use native script where customary; preserve product names and IDs.",
        ],
    }
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a professional localization translator. Return only valid JSON."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        max_completion_tokens=6000,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""
    start_json = content.find("{")
    end_json = content.rfind("}")
    if start_json < 0 or end_json <= start_json:
        raise RuntimeError("translator did not return JSON")
    print(json.dumps(json.loads(content[start_json:end_json + 1]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
