"""Tests for the Temporal connection and the auto-started dev server (core/temporal.py)."""

from __future__ import annotations

import asyncio
import socket
from pathlib import Path
from typing import Any

import pytest

from agentville.core import temporal
from agentville.core.config import Config, load_config
from agentville.core.errors import AgentvilleError
from agentville.townhall import workflows as wf
from agentville.townhall.storage import Stage, TownhallStorage
from tests.townhall.test_workflows import relax_budgets, submit


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(temporal.ADDRESS_ENV, raising=False)
    monkeypatch.setenv(temporal.PLUGIN_DATA_ENV, str(tmp_path / "plugin-data"))


def closed_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def engine(**values: Any) -> Config:
    config = Config()
    for key, value in values.items():
        setattr(config.engine, key, value)
    return config


def test_engine_keys_load_from_toml(tmp_path: Path) -> None:
    (tmp_path / ".agentville").mkdir()
    (tmp_path / ".agentville" / "config.toml").write_text(
        '[engine]\ntemporal_port = 7300\ntemporal_address = "tc.example:7233"\n',
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    assert config.engine.temporal_port == 7300
    assert config.engine.claude_auto_args == ["--permission-mode", "auto"]


def test_settings_default_to_local_auto_start(tmp_path: Path) -> None:
    settings = temporal.resolve_settings(engine(temporal_port=7301))
    assert settings.address == "127.0.0.1:7301" and settings.auto_start
    assert settings.data_dir == tmp_path / "plugin-data" / "temporal"
    assert settings.db_path.name == "dev-server.sqlite"
    assert settings.download_dir == settings.data_dir / "bin"


def test_env_address_overrides_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(temporal.ADDRESS_ENV, "cluster:7233")
    settings = temporal.resolve_settings(engine(temporal_address="other:7233"))
    assert settings.address == "cluster:7233" and not settings.auto_start
    monkeypatch.delenv(temporal.ADDRESS_ENV)
    assert temporal.resolve_settings(engine(temporal_address="other:7233")).address == (
        "other:7233"
    )


def test_user_data_dir_without_plugin_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(temporal.PLUGIN_DATA_ENV)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    if temporal.sys.platform.startswith("linux"):
        assert (
            temporal.temporal_data_dir() == tmp_path / "xdg" / "agentville" / "temporal"
        )


def test_is_listening() -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        assert temporal.is_listening(f"127.0.0.1:{listener.getsockname()[1]}")
    assert not temporal.is_listening(f"127.0.0.1:{closed_port()}")
    assert not temporal.is_listening("nonsense")


@pytest.fixture
def fake_connect(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []

    async def connect(settings: temporal.ServerSettings) -> str:
        seen.append(settings.address)
        return "client"

    monkeypatch.setattr(temporal, "connect", connect)
    return seen


async def test_external_address_never_starts(
    monkeypatch: pytest.MonkeyPatch, fake_connect: list[str]
) -> None:
    monkeypatch.setenv(temporal.ADDRESS_ENV, "cluster:7233")
    async with temporal.ensure_server(Config()) as server:
        assert server.mode == "external" and server.client == "client"
    assert fake_connect == ["cluster:7233"]


async def test_reuses_a_listening_server(fake_connect: list[str]) -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        async with temporal.ensure_server(engine(temporal_port=port)) as server:
            assert server.mode == "reused"
    assert fake_connect == [f"127.0.0.1:{port}"]


class FakeEnv:
    client = "dev-client"
    stopped = False

    async def shutdown(self) -> None:
        FakeEnv.stopped = True


async def test_starts_a_persistent_dev_server(monkeypatch: pytest.MonkeyPatch) -> None:
    from temporalio.testing import WorkflowEnvironment

    calls: list[dict[str, Any]] = []

    async def start_local(**kwargs: Any) -> FakeEnv:
        calls.append(kwargs)
        return FakeEnv()

    monkeypatch.setattr(WorkflowEnvironment, "start_local", start_local)
    port = closed_port()
    async with temporal.ensure_server(
        engine(temporal_port=port, temporal_cli_path="/opt/temporal")
    ) as server:
        assert server.mode == "started" and server.client == "dev-client"
    kwargs = calls[0]
    assert kwargs["port"] == port and kwargs["ip"] == "127.0.0.1"
    assert kwargs["dev_server_database_filename"].endswith("temporal/dev-server.sqlite")
    assert kwargs["download_dest_dir"].endswith("temporal/bin")
    assert kwargs["dev_server_existing_path"] == "/opt/temporal"
    assert Path(kwargs["download_dest_dir"]).is_dir() and FakeEnv.stopped


async def test_run_worker_reports_a_failed_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from temporalio.testing import WorkflowEnvironment

    async def start_local(**kwargs: Any) -> FakeEnv:
        raise RuntimeError("download blocked")

    monkeypatch.setattr(WorkflowEnvironment, "start_local", start_local)
    root = tmp_path / "project"
    TownhallStorage(root).init_project()
    (root / ".agentville" / "config.toml").write_text(
        f"[engine]\ntemporal_port = {closed_port()}\n", encoding="utf-8"
    )
    with pytest.raises(AgentvilleError, match="download blocked"):
        await wf.run_worker(root)


async def test_end_to_end_with_auto_started_server(tmp_path: Path) -> None:
    """Real run: ensure a dev server, run the worker, signal a ticket to Complete."""
    store = TownhallStorage(tmp_path / "project")
    store.init_project()
    relax_budgets(store)
    store.create_board("B01", "Main board")
    tid = store.create_ticket("B01", "End to end").id
    stop = asyncio.Event()
    lines: list[str] = []
    task = asyncio.create_task(wf.run_worker(store.root, stop=stop, echo=lines.append))
    try:
        for _ in range(1200):
            if len(lines) >= 2 or task.done():
                break
            await asyncio.sleep(0.1)
        if task.done() and isinstance(task.exception(), AgentvilleError):
            pytest.skip(str(task.exception()).splitlines()[0])
        config = load_config(store.root)
        client = await temporal.connect(temporal.resolve_settings(config))
        handle = client.get_workflow_handle(wf.workflow_id(store.root, "B01", tid))
        for target in ("Discuss", "Planning", "Todo", "Execute"):  # the MCP hook path
            moved = store.move_ticket("B01", tid, target, "e2e")
            assert wf.notify_move(
                store.root, "B01", tid, moved.from_stage.value, target, "e2e"
            )

        for _ in range(100):
            if await handle.query("stage") == "Execute":
                break
            await asyncio.sleep(0.1)
        submit(store, tid)
        await handle.signal("sync")
        store.move_ticket("B01", tid, "Complete", "ship")  # the CLI approve path
        assert wf.notify_move(store.root, "B01", tid, "Review", "Complete", "ship")
        result = await asyncio.wait_for(handle.result(), 30)
        print(
            *lines,
            f"result: {result['stage']} after {result['events']} events",
            sep="\n",
        )
        assert result["stage"] == "Complete"
        assert store.get_ticket("B01", tid).stage is Stage.COMPLETE
    finally:
        stop.set()
        if not task.done():
            await asyncio.wait_for(task, 30)


def test_init_seeds_the_engine_section(tmp_path: Path) -> None:
    TownhallStorage(tmp_path).init_project()
    text = (tmp_path / ".agentville" / "config.toml").read_text(encoding="utf-8")
    assert "[engine]" in text and "temporal_port = 7233" in text
    assert load_config(tmp_path).engine == Config().engine
