"""Shared TOTP/backup-code mechanics, extracted from app/services/doctor_auth.py's
original inline implementation so both doctor and patient MFA use one code path for
the actual cryptography and replay-protection logic. Deliberately takes the Fernet key
as an explicit argument rather than reading DOCTOR_AUTH_ENCRYPTION_KEY itself — same
"explicit params" pattern as app/services/email.py — callers own their own key
resolution. Doctor and patient accounts stay fully separate tables/flows; only this
algorithm is shared.
"""
import secrets
import time

import pyotp
from cryptography.fernet import Fernet, InvalidToken

TOTP_INTERVAL = 30


class TotpReplayError(Exception):
    """Raised by verify_totp when a code is a genuinely valid TOTP value but its
    time-step has already been consumed — distinct from "not a valid code at all" so
    callers can hard-reject a replay without falling through to a recovery-code check
    the way an ordinary wrong code would."""


def generate_secret() -> str:
    return pyotp.random_base32()


def encrypt_secret(secret: str, fernet_key: str) -> str:
    return Fernet(fernet_key.encode("utf-8")).encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str, fernet_key: str) -> str:
    try:
        return Fernet(fernet_key.encode("utf-8")).decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise ValueError("The enrolled MFA factor is unavailable.") from exc


def provisioning_uri(secret: str, *, name: str, issuer_name: str = "Smart Hospital Portal") -> str:
    return pyotp.TOTP(secret, interval=TOTP_INTERVAL).provisioning_uri(name=name, issuer_name=issuer_name)


def verify_totp(secret: str, code: str, last_step: int | None, *, at_step: int | None = None) -> int | None:
    """Verify a TOTP code with replay protection.

    Returns the matching step on success — callers must persist it as the new
    last_step so the same code can never be replayed, even within its own valid
    window. Returns None if the code doesn't match any step in the +/-1 clock-skew
    window at all (an ordinary wrong code — callers may fall through to another
    factor, e.g. a backup/recovery code). Raises TotpReplayError if the code is
    genuinely valid but its step was already consumed — a distinct, harder failure
    callers should not treat the same as an ordinary wrong code. at_step overrides
    "now" (for testing); defaults to the real current step.
    """
    totp = pyotp.TOTP(secret, interval=TOTP_INTERVAL)
    if not totp.verify(code, valid_window=1):
        return None

    step = at_step if at_step is not None else int(time.time() // TOTP_INTERVAL)
    matching_step = next(
        (candidate for candidate in (step, step - 1, step + 1) if totp.at(candidate * TOTP_INTERVAL) == code),
        None,
    )
    if matching_step is None:
        return None
    if last_step is not None and matching_step <= int(last_step):
        raise TotpReplayError()
    return matching_step


def generate_backup_codes(count: int = 10) -> list[str]:
    return [secrets.token_urlsafe(10) for _ in range(count)]
