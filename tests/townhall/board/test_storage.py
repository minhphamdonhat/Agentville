"""Tests for Townhall filesystem storage."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import agentville.townhall.board.storage as module
from agentville.townhall.board.markdown_ast import parse_document
from agentville.townhall.board.storage import (
    TRANSITIONS,
    QuestionInput,
    QuestionOption,
    Stage,
    TaskStatus,
    TownhallStorage,
    can_transition,
    parse_stage,
)
from agentville.townhall.core.config import load_config
from agentville.townhall.core.errors import (
    AlreadyExistsError,
    ClaimError,
    InvalidInputError,
    InvalidTransitionError,
    NotFoundError,
    PageBudgetError,
)

NOW = datetime(2026, 10, 22, 9, 0, 0, tzinfo=UTC)
FM = '---\ntitle: "{t}"\nstatus: "draft"\nupdated: 2026-10-22\norder: {o}\n---\n'
TLDR = "**tl;dr:** This page states one topic. It stays short and plain. Readers get the point fast."


class Clock:
    """A settable clock for deterministic tests."""

    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def store(tmp_path: Path, clock: Clock) -> TownhallStorage:
    storage = TownhallStorage(tmp_path, clock=clock, enforce_page_budgets=True)
    storage.init_project()
    storage.create_board("B01", "Main board")
    return storage


@pytest.fixture
def ticket(store: TownhallStorage) -> str:
    return store.create_ticket("B01", "Implement rate limiting").id


def page(title: str, order: int, body: str | None = None) -> str:
    return f"{FM.format(t=title, o=order)}\n# {title}\n\n{body or TLDR}\n"


def question(slug: str = "failure-mode", **overrides: object) -> QuestionInput:
    values: dict[str, object] = {
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
    return QuestionInput(**values)  # type: ignore[arg-type]


def write_plan(store: TownhallStorage, ticket_id: str) -> None:
    """Edit every seeded plan page so it no longer matches the template."""
    for path in sorted((store.get_ticket("B01", ticket_id).path / "plan").glob("*.md")):
        path.write_text(
            path.read_text(encoding="utf-8") + "\nThis plan is agreed.\n",
            encoding="utf-8",
        )


def move_to(store: TownhallStorage, ticket_id: str, *stages: Stage) -> None:
    for stage in stages:
        if stage is Stage.TODO:
            write_plan(store, ticket_id)
        store.move_ticket("B01", ticket_id, stage)


def to_execute(store: TownhallStorage, ticket_id: str) -> None:
    move_to(store, ticket_id, Stage.DISCUSS, Stage.PLANNING, Stage.TODO, Stage.EXECUTE)


def to_review_ready(store: TownhallStorage, ticket_id: str) -> None:
    """Execute with one finished task, so a review may be submitted."""
    to_execute(store, ticket_id)
    make_task(store, ticket_id)
    store.update_task_status("B01", ticket_id, "task-01", "done")


def make_task(
    store: TownhallStorage,
    ticket_id: str,
    name: str = "task-01-pool.md",
    order: int = 30,
) -> None:
    store.create_task(
        "B01",
        ticket_id,
        name,
        "Build the pool",
        order,
        ["src/pool.py"],
        f"{TLDR}\n\n## Todo\n\n- [ ] one\n- [ ] two\n",
    )


# --- state machine --------------------------------------------------------------------


def test_transition_table_matches_the_state_machine() -> None:
    assert can_transition(Stage.BACKLOG, Stage.DISCUSS)
    assert can_transition(Stage.EXECUTE, Stage.REVIEW)
    assert can_transition(Stage.REVIEW, Stage.DISCUSS)
    assert not can_transition(Stage.BACKLOG, Stage.EXECUTE)
    assert TRANSITIONS[Stage.COMPLETE] == frozenset()
    assert parse_stage("need-inputs") is Stage.NEED_INPUTS
    with pytest.raises(InvalidInputError):
        parse_stage("Nonsense")


# --- init and boards ------------------------------------------------------------------


def test_init_project_creates_layout_and_is_idempotent(tmp_path: Path) -> None:
    storage = TownhallStorage(tmp_path)
    first = storage.init_project()
    assert ".agentville/config.toml" in first.created
    assert ".agentville/townhall/_template/plan/plan-01-context.md" in first.created
    assert (tmp_path / ".agentville/townhall/boards").is_dir()
    assert storage.init_project().created == []
    assert load_config(tmp_path).townhall.enforce_page_budgets is True


def test_init_writes_a_gitignore_for_runtime_files(tmp_path: Path) -> None:
    storage = TownhallStorage(tmp_path)
    assert ".agentville/.gitignore" in storage.init_project().created
    lines = (
        (tmp_path / ".agentville/.gitignore").read_text(encoding="utf-8").splitlines()
    )
    for pattern in (".lock", "*.lock", "*.tmp"):
        assert pattern in lines
    # Every runtime file the storage layer can leave behind is covered.
    storage.create_board("B01", "Main")
    ticket = storage.create_ticket("B01", "Ignore me")
    (ticket.path / ".lock").write_text("1", encoding="utf-8")
    (ticket.path.parent.parent / ".tickets.lock").write_text("1", encoding="utf-8")
    (ticket.path / ".index.md.abc123.tmp").write_text("x", encoding="utf-8")


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_gitignore_hides_runtime_files_from_git(tmp_path: Path) -> None:
    storage = TownhallStorage(tmp_path)
    storage.init_project()
    storage.create_board("B01", "Main")
    ticket = storage.create_ticket("B01", "Ignore me")
    (ticket.path / ".lock").write_text("1", encoding="utf-8")
    (ticket.path.parent.parent / ".tickets.lock").write_text("1", encoding="utf-8")
    (ticket.path / ".index.md.abc123.tmp").write_text("x", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for leftover in (
        ticket.path / ".lock",
        ticket.path.parent.parent / ".tickets.lock",
        ticket.path / ".index.md.abc123.tmp",
        ticket.path / ".lock.break",
    ):
        found = subprocess.run(
            ["git", "check-ignore", "-q", str(leftover)], cwd=tmp_path, check=False
        )
        assert found.returncode == 0, leftover.name
    tracked = subprocess.run(
        ["git", "check-ignore", "-q", str(ticket.path / "index.md")],
        cwd=tmp_path,
        check=False,
    )
    assert tracked.returncode == 1


def test_create_and_list_boards(store: TownhallStorage) -> None:
    store.create_board("A02", 'Second "quoted" board')
    boards = store.list_boards()
    assert [b.id for b in boards] == ["A02", "B01"]
    assert store.get_board("A02").name == 'Second "quoted" board'
    assert (store.townhall_dir / "boards/B01/board.toml").read_text(
        encoding="utf-8"
    ) == 'id = "B01"\nname = "Main board"\n'


def test_board_errors(store: TownhallStorage) -> None:
    with pytest.raises(AlreadyExistsError):
        store.create_board("B01", "Again")
    with pytest.raises(InvalidInputError):
        store.create_board("../evil", "x")
    with pytest.raises(NotFoundError):
        store.get_board("Z99")


# --- tickets --------------------------------------------------------------------------


def test_create_ticket_allocates_sequential_ids_and_seeds_the_pack(
    store: TownhallStorage,
) -> None:
    first = store.create_ticket("B01", "First", labels=["backend"], priority="high")
    second = store.create_ticket("B01", "Second")
    assert (first.id, second.id) == ("1001", "1002")
    assert (
        first.stage is Stage.BACKLOG
        and first.priority == "high"
        and first.labels == ("backend",)
    )
    ticket_dir = first.path
    for rel in (
        "index.md",
        "GLOSSARY.md",
        "HANDOFF.md",
        "DRAFT.md",
        "plan/plan-01-context.md",
        "questions/.gitkeep",
    ):
        assert (ticket_dir / rel).exists(), rel
    assert "ticket 1001" in (ticket_dir / "GLOSSARY.md").read_text(encoding="utf-8")
    assert store.create_ticket("B01", "Third").id == "1003"


def test_index_md_follows_the_schema(store: TownhallStorage, ticket: str) -> None:
    text = (store.townhall_dir / f"boards/B01/tickets/{ticket}/index.md").read_text(
        encoding="utf-8"
    )
    doc = parse_document(text)
    assert list(doc.frontmatter or {}) == [
        "id", "board_id", "title", "stage", "status", "priority", "updated", "order",
        "claimed_by", "claim_expires_at", "source_stage", "labels",
    ]  # fmt: skip
    assert "# Ticket 1001: Implement rate limiting" in text
    assert "| Stage | Backlog |" in text and "## Resume" in text
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_ticket_errors_and_unsafe_priority(store: TownhallStorage) -> None:
    with pytest.raises(NotFoundError):
        store.get_ticket("B01", "9999")
    with pytest.raises(InvalidInputError):
        store.get_ticket("B01", "../x")
    with pytest.raises(InvalidInputError):
        store.create_ticket("B01", "x", priority="urgent")
    with pytest.raises(InvalidInputError):
        store.create_ticket("B01", "x", stage="Need Inputs")


def test_list_tickets_filters_by_stage(store: TownhallStorage) -> None:
    a = store.create_ticket("B01", "A").id
    store.create_ticket("B01", "B")
    store.move_ticket("B01", a, "Discuss")
    assert [t.id for t in store.list_tickets("B01")] == ["1001", "1002"]
    assert [t.id for t in store.list_tickets("B01", "Discuss")] == ["1001"]
    assert store.list_tickets("B01", Stage.COMPLETE) == []


# --- pack and pages -------------------------------------------------------------------


def test_get_ticket_pack_is_ordered_by_frontmatter_order(
    store: TownhallStorage, ticket: str
) -> None:
    assert store.write_page("B01", ticket, "plan/plan-02-z.md", page("Zed", 21)).written
    assert store.write_page(
        "B01", ticket, "draft/draft-01-a.md", page("Alpha", 10)
    ).written
    pack = store.get_ticket_pack("B01", ticket)
    paths = [p.rel_path for p in pack.pages]
    assert paths[0] == "index.md"
    assert (
        paths.index("draft/draft-01-a.md")
        < paths.index("plan/plan-01-context.md")
        < paths.index("plan/plan-02-z.md")
    )
    assert paths[-1] == "GLOSSARY.md"
    assert "HANDOFF.md" not in paths and pack.handoff and pack.draft is not None


def test_get_ticket_pack_agent_files_are_optional(
    store: TownhallStorage, ticket: str
) -> None:
    pack = store.get_ticket_pack("B01", ticket, include_agent_files=False)
    assert (pack.handoff, pack.draft, pack.diff_patch) == (None, None, None)


def test_write_page_writes_and_syncs_index(store: TownhallStorage, ticket: str) -> None:
    result = store.write_page(
        "B01", ticket, "draft/draft-01-problem.md", page("Problem", 10).rstrip("\n")
    )
    assert result.written and result.findings == []
    index = (store.get_ticket(" B01".strip(), ticket).path / "index.md").read_text(
        encoding="utf-8"
    )
    assert "- [draft-01-problem.md](./draft/draft-01-problem.md) — Problem" in index


def test_write_page_rejects_lint_failures_when_enforced(
    store: TownhallStorage, ticket: str
) -> None:
    result = store.write_page(
        "B01", ticket, "plan/plan-05-bad.md", "# No frontmatter\n"
    )
    assert not result.written
    assert {f.rule for f in result.findings} >= {"FM001", "TLDR001"}
    assert not (store.get_ticket("B01", ticket).path / "plan/plan-05-bad.md").exists()


def test_write_page_allows_bad_pages_when_budgets_are_off(tmp_path: Path) -> None:
    storage = TownhallStorage(tmp_path, enforce_page_budgets=False)
    storage.init_project()
    storage.create_board("B01", "Main")
    tid = storage.create_ticket("B01", "x").id
    result = storage.write_page("B01", tid, "plan/plan-05-bad.md", "# Bad\n")
    assert result.written and result.findings


def test_write_page_honours_config_flag(tmp_path: Path) -> None:
    storage = TownhallStorage(tmp_path)
    storage.init_project()
    (tmp_path / ".agentville/config.toml").write_text(
        "[townhall]\nenforce_page_budgets = false\n", encoding="utf-8"
    )
    assert storage.enforce_page_budgets is False


@pytest.mark.parametrize(
    "bad",
    [
        "../escape.md",
        "/abs.md",
        "index.md",
        "tasks/task-01-x.md",
        "HANDOFF.md",
        "plan/x.txt",
        "plan",
    ],
)
def test_write_page_refuses_unsafe_or_unowned_paths(
    store: TownhallStorage, ticket: str, bad: str
) -> None:
    with pytest.raises(InvalidInputError):
        store.write_page("B01", ticket, bad, page("X", 1))


def test_write_page_accepts_agent_only_draft(
    store: TownhallStorage, ticket: str
) -> None:
    assert store.write_page("B01", ticket, "DRAFT.md", "just notes").written
    assert store.get_ticket_pack("B01", ticket).draft == "just notes\n"


def test_writes_are_deterministic_and_updated_changes_only_on_change(
    store: TownhallStorage, ticket: str, clock: Clock
) -> None:
    index = store.get_ticket("B01", ticket).path / "index.md"
    store.write_page("B01", ticket, "draft/draft-01-a.md", page("A", 10))
    before = index.read_text(encoding="utf-8")
    clock.now = NOW + timedelta(days=3)
    store.sync_index("B01", ticket)
    store.write_page("B01", ticket, "draft/draft-01-a.md", page("A", 10))
    assert index.read_text(encoding="utf-8") == before
    store.write_page("B01", ticket, "draft/draft-02-b.md", page("B", 11))
    assert "updated: 2026-10-25" in index.read_text(encoding="utf-8")
    assert not list(index.parent.glob(".*.tmp"))


def test_sync_index_keeps_h1_and_tldr_and_regenerates_links(
    store: TownhallStorage, ticket: str
) -> None:
    index = store.get_ticket("B01", ticket).path / "index.md"
    text = index.read_text(encoding="utf-8")
    index.write_text(
        text.replace("## Plan", "## Plan\n\n- [stale](./plan/gone.md) — stale", 1),
        encoding="utf-8",
    )
    store.sync_index("B01", ticket)
    synced = index.read_text(encoding="utf-8")
    assert "gone.md" not in synced and "plan-01-context.md" in synced
    assert (
        "# Ticket 1001: Implement rate limiting" in synced
        and "**tl;dr:** This ticket tracks" in synced
    )


def test_lint_ticket_on_a_fresh_pack_is_clean(
    store: TownhallStorage, ticket: str
) -> None:
    assert store.lint_ticket("B01", ticket) == []


def test_lint_ticket_reports_findings_with_file_names(
    store: TownhallStorage, ticket: str
) -> None:
    (store.get_ticket("B01", ticket).path / "plan/plan-09-x.md").write_text(
        "# Bad\n", encoding="utf-8"
    )
    findings = store.lint_ticket("B01", ticket)
    assert findings and {f.file for f in findings} == {"plan/plan-09-x.md"}


# --- tasks ----------------------------------------------------------------------------


def test_create_and_list_tasks(store: TownhallStorage, ticket: str) -> None:
    make_task(store, ticket)
    make_task(store, ticket, "task-02-lua.md", 31)
    tasks = store.list_tasks("B01", ticket)
    assert [t.file_name for t in tasks] == ["task-01-pool.md", "task-02-lua.md"]
    assert tasks[0].status is TaskStatus.TODO and tasks[0].target_files == (
        "src/pool.py",
    )
    body = tasks[0].path.read_text(encoding="utf-8")
    assert "# T1 — Build the pool {#t1}" in body
    index = (store.get_ticket("B01", ticket).path / "index.md").read_text(
        encoding="utf-8"
    )
    assert "- [ ] [task-01-pool.md](./tasks/task-01-pool.md) — Build the pool" in index


def test_create_task_rejects_bad_names_duplicates_and_lint(
    store: TownhallStorage, ticket: str
) -> None:
    make_task(store, ticket)
    with pytest.raises(AlreadyExistsError):
        make_task(store, ticket)
    with pytest.raises(InvalidInputError):
        store.create_task("B01", ticket, "pool.md", "t", 1, [], TLDR)
    with pytest.raises(InvalidInputError):
        store.create_task(
            "B01", ticket, "task-03-x.md", "t", 1, [], f"# Own H1\n\n{TLDR}"
        )
    with pytest.raises(PageBudgetError) as excinfo:
        store.create_task("B01", ticket, "task-04-x.md", "t", 1, [], "no tldr here")
    assert any(f.rule == "TLDR001" for f in excinfo.value.findings)
    assert not (store.get_ticket("B01", ticket).path / "tasks/task-04-x.md").exists()


def test_update_task_status_syncs_checkboxes_and_index(
    store: TownhallStorage, ticket: str, clock: Clock
) -> None:
    make_task(store, ticket)
    done = store.update_task_status("B01", ticket, "task-01-pool.md", "done")
    assert done.status is TaskStatus.DONE and done.completed_at == "2026-10-22"
    text = done.path.read_text(encoding="utf-8")
    assert "- [x] one" in text and "- [ ]" not in text
    summary = store.get_ticket("B01", ticket)
    assert (summary.tasks_done, summary.tasks_total) == (1, 1)
    assert "- [x] [task-01-pool.md]" in (summary.path / "index.md").read_text(
        encoding="utf-8"
    )
    reopened = store.update_task_status(
        "B01", ticket, "task-01", TaskStatus.IN_PROGRESS
    )
    assert reopened.status is TaskStatus.IN_PROGRESS and reopened.completed_at is None
    assert "- [x] one" in reopened.path.read_text(encoding="utf-8")
    store.update_task_status("B01", ticket, "task-01-pool", "todo")
    assert "- [x]" not in reopened.path.read_text(encoding="utf-8")
    with pytest.raises(InvalidInputError):
        store.update_task_status("B01", ticket, "task-01-pool", "finished")
    with pytest.raises(NotFoundError):
        store.update_task_status("B01", ticket, "task-99", "done")


def test_delete_task_removes_file_and_index_entry(
    store: TownhallStorage, ticket: str
) -> None:
    make_task(store, ticket)
    store.delete_task("B01", ticket, "task-01-pool")
    assert store.list_tasks("B01", ticket) == []
    assert "task-01-pool" not in (
        store.get_ticket("B01", ticket).path / "index.md"
    ).read_text(encoding="utf-8")


# --- request_inputs, handoff, answers -------------------------------------------------


def test_request_inputs_writes_everything_and_moves_the_ticket(
    store: TownhallStorage, ticket: str
) -> None:
    to_execute(store, ticket)
    result = store.request_inputs(
        "B01",
        ticket,
        "Execute",
        "# Handoff\n\n- Stage: Need Inputs",
        [question(), question("other", header="Second")],
    )
    assert result.stage is Stage.NEED_INPUTS
    assert [q.file_name for q in result.questions] == [
        "q-01-failure-mode.md",
        "q-02-other.md",
    ]
    summary = store.get_ticket("B01", ticket)
    assert summary.stage is Stage.NEED_INPUTS and summary.source_stage is Stage.EXECUTE
    assert summary.open_questions == 2 and summary.claimed_by is None
    assert (summary.path / "HANDOFF.md").read_text(
        encoding="utf-8"
    ) == "# Handoff\n\n- Stage: Need Inputs\n"
    text = (summary.path / "questions/q-01-failure-mode.md").read_text(encoding="utf-8")
    assert (
        "# Q1 — How should it fail? {#q1}" in text
        and "| `fail_open` | Fail open |" in text
    )
    index = (summary.path / "index.md").read_text(encoding="utf-8")
    assert "- [ ] [q-01-failure-mode.md](./questions/q-01-failure-mode.md)" in index
    assert (
        "| Open | 2 pending questions |" in index and "| Stage | Need Inputs |" in index
    )
    assert "HANDOFF" not in index.split("## Resume")[0]


def test_request_inputs_numbers_continue_and_check_source_stage(
    store: TownhallStorage, ticket: str
) -> None:
    move_to(store, ticket, Stage.DISCUSS, Stage.PLANNING)
    with pytest.raises(InvalidTransitionError):
        store.request_inputs("B01", ticket, "Execute", "h", [question()])
    store.request_inputs("B01", ticket, "Planning", "h", [question()])
    store.answer_question("B01", ticket, "q-01-failure-mode", ["fail_open"])
    store.move_ticket("B01", ticket, "Planning")
    again = store.request_inputs("B01", ticket, Stage.PLANNING, "h", [question("next")])
    assert again.questions[0].file_name == "q-02-next.md"


def test_request_inputs_is_all_or_nothing_on_invalid_content(
    store: TownhallStorage, ticket: str
) -> None:
    move_to(store, ticket, Stage.DISCUSS, Stage.PLANNING)
    bad = question(tldr="One sentence only.")
    with pytest.raises(PageBudgetError):
        store.request_inputs("B01", ticket, "Planning", "handoff", [question(), bad])
    summary = store.get_ticket("B01", ticket)
    assert summary.stage is Stage.PLANNING and summary.open_questions == 0
    assert "No handoff yet" in (summary.path / "HANDOFF.md").read_text(encoding="utf-8")
    with pytest.raises(InvalidInputError):
        store.request_inputs("B01", ticket, "Planning", "h", [])
    with pytest.raises(InvalidInputError):
        store.request_inputs(
            "B01",
            ticket,
            "Planning",
            "h",
            [question(options=[QuestionOption("a", "A")])],
        )
    with pytest.raises(InvalidInputError):
        store.request_inputs("B01", ticket, "Backlog", "h", [question()])


def test_get_handoff_returns_log_and_answered_questions(
    store: TownhallStorage, ticket: str
) -> None:
    to_execute(store, ticket)
    store.request_inputs(
        "B01",
        ticket,
        "Execute",
        "# Handoff\n\nResume here.",
        [question(), question("two", header="Two")],
    )
    store.answer_question("B01", ticket, "q-01-failure-mode.md", ["fail_open"], "note")
    handoff = store.get_handoff("B01", ticket)
    assert (
        "Resume here." in handoff.handoff_markdown
        and handoff.source_stage is Stage.EXECUTE
    )
    assert [q.file_name for q in handoff.answered] == ["q-01-failure-mode.md"]
    assert (
        handoff.answered[0].selected == ("fail_open",)
        and handoff.answered[0].other_text == "note"
    )
    assert [q.file_name for q in handoff.pending] == ["q-02-two.md"]


def test_answer_question_validates_and_records(
    store: TownhallStorage, ticket: str, clock: Clock
) -> None:
    move_to(store, ticket, Stage.DISCUSS, Stage.PLANNING)
    store.request_inputs(
        "B01",
        ticket,
        "Planning",
        "h",
        [
            question(),
            question("multi", header="M", multi_select=True, allow_other=False),
        ],
    )
    with pytest.raises(InvalidInputError):
        store.answer_question("B01", ticket, "q-01-failure-mode", [])
    with pytest.raises(InvalidInputError):
        store.answer_question("B01", ticket, "q-01-failure-mode", ["nope"])
    with pytest.raises(InvalidInputError):
        store.answer_question(
            "B01", ticket, "q-01-failure-mode", ["fail_open", "fail_closed"]
        )
    with pytest.raises(InvalidInputError):
        store.answer_question("B01", ticket, "q-02-multi", ["fail_open"], "other text")
    with pytest.raises(NotFoundError):
        store.answer_question("B01", ticket, "q-09-none", ["fail_open"])
    answered = store.answer_question(
        "B01", ticket, "q-01-failure-mode", [], "something else"
    )
    assert (
        answered.status == "answered" and answered.answered_at == "2026-10-22T09:00:00Z"
    )
    assert answered.other_text == "something else" and answered.selected == ()
    both = store.answer_question(
        "B01", ticket, "q-02-multi", ["fail_open", "fail_closed"]
    )
    assert both.selected == ("fail_open", "fail_closed")
    with pytest.raises(InvalidInputError):
        store.answer_question("B01", ticket, "q-02-multi", ["fail_open"])
    index = (store.get_ticket("B01", ticket).path / "index.md").read_text(
        encoding="utf-8"
    )
    assert "- [x] [q-01-failure-mode.md]" in index and "| Open | None |" in index


def test_question_files_pass_the_linter(store: TownhallStorage, ticket: str) -> None:
    move_to(store, ticket, Stage.DISCUSS, Stage.PLANNING)
    store.request_inputs("B01", ticket, "Planning", "h", [question()])
    assert store.lint_ticket("B01", ticket) == []


# --- review ---------------------------------------------------------------------------

SUMMARY = f"{TLDR}\n\n## Slices\n\n| Slice | Status | Summary |\n|---|---|---|\n| T1 | done | Pool |\n"
EVIDENCE = f"{TLDR}\n\n## Runs\n\n| Command | Exit Code | Duration | Summary |\n|---|---|---|---|\n| `pytest` | 0 | 1s | ok |\n"


def test_submit_review_writes_files_and_moves_to_review(
    store: TownhallStorage, ticket: str
) -> None:
    to_execute(store, ticket)
    make_task(store, ticket)
    store.update_task_status("B01", ticket, "task-01", "done")
    result = store.submit_review(
        "B01", ticket, SUMMARY, EVIDENCE, "diff --git a/x b/x\n+new"
    )
    assert (result.from_stage, result.to_stage) == (Stage.EXECUTE, Stage.REVIEW)
    summary = store.get_ticket("B01", ticket)
    assert summary.stage is Stage.REVIEW
    review = summary.path / "review"
    assert (review / "diff.patch").read_text(
        encoding="utf-8"
    ) == "diff --git a/x b/x\n+new\n"
    doc = parse_document((review / "review-01-summary.md").read_text(encoding="utf-8"))
    assert (
        doc.frontmatter
        and doc.frontmatter["order"] == 50
        and doc.body.startswith("# Review summary")
    )
    assert (
        parse_document(
            (review / "review-02-evidence.md").read_text(encoding="utf-8")
        ).frontmatter["order"]
        == 51
    )  # type: ignore[index]
    index = (summary.path / "index.md").read_text(encoding="utf-8")
    assert "review-01-summary.md" in index and "review-02-evidence.md" in index
    assert (
        store.get_ticket_pack("B01", ticket).diff_patch == "diff --git a/x b/x\n+new\n"
    )


def test_submit_review_accepts_full_pages(store: TownhallStorage, ticket: str) -> None:
    to_review_ready(store, ticket)
    full = f"{FM.format(t='Summary', o=50)}\n# Summary\n\n{TLDR}\n"
    store.submit_review("B01", ticket, full, EVIDENCE, "d")
    assert (
        (store.get_ticket("B01", ticket).path / "review/review-01-summary.md")
        .read_text(encoding="utf-8")
        .startswith('---\ntitle: "Summary"')
    )


def test_submit_review_guards(store: TownhallStorage, ticket: str) -> None:
    with pytest.raises(InvalidTransitionError):
        store.submit_review("B01", ticket, SUMMARY, EVIDENCE, "d")
    to_execute(store, ticket)
    make_task(store, ticket)
    with pytest.raises(InvalidInputError):
        store.submit_review("B01", ticket, SUMMARY, EVIDENCE, "d")
    with pytest.raises(PageBudgetError):
        store.submit_review(
            "B01", ticket, "no tldr", EVIDENCE, "d", require_tasks_done=False
        )
    assert store.get_ticket("B01", ticket).stage is Stage.EXECUTE
    assert not (store.get_ticket("B01", ticket).path / "review/diff.patch").exists()


def test_submit_review_needs_at_least_one_task(
    store: TownhallStorage, ticket: str
) -> None:
    to_execute(store, ticket)
    with pytest.raises(InvalidInputError, match="no tasks"):
        store.submit_review("B01", ticket, SUMMARY, EVIDENCE, "d")
    assert store.get_ticket("B01", ticket).stage is Stage.EXECUTE
    assert not (store.get_ticket("B01", ticket).path / "review/diff.patch").exists()
    # The explicit opt-out still works.
    store.submit_review("B01", ticket, SUMMARY, EVIDENCE, "d", require_tasks_done=False)
    assert store.get_ticket("B01", ticket).stage is Stage.REVIEW


# --- moves ----------------------------------------------------------------------------


def test_move_ticket_follows_the_state_machine(
    store: TownhallStorage, ticket: str
) -> None:
    result = store.move_ticket("B01", ticket, "Discuss", "agreed")
    assert (result.from_stage, result.to_stage, result.reason) == (
        Stage.BACKLOG,
        Stage.DISCUSS,
        "agreed",
    )
    assert store.get_ticket("B01", ticket).status == "draft"
    with pytest.raises(InvalidTransitionError) as excinfo:
        store.move_ticket("B01", ticket, "Execute")
    assert "Allowed: Planning" in str(excinfo.value)
    move_to(store, ticket, Stage.PLANNING, Stage.TODO, Stage.EXECUTE)
    assert store.get_ticket("B01", ticket).status == "active"


def test_move_ticket_guards_special_entries_and_plan_lint(
    store: TownhallStorage, ticket: str
) -> None:
    move_to(store, ticket, Stage.DISCUSS, Stage.PLANNING)
    with pytest.raises(InvalidTransitionError):
        store.move_ticket("B01", ticket, "Need Inputs")
    (store.get_ticket("B01", ticket).path / "plan/plan-01-context.md").write_text(
        "# broken\n", encoding="utf-8"
    )
    with pytest.raises(PageBudgetError):
        store.move_ticket("B01", ticket, "Todo")
    assert store.get_ticket("B01", ticket).stage is Stage.PLANNING


def test_planning_to_todo_rejects_untouched_template_pages(
    store: TownhallStorage, ticket: str
) -> None:
    move_to(store, ticket, Stage.DISCUSS, Stage.PLANNING)
    with pytest.raises(InvalidTransitionError) as excinfo:
        store.move_ticket("B01", ticket, "Todo")
    message = str(excinfo.value)
    for name in ("plan-01-context", "plan-02-architecture", "plan-03-verification"):
        assert name in message
    assert store.get_ticket("B01", ticket).stage is Stage.PLANNING

    plan = store.get_ticket("B01", ticket).path / "plan"
    for rel in ("plan-01-context.md", "plan-02-architecture.md"):
        (plan / rel).write_text(
            (plan / rel).read_text(encoding="utf-8") + "\nAgreed.\n", encoding="utf-8"
        )
    with pytest.raises(InvalidTransitionError) as excinfo:  # one page still untouched
        store.move_ticket("B01", ticket, "Todo")
    assert "plan-03-verification" in str(excinfo.value)
    assert "plan-01-context" not in str(excinfo.value)

    (plan / "plan-03-verification.md").unlink()  # deleting the page it does not need
    store.move_ticket("B01", ticket, "Todo")
    assert store.get_ticket("B01", ticket).stage is Stage.TODO


def test_untouched_check_ignores_frontmatter_and_trailing_space(
    store: TownhallStorage, ticket: str
) -> None:
    move_to(store, ticket, Stage.DISCUSS, Stage.PLANNING)
    plan = store.get_ticket("B01", ticket).path / "plan"
    page = plan / "plan-01-context.md"
    page.write_text(
        page.read_text(encoding="utf-8").replace("updated:", "updated: 2030-01-01 #")
        + "\n\n",
        encoding="utf-8",
    )
    with pytest.raises(InvalidTransitionError, match="plan-01-context"):
        store.move_ticket("B01", ticket, "Todo")


def test_move_ticket_blocks_leaving_need_inputs_with_pending_questions(
    store: TownhallStorage, ticket: str
) -> None:
    to_execute(store, ticket)
    store.request_inputs("B01", ticket, "Execute", "h", [question()])
    with pytest.raises(InvalidTransitionError):
        store.move_ticket("B01", ticket, "Execute")
    store.answer_question("B01", ticket, "q-01", ["fail_open"])
    with pytest.raises(InvalidTransitionError):
        store.move_ticket("B01", ticket, "Todo")
    store.move_ticket("B01", ticket, "Execute")
    summary = store.get_ticket("B01", ticket)
    assert summary.stage is Stage.EXECUTE and summary.source_stage is None


def test_review_can_complete_or_return_to_discuss(
    store: TownhallStorage, ticket: str
) -> None:
    to_review_ready(store, ticket)
    store.submit_review("B01", ticket, SUMMARY, EVIDENCE, "d")
    store.move_ticket("B01", ticket, "Discuss", "scope rework")
    other = store.create_ticket("B01", "Other").id
    to_review_ready(store, other)
    store.submit_review("B01", other, SUMMARY, EVIDENCE, "d")
    store.move_ticket("B01", other, "Complete")
    assert store.get_ticket("B01", other).status == "done"
    with pytest.raises(InvalidTransitionError):
        store.move_ticket("B01", other, "Discuss")


# --- pick and release -----------------------------------------------------------------


def test_pick_ticket_claims_and_advances(store: TownhallStorage, ticket: str) -> None:
    store.move_ticket("B01", ticket, "Discuss")
    picked = store.pick_ticket("B01", "agent-1", "Discuss", "Planning", ttl_minutes=30)
    assert picked is not None
    assert (
        picked.ticket.stage is Stage.PLANNING and picked.ticket.claimed_by == "agent-1"
    )
    assert picked.claim_expires_at == "2026-10-22T09:30:00Z"
    assert picked.ticket.claim_expires_at == "2026-10-22T09:30:00Z"
    assert not (picked.ticket.path / ".lock").exists()


def test_pick_ticket_skips_claimed_and_returns_none_when_empty(
    store: TownhallStorage,
) -> None:
    first = store.create_ticket("B01", "A").id
    second = store.create_ticket("B01", "B").id
    first_pick = store.pick_ticket("B01", "a1", "Backlog", "Discuss")
    second_pick = store.pick_ticket("B01", "a2", "Backlog", "Discuss")
    assert first_pick and first_pick.ticket.id == first
    assert second_pick and second_pick.ticket.id == second
    assert store.pick_ticket("B01", "a3", "Backlog", "Discuss") is None
    # Claimed tickets in the next stage are not eligible until the claim expires or is released.
    assert store.pick_ticket("B01", "a3", "Discuss", "Planning") is None


def test_pick_ticket_reclaims_expired_claims(
    store: TownhallStorage, ticket: str, clock: Clock
) -> None:
    store.move_ticket("B01", ticket, "Discuss")
    store.pick_ticket("B01", "a1", "Discuss", "Planning", ttl_minutes=10)
    write_plan(store, ticket)
    clock.now = NOW + timedelta(minutes=11)
    again = store.pick_ticket("B01", "a2", "Planning", "Todo")
    assert (
        again and again.ticket.claimed_by == "a2" and again.ticket.stage is Stage.TODO
    )


def test_pick_ticket_explicit_ticket_errors(
    store: TownhallStorage, ticket: str
) -> None:
    store.pick_ticket("B01", "a1", "Backlog", "Discuss")
    with pytest.raises(ClaimError):
        store.pick_ticket("B01", "a2", "Discuss", "Planning", ticket_id=ticket)
    with pytest.raises(InvalidTransitionError):
        store.pick_ticket("B01", "a2", "Backlog", "Planning", ticket_id=ticket)
    with pytest.raises(InvalidTransitionError):
        store.pick_ticket("B01", "a2", "Discuss", "Todo")
    with pytest.raises(InvalidInputError):
        store.pick_ticket("B01", " ", "Discuss", "Planning")


def test_release_ticket(store: TownhallStorage, ticket: str, clock: Clock) -> None:
    store.pick_ticket("B01", "a1", "Backlog", "Discuss")
    with pytest.raises(ClaimError):
        store.release_ticket("B01", ticket, "intruder")
    released = store.release_ticket("B01", ticket, "a1")
    assert released.claimed_by is None and released.claim_expires_at is None
    assert released.stage is Stage.DISCUSS
    assert store.release_ticket("B01", ticket, "a1").claimed_by is None  # idempotent
    assert store.pick_ticket("B01", "a2", "Discuss", "Planning") is not None


def test_stale_lock_files_are_ignored(store: TownhallStorage, ticket: str) -> None:
    lock = store.get_ticket("B01", ticket).path / ".lock"
    lock.write_text("999999", encoding="utf-8")
    os.utime(lock, (0, 0))
    assert store.pick_ticket("B01", "a1", "Backlog", "Discuss") is not None


def test_stale_lock_takeover_keeps_mutual_exclusion(tmp_path: Path) -> None:
    lock = tmp_path / ".lock"
    lock.write_text("999999", encoding="utf-8")
    os.utime(lock, (0, 0))
    inside = 0
    peak = 0
    entries = 0
    guard = threading.Lock()
    barrier = threading.Barrier(8)

    def worker() -> None:
        nonlocal inside, peak, entries
        barrier.wait()
        with module._exclusive_lock(lock, wait=20):
            with guard:
                inside += 1
                entries += 1
                peak = max(peak, inside)
            time.sleep(0.01)
            with guard:
                inside -= 1

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert (entries, peak) == (8, 1)
    assert not lock.exists()
    assert not list(tmp_path.glob(".lock.*"))


def test_break_stale_lock_never_removes_a_fresh_lock(tmp_path: Path) -> None:
    lock = tmp_path / ".lock"
    lock.write_text(
        "1", encoding="utf-8"
    )  # fresh: a second process saw a stale lock, this one replaced it
    assert module._break_stale_lock(lock) is False
    assert lock.read_text(encoding="utf-8") == "1"
    os.utime(lock, (0, 0))
    assert module._break_stale_lock(lock) is True
    assert not lock.exists() and not list(tmp_path.iterdir())
    assert module._break_stale_lock(lock) is False  # nothing left to break


def test_break_stale_lock_puts_back_a_lock_swapped_in_mid_break(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock = tmp_path / ".lock"
    lock.write_text("old", encoding="utf-8")
    os.utime(lock, (0, 0))
    real_identity = module._lock_identity
    calls = 0

    def swapped(path: Path) -> tuple[int, int] | None:
        nonlocal calls
        calls += 1
        if calls == 2:  # the check of the renamed file: pretend it is another lock
            return (-1, -1)
        return real_identity(path)

    monkeypatch.setattr(module, "_lock_identity", swapped)
    assert module._break_stale_lock(lock) is False
    assert lock.exists()
    assert not list(tmp_path.glob(".lock.*"))


def test_a_leftover_break_guard_expires(tmp_path: Path) -> None:
    lock = tmp_path / ".lock"
    lock.write_text("1", encoding="utf-8")
    os.utime(lock, (0, 0))
    guard = tmp_path / ".lock.break"
    guard.write_text("", encoding="utf-8")
    assert module._break_stale_lock(lock) is False  # a live guard: someone else breaks
    os.utime(guard, (0, 0))
    assert module._break_stale_lock(lock) is False  # removes the dead guard
    assert not guard.exists()
    assert module._break_stale_lock(lock) is True


def test_live_lock_makes_a_pick_scan_skip_the_ticket(
    store: TownhallStorage, ticket: str
) -> None:
    (store.get_ticket("B01", ticket).path / ".lock").write_text("1", encoding="utf-8")
    assert store.pick_ticket("B01", "a1", "Backlog", "Discuss") is None
    with pytest.raises(ClaimError):
        _short_wait_pick(store, ticket)


def _short_wait_pick(store: TownhallStorage, ticket: str) -> None:
    original = module.DEFAULT_LOCK_WAIT_SECONDS
    module.DEFAULT_LOCK_WAIT_SECONDS = 0.1
    try:
        store.pick_ticket("B01", "a1", "Backlog", "Discuss", ticket_id=ticket)
    finally:
        module.DEFAULT_LOCK_WAIT_SECONDS = original


def _claim_in_process(args: tuple[str, str, str]) -> str:
    root, ticket, agent = args
    storage = TownhallStorage(root, enforce_page_budgets=True)
    try:
        picked = storage.pick_ticket(
            "B01", agent, "Backlog", "Discuss", ticket_id=ticket
        )
    except ClaimError, InvalidTransitionError:
        return "lost"
    return "won" if picked else "none"


def test_two_processes_cannot_both_claim_a_ticket(
    store: TownhallStorage, ticket: str
) -> None:
    with ProcessPoolExecutor(max_workers=4) as pool:
        outcomes = list(
            pool.map(
                _claim_in_process,
                [(str(store.root), ticket, f"agent-{n}") for n in range(8)],
            )
        )
    assert outcomes.count("won") == 1
    assert outcomes.count("lost") == 7
    assert store.get_ticket("B01", ticket).claimed_by is not None


def test_concurrent_ticket_creation_allocates_unique_ids(
    store: TownhallStorage,
) -> None:
    def make(n: int) -> str:
        return TownhallStorage(store.root).create_ticket("B01", f"T{n}").id

    with ThreadPoolExecutor(max_workers=6) as pool:
        ids = list(pool.map(make, range(12)))
    assert len(set(ids)) == 12 and min(ids) == "1001" and max(ids) == "1012"
