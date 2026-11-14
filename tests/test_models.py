import hashlib
from pathlib import Path

import pytest

from hub.models import download_models, verify_file, verify_models


def test_checksum_detects_corruption(tmp_path):
    path = tmp_path / "model"
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        verify_file(path, hashlib.sha256(b"expected").hexdigest())


def test_missing_models_have_actionable_message(tmp_path):
    with pytest.raises(ValueError, match="python -m hub.models"):
        verify_models(tmp_path)


def test_download_checks_hash_and_reuses_verified_file(monkeypatch, tmp_path):
    content = b"test-model"
    monkeypatch.setattr("hub.models.FILES", {"model": hashlib.sha256(content).hexdigest()})
    calls = []
    def curl(command, **kwargs):
        assert "--proto" in command and "=https" in command
        assert "--insecure" not in command
        calls.append(command)
        Path(command[command.index("--output") + 1]).write_bytes(content)
    monkeypatch.setattr("hub.models.subprocess.run", curl)
    download_models(tmp_path)
    download_models(tmp_path)
    assert len(calls) == 1
    assert (tmp_path / "model").read_bytes() == content


def test_bad_download_preserves_existing_file_and_removes_temporary(monkeypatch, tmp_path):
    monkeypatch.setattr("hub.models.FILES", {"model": hashlib.sha256(b"good").hexdigest()})
    target = tmp_path / "model"
    target.write_bytes(b"old")
    def curl(command, **kwargs):
        Path(command[command.index("--output") + 1]).write_bytes(b"bad")
    monkeypatch.setattr("hub.models.subprocess.run", curl)
    with pytest.raises(ValueError):
        download_models(tmp_path)
    assert target.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [target]
