from pathlib import Path

from typer.testing import CliRunner

from agentville import __version__
from agentville.cli.main import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help_lists_subapps() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "townhall" in result.output
    assert "engine" in result.output
    assert "init" in result.output


def test_init_creates_the_project_folder(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--root", str(tmp_path), "init"])
    assert result.exit_code == 0
    assert (tmp_path / ".agentville" / "config.toml").is_file()


def test_engine_help_lists_the_three_commands() -> None:
    result = runner.invoke(app, ["engine", "--help"])
    assert result.exit_code == 0
    for name in ("worker", "poller", "mcp"):
        assert name in result.output


def test_version_matches_the_installed_metadata() -> None:
    from importlib.metadata import version

    assert __version__ == version("agentville")


def test_init_writes_a_gitignore_for_runtime_files(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--root", str(tmp_path), "init"])
    assert result.exit_code == 0
    lines = (
        (tmp_path / ".agentville" / ".gitignore")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert {".lock", "*.lock", "*.tmp"} <= set(lines)
