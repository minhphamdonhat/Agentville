"""Registry of install targets. Add a platform, such as Codex or Cursor, as a module here."""

from __future__ import annotations

from agentville.targets import claude_code
from agentville.targets.base import Target

TARGETS: dict[str, Target] = {
    claude_code.TARGET.name: claude_code.TARGET,
}

DEFAULT_TARGET = claude_code.TARGET.name


def get_target(name: str) -> Target:
    return TARGETS[name]
