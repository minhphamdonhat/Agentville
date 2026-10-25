"""Townhall FastMCP sub-server: the agent-facing tools of specification section 9.

Tools are defined here with short names. The root server mounts this server with
``namespace="townhall"``, so agents see ``townhall_<name>``.
"""

from __future__ import annotations

import dataclasses
import functools
import logging
from collections.abc import Callable, Mapping
from enum import Enum
from pathlib import Path, PurePath
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from agentville.core.errors import PageBudgetError, TownhallError
from agentville.townhall.storage import (
    QuestionInput,
    QuestionOption,
    Stage,
    TaskStatus,
    TownhallStorage,
)

_log = logging.getLogger(__name__)

NAMESPACE = "townhall"
Notifier = Callable[..., Any]
"""``notifier(root, board_id, ticket_id, from_stage, to_stage, reason)``."""
TOOL_NAMES = (
    "list_tickets",
    "pick_ticket",
    "get_ticket_pack",
    "write_page",
    "list_tasks",
    "create_task",
    "update_task_status",
    "request_inputs",
    "get_handoff",
    "submit_review",
    "move_ticket",
)
"""Short tool names; the public names carry the ``townhall_`` prefix."""

INSTRUCTIONS = (
    "Townhall is the project's file-based Kanban board. Tickets move through "
    "Backlog, Discuss, Planning, Need Inputs, Todo, Execute, Review and Complete. "
    "Pages must pass the readability linter: findings come back in the result."
)


class QuestionOptionModel(BaseModel):
    """One answer option of a question."""

    key: str = Field(description="Short id: lower-case letters, digits, '-' or '_'.")
    label: str = Field(
        description="What the user sees. Add '(Recommended)' to the preferred option."
    )
    description: str = Field(default="", description="One sentence on the trade-off.")


class QuestionModel(BaseModel):
    """One question for the user (specification section 6.3)."""

    header: str = Field(description="Short chip label, a few words.")
    title: str = Field(description="The full question, ending with a question mark.")
    tldr: str = Field(
        description="One or two sentences: why it is asked and the trade-off."
    )
    context: str = Field(
        description="Markdown: what the plan or code says now and why it is not enough."
    )
    options: list[QuestionOptionModel] = Field(
        description="Two to four distinct options."
    )
    slug: str | None = Field(
        default=None,
        description="File-name slug; derived from the header when omitted.",
    )
    multi_select: bool = Field(default=False, description="Allow more than one option.")
    allow_other: bool = Field(default=True, description="Allow a free-text answer.")

    def to_storage(self) -> QuestionInput:
        return QuestionInput(
            header=self.header,
            title=self.title,
            tldr=self.tldr,
            context=self.context,
            options=[
                QuestionOption(o.key, o.label, o.description) for o in self.options
            ],
            slug=self.slug,
            multi_select=self.multi_select,
            allow_other=self.allow_other,
        )


# ------------------------------------------------------------------- serialisation


def to_plain(value: Any, root: Path | None = None) -> Any:
    """Turn storage results into JSON-serialisable data.

    Dataclasses become dicts, enums their value, tuples lists and paths strings
    (relative to `root` when they sit under it).
    """
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            f.name: to_plain(getattr(value, f.name), root)
            for f in dataclasses.fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, PurePath):
        if root is not None:
            try:
                return Path(value).relative_to(root).as_posix()
            except ValueError:
                pass
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): to_plain(v, root) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_plain(v, root) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _tool_error(exc: TownhallError) -> ToolError:
    message = str(exc)
    if isinstance(exc, PageBudgetError):
        lines = [f"- {f.file}:{f.line} [{f.rule}] {f.message}" for f in exc.findings]
        message = "\n".join([message, "Fix these findings and retry:", *lines])
    return ToolError(message)


def _guard[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """Map Townhall errors to MCP tool errors with their message intact."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except TownhallError as exc:
            raise _tool_error(exc) from exc

    return wrapper


# ------------------------------------------------------------------------ server


def build_townhall_server(
    root: Path | str | None = None, *, notifier: Notifier | None = None
) -> FastMCP:
    """Build the Townhall sub-server for the project at `root`.

    `notifier` replaces `agentville.townhall.workflows.notify_move` (tests).
    """
    storage = TownhallStorage(root)
    base = storage.root

    def plain(value: Any) -> Any:
        return to_plain(value, base)

    def notify(
        board_id: str,
        ticket_id: str,
        target: Stage,
        reason: str,
        expected_from: Stage | None,
    ) -> None:
        """The one hook after every stage change: tell the ticket's workflow.

        Called only after the storage change succeeded. Best effort: it gives up
        within about a second and never fails the tool when Temporal is down.
        """
        try:
            send = notifier
            if send is None:
                from agentville.townhall.workflows import notify_move as send
            send(
                base,
                board_id,
                ticket_id,
                expected_from.value if expected_from else None,
                target.value,
                reason,
            )
        except Exception:  # noqa: BLE001 - the move is on disk; the signal is optional
            _log.debug("Workflow notification failed.", exc_info=True)

    server = FastMCP(NAMESPACE, instructions=INSTRUCTIONS)

    @server.tool
    @_guard
    def list_tickets(board_id: str, stage: str | None = None) -> dict[str, Any]:
        """List a board's ticket summaries, optionally only those in one stage.

        Each summary has id, title, stage, priority, claim holder, open question
        count and task progress.
        """
        tickets = storage.list_tickets(board_id, stage)
        return {"board_id": board_id, "count": len(tickets), "tickets": plain(tickets)}

    @server.tool
    @_guard
    def pick_ticket(
        board_id: str,
        from_stage: str,
        to_stage: str,
        agent_id: str,
        ttl_minutes: int = 60,
    ) -> dict[str, Any]:
        """Atomically claim the lowest-numbered eligible ticket in `from_stage` and move it to `to_stage`.

        Eligible means unclaimed or holding an expired claim. The claim lasts
        `ttl_minutes`. Returns `picked: false` when nothing is eligible.
        """
        result = storage.pick_ticket(
            board_id, agent_id, from_stage, to_stage, ttl_minutes
        )
        if result is None:
            return {
                "picked": False,
                "message": f"No eligible ticket in {from_stage} on board {board_id}.",
            }
        notify(board_id, result.ticket.id, result.to_stage, "picked", result.from_stage)
        return {"picked": True, **plain(result)}

    @server.tool
    @_guard
    def get_ticket_pack(
        board_id: str, ticket_id: str, include_agent_files: bool = True
    ) -> dict[str, Any]:
        """Load a ticket: summary and every Markdown page in reading order.

        With `include_agent_files` the result also carries HANDOFF.md, DRAFT.md
        and review/diff.patch when they exist.
        """
        return plain(
            storage.get_ticket_pack(
                board_id, ticket_id, include_agent_files=include_agent_files
            )
        )

    @server.tool
    @_guard
    def write_page(
        board_id: str, ticket_id: str, rel_path: str, content: str
    ) -> dict[str, Any]:
        """Lint and write a page under draft/, plan/ or execution/, or GLOSSARY.md or DRAFT.md.

        `content` is the full page with frontmatter. When the linter finds errors
        nothing is written: `written` is false and `findings` says what to fix.
        Warnings never block.
        """
        result = storage.write_page(board_id, ticket_id, rel_path, content)
        data = plain(result)
        if not result.written:
            data["message"] = "Page not written: fix the error findings and retry."
        return data

    @server.tool
    @_guard
    def list_tasks(board_id: str, ticket_id: str) -> dict[str, Any]:
        """List a ticket's tasks (tasks/task-NN-*.md) with status and target files."""
        tasks = storage.list_tasks(board_id, ticket_id)
        return {"ticket_id": ticket_id, "count": len(tasks), "tasks": plain(tasks)}

    @server.tool
    @_guard
    def create_task(
        board_id: str,
        ticket_id: str,
        file_name: str,
        title: str,
        order: int,
        target_files: list[str],
        body_markdown: str,
    ) -> dict[str, Any]:
        """Create tasks/task-NN-slug.md and register it in the ticket index.

        `file_name` looks like task-01-short-name.md. `body_markdown` starts with
        a tl;dr and must not start with an H1; the heading is added for you.
        """
        return plain(
            storage.create_task(
                board_id,
                ticket_id,
                file_name,
                title,
                order,
                target_files,
                body_markdown,
            )
        )

    @server.tool
    @_guard
    def update_task_status(
        board_id: str,
        ticket_id: str,
        file_name: str,
        status: Literal["todo", "in_progress", "done"],
    ) -> dict[str, Any]:
        """Set a task's status. `done` ticks its checkboxes; the index is synced."""
        return plain(
            storage.update_task_status(
                board_id, ticket_id, file_name, TaskStatus(status)
            )
        )

    @server.tool
    @_guard
    def request_inputs(
        board_id: str,
        ticket_id: str,
        source_stage: Literal["Planning", "Execute"],
        handoff_markdown: str,
        questions: list[QuestionModel],
    ) -> dict[str, Any]:
        """Stop and ask the user: write HANDOFF.md and the question files, then move the ticket to Need Inputs.

        `handoff_markdown` must let a fresh agent resume: what is done, what is
        next and what the questions block. Your claim is released. Stop work
        after this call.
        """
        result = storage.request_inputs(
            board_id,
            ticket_id,
            source_stage,
            handoff_markdown,
            [q.to_storage() for q in questions],
        )
        notify(
            board_id, ticket_id, result.stage, "inputs requested", Stage(source_stage)
        )
        return plain(result)

    @server.tool
    @_guard
    def get_handoff(board_id: str, ticket_id: str) -> dict[str, Any]:
        """Read HANDOFF.md and the answered (and pending) questions so you can resume.

        `source_stage` says where the ticket was before it needed inputs.
        """
        return plain(storage.get_handoff(board_id, ticket_id))

    @server.tool
    @_guard
    def submit_review(
        board_id: str,
        ticket_id: str,
        summary_markdown: str,
        evidence_markdown: str,
        diff_patch: str,
    ) -> dict[str, Any]:
        """Write the review summary, evidence and diff.patch, then move the ticket from Execute to Review.

        Every task must be done first. Pass a page body or a full page for each
        markdown argument; the linter applies.
        """
        result = storage.submit_review(
            board_id, ticket_id, summary_markdown, evidence_markdown, diff_patch
        )
        notify(board_id, ticket_id, result.to_stage, result.reason, result.from_stage)
        return plain(result)

    @server.tool
    @_guard
    def move_ticket(
        board_id: str, ticket_id: str, target_stage: str, reason: str = ""
    ) -> dict[str, Any]:
        """Move a ticket to `target_stage` if the state machine allows it.

        Need Inputs and Review are entered only through request_inputs and
        submit_review. `reason` is returned for the log, not stored.
        """
        result = storage.move_ticket(board_id, ticket_id, target_stage, reason)
        notify(board_id, ticket_id, result.to_stage, reason, result.from_stage)
        return plain(result)

    return server
