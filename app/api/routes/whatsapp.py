from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import urllib.parse
import urllib.request
import urllib.error
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.api.routes.chat import _run_chat_with_usage
from app.services.users import get_user_profile_by_mobile


router = APIRouter()
logger = logging.getLogger(__name__)

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
VALIDATE_TWILIO_WEBHOOK = os.getenv("VALIDATE_TWILIO_WEBHOOK", "true").lower() in {
    "1", "true", "yes", "on"
}


def _twiml(message: str) -> Response:
    """Escapes string characters and constructs a standard TwiML XML response."""
    escaped = (
        str(message or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return Response(
        content=f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escaped}</Message></Response>',
        media_type="application/xml",
    )


def _valid_twilio_signature(url: str, params: dict[str, str], signature: str | None) -> bool:
    """Validates that incoming webhook requests are genuinely from Twilio."""
    if not TWILIO_AUTH_TOKEN or not signature:
        return False
    payload = url + "".join(key + params[key] for key in sorted(params))
    expected = hmac.new(TWILIO_AUTH_TOKEN.encode(), payload.encode(), hashlib.sha1).digest()
    return hmac.compare_digest(base64.b64encode(expected).decode(), signature)


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    params = {str(key): str(value) for key, value in form.items()}

    # 1. Validate incoming Twilio webhook signature
    if VALIDATE_TWILIO_WEBHOOK:
        if PUBLIC_BASE_URL:
            public_url = f"{PUBLIC_BASE_URL}{request.url.path}"
        else:
            forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            forwarded_host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
            public_url = f"{forwarded_proto}://{forwarded_host}{request.url.path}"
        if not _valid_twilio_signature(
            public_url,
            params,
            request.headers.get("x-twilio-signature"),
        ):
            return Response(status_code=403, content="Invalid Twilio signature")

    sender = params.get("From", "")
    body = params.get("Body", "").strip()

    # 2. Check for empty inbound body
    if not body:
        return _twiml("Please send a message so I can help with your appointment.")

    # 3. Resolve user profile by WhatsApp phone number
    patient = get_user_profile_by_mobile(sender)
    if not patient:
        return _twiml(
            "I couldn't find a hospital portal account for this WhatsApp number. "
            "Please register on the hospital portal using the same mobile number, then message me again."
        )

    # 4. Generate persistent session ID per patient
    session_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"hospital-whatsapp:{patient['patient_id']}"))

    try:
        # 5. Run AI agent synchronously in the webhook handler
        response_text, _, _ = await _run_chat_with_usage(
            {"message": body, "session_id": session_id, "state": {"session_id": session_id}},
            patient,
        )
        # 6. Send reply back directly in TwiML XML payload
        return _twiml(response_text)
    except Exception:
        logger.exception("WhatsApp AI processing failed for patient %s", patient.get("patient_id"))
        return _twiml("I am sorry, but I encountered an error while processing your request. Please try again.")