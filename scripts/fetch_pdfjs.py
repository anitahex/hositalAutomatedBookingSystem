"""Vendors PDF.js for the in-app document viewer.

WHY VENDORED. Same reason as the fonts (fetch_redesign_fonts.py): the application makes no
external request at runtime. A clinical workspace that fetched a script from a CDN to
render a patient's medical record would put a third party on the path of every document
open, and would stop working the moment that CDN did.

WHY PDF.js AT ALL. The document route serves files as Content-Disposition: attachment and
will keep doing so — a stored file the browser renders inline is stored XSS against the
doctor's authenticated session on this same origin (document_catalog._content_type_for
documents that decision). PDF.js renders a PDF into a <canvas> from bytes the page already
holds, so the browser never navigates to document content and no inline-rendering path is
created. The viewer still fetches through our auth and our audit, which a signed storage
URL would bypass.

WHY VERSION 3 AND NOT 4. Version 3 ships a UMD build: pdf.min.js is a classic script that
sets window.pdfjsLib, and pdf.worker.min.js is a classic worker. That matches this
frontend — classic scripts, no bundler, no build step — and it does not depend on the
server sending a JavaScript MIME type for the .mjs extension, which Python's mimetypes
module does not know and which the static route would therefore serve as
application/octet-stream, blocking module loading.

Honesty about how this was chosen: 4.x was tried first and appeared to hang, but that
turned out to be an artefact of verifying with Chrome's --virtual-time-budget, which
fast-forwards timers and breaks PDF.js's worker handshake. 4.x was never shown to be
broken in a real browser. The reasons above stand on their own; "4.x is broken" is not
one of them.

Run: python scripts/fetch_pdfjs.py
"""
import os
import sys

import httpx

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(_REPO_ROOT, "app", "api", "static", "vendor", "pdfjs")

# Pinned. An unpinned "latest" would change what renders a clinical document without any
# change landing in this repository.
VERSION = "3.11.174"
BASE = f"https://cdnjs.cloudflare.com/ajax/libs/pdf.js/{VERSION}"

FILES = {
    "pdf.min.js": f"{BASE}/pdf.min.js",
    "pdf.worker.min.js": f"{BASE}/pdf.worker.min.js",
}


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    for filename, url in FILES.items():
        print(f"fetching {filename} from {url}")
        response = httpx.get(url, timeout=120, follow_redirects=True)
        if response.status_code != 200:
            print(f"  FAILED: HTTP {response.status_code}", file=sys.stderr)
            return 1
        target = os.path.join(OUT_DIR, filename)
        with open(target, "wb") as handle:
            handle.write(response.content)
        print(f"  wrote {len(response.content):,} bytes -> {target}")
    print(f"\nPDF.js {VERSION} vendored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
