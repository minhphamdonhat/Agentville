"""CliRunner tests for the `agentville` Townhall command tree."""

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from agentville.townhall.board.storage import (
    QuestionInput,
    QuestionOption,
    Stage,
    TownhallStorage,
)
from agentville.townhall.cli.main import app

runner = CliRunner()

TLDR = "**tl;dr:** This page states one topic. It stays short and plain. Readers get the point fast."
SUMMARY = f"{TLDR}\n\n## Slices\n\n| Slice | Status | Summary |\n|---|---|---|\n| T1 | done | Pool |\n"
EVIDENCE = f"{TLDR}\n\n## Runs\n\n| Command | Exit Code | Duration | Summary |\n|---|---|---|---|\n| `pytest` | 0 | 1s | ok |\n"


class Project:
    """A temporary project with board B01, plus helpers to drive the CLI."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.storage = TownhallStorage(root)

    def run(self, *args: str, input: str | None = None):
        return runner.invoke(app, ["--root", str(self.root), *args], input=input)

    def ticket(self, title: str = "Rate limiting", stage: str = "Backlog") -> str:
        return self.storage.create_ticket("B01", title, stage=stage).id

    def advance(self, ticket: str, *stages: str) -> None:
        for stage in stages:
            self.storage.move_ticket("B01", ticket, stage)

    def ticket_dir(self, ticket: str) -> Path:
        return self.storage.get_ticket("B01", ticket).path


@pytest.fixture(autouse=True)
def _no_visual(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep a host $VISUAL from overriding the $EDITOR the edit tests set."""
    monkeypatch.delenv("VISUAL", raising=False)


@pytest.fixture
def project(tmp_path: Path) -> Project:
    result = runner.invoke(app, ["--root", str(tmp_path), "init"])
    assert result.exit_code == 0, result.output
    proj = Project(tmp_path)
    assert proj.run("create", "B01", "--name", "Main board").exit_code == 0
    return proj


def tk(*parts: str, ticket: str = "1001") -> tuple[str, ...]:
    """Arguments for a command on ticket `ticket` of board B01."""
    return ("B01", "tickets", ticket, *parts)


def fake_module(
    monkeypatch: pytest.MonkeyPatch, name: str, **attrs: Any
) -> types.ModuleType:
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


# --------------------------------------------------------------------------- init


def test_init_creates_the_umbrella_and_is_idempotent(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "Initialised .agentville/" in result.output
    assert (tmp_path / ".agentville" / "config.toml").is_file()
    assert (tmp_path / ".agentville/townhall/_template/GLOSSARY.md").is_file()
    again = runner.invoke(app, ["init", str(tmp_path)])
    assert again.exit_code == 0 and "Already initialised" in again.output


def test_init_uses_the_root_option_and_reports_a_file_path(tmp_path: Path) -> None:
    ok = runner.invoke(app, ["--root", str(tmp_path), "init"])
    assert ok.exit_code == 0 and (tmp_path / ".agentville").is_dir()
    blocker = tmp_path / "plain-file"
    blocker.write_text("x", encoding="utf-8")
    bad = runner.invoke(app, ["init", str(blocker)])
    assert bad.exit_code == 1 and bad.output.startswith("Error:")


def test_root_is_found_by_walking_up_to_agentville(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    project.ticket()
    nested = project.root / "src" / "deep"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    result = runner.invoke(app, ["B01", "tickets", "list", "--compact"])
    assert result.exit_code == 0 and "1001 [Backlog]" in result.output


# --------------------------------------------------------------------------- boards


def test_townhall_list_shows_boards(project: Project) -> None:
    project.ticket()
    table = project.run("list")
    assert (
        table.exit_code == 0 and "B01" in table.output and "Main board" in table.output
    )
    data = json.loads(project.run("list", "--json").output)
    assert data == [{"id": "B01", "name": "Main board", "tickets": 1}]


def test_townhall_list_with_no_boards(tmp_path: Path) -> None:
    runner.invoke(app, ["init", str(tmp_path)])
    result = runner.invoke(app, ["--root", str(tmp_path), "list"])
    assert result.exit_code == 0 and "No boards yet" in result.output


def test_townhall_create_board_and_rejects_duplicates(project: Project) -> None:
    ok = project.run("create", "B02", "--name", "Second")
    assert ok.exit_code == 0 and "Created board B02" in ok.output
    dup = project.run("create", "B02", "--name", "Again")
    assert dup.exit_code == 1 and "already exists" in dup.output
    bad = project.run("create", "bad id!", "--name", "x")
    assert bad.exit_code == 1 and "not a valid board id" in bad.output


# --------------------------------------------------------------------------- tickets


def test_tickets_create_then_list_in_every_format(project: Project) -> None:
    created = project.run(
        "B01",
        "tickets",
        "create",
        "Add rate limiting",
        "--priority",
        "high",
    )
    assert created.exit_code == 0 and "B01-1001 in Backlog" in created.output
    project.run("B01", "tickets", "create", "Second", "--stage", "Discuss")

    table = project.run("B01", "tickets", "list")
    assert table.exit_code == 0 and "Add rate limiting" in table.output

    compact = project.run("B01", "tickets", "list", "--compact")
    assert compact.output.splitlines() == [
        "1001 [Backlog] high - Add rate limiting",
        "1002 [Discuss] medium - Second",
    ]

    data = json.loads(
        project.run("B01", "tickets", "list", "--json").output
    )
    assert [t["id"] for t in data] == ["1001", "1002"]
    assert set(data[0]) == {
        "id", "board_id", "title", "stage", "status", "priority", "labels", "updated",
        "claimed_by", "claim_expires_at", "source_stage", "open_questions",
        "tasks_done", "tasks_total",
    }  # fmt: skip

    only = project.run(
        "B01", "tickets", "list", "--stage", "discuss", "--compact"
    )
    assert only.output.splitlines() == ["1002 [Discuss] medium - Second"]


def test_tickets_list_and_create_errors(project: Project) -> None:
    empty = project.run("B01", "tickets", "list")
    assert empty.exit_code == 0 and "No tickets." in empty.output
    bad_stage = project.run("B01", "tickets", "list", "--stage", "Nope")
    assert bad_stage.exit_code == 1 and "Unknown stage" in bad_stage.output
    bad_priority = project.run(
        "B01", "tickets", "create", "T", "--priority", "urgent"
    )
    assert (
        bad_priority.exit_code == 1 and "Priority must be one of" in bad_priority.output
    )
    no_board = project.run("B99", "tickets", "list")
    assert no_board.exit_code == 1 and "Board B99 does not exist" in no_board.output


def test_help_works_at_every_dynamic_level(project: Project) -> None:
    for args, expected in [
        (("--help",), "create"),
        (("B01", "--help"), "tickets"),
        (("B01", "tickets", "--help"), "create"),
        (("B01", "tickets", "1001", "--help"), "questions"),
        (("B01", "tickets", "1001", "tasks", "--help"), "delete"),
        (("B01", "tickets", "1001", "pick", "--help"), "--claim"),
    ]:
        result = project.run(*args)
        assert result.exit_code == 0 and expected in result.output, args
    assert (
        "B01 tickets 1001"
        in project.run("B01", "tickets", "1001", "--help").output
    )


# --------------------------------------------------------------------------- show / view


def test_show_renders_the_ticket_and_pages(project: Project) -> None:
    project.ticket("Rate limiting")
    default = project.run(*tk("show"))
    assert default.exit_code == 0
    assert "B01-1001" in default.output and "Rate limiting" in default.output

    page = project.run(*tk("show", "--page", "plan/plan-01-context.md"))
    assert page.exit_code == 0 and "Fixed decisions" in page.output
    assert "B01-1001" not in page.output  # a page alone has no ticket card

    raw = project.run(*tk("show", "--raw"))
    assert (
        raw.output.startswith("---\nid:")
        and "# Ticket 1001: Rate limiting" in raw.output
    )


def test_show_json_has_ticket_pages_and_page(project: Project) -> None:
    project.ticket()
    data = json.loads(project.run(*tk("show", "--json")).output)
    assert data["ticket"]["id"] == "1001"
    assert "index.md" in [p["rel_path"] for p in data["pages"]] and "page" not in data
    one = json.loads(
        project.run(*tk("show", "--json", "--page", "plan/plan-01-context.md")).output
    )
    assert one["page"]["rel_path"] == "plan/plan-01-context.md"
    assert one["page"]["body"].lstrip().startswith("# Context")
    assert one["page"]["frontmatter"]["order"] == 20


def test_show_agent_files_and_errors(project: Project) -> None:
    project.ticket()
    handoff = project.run(*tk("show", "--raw", "--page", "HANDOFF.md"))
    assert handoff.exit_code == 0 and "Agent-only resume log" in handoff.output
    missing = project.run(*tk("show", "--page", "nope.md"))
    assert missing.exit_code == 1 and "Page 'nope.md' not found" in missing.output
    unknown = project.run(*tk("show", ticket="9999"))
    assert unknown.exit_code == 1 and "Ticket B01-9999 does not exist" in unknown.output
    clash = project.run(*tk("show", "--view", "--json"))
    assert clash.exit_code == 1 and "cannot be combined" in clash.output


def test_show_view_and_view_launch_the_viewer(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    project.ticket()
    calls: list[tuple[Any, ...]] = []

    def run_viewer(
        storage: TownhallStorage, board_id: str, ticket_id: str, page: str | None = None
    ) -> None:
        calls.append((storage.root, board_id, ticket_id, page))

    fake_module(monkeypatch, "agentville.townhall.board.viewer", run_viewer=run_viewer)
    assert project.run(*tk("show", "--view", "--page", "index.md")).exit_code == 0
    assert project.run(*tk("view")).exit_code == 0
    assert calls == [
        (project.root, "B01", "1001", "index.md"),
        (project.root, "B01", "1001", None),
    ]


def test_view_surfaces_the_real_import_error_and_unknown_ticket(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    project.ticket()
    monkeypatch.setitem(sys.modules, "agentville.townhall.board.viewer", None)
    broken = project.run(*tk("view"))
    assert broken.exit_code == 1
    assert isinstance(broken.exception, ImportError)
    assert "agentville.townhall.board.viewer" in str(broken.exception)
    unknown = project.run(*tk("view", ticket="4242"))
    assert unknown.exit_code == 1 and "does not exist" in unknown.output


# --------------------------------------------------------------------------- questions


def ask(project: Project, *questions: QuestionInput) -> str:
    ticket = project.ticket("Needs answers", stage="Planning")
    project.storage.request_inputs(
        "B01", ticket, "Planning", "Waiting on answers.", list(questions)
    )
    return ticket


def question(slug: str, **overrides: Any) -> QuestionInput:
    values: dict[str, Any] = {
        "header": "Failure mode",
        "title": "How should it fail?",
        "tldr": "The limiter needs a fallback. Failing open keeps uptime. Failing closed keeps protection.",
        "context": "The pool times out after 50ms.",
        "options": [
            QuestionOption("fail_open", "Fail open", "Let requests through."),
            QuestionOption("fail_closed", "Fail closed", "Return 503."),
        ],
        "slug": slug,
    }
    values.update(overrides)
    return QuestionInput(**values)


def test_questions_single_select_by_number_and_key(project: Project) -> None:
    ticket = ask(project, question("first"), question("second"))
    result = project.run(*tk("questions", ticket=ticket), input="2\nfail_open\n")
    assert result.exit_code == 0, result.output
    assert "Fail open - Let requests through." in result.output
    assert "Answered 2 of 2 questions." in result.output
    answered = {
        q.file_name: q.selected for q in project.storage.list_questions("B01", ticket)
    }
    assert answered == {
        "q-01-first.md": ("fail_closed",),
        "q-02-second.md": ("fail_open",),
    }


def test_questions_other_and_multi_select(project: Project) -> None:
    ticket = ask(
        project,
        question("freeform"),
        question("several", multi_select=True, allow_other=True),
    )
    result = project.run(
        *tk("questions", ticket=ticket),
        input="o\nUse a circuit breaker\n1, 2, o\nAlso log it\n",
    )
    assert result.exit_code == 0, result.output
    first, second = project.storage.list_questions("B01", ticket)
    assert (first.selected, first.other_text) == ((), "Use a circuit breaker")
    assert (second.selected, second.other_text) == (
        ("fail_open", "fail_closed"),
        "Also log it",
    )


def test_questions_reprompt_on_bad_input_and_skip_on_blank(project: Project) -> None:
    ticket = ask(project, question("one"), question("two", allow_other=False))
    result = project.run(*tk("questions", ticket=ticket), input="9\n1 2\n1\n\n")
    assert result.exit_code == 0, result.output
    assert "'9' is not one of the choices." in result.output
    assert "This question takes one answer only." in result.output
    assert (
        "Skipped q-02-two.md." in result.output and "Answered 1 of 2" in result.output
    )
    states = {
        q.file_name: q.status for q in project.storage.list_questions("B01", ticket)
    }
    assert states == {"q-01-one.md": "answered", "q-02-two.md": "pending"}


def test_questions_without_pending_or_without_input(project: Project) -> None:
    quiet = project.ticket()
    none_pending = project.run(*tk("questions", ticket=quiet))
    assert (
        none_pending.exit_code == 0 and "No pending questions." in none_pending.output
    )
    ticket = ask(project, question("one"))
    aborted = project.run(*tk("questions", ticket=ticket), input="")
    assert aborted.exit_code != 0  # input ran out mid-prompt
    assert project.storage.list_questions("B01", ticket)[0].status == "pending"


# --------------------------------------------------------------------------- review


def in_review(project: Project) -> str:
    ticket = project.ticket("Ship it", stage="Execute")
    project.storage.create_task(
        "B01",
        ticket,
        "task-01-ship.md",
        "Ship it",
        30,
        ["src/ship.py"],
        f"{TLDR}\n\n## Todo\n\n- [ ] one\n",
    )
    project.storage.update_task_status("B01", ticket, "task-01", "done")
    project.storage.submit_review(
        "B01", ticket, SUMMARY, EVIDENCE, "diff --git a/x b/x\n+new"
    )
    return ticket


def test_review_inspect_approve_and_reject(project: Project) -> None:
    approved, rejected = in_review(project), in_review(project)
    look = project.run(*tk("review", ticket=approved))
    assert look.exit_code == 0 and "review/review-01-summary.md" in look.output
    assert "2 lines" in look.output

    ok = project.run(*tk("review", "--approve", ticket=approved))
    assert ok.exit_code == 0 and "Review -> Complete" in ok.output
    assert project.storage.get_ticket("B01", approved).stage is Stage.COMPLETE

    no_reason = project.run(*tk("review", "--reject", ticket=rejected))
    assert no_reason.exit_code == 1 and "--reason" in no_reason.output
    bad = project.run(
        *tk("review", "--reject", "--reason", "Tests missing", ticket=rejected)
    )
    assert bad.exit_code == 0 and "Review -> Discuss (Tests missing)" in bad.output
    assert project.storage.get_ticket("B01", rejected).stage is Stage.DISCUSS


def test_review_errors(project: Project) -> None:
    ticket = project.ticket()
    early = project.run(*tk("review", "--approve", ticket=ticket))
    assert early.exit_code == 1 and "only a ticket in Review" in early.output
    both = project.run(
        *tk("review", "--approve", "--reject", "--reason", "x", ticket=ticket)
    )
    assert both.exit_code == 1 and "not both" in both.output
    nothing = project.run(*tk("review", ticket=ticket))
    assert nothing.exit_code == 0 and "No review pages yet." in nothing.output


# --------------------------------------------------------------------------- move / pick / release


def test_move_follows_the_state_machine(project: Project) -> None:
    ticket = project.ticket()
    ok = project.run(*tk("move", "discuss", "--reason", "agreed", ticket=ticket))
    assert ok.exit_code == 0 and "Backlog -> Discuss (agreed)" in ok.output
    bad = project.run(*tk("move", "Complete", ticket=ticket))
    assert bad.exit_code == 1 and "cannot move to Complete" in bad.output


def test_pick_and_release(project: Project) -> None:
    ticket = project.ticket()
    picked = project.run(
        *tk(
            "pick",
            "--claim",
            "agent-a",
            "--from",
            "Backlog",
            "--to",
            "Discuss",
            "--ttl",
            "30",
            ticket=ticket,
        )
    )
    assert picked.exit_code == 0 and "claimed by agent-a" in picked.output
    held = project.storage.get_ticket("B01", ticket)
    assert (held.stage, held.claimed_by) == (Stage.DISCUSS, "agent-a")

    other = project.run(*tk("release", "--claim", "agent-b", ticket=ticket))
    assert other.exit_code == 1 and "claimed by agent-a" in other.output
    freed = project.run(*tk("release", "--claim", "agent-a", ticket=ticket))
    assert freed.exit_code == 0 and "Released B01-1001" in freed.output
    assert project.storage.get_ticket("B01", ticket).claimed_by is None


def test_pick_errors(project: Project) -> None:
    ticket = project.ticket()
    wrong = project.run(
        *tk("pick", "--claim", "a", "--from", "Todo", "--to", "Execute", ticket=ticket)
    )
    assert wrong.exit_code == 1 and "is in Backlog, not Todo" in wrong.output
    illegal = project.run(
        *tk(
            "pick",
            "--claim",
            "a",
            "--from",
            "Backlog",
            "--to",
            "Execute",
            ticket=ticket,
        )
    )
    assert illegal.exit_code == 1 and "cannot move Backlog to Execute" in illegal.output
    missing = project.run(*tk("pick", ticket=ticket))
    assert missing.exit_code == 2  # usage error: --claim, --from, --to are required


# --------------------------------------------------------------------------- lint


def test_lint_is_clean_then_reports_errors_and_page_budget_findings(
    project: Project,
) -> None:
    ticket = project.ticket()
    clean = project.run(*tk("lint", ticket=ticket))
    assert clean.exit_code == 0 and "No findings." in clean.output

    (project.ticket_dir(ticket) / "plan" / "plan-01-context.md").write_text(
        '---\ntitle: "Context"\nstatus: "draft"\nupdated: 2026-10-22\norder: 20\n---\n\n# Context\n\nNo summary.\n',
        encoding="utf-8",
    )
    dirty = project.run(*tk("lint", ticket=ticket))
    assert dirty.exit_code == 1 and "TLDR001" in dirty.output
    as_json = json.loads(project.run(*tk("lint", "--json", ticket=ticket)).output)
    assert "TLDR001" in {f["rule"] for f in as_json} and {
        f["severity"] for f in as_json
    } <= {"error", "warning"}


def test_lint_unknown_ticket(project: Project) -> None:
    result = project.run(*tk("lint", ticket="7777"))
    assert result.exit_code == 1 and "does not exist" in result.output


def test_page_budget_errors_print_each_finding(project: Project) -> None:
    ticket = project.ticket()
    bad = project.run(
        *tk(
            "tasks",
            "create",
            "task-01-x.md",
            "--title",
            "X",
            "--body",
            "no tldr here",
            ticket=ticket,
        )
    )
    assert bad.exit_code == 1
    assert (
        bad.output.startswith("Error:")
        and "TLDR001" in bad.output
        and "tasks/task-01-x.md" in bad.output
    )


# --------------------------------------------------------------------------- edit


def make_editor(tmp_path: Path, source: str) -> str:
    """Return an EDITOR command that runs ``source`` as a Python script.

    The script sees the page to edit as ``sys.argv[1]``. Forward slashes keep
    ``shlex.split`` intact on every OS.
    """
    script = tmp_path / "fake_editor.py"
    script.write_text("import sys\n" + source + "\n", encoding="utf-8")
    return f"{Path(sys.executable).as_posix()} {script.as_posix()}"


def test_edit_opens_the_page_in_editor_and_syncs(
    project: Project, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ticket = project.ticket()
    log = tmp_path / "editor.log"
    editor = make_editor(
        tmp_path,
        "from pathlib import Path\n"
        f"Path({log.as_posix()!r}).write_text(sys.argv[1], encoding='utf-8')\n"
        "with open(sys.argv[1], 'a', encoding='utf-8') as page:\n"
        "    page.write('\\nEdited.\\n')",
    )
    monkeypatch.setenv("EDITOR", editor)
    result = project.run(*tk("edit", "plan/plan-01-context.md", ticket=ticket))
    assert result.exit_code == 0, result.output
    target = project.ticket_dir(ticket) / "plan" / "plan-01-context.md"
    assert log.read_text(encoding="utf-8").strip() == str(target.resolve())
    assert target.read_text(encoding="utf-8").endswith("Edited.\n")
    assert "Saved plan/plan-01-context.md." in result.output


def test_edit_defaults_to_index_and_reports_editor_failures(
    project: Project, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ticket = project.ticket()
    log = tmp_path / "editor.log"
    logger = (
        "from pathlib import Path\n"
        f"Path({log.as_posix()!r}).write_text(sys.argv[1], encoding='utf-8')"
    )
    monkeypatch.setenv("EDITOR", make_editor(tmp_path, logger))
    assert project.run(*tk("edit", ticket=ticket)).exit_code == 0
    assert log.read_text(encoding="utf-8").strip().endswith("1001/index.md")

    monkeypatch.setenv("EDITOR", make_editor(tmp_path, "sys.exit(3)"))
    failed = project.run(*tk("edit", ticket=ticket))
    assert failed.exit_code == 1 and "exited with status 3" in failed.output

    monkeypatch.setenv("EDITOR", str(tmp_path / "no-such-editor"))
    absent = project.run(*tk("edit", ticket=ticket))
    assert absent.exit_code == 1 and "Could not start the editor" in absent.output


@pytest.mark.parametrize(
    ("platform", "os_name", "expected"),
    [("win32", "nt", "notepad"), ("linux", "posix", "vi"), ("darwin", "posix", "vi")],
)
def test_edit_falls_back_to_the_platform_editor(
    project: Project,
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    os_name: str,
    expected: str,
) -> None:
    import os
    import subprocess

    from agentville.townhall.board import cli

    ticket = project.ticket()
    calls: list[list[str]] = []

    def fake_run(args: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    with monkeypatch.context() as patched:
        patched.setattr(sys, "platform", platform)
        patched.setattr(os, "name", os_name)
        assert cli._default_editor() == expected
    monkeypatch.setattr(cli, "_default_editor", lambda: expected)
    result = project.run(*tk("edit", ticket=ticket))
    assert result.exit_code == 0, result.output
    assert calls and calls[0][0] == expected

    monkeypatch.setenv("EDITOR", "from-editor")
    monkeypatch.setenv("VISUAL", "from-visual")
    assert project.run(*tk("edit", ticket=ticket)).exit_code == 0
    assert calls[-1][0] == "from-visual"


def test_edit_rejects_missing_and_escaping_paths(
    project: Project, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ticket = project.ticket()
    monkeypatch.setenv("EDITOR", make_editor(tmp_path, "sys.exit(0)"))
    missing = project.run(*tk("edit", "plan/none.md", ticket=ticket))
    assert missing.exit_code == 1 and "does not exist" in missing.output
    escape = project.run(*tk("edit", "../../../../config.toml", ticket=ticket))
    assert escape.exit_code == 1 and "escapes the ticket folder" in escape.output


# --------------------------------------------------------------------------- tasks


def test_tasks_create_list_update_delete(project: Project) -> None:
    ticket = project.ticket()
    empty = project.run(*tk("tasks", "list", ticket=ticket))
    assert empty.exit_code == 0 and "No tasks." in empty.output

    body = f"{TLDR}\n\n## Todo\n\n- [ ] one\n- [ ] two\n"
    created = project.run(
        *tk("tasks", "create", "task-01-redis-pool.md", "--title", "Build the pool",
            "--target", "src/pool.py", "--body", body, ticket=ticket)
    )  # fmt: skip
    assert (
        created.exit_code == 0 and "Created task task-01-redis-pool" in created.output
    )
    default_body = project.run(
        *tk("tasks", "create", "task-02-lua.md", "--title", "Lua script", ticket=ticket)
    )
    assert default_body.exit_code == 0, default_body.output

    table = project.run(*tk("tasks", "list", ticket=ticket))
    assert "task-01-redis-pool" in table.output and "Build the pool" in table.output
    data = json.loads(project.run(*tk("tasks", "list", "--json", ticket=ticket)).output)
    assert [(t["id"], t["status"], t["order"]) for t in data] == [
        ("task-01-redis-pool", "todo", 30),
        ("task-02-lua", "todo", 31),
    ]
    assert data[0]["target_files"] == ["src/pool.py"]

    done = project.run(
        *tk("tasks", "update", "task-01", "--status", "done", ticket=ticket)
    )
    assert done.exit_code == 0 and "task-01-redis-pool is now done" in done.output
    assert "[x] one" in (
        project.ticket_dir(ticket) / "tasks/task-01-redis-pool.md"
    ).read_text(encoding="utf-8")
    assert project.storage.get_ticket("B01", ticket).tasks_done == 1

    deleted = project.run(*tk("tasks", "delete", "task-02", ticket=ticket))
    assert deleted.exit_code == 0 and "Deleted task task-02" in deleted.output
    assert not (project.ticket_dir(ticket) / "tasks/task-02-lua.md").exists()


def test_tasks_read_body_from_stdin(project: Project) -> None:
    ticket = project.ticket()
    result = project.run(
        *tk(
            "tasks",
            "create",
            "task-03-piped.md",
            "--title",
            "Piped",
            "--body",
            "-",
            ticket=ticket,
        ),
        input=f"{TLDR}\n",
    )
    assert result.exit_code == 0, result.output
    assert (project.ticket_dir(ticket) / "tasks/task-03-piped.md").is_file()


def test_tasks_errors(project: Project) -> None:
    ticket = project.ticket()
    bad_name = project.run(
        *tk("tasks", "create", "pool.md", "--title", "T", ticket=ticket)
    )
    assert (
        bad_name.exit_code == 1
        and "must look like task-01-short-name.md" in bad_name.output
    )
    unknown = project.run(
        *tk("tasks", "update", "task-09", "--status", "done", ticket=ticket)
    )
    assert unknown.exit_code == 1 and "not found" in unknown.output
    bad_status = project.run(
        *tk("tasks", "update", "task-09", "--status", "weird", ticket=ticket)
    )
    assert bad_status.exit_code == 2  # rejected by the option's choices
    gone = project.run(*tk("tasks", "delete", "task-09", ticket=ticket))
    assert gone.exit_code == 1 and "not found" in gone.output


# --------------------------------------------------------------------------- engine


def test_engine_mcp_runs_the_server_with_the_chosen_transport(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []
    fake_module(
        monkeypatch,
        "agentville.townhall.mcp.server",
        run=lambda transport="stdio", root=None: seen.append(transport),
    )
    assert project.run("engine", "mcp").exit_code == 0
    assert project.run("engine", "mcp", "--transport", "sse").exit_code == 0
    assert seen == ["stdio", "sse"]
    bad = project.run("engine", "mcp", "--transport", "carrier-pigeon")
    assert bad.exit_code == 2


def test_engine_mcp_runs_the_server_for_the_cli_root(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, Path | None]] = []

    def run(transport: str = "stdio", root: Path | None = None) -> None:
        calls.append((transport, root))

    fake_module(monkeypatch, "agentville.townhall.mcp.server", run=run)
    result = project.run("engine", "mcp", "--transport", "http")
    assert result.exit_code == 0, result.output
    assert calls == [("http", project.root.resolve())]


@pytest.mark.parametrize(
    ("command", "function"), [("worker", "run_worker"), ("poller", "run_poller")]
)
def test_engine_worker_and_poller_receive_the_project_root(
    project: Project, monkeypatch: pytest.MonkeyPatch, command: str, function: str
) -> None:
    roots: list[Path] = []
    fake_module(
        monkeypatch, "agentville.townhall.board.workflows", **{function: roots.append}
    )
    result = project.run("engine", command)
    assert result.exit_code == 0, result.output
    assert roots == [project.root.resolve()]


def test_engine_worker_awaits_async_entry_points(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    roots: list[Path] = []

    async def run_worker(root: Path) -> None:
        roots.append(root)

    fake_module(monkeypatch, "agentville.townhall.board.workflows", run_worker=run_worker)
    assert project.run("engine", "worker").exit_code == 0
    assert roots == [project.root.resolve()]


@pytest.mark.parametrize("command", ["worker", "poller"])
def test_engine_worker_and_poller_surface_the_real_import_error(
    project: Project, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    monkeypatch.setitem(sys.modules, "agentville.townhall.board.workflows", None)
    result = project.run("engine", command)
    assert result.exit_code == 1
    assert isinstance(result.exception, ImportError)
    assert "agentville.townhall.board.workflows" in str(result.exception)


# --------------------------------------------------------------------------- root discovery


def test_engine_mcp_and_worker_share_the_root_chosen_by_the_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("AGENTVILLE_ROOT", str(tmp_path / "from-env"))
    seen: dict[str, Path | None] = {}
    fake_module(
        monkeypatch,
        "agentville.townhall.mcp.server",
        run=lambda transport="stdio", root=None: seen.update(mcp=root),
    )
    fake_module(
        monkeypatch,
        "agentville.townhall.board.workflows",
        run_worker=lambda root: seen.update(worker=root),
    )
    assert runner.invoke(app, ["--root", str(other), "engine", "mcp"]).exit_code == 0
    assert runner.invoke(app, ["--root", str(other), "engine", "worker"]).exit_code == 0
    assert seen == {"mcp": other.resolve(), "worker": other.resolve()}
    # Without --root both fall back to the same environment root.
    seen.clear()
    assert runner.invoke(app, ["engine", "mcp"]).exit_code == 0
    assert runner.invoke(app, ["engine", "worker"]).exit_code == 0
    assert seen == {
        "mcp": (tmp_path / "from-env").resolve(),
        "worker": (tmp_path / "from-env").resolve(),
    }


def test_townhall_commands_honour_the_environment_root(
    project: Project, monkeypatch: pytest.MonkeyPatch, tmp_path_factory: Any
) -> None:
    project.ticket("Env ticket")
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    monkeypatch.chdir(elsewhere)
    monkeypatch.setenv("AGENTVILLE_ROOT", str(project.root))
    result = runner.invoke(app, ["B01", "tickets", "list", "--json"])
    assert result.exit_code == 0, result.output
    assert "Env ticket" in result.output
    # A placeholder that was never expanded is ignored, not used as a folder name.
    monkeypatch.setenv("AGENTVILLE_ROOT", "${CLAUDE_PROJECT_DIR}")
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    result = runner.invoke(app, ["list", "--json"])
    assert not (elsewhere / "${CLAUDE_PROJECT_DIR}").exists()


# --------------------------------------------------------------------------- engine notification


class Notified:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> bool:
        self.calls.append((*args, kwargs))
        return True


@pytest.fixture
def notified(monkeypatch: pytest.MonkeyPatch) -> Notified:
    from agentville.townhall.board import workflows

    recorder = Notified()
    monkeypatch.setattr(workflows, "notify_move", recorder)
    return recorder


def test_move_notifies_the_workflow(project: Project, notified: Notified) -> None:
    ticket = project.ticket()
    result = project.run(*tk("move", "Discuss", "--reason", "agreed", ticket=ticket))
    assert result.exit_code == 0, result.output
    assert notified.calls == [
        (project.root, "B01", ticket, "Backlog", "Discuss", "agreed", {})
    ]


def test_a_refused_move_does_not_notify(project: Project, notified: Notified) -> None:
    ticket = project.ticket()
    assert project.run(*tk("move", "Complete", ticket=ticket)).exit_code == 1
    assert notified.calls == []


def test_pick_notifies_the_workflow(project: Project, notified: Notified) -> None:
    ticket = project.ticket()
    picked = project.run(
        *tk(
            "pick", "--claim", "agent-a", "--from", "Backlog", "--to", "Discuss",
            ticket=ticket,
        )
    )  # fmt: skip
    assert picked.exit_code == 0, picked.output
    assert len(notified.calls) == 1
    call = notified.calls[0]
    assert call[:5] == (project.root, "B01", ticket, "Backlog", "Discuss")
    assert "agent-a" in call[5]
    # An ineligible pick notifies nothing.
    assert (
        project.run(
            *tk(
                "pick",
                "--claim",
                "b",
                "--from",
                "Todo",
                "--to",
                "Execute",
                ticket=ticket,
            )
        ).exit_code
        == 1
    )
    assert len(notified.calls) == 1


def test_review_sign_off_notifies_the_workflow(
    project: Project, notified: Notified
) -> None:
    approved, rejected = in_review(project), in_review(project)
    assert project.run(*tk("review", ticket=approved)).exit_code == 0
    assert notified.calls == []  # inspecting moves nothing
    assert project.run(*tk("review", "--approve", ticket=approved)).exit_code == 0
    assert (
        project.run(
            *tk("review", "--reject", "--reason", "Tests missing", ticket=rejected)
        ).exit_code
        == 0
    )
    assert [c[2:6] for c in notified.calls] == [
        (approved, "Review", "Complete", "approved"),
        (rejected, "Review", "Discuss", "Tests missing"),
    ]


def test_cli_succeeds_when_the_hook_is_missing(
    project: Project, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    ticket = project.ticket()
    monkeypatch.setitem(sys.modules, "agentville.townhall.board.workflows", None)
    with caplog.at_level("WARNING"):
        result = project.run(*tk("move", "Discuss", ticket=ticket))
    assert result.exit_code == 0, result.output
    assert project.storage.get_ticket("B01", ticket).stage is Stage.DISCUSS
    assert "Workflow notification unavailable" in caplog.text
