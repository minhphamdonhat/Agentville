"""Shared fixtures: every test runs against temporary folders, never the real home."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "home"
    folder.mkdir()
    monkeypatch.setenv("HOME", str(folder))
    monkeypatch.setenv("USERPROFILE", str(folder))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: folder))
    return folder


@pytest.fixture
def project(tmp_path: Path) -> Path:
    folder = tmp_path / "project"
    folder.mkdir()
    return folder


@pytest.fixture
def no_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agentville.targets.claude_code.shutil.which", lambda name: None)
