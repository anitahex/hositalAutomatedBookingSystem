import base64
import hashlib
import hmac
import json
import os
import time


JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("HF_TOKEN") or "dev-only-change-me"
JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", str(60 * 60 * 24 * 7)))


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_access_token(*, patient_id: str, email: str) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": patient_id,
        "email": email,
        "iat": now,
        "exp": now + JWT_EXP_SECONDS,
    }

    signing_input = ".".join(
        [
            _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(
        JWT_SECRET.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def verify_access_token(token: str) -> dict | None:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".", 2)
    except ValueError:
        return None

    signing_input = f"{header_b64}.{payload_b64}"
    expected_signature = hmac.new(
        JWT_SECRET.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()

    try:
        supplied_signature = _b64url_decode(signature_b64)
    except Exception:
        return None

    if not hmac.compare_digest(expected_signature, supplied_signature):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None

    if payload.get("exp", 0) < int(time.time()):
        return None

    if not payload.get("sub"):
        return None

    return payload
