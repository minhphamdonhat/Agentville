from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from agentville import __version__
from agentville.cli import main
from agentville.targets import TARGETS
from agentville.targets.claude_code import PLUGIN_IDS, STEERING_LINES

CLAUDE = "/opt/bin/claude"


class FakeRun:
    """Records subprocess.run calls and answers with the given exit codes."""

    def __init__(self, codes: list[int] | None = None, output: str = "") -> None:
        self.calls: list[dict[str, Any]] = []
        self.codes = list(codes or [])
        self.output = output

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"command": command, **kwargs})
        code = self.codes.pop(0) if self.codes else 0
        return subprocess.CompletedProcess(command, code, stdout=self.output, stderr="")


@pytest.fixture
def with_claude(monkeypatch: pytest.MonkeyPatch) -> FakeRun:
    fake = FakeRun()
    monkeypatch.setattr("agentville.targets.claude_code.shutil.which", lambda name: CLAUDE if name == "claude" else None)
    monkeypatch.setattr("agentville.targets.claude_code.subprocess.run", fake)
    return fake


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_command_prints_help_and_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "install" in capsys.readouterr().out


def test_unknown_channel_is_usage_error() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["install", "--channel", "nightly"])
    assert exc.value.code == 2


def test_registry_holds_claude_code() -> None:
    assert "claude-code" in TARGETS


def test_missing_project_dir_exits_2(home: Path, tmp_path: Path) -> None:
    assert main(["install", "--scope", "project", "--project-dir", str(tmp_path / "absent")]) == 2


@pytest.mark.parametrize("channel", ["stable", "beta", "dev"])
def test_cli_path_user_scope_commands(home: Path, with_claude: FakeRun, channel: str) -> None:
    assert main(["install", "--channel", channel]) == 0
    commands = [call["command"] for call in with_claude.calls]
    assert commands == [
        [CLAUDE, "plugin", "marketplace", "add", "minhphamdonhat/Agentville", "--scope", "user"],
        [CLAUDE, "plugin", "install", PLUGIN_IDS[channel], "--scope", "user"],
    ]
    assert all(call["cwd"] is None for call in with_claude.calls)
    claude_md = home / ".claude" / "CLAUDE.md"
    assert claude_md.read_text(encoding="utf-8").splitlines() == list(STEERING_LINES)
    assert not (home / ".claude" / "settings.json").exists()


def test_cli_path_project_scope_runs_in_project(home: Path, project: Path, with_claude: FakeRun) -> None:
    assert main(["install", "--scope", "project", "--project-dir", str(project)]) == 0
    assert [call["command"][-1] for call in with_claude.calls] == ["project", "project"]
    assert all(call["cwd"] == project.resolve() for call in with_claude.calls)
    assert (project / "CLAUDE.md").exists()
    assert not (home / ".claude" / "CLAUDE.md").exists()


def test_cli_path_tolerates_marketplace_already_added(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRun(codes=[1, 0], output="Marketplace 'minhphamdo' is already added")
    monkeypatch.setattr("agentville.targets.claude_code.shutil.which", lambda name: CLAUDE)
    monkeypatch.setattr("agentville.targets.claude_code.subprocess.run", fake)
    assert main(["install"]) == 0
    assert len(fake.calls) == 2


def test_cli_path_install_failure_exits_1_and_skips_claude_md(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRun(codes=[0, 3], output="boom")
    monkeypatch.setattr("agentville.targets.claude_code.shutil.which", lambda name: CLAUDE)
    monkeypatch.setattr("agentville.targets.claude_code.subprocess.run", fake)
    assert main(["install"]) == 1
    assert not (home / ".claude" / "CLAUDE.md").exists()


def test_fallback_user_scope_writes_settings(home: Path, no_claude: None) -> None:
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"model": "opus"}), encoding="utf-8")
    assert main(["install", "--channel", "beta"]) == 0
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["model"] == "opus"
    assert data["enabledPlugins"] == {"agentville-beta@minhphamdo": True}
    assert data["extraKnownMarketplaces"] == {
        "minhphamdo": {"source": {"source": "github", "repo": "minhphamdonhat/Agentville"}}
    }


def test_fallback_project_scope_writes_project_files(home: Path, project: Path, no_claude: None) -> None:
    assert main(["install", "--scope", "project", "--project-dir", str(project)]) == 0
    data = json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert data["enabledPlugins"] == {"agentville@minhphamdo": True}
    assert (project / "CLAUDE.md").read_text(encoding="utf-8").splitlines() == list(STEERING_LINES)
    assert not (home / ".claude").exists()


def test_fallback_refuses_invalid_settings(home: Path, no_claude: None, capsys: pytest.CaptureFixture[str]) -> None:
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text("{oops", encoding="utf-8")
    assert main(["install"]) == 1
    assert settings.read_text(encoding="utf-8") == "{oops"
    assert not (home / ".claude" / "CLAUDE.md").exists()
    assert "not valid JSON" in capsys.readouterr().err


def test_install_twice_is_idempotent(home: Path, no_claude: None) -> None:
    assert main(["install"]) == 0
    files = [home / ".claude" / "settings.json", home / ".claude" / "CLAUDE.md"]
    before = [path.read_bytes() for path in files]
    assert main(["install"]) == 0
    assert [path.read_bytes() for path in files] == before


def test_dry_run_with_claude_runs_and_writes_nothing(
    home: Path, project: Path, with_claude: FakeRun, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["install", "--dry-run", "--scope", "project", "--project-dir", str(project)]) == 0
    assert with_claude.calls == []
    assert list(project.iterdir()) == []
    out = capsys.readouterr().out
    assert "[dry-run] would run: claude plugin install agentville@minhphamdo --scope project" in out
    assert "[dry-run] would append 2 line(s)" in out


def test_dry_run_without_claude_writes_nothing(home: Path, no_claude: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["install", "--dry-run"]) == 0
    assert list(home.iterdir()) == []
    assert "[dry-run] would update" in capsys.readouterr().out


def test_cli_path_warns_when_other_channel_enabled(
    home: Path, with_claude: FakeRun, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"enabledPlugins": {"agentville@minhphamdo": True}}), encoding="utf-8")
    assert main(["install", "--channel", "beta"]) == 0
    assert "agentville@minhphamdo is also enabled" in capsys.readouterr().err


def test_cli_path_ignores_invalid_settings_for_warning(home: Path, with_claude: FakeRun) -> None:
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text("{oops", encoding="utf-8")
    assert main(["install"]) == 0
    assert settings.read_text(encoding="utf-8") == "{oops"


def test_fallback_warns_when_other_channel_enabled(
    home: Path, no_claude: None, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"enabledPlugins": {"agentville-dev@minhphamdo": True}}), encoding="utf-8")
    assert main(["install"]) == 0
    assert "agentville-dev@minhphamdo is also enabled" in capsys.readouterr().err
