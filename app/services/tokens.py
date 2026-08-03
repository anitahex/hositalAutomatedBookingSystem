import base64
import hashlib
import hmac
import json
import os
import time


JWT_SECRET = os.getenv("JWT_SECRET") or "dev-only-change-me"
JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", str(60 * 60 * 24 * 7)))
LEGACY_JWT_SECRETS = [
    secret
    for secret in {
        os.getenv("HF_TOKEN"),
        "dev-only-change-me",
    }
    if secret
]


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_access_token(
    *,
    patient_id: str | None = None,
    subject: str | None = None,
    email: str,
    role: str = "patient",
) -> str:
    token_subject = subject or patient_id
    if not token_subject:
        raise ValueError("A token subject is required.")

    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": token_subject,
        "email": email,
        "role": role,
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
    try:
        supplied_signature = _b64url_decode(signature_b64)
    except Exception:
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None

    if payload.get("exp", 0) < int(time.time()):
        return None

    if not payload.get("sub"):
        return None

    candidate_secrets = [JWT_SECRET, *LEGACY_JWT_SECRETS]
    for secret in candidate_secrets:
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if hmac.compare_digest(expected_signature, supplied_signature):
            return payload

    return None
