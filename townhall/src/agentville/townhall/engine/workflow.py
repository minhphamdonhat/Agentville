"""`TicketLifecycleWorkflow` and its activities: the sandbox-safe part of the engine.

Ground truth stays on disk. The workflow keeps one ticket's stage in step with
``index.md``; it touches storage only through activities, so it stays
deterministic. The decision logic lives in `LifecycleCore`, which the workflow
wraps and the tests drive without a server.

Every product path (CLI, MCP tools, poller) writes a move to disk first and then
notifies the workflow, so two signals are enough:

* ``move(target, reason, expected_from)``: apply the move if the disk is not
  there yet; with ``expected_from`` it is a notification, and a stale one only
  re-reads the disk;
* ``sync()``: re-read the disk.

Queries: ``stage()`` and ``status()``. The workflow completes when the ticket
reaches Complete, or with ``removed: true`` when its folder is gone, and
continues as new after ``[engine].continue_as_new_after`` events.

Nothing here may import subprocess, signal, threading or the client: the
sandbox re-imports this module.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from datetime import timedelta
from pathlib import Path
from typing import Any

from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from agentville.core.errors import (
        InvalidTransitionError,
        NotFoundError,
        TownhallError,
    )
    from agentville.townhall.storage import Stage, TownhallStorage, parse_stage

WORKFLOW_NAME = "TicketLifecycleWorkflow"
SYNC_STAGE = "townhall.sync_stage"
APPLY_MOVE = "townhall.apply_move"
HISTORY_LIMIT = 50
ACTIVITY_TIMEOUT = timedelta(seconds=30)
ACTIVITY_RETRY = RetryPolicy(maximum_attempts=5)


# ------------------------------------------------------------------------ payloads


@dataclass
class TicketRef:
    board_id: str
    ticket_id: str


@dataclass
class MoveSignal:
    """``expected_from`` marks a notification: a stale one only re-reads the disk."""

    target: str
    reason: str = ""
    expected_from: str | None = None


@dataclass
class Event:
    kind: str  # "move" or "sync"
    target: str | None = None
    reason: str = ""
    expected_from: str | None = None


@dataclass
class MoveRequest:
    board_id: str
    ticket_id: str
    target: str | None
    reason: str = ""
    expected_from: str | None = None  # mismatch: stale notification, re-read only


@dataclass
class MoveOutcome:
    stage: str
    applied: bool
    note: str = ""


@dataclass
class LifecycleInput:
    board_id: str
    ticket_id: str
    stage: str | None = None
    pending: list[Event] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    events: int = 0
    runs: int = 1
    continue_as_new_after: int = 500
    removed: bool = False


class MoveRejected(Exception):
    """A requested move the state machine or its guards refused."""


# ---------------------------------------------------------------------- core logic

Call = Callable[[str, Any], Awaitable[Any]]
"""Runs one activity by name: ``await call(APPLY_MOVE, request)``."""


class LifecycleCore:
    """The workflow's state and decisions, free of Temporal so tests can drive it."""

    def __init__(self, state: LifecycleInput) -> None:
        self.state = state
        self.events_this_run = 0

    @property
    def ref(self) -> TicketRef:
        return TicketRef(self.state.board_id, self.state.ticket_id)

    @property
    def done(self) -> bool:
        return self.state.removed or self.state.stage == Stage.COMPLETE.value

    @property
    def has_pending(self) -> bool:
        return bool(self.state.pending)

    def enqueue(self, event: Event) -> None:
        self.state.pending.append(event)

    def should_continue_as_new(self) -> bool:
        return self.events_this_run >= max(1, self.state.continue_as_new_after)

    async def start(self, call: Call) -> None:
        if self.state.stage is None:
            await self._sync(call)

    async def _sync(self, call: Call) -> str:
        """Re-read the disk stage; never raises.

        A missing ticket marks the run removed, so it ends cleanly. Any other
        read error keeps the last known stage; the next ``sync`` tries again.
        """
        try:
            stage = await call(SYNC_STAGE, self.ref)
        except MoveRejected as exc:
            return f"sync failed: {exc}"
        if stage is None:
            self.state.removed = True
            return "ticket removed"
        self.state.stage = stage
        return "synced"

    async def drain(self, call: Call) -> None:
        """Handle queued events until none remain, the ticket completes or the run is full."""
        while (
            self.state.pending and not self.done and not self.should_continue_as_new()
        ):
            await self.handle(self.state.pending.pop(0), call)

    async def handle(self, event: Event, call: Call) -> None:
        entry: dict[str, Any] = {"event": event.kind, "from": self.state.stage}
        if event.kind == "move":
            request = MoveRequest(
                self.state.board_id,
                self.state.ticket_id,
                event.target,
                event.reason,
                event.expected_from,
            )
            try:
                outcome = await call(APPLY_MOVE, request)
            except MoveRejected as exc:
                entry.update(rejected=True, note=str(exc))
                if (note := await self._sync(call)) != "synced":
                    entry["note"] = f"{exc}; {note}"
            else:
                self.state.stage = outcome.stage
                entry.update(applied=outcome.applied, note=outcome.note)
        elif event.kind == "sync":
            entry.update(applied=False, note=await self._sync(call))
        else:
            entry.update(rejected=True, note=f"Unknown event '{event.kind}'.")
        entry["to"] = self.state.stage
        self.state.history = [*self.state.history, entry][-HISTORY_LIMIT:]
        self.state.events += 1
        self.events_this_run += 1

    def snapshot(self) -> LifecycleInput:
        return replace(self.state, runs=self.state.runs + 1)

    def status(self) -> dict[str, Any]:
        return {
            "board_id": self.state.board_id,
            "ticket_id": self.state.ticket_id,
            "stage": self.state.stage,
            "removed": self.state.removed,
            "events": self.state.events,
            "runs": self.state.runs,
            "pending": len(self.state.pending),
            "history": list(self.state.history),
        }


# ---------------------------------------------------------------------- activities


def apply_move(storage: TownhallStorage, request: MoveRequest) -> MoveOutcome:
    """Make the disk stage match `request.target`; idempotent, so retries are safe."""
    if request.target is None:
        raise InvalidTransitionError("A move needs a target stage.")
    target = parse_stage(request.target)
    current = storage.get_ticket(request.board_id, request.ticket_id).stage
    if current is target:
        return MoveOutcome(current.value, False, f"already in {current.value}")
    if request.expected_from and current is not parse_stage(request.expected_from):
        return MoveOutcome(
            current.value, False, f"stale signal; ticket is in {current.value}"
        )
    storage.move_ticket(request.board_id, request.ticket_id, target, request.reason)
    return MoveOutcome(target.value, True, request.reason)


def sync_stage(storage: TownhallStorage, ref: TicketRef) -> str | None:
    """The ticket's disk stage, or None when its board or folder no longer exists."""
    try:
        return storage.get_ticket(ref.board_id, ref.ticket_id).stage.value
    except NotFoundError:
        return None


def _non_retryable(exc: TownhallError) -> ApplicationError:
    return ApplicationError(str(exc), type=type(exc).__name__, non_retryable=True)


class TownhallActivities:
    """Activities bound to one project root; storage calls run in a thread."""

    def __init__(self, root: Path | str) -> None:
        self.storage = TownhallStorage(root)

    @activity.defn(name=SYNC_STAGE)
    async def sync_stage(self, ref: TicketRef) -> str | None:
        try:
            return await asyncio.to_thread(sync_stage, self.storage, ref)
        except TownhallError as exc:
            raise _non_retryable(exc) from exc

    @activity.defn(name=APPLY_MOVE)
    async def apply_move(self, request: MoveRequest) -> MoveOutcome:
        try:
            return await asyncio.to_thread(apply_move, self.storage, request)
        except TownhallError as exc:
            raise _non_retryable(exc) from exc

    def all(self) -> list[Callable[..., Any]]:
        return [self.sync_stage, self.apply_move]


# ------------------------------------------------------------------------ workflow

_RESULT_TYPES: dict[str, Any] = {SYNC_STAGE: str | None, APPLY_MOVE: MoveOutcome}


@workflow.defn(name=WORKFLOW_NAME)
class TicketLifecycleWorkflow:
    """One ticket's lifecycle (specification section 8)."""

    @workflow.init
    def __init__(self, data: LifecycleInput) -> None:
        self.core = LifecycleCore(data)

    @workflow.run
    async def run(self, data: LifecycleInput) -> dict[str, Any]:
        await self.core.start(self._call)
        while True:
            await workflow.wait_condition(
                lambda: self.core.has_pending or self.core.done
            )
            await self.core.drain(self._call)
            if self.core.done:
                return self.core.status()
            if (
                self.core.should_continue_as_new()
                or workflow.info().is_continue_as_new_suggested()
            ):
                await workflow.wait_condition(workflow.all_handlers_finished)
                workflow.continue_as_new(self.core.snapshot())

    async def _call(self, name: str, arg: Any) -> Any:
        try:
            return await workflow.execute_activity(
                name,
                arg,
                start_to_close_timeout=ACTIVITY_TIMEOUT,
                retry_policy=ACTIVITY_RETRY,
                result_type=_RESULT_TYPES[name],
            )
        except ActivityError as exc:
            cause = exc.cause
            raise MoveRejected(getattr(cause, "message", None) or str(exc)) from exc

    @workflow.signal
    def move(self, data: MoveSignal) -> None:
        self.core.enqueue(Event("move", data.target, data.reason, data.expected_from))

    @workflow.signal
    def sync(self) -> None:
        self.core.enqueue(Event("sync"))

    @workflow.query
    def stage(self) -> str | None:
        return self.core.state.stage

    @workflow.query
    def status(self) -> dict[str, Any]:
        return self.core.status()
