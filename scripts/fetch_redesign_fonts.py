"""Downloads the latin subset of the three redesign font families and writes a local
@font-face stylesheet, so the application makes no external font request at runtime.

Latin subset only: the doctor workspace is an English-language UI, and pulling every
unicode-range would multiply the payload for glyphs nothing renders.
"""
import os
import re
import sys

import httpx

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(_REPO_ROOT, "app", "api", "static", "vendor", "fonts")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

FAMILIES = {
    "Bricolage Grotesque": "family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700",
    "Geist": "family=Geist:wght@400;500;600",
    "Geist Mono": "family=Geist+Mono:wght@400;500",
}

BLOCK = re.compile(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{[^}]*\})", re.S)
SRC = re.compile(r"src:\s*url\((https://[^)]+\.woff2)\)")

os.makedirs(OUT_DIR, exist_ok=True)
css_out = [
    "/* Self-hosted redesign typefaces (latin subset).",
    " * Downloaded from Google Fonts at build time and served from this origin so the",
    " * application makes NO external request at runtime: a clinical app should not call",
    " * a third party on every page load, and it must still render on a restricted or",
    " * offline network. Regenerate with scripts/fetch_redesign_fonts.py.",
    " * Fonts are licensed under the SIL Open Font License 1.1.",
    " */",
    "",
]

total = 0
with httpx.Client(timeout=30.0, follow_redirects=True, headers={"User-Agent": UA}) as client:
    for label, query in FAMILIES.items():
        resp = client.get(f"https://fonts.googleapis.com/css2?{query}&display=swap")
        resp.raise_for_status()
        found = False
        for subset, block in BLOCK.findall(resp.text):
            if subset != "latin":
                continue
            match = SRC.search(block)
            if not match:
                continue
            url = match.group(1)
            weight = re.search(r"font-weight:\s*([^;]+);", block)
            weight_label = (weight.group(1).strip() if weight else "400").replace(" ", "")
            filename = f"{label.lower().replace(' ', '-')}-{weight_label}.woff2"
            data = client.get(url).content
            with open(os.path.join(OUT_DIR, filename), "wb") as handle:
                handle.write(data)
            total += len(data)
            css_out.append(block.replace(url, f"./{filename}").strip())
            css_out.append("")
            found = True
            print(f"  {filename}  {len(data) / 1024:.1f} KB")
        if not found:
            print(f"!! no latin subset found for {label}", file=sys.stderr)
            sys.exit(1)

with open(os.path.join(OUT_DIR, "fonts.css"), "w", encoding="utf-8") as handle:
    handle.write("\n".join(css_out))

print(f"TOTAL: {total / 1024:.1f} KB across {len(os.listdir(OUT_DIR)) - 1} files")
