"""One answer to "which folder is the project root?" for the CLI and the MCP server."""

from __future__ import annotations

import os
from pathlib import Path

ROOT_ENV_VARS = ("AGENTVILLE_ROOT", "CLAUDE_PROJECT_DIR")


def _env_root(name: str) -> Path | None:
    """The folder an environment variable names, or None when it is unset, empty or a literal placeholder.

    A value that starts with ``${`` is a template a client failed to expand (for
    example ``${CLAUDE_PROJECT_DIR}``); using it would make a folder of that name.
    """
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("${"):
        return None
    return Path(value).expanduser().resolve()


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: the current folder) to the first ``.agentville/``, else `start`."""
    origin = (start or Path.cwd()).resolve()
    for candidate in (origin, *origin.parents):
        if (candidate / ".agentville").is_dir():
            return candidate
    return origin


def discover_root(
    explicit: Path | str | None = None, *, start: Path | None = None
) -> Path:
    """Find the project root.

    Order, first match wins: `explicit` (such as ``--root``), ``AGENTVILLE_ROOT``,
    ``CLAUDE_PROJECT_DIR``, the nearest folder at or above `start` (default: the
    current folder) that holds ``.agentville/``, else `start` itself. Environment
    values that are empty or start with ``${`` are skipped.
    """
    if explicit is not None and str(explicit).strip():
        return Path(explicit).expanduser().resolve()
    for name in ROOT_ENV_VARS:
        found = _env_root(name)
        if found is not None:
            return found
    return find_project_root(start)
