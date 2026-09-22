"""One-time helper to mint the Gmail refresh token app/services/email.py needs.

Run this on a machine WITH A BROWSER (your laptop — not the server, which has no
display and, being the reason we moved off SMTP in the first place, is the wrong
place to do an interactive consent flow). It prints a refresh token to paste into
the server's .env as GMAIL_OAUTH_REFRESH_TOKEN.

Prerequisites, in the Google Cloud Console (console.cloud.google.com):
  1. Create (or pick) a project, then enable the "Gmail API" for it.
  2. OAuth consent screen: User type "External", add the sending Gmail account
     itself as a Test user, then — IMPORTANT — click PUBLISH APP so the status is
     "In production". Refresh tokens issued while the app sits in "Testing" expire
     after 7 days, which silently breaks email again a week later.
  3. Credentials -> Create credentials -> OAuth client ID -> type "Desktop app".
     Copy the client ID and client secret.

Usage:
    python scripts/gmail_oauth_setup.py --client-id XXX --client-secret YYY
"""
import argparse
import http.server
import secrets
import socket
import sys
import threading
import urllib.parse

import httpx

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
# gmail.send only — the narrowest scope that can send mail. Deliberately not
# gmail.modify or full mail.google.com: this token never needs to read the inbox.
SCOPE = "https://www.googleapis.com/auth/gmail.send"


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    result: dict[str, str] = {}
    done = threading.Event()

    def do_GET(self) -> None:
        params = {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).items()}
        # Browsers fire extra requests at this server — /favicon.ico above all — and
        # those carry no query string. Only the redirect actually carrying the OAuth
        # result may set `result`, or a favicon hit would erase the code before the
        # main thread reads it, hanging the script forever.
        if "code" not in params and "error" not in params:
            self.send_response(404)
            self.end_headers()
            return

        _CallbackHandler.result = params
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<h2>Authorized. You can close this tab and return to the terminal.</h2>"
            if "code" in params
            else b"<h2>Authorization failed. Check the terminal.</h2>"
        )
        _CallbackHandler.done.set()

    def log_message(self, *args) -> None:
        pass  # keep the console output to just our own prompts


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    args = parser.parse_args()

    port = _free_port()
    redirect_uri = f"http://localhost:{port}"
    state = secrets.token_urlsafe(16)

    query = urllib.parse.urlencode(
        {
            "client_id": args.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            # access_type=offline + prompt=consent is what makes Google return a
            # refresh_token; without both, repeat authorizations return only a
            # short-lived access token and this script has nothing to print.
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    print(f"\nOpen this URL in a browser and sign in as the SENDING Gmail account:\n\n{AUTH_URL}?{query}\n")

    server = http.server.HTTPServer(("127.0.0.1", port), _CallbackHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Waiting for the redirect back to {redirect_uri} ...")
    if not _CallbackHandler.done.wait(timeout=300):
        print("ERROR: timed out after 5 minutes waiting for the browser redirect.", file=sys.stderr)
        return 1
    server.shutdown()

    result = _CallbackHandler.result
    if result.get("state") != state:
        print("ERROR: state mismatch — aborting rather than trusting this redirect.", file=sys.stderr)
        return 1
    if "code" not in result:
        print(f"ERROR: no authorization code returned: {result}", file=sys.stderr)
        return 1

    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "code": result["code"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    if response.status_code != 200:
        print(f"ERROR: token exchange failed ({response.status_code}): {response.text}", file=sys.stderr)
        return 1

    refresh_token = response.json().get("refresh_token")
    if not refresh_token:
        print(
            "ERROR: Google returned no refresh_token. This happens when the account has "
            "already authorized this client — revoke it at "
            "https://myaccount.google.com/permissions and run this again.",
            file=sys.stderr,
        )
        return 1

    print("\nDone. Add these three lines to the server's .env:\n")
    print(f"GMAIL_OAUTH_CLIENT_ID={args.client_id}")
    print(f"GMAIL_OAUTH_CLIENT_SECRET={args.client_secret}")
    print(f"GMAIL_OAUTH_REFRESH_TOKEN={refresh_token}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
