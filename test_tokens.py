import hashlib
import hmac
import json

import pytest

from app.db.connection import connect_db
from app.services import tokens as tokens_module
from app.services.tokens import create_access_token, verify_access_token


def _skip_if_no_database():
    # create_access_token now issues a real jti (FULL_SYSTEM_AUDIT.md P1 #7), so
    # verifying it reaches the DB-backed revocation check — this test isn't testing
    # revocation, just the basic round-trip, so it skips cleanly without a DB rather
    # than erroring.
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"Requires a reachable Postgres database (DATABASE_URL): {exc}")


def test_access_token_round_trip():
    _skip_if_no_database()
    token = create_access_token(
        patient_id="patient-123",
        email="patient@example.com",
    )

    payload = verify_access_token(token)

    assert payload["sub"] == "patient-123"
    assert payload["email"] == "patient@example.com"


def test_access_token_rejects_tampering():
    token = create_access_token(
        patient_id="patient-123",
        email="patient@example.com",
    )
    header, payload, signature = token.split(".")
    tampered_payload = f"{payload[:-1]}x"
    tampered = ".".join([header, tampered_payload, signature])

    assert verify_access_token(tampered) is None


def _sign_with_secret(secret: str, payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            tokens_module._b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            tokens_module._b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{tokens_module._b64url_encode(signature)}"


def test_legacy_dev_secret_is_rejected_once_a_real_jwt_secret_is_configured(monkeypatch):
    # Regression test for FULL_SYSTEM_AUDIT.md P0 #1: the public "dev-only-change-me"
    # string used to be permanently accepted regardless of JWT_SECRET configuration,
    # letting anyone forge a valid token (including role=admin) for a properly
    # configured deployment. It must now be rejected once a real secret is set.
    monkeypatch.setattr(tokens_module, "JWT_SECRET", "a-real-long-random-production-secret")
    monkeypatch.setattr(tokens_module, "LEGACY_JWT_SECRETS", [])

    forged = _sign_with_secret(
        "dev-only-change-me",
        {"sub": "attacker", "email": "attacker@example.com", "role": "admin", "iat": 0, "exp": 9999999999},
    )

    assert tokens_module.verify_access_token(forged) is None


def test_legacy_secret_is_accepted_only_when_explicitly_configured_for_rotation(monkeypatch):
    monkeypatch.setattr(tokens_module, "JWT_SECRET", "new-secret-after-rotation")
    monkeypatch.setattr(tokens_module, "LEGACY_JWT_SECRETS", ["old-secret-before-rotation"])

    token_signed_with_old_secret = _sign_with_secret(
        "old-secret-before-rotation",
        {"sub": "patient-1", "email": "p@example.com", "role": "patient", "iat": 0, "exp": 9999999999},
    )

    payload = tokens_module.verify_access_token(token_signed_with_old_secret)
    assert payload["sub"] == "patient-1"
