"""Tests for the Townhall MCP tools, through fastmcp's in-memory client."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from agentville.mcp.server import build_server, discover_root
from agentville.townhall.mcp import TOOL_NAMES, build_townhall_server
from agentville.townhall.storage import TownhallStorage

TLDR = "**tl;dr:** This page states one topic. It stays short and plain. Readers get the point fast."
FM = '---\ntitle: "{t}"\nstatus: "draft"\nupdated: 2026-10-22\norder: {o}\n---\n'
SUMMARY = f"{TLDR}\n\n## Result\n\nIt works.\n"
EVIDENCE = (
    f"{TLDR}\n\n## Runs\n\n| Command | Exit Code | Duration | Summary |\n"
    "|---|---|---|---|\n| `pytest` | 0 | 1s | ok |\n"
)
EXPECTED = sorted(f"townhall_{name}" for name in TOOL_NAMES)


@pytest.fixture
def storage(tmp_path: Path) -> TownhallStorage:
    store = TownhallStorage(tmp_path, enforce_page_budgets=True)
    store.init_project()
    store.create_board("B01", "Main board")
    return store


@pytest.fixture
def server(storage: TownhallStorage) -> FastMCP:
    return build_server(storage.root)


@pytest.fixture
def ticket(storage: TownhallStorage) -> str:
    return storage.create_ticket("B01", "Implement rate limiting").id


async def call(server: FastMCP, name: str, **args: Any) -> dict[str, Any]:
    async with Client(server) as client:
        result = await client.call_tool(f"townhall_{name}", args)
    assert isinstance(result.data, dict)
    return result.data


async def fails(server: FastMCP, name: str, **args: Any) -> str:
    async with Client(server) as client:
        with pytest.raises(ToolError) as excinfo:
            await client.call_tool(f"townhall_{name}", args)
    return str(excinfo.value)


def page(title: str, order: int) -> str:
    return f"{FM.format(t=title, o=order)}\n# {title}\n\n{TLDR}\n"


async def test_lists_exactly_the_eleven_townhall_tools(server: FastMCP) -> None:
    async with Client(server) as client:
        tools = await client.list_tools()
    names = sorted(tool.name for tool in tools)
    assert names == EXPECTED
    assert len(names) == 11
    assert all(tool.description for tool in tools)


async def test_round_trip_through_planning_and_handoff(
    server: FastMCP, storage: TownhallStorage, ticket: str
) -> None:
    listed = await call(server, "list_tickets", board_id="B01")
    assert listed["count"] == 1 and listed["tickets"][0]["stage"] == "Backlog"
    assert (await call(server, "list_tickets", board_id="B01", stage="todo"))[
        "count"
    ] == 0

    written = await call(
        server,
        "write_page",
        board_id="B01",
        ticket_id=ticket,
        rel_path="draft/draft-01-problem.md",
        content=page("Problem", 10),
    )
    assert written["written"] is True and written["findings"] == []

    for stage in ("Discuss", "Planning"):
        moved = await call(
            server,
            "move_ticket",
            board_id="B01",
            ticket_id=ticket,
            target_stage=stage,
            reason="go",
        )
        assert moved["to_stage"] == stage and moved["reason"] == "go"

    task = await call(
        server,
        "create_task",
        board_id="B01",
        ticket_id=ticket,
        file_name="task-01-pool.md",
        title="Build the pool",
        order=30,
        target_files=["src/pool.py"],
        body_markdown=f"{TLDR}\n\n## Todo\n\n- [ ] one\n",
    )
    assert task["status"] == "todo" and task["path"].endswith("tasks/task-01-pool.md")
    assert not Path(task["path"]).is_absolute()

    updated = await call(
        server,
        "update_task_status",
        board_id="B01",
        ticket_id=ticket,
        file_name="task-01",
        status="in_progress",
    )
    assert updated["status"] == "in_progress"
    tasks = await call(server, "list_tasks", board_id="B01", ticket_id=ticket)
    assert tasks["count"] == 1 and tasks["tasks"][0]["target_files"] == ["src/pool.py"]

    asked = await call(
        server,
        "request_inputs",
        board_id="B01",
        ticket_id=ticket,
        source_stage="Planning",
        handoff_markdown="# Handoff\n\n- Stage: Need Inputs",
        questions=[
            {
                "header": "Failure mode",
                "title": "How should it fail?",
                "tldr": "The limiter needs a fallback. Open keeps uptime. Closed keeps protection.",
                "context": "The pool times out after 50ms.",
                "options": [
                    {"key": "fail_open", "label": "Fail open", "description": "Allow."},
                    {
                        "key": "fail_closed",
                        "label": "Fail closed",
                        "description": "503.",
                    },
                ],
                "slug": "failure-mode",
            }
        ],
    )
    assert asked["stage"] == "Need Inputs"
    assert asked["questions"][0]["file_name"] == "q-01-failure-mode.md"
    assert storage.get_ticket("B01", ticket).open_questions == 1

    storage.answer_question("B01", ticket, "q-01-failure-mode", ["fail_open"])
    handoff = await call(server, "get_handoff", board_id="B01", ticket_id=ticket)
    assert handoff["source_stage"] == "Planning"
    assert "Need Inputs" in handoff["handoff_markdown"]
    assert handoff["answered"][0]["selected"] == ["fail_open"]
    assert handoff["pending"] == []

    pack = await call(server, "get_ticket_pack", board_id="B01", ticket_id=ticket)
    assert pack["ticket"]["id"] == ticket
    assert pack["handoff"] and any(
        p["rel_path"] == "draft/draft-01-problem.md" for p in pack["pages"]
    )
    bare = await call(
        server,
        "get_ticket_pack",
        board_id="B01",
        ticket_id=ticket,
        include_agent_files=False,
    )
    assert bare["handoff"] is None
    json.dumps(pack)


async def test_pick_ticket_claims_then_reports_nothing_eligible(
    server: FastMCP, ticket: str
) -> None:
    empty = await call(
        server,
        "pick_ticket",
        board_id="B01",
        from_stage="Discuss",
        to_stage="Planning",
        agent_id="agent-1",
    )
    assert empty["picked"] is False and "No eligible ticket" in empty["message"]

    got = await call(
        server,
        "pick_ticket",
        board_id="B01",
        from_stage="Backlog",
        to_stage="Discuss",
        agent_id="agent-1",
        ttl_minutes=30,
    )
    assert got["picked"] is True and got["claimed_by"] == "agent-1"
    assert got["ticket"]["id"] == ticket and got["to_stage"] == "Discuss"


async def test_submit_review_moves_execute_to_review(
    server: FastMCP, storage: TownhallStorage, ticket: str
) -> None:
    relaxed = TownhallStorage(storage.root, enforce_page_budgets=False)
    for stage in ("Discuss", "Planning", "Todo", "Execute"):
        relaxed.move_ticket("B01", ticket, stage)
    relaxed.create_task("B01", ticket, "task-01-x.md", "X", 1, ["x.py"], f"{TLDR}\n")
    relaxed.update_task_status("B01", ticket, "task-01-x.md", "done")
    review = await call(
        server,
        "submit_review",
        board_id="B01",
        ticket_id=ticket,
        summary_markdown=SUMMARY,
        evidence_markdown=EVIDENCE,
        diff_patch="diff --git a/x b/x\n+new",
    )
    assert (review["from_stage"], review["to_stage"]) == ("Execute", "Review")
    assert storage.get_ticket("B01", ticket).stage.value == "Review"


async def test_move_ticket_invalid_transition_is_a_tool_error(
    server: FastMCP, ticket: str
) -> None:
    message = await fails(
        server, "move_ticket", board_id="B01", ticket_id=ticket, target_stage="Complete"
    )
    assert "Complete" in message


async def test_unknown_stage_and_missing_ticket_are_tool_errors(
    server: FastMCP, ticket: str
) -> None:
    assert "Unknown stage" in await fails(
        server, "list_tickets", board_id="B01", stage="nowhere"
    )
    assert await fails(server, "get_ticket_pack", board_id="B01", ticket_id="9999")


async def test_write_page_reports_lint_findings_without_writing(
    server: FastMCP, storage: TownhallStorage, ticket: str
) -> None:
    result = await call(
        server,
        "write_page",
        board_id="B01",
        ticket_id=ticket,
        rel_path="plan/plan-05-bad.md",
        content="# No frontmatter\n",
    )
    assert result["written"] is False and "message" in result
    assert {f["rule"] for f in result["findings"]} >= {"FM001", "TLDR001"}
    assert not (storage.get_ticket("B01", ticket).path / "plan/plan-05-bad.md").exists()


async def test_page_budget_failure_lists_findings_in_the_error(
    server: FastMCP, ticket: str
) -> None:
    message = await fails(
        server,
        "create_task",
        board_id="B01",
        ticket_id=ticket,
        file_name="task-04-x.md",
        title="t",
        order=1,
        target_files=[],
        body_markdown="no tldr here",
    )
    assert "TLDR001" in message and "Fix these findings" in message


async def test_bad_task_status_is_rejected_by_the_schema(
    server: FastMCP, ticket: str
) -> None:
    assert await fails(
        server,
        "update_task_status",
        board_id="B01",
        ticket_id=ticket,
        file_name="task-01",
        status="finished",
    )


def test_discover_root_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    nested = project / "a" / "b"
    nested.mkdir(parents=True)
    (project / ".agentville").mkdir()
    for name in ("AGENTVILLE_ROOT", "CLAUDE_PROJECT_DIR"):
        monkeypatch.delenv(name, raising=False)
    assert discover_root(nested) == project.resolve()
    assert discover_root(tmp_path) == tmp_path.resolve()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "claude"))
    assert discover_root(nested) == (tmp_path / "claude").resolve()
    monkeypatch.setenv("AGENTVILLE_ROOT", str(tmp_path / "explicit"))
    assert discover_root(nested) == (tmp_path / "explicit").resolve()


# ------------------------------------------------------------ workflow notify


class Recorder:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.error = error

    def __call__(self, *args: Any) -> bool:
        self.calls.append(args[1:])
        if self.error:
            raise self.error
        return True


def question_args() -> dict[str, Any]:
    return {
        "header": "Failure mode",
        "title": "How should it fail?",
        "tldr": "The limiter needs a fallback. Failing open keeps uptime. Failing closed keeps protection.",
        "context": "The pool times out after 50ms.",
        "options": [
            {"key": "fail_open", "label": "Fail open (Recommended)"},
            {"key": "fail_closed", "label": "Fail closed"},
        ],
    }


async def tool(server: FastMCP, name: str, **args: Any) -> dict[str, Any]:
    async with Client(server) as client:
        return (await client.call_tool(name, args)).data


async def test_every_stage_change_notifies_once_after_the_write(
    storage: TownhallStorage, ticket: str
) -> None:
    rec = Recorder()
    server = build_townhall_server(storage.root, notifier=rec)
    ids = {"board_id": "B01"}
    await tool(
        server,
        "pick_ticket",
        **ids,
        from_stage="Backlog",
        to_stage="Discuss",
        agent_id="a",
    )
    await tool(
        server,
        "move_ticket",
        **ids,
        ticket_id=ticket,
        target_stage="Planning",
        reason="go",
    )
    await tool(
        server,
        "request_inputs",
        **ids,
        ticket_id=ticket,
        source_stage="Planning",
        handoff_markdown="Paused for a decision.",
        questions=[question_args()],
    )
    assert rec.calls == [
        ("B01", ticket, "Backlog", "Discuss", "picked"),
        ("B01", ticket, "Discuss", "Planning", "go"),
        ("B01", ticket, "Planning", "Need Inputs", "inputs requested"),
    ]
    relaxed = TownhallStorage(storage.root, enforce_page_budgets=False)
    other = relaxed.create_ticket("B01", "Review me").id
    for stage in ("Discuss", "Planning", "Todo", "Execute"):
        relaxed.move_ticket("B01", other, stage)
    relaxed.create_task("B01", other, "task-01-x.md", "X", 1, ["x.py"], f"{TLDR}\n")
    relaxed.update_task_status("B01", other, "task-01-x.md", "done")
    rec.calls.clear()
    await tool(
        server,
        "submit_review",
        **ids,
        ticket_id=other,
        summary_markdown=SUMMARY,
        evidence_markdown=EVIDENCE,
        diff_patch="diff",
    )
    assert rec.calls == [("B01", other, "Execute", "Review", "review submitted")]


async def test_a_rejected_move_does_not_notify(
    storage: TownhallStorage, ticket: str
) -> None:
    rec = Recorder()
    server = build_townhall_server(storage.root, notifier=rec)
    async with Client(server) as client:
        with pytest.raises(ToolError):
            await client.call_tool(
                "move_ticket",
                {"board_id": "B01", "ticket_id": ticket, "target_stage": "Execute"},
            )
    assert rec.calls == []


async def test_a_failing_notifier_never_fails_the_tool(
    storage: TownhallStorage, ticket: str
) -> None:
    rec = Recorder(RuntimeError("temporal exploded"))
    server = build_townhall_server(storage.root, notifier=rec)
    data = await tool(
        server, "move_ticket", board_id="B01", ticket_id=ticket, target_stage="Discuss"
    )
    assert data["to_stage"] == "Discuss" and len(rec.calls) == 1
    assert storage.get_ticket("B01", ticket).stage.value == "Discuss"
