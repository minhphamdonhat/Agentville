from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentville.files import FileEditError, append_lines, merge_json_object

LINES = ("- first line", "- second line")


def test_append_creates_missing_file_and_parents(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "CLAUDE.md"
    assert append_lines(path, LINES) == list(LINES)
    assert path.read_text(encoding="utf-8") == "- first line\n- second line\n"


def test_append_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "CLAUDE.md"
    append_lines(path, LINES)
    before = path.read_bytes()
    assert append_lines(path, LINES) == []
    assert path.read_bytes() == before


def test_append_adds_only_missing_lines_after_existing_content(tmp_path: Path) -> None:
    path = tmp_path / "CLAUDE.md"
    path.write_text("# Project\nSome text\n  - second line  \n", encoding="utf-8")
    assert append_lines(path, LINES) == ["- first line"]
    assert path.read_text(encoding="utf-8") == "# Project\nSome text\n  - second line  \n\n- first line\n"


def test_append_handles_missing_final_newline(tmp_path: Path) -> None:
    path = tmp_path / "CLAUDE.md"
    path.write_text("# Project", encoding="utf-8")
    append_lines(path, LINES)
    assert path.read_text(encoding="utf-8") == "# Project\n\n- first line\n- second line\n"


def test_append_writes_lf_only(tmp_path: Path) -> None:
    path = tmp_path / "CLAUDE.md"
    append_lines(path, LINES)
    assert b"\r\n" not in path.read_bytes()


def test_append_dry_run_writes_nothing(tmp_path: Path) -> None:
    path = tmp_path / "CLAUDE.md"
    assert append_lines(path, LINES, dry_run=True) == list(LINES)
    assert not path.exists()


def test_merge_creates_file(tmp_path: Path) -> None:
    path = tmp_path / ".claude" / "settings.json"
    changed = merge_json_object(path, {"enabledPlugins": {"a@b": True}})
    assert changed == ["enabledPlugins.a@b"]
    assert json.loads(path.read_text(encoding="utf-8")) == {"enabledPlugins": {"a@b": True}}


def test_merge_preserves_other_keys(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    original = {"model": "opus", "enabledPlugins": {"other@x": False}, "permissions": {"allow": ["Read"]}}
    path.write_text(json.dumps(original), encoding="utf-8")
    merge_json_object(path, {"enabledPlugins": {"a@b": True}, "extraKnownMarketplaces": {"m": {"source": {}}}})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["model"] == "opus"
    assert data["permissions"] == {"allow": ["Read"]}
    assert data["enabledPlugins"] == {"other@x": False, "a@b": True}
    assert data["extraKnownMarketplaces"] == {"m": {"source": {}}}


def test_merge_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    merge_json_object(path, {"enabledPlugins": {"a@b": True}})
    before = path.read_bytes()
    assert merge_json_object(path, {"enabledPlugins": {"a@b": True}}) == []
    assert path.read_bytes() == before


@pytest.mark.parametrize("content", ["{not json", "[1, 2]", '{"enabledPlugins": []}'])
def test_merge_refuses_invalid_content(tmp_path: Path, content: str) -> None:
    path = tmp_path / "settings.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(FileEditError):
        merge_json_object(path, {"enabledPlugins": {"a@b": True}})
    assert path.read_text(encoding="utf-8") == content


def test_merge_dry_run_writes_nothing(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    assert merge_json_object(path, {"enabledPlugins": {"a@b": True}}, dry_run=True) == ["enabledPlugins.a@b"]
    assert not path.exists()


def test_append_keeps_crlf_in_claude_md(tmp_path: Path) -> None:
    path = tmp_path / "CLAUDE.md"
    path.write_bytes(b"# Project\r\nSome text\r\n")
    assert append_lines(path, LINES) == list(LINES)
    assert path.read_bytes() == b"# Project\r\nSome text\r\n\r\n- first line\r\n- second line\r\n"
    assert append_lines(path, LINES) == []


def test_append_keeps_crlf_without_final_newline(tmp_path: Path) -> None:
    path = tmp_path / "CLAUDE.md"
    path.write_bytes(b"# Project\r\nSome text")
    append_lines(path, LINES)
    assert path.read_bytes() == b"# Project\r\nSome text\r\n\r\n- first line\r\n- second line\r\n"


def test_append_keeps_lf_in_lf_file(tmp_path: Path) -> None:
    path = tmp_path / "CLAUDE.md"
    path.write_bytes(b"# Project\n")
    append_lines(path, LINES)
    assert path.read_bytes() == b"# Project\n\n- first line\n- second line\n"


def test_merge_keeps_crlf_in_settings_json(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_bytes(b'{\r\n  "model": "opus"\r\n}\r\n')
    assert merge_json_object(path, {"enabledPlugins": {"a@b": True}}) == ["enabledPlugins.a@b"]
    raw = path.read_bytes()
    assert raw.count(b"\r\n") == raw.count(b"\n")
    assert raw.endswith(b"}\r\n")
    assert json.loads(raw.decode("utf-8")) == {"model": "opus", "enabledPlugins": {"a@b": True}}


def test_merge_keeps_lf_in_settings_json(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_bytes(b'{\n  "model": "opus"\n}\n')
    merge_json_object(path, {"enabledPlugins": {"a@b": True}})
    assert b"\r" not in path.read_bytes()
