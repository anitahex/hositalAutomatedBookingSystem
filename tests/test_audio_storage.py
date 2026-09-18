"""Tests for the local audio storage backend (app/services/audio_storage.py).

No Azure subscription is available (per explicit instruction), so the "azure" backend
branch is only covered by monkeypatching blob_storage's functions — it can't be
exercised against a real Azure account here. The "local" backend is exercised for real
against actual disk I/O, since that's the default and the one this environment can
genuinely run.
"""

import asyncio
import os
import stat
import sys
import time

import pytest

from app.services import audio_storage


def test_default_backend_is_local():
    assert audio_storage.AUDIO_STORAGE_BACKEND == "local"


def test_ensure_private_dir_chmods_without_raising(tmp_path):
    target = tmp_path / "private"
    audio_storage._ensure_private_dir(target)
    assert target.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no POSIX permission bits — os.chmod can't enforce 0700 there")
def test_ensure_private_dir_is_actually_0700_on_posix(tmp_path):
    target = tmp_path / "private"
    audio_storage._ensure_private_dir(target)
    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == 0o700


def test_open_recording_tempfile_creates_the_directory_privately(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_storage, "LOCAL_AUDIO_DIR", tmp_path / "consult_audio")
    handle, temp_path = audio_storage.open_recording_tempfile()
    try:
        assert audio_storage.LOCAL_AUDIO_DIR.exists()
    finally:
        handle.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_local_dir_is_outside_the_publicly_served_static_directory():
    from app.api.main import _STATIC_DIR

    local_dir = audio_storage.LOCAL_AUDIO_DIR.resolve()
    static_dir = _STATIC_DIR.resolve()
    assert static_dir not in local_dir.parents and local_dir != static_dir


def test_open_recording_tempfile_creates_a_writable_file():
    handle, temp_path = audio_storage.open_recording_tempfile()
    try:
        assert os.path.exists(temp_path)
        handle.write(b"abc")
        handle.flush()
        assert os.path.getsize(temp_path) == 3
    finally:
        handle.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_finalize_recording_local_moves_temp_file_into_permanent_storage():
    handle, temp_path = audio_storage.open_recording_tempfile()
    handle.write(b"pcm-audio-bytes")
    handle.close()

    storage_ref = asyncio.run(
        audio_storage.finalize_recording(temp_path, doctor_id="doctor-1", consultation_id="consult-1")
    )
    try:
        assert storage_ref is not None
        assert not os.path.exists(temp_path), "temp file should have been moved, not copied"
        assert os.path.exists(storage_ref)
        with open(storage_ref, "rb") as f:
            assert f.read() == b"pcm-audio-bytes"
    finally:
        if storage_ref and os.path.exists(storage_ref):
            os.remove(storage_ref)


def test_finalize_recording_returns_none_for_empty_file_and_cleans_up_temp():
    handle, temp_path = audio_storage.open_recording_tempfile()
    handle.close()  # zero bytes written

    storage_ref = asyncio.run(
        audio_storage.finalize_recording(temp_path, doctor_id="doctor-1", consultation_id="consult-2")
    )
    assert storage_ref is None
    assert not os.path.exists(temp_path)


def test_download_audio_reads_back_finalized_local_file():
    handle, temp_path = audio_storage.open_recording_tempfile()
    handle.write(b"round-trip-check")
    handle.close()
    storage_ref = asyncio.run(
        audio_storage.finalize_recording(temp_path, doctor_id="doctor-1", consultation_id="consult-3")
    )
    try:
        data = asyncio.run(audio_storage.download_audio(storage_ref))
        assert data == b"round-trip-check"
    finally:
        if storage_ref and os.path.exists(storage_ref):
            os.remove(storage_ref)


def test_delete_audio_removes_local_file_and_is_idempotent():
    handle, temp_path = audio_storage.open_recording_tempfile()
    handle.write(b"to-be-deleted")
    handle.close()
    storage_ref = asyncio.run(
        audio_storage.finalize_recording(temp_path, doctor_id="doctor-1", consultation_id="consult-4")
    )
    assert os.path.exists(storage_ref)

    asyncio.run(audio_storage.delete_audio(storage_ref))
    assert not os.path.exists(storage_ref)

    # Deleting an already-missing file must not raise (mirrors blob_storage.delete_blob).
    asyncio.run(audio_storage.delete_audio(storage_ref))


def test_azure_backend_delegates_to_blob_storage(monkeypatch):
    """Cannot exercise a real Azure account here — this only proves the branch calls
    through to blob_storage's functions with the right arguments."""
    monkeypatch.setattr(audio_storage, "AUDIO_STORAGE_BACKEND", "azure")

    calls = {}

    async def fake_upload_blob(blob_name, data, content_type=None):
        calls["upload"] = (blob_name, data, content_type)

    async def fake_download_blob(blob_name):
        calls["download"] = blob_name
        return b"azure-bytes"

    async def fake_delete_blob(blob_name):
        calls["delete"] = blob_name

    monkeypatch.setattr("app.services.blob_storage.upload_blob", fake_upload_blob)
    monkeypatch.setattr("app.services.blob_storage.download_blob", fake_download_blob)
    monkeypatch.setattr("app.services.blob_storage.delete_blob", fake_delete_blob)

    handle, temp_path = audio_storage.open_recording_tempfile()
    handle.write(b"azure-path-bytes")
    handle.close()

    storage_ref = asyncio.run(
        audio_storage.finalize_recording(temp_path, doctor_id="doctor-1", consultation_id="consult-5")
    )
    assert storage_ref == "consult-audio/doctor-1/consult-5.pcm"
    assert calls["upload"][0] == storage_ref
    assert calls["upload"][1] == b"azure-path-bytes"
    assert not os.path.exists(temp_path), "azure branch must discard its local temp file"

    data = asyncio.run(audio_storage.download_audio(storage_ref))
    assert data == b"azure-bytes"
    assert calls["download"] == storage_ref

    asyncio.run(audio_storage.delete_audio(storage_ref))
    assert calls["delete"] == storage_ref


# ── cleanup_stale_temp_files (crash-orphaned temp file sweep) ────────────────

def _make_temp_pcm(directory, name, age_hours):
    path = directory / name
    path.write_bytes(b"orphaned")
    old_time = time.time() - (age_hours * 3600)
    os.utime(path, (old_time, old_time))
    return path


def test_cleanup_deletes_only_files_older_than_max_age(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_storage, "LOCAL_AUDIO_DIR", tmp_path)
    old_file = _make_temp_pcm(tmp_path, "consult-audio-old123.pcm", age_hours=10)
    recent_file = _make_temp_pcm(tmp_path, "consult-audio-recent456.pcm", age_hours=1)

    deleted = audio_storage.cleanup_stale_temp_files(max_age_hours=6)

    assert deleted == 1
    assert not old_file.exists()
    assert recent_file.exists()


def test_cleanup_ignores_finalized_recordings_outside_temp_naming(tmp_path, monkeypatch):
    """Finalized recordings live in per-doctor subdirectories as {consultation_id}.pcm,
    never matching the consult-audio-* temp-file naming pattern — this pins down that
    the cleanup glob can't accidentally sweep up a real, referenced recording."""
    monkeypatch.setattr(audio_storage, "LOCAL_AUDIO_DIR", tmp_path)
    doctor_dir = tmp_path / "doctor-1"
    doctor_dir.mkdir()
    finalized = _make_temp_pcm(doctor_dir, "consultation-abc.pcm", age_hours=100)

    deleted = audio_storage.cleanup_stale_temp_files(max_age_hours=6)

    assert deleted == 0
    assert finalized.exists()


def test_cleanup_returns_zero_when_directory_does_not_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_storage, "LOCAL_AUDIO_DIR", tmp_path / "does-not-exist")
    assert audio_storage.cleanup_stale_temp_files() == 0


def test_cleanup_uses_configured_default_max_age(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_storage, "LOCAL_AUDIO_DIR", tmp_path)
    monkeypatch.setattr(audio_storage, "CONSULT_AUDIO_TEMP_MAX_AGE_HOURS", 2)
    stale = _make_temp_pcm(tmp_path, "consult-audio-stale.pcm", age_hours=3)

    deleted = audio_storage.cleanup_stale_temp_files()  # no explicit max_age_hours

    assert deleted == 1
    assert not stale.exists()
