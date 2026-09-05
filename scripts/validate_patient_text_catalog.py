"""LLM-judge audit for patient-facing localization coverage.

Usage:
    python scripts/validate_patient_text_catalog.py

The script reads the OpenAI key through the normal environment configuration,
never prints it, and reports only aggregate validation results.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from openai import OpenAI

from app.services import language, patient_text


MESSAGE_KEYS = (
    "booking_prompt",
    "department_booking_prompt",
    "report_forward_prompt",
    "appointment_confirmed",
    "report_sent",
    "cancellation_prompt",
    "cancellation_confirmed",
    "reschedule_prompt",
    "slot_error",
    "selection_error",
)


def _render(code: str, key: str) -> str:
    values = {
        "department": "Cardiology",
        "doctor": "Dr. A",
        "date_time": "10 June 2026, 10:00 AM",
        "reference": "REF-123",
    }
    if key not in patient_text._MESSAGES:
        return "[MISSING_CATALOG_ENTRY]"
    return patient_text.patient_message({"active_language": code}, key, **values)


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text or "", flags=re.DOTALL)
    if not match:
        raise ValueError("judge did not return JSON")
    return json.loads(match.group(0))


def _judge_batch(client: OpenAI, model: str, batch: list[dict]) -> list[dict]:
    prompt = {
        "task": "Evaluate patient-facing healthcare UI translations. Do not rewrite them.",
        "criteria": [
            "The text is in the requested language, not English fallback.",
            "The meaning and user action are preserved.",
            "Doctor and department placeholders are preserved.",
            "The tone is natural and respectful.",
            "No unsafe medical claim was added.",
        ],
        "output_schema": {
            "results": [
                {"language": "code", "score": "0-100", "passed": "boolean", "issues": ["short issue"]}
            ]
        },
        "languages": batch,
    }
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a strict multilingual localization QA judge. Return only valid JSON matching the requested schema.",
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        max_completion_tokens=3000,
    )
    return _parse_json(response.choices[0].message.content).get("results") or []


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("LLM judge unavailable: OPENAI_API_KEY is not configured")
        return 2

    model = os.getenv("OPENAI_SUMMARY_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o"
    client = OpenAI(api_key=api_key)
    codes = list(language.SUPPORTED_LANGUAGES)
    records = []
    for code in codes:
        records.append({
            "language": code,
            "name": language.SUPPORTED_LANGUAGES[code],
            "review_status": patient_text.CATALOG_REVIEW_STATUS.get(code, "unknown"),
            "messages": {key: _render(code, key) for key in MESSAGE_KEYS},
        })

    judged: list[dict] = []
    for start in range(0, len(records), 8):
        judged.extend(_judge_batch(client, model, records[start:start + 8]))

    by_code = {str(item.get("language")): item for item in judged if item.get("language")}
    passed = sum(bool(item.get("passed")) for item in judged)
    failed = len(codes) - passed
    print(f"LLM judge model: {model}")
    print(f"Languages evaluated: {len(codes)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("language,status,score,issues")
    for code in codes:
        item = by_code.get(code, {})
        issues = "; ".join(str(issue) for issue in (item.get("issues") or []))
        print(f"{code},{'PASS' if item.get('passed') else 'FAIL'},{item.get('score', 0)},{issues[:240]}")

    issue_counts = Counter(
        key
        for record in records
        for key, value in record["messages"].items()
        if value == "[MISSING_CATALOG_ENTRY]"
    )
    if issue_counts:
        print("missing_catalog_entries=" + ",".join(f"{key}:{count}" for key, count in issue_counts.items()))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
