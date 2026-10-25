"""Public face of Townhall's durable engine; the code lives in `agentville.townhall.board.engine`.

* `engine.workflow`: `TicketLifecycleWorkflow`, `LifecycleCore` and the
  activities (sandbox-safe).
* `engine.client`: workflow ids, `signal_with_start` and `notify_move`.
* `engine.worker`: `run_worker` and `build_worker`.
* `engine.poller`: `run_poller`, `TriagePoller` and the Complete-stage auto-merge.

Callers (CLI, MCP tools) import from here.
"""

from __future__ import annotations

from agentville.townhall.board.engine.client import (
    NOTIFY_TIMEOUT,
    notify_move,
    project_key,
    signal_with_start,
    task_queue,
    workflow_id,
)
from agentville.townhall.board.engine.poller import (
    POLLER_AGENT_ID,
    Runner,
    RunResult,
    TriagePoller,
    claude_argv,
    render_prompt,
    run_poller,
    subprocess_runner,
    ticket_branches,
)
from agentville.townhall.board.engine.worker import build_worker, reconcile, run_worker
from agentville.townhall.board.engine.workflow import (
    APPLY_MOVE,
    SYNC_STAGE,
    WORKFLOW_NAME,
    Call,
    Event,
    LifecycleCore,
    LifecycleInput,
    MoveOutcome,
    MoveRejected,
    MoveRequest,
    MoveSignal,
    TicketLifecycleWorkflow,
    TicketRef,
    TownhallActivities,
    apply_move,
    sync_stage,
)

__all__ = [
    "APPLY_MOVE",
    "NOTIFY_TIMEOUT",
    "POLLER_AGENT_ID",
    "SYNC_STAGE",
    "WORKFLOW_NAME",
    "Call",
    "Event",
    "LifecycleCore",
    "LifecycleInput",
    "MoveOutcome",
    "MoveRejected",
    "MoveRequest",
    "MoveSignal",
    "RunResult",
    "Runner",
    "TicketLifecycleWorkflow",
    "TicketRef",
    "TownhallActivities",
    "TriagePoller",
    "apply_move",
    "build_worker",
    "claude_argv",
    "notify_move",
    "project_key",
    "reconcile",
    "render_prompt",
    "run_poller",
    "run_worker",
    "signal_with_start",
    "subprocess_runner",
    "sync_stage",
    "task_queue",
    "ticket_branches",
    "workflow_id",
]
