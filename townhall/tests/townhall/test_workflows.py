"""Tests for the Townhall engine: lifecycle core, activities, MCP hook and poller.

The lifecycle tests drive `LifecycleCore` (the workflow's logic) through the real
activities in `ActivityEnvironment`, against real storage, so they need no server.
The last test runs the real workflow on a server and skip when no Temporal server
can be had (set ``AGENTVILLE_TEMPORAL_ADDRESS`` to use one).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import socket
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment

from agentville.core.config import load_config
from agentville.mcp.server import build_server
from agentville.townhall import workflows as wf
from agentville.townhall.storage import (
    QuestionInput,
    QuestionOption,
    Stage,
    TaskStatus,
    TownhallStorage,
)

SUMMARY = "**tl;dr:** This page states one topic. It stays short and plain. Readers get the point fast.\n\n## Result\n\nIt works.\n"
EVIDENCE = (
    "**tl;dr:** This page states one topic. It stays short and plain. Readers get the point fast.\n\n"
    "## Runs\n\n| Command | Exit Code | Duration | Summary |\n|---|---|---|---|\n| `pytest` | 0 | 1s | ok |\n"
)


# ------------------------------------------------------------------------ helpers


@pytest.fixture
def store(tmp_path: Path) -> TownhallStorage:
    storage = TownhallStorage(tmp_path)
    storage.init_project()
    relax_budgets(storage)
    storage.create_board("B01", "Main board")
    return storage


def submit(storage: TownhallStorage, ticket_id: str) -> None:
    """Finish one task and submit the review (Execute to Review)."""
    storage.create_task(
        "B01",
        ticket_id,
        "task-01-work.md",
        "Work",
        1,
        ["src/x.py"],
        "**tl;dr:** Do the work. It stays short and plain. Readers get the point fast.\n",
    )
    storage.update_task_status("B01", ticket_id, "task-01-work.md", TaskStatus.DONE)
    storage.submit_review("B01", ticket_id, SUMMARY, EVIDENCE, "diff")


def relax_budgets(storage: TownhallStorage) -> None:
    """Engine tests skip the plan-page guards; storage tests cover those."""
    path = storage.root / ".agentville" / "config.toml"
    text = path.read_text(encoding="utf-8")
    assert "enforce_page_budgets = true" in text
    path.write_text(
        text.replace("enforce_page_budgets = true", "enforce_page_budgets = false"),
        encoding="utf-8",
    )


@pytest.fixture
def ticket(store: TownhallStorage) -> str:
    return store.create_ticket("B01", "Implement rate limiting").id


@pytest.fixture(autouse=True)
def no_temporal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the engine at a closed port unless a test asks for a real server."""
    if not os.environ.get("AGENTVILLE_TEST_TEMPORAL_ADDRESS"):
        monkeypatch.setenv("AGENTVILLE_TEMPORAL_ADDRESS", f"127.0.0.1:{free_port()}")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def question() -> QuestionInput:
    return QuestionInput(
        header="Failure mode",
        title="How should it fail?",
        tldr="The limiter needs a fallback. Failing open keeps uptime. Failing closed keeps protection.",
        context="The pool times out after 50ms.",
        options=[
            QuestionOption("fail_open", "Fail open", "Let requests through."),
            QuestionOption("fail_closed", "Fail closed", "Return 503."),
        ],
        slug="failure-mode",
    )


def make_call(root: Path) -> wf.Call:
    """Run the real activities offline, mapping their errors like the workflow does."""
    acts = wf.TownhallActivities(root)
    by_name = {
        wf.SYNC_STAGE: acts.sync_stage,
        wf.APPLY_MOVE: acts.apply_move,
    }

    async def call(name: str, arg: Any) -> Any:
        try:
            return await ActivityEnvironment().run(by_name[name], arg)
        except ApplicationError as exc:
            assert exc.non_retryable
            raise wf.MoveRejected(exc.message) from exc

    return call


async def core_for(store: TownhallStorage, ticket: str, **kw: Any) -> wf.LifecycleCore:
    core = wf.LifecycleCore(wf.LifecycleInput("B01", ticket, **kw))
    await core.start(make_call(store.root))
    return core


async def send(
    core: wf.LifecycleCore, store: TownhallStorage, *events: wf.Event
) -> None:
    for event in events:
        core.enqueue(event)
    await core.drain(make_call(store.root))


def move(target: Stage, expected_from: Stage | None = None) -> wf.Event:
    return wf.Event(
        "move", target.value, "test", expected_from.value if expected_from else None
    )


async def to_stage(
    core: wf.LifecycleCore, store: TownhallStorage, *stages: Stage
) -> None:
    await send(core, store, *(move(s) for s in stages))


# ---------------------------------------------------------- section 8 transitions


async def test_full_path_backlog_to_complete(
    store: TownhallStorage, ticket: str
) -> None:
    core = await core_for(store, ticket)
    assert core.state.stage == "Backlog"
    await to_stage(
        core, store, Stage.DISCUSS, Stage.PLANNING, Stage.TODO, Stage.EXECUTE
    )
    assert core.state.stage == "Execute"
    assert store.get_ticket("B01", ticket).stage is Stage.EXECUTE
    submit(store, ticket)
    await send(core, store, move(Stage.REVIEW, Stage.EXECUTE))  # notification
    assert core.state.stage == "Review"
    store.move_ticket("B01", ticket, Stage.COMPLETE, "approved")
    await send(core, store, move(Stage.COMPLETE, Stage.REVIEW))  # notification
    assert (
        core.done
        and not core.state.removed
        and store.get_ticket("B01", ticket).stage is Stage.COMPLETE
    )
    assert [h["to"] for h in core.state.history] == [
        "Discuss",
        "Planning",
        "Todo",
        "Execute",
        "Review",
        "Complete",
    ]


async def test_planning_need_inputs_back_to_planning(
    store: TownhallStorage, ticket: str
) -> None:
    core = await core_for(store, ticket)
    await to_stage(core, store, Stage.DISCUSS, Stage.PLANNING)
    store.request_inputs(
        "B01", ticket, "Planning", "Paused for a decision.", [question()]
    )
    await send(core, store, wf.Event("sync"))
    assert core.state.stage == "Need Inputs"
    await send(core, store, move(Stage.PLANNING))  # questions still pending
    assert core.state.history[-1]["rejected"] and core.state.stage == "Need Inputs"
    store.answer_question("B01", ticket, "q-01-failure-mode", ["fail_open"])
    await send(core, store, move(Stage.PLANNING))
    assert core.state.stage == "Planning"


async def test_planning_need_inputs_to_todo(
    store: TownhallStorage, ticket: str
) -> None:
    core = await core_for(store, ticket)
    await to_stage(core, store, Stage.DISCUSS, Stage.PLANNING)
    store.request_inputs("B01", ticket, "Planning", "Paused.", [question()])
    store.answer_question("B01", ticket, "q-01-failure-mode", ["fail_closed"])
    await send(core, store, move(Stage.TODO))
    assert core.state.stage == "Todo"


async def test_execute_need_inputs_resumes_in_execute(
    store: TownhallStorage, ticket: str
) -> None:
    core = await core_for(store, ticket)
    await to_stage(
        core, store, Stage.DISCUSS, Stage.PLANNING, Stage.TODO, Stage.EXECUTE
    )
    store.request_inputs("B01", ticket, "Execute", "Paused mid-task.", [question()])
    store.answer_question("B01", ticket, "q-01-failure-mode", ["fail_open"])
    await send(core, store, move(Stage.NEED_INPUTS, Stage.EXECUTE))
    assert core.state.stage == "Need Inputs"
    await send(core, store, move(Stage.PLANNING))
    assert core.state.history[-1]["rejected"]  # paused from Execute must resume there
    await send(core, store, move(Stage.EXECUTE))
    assert core.state.stage == "Execute"


async def test_review_rejected_returns_to_discuss(
    store: TownhallStorage, ticket: str
) -> None:
    core = await core_for(store, ticket)
    await to_stage(
        core, store, Stage.DISCUSS, Stage.PLANNING, Stage.TODO, Stage.EXECUTE
    )
    submit(store, ticket)
    await send(
        core,
        store,
        wf.Event("sync"),
        wf.Event("move", "Discuss", "rework"),
    )
    assert core.state.stage == "Discuss" and not core.done
    assert store.get_ticket("B01", ticket).stage is Stage.DISCUSS


async def test_invalid_transitions_are_rejected(
    store: TownhallStorage, ticket: str
) -> None:
    core = await core_for(store, ticket)
    await send(core, store, move(Stage.EXECUTE))
    last = core.state.history[-1]
    assert last["rejected"] and "Backlog cannot move to Execute" in last["note"]
    await send(core, store, move(Stage.COMPLETE))
    assert core.state.history[-1]["rejected"] and core.state.stage == "Backlog"
    await send(core, store, move(Stage.REVIEW))  # Review only via submit_review
    assert core.state.history[-1]["rejected"]
    assert store.get_ticket("B01", ticket).stage is Stage.BACKLOG


async def test_stale_notification_only_resyncs(
    store: TownhallStorage, ticket: str
) -> None:
    core = await core_for(store, ticket)
    store.move_ticket("B01", ticket, Stage.DISCUSS)
    store.move_ticket("B01", ticket, Stage.PLANNING)
    await send(core, store, move(Stage.DISCUSS, Stage.BACKLOG))
    assert core.state.stage == "Planning"
    assert (
        core.state.history[-1]["applied"] is False
        and "stale" in core.state.history[-1]["note"]
    )


async def test_move_is_idempotent_on_retry(store: TownhallStorage, ticket: str) -> None:
    store.move_ticket("B01", ticket, Stage.DISCUSS)
    outcome = wf.apply_move(store, wf.MoveRequest("B01", ticket, "Discuss"))
    assert outcome == wf.MoveOutcome("Discuss", False, "already in Discuss")


async def test_continue_as_new_after_threshold(
    store: TownhallStorage, ticket: str
) -> None:
    core = await core_for(store, ticket, continue_as_new_after=2)
    await send(core, store, wf.Event("sync"), wf.Event("sync"), move(Stage.DISCUSS))
    assert core.should_continue_as_new() and len(core.state.pending) == 1
    nxt = wf.LifecycleCore(core.snapshot())
    assert nxt.state.runs == 2 and nxt.state.events == 2
    await nxt.drain(make_call(store.root))
    assert nxt.state.stage == "Discuss" and nxt.status()["events"] == 3


async def test_status_query_payload(store: TownhallStorage, ticket: str) -> None:
    core = await core_for(store, ticket)
    status = core.status()
    assert (
        status["stage"] == "Backlog" and status["pending"] == 0 and status["runs"] == 1
    )


async def test_removed_ticket_ends_the_run_cleanly(
    store: TownhallStorage, ticket: str
) -> None:
    core = await core_for(store, ticket)
    shutil.rmtree(store.get_ticket("B01", ticket).path)
    await send(core, store, move(Stage.DISCUSS), wf.Event("sync"))
    assert core.done and core.state.removed and len(core.state.pending) == 1
    assert "ticket removed" in core.state.history[-1]["note"]
    assert core.status()["removed"] is True and core.state.stage == "Backlog"


async def test_missing_ticket_at_start_is_removed(store: TownhallStorage) -> None:
    core = await core_for(store, "9999")
    assert core.done and core.state.removed and core.state.stage is None


async def test_unreadable_ticket_keeps_the_last_stage(
    store: TownhallStorage, ticket: str
) -> None:
    core = await core_for(store, ticket)
    index = store.get_ticket("B01", ticket).path / "index.md"
    good = index.read_text(encoding="utf-8")
    index.write_text("---\nstage: [broken\n---\n", encoding="utf-8")
    await send(core, store, wf.Event("sync"))
    assert not core.done and core.state.stage == "Backlog"
    assert core.state.history[-1]["note"].startswith("sync failed")
    index.write_text(good, encoding="utf-8")
    await send(core, store, move(Stage.DISCUSS))
    assert core.state.stage == "Discuss"


async def test_workflow_passes_the_sandbox() -> None:
    from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner
    from temporalio.workflow import _Definition

    defn = _Definition.must_from_class(wf.TicketLifecycleWorkflow)
    assert defn.name == "TicketLifecycleWorkflow"
    assert set(defn.signals) == {"move", "sync"}
    assert set(defn.queries) >= {"stage", "status"}
    SandboxedWorkflowRunner().prepare_workflow(defn)


def test_ids_are_per_project(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    assert wf.workflow_id(a, "B01", "1001") != wf.workflow_id(b, "B01", "1001")
    assert wf.workflow_id(a, "B01", "1001").startswith("townhall-B01-1001-")


# --------------------------------------------------------------------- MCP hook


def test_notify_move_no_server_is_fast(store: TownhallStorage, ticket: str) -> None:
    started = time.monotonic()
    assert (
        wf.notify_move(store.root, "B01", ticket, "Backlog", "Discuss", "go") is False
    )
    assert time.monotonic() - started < 1.0


def test_notify_move_silent_server_times_out(
    store: TownhallStorage, ticket: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with socket.socket() as listener:  # accepts TCP, never speaks gRPC
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        monkeypatch.setenv(
            "AGENTVILLE_TEMPORAL_ADDRESS", f"127.0.0.1:{listener.getsockname()[1]}"
        )
        started = time.monotonic()
        assert wf.notify_move(store.root, "B01", ticket, None, "Discuss") is False
        assert time.monotonic() - started < 1.6


async def test_mcp_move_succeeds_without_temporal(
    store: TownhallStorage, ticket: str
) -> None:
    async with Client(build_server(store.root)) as client:
        result = await client.call_tool(
            "townhall_move_ticket",
            {
                "board_id": "B01",
                "ticket_id": ticket,
                "target_stage": "Discuss",
                "reason": "go",
            },
        )
    assert result.data["to_stage"] == "Discuss"
    assert store.get_ticket("B01", ticket).stage is Stage.DISCUSS


# ------------------------------------------------------------------------ poller


def enable_claude(
    store: TownhallStorage, auto_mode: bool = True, auto_merge: bool = False
) -> None:
    path = store.root / ".agentville" / "config.toml"
    text = path.read_text(encoding="utf-8").replace(
        "[plugins.claude]\nenabled = false", "[plugins.claude]\nenabled = true"
    )
    if auto_merge:
        text = text.replace("auto_merge = false", "auto_merge = true")
    if not auto_mode:
        text = text.replace("auto_mode = true", "auto_mode = false")
    path.write_text(text, encoding="utf-8")


class FakeClaude:
    """Stands in for every subprocess; never runs a real claude."""

    def __init__(self, *codes: int, during: Any = None) -> None:
        self.codes = list(codes)
        self.calls: list[list[str]] = []
        self.timeouts: list[float | None] = []
        self.during = during

    def __call__(self, argv: Any, cwd: Path, timeout: float | None) -> wf.RunResult:
        self.calls.append(list(argv))
        self.timeouts.append(timeout)
        if self.during:
            self.during()
        return wf.RunResult(self.codes.pop(0) if self.codes else 0, "BRIEF: do it", "")


def todo_ticket(store: TownhallStorage) -> str:
    tid = store.create_ticket("B01", "Poll me").id
    for stage in (Stage.DISCUSS, Stage.PLANNING, Stage.TODO):
        store.move_ticket("B01", tid, stage)
    return tid


def complete_ticket(store: TownhallStorage, **frontmatter: str) -> str:
    """A Complete ticket whose index.md carries `frontmatter` from creation on."""
    tid = store.create_ticket("B01", "Merge me").id
    index = store.get_ticket("B01", tid).path / "index.md"
    extra = "".join(f'{key}: "{value}"\n' for key, value in frontmatter.items())
    index.write_text(
        index.read_text(encoding="utf-8").replace("---\n", "---\n" + extra, 1),
        encoding="utf-8",
    )
    for stage in (Stage.DISCUSS, Stage.PLANNING, Stage.TODO, Stage.EXECUTE):
        store.move_ticket("B01", tid, stage)
    submit(store, tid)
    store.move_ticket("B01", tid, Stage.COMPLETE, "approved")
    return tid


def test_poller_disabled_exits_zero(store: TownhallStorage) -> None:
    complete_ticket(store, branch="th/1", target_branch="main")
    todo_ticket(store)
    fake, lines = FakeClaude(), []
    assert wf.run_poller(store.root, runner=fake, once=True, echo=lines.append) == 0
    assert fake.calls == [] and "disabled" in lines[0]
    assert wf.TriagePoller(store.root, runner=fake).tick() == [] and fake.calls == []


def test_poller_claims_triages_and_dispatches(store: TownhallStorage) -> None:
    enable_claude(store)
    tid, notes = todo_ticket(store), []
    seen: list[Any] = []
    fake = FakeClaude(during=lambda: seen.append(store.get_ticket("B01", tid)))
    notify = lambda *a, **k: notes.append(a[1:]) or True
    assert (
        wf.run_poller(store.root, runner=fake, notify=notify, once=True, echo=print)
        == 0
    )
    triage, orchestrate = fake.calls
    assert triage[:2] == ["claude", "-p"] and f"ticket {tid} on board B01" in triage[2]
    assert triage[3:] == ["--model", "haiku", "--permission-mode", "auto"]
    assert (
        orchestrate[3:5] == ["--model", "sonnet"] and "BRIEF: do it" in orchestrate[2]
    )
    # Claimed (and moved) before triage ran; released afterwards.
    assert seen[0].stage is Stage.EXECUTE and seen[0].claimed_by == wf.POLLER_AGENT_ID
    summary = store.get_ticket("B01", tid)
    assert summary.stage is Stage.EXECUTE and summary.claimed_by is None
    assert notes == [("B01", tid, "Todo", "Execute", "claimed for triage")]
    assert fake.timeouts == [1800.0, 1800.0]


def test_concurrent_pollers_triage_a_ticket_once(store: TownhallStorage) -> None:
    """Both pollers saw the ticket in Todo; only the one that claims it triages."""
    enable_claude(store)
    tid = todo_ticket(store)
    stale = store.get_ticket("B01", tid)
    other = FakeClaude()
    second = wf.TriagePoller(store.root, runner=other, notify=lambda *a, **k: False)
    raced: list[bool] = []
    first = wf.TriagePoller(
        store.root,
        runner=FakeClaude(
            during=lambda: raced.append(
                second.triage(load_config(store.root), "B01", stale)
            )
        ),
        notify=lambda *a, **k: False,
    )
    assert first.tick() == [tid]
    assert raced == [False, False] and other.calls == []


def test_poller_triage_failure_is_not_retried(
    store: TownhallStorage, caplog: pytest.LogCaptureFixture
) -> None:
    enable_claude(store, auto_mode=False)
    tid = todo_ticket(store)
    fake = FakeClaude(1)
    poller = wf.TriagePoller(store.root, runner=fake, notify=lambda *a, **k: False)
    assert poller.tick() == [] and poller.tick() == []
    assert len(fake.calls) == 1 and "--permission-mode" not in fake.calls[0]
    summary = store.get_ticket("B01", tid)
    assert summary.stage is Stage.EXECUTE and summary.claimed_by is None
    assert "triage failed" in caplog.text


@pytest.mark.parametrize("fail_on_call", [1, 2])
def test_poller_runner_exception_releases_the_claim(
    store: TownhallStorage,
    caplog: pytest.LogCaptureFixture,
    fail_on_call: int,
) -> None:
    enable_claude(store, auto_mode=False)
    tid = todo_ticket(store)
    calls: list[int] = []

    def runner(argv: Any, cwd: Path, timeout: float | None) -> wf.RunResult:
        calls.append(1)
        if len(calls) == fail_on_call:
            raise OSError("boom")
        return wf.RunResult(0, "triage output", "")

    poller = wf.TriagePoller(store.root, runner=runner, notify=lambda *a, **k: False)
    poller.tick()
    poller.tick()  # not retried
    assert len(calls) == fail_on_call
    summary = store.get_ticket("B01", tid)
    assert summary.stage is Stage.EXECUTE and summary.claimed_by is None


def test_render_prompt_keeps_unknown_placeholders() -> None:
    assert wf.render_prompt("{{a}} {{ b }} {{c}}", {"a": "1", "b": "2"}) == "1 2 {{c}}"


def test_subprocess_runner_times_out_and_reports_missing_binaries(
    tmp_path: Path,
) -> None:
    slow = [sys.executable, "-c", "import time; time.sleep(5)"]
    started = time.monotonic()
    assert wf.subprocess_runner(slow, tmp_path, 0.3).returncode == 124
    assert time.monotonic() - started < 3
    assert wf.subprocess_runner(["no-such-binary-xyz"], tmp_path, 1).returncode == 127


# ------------------------------------------------------------------ auto-merge


def test_merge_runs_once_and_records_the_outcome(store: TownhallStorage) -> None:
    enable_claude(store, auto_merge=True)
    tid = complete_ticket(store, branch="th/1001-limits", target_branch="main")
    fake = FakeClaude()
    poller = wf.TriagePoller(store.root, runner=fake, notify=lambda *a, **k: False)
    poller.tick()
    poller.tick()
    wf.TriagePoller(store.root, runner=fake).tick()  # a restarted poller
    (argv,) = fake.calls
    assert argv[3:] == ["--model", "haiku", "--permission-mode", "auto"]
    assert f"ticket {tid}" in argv[2] and "branch th/1001-limits into main" in argv[2]
    folder = store.get_ticket("B01", tid).path
    assert (
        (folder / ".merge").read_text(encoding="utf-8").startswith("completed (exit 0)")
    )
    handoff = (folder / "HANDOFF.md").read_text(encoding="utf-8")
    assert "## Merge, " in handoff and "`th/1001-limits` into `main`" in handoff
    assert "BRIEF: do it" in handoff
    assert all("HANDOFF" not in str(f.file) for f in store.lint_ticket("B01", tid))


def test_failed_merge_is_recorded_and_not_retried(store: TownhallStorage) -> None:
    enable_claude(store, auto_merge=True)
    tid = complete_ticket(store, branch="th/1", target_branch="main")
    fake = FakeClaude(1)
    poller = wf.TriagePoller(store.root, runner=fake)
    poller.tick()
    poller.tick()
    assert len(fake.calls) == 1
    folder = store.get_ticket("B01", tid).path
    assert (folder / ".merge").read_text(encoding="utf-8").startswith("failed (exit 1)")
    assert "- Result: failed (exit 1)" in (folder / "HANDOFF.md").read_text(
        encoding="utf-8"
    )


def test_merge_runner_error_is_recorded(store: TownhallStorage) -> None:
    enable_claude(store, auto_merge=True)
    tid = complete_ticket(store, branch="th/1", target_branch="main")

    def broken(argv: Any, cwd: Path, timeout: float | None) -> wf.RunResult:
        raise OSError("boom")

    wf.TriagePoller(store.root, runner=broken).tick()
    handoff = (store.get_ticket("B01", tid).path / "HANDOFF.md").read_text(
        encoding="utf-8"
    )
    assert "failed (exit 1)" in handoff and "runner raised OSError: boom" in handoff


def test_merge_is_skipped_when_auto_merge_is_off(
    store: TownhallStorage, caplog: pytest.LogCaptureFixture
) -> None:
    enable_claude(store)  # enabled = true, auto_merge stays false
    tid = complete_ticket(store, branch="th/1", target_branch="main")
    fake = FakeClaude()
    poller = wf.TriagePoller(store.root, runner=fake)
    poller.tick()
    poller.tick()
    assert fake.calls == []
    assert not (store.get_ticket("B01", tid).path / ".merge").exists()
    assert caplog.text.count("auto_merge is false") == 1  # noticed once


@pytest.mark.parametrize(
    ("frontmatter", "why"),
    [
        ({}, "no branch or target_branch"),
        ({"branch": "th/1"}, "no target_branch"),
        ({"branch": "-rf", "target_branch": "main"}, "unsafe branch name"),
        ({"branch": "main", "target_branch": "main"}, "the same"),
    ],
)
def test_merge_skips_without_safe_branches(
    store: TownhallStorage,
    caplog: pytest.LogCaptureFixture,
    frontmatter: dict[str, str],
    why: str,
) -> None:
    enable_claude(store, auto_merge=True)
    tid = complete_ticket(store, **frontmatter)
    fake = FakeClaude()
    poller = wf.TriagePoller(store.root, runner=fake)
    poller.tick()
    poller.tick()
    assert fake.calls == []
    assert not (store.get_ticket("B01", tid).path / ".merge").exists()
    assert caplog.text.count(why) == 1  # noticed once, not every pass


# ------------------------------------------------------------- real Temporal


@pytest.fixture
async def temporal_client() -> Any:
    address = os.environ.get("AGENTVILLE_TEST_TEMPORAL_ADDRESS")
    if address:
        from temporalio.client import Client as TemporalClient

        yield await TemporalClient.connect(address)
        return
    try:
        env = await asyncio.wait_for(WorkflowEnvironment.start_local(), 120)
    except (RuntimeError, TimeoutError) as exc:
        pytest.skip(f"No Temporal dev server available: {exc}")
    try:
        yield env.client
    finally:
        await env.shutdown()


async def test_workflow_end_to_end_on_server(
    temporal_client: Any, store: TownhallStorage
) -> None:
    tid = store.create_ticket("B01", f"E2E {uuid.uuid4().hex[:6]}").id
    async with wf.build_worker(temporal_client, store.root):
        handle = await wf.signal_with_start(
            temporal_client,
            store.root,
            "B01",
            tid,
            "move",
            wf.MoveSignal("Discuss", "go"),
        )
        for target in ("Planning", "Todo", "Execute"):
            await handle.signal("move", wf.MoveSignal(target, "go"))
        await _until(handle, "Execute")
        submit(store, tid)
        await handle.signal("sync")
        await _until(handle, "Review")
        await handle.signal("move", wf.MoveSignal("Complete", "ship"))
        result = await asyncio.wait_for(handle.result(), 30)
    assert result["stage"] == "Complete" and result["removed"] is False
    assert store.get_ticket("B01", tid).stage is Stage.COMPLETE


async def test_removed_ticket_completes_the_workflow_on_server(
    temporal_client: Any, store: TownhallStorage
) -> None:
    tid = store.create_ticket("B01", f"Gone {uuid.uuid4().hex[:6]}").id
    async with wf.build_worker(temporal_client, store.root):
        handle = await wf.signal_with_start(
            temporal_client, store.root, "B01", tid, "sync"
        )
        await _until(handle, "Backlog")
        shutil.rmtree(store.get_ticket("B01", tid).path)  # e.g. a git checkout
        await handle.signal("move", wf.MoveSignal("Discuss", "go"))
        result = await asyncio.wait_for(handle.result(), 30)
    assert result["removed"] is True and result["stage"] == "Backlog"
    assert "ticket removed" in result["history"][-1]["note"]


async def _until(handle: Any, stage: str) -> None:
    for _ in range(100):
        if await handle.query("stage") == stage:
            return
        await asyncio.sleep(0.1)
    raise AssertionError(f"workflow never reached {stage}")
