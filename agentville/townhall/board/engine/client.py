"""Client side of the engine: workflow ids, signal-with-start and `notify_move`.

`notify_move` is the one hook every product path calls after it has changed a
ticket's stage on disk (CLI moves, the MCP tools, the poller). It is best
effort: it gives up within about a second and never raises.
"""

from __future__ import annotations

import asyncio
import hashlib
import threading
from pathlib import Path
from typing import Any

from agentville.townhall.board.engine.workflow import (
    LifecycleInput,
    MoveSignal,
    TicketLifecycleWorkflow,
)
from agentville.townhall.core import temporal as engine_server
from agentville.townhall.core.config import Config, load_config

NOTIFY_TIMEOUT = 1.0


def project_key(root: Path | str) -> str:
    return hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:10]


def task_queue(root: Path | str) -> str:
    return f"agentville-townhall-{project_key(root)}"


def workflow_id(root: Path | str, board_id: str, ticket_id: str) -> str:
    return f"townhall-{board_id}-{ticket_id}-{project_key(root)}"


async def signal_with_start(
    client: Any,
    root: Path | str,
    board_id: str,
    ticket_id: str,
    signal_name: str,
    arg: Any = None,
    *,
    config: Config | None = None,
) -> Any:
    """Signal the ticket's workflow, starting it first when none is running."""
    config = config or load_config(Path(root))
    return await client.start_workflow(
        TicketLifecycleWorkflow.run,
        LifecycleInput(
            board_id,
            ticket_id,
            continue_as_new_after=config.engine.continue_as_new_after,
        ),
        id=workflow_id(root, board_id, ticket_id),
        task_queue=task_queue(root),
        start_signal=signal_name,
        start_signal_args=[] if arg is None else [arg],
    )


def notify_move(
    root: Path | str,
    board_id: str,
    ticket_id: str,
    from_stage: str | None,
    to_stage: str,
    reason: str = "",
    *,
    timeout: float = NOTIFY_TIMEOUT,
) -> bool:
    """Best effort: tell the ticket's workflow about a move already made on disk.

    `to_stage` is the stage the ticket is now in and `from_stage` the stage it
    left; with None the workflow applies `to_stage` unless the disk is already
    there. Returns False, quickly and without raising, when no server answers
    within `timeout` seconds. It never starts a server and writes
    nothing to disk.
    """
    try:
        config = load_config(Path(root))
        settings = engine_server.resolve_settings(config)
        if not engine_server.is_listening(settings.address, timeout=min(0.3, timeout)):
            return False
    except Exception:  # noqa: BLE001 - best effort; the caller's move already succeeded
        return False
    outcome: list[bool] = []

    async def send() -> None:
        client = await engine_server.connect(settings)
        await signal_with_start(
            client,
            root,
            board_id,
            ticket_id,
            "move",
            MoveSignal(str(to_stage), reason, from_stage and str(from_stage)),
            config=config,
        )

    def run() -> None:
        try:
            asyncio.run(asyncio.wait_for(send(), timeout))
            outcome.append(True)
        except BaseException:  # noqa: BLE001 - best effort, including timeouts
            outcome.append(False)

    thread = threading.Thread(target=run, name="townhall-notify", daemon=True)
    thread.start()
    thread.join(timeout + 0.2)
    return bool(outcome and outcome[0])
