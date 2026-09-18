"""Shared SMTP-sending mechanics, extracted from app/services/doctor_auth.py's original
inline implementation so both the doctor-invite flow and patient email verification send
through one code path. Deliberately takes every setting as an explicit argument rather
than reading environment variables itself — callers own their own config source, so this
stays reusable for any future caller with a different config surface.
"""
import smtplib
from email.message import EmailMessage


def send_email(
    *,
    host: str,
    port: int,
    use_tls: bool,
    username: str | None,
    password: str | None,
    sender: str,
    to: str,
    subject: str,
    body: str,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to
    message.set_content(body)

    with smtplib.SMTP(host, port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password or "")
        smtp.send_message(message)
