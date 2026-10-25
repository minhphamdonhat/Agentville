"""Loader for `.agentville/config.toml`."""

import tomllib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from agentville.townhall.core.errors import ConfigError

CONFIG_RELATIVE_PATH = Path(".agentville") / "config.toml"


@dataclass
class TownhallConfig:
    default_board: str = "B01"
    enforce_page_budgets: bool = True


@dataclass
class ClaudePromptsConfig:
    triage_todo: str = (
        "You are the Townhall triage officer for ticket {{ticket_id}} on board {{board_id}}.\n"
        "Read index.md, plan/plan-01-context.md, and HANDOFF.md (if resuming).\n"
        "Target files: {{where_to_change}}\n"
        "Test command: {{how_to_test}}\n\n"
        "Draft a concise, token-optimised operational brief for the downstream orchestrator.\n"
    )
    merge_worktree: str = (
        "You are the release automation officer for ticket {{ticket_id}}.\n"
        "Merge the working branch {{from_branch}} into {{to_branch}}.\n\n"
        "Operating Instructions:\n"
        "1. Navigate to the git repository root.\n"
        "2. Ensure working tree is clean.\n"
        "3. Switch to branch {{to_branch}} and pull latest changes.\n"
        "4. Merge branch {{from_branch}} with a clean merge commit referencing ticket {{ticket_id}}.\n"
        "5. If git conflicts occur, abort the merge immediately and report the conflicting files.\n"
        "6. Once merged, delete the local worktree branch {{from_branch}}.\n"
    )


@dataclass
class ClaudeConfig:
    enabled: bool = False
    default_model: str = "haiku"
    orchestrator_model: str = "sonnet"
    auto_mode: bool = True
    # Irreversible: lets the poller merge a Complete ticket's branch. Needs `enabled` too.
    auto_merge: bool = False
    prompts: ClaudePromptsConfig = field(default_factory=ClaudePromptsConfig)


@dataclass
class PluginsConfig:
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)


@dataclass
class EngineConfig:
    """``[engine]``: the Temporal engine and the triage poller."""

    # host:port of a running server or cluster; empty auto-starts a local dev server.
    temporal_address: str = ""
    temporal_namespace: str = "default"
    temporal_port: int = 7233  # fixed port of the local dev server
    temporal_ui: bool = True
    # An installed `temporal` CLI; empty looks on PATH, then downloads one.
    temporal_cli_path: str = ""
    continue_as_new_after: int = 500  # workflow events before continue-as-new
    poll_interval_seconds: float = 30.0
    claude_executable: str = "claude"
    claude_timeout_seconds: float = 1800.0  # limit for each `claude -p` run
    claude_auto_args: list[str] = field(
        default_factory=lambda: ["--permission-mode", "auto"]
    )


@dataclass
class ReservedConfig:
    enabled: bool = False


@dataclass
class Config:
    townhall: TownhallConfig = field(default_factory=TownhallConfig)
    plugins: PluginsConfig = field(default_factory=PluginsConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    rag: ReservedConfig = field(default_factory=ReservedConfig)
    memory: ReservedConfig = field(default_factory=ReservedConfig)


def _check_type(name: str, default: Any, value: Any) -> None:
    """Reject a bool, int or float value whose type differs from the default's."""
    if isinstance(default, bool):
        ok = isinstance(value, bool)
    elif isinstance(default, int):
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif isinstance(default, float):
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    else:
        return
    if not ok:
        raise ConfigError(
            f"Config key {name} must be {type(default).__name__}, "
            f"got {type(value).__name__}"
        )


def _merge(target: Any, data: dict[str, Any], path: str = "") -> None:
    """Copy known keys from `data` onto the dataclass `target`; reject unknown keys."""
    known = {f.name for f in fields(target)}
    for key, value in data.items():
        if key not in known:
            raise ConfigError(f"Unknown config key: {path}{key}")
        current = getattr(target, key)
        if is_dataclass(current):
            if not isinstance(value, dict):
                raise ConfigError(f"Config section {path}{key} must be a table")
            _merge(current, value, f"{path}{key}.")
        else:
            _check_type(f"{path}{key}", current, value)
            setattr(target, key, value)


def load_config(root: Path | None = None) -> Config:
    """Load `.agentville/config.toml` under `root`; return defaults if it is absent."""
    config = Config()
    path = (root or Path.cwd()) / CONFIG_RELATIVE_PATH
    if not path.is_file():
        return config
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"Invalid TOML in {path}: {error}") from error
    _merge(config, data)
    return config
