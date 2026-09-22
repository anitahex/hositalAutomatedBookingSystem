"""Shared email-sending mechanics for every flow that mails a user (doctor invites,
patient signup verification, password reset, MFA notices).

Sends via the Gmail REST API over HTTPS rather than SMTP: the deployment server's
provider blocks outbound SMTP entirely (ports 587/465), so smtplib could never
connect from there, while HTTPS/443 works normally. Authentication is OAuth2 — the
Gmail API does not accept the app passwords SMTP used. Run
scripts/gmail_oauth_setup.py once to mint the refresh token these settings need.
"""
import base64
import os
import threading
import time
from email.message import EmailMessage

import httpx

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

# An access token lasts ~1 hour, so caching it keeps all but the first send of each
# hour down to a single HTTP round trip. Guarded by a lock because every caller
# sends from its own daemon thread.
_token_lock = threading.Lock()
_cached_token: tuple[str, float] | None = None


class EmailConfigError(RuntimeError):
    """Raised when the Gmail OAuth settings are missing or no longer valid."""


def _access_token() -> str:
    global _cached_token
    with _token_lock:
        if _cached_token is not None and time.monotonic() < _cached_token[1]:
            return _cached_token[0]

        client_id = os.getenv("GMAIL_OAUTH_CLIENT_ID", "").strip()
        client_secret = os.getenv("GMAIL_OAUTH_CLIENT_SECRET", "").strip()
        refresh_token = os.getenv("GMAIL_OAUTH_REFRESH_TOKEN", "").strip()
        if not (client_id and client_secret and refresh_token):
            raise EmailConfigError(
                "GMAIL_OAUTH_CLIENT_ID, GMAIL_OAUTH_CLIENT_SECRET and GMAIL_OAUTH_REFRESH_TOKEN "
                "must all be set when email delivery is enabled. Run scripts/gmail_oauth_setup.py."
            )

        response = httpx.post(
            _TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
        if response.status_code != 200:
            # Google returns the real reason only in the body, and this runs on a
            # daemon thread where the log line is the sole diagnostic — so include it.
            if "invalid_grant" in response.text:
                raise EmailConfigError(
                    "Gmail refresh token is no longer valid, so no email can be sent. The OAuth app "
                    "is in 'Testing' status, where Google expires refresh tokens after 7 days. Mint a "
                    "new one (python scripts/gmail_oauth_setup.py --client-id ... --client-secret ...), "
                    "put it in GMAIL_OAUTH_REFRESH_TOKEN, and restart. Publishing the app in the Cloud "
                    f"Console makes tokens stop expiring. Google's response: {response.text}"
                )
            raise EmailConfigError(
                f"Gmail OAuth token refresh failed ({response.status_code}): {response.text}"
            )

        payload = response.json()
        # Refresh a minute early so a token can't expire between this check and the send.
        _cached_token = (payload["access_token"], time.monotonic() + payload.get("expires_in", 3600) - 60)
        return _cached_token[0]


def send_email(*, sender: str, to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to
    message.set_content(body)

    response = httpx.post(
        _SEND_URL,
        headers={"Authorization": f"Bearer {_access_token()}"},
        json={"raw": base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")},
        timeout=20,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Gmail API send failed ({response.status_code}): {response.text}")
