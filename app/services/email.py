"""Shared SMTP-sending mechanics, extracted from app/services/doctor_auth.py's original
inline implementation so both the doctor-invite flow and patient email verification send
through one code path. Deliberately takes every setting as an explicit argument rather
than reading environment variables itself — callers own their own config source, so this
stays reusable for any future caller with a different config surface.
"""
import smtplib
import socket
from email.message import EmailMessage


class _IPv4SMTP(smtplib.SMTP):
    """smtplib.SMTP, but the initial socket connection is forced to IPv4.

    Some Docker hosts advertise an IPv6 route that doesn't actually work (no real
    IPv6 connectivity upstream). smtplib's default connect() uses
    socket.create_connection(), which tries every address getaddrinfo() returns —
    including the AAAA record smtp.gmail.com has — in order, so it fails fast with
    "OSError: [Errno 101] Network is unreachable" on the IPv6 attempt and never
    reaches the IPv4 address that would have worked. Restricting getaddrinfo() to
    AF_INET here skips the dead IPv6 route entirely. self._host is left untouched
    (still the hostname, not an IP literal) so starttls()'s SNI/hostname
    verification against the server's certificate still works correctly.
    """

    def _get_socket(self, host, port, timeout):
        exceptions = []
        for family, socktype, proto, _, sockaddr in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
            sock = None
            try:
                sock = socket.socket(family, socktype, proto)
                if timeout is not None:
                    sock.settimeout(timeout)
                if self.source_address:
                    sock.bind(self.source_address)
                sock.connect(sockaddr)
                return sock
            except OSError as exc:
                exceptions.append(exc)
                if sock is not None:
                    sock.close()
        raise exceptions[0] if exceptions else OSError(f"No IPv4 address found for {host}")


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

    with _IPv4SMTP(host, port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password or "")
        smtp.send_message(message)
