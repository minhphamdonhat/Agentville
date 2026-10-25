from pathlib import Path

import pytest

from agentville.core.config import load_config
from agentville.core.errors import ConfigError
from agentville.core.paths import discover_root


def test_defaults_when_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config.townhall.default_board == "B01"
    assert config.plugins.claude.enabled is False


def test_override(tmp_path: Path) -> None:
    (tmp_path / ".agentville").mkdir()
    (tmp_path / ".agentville" / "config.toml").write_text(
        '[townhall]\ndefault_board = "B02"\n', encoding="utf-8"
    )
    assert load_config(tmp_path).townhall.default_board == "B02"


def test_unknown_key(tmp_path: Path) -> None:
    (tmp_path / ".agentville").mkdir()
    (tmp_path / ".agentville" / "config.toml").write_text(
        "[nope]\nx = 1\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError):
        load_config(tmp_path)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in ("AGENTVILLE_ROOT", "CLAUDE_PROJECT_DIR"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_discover_root_order(tmp_path: Path, clean_env: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    nested = project / "a" / "b"
    nested.mkdir(parents=True)
    (project / ".agentville").mkdir()
    clean_env.chdir(nested)
    assert discover_root() == project.resolve()  # walk up
    clean_env.chdir(tmp_path)
    assert discover_root() == tmp_path.resolve()  # else the current folder
    clean_env.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "claude"))
    assert discover_root() == (tmp_path / "claude").resolve()
    clean_env.setenv("AGENTVILLE_ROOT", str(tmp_path / "env"))
    assert discover_root() == (tmp_path / "env").resolve()
    assert discover_root(tmp_path / "explicit") == (tmp_path / "explicit").resolve()


@pytest.mark.parametrize("value", ["", "   ", "${CLAUDE_PROJECT_DIR}", "${HOME}/x"])
def test_discover_root_skips_empty_and_unexpanded_values(
    tmp_path: Path, clean_env: pytest.MonkeyPatch, value: str
) -> None:
    (tmp_path / ".agentville").mkdir()
    clean_env.chdir(tmp_path)
    clean_env.setenv("AGENTVILLE_ROOT", value)
    clean_env.setenv("CLAUDE_PROJECT_DIR", value)
    assert discover_root() == tmp_path.resolve()
    clean_env.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "real"))
    assert (
        discover_root() == (tmp_path / "real").resolve()
    )  # a bad first value falls through


def test_server_and_cli_agree_on_the_root(
    tmp_path: Path, clean_env: pytest.MonkeyPatch
) -> None:
    from agentville.mcp.server import discover_root as server_root

    (tmp_path / ".agentville").mkdir()
    nested = tmp_path / "x"
    nested.mkdir()
    clean_env.chdir(nested)
    assert server_root() == discover_root() == tmp_path.resolve()
    clean_env.setenv("AGENTVILLE_ROOT", "${CLAUDE_PROJECT_DIR}")
    assert server_root() == discover_root() == tmp_path.resolve()


def test_init_seeds_the_automation_keys_and_they_round_trip(tmp_path: Path) -> None:
    from agentville.townhall.storage import TownhallStorage

    TownhallStorage(tmp_path).init_project()
    text = (tmp_path / ".agentville" / "config.toml").read_text(encoding="utf-8")
    assert "auto_merge = false" in text and "claude_timeout_seconds = 1800.0" in text
    config = load_config(tmp_path)
    assert config.plugins.claude.auto_merge is False
    assert config.plugins.claude.enabled is False
    assert config.engine.claude_timeout_seconds == 1800.0
    (tmp_path / ".agentville" / "config.toml").write_text(
        text.replace("auto_merge = false", "auto_merge = true").replace(
            "claude_timeout_seconds = 1800.0", "claude_timeout_seconds = 60"
        ),
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    assert config.plugins.claude.auto_merge is True
    assert config.engine.claude_timeout_seconds == 60


def _write(tmp_path: Path, text: str) -> None:
    (tmp_path / ".agentville").mkdir()
    (tmp_path / ".agentville" / "config.toml").write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    "text",
    [
        '[plugins.claude]\nenabled = "false"\n',
        '[plugins.claude]\nauto_merge = "false"\n',
        "[engine]\ntemporal_port = true\n",
    ],
)
def test_wrong_type_rejected(tmp_path: Path, text: str) -> None:
    _write(tmp_path, text)
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_int_accepted_for_float(tmp_path: Path) -> None:
    _write(tmp_path, "[engine]\npoll_interval_seconds = 10\n")
    assert load_config(tmp_path).engine.poll_interval_seconds == 10


def test_valid_file_loads(tmp_path: Path) -> None:
    _write(tmp_path, "[plugins.claude]\nenabled = true\nauto_merge = true\n")
    config = load_config(tmp_path)
    assert config.plugins.claude.enabled is True
    assert config.plugins.claude.auto_merge is True
