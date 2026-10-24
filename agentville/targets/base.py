"""What every install target receives and provides."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agentville.console import Console

SCOPES = ("user", "project")
CHANNELS = ("stable", "beta", "dev")

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


@dataclass(frozen=True)
class InstallOptions:
    """One install request, already validated by the CLI."""

    scope: str
    channel: str
    project_dir: Path
    home: Path
    dry_run: bool = False


class Target(Protocol):
    """An agent platform Agentville can be installed into, such as Claude Code."""

    name: str
    description: str

    def install(self, options: InstallOptions, console: Console) -> int:
        """Install Agentville and return an exit code."""
        ...
