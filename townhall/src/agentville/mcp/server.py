"""Root FastMCP server; domain sub-servers are mounted here."""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from agentville.core.paths import ROOT_ENV_VARS  # noqa: F401  (re-exported)
from agentville.core.paths import discover_root as core_discover_root
from agentville.townhall.mcp import NAMESPACE, build_townhall_server


def discover_root(start: Path | None = None) -> Path:
    """Find the project root with the shared rules of `agentville.core.paths`.

    Order: ``AGENTVILLE_ROOT``, ``CLAUDE_PROJECT_DIR``, the nearest folder at or
    above `start` (default: the working directory) that holds ``.agentville/``, else
    `start`. Set ``AGENTVILLE_ROOT`` in the server's environment, or pass ``--root`` to
    ``agentville``, to pin the root; empty values and unexpanded ``${...}`` placeholders
    are ignored. Whether a client exports ``CLAUDE_PROJECT_DIR`` to the server process
    is not guaranteed, so it is only read when present.
    """
    return core_discover_root(None, start=start)


def build_server(root: Path | None = None) -> FastMCP:
    """Build the root server with the Townhall tools mounted as ``townhall_*``."""
    resolved = Path(root).resolve() if root is not None else discover_root()
    server = FastMCP(
        "agentville",
        instructions="Agentville tools. Townhall tools are prefixed 'townhall_'.",
    )
    server.mount(build_townhall_server(resolved), namespace=NAMESPACE)
    return server


def run(transport: str = "stdio", root: Path | None = None) -> None:
    """Serve the root server over `transport` (``stdio``, ``http`` or ``sse``)."""
    build_server(root).run(transport=transport)  # type: ignore[arg-type]
