"""Download the fastText language-identification model if it isn't already present.

Usage:
    python scripts/download_language_model.py

Run automatically during `docker build` (see Dockerfile) and optionally by hand for
local, non-Docker development. Never raises: language.py already falls back to a
script-based heuristic when the model is missing ("detector failures must never
block a chat turn"), so a failed download here only warns and exits 0.
"""

from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
TARGET_PATH = Path(os.getenv("LANGUAGE_ID_MODEL_PATH", str(ROOT / "models" / "lid.176.bin")))

# Real file is ~131,266,198 bytes. A much lower floor tolerates future minor
# revisions of the model while still catching a truncated download or an HTML
# error page saved in its place.
MIN_EXPECTED_SIZE = 100_000_000
CONNECT_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 5


def _is_valid_existing_file(path: Path) -> bool:
    return path.exists() and path.stat().st_size >= MIN_EXPECTED_SIZE


def _download_once(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=CONNECT_TIMEOUT_SECONDS) as response:
        with open(part_path, "wb") as out_file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out_file.write(chunk)

    if part_path.stat().st_size < MIN_EXPECTED_SIZE:
        part_path.unlink(missing_ok=True)
        raise ValueError(
            f"downloaded file is only {part_path.stat().st_size if part_path.exists() else 0} bytes, "
            f"expected at least {MIN_EXPECTED_SIZE}"
        )

    os.replace(part_path, dest)


def main() -> int:
    if _is_valid_existing_file(TARGET_PATH):
        print(f"download_language_model: already present at {TARGET_PATH}, skipping")
        return 0

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            print(f"download_language_model: downloading (attempt {attempt}/{MAX_ATTEMPTS}) to {TARGET_PATH}")
            _download_once(MODEL_URL, TARGET_PATH)
            print(f"download_language_model: done, {TARGET_PATH.stat().st_size} bytes")
            return 0
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_PAUSE_SECONDS)

    print(
        f"download_language_model: WARNING - could not download the language-ID model "
        f"after {MAX_ATTEMPTS} attempts ({last_error}). Continuing without it - the app "
        f"falls back to a lower-accuracy language heuristic. To add it later, download "
        f"{MODEL_URL} to {TARGET_PATH} manually.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
