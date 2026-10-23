"""Filesystem storage for Townhall: boards, ticket packs, tasks, questions, claims.

Layout under the project root::

    .agentville/townhall/
        _template/                      seed files copied into every new ticket pack
        boards/<board_id>/board.toml    id and name of the board
        boards/<board_id>/tickets/<ticket_id>/
            index.md  GLOSSARY.md  HANDOFF.md  DRAFT.md
            draft/  plan/  questions/  tasks/  execution/  review/

Rules that hold for every write:

* Writes are deterministic: stable YAML key order, one trailing newline and no
  timestamps beyond the frontmatter fields. ``updated`` changes only when the
  file content changes.
* Writes are atomic: content goes to a temp file in the same directory and is
  moved into place with ``os.replace``. Multi-file writes stage every temp file
  first, so a failure before the first rename leaves the pack untouched.
* Mutations of one ticket are serialised by an exclusive lock file
  (``O_CREAT | O_EXCL``), so two processes cannot both claim a ticket.

Ticket ids are decimal strings, unique per board and allocated as
``max(existing) + 1``, starting at ``1001`` (``"1001"``, ``"1002"``, ...).
They are padded to at least four digits.
"""

from __future__ import annotations

import os
import re
import tempfile
import time
import tomllib
import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from agentville.core.config import Config, load_config
from agentville.core.errors import (
    AlreadyExistsError,
    ClaimError,
    InvalidInputError,
    InvalidTransitionError,
    NotFoundError,
    PageBudgetError,
)
from agentville.townhall.markdown_ast import (
    LintFinding,
    has_errors,
    lint_markdown,
    parse_document,
    render_document,
    split_frontmatter,
)

__all__ = [
    "TRANSITIONS",
    "Board",
    "Handoff",
    "InitResult",
    "InputRequestResult",
    "MoveResult",
    "Page",
    "PickResult",
    "Question",
    "QuestionInput",
    "QuestionOption",
    "Stage",
    "TaskRecord",
    "TaskStatus",
    "TicketPack",
    "TicketSummary",
    "TownhallStorage",
    "WritePageResult",
    "can_transition",
    "parse_stage",
]

TOWNHALL_RELATIVE = Path(".agentville") / "townhall"
FIRST_TICKET_NUMBER = 1001
TICKET_PADDING = 4
PRIORITIES = ("low", "medium", "high", "critical")
PACK_SUBDIRECTORIES = ("draft", "plan", "questions", "tasks", "execution", "review")
WRITABLE_PAGE_DIRECTORIES = ("draft", "plan", "execution")
WRITABLE_ROOT_FILES = ("GLOSSARY.md", "DRAFT.md")
STALE_LOCK_SECONDS = 30.0
DEFAULT_LOCK_WAIT_SECONDS = 10.0
DEFAULT_QUESTION_ORDER = 25
REVIEW_SUMMARY_ORDER = 50
REVIEW_EVIDENCE_ORDER = 51

_BOARD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
_TICKET_ID_RE = re.compile(r"^\d{1,12}$")
_TASK_NAME_RE = re.compile(r"^task-(\d+)-[a-z0-9][a-z0-9-]*$")
_QUESTION_NAME_RE = re.compile(r"^q-(\d+)-[a-z0-9][a-z0-9-]*$")
_OPTION_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_CHECKBOX_RE = re.compile(r"^(\s*[-*] )\[[ xX]\]", re.MULTILINE)
_H1_RE = re.compile(r"^# \S", re.MULTILINE)


# ------------------------------------------------------------------------- stages


class Stage(StrEnum):
    """Ticket stages (Townhall's own vocabulary)."""

    BACKLOG = "Backlog"
    DISCUSS = "Discuss"
    PLANNING = "Planning"
    NEED_INPUTS = "Need Inputs"
    TODO = "Todo"
    EXECUTE = "Execute"
    REVIEW = "Review"
    COMPLETE = "Complete"


TRANSITIONS: Mapping[Stage, frozenset[Stage]] = {
    Stage.BACKLOG: frozenset({Stage.DISCUSS}),
    Stage.DISCUSS: frozenset({Stage.PLANNING}),
    Stage.PLANNING: frozenset({Stage.NEED_INPUTS, Stage.TODO}),
    Stage.NEED_INPUTS: frozenset({Stage.PLANNING, Stage.TODO, Stage.EXECUTE}),
    Stage.TODO: frozenset({Stage.EXECUTE}),
    Stage.EXECUTE: frozenset({Stage.NEED_INPUTS, Stage.REVIEW}),
    Stage.REVIEW: frozenset({Stage.COMPLETE, Stage.DISCUSS}),
    Stage.COMPLETE: frozenset(),
}
"""Allowed moves, from the state machine in specification section 8."""

_STATUS_FOR_STAGE: Mapping[Stage, str] = {
    Stage.BACKLOG: "draft",
    Stage.DISCUSS: "draft",
    Stage.PLANNING: "draft",
    Stage.NEED_INPUTS: "blocked",
    Stage.TODO: "ready",
    Stage.EXECUTE: "active",
    Stage.REVIEW: "review",
    Stage.COMPLETE: "done",
}


class TaskStatus(StrEnum):
    """Task progress."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


def parse_stage(value: str | Stage) -> Stage:
    """Parse a stage name, ignoring case and treating ``-`` and ``_`` as spaces."""
    if isinstance(value, Stage):
        return value
    wanted = re.sub(r"[-_\s]+", " ", value).strip().casefold()
    for stage in Stage:
        if stage.value.casefold() == wanted:
            return stage
    names = ", ".join(s.value for s in Stage)
    raise InvalidInputError(f"Unknown stage '{value}'. Stages are: {names}.")


def can_transition(source: Stage, target: Stage) -> bool:
    """True when the state machine allows `source` to `target`."""
    return target in TRANSITIONS[source]


# --------------------------------------------------------------------- dataclasses


@dataclass(frozen=True)
class Board:
    """A board: a named group of tickets."""

    id: str
    name: str
    path: Path


@dataclass(frozen=True)
class TicketSummary:
    """The index.md frontmatter of a ticket, plus counters computed from disk."""

    id: str
    board_id: str
    title: str
    stage: Stage
    status: str
    priority: str
    labels: tuple[str, ...]
    updated: str
    claimed_by: str | None
    claim_expires_at: str | None
    source_stage: Stage | None
    open_questions: int
    tasks_done: int
    tasks_total: int
    path: Path


@dataclass(frozen=True)
class Page:
    """One Markdown page of a pack."""

    rel_path: str
    frontmatter: dict[str, Any]
    body: str
    content: str

    @property
    def order(self) -> int | None:
        value = self.frontmatter.get("order")
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    @property
    def title(self) -> str:
        return str(self.frontmatter.get("title") or self.rel_path)


@dataclass(frozen=True)
class TicketPack:
    """A ticket with its ordered pages and, optionally, its agent-only files."""

    ticket: TicketSummary
    pages: list[Page]
    handoff: str | None = None
    draft: str | None = None
    diff_patch: str | None = None


@dataclass(frozen=True)
class WritePageResult:
    """Outcome of `write_page`. `written` is False when budgets rejected the content."""

    rel_path: str
    written: bool
    findings: list[LintFinding]


@dataclass(frozen=True)
class TaskRecord:
    """A task slice document."""

    file_name: str
    id: str
    ticket_id: str
    title: str
    status: TaskStatus
    order: int
    target_files: tuple[str, ...]
    updated: str
    completed_at: str | None
    path: Path


@dataclass(frozen=True)
class QuestionOption:
    """One answer option of a question."""

    key: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class QuestionInput:
    """What an agent supplies to ask one question (``townhall_request_inputs``)."""

    header: str
    title: str
    tldr: str
    context: str
    options: Sequence[QuestionOption]
    slug: str | None = None
    multi_select: bool = False
    allow_other: bool = True


@dataclass(frozen=True)
class Question:
    """A stored question file."""

    file_name: str
    id: str
    ticket_id: str
    header: str
    title: str
    status: Literal["pending", "answered"]
    source_stage: Stage | None
    multi_select: bool
    allow_other: bool
    options: tuple[QuestionOption, ...]
    selected: tuple[str, ...]
    other_text: str | None
    answered_at: str | None
    order: int
    path: Path


@dataclass(frozen=True)
class InputRequestResult:
    """Outcome of `request_inputs`."""

    handoff_path: Path
    questions: list[Question]
    stage: Stage


@dataclass(frozen=True)
class Handoff:
    """What a resumed agent needs: the log, the source stage and the questions."""

    handoff_markdown: str
    source_stage: Stage | None
    answered: list[Question]
    pending: list[Question]


@dataclass(frozen=True)
class MoveResult:
    """Outcome of a stage move. `reason` is returned, not stored."""

    ticket_id: str
    from_stage: Stage
    to_stage: Stage
    reason: str


@dataclass(frozen=True)
class PickResult:
    """A successful claim."""

    ticket: TicketSummary
    from_stage: Stage
    to_stage: Stage
    claimed_by: str
    claim_expires_at: str


@dataclass(frozen=True)
class InitResult:
    """Paths created by `init_project` (relative to the project root)."""

    root: Path
    created: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------- templates

_TEMPLATE_FILES: Mapping[str, str] = {
    "GLOSSARY.md": """---
title: "Glossary"
status: "draft"
updated: {{date}}
order: 60
---

# Glossary

**tl;dr:** This page defines the terms used across ticket {{ticket_id}}. Each entry has a stable anchor so other pages can link to it. Add entries as new terms appear.

## Terms

No terms defined yet. Add entries as `### R1 — <term> {#r1}`.
""",
    "DRAFT.md": """# Draft

Agent-only scratch pad. No frontmatter, no tl;dr, never linked from another file.
""",
    "HANDOFF.md": """# Handoff

Agent-only resume log. Not rendered by the site, no frontmatter, never linked from another file in this pack. Stay CONCISE.

No handoff yet.
""",
    "plan/plan-01-context.md": """---
title: "Context"
status: "draft"
updated: {{date}}
order: 20
---

# Context

**tl;dr:** This page states why ticket {{ticket_id}} exists and what it covers. It lists the fixed decisions and the request flow. Replace this text once the problem is agreed.

## Why

Describe the problem and who it affects.

## Scope

In scope: list what the ticket delivers. Out of scope: list what it does not.

## Fixed decisions

| Name | Value | Why |
|---|---|---|
| `example` | `value` | Replace with a real decision and its reason. |

## Diagram

```mermaid
flowchart LR
  accTitle: Request flow
  accDescr: A request enters the system, is handled, and a result is returned.
  Req["Request"] --> Handle["Handle"] --> Result["Result"]
```
""",
    "plan/plan-02-architecture.md": """---
title: "Architecture"
status: "draft"
updated: {{date}}
order: 21
---

# Architecture

**tl;dr:** This page describes how the change is built for ticket {{ticket_id}}. It names the components and how they talk to each other. Replace this text once the design is agreed.

## Components

Describe the parts that change and the parts that stay.

## Diagram

```mermaid
flowchart LR
  accTitle: Component overview
  accDescr: The caller uses the new component, which reads from and writes to storage.
  Caller["Caller"] --> Component["Component"] --> Store["Storage"]
```
""",
    "plan/plan-03-verification.md": """---
title: "Verification"
status: "draft"
updated: {{date}}
order: 22
---

# Verification

**tl;dr:** This page lists the checks that prove ticket {{ticket_id}} is done. Each check names a command and the result that counts as a pass. Replace this text once the plan is agreed.

## Checks

| Command | Pass when |
|---|---|
| `pytest` | All tests pass. |
""",
}

_AGENTVILLE_GITIGNORE = """# Runtime files Townhall writes while it works; never commit them.
.lock
*.lock
*.tmp
*.break
"""

_DEFAULT_CONFIG = """[townhall]
default_board = "B01"
enforce_page_budgets = true

[plugins.claude]
enabled = false
default_model = "haiku"
orchestrator_model = "sonnet"
auto_mode = true
auto_merge = false                   # merge Complete tickets by branch; needs enabled = true too

[engine]
temporal_address = ""                # host:port of a running server; empty auto-starts a dev server
temporal_namespace = "default"
temporal_port = 7233                 # fixed port of the local dev server
temporal_ui = true
temporal_cli_path = ""               # installed `temporal` CLI; empty looks on PATH, then downloads
continue_as_new_after = 500
poll_interval_seconds = 30.0
claude_executable = "claude"
claude_timeout_seconds = 1800.0      # limit for each `claude -p` run
claude_auto_args = ["--permission-mode", "auto"]

[rag]
enabled = false

[memory]
enabled = false
"""


# ---------------------------------------------------------------------- file helpers


def _atomic_write(path: Path, text: str) -> None:
    """Write `text` to `path` through a temp file in the same directory."""
    _commit({path: text})


def _commit(files: Mapping[Path, str]) -> None:
    """Write several files: stage every temp file, then rename each into place."""
    staged: list[tuple[Path, Path]] = []
    try:
        for path, text in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            handle, temp_name = tempfile.mkstemp(
                dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
            )
            temp = Path(temp_name)
            staged.append((temp, path))
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
        while staged:
            temp, path = staged[0]
            os.replace(temp, path)
            staged.pop(0)
    finally:
        for temp, _ in staged:
            with suppress(FileNotFoundError):
                temp.unlink()


def _lock_identity(path: Path) -> tuple[int, int] | None:
    """The (inode, mtime in ns) of a lock file, or None when it is gone."""
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    return info.st_ino, info.st_mtime_ns


def _break_stale_lock(path: Path) -> bool:
    """Remove `path` if it is still the same stale lock; never remove a fresh one.

    Only the holder of a short-lived ``<lock>.break`` guard may break a lock, so two
    processes that both saw a stale lock cannot delete each other's fresh lock. Under
    the guard the lock is renamed to a unique name and the renamed file is checked
    against what was seen; a mismatch means a fresh lock was caught and it is put back.
    Returns True when a stale lock was removed.
    """
    guard = path.with_name(path.name + ".break")
    try:
        descriptor = os.open(guard, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        # A crashed breaker leaves its guard behind; an old one may be removed.
        with suppress(FileNotFoundError):
            if time.time() - guard.stat().st_mtime > STALE_LOCK_SECONDS:
                guard.unlink()
        return False
    try:
        seen = _lock_identity(path)
        if seen is None:
            return False
        try:
            age = time.time() - path.stat().st_mtime
        except FileNotFoundError:
            return False
        if age <= STALE_LOCK_SECONDS:
            return False
        parked = path.with_name(f"{path.name}.stale-{uuid.uuid4().hex}.tmp")
        try:
            os.rename(path, parked)
        except FileNotFoundError:
            return False
        if _lock_identity(parked) != seen:
            # The stale lock was released and a fresh one created between our checks.
            with suppress(OSError):
                os.link(parked, path)
            with suppress(FileNotFoundError):
                parked.unlink()
            return False
        with suppress(FileNotFoundError):
            parked.unlink()
        return True
    finally:
        os.close(descriptor)
        with suppress(FileNotFoundError):
            guard.unlink()


@contextmanager
def _exclusive_lock(
    path: Path, wait: float = DEFAULT_LOCK_WAIT_SECONDS
) -> Iterator[None]:
    """Hold an exclusive lock file; raise `ClaimError` if it stays busy for `wait` seconds."""
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + wait
    while True:
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            break
        except FileExistsError:
            try:
                age = time.time() - path.stat().st_mtime
            except FileNotFoundError:
                continue
            if age > STALE_LOCK_SECONDS and _break_stale_lock(path):
                continue
            if time.monotonic() >= deadline:
                raise ClaimError(
                    f"{path.parent.name} is locked by another process."
                ) from None
            time.sleep(0.01)
    try:
        os.write(descriptor, str(os.getpid()).encode())
        yield
    finally:
        os.close(descriptor)
        with suppress(FileNotFoundError):
            path.unlink()


def _slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit].strip("-")
    return slug or "item"


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_moment(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _text(value: object) -> str:
    return (
        value.isoformat()
        if isinstance(value, date)
        else ("" if value is None else str(value))
    )


def _ordered(data: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    """Return `data` with `keys` first, in that order, then any extra keys in their order."""
    result = {key: data[key] for key in keys if key in data}
    result.update({key: value for key, value in data.items() if key not in result})
    return result


_INDEX_KEYS = (
    "id", "board_id", "title", "stage", "status", "priority", "updated", "order",
    "claimed_by", "claim_expires_at", "source_stage", "labels",
)  # fmt: skip
_TASK_KEYS = (
    "id",
    "ticket_id",
    "title",
    "status",
    "updated",
    "completed_at",
    "order",
    "target_files",
)
_QUESTION_KEYS = (
    "id", "ticket_id", "header", "title", "status", "source_stage", "multi_select", "allow_other",
    "options", "selected", "other_text", "answered_at", "updated", "order",
)  # fmt: skip

_DIRECTORY_RANK = {
    "draft": 1,
    "plan": 2,
    "questions": 3,
    "tasks": 4,
    "execution": 5,
    "review": 6,
}


def _safe_rel_path(rel_path: str) -> PurePosixPath:
    pure = PurePosixPath(rel_path.replace("\\", "/"))
    if not pure.parts or pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise InvalidInputError(
            f"'{rel_path}' is not a safe relative path inside a ticket pack."
        )
    return pure


# ----------------------------------------------------------------------- storage


class TownhallStorage:
    """All Townhall filesystem operations for one project root.

    `enforce_page_budgets` defaults to ``[townhall].enforce_page_budgets`` from
    ``.agentville/config.toml``. `clock` returns an aware UTC datetime and exists so
    tests can fix time.
    """

    def __init__(
        self,
        root: Path | str | None = None,
        *,
        enforce_page_budgets: bool | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.root = Path(root) if root is not None else Path.cwd()
        self._enforce_override = enforce_page_budgets
        self._clock = clock or (lambda: datetime.now(UTC))

    # -- basics --------------------------------------------------------------

    @property
    def townhall_dir(self) -> Path:
        return self.root / TOWNHALL_RELATIVE

    @property
    def config(self) -> Config:
        return load_config(self.root)

    @property
    def enforce_page_budgets(self) -> bool:
        if self._enforce_override is not None:
            return self._enforce_override
        return self.config.townhall.enforce_page_budgets

    def _today(self) -> date:
        return self._clock().astimezone(UTC).date()

    # -- init ----------------------------------------------------------------

    def init_project(self) -> InitResult:
        """Create ``.agentville/``, its config, the boards folder and ``_template/``. Idempotent."""
        result = InitResult(self.root)
        config_path = self.root / ".agentville" / "config.toml"
        wanted: dict[Path, str] = {config_path: _DEFAULT_CONFIG}
        for rel, text in _TEMPLATE_FILES.items():
            wanted[self.townhall_dir / "_template" / rel] = text
        wanted[self.root / ".agentville" / ".gitignore"] = _AGENTVILLE_GITIGNORE
        wanted[self.townhall_dir / "boards" / ".gitkeep"] = ""
        for sub in PACK_SUBDIRECTORIES:
            wanted.setdefault(self.townhall_dir / "_template" / sub / ".gitkeep", "")
        for path, text in wanted.items():
            if not path.exists():
                _atomic_write(path, text)
                result.created.append(path.relative_to(self.root).as_posix())
        return result

    # -- boards --------------------------------------------------------------

    def _board_dir(self, board_id: str) -> Path:
        if not _BOARD_ID_RE.match(board_id):
            raise InvalidInputError(
                f"'{board_id}' is not a valid board id (letters, digits, '-' and '_')."
            )
        return self.townhall_dir / "boards" / board_id

    def create_board(self, board_id: str, name: str) -> Board:
        """Create a board with its ``board.toml``."""
        path = self._board_dir(board_id)
        if path.exists():
            raise AlreadyExistsError(f"Board {board_id} already exists.")
        if not name.strip():
            raise InvalidInputError("A board needs a name.")
        _atomic_write(
            path / "board.toml",
            f"id = {_toml_str(board_id)}\nname = {_toml_str(name.strip())}\n",
        )
        (path / "tickets").mkdir(exist_ok=True)
        _atomic_write(path / "tickets" / ".gitkeep", "")
        return Board(board_id, name.strip(), path)

    def get_board(self, board_id: str) -> Board:
        path = self._board_dir(board_id)
        meta = path / "board.toml"
        if not meta.is_file():
            raise NotFoundError(f"Board {board_id} does not exist.")
        data = tomllib.loads(meta.read_text(encoding="utf-8"))
        return Board(
            str(data.get("id", board_id)), str(data.get("name", board_id)), path
        )

    def list_boards(self) -> list[Board]:
        boards_dir = self.townhall_dir / "boards"
        if not boards_dir.is_dir():
            return []
        found = [
            self.get_board(p.name)
            for p in sorted(boards_dir.iterdir())
            if (p / "board.toml").is_file()
        ]
        return sorted(found, key=lambda b: b.id)

    # -- tickets: lookup -----------------------------------------------------

    def _ticket_dir(self, board_id: str, ticket_id: str) -> Path:
        self.get_board(board_id)
        if not _TICKET_ID_RE.match(ticket_id):
            raise InvalidInputError(f"'{ticket_id}' is not a valid ticket id.")
        path = self._board_dir(board_id) / "tickets" / ticket_id
        if not (path / "index.md").is_file():
            raise NotFoundError(f"Ticket {board_id}-{ticket_id} does not exist.")
        return path

    def _read_index(self, ticket_dir: Path) -> tuple[dict[str, Any], str]:
        """Return (frontmatter, preamble) where preamble is the H1 plus tl;dr."""
        doc = parse_document((ticket_dir / "index.md").read_text(encoding="utf-8"))
        if doc.frontmatter is None:
            raise InvalidInputError(
                f"{ticket_dir / 'index.md'} has invalid frontmatter: {doc.error}."
            )
        head, _, _ = doc.body.partition("\n## ")
        return doc.frontmatter, head.strip("\n")

    def _summary(
        self, ticket_dir: Path, fm: Mapping[str, Any] | None = None
    ) -> TicketSummary:
        if fm is None:
            fm, _ = self._read_index(ticket_dir)
        tasks = self._load_tasks(ticket_dir)
        pending = [q for q in self._load_questions(ticket_dir) if q.status == "pending"]
        source = fm.get("source_stage")
        return TicketSummary(
            id=str(fm["id"]),
            board_id=str(fm["board_id"]),
            title=str(fm.get("title", "")),
            stage=parse_stage(str(fm["stage"])),
            status=str(fm.get("status", "")),
            priority=str(fm.get("priority", "medium")),
            labels=tuple(str(x) for x in fm.get("labels") or ()),
            updated=_text(fm.get("updated")),
            claimed_by=fm.get("claimed_by"),
            claim_expires_at=_text(fm.get("claim_expires_at")) or None,
            source_stage=parse_stage(source) if source else None,
            open_questions=len(pending),
            tasks_done=sum(1 for t in tasks if t.status is TaskStatus.DONE),
            tasks_total=len(tasks),
            path=ticket_dir,
        )

    def get_ticket(self, board_id: str, ticket_id: str) -> TicketSummary:
        return self._summary(self._ticket_dir(board_id, ticket_id))

    def list_tickets(
        self, board_id: str, stage: str | Stage | None = None
    ) -> list[TicketSummary]:
        """Summaries of a board's tickets by id, optionally only those in `stage`."""
        self.get_board(board_id)
        wanted = parse_stage(stage) if stage is not None else None
        tickets_dir = self._board_dir(board_id) / "tickets"
        result = []
        for path in sorted(tickets_dir.iterdir()) if tickets_dir.is_dir() else []:
            if path.is_dir() and (path / "index.md").is_file():
                summary = self._summary(path)
                if wanted is None or summary.stage is wanted:
                    result.append(summary)
        return sorted(result, key=lambda t: (len(t.id), t.id))

    # -- tickets: create -----------------------------------------------------

    def create_ticket(
        self,
        board_id: str,
        title: str,
        *,
        stage: str | Stage = Stage.BACKLOG,
        priority: str = "medium",
        labels: Sequence[str] = (),
        tldr: str | None = None,
    ) -> TicketSummary:
        """Create the next ticket of a board and seed its pack from ``_template/``."""
        board = self.get_board(board_id)
        title = " ".join(title.split())
        if not title:
            raise InvalidInputError("A ticket needs a title.")
        if priority not in PRIORITIES:
            raise InvalidInputError(
                f"Priority must be one of: {', '.join(PRIORITIES)}."
            )
        first_stage = parse_stage(stage)
        if first_stage is Stage.NEED_INPUTS:
            raise InvalidInputError(
                "A ticket cannot start in Need Inputs; use request_inputs."
            )
        tickets_dir = board.path / "tickets"
        with _exclusive_lock(board.path / ".tickets.lock"):
            numbers = [
                int(p.name)
                for p in tickets_dir.iterdir()
                if p.is_dir() and p.name.isdigit()
            ]
            ticket_id = f"{max(numbers, default=FIRST_TICKET_NUMBER - 1) + 1:0{TICKET_PADDING}d}"
            ticket_dir = tickets_dir / ticket_id
            ticket_dir.mkdir(parents=True)
        summary = tldr or (
            f"This ticket tracks: {title}. Scope and plan are not written yet. "
            "The pack grows as the ticket moves through its stages."
        )
        fm: dict[str, Any] = {
            "id": ticket_id,
            "board_id": board_id,
            "title": title,
            "stage": first_stage.value,
            "status": _STATUS_FOR_STAGE[first_stage],
            "priority": priority,
            "updated": self._today(),
            "order": 0,
            "claimed_by": None,
            "claim_expires_at": None,
            "source_stage": None,
            "labels": list(labels),
        }
        values = {
            "ticket_id": ticket_id,
            "board_id": board_id,
            "title": title,
            "date": self._today().isoformat(),
        }
        files = {
            ticket_dir / rel: _fill(text, values)
            for rel, text in self._template_files().items()
        }
        for sub in PACK_SUBDIRECTORIES:
            files.setdefault(ticket_dir / sub / ".gitkeep", "")
        _commit(files)
        preamble = (
            f"# Ticket {ticket_id}: {title}\n\n**tl;dr:** {' '.join(summary.split())}"
        )
        with _exclusive_lock(ticket_dir / ".lock"):
            self._write_index(ticket_dir, fm, preamble, touch=False)
        return self._summary(ticket_dir)

    def _template_files(self) -> dict[str, str]:
        template_dir = self.townhall_dir / "_template"
        if not template_dir.is_dir():
            return dict(_TEMPLATE_FILES)
        found: dict[str, str] = {}
        for path in sorted(template_dir.rglob("*")):
            if path.is_file() and path.name != ".gitkeep":
                found[path.relative_to(template_dir).as_posix()] = path.read_text(
                    encoding="utf-8"
                )
        return found

    # -- index.md ------------------------------------------------------------

    def _write_index(
        self, ticket_dir: Path, fm: Mapping[str, Any], preamble: str, *, touch: bool
    ) -> None:
        """Render index.md; set ``updated`` to today only when the content changes and `touch` is true."""
        data = _ordered(dict(fm), _INDEX_KEYS)
        data["stage"] = str(data["stage"])
        body = self._render_index_body(ticket_dir, data, preamble)
        path = ticket_dir / "index.md"
        text = render_document(data, body)
        existing = path.read_text(encoding="utf-8") if path.is_file() else None
        if existing == text:
            return
        if touch:
            data["updated"] = self._today()
            text = render_document(data, body)
        _atomic_write(path, text)

    def _sync_index_unlocked(
        self, ticket_dir: Path, fm_changes: Mapping[str, Any] | None = None
    ) -> None:
        fm, preamble = self._read_index(ticket_dir)
        fm.update(fm_changes or {})
        self._write_index(ticket_dir, fm, preamble, touch=True)

    def sync_index(self, board_id: str, ticket_id: str) -> None:
        """Regenerate the section link lists of index.md from the files on disk."""
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        with _exclusive_lock(ticket_dir / ".lock"):
            self._sync_index_unlocked(ticket_dir)

    def _render_index_body(
        self, ticket_dir: Path, fm: Mapping[str, Any], preamble: str
    ) -> str:
        pending = [q for q in self._load_questions(ticket_dir) if q.status == "pending"]
        open_text = (
            f"{len(pending)} pending question{'s' if len(pending) != 1 else ''}"
            if pending
            else "None"
        )
        lines = [
            preamble.strip("\n"),
            "",
            "## Status",
            "",
            "| Area | State |",
            "|---|---|",
            f"| Ticket | {fm['board_id']}-{fm['id']} |",
            f"| Stage | {fm['stage']} |",
            f"| Open | {open_text} |",
        ]

        def section(heading: str, entries: list[str]) -> None:
            lines.extend(["", f"## {heading}", ""])
            lines.extend(entries or ["None yet."])

        def links(folder: str) -> list[str]:
            return [
                f"- [{p.name}](./{folder}/{p.name}) — {title}"
                for p, title, _ in self._folder_pages(ticket_dir, folder)
            ]

        section("Draft & Discovery", links("draft"))
        section("Plan", links("plan"))
        section(
            "Questions (Need Inputs)",
            [
                f"- [{'x' if q.status == 'answered' else ' '}] [{q.file_name}](./questions/{q.file_name}) — {q.title}"
                for q in self._load_questions(ticket_dir)
            ],
        )
        section(
            "Tasks",
            [
                f"- [{'x' if t.status is TaskStatus.DONE else ' '}] [{t.file_name}](./tasks/{t.file_name}) — {t.title}"
                for t in self._load_tasks(ticket_dir)
            ],
        )
        if any(True for _ in self._folder_pages(ticket_dir, "execution")):
            section("Execution", links("execution"))
        section("Review", links("review"))
        glossary = ticket_dir / "GLOSSARY.md"
        if (
            glossary.is_file()
            and parse_document(glossary.read_text(encoding="utf-8")).frontmatter
            is not None
        ):
            section(
                "Reference",
                ["- [GLOSSARY.md](./GLOSSARY.md) — Terms used in this pack"],
            )
        lines.extend(
            [
                "",
                "## Resume",
                "",
                (
                    "See `HANDOFF.md` in this pack's folder for the resume log "
                    "(agent-only, not rendered — do not link to it from prose)."
                ),
            ]
        )
        return "\n".join(lines) + "\n"

    def _folder_pages(
        self, ticket_dir: Path, folder: str
    ) -> Iterator[tuple[Path, str, int]]:
        """Yield (path, title, order) of ``*.md`` files in a folder, ordered by (order, name)."""
        found = []
        for path in (ticket_dir / folder).glob("*.md"):
            fm = parse_document(path.read_text(encoding="utf-8")).frontmatter or {}
            order = fm.get("order")
            order = (
                order
                if isinstance(order, int) and not isinstance(order, bool)
                else 10_000
            )
            found.append((order, path.name, path, str(fm.get("title") or path.stem)))
        for order, _, path, title in sorted(found, key=lambda item: (item[0], item[1])):
            yield path, title, order

    # -- pack and pages ------------------------------------------------------

    def get_ticket_pack(
        self, board_id: str, ticket_id: str, *, include_agent_files: bool = True
    ) -> TicketPack:
        """Load every page sorted by frontmatter ``order`` (pages without one sort last by folder)."""
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        pages = []
        for path in ticket_dir.rglob("*.md"):
            rel = path.relative_to(ticket_dir).as_posix()
            if rel in ("DRAFT.md", "HANDOFF.md"):
                continue
            content = path.read_text(encoding="utf-8")
            doc = parse_document(content)
            pages.append(Page(rel, doc.frontmatter or {}, doc.body, content))

        def sort_key(page: Page) -> tuple[int, int, str]:
            if page.order is not None:
                return (0, page.order, page.rel_path)
            return (
                1,
                _DIRECTORY_RANK.get(page.rel_path.split("/", 1)[0], 9),
                page.rel_path,
            )

        pages.sort(key=sort_key)
        handoff = draft = diff = None
        if include_agent_files:
            handoff = _read_optional(ticket_dir / "HANDOFF.md")
            draft = _read_optional(ticket_dir / "DRAFT.md")
            diff = _read_optional(ticket_dir / "review" / "diff.patch")
        return TicketPack(self._summary(ticket_dir), pages, handoff, draft, diff)

    def write_page(
        self, board_id: str, ticket_id: str, rel_path: str, content: str
    ) -> WritePageResult:
        """Lint and write a page under ``draft/``, ``plan/``, ``execution/`` or ``GLOSSARY.md``/``DRAFT.md``.

        When page budgets are enforced and the lint has errors, nothing is written
        and the result has ``written=False`` with the findings. Warnings never block.
        """
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        pure = _safe_rel_path(rel_path)
        rel = pure.as_posix()
        top_ok = (
            len(pure.parts) >= 2
            and pure.parts[0] in WRITABLE_PAGE_DIRECTORIES
            and pure.suffix == ".md"
        )
        if not (top_ok or rel in WRITABLE_ROOT_FILES):
            raise InvalidInputError(
                f"'{rel}' is not writable here. Use draft/*.md, plan/*.md, execution/*.md, GLOSSARY.md or DRAFT.md; "
                "tasks, questions, review and HANDOFF.md have their own operations."
            )
        text = content.rstrip("\n") + "\n"
        findings = lint_markdown(text, rel)
        if self.enforce_page_budgets and has_errors(findings):
            return WritePageResult(rel, False, findings)
        target = ticket_dir.joinpath(*pure.parts)
        if not target.resolve().is_relative_to(ticket_dir.resolve()):
            raise InvalidInputError(f"'{rel}' escapes the ticket pack.")
        with _exclusive_lock(ticket_dir / ".lock"):
            _atomic_write(target, text)
            self._sync_index_unlocked(ticket_dir)
        return WritePageResult(rel, True, findings)

    def lint_ticket(self, board_id: str, ticket_id: str) -> list[LintFinding]:
        """Lint every Markdown page of the pack (agent-only files are skipped)."""
        pack = self.get_ticket_pack(board_id, ticket_id, include_agent_files=False)
        findings: list[LintFinding] = []
        for page in pack.pages:
            findings.extend(lint_markdown(page.content, page.rel_path))
        return findings

    def _require_clean(self, files: Mapping[str, str], what: str) -> None:
        if not self.enforce_page_budgets:
            return
        findings = [f for rel, text in files.items() for f in lint_markdown(text, rel)]
        if has_errors(findings):
            raise PageBudgetError(f"{what} fails the page-budget linter.", findings)

    # -- tasks ---------------------------------------------------------------

    def _load_tasks(self, ticket_dir: Path) -> list[TaskRecord]:
        tasks = []
        for path, _, _ in self._folder_pages(ticket_dir, "tasks"):
            fm = parse_document(path.read_text(encoding="utf-8")).frontmatter or {}
            order = fm.get("order")
            tasks.append(
                TaskRecord(
                    file_name=path.name,
                    id=str(fm.get("id", path.stem)),
                    ticket_id=str(fm.get("ticket_id", "")),
                    title=str(fm.get("title", path.stem)),
                    status=TaskStatus(fm.get("status", "todo")),
                    order=order if isinstance(order, int) else 0,
                    target_files=tuple(str(x) for x in fm.get("target_files") or ()),
                    updated=_text(fm.get("updated")),
                    completed_at=_text(fm.get("completed_at")) or None,
                    path=path,
                )
            )
        return tasks

    def list_tasks(self, board_id: str, ticket_id: str) -> list[TaskRecord]:
        return self._load_tasks(self._ticket_dir(board_id, ticket_id))

    def _resolve_task(self, ticket_dir: Path, name: str) -> Path:
        stem = name.removesuffix(".md")
        exact = ticket_dir / "tasks" / f"{stem}.md"
        if exact.is_file():
            return exact
        matches = [
            t.path
            for t in self._load_tasks(ticket_dir)
            if t.id == stem or t.path.stem.startswith(f"{stem}-")
        ]
        if len(matches) == 1:
            return matches[0]
        raise NotFoundError(
            f"Task '{name}' not found."
            if not matches
            else f"Task '{name}' is ambiguous."
        )

    def create_task(
        self,
        board_id: str,
        ticket_id: str,
        file_name: str,
        title: str,
        order: int,
        target_files: Sequence[str],
        body_markdown: str,
    ) -> TaskRecord:
        """Write ``tasks/task-NN-slug.md`` (body starts with the tl;dr) and register it in index.md."""
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        stem = file_name.removesuffix(".md")
        match = _TASK_NAME_RE.match(stem)
        if match is None:
            raise InvalidInputError(
                f"Task file '{file_name}' must look like task-01-short-name.md."
            )
        if _H1_RE.match(body_markdown.lstrip()):
            raise InvalidInputError(
                "body_markdown must not start with an H1; the task heading is added for you."
            )
        number = int(match.group(1))
        title = " ".join(title.split())
        fm = _ordered(
            {
                "id": stem,
                "ticket_id": ticket_id,
                "title": title,
                "status": TaskStatus.TODO.value,
                "updated": self._today(),
                "completed_at": None,
                "order": order,
                "target_files": list(target_files),
            },
            _TASK_KEYS,
        )
        text = render_document(
            fm, f"# T{number} — {title} {{#t{number}}}\n\n{body_markdown.strip()}"
        )
        rel = f"tasks/{stem}.md"
        self._require_clean({rel: text}, f"Task {stem}")
        with _exclusive_lock(ticket_dir / ".lock"):
            if (ticket_dir / rel).exists():
                raise AlreadyExistsError(f"Task {stem} already exists.")
            _atomic_write(ticket_dir / rel, text)
            self._sync_index_unlocked(ticket_dir)
        return next(t for t in self._load_tasks(ticket_dir) if t.id == stem)

    def update_task_status(
        self, board_id: str, ticket_id: str, file_name: str, status: str | TaskStatus
    ) -> TaskRecord:
        """Set a task's status; ``done`` ticks its checkboxes and sets ``completed_at``."""
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        try:
            new_status = TaskStatus(status)
        except ValueError:
            raise InvalidInputError(
                "Task status must be todo, in_progress or done."
            ) from None
        with _exclusive_lock(ticket_dir / ".lock"):
            path = self._resolve_task(ticket_dir, file_name)
            doc = parse_document(path.read_text(encoding="utf-8"))
            fm = dict(doc.frontmatter or {})
            body = doc.body
            if new_status is TaskStatus.DONE:
                body = _CHECKBOX_RE.sub(r"\1[x]", body)
            elif new_status is TaskStatus.TODO:
                body = _CHECKBOX_RE.sub(r"\1[ ]", body)
            fm.update(
                status=new_status.value,
                updated=self._today(),
                completed_at=self._today() if new_status is TaskStatus.DONE else None,
            )
            _atomic_write(path, render_document(_ordered(fm, _TASK_KEYS), body))
            self._sync_index_unlocked(ticket_dir)
        return next(t for t in self._load_tasks(ticket_dir) if t.path == path)

    def delete_task(self, board_id: str, ticket_id: str, file_name: str) -> None:
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        with _exclusive_lock(ticket_dir / ".lock"):
            self._resolve_task(ticket_dir, file_name).unlink()
            self._sync_index_unlocked(ticket_dir)

    # -- questions, handoff, inputs -----------------------------------------

    def _load_questions(self, ticket_dir: Path) -> list[Question]:
        questions = []
        for path, _, _ in self._folder_pages(ticket_dir, "questions"):
            fm = parse_document(path.read_text(encoding="utf-8")).frontmatter or {}
            source = fm.get("source_stage")
            order = fm.get("order")
            questions.append(
                Question(
                    file_name=path.name,
                    id=str(fm.get("id", path.stem)),
                    ticket_id=str(fm.get("ticket_id", "")),
                    header=str(fm.get("header", "")),
                    title=str(fm.get("title", path.stem)),
                    status="answered" if fm.get("status") == "answered" else "pending",
                    source_stage=parse_stage(source) if source else None,
                    multi_select=bool(fm.get("multi_select", False)),
                    allow_other=bool(fm.get("allow_other", True)),
                    options=tuple(
                        QuestionOption(
                            str(o["key"]),
                            str(o.get("label", o["key"])),
                            str(o.get("description", "")),
                        )
                        for o in fm.get("options") or ()
                    ),
                    selected=tuple(str(x) for x in fm.get("selected") or ()),
                    other_text=fm.get("other_text"),
                    answered_at=_text(fm.get("answered_at")) or None,
                    order=order if isinstance(order, int) else DEFAULT_QUESTION_ORDER,
                    path=path,
                )
            )
        return questions

    def list_questions(self, board_id: str, ticket_id: str) -> list[Question]:
        return self._load_questions(self._ticket_dir(board_id, ticket_id))

    def request_inputs(
        self,
        board_id: str,
        ticket_id: str,
        source_stage: Literal["Planning", "Execute"] | Stage,
        handoff_markdown: str,
        questions: Sequence[QuestionInput],
    ) -> InputRequestResult:
        """Write HANDOFF.md and ``questions/q-NN-*.md``, link them and move the ticket to Need Inputs.

        All content is linted before anything is written; the claim, if any, is released.
        """
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        source = parse_stage(source_stage)
        if source not in (Stage.PLANNING, Stage.EXECUTE):
            raise InvalidInputError("source_stage must be Planning or Execute.")
        if not questions:
            raise InvalidInputError("Ask at least one question.")
        if not handoff_markdown.strip():
            raise InvalidInputError("handoff_markdown must not be empty.")
        with _exclusive_lock(ticket_dir / ".lock"):
            fm, _ = self._read_index(ticket_dir)
            current = parse_stage(str(fm["stage"]))
            if current is not source:
                raise InvalidTransitionError(
                    f"Ticket is in {current.value}, not {source.value}."
                )
            existing = [
                int(m.group(1))
                for q in self._load_questions(ticket_dir)
                if (m := _QUESTION_NAME_RE.match(q.path.stem))
            ]
            number = max(existing, default=0)
            files: dict[Path, str] = {}
            rendered: dict[str, str] = {}
            for item in questions:
                number += 1
                _validate_question(item)
                stem = f"q-{number:02d}-{item.slug or _slugify(item.header)}"
                text = _render_question(
                    item, stem, number, ticket_id, source, self._today()
                )
                rendered[f"questions/{stem}.md"] = text
                files[ticket_dir / "questions" / f"{stem}.md"] = text
            self._require_clean(rendered, "The questions")
            files[ticket_dir / "HANDOFF.md"] = handoff_markdown.strip("\n") + "\n"
            _commit(files)
            self._sync_index_unlocked(
                ticket_dir,
                {
                    "stage": Stage.NEED_INPUTS.value,
                    "status": _STATUS_FOR_STAGE[Stage.NEED_INPUTS],
                    "source_stage": source.value,
                    "claimed_by": None,
                    "claim_expires_at": None,
                },
            )
            stored = [
                q
                for q in self._load_questions(ticket_dir)
                if f"questions/{q.file_name}" in rendered
            ]
        return InputRequestResult(ticket_dir / "HANDOFF.md", stored, Stage.NEED_INPUTS)

    def get_handoff(self, board_id: str, ticket_id: str) -> Handoff:
        """HANDOFF.md plus every answered (and pending) question payload."""
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        fm, _ = self._read_index(ticket_dir)
        source = fm.get("source_stage")
        questions = self._load_questions(ticket_dir)
        return Handoff(
            _read_optional(ticket_dir / "HANDOFF.md") or "",
            parse_stage(source) if source else None,
            [q for q in questions if q.status == "answered"],
            [q for q in questions if q.status == "pending"],
        )

    def answer_question(
        self,
        board_id: str,
        ticket_id: str,
        question_file: str,
        selected: Sequence[str] = (),
        other_text: str | None = None,
    ) -> Question:
        """Record an answer. The ticket stays in Need Inputs until it is moved."""
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        with _exclusive_lock(ticket_dir / ".lock"):
            stem = question_file.removesuffix(".md")
            matches = [
                q.path
                for q in self._load_questions(ticket_dir)
                if q.path.stem == stem or q.path.stem.startswith(f"{stem}-")
            ]
            if len(matches) != 1:
                raise NotFoundError(
                    f"Question '{question_file}' not found."
                    if not matches
                    else f"Question '{question_file}' is ambiguous."
                )
            path = matches[0]
            question = next(
                q for q in self._load_questions(ticket_dir) if q.path == path
            )
            if question.status == "answered":
                raise InvalidInputError(f"{question.file_name} is already answered.")
            chosen = list(dict.fromkeys(selected))
            unknown = [k for k in chosen if k not in {o.key for o in question.options}]
            other = (other_text or "").strip() or None
            if unknown:
                raise InvalidInputError(f"Unknown option key(s): {', '.join(unknown)}.")
            if other and not question.allow_other:
                raise InvalidInputError("This question does not allow other text.")
            if not chosen and not other:
                raise InvalidInputError("Select an option or give other text.")
            if len(chosen) > 1 and not question.multi_select:
                raise InvalidInputError("This question allows one option only.")
            doc = parse_document(path.read_text(encoding="utf-8"))
            fm = dict(doc.frontmatter or {})
            fm.update(
                status="answered",
                selected=chosen,
                other_text=other,
                answered_at=_iso(self._clock()),
                updated=self._today(),
            )
            _atomic_write(path, render_document(_ordered(fm, _QUESTION_KEYS), doc.body))
            self._sync_index_unlocked(ticket_dir)
            return next(q for q in self._load_questions(ticket_dir) if q.path == path)

    # -- review --------------------------------------------------------------

    def submit_review(
        self,
        board_id: str,
        ticket_id: str,
        summary_markdown: str,
        evidence_markdown: str,
        diff_patch: str,
        *,
        require_tasks_done: bool = True,
    ) -> MoveResult:
        """Write the review pages and ``diff.patch``, then move Execute to Review.

        Each markdown argument is either a full page (with frontmatter) or a body;
        a body gets default frontmatter and, if missing, an H1.
        """
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        summary = _review_page(
            summary_markdown, "Review summary", REVIEW_SUMMARY_ORDER, self._today()
        )
        evidence = _review_page(
            evidence_markdown, "Review evidence", REVIEW_EVIDENCE_ORDER, self._today()
        )
        pages = {
            "review/review-01-summary.md": summary,
            "review/review-02-evidence.md": evidence,
        }
        self._require_clean(pages, "The review pages")
        with _exclusive_lock(ticket_dir / ".lock"):
            fm, _ = self._read_index(ticket_dir)
            current = parse_stage(str(fm["stage"]))
            if current is not Stage.EXECUTE:
                raise InvalidTransitionError(
                    f"Ticket is in {current.value}; only Execute can submit a review."
                )
            tasks = self._load_tasks(ticket_dir)
            if require_tasks_done and not tasks:
                raise InvalidInputError(
                    "The ticket has no tasks. Add at least one task and finish it before submitting a review."
                )
            unfinished = [t.file_name for t in tasks if t.status is not TaskStatus.DONE]
            if require_tasks_done and unfinished:
                raise InvalidInputError(f"Tasks are not done: {', '.join(unfinished)}.")
            files = {ticket_dir / rel: text for rel, text in pages.items()}
            files[ticket_dir / "review" / "diff.patch"] = diff_patch.rstrip("\n") + "\n"
            _commit(files)
            self._sync_index_unlocked(
                ticket_dir, _stage_changes(Stage.REVIEW, clear_claim=True)
            )
        return MoveResult(ticket_id, Stage.EXECUTE, Stage.REVIEW, "review submitted")

    # -- moves, claims -------------------------------------------------------

    def _validate_move(
        self, ticket_dir: Path, fm: Mapping[str, Any], target: Stage
    ) -> Stage:
        """Check a move against the state machine and its guards; return the current stage."""
        current = parse_stage(str(fm["stage"]))
        if not can_transition(current, target):
            allowed = (
                ", ".join(
                    s.value for s in sorted(TRANSITIONS[current], key=list(Stage).index)
                )
                or "none"
            )
            raise InvalidTransitionError(
                f"{current.value} cannot move to {target.value}. Allowed: {allowed}."
            )
        if target is Stage.NEED_INPUTS:
            raise InvalidTransitionError("Use request_inputs to enter Need Inputs.")
        if target is Stage.REVIEW:
            raise InvalidTransitionError("Use submit_review to enter Review.")
        if current is Stage.NEED_INPUTS:
            if any(q.status == "pending" for q in self._load_questions(ticket_dir)):
                raise InvalidTransitionError(
                    "Answer every pending question before leaving Need Inputs."
                )
            source = fm.get("source_stage")
            if (
                source
                and parse_stage(source) is Stage.EXECUTE
                and target is not Stage.EXECUTE
            ):
                raise InvalidTransitionError(
                    "A ticket paused from Execute must resume in Execute."
                )
            if (
                source
                and parse_stage(source) is Stage.PLANNING
                and target is Stage.EXECUTE
            ):
                raise InvalidTransitionError(
                    "A ticket paused from Planning cannot resume in Execute."
                )
        if (
            current is Stage.PLANNING
            and target is Stage.TODO
            and self.enforce_page_budgets
        ):
            plans = {
                p.relative_to(ticket_dir).as_posix(): p.read_text(encoding="utf-8")
                for p in (ticket_dir / "plan").glob("*.md")
            }
            if not plans:
                raise InvalidTransitionError(
                    "Planning needs at least one plan page before Todo."
                )
            self._require_clean(plans, "The plan")
            untouched = self._untouched_template_pages(ticket_dir, fm, plans)
            if untouched:
                raise InvalidTransitionError(
                    "These plan pages still match the template: "
                    f"{', '.join(untouched)}. Write them or delete the ones you do not need."
                )
        return current

    def _untouched_template_pages(
        self, ticket_dir: Path, fm: Mapping[str, Any], pages: Mapping[str, str]
    ) -> list[str]:
        """Pages whose body equals the seeded template body after placeholder substitution."""
        values = {
            "ticket_id": str(fm.get("id", ticket_dir.name)),
            "board_id": str(fm.get("board_id", "")),
            "title": str(fm.get("title", "")),
        }
        seeded: dict[str, str] = {}
        for rel, text in self._template_files().items():
            _, body = split_frontmatter(text)
            seeded[rel] = _normalise_body(_fill(body, values))
        return [
            rel
            for rel, text in pages.items()
            if rel in seeded
            and _normalise_body(split_frontmatter(text)[1]) == seeded[rel]
        ]

    def move_ticket(
        self, board_id: str, ticket_id: str, target_stage: str | Stage, reason: str = ""
    ) -> MoveResult:
        """Move a ticket if the state machine and the guards allow it.

        Need Inputs and Review are entered only through `request_inputs` and
        `submit_review`. Complete clears the claim. `reason` is returned, not stored.
        """
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        target = parse_stage(target_stage)
        with _exclusive_lock(ticket_dir / ".lock"):
            fm, _ = self._read_index(ticket_dir)
            current = self._validate_move(ticket_dir, fm, target)
            self._sync_index_unlocked(
                ticket_dir, _stage_changes(target, clear_claim=target is Stage.COMPLETE)
            )
        return MoveResult(ticket_id, current, target, reason)

    def pick_ticket(
        self,
        board_id: str,
        agent_id: str,
        from_stage: str | Stage,
        to_stage: str | Stage,
        ttl_minutes: int = 60,
        *,
        ticket_id: str | None = None,
    ) -> PickResult | None:
        """Atomically claim the lowest-id eligible ticket and advance it.

        Eligible means: in `from_stage` and unclaimed or holding an expired claim.
        Tickets locked by another process are skipped. Returns None when nothing
        is eligible; with an explicit `ticket_id` it raises instead.
        """
        source, target = parse_stage(from_stage), parse_stage(to_stage)
        if not agent_id.strip():
            raise InvalidInputError("agent_id must not be empty.")
        if ttl_minutes < 1:
            raise InvalidInputError("ttl_minutes must be at least 1.")
        if not can_transition(source, target) or target in (
            Stage.NEED_INPUTS,
            Stage.REVIEW,
        ):
            raise InvalidTransitionError(
                f"A pick cannot move {source.value} to {target.value}."
            )
        self.get_board(board_id)
        candidates = (
            [self._ticket_dir(board_id, ticket_id)]
            if ticket_id
            else [t.path for t in self.list_tickets(board_id, source)]
        )
        for ticket_dir in candidates:
            try:
                with _exclusive_lock(
                    ticket_dir / ".lock",
                    wait=DEFAULT_LOCK_WAIT_SECONDS if ticket_id else 0.0,
                ):
                    fm, _ = self._read_index(ticket_dir)
                    if parse_stage(str(fm["stage"])) is not source:
                        if ticket_id:
                            raise InvalidTransitionError(
                                f"Ticket {ticket_id} is in {fm['stage']}, not {source.value}."
                            )
                        continue
                    holder = fm.get("claimed_by")
                    expires = _parse_moment(fm.get("claim_expires_at"))
                    if holder and expires and expires > self._clock():
                        if ticket_id:
                            raise ClaimError(
                                f"Ticket {ticket_id} is claimed by {holder} until {_iso(expires)}."
                            )
                        continue
                    try:
                        self._validate_move(ticket_dir, fm, target)
                    except InvalidTransitionError:
                        if ticket_id:
                            raise
                        continue
                    expiry = _iso(self._clock() + timedelta(minutes=ttl_minutes))
                    changes = _stage_changes(target, clear_claim=False)
                    changes.update(claimed_by=agent_id, claim_expires_at=expiry)
                    self._sync_index_unlocked(ticket_dir, changes)
                    return PickResult(
                        self._summary(ticket_dir), source, target, agent_id, expiry
                    )
            except ClaimError:
                if ticket_id:
                    raise
        return None

    def release_ticket(
        self, board_id: str, ticket_id: str, agent_id: str
    ) -> TicketSummary:
        """Release `agent_id`'s claim. Releasing an unclaimed or expired ticket is a no-op."""
        ticket_dir = self._ticket_dir(board_id, ticket_id)
        with _exclusive_lock(ticket_dir / ".lock"):
            fm, _ = self._read_index(ticket_dir)
            holder = fm.get("claimed_by")
            expires = _parse_moment(fm.get("claim_expires_at"))
            if (
                holder
                and holder != agent_id
                and not (expires and expires <= self._clock())
            ):
                raise ClaimError(
                    f"Ticket {ticket_id} is claimed by {holder}, not {agent_id}."
                )
            if holder:
                self._sync_index_unlocked(
                    ticket_dir, {"claimed_by": None, "claim_expires_at": None}
                )
        return self._summary(ticket_dir)


# --------------------------------------------------------------------- module helpers


def _stage_changes(target: Stage, *, clear_claim: bool) -> dict[str, Any]:
    changes: dict[str, Any] = {
        "stage": target.value,
        "status": _STATUS_FOR_STAGE[target],
        "source_stage": None,
    }
    if clear_claim:
        changes.update(claimed_by=None, claim_expires_at=None)
    return changes


def _read_optional(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _toml_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _normalise_body(body: str) -> str:
    return "\n".join(line.rstrip() for line in body.strip().splitlines())


def _fill(text: str, values: Mapping[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def _validate_question(item: QuestionInput) -> None:
    if not (
        item.header.strip()
        and item.title.strip()
        and item.tldr.strip()
        and item.context.strip()
    ):
        raise InvalidInputError("A question needs header, title, tldr and context.")
    keys = [o.key for o in item.options]
    if len(keys) < 2:
        raise InvalidInputError("A question needs at least two options.")
    if len(set(keys)) != len(keys) or not all(_OPTION_KEY_RE.match(k) for k in keys):
        raise InvalidInputError(
            "Option keys must be unique and look like fail_open (lowercase, digits, '-', '_')."
        )


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def _render_question(
    item: QuestionInput,
    stem: str,
    number: int,
    ticket_id: str,
    source: Stage,
    today: date,
) -> str:
    fm = _ordered(
        {
            "id": stem,
            "ticket_id": ticket_id,
            "header": item.header.strip(),
            "title": " ".join(item.title.split()),
            "status": "pending",
            "source_stage": source.value,
            "multi_select": item.multi_select,
            "allow_other": item.allow_other,
            "options": [
                {"key": o.key, "label": o.label, "description": o.description}
                for o in item.options
            ],
            "selected": [],
            "other_text": None,
            "answered_at": None,
            "updated": today,
            "order": DEFAULT_QUESTION_ORDER,
        },
        _QUESTION_KEYS,
    )
    tldr = item.tldr.strip()
    tldr = tldr if tldr.startswith("**tl;dr:**") else f"**tl;dr:** {tldr}"
    table = ["| Option | Label | What it means |", "|---|---|---|"]
    table += [
        f"| `{o.key}` | {_cell(o.label)} | {_cell(o.description)} |"
        for o in item.options
    ]
    body = (
        f"# Q{number} — {fm['title']} {{#q{number}}}\n\n{tldr}\n\n"
        f"## Context\n\n{item.context.strip()}\n\n## Options comparison\n\n"
        + "\n".join(table)
    )
    return render_document(fm, body)


def _review_page(content: str, title: str, order: int, today: date) -> str:
    text = content.strip("\n")
    doc = parse_document(text + "\n")
    if doc.frontmatter is not None:
        return text + "\n"
    body = text if _H1_RE.match(text) else f"# {title}\n\n{text}"
    return render_document(
        {"title": title, "status": "review", "updated": today, "order": order},
        body,
    )
