"""The Townhall worker process: hosts the lifecycle workflow and its activities."""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Callable
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from agentville.townhall.board.engine.client import signal_with_start, task_queue
from agentville.townhall.board.engine.workflow import (
    TicketLifecycleWorkflow,
    TownhallActivities,
)
from agentville.townhall.board.storage import Stage, TownhallStorage
from agentville.townhall.core import temporal as engine_server
from agentville.townhall.core.config import load_config
from agentville.townhall.core.errors import AgentvilleError, TownhallError
from agentville.townhall.core.logging import get_logger

log = get_logger("agentville.townhall.board.worker")


def build_worker(client: Any, root: Path | str) -> Any:
    from temporalio.worker import Worker

    return Worker(
        client,
        task_queue=task_queue(root),
        workflows=[TicketLifecycleWorkflow],
        activities=TownhallActivities(root).all(),
    )


async def reconcile(client: Any, root: Path | str) -> int:
    """Signal ``sync`` to every unfinished ticket, so moves made while down are seen."""
    storage = TownhallStorage(root)
    config = load_config(Path(root))
    count = 0
    for board in storage.list_boards():
        try:
            tickets = storage.list_tickets(board.id)
        except TownhallError as exc:
            log.warning("Board %s skipped during reconcile: %s", board.id, exc)
            continue
        for ticket in tickets:
            if ticket.stage is not Stage.COMPLETE:
                await signal_with_start(
                    client, root, board.id, ticket.id, "sync", config=config
                )
                count += 1
    return count


async def run_worker(
    root: Path | str,
    *,
    stop: asyncio.Event | None = None,
    echo: Callable[[str], Any] | None = None,
) -> int:
    """Ensure a Temporal server, run the Townhall worker and stop on Ctrl-C or SIGTERM."""
    echo = echo or log.info
    root = Path(root).resolve()
    config = load_config(root)
    stop = stop or asyncio.Event()
    async with AsyncExitStack() as stack:
        try:
            server = await stack.enter_async_context(
                engine_server.ensure_server(config)
            )
        except RuntimeError as exc:
            raise AgentvilleError(
                f"Could not start the local Temporal dev server: {exc}\n"
                f"Install the `temporal` CLI (or set [engine].temporal_cli_path), or point "
                f"{engine_server.ADDRESS_ENV} at a running server."
            ) from exc
        await _serve(server, root, stop, echo)
    echo("Worker stopped.")
    return 0


async def _serve(
    server: engine_server.ServerHandle,
    root: Path,
    stop: asyncio.Event,
    echo: Callable[[str], Any],
) -> None:
    loop = asyncio.get_running_loop()
    handled: list[signal.Signals] = []
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
            handled.append(sig)
        except NotImplementedError, RuntimeError, ValueError:
            pass
    try:
        echo(
            f"Temporal {server.mode} at {server.address} "
            f"(data: {server.settings.data_dir})."
        )
        async with build_worker(server.client, root):
            synced = await reconcile(server.client, root)
            echo(
                f"Worker on task queue {task_queue(root)}; {synced} ticket(s) synced. Ctrl-C stops."
            )
            await stop.wait()
    finally:
        for sig in handled:
            loop.remove_signal_handler(sig)
