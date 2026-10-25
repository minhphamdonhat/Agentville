"""The `agentville townhall` command tree.

Two levels of the tree are dynamic: `townhall <board_id>` and
`townhall <board_id> tickets <ticket_id>`. Typer has no native dynamic groups, so
each of those two groups is a `TyperGroup` subclass (see `_dynamic_group`) whose
`resolve_command` treats any name that is not a static command as an id. It stores
the id in `ctx.meta` (which every nested context shares) and hands back the child
group, built once from an ordinary Typer app. Help works at every level because the
child is an ordinary group, and the static commands win over ids with the same name.
"""

import json
import logging
import os
import shlex
import subprocess
import sys
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from typer.core import TyperGroup

from agentville.townhall.board.markdown_ast import LintFinding, Severity
from agentville.townhall.board.storage import (
    PRIORITIES,
    Page,
    Question,
    Stage,
    TaskRecord,
    TicketSummary,
    TownhallStorage,
)
from agentville.townhall.core.errors import (
    AgentvilleError,
    InvalidInputError,
    NotFoundError,
)
from agentville.townhall.core.paths import discover_root

LOGGER = logging.getLogger(__name__)

ROOT_META = "agentville.root"
BOARD_META = "agentville.board_id"
TICKET_META = "agentville.ticket_id"

DEFAULT_TASK_ORDER_BASE = 29
DEFAULT_TASK_BODY = (
    "**tl;dr:** This task is one slice of the ticket. "
    "Its scope and done criteria are not written yet. "
    "Fill them in before work starts."
)


# ------------------------------------------------------------------------ plumbing


def project_root(ctx: typer.Context) -> Path:
    """The project root: `--root`, else the shared discovery of `agentville.townhall.core.paths`."""
    return discover_root(ctx.meta.get(ROOT_META))


def notify_stage_change(
    root: Path,
    board_id: str,
    ticket_id: str,
    from_stage: str,
    to_stage: str,
    reason: str = "",
) -> None:
    """Best effort: tell the ticket's workflow about a move already made on disk.

    The CLI succeeds whether or not the engine is installed or running. An import
    problem is logged, not raised.
    """
    try:
        from agentville.townhall.board.workflows import notify_move
    except ImportError as error:
        LOGGER.warning("Workflow notification unavailable: %s", error)
        return
    notify_move(root, board_id, ticket_id, from_stage, to_stage, reason)


def get_storage(ctx: typer.Context) -> TownhallStorage:
    return TownhallStorage(project_root(ctx))


def _console() -> Console:
    return Console()


def _echo_json(data: Any) -> None:
    typer.echo(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _board(ctx: typer.Context) -> str:
    return str(ctx.meta[BOARD_META])


def _ticket(ctx: typer.Context) -> str:
    return str(ctx.meta[TICKET_META])


def _fail(message: str) -> typer.Exit:
    """Print a one-line error and return the exit to raise."""
    typer.echo(f"Error: {message}", err=True)
    return typer.Exit(1)


def format_finding(finding: LintFinding) -> str:
    return f"{finding.file}:{finding.line} {finding.rule} ({finding.severity.value}) {finding.message}"


def _dynamic_group(meta_key: str, build: Callable[[], typer.Typer]) -> type[TyperGroup]:
    """A group class that turns unknown command names into ids for `build()`'s child group."""

    class DynamicGroup(TyperGroup):
        _child: Any = None

        def resolve_command(self, ctx, args):  # type: ignore[no-untyped-def]
            name = args[0] if args else ""
            if name and name not in self.commands and not name.startswith("-"):
                if DynamicGroup._child is None:
                    DynamicGroup._child = typer.main.get_command(build())
                ctx.meta[meta_key] = name
                return name, DynamicGroup._child, args[1:]
            return super().resolve_command(ctx, args)

    return DynamicGroup


# ------------------------------------------------------------------------ rendering


def ticket_to_dict(ticket: TicketSummary) -> dict[str, Any]:
    """Stable machine-readable form of a ticket (the keys never change)."""
    return {
        "id": ticket.id,
        "board_id": ticket.board_id,
        "title": ticket.title,
        "stage": ticket.stage.value,
        "status": ticket.status,
        "priority": ticket.priority,
        "labels": list(ticket.labels),
        "updated": ticket.updated,
        "claimed_by": ticket.claimed_by,
        "claim_expires_at": ticket.claim_expires_at,
        "source_stage": ticket.source_stage.value if ticket.source_stage else None,
        "open_questions": ticket.open_questions,
        "tasks_done": ticket.tasks_done,
        "tasks_total": ticket.tasks_total,
    }


def task_to_dict(task: TaskRecord) -> dict[str, Any]:
    return {
        "id": task.id,
        "file_name": task.file_name,
        "ticket_id": task.ticket_id,
        "title": task.title,
        "status": task.status.value,
        "order": task.order,
        "target_files": list(task.target_files),
        "updated": task.updated,
        "completed_at": task.completed_at,
    }


def _compact_line(ticket: TicketSummary) -> str:
    line = f"{ticket.id} [{ticket.stage.value}] {ticket.priority} - {ticket.title}"
    if ticket.claimed_by:
        line += f" (claimed: {ticket.claimed_by})"
    if ticket.open_questions:
        line += f" (questions: {ticket.open_questions})"
    if ticket.tasks_total:
        line += f" (tasks: {ticket.tasks_done}/{ticket.tasks_total})"
    return line


def _ticket_table(tickets: list[TicketSummary]) -> Table:
    table = Table(show_header=True, header_style="bold")
    for column in ("ID", "Stage", "Priority", "Title", "Claim", "Q", "Tasks"):
        table.add_column(column, overflow="fold")
    for t in tickets:
        table.add_row(
            t.id,
            t.stage.value,
            t.priority,
            t.title,
            t.claimed_by or "",
            str(t.open_questions) if t.open_questions else "",
            f"{t.tasks_done}/{t.tasks_total}" if t.tasks_total else "",
        )
    return table


def _print_ticket_card(ticket: TicketSummary) -> None:
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="bold")
    table.add_column(overflow="fold")
    table.add_row("Ticket", f"{ticket.board_id}-{ticket.id}")
    table.add_row("Title", ticket.title)
    table.add_row("Stage", f"{ticket.stage.value} ({ticket.status})")
    table.add_row("Priority", ticket.priority)
    table.add_row("Updated", ticket.updated)
    if ticket.claimed_by:
        table.add_row(
            "Claimed by", f"{ticket.claimed_by} until {ticket.claim_expires_at}"
        )
    table.add_row("Open questions", str(ticket.open_questions))
    table.add_row("Tasks", f"{ticket.tasks_done}/{ticket.tasks_total} done")
    _console().print(table)


def _page_to_dict(page: Page) -> dict[str, Any]:
    return {
        "rel_path": page.rel_path,
        "title": page.title,
        "order": page.order,
        "frontmatter": page.frontmatter,
    }


def _print_findings(findings: list[LintFinding]) -> None:
    table = Table(show_header=True, header_style="bold")
    for column in ("File", "Line", "Rule", "Severity", "Message"):
        table.add_column(column, overflow="fold")
    for f in findings:
        table.add_row(f.file, str(f.line), f.rule, f.severity.value, f.message)
    _console().print(table)


# ------------------------------------------------------------------------ apps

townhall_app = typer.Typer(
    cls=_dynamic_group(BOARD_META, lambda: board_app),
    help="Townhall Kanban and documentation engine.",
    epilog=(
        "Board commands: agentville townhall BOARD_ID tickets (list | create | TICKET_ID ...). "
        "Use 'agentville townhall BOARD_ID --help' for a board."
    ),
    no_args_is_help=True,
)
board_app = typer.Typer(
    help="Work with the tickets of one board.",
    no_args_is_help=True,
    add_completion=False,
)
tickets_app = typer.Typer(
    cls=_dynamic_group(TICKET_META, lambda: ticket_app),
    help="List and create tickets, or open one by its id.",
    epilog=(
        "Ticket commands: agentville townhall BOARD_ID tickets TICKET_ID "
        "(show | view | questions | review | move | pick | release | lint | edit | tasks). "
        "Use '... tickets TICKET_ID --help' for a ticket."
    ),
    no_args_is_help=True,
)
ticket_app = typer.Typer(
    help="Work with one ticket.", no_args_is_help=True, add_completion=False
)
tasks_app = typer.Typer(
    help="Manage the task slices of a ticket.", no_args_is_help=True
)

board_app.add_typer(tickets_app, name="tickets")
ticket_app.add_typer(tasks_app, name="tasks")


# ------------------------------------------------------------------------ boards


@townhall_app.command("list")
def boards_list(
    ctx: typer.Context,
    as_json: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    """List the boards of the project."""
    storage = get_storage(ctx)
    boards = storage.list_boards()
    rows = [
        {"id": b.id, "name": b.name, "tickets": len(storage.list_tickets(b.id))}
        for b in boards
    ]
    if as_json:
        _echo_json(rows)
        return
    if not rows:
        typer.echo(
            "No boards yet. Create one with: agentville townhall create <board_id> --name <name>"
        )
        return
    table = Table(show_header=True, header_style="bold")
    for column in ("ID", "Name", "Tickets"):
        table.add_column(column)
    for row in rows:
        table.add_row(row["id"], row["name"], str(row["tickets"]))
    _console().print(table)


@townhall_app.command("create")
def boards_create(
    ctx: typer.Context,
    board_id: str = typer.Argument(..., help="Board id, such as B01."),
    name: str = typer.Option(..., "--name", help="Board name."),
) -> None:
    """Create a board."""
    board = get_storage(ctx).create_board(board_id, name)
    typer.echo(f"Created board {board.id}: {board.name}")


# ------------------------------------------------------------------------ tickets


@tickets_app.command("list")
def tickets_list(
    ctx: typer.Context,
    stage: str | None = typer.Option(
        None, "--stage", help="Only tickets in this stage."
    ),
    as_json: bool = typer.Option(False, "--json", help="Print JSON."),
    compact: bool = typer.Option(False, "--compact", help="One line per ticket."),
) -> None:
    """List the tickets of the board."""
    tickets = get_storage(ctx).list_tickets(_board(ctx), stage)
    if as_json:
        _echo_json([ticket_to_dict(t) for t in tickets])
    elif compact:
        for t in tickets:
            typer.echo(_compact_line(t))
    elif not tickets:
        typer.echo("No tickets.")
    else:
        _console().print(_ticket_table(tickets))


@tickets_app.command("create")
def tickets_create(
    ctx: typer.Context,
    title: str = typer.Argument(..., help="Ticket title."),
    stage: str = typer.Option(Stage.BACKLOG.value, "--stage", help="Starting stage."),
    priority: str = typer.Option(
        "medium", "--priority", help=f"One of: {', '.join(PRIORITIES)}."
    ),
) -> None:
    """Create a ticket."""
    ticket = get_storage(ctx).create_ticket(
        _board(ctx), title, stage=stage, priority=priority
    )
    typer.echo(
        f"Created ticket {ticket.board_id}-{ticket.id} in {ticket.stage.value}: {ticket.title}"
    )


# ------------------------------------------------------------------------ one ticket


def _launch_viewer(
    ctx: typer.Context, storage: TownhallStorage, page: str | None
) -> None:
    storage.get_ticket(_board(ctx), _ticket(ctx))  # fail early on an unknown ticket
    from agentville.townhall.board.viewer import run_viewer

    run_viewer(storage, _board(ctx), _ticket(ctx), page=page)


@ticket_app.command("show")
def ticket_show(
    ctx: typer.Context,
    view: bool = typer.Option(False, "--view", help="Open the full-screen viewer."),
    page: str | None = typer.Option(
        None,
        "--page",
        help="Page to show, relative to the ticket, such as plan/plan-01-context.md.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Print JSON."),
    raw: bool = typer.Option(
        False, "--raw", help="Print the page source without rendering."
    ),
) -> None:
    """Show a ticket, or one of its pages."""
    storage = get_storage(ctx)
    board_id, ticket_id = _board(ctx), _ticket(ctx)
    if view:
        if as_json or raw:
            raise _fail("--view cannot be combined with --json or --raw.")
        _launch_viewer(ctx, storage, page)
        return
    pack = storage.get_ticket_pack(board_id, ticket_id)
    chosen: Page | None = None
    agent_text: str | None = None
    wanted = page or "index.md"
    if wanted in ("HANDOFF.md", "DRAFT.md"):
        agent_text = pack.handoff if wanted == "HANDOFF.md" else pack.draft
        if agent_text is None:
            raise NotFoundError(
                f"{wanted} does not exist in ticket {board_id}-{ticket_id}."
            )
    else:
        chosen = next((p for p in pack.pages if p.rel_path == wanted), None)
        if chosen is None:
            known = ", ".join(p.rel_path for p in pack.pages)
            raise NotFoundError(f"Page '{wanted}' not found. Pages: {known}.")
    content = chosen.content if chosen else agent_text or ""
    if as_json:
        data: dict[str, Any] = {
            "ticket": ticket_to_dict(pack.ticket),
            "pages": [_page_to_dict(p) for p in pack.pages],
        }
        if page:
            data["page"] = {
                "rel_path": wanted,
                "frontmatter": chosen.frontmatter if chosen else {},
                "body": chosen.body if chosen else content,
                "content": content,
            }
        _echo_json(data)
    elif raw:
        typer.echo(content, nl=not content.endswith("\n"))
    else:
        console = _console()
        if not page:
            _print_ticket_card(pack.ticket)
            console.print()
        console.print(Markdown(chosen.body if chosen else content))


@ticket_app.command("view")
def ticket_view(ctx: typer.Context) -> None:
    """Open the ticket in the full-screen viewer (alias for 'show --view')."""
    _launch_viewer(ctx, get_storage(ctx), None)


class _Skip(Exception):
    """The reader left a question blank."""


def _ask_question(question: Question) -> tuple[list[str], str | None]:
    """Prompt for one answer. Raises `_Skip` on a blank reply."""
    typer.echo("")
    typer.echo(f"[{question.file_name}] {question.header}: {question.title}")
    for number, option in enumerate(question.options, start=1):
        detail = f" - {option.description}" if option.description else ""
        typer.echo(f"  {number}) {option.label}{detail}")
    if question.allow_other:
        typer.echo("  o) Other (write your own answer)")
    choices = f"1-{len(question.options)}" + (",o" if question.allow_other else "")
    hint = "Pick one or more, comma-separated" if question.multi_select else "Pick one"
    while True:
        reply = typer.prompt(
            f"{hint} [{choices}], blank to skip", default="", show_default=False
        ).strip()
        if not reply:
            raise _Skip
        tokens = [t for t in reply.replace(",", " ").split() if t]
        keys: list[str] = []
        wants_other = False
        problem = None
        by_key = {o.key: o.key for o in question.options}
        for token in tokens:
            if token.isdigit() and 1 <= int(token) <= len(question.options):
                keys.append(question.options[int(token) - 1].key)
            elif token.casefold() in ("o", "other") and question.allow_other:
                wants_other = True
            elif token in by_key:
                keys.append(token)
            else:
                problem = f"'{token}' is not one of the choices."
                break
        if (
            problem is None
            and len(keys) + wants_other > 1
            and not question.multi_select
        ):
            problem = "This question takes one answer only."
        if problem:
            typer.echo(problem)
            continue
        other_text = None
        if wants_other:
            other_text = typer.prompt("Your answer").strip() or None
            if other_text is None and not keys:
                typer.echo("An empty answer is not accepted.")
                continue
        return list(dict.fromkeys(keys)), other_text


@ticket_app.command("questions")
def ticket_questions(ctx: typer.Context) -> None:
    """Answer the pending questions one by one."""
    storage = get_storage(ctx)
    board_id, ticket_id = _board(ctx), _ticket(ctx)
    pending = [
        q for q in storage.list_questions(board_id, ticket_id) if q.status == "pending"
    ]
    if not pending:
        typer.echo("No pending questions.")
        return
    answered = 0
    for question in pending:
        try:
            keys, other_text = _ask_question(question)
        except _Skip:
            typer.echo(f"Skipped {question.file_name}.")
            continue
        storage.answer_question(
            board_id, ticket_id, question.file_name, keys, other_text
        )
        answered += 1
        typer.echo(f"Recorded the answer to {question.file_name}.")
    left = len(pending) - answered
    typer.echo(f"Answered {answered} of {len(pending)} questions.")
    if left == 0:
        typer.echo(
            "Move the ticket on with: agentville townhall <board_id> tickets <ticket_id> move <stage>"
        )


@ticket_app.command("review")
def ticket_review(
    ctx: typer.Context,
    approve: bool = typer.Option(
        False, "--approve", help="Sign off: move the ticket to Complete."
    ),
    reject: bool = typer.Option(
        False, "--reject", help="Send back: move the ticket to Discuss."
    ),
    reason: str | None = typer.Option(
        None, "--reason", help="Why it was rejected (required with --reject)."
    ),
) -> None:
    """Inspect the review pages, or sign them off."""
    storage = get_storage(ctx)
    board_id, ticket_id = _board(ctx), _ticket(ctx)
    if approve and reject:
        raise _fail("Use --approve or --reject, not both.")
    if reject and not (reason and reason.strip()):
        raise _fail('--reject needs --reason "<why>".')
    if approve or reject:
        ticket = storage.get_ticket(board_id, ticket_id)
        if ticket.stage is not Stage.REVIEW:
            raise _fail(
                f"Ticket is in {ticket.stage.value}; only a ticket in Review can be signed off."
            )
        target = Stage.COMPLETE if approve else Stage.DISCUSS
        result = storage.move_ticket(
            board_id, ticket_id, target, (reason or "approved").strip()
        )
        notify_stage_change(
            storage.root,
            board_id,
            ticket_id,
            result.from_stage.value,
            result.to_stage.value,
            result.reason,
        )
        verb = "Approved" if approve else "Rejected"
        typer.echo(
            f"{verb} {board_id}-{ticket_id}: {result.from_stage.value} -> {result.to_stage.value} ({result.reason})"
        )
        return
    pack = storage.get_ticket_pack(board_id, ticket_id)
    pages = [p for p in pack.pages if p.rel_path.startswith("review/")]
    console = _console()
    console.print(f"Ticket {board_id}-{ticket_id} is in {pack.ticket.stage.value}.")
    if not pages:
        console.print("No review pages yet.")
        return
    for page in pages:
        console.rule(page.rel_path)
        console.print(Markdown(page.body))
    if pack.diff_patch:
        console.rule("review/diff.patch")
        console.print(
            f"{len(pack.diff_patch.splitlines())} lines; open the file in the ticket folder to read it."
        )


@ticket_app.command("move")
def ticket_move(
    ctx: typer.Context,
    target_stage: str = typer.Argument(..., help="Stage to move to."),
    reason: str = typer.Option("", "--reason", help="Why the ticket moves."),
) -> None:
    """Move the ticket to another stage."""
    storage = get_storage(ctx)
    result = storage.move_ticket(_board(ctx), _ticket(ctx), target_stage, reason)
    notify_stage_change(
        storage.root,
        _board(ctx),
        result.ticket_id,
        result.from_stage.value,
        result.to_stage.value,
        reason,
    )
    suffix = f" ({result.reason})" if result.reason else ""
    typer.echo(
        f"Moved {_board(ctx)}-{result.ticket_id}: {result.from_stage.value} -> {result.to_stage.value}{suffix}"
    )


@ticket_app.command("pick")
def ticket_pick(
    ctx: typer.Context,
    claim: str = typer.Option(..., "--claim", help="Agent id that takes the claim."),
    from_stage: str = typer.Option(..., "--from", help="Stage the ticket must be in."),
    to_stage: str = typer.Option(..., "--to", help="Stage to advance it to."),
    ttl: int = typer.Option(60, "--ttl", help="Claim lifetime in minutes."),
) -> None:
    """Claim the ticket and advance it."""
    storage = get_storage(ctx)
    result = storage.pick_ticket(
        _board(ctx), claim, from_stage, to_stage, ttl, ticket_id=_ticket(ctx)
    )
    if result is None:
        raise _fail(f"Ticket {_ticket(ctx)} is not eligible to be picked.")
    notify_stage_change(
        storage.root,
        _board(ctx),
        result.ticket.id,
        result.from_stage.value,
        result.to_stage.value,
        f"picked by {claim}",
    )
    typer.echo(
        f"Picked {_board(ctx)}-{result.ticket.id}: {result.from_stage.value} -> {result.to_stage.value}, "
        f"claimed by {result.claimed_by} until {result.claim_expires_at}"
    )


@ticket_app.command("release")
def ticket_release(
    ctx: typer.Context,
    claim: str = typer.Option(..., "--claim", help="Agent id that holds the claim."),
) -> None:
    """Release a claim on the ticket."""
    ticket = get_storage(ctx).release_ticket(_board(ctx), _ticket(ctx), claim)
    typer.echo(f"Released {_board(ctx)}-{ticket.id}.")


@ticket_app.command("lint")
def ticket_lint(
    ctx: typer.Context,
    as_json: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    """Check every page of the ticket against the page budgets."""
    findings = get_storage(ctx).lint_ticket(_board(ctx), _ticket(ctx))
    if as_json:
        _echo_json([f.to_dict() for f in findings])
    elif not findings:
        typer.echo("No findings.")
    else:
        _print_findings(findings)
    if any(f.severity is Severity.ERROR for f in findings):
        raise typer.Exit(1)


def _default_editor() -> str:
    """The editor to start when neither $VISUAL nor $EDITOR is set: notepad on Windows, else vi."""
    return "notepad" if sys.platform == "win32" or os.name == "nt" else "vi"


@ticket_app.command("edit")
def ticket_edit(
    ctx: typer.Context,
    rel_path: str = typer.Argument(
        "index.md", help="Page to edit, relative to the ticket."
    ),
) -> None:
    """Open a page of the ticket in $VISUAL or $EDITOR (vi, or notepad on Windows, when both are unset)."""
    storage = get_storage(ctx)
    board_id, ticket_id = _board(ctx), _ticket(ctx)
    ticket_dir = storage.get_ticket(board_id, ticket_id).path
    target = (ticket_dir / rel_path).resolve()
    if not target.is_relative_to(ticket_dir.resolve()):
        raise InvalidInputError(f"'{rel_path}' escapes the ticket folder.")
    if not target.is_file():
        raise NotFoundError(f"Page '{rel_path}' does not exist.")
    editor = shlex.split(
        os.environ.get("VISUAL") or os.environ.get("EDITOR") or _default_editor()
    )
    try:
        completed = subprocess.run([*editor, str(target)], check=False)
    except OSError as error:
        raise AgentvilleError(
            f"Could not start the editor '{editor[0]}': {error.strerror or error}."
        ) from None
    if completed.returncode != 0:
        raise _fail(f"The editor exited with status {completed.returncode}.")
    storage.sync_index(board_id, ticket_id)
    rel = target.relative_to(ticket_dir.resolve()).as_posix()
    findings = [f for f in storage.lint_ticket(board_id, ticket_id) if f.file == rel]
    typer.echo(f"Saved {rel}.")
    if findings:
        typer.echo(f"{len(findings)} lint finding(s) in {rel}; run 'lint' for details.")


# ------------------------------------------------------------------------ tasks


@tasks_app.command("list")
def tasks_list(
    ctx: typer.Context,
    as_json: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    """List the tasks of the ticket."""
    tasks = get_storage(ctx).list_tasks(_board(ctx), _ticket(ctx))
    if as_json:
        _echo_json([task_to_dict(t) for t in tasks])
    elif not tasks:
        typer.echo("No tasks.")
    else:
        table = Table(show_header=True, header_style="bold")
        for column in ("Task", "Status", "Title", "Order"):
            table.add_column(column, overflow="fold")
        for t in tasks:
            table.add_row(t.id, t.status.value, t.title, str(t.order))
        _console().print(table)


@tasks_app.command("create")
def tasks_create(
    ctx: typer.Context,
    file_name: str = typer.Argument(
        ..., metavar="FILE", help="Task file, such as task-01-api-routes.md."
    ),
    title: str = typer.Option(..., "--title", help="Task title."),
    order: int | None = typer.Option(
        None, "--order", help="Sort order (default: 29 plus the task number)."
    ),
    target: Annotated[
        list[str] | None,
        typer.Option("--target", help="File the task changes; repeat for more."),
    ] = None,
    body: str | None = typer.Option(
        None, "--body", help="Task body starting with a tl;dr; '-' reads stdin."
    ),
) -> None:
    """Create a task slice."""
    text = (
        DEFAULT_TASK_BODY
        if body is None
        else typer.get_text_stream("stdin").read()
        if body == "-"
        else body
    )
    if order is None:
        digits = "".join(
            c for c in file_name.removeprefix("task-").split("-")[0] if c.isdigit()
        )
        order = DEFAULT_TASK_ORDER_BASE + int(digits or 0)
    task = get_storage(ctx).create_task(
        _board(ctx), _ticket(ctx), file_name, title, order, target or [], text
    )
    typer.echo(f"Created task {task.id}: {task.title}")


class _Status(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@tasks_app.command("update")
def tasks_update(
    ctx: typer.Context,
    task_id: Annotated[
        str, typer.Argument(help="Task id, file name or unique prefix.")
    ],
    status: Annotated[_Status, typer.Option("--status", help="New status.")],
) -> None:
    """Set the status of a task."""
    task = get_storage(ctx).update_task_status(
        _board(ctx), _ticket(ctx), task_id, status.value
    )
    typer.echo(f"Task {task.id} is now {task.status.value}.")


@tasks_app.command("delete")
def tasks_delete(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task id, file name or unique prefix."),
) -> None:
    """Delete a task."""
    get_storage(ctx).delete_task(_board(ctx), _ticket(ctx), task_id)
    typer.echo(f"Deleted task {task_id}.")
