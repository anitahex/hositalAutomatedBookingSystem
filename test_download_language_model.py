"""scripts/download_language_model.py -- no real network calls (see testing standards:
tests must not depend on live third-party services). urllib is monkeypatched instead."""

from __future__ import annotations

import io
from contextlib import contextmanager

import scripts.download_language_model as download_language_model


def test_skips_download_when_valid_file_already_present(tmp_path, monkeypatch):
    target = tmp_path / "lid.176.bin"
    target.write_bytes(b"0" * download_language_model.MIN_EXPECTED_SIZE)
    monkeypatch.setattr(download_language_model, "TARGET_PATH", target)

    def _boom(*args, **kwargs):
        raise AssertionError("urlopen should not be called when a valid file already exists")

    monkeypatch.setattr(download_language_model.urllib.request, "urlopen", _boom)

    assert download_language_model.main() == 0


def test_redownloads_when_existing_file_is_too_small(tmp_path, monkeypatch):
    target = tmp_path / "lid.176.bin"
    target.write_bytes(b"0" * 10)  # far below MIN_EXPECTED_SIZE -- looks truncated/corrupt
    monkeypatch.setattr(download_language_model, "TARGET_PATH", target)
    monkeypatch.setattr(download_language_model, "MAX_ATTEMPTS", 1)

    body = b"1" * download_language_model.MIN_EXPECTED_SIZE

    @contextmanager
    def fake_urlopen(url, timeout=None):
        yield io.BytesIO(body)

    monkeypatch.setattr(download_language_model.urllib.request, "urlopen", fake_urlopen)

    assert download_language_model.main() == 0
    assert target.read_bytes() == body
    assert not target.with_suffix(target.suffix + ".part").exists()


def test_warns_and_returns_zero_on_persistent_network_failure(tmp_path, monkeypatch, capsys):
    target = tmp_path / "lid.176.bin"
    monkeypatch.setattr(download_language_model, "TARGET_PATH", target)
    monkeypatch.setattr(download_language_model, "MAX_ATTEMPTS", 2)
    monkeypatch.setattr(download_language_model, "RETRY_PAUSE_SECONDS", 0)

    def _always_fails(*args, **kwargs):
        raise download_language_model.urllib.error.URLError("no network")

    monkeypatch.setattr(download_language_model.urllib.request, "urlopen", _always_fails)

    assert download_language_model.main() == 0
    assert not target.exists()
    assert "WARNING" in capsys.readouterr().err


def test_partial_download_never_replaces_target_on_size_mismatch(tmp_path, monkeypatch):
    target = tmp_path / "lid.176.bin"
    monkeypatch.setattr(download_language_model, "TARGET_PATH", target)
    monkeypatch.setattr(download_language_model, "MAX_ATTEMPTS", 1)

    @contextmanager
    def fake_urlopen(url, timeout=None):
        yield io.BytesIO(b"too short")  # well under MIN_EXPECTED_SIZE

    monkeypatch.setattr(download_language_model.urllib.request, "urlopen", fake_urlopen)

    assert download_language_model.main() == 0
    assert not target.exists()
    assert not target.with_suffix(target.suffix + ".part").exists()
