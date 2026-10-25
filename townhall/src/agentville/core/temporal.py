"""Temporal connection and the auto-started local dev server.

Resolution order for the server address:

1. ``AGENTVILLE_TEMPORAL_ADDRESS`` (environment), then ``[engine].temporal_address``:
   an existing server or cluster. Nothing is started.
2. Otherwise ``127.0.0.1:[engine].temporal_port``. A server already listening there is
   reused; if none is, `ensure_server` starts the Temporal CLI dev server through
   ``temporalio.testing.WorkflowEnvironment.start_local``.

The dev server keeps its data in a SQLite file, so workflows survive restarts. Its
binary and data live under ``${CLAUDE_PLUGIN_DATA}/temporal/`` when that variable is
set, else under the per-user data folder (``~/.local/share/agentville/temporal`` on
Linux).
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from temporalio.client import Client

from agentville.core.config import Config, EngineConfig

ADDRESS_ENV = "AGENTVILLE_TEMPORAL_ADDRESS"
PLUGIN_DATA_ENV = "CLAUDE_PLUGIN_DATA"
LOCAL_HOST = "127.0.0.1"
DB_FILENAME = "dev-server.sqlite"


@dataclass(frozen=True)
class ServerSettings:
    """Where to reach Temporal and whether a local dev server may be started."""

    address: str
    namespace: str
    auto_start: bool
    port: int
    ui: bool
    data_dir: Path
    cli_path: str | None

    @property
    def db_path(self) -> Path:
        return self.data_dir / DB_FILENAME

    @property
    def download_dir(self) -> Path:
        return self.data_dir / "bin"


@dataclass(frozen=True)
class ServerHandle:
    """A connected client, and how the server was obtained."""

    client: Client
    address: str
    mode: str  # "external", "reused" or "started"
    settings: ServerSettings


def user_data_dir(app: str = "agentville") -> Path:
    """The per-user data folder, without a platformdirs dependency."""
    home = Path.home()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    return base / app


def temporal_data_dir() -> Path:
    """``${CLAUDE_PLUGIN_DATA}/temporal`` when set, else ``<user data>/temporal``."""
    plugin_data = os.environ.get(PLUGIN_DATA_ENV)
    return (Path(plugin_data) if plugin_data else user_data_dir()) / "temporal"


def resolve_settings(config: Config | EngineConfig) -> ServerSettings:
    engine = config.engine if isinstance(config, Config) else config
    explicit = (
        os.environ.get(ADDRESS_ENV, "").strip() or engine.temporal_address.strip()
    )
    cli = engine.temporal_cli_path.strip() or shutil.which("temporal")
    return ServerSettings(
        address=explicit or f"{LOCAL_HOST}:{engine.temporal_port}",
        namespace=engine.temporal_namespace,
        auto_start=not explicit,
        port=engine.temporal_port,
        ui=engine.temporal_ui,
        data_dir=temporal_data_dir(),
        cli_path=cli or None,
    )


def is_listening(address: str, timeout: float = 0.3) -> bool:
    """True when something accepts TCP connections at ``host:port``."""
    host, _, port = address.rpartition(":")
    try:
        with socket.create_connection((host or LOCAL_HOST, int(port)), timeout=timeout):
            return True
    except OSError, ValueError:
        return False


async def connect(settings: ServerSettings) -> Client:
    return await Client.connect(settings.address, namespace=settings.namespace)


@asynccontextmanager
async def ensure_server(config: Config | EngineConfig) -> AsyncIterator[ServerHandle]:
    """Yield a client for the configured server, starting a local dev server if needed.

    A server this call starts runs for the life of the context and stops with it;
    its SQLite file keeps the workflows for the next start.
    """
    settings = resolve_settings(config)
    if not settings.auto_start:
        yield ServerHandle(
            await connect(settings), settings.address, "external", settings
        )
        return
    if is_listening(settings.address):
        yield ServerHandle(
            await connect(settings), settings.address, "reused", settings
        )
        return
    from temporalio.testing import WorkflowEnvironment

    settings.download_dir.mkdir(parents=True, exist_ok=True)
    env = await WorkflowEnvironment.start_local(
        namespace=settings.namespace,
        ip=LOCAL_HOST,
        port=settings.port,
        ui=settings.ui,
        download_dest_dir=str(settings.download_dir),
        dev_server_existing_path=settings.cli_path,
        dev_server_database_filename=str(settings.db_path),
        dev_server_log_level="warn",
    )
    try:
        yield ServerHandle(env.client, settings.address, "started", settings)
    finally:
        await env.shutdown()
