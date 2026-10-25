"""The triage poller and the Complete-stage auto-merge (specification sections 7 and 8).

Both run only when ``[plugins.claude].enabled`` is true, which is off by default.
The merge also needs ``[plugins.claude].auto_merge = true`` (off by default), because
a merge cannot be undone.

Triage, per Todo ticket:

1. claim it with ``pick_ticket`` (Todo to Execute, with a TTL), so concurrent
   pollers never triage the same ticket twice;
2. notify the workflow;
3. run the ``triage_todo`` prompt with ``default_model``, then dispatch the
   orchestrator with ``orchestrator_model``;
4. release the claim. A failed triage leaves the ticket in Execute, unclaimed,
   with a logged warning.

Auto-merge (``enabled`` and ``auto_merge`` both true), per Complete ticket whose ``index.md`` frontmatter names both
``branch`` (the worktree branch) and ``target_branch``:

1. claim it by creating ``.merge`` in the ticket folder (exclusive create);
2. run the ``merge_worktree`` prompt with ``default_model``;
3. write the outcome to ``.merge`` and append a ``## Merge`` record to
   ``HANDOFF.md``.

A ticket missing either key is skipped with a logged notice; branches are never
guessed. A ticket with a ``.merge`` file is never merged again; delete it to retry.

Every claude call goes through an injectable `Runner` with a timeout from
``[engine].claude_timeout_seconds`` (default 1800 s).
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentville.core.config import Config, load_config
from agentville.core.errors import TownhallError
from agentville.core.logging import get_logger
from agentville.townhall.engine.client import notify_move
from agentville.townhall.markdown_ast import parse_document
from agentville.townhall.storage import Stage, TicketSummary, TownhallStorage

log = get_logger("agentville.townhall.poller")

POLLER_AGENT_ID = "agentville-poller"
DEFAULT_CLAUDE_TIMEOUT = 1800.0
MIN_CLAIM_TTL_MINUTES = 60
MERGE_MARKER = ".merge"
OUTPUT_TAIL_LINES = 20
_BRANCH_RE = re.compile(r"^(?!-)(?!.*\.\.)[A-Za-z0-9._/-]+$")


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


Runner = Callable[[Sequence[str], Path, float | None], RunResult]
"""Runs one command: ``runner(argv, cwd, timeout_seconds)``."""
Notify = Callable[..., bool]


def subprocess_runner(
    argv: Sequence[str], cwd: Path, timeout: float | None = None
) -> RunResult:
    """Run `argv` in `cwd`; a timeout returns 124 and a missing binary 127."""
    try:
        done = subprocess.run(
            list(argv),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        return RunResult(124, out, f"timed out after {timeout:g}s")
    except OSError as exc:
        return RunResult(127, "", str(exc))
    return RunResult(done.returncode, done.stdout, done.stderr)


def render_prompt(template: str, values: dict[str, str]) -> str:
    """Fill ``{{name}}`` placeholders; unknown ones stay as written."""
    return re.sub(
        r"\{\{\s*(\w+)\s*\}\}", lambda m: values.get(m.group(1), m.group(0)), template
    )


def claude_argv(config: Config, model: str, prompt: str) -> list[str]:
    claude, engine = config.plugins.claude, config.engine
    auto = list(engine.claude_auto_args) if claude.auto_mode else []
    return [engine.claude_executable, "-p", prompt, "--model", model, *auto]


def claude_timeout(config: Config) -> float:
    """``[engine].claude_timeout_seconds``; the default when it is zero or negative."""
    value = config.engine.claude_timeout_seconds
    return float(value) if value and value > 0 else DEFAULT_CLAUDE_TIMEOUT


def claim_ttl_minutes(timeout: float) -> int:
    """Long enough for triage plus the orchestrator run."""
    return max(MIN_CLAIM_TTL_MINUTES, math.ceil(2 * timeout / 60))


def ticket_branches(ticket_dir: Path) -> tuple[str, str] | str:
    """(branch, target_branch) from index.md frontmatter, or why there is none."""
    doc = parse_document((ticket_dir / "index.md").read_text(encoding="utf-8"))
    fm = doc.frontmatter or {}
    found = {key: str(fm.get(key) or "").strip() for key in ("branch", "target_branch")}
    missing = [key for key, value in found.items() if not value]
    if missing:
        return f"no {' or '.join(missing)} in index.md frontmatter"
    bad = [value for value in found.values() if not _BRANCH_RE.match(value)]
    if bad:
        return f"unsafe branch name {bad[0]!r}"
    if found["branch"] == found["target_branch"]:
        return "branch and target_branch are the same"
    return found["branch"], found["target_branch"]


def _claimed(expires: str | None, holder: str | None) -> bool:
    if not holder:
        return False
    try:
        return bool(expires) and datetime.fromisoformat(str(expires)) > datetime.now(
            UTC
        )
    except ValueError:
        return True


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tail(result: RunResult) -> str:
    text = "\n".join(p for p in (result.stdout.strip(), result.stderr.strip()) if p)
    lines = text.replace("```", "'''").splitlines()[-OUTPUT_TAIL_LINES:]
    return "\n".join(lines) or "(no output)"


class TriagePoller:
    """Triage Todo tickets and auto-merge Complete ones, when automation is on."""

    def __init__(
        self,
        root: Path | str,
        *,
        runner: Runner = subprocess_runner,
        notify: Notify = notify_move,
    ) -> None:
        self.root = Path(root).resolve()
        self.storage = TownhallStorage(self.root)
        self.runner, self.notify = runner, notify
        self.failed: set[tuple[str, str]] = set()
        self.noticed: set[tuple[str, str, str]] = set()

    def tick(self) -> list[str]:
        """One pass over every board; returns the ticket ids dispatched."""
        config = load_config(self.root)
        if not config.plugins.claude.enabled:
            return []
        dispatched = []
        for board in self.storage.list_boards():
            for ticket in self.storage.list_tickets(board.id, Stage.TODO):
                if self.triage(config, board.id, ticket):
                    dispatched.append(ticket.id)
            for ticket in self.storage.list_tickets(board.id, Stage.COMPLETE):
                self.merge(config, board.id, ticket)
        return dispatched

    # -- triage ---------------------------------------------------------------

    def triage(self, config: Config, board_id: str, ticket: TicketSummary) -> bool:
        key = (board_id, ticket.id)
        if key in self.failed or _claimed(ticket.claim_expires_at, ticket.claimed_by):
            return False
        claude, timeout = config.plugins.claude, claude_timeout(config)
        try:
            self.storage.pick_ticket(
                board_id,
                POLLER_AGENT_ID,
                Stage.TODO,
                Stage.EXECUTE,
                claim_ttl_minutes(timeout),
                ticket_id=ticket.id,
            )
        except TownhallError as exc:
            log.info("%s/%s: not claimed (%s).", board_id, ticket.id, exc)
            return False
        self.notify(
            self.root,
            board_id,
            ticket.id,
            Stage.TODO.value,
            Stage.EXECUTE.value,
            "claimed for triage",
        )
        files = sorted(
            {
                f
                for t in self.storage.list_tasks(board_id, ticket.id)
                for f in t.target_files
            }
        )
        prompt = render_prompt(
            claude.prompts.triage_todo,
            {
                "ticket_id": ticket.id,
                "board_id": board_id,
                "where_to_change": ", ".join(files) or "see the plan/ pages",
                "how_to_test": "see the plan/ pages and each task's done criteria",
            },
        )
        try:
            triage = self.runner(
                claude_argv(config, claude.default_model, prompt), self.root, timeout
            )
        except Exception as exc:  # noqa: BLE001 - an injected runner must not stop the loop
            log.warning(
                "%s/%s: triage runner raised %s: %s; left in Execute without a claim.",
                board_id,
                ticket.id,
                type(exc).__name__,
                exc,
            )
            self.failed.add(key)
            self._release(board_id, ticket.id)
            return False
        if triage.returncode != 0:
            log.warning(
                "%s/%s: triage failed (%d); left in Execute without a claim. "
                "Dispatch an agent by hand.",
                board_id,
                ticket.id,
                triage.returncode,
            )
            self.failed.add(key)
            self._release(board_id, ticket.id)
            return False
        brief = (
            f"You are the Townhall orchestrator for ticket {ticket.id} on board "
            f"{board_id}. The ticket is in Execute. Work the tasks, then call "
            f"townhall_submit_review.\n\n{triage.stdout.strip()}\n"
        )
        try:
            run = self.runner(
                claude_argv(config, claude.orchestrator_model, brief),
                self.root,
                timeout,
            )
        except Exception as exc:  # noqa: BLE001 - an injected runner must not stop the loop
            run = RunResult(1, "", f"runner raised {type(exc).__name__}: {exc}")
        if run.returncode != 0:
            log.warning(
                "%s/%s: orchestrator failed (%d): %s",
                board_id,
                ticket.id,
                run.returncode,
                run.stderr.strip()[-500:],
            )
            self.failed.add(key)
        self._release(board_id, ticket.id)
        return True

    def _release(self, board_id: str, ticket_id: str) -> None:
        try:
            self.storage.release_ticket(board_id, ticket_id, POLLER_AGENT_ID)
        except TownhallError as exc:
            log.info("%s/%s: claim not released (%s).", board_id, ticket_id, exc)

    # -- auto-merge -----------------------------------------------------------

    def merge(self, config: Config, board_id: str, ticket: TicketSummary) -> bool:
        """Merge a Complete ticket's branch once; True when a merge ran."""
        marker = ticket.path / MERGE_MARKER
        if marker.exists():
            return False
        if not config.plugins.claude.auto_merge:
            key = (board_id, ticket.id, "auto_merge is off")
            if key not in self.noticed:
                self.noticed.add(key)
                log.info(
                    "%s/%s: no auto-merge, [plugins.claude].auto_merge is false.",
                    board_id,
                    ticket.id,
                )
            return False
        branches = ticket_branches(ticket.path)
        if isinstance(branches, str):
            if (board_id, ticket.id, branches) not in self.noticed:
                self.noticed.add((board_id, ticket.id, branches))
                log.info("%s/%s: no auto-merge, %s.", board_id, ticket.id, branches)
            return False
        try:
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            return False  # another poller claimed it first
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"running {_now()}\n")
        source, target = branches
        claude = config.plugins.claude
        prompt = render_prompt(
            claude.prompts.merge_worktree,
            {
                "ticket_id": ticket.id,
                "board_id": board_id,
                "from_branch": source,
                "to_branch": target,
            },
        )
        try:
            result = self.runner(
                claude_argv(config, claude.default_model, prompt),
                self.root,
                claude_timeout(config),
            )
        except Exception as exc:  # noqa: BLE001 - an injected runner must not stop the loop
            result = RunResult(1, "", f"runner raised {type(exc).__name__}: {exc}")
        verdict = (
            "completed (exit 0)"
            if result.returncode == 0
            else f"failed (exit {result.returncode})"
        )
        marker.write_text(f"{verdict} {_now()}\n", encoding="utf-8")
        self._record_merge(
            ticket.path, source, target, claude.default_model, verdict, result
        )
        log_at = log.info if result.returncode == 0 else log.warning
        log_at(
            "%s/%s: merge %s into %s %s.", board_id, ticket.id, source, target, verdict
        )
        return True

    def _record_merge(
        self,
        ticket_dir: Path,
        source: str,
        target: str,
        model: str,
        verdict: str,
        result: RunResult,
    ) -> None:
        handoff = ticket_dir / "HANDOFF.md"
        lead = (
            ""
            if not handoff.exists()
            or handoff.read_text(encoding="utf-8").endswith("\n\n")
            else "\n"
        )
        record = (
            f"{lead}## Merge, {_now()}\n\n"
            f"- Result: {verdict}\n"
            f"- Branches: `{source}` into `{target}`\n"
            f"- Model: {model}\n"
            f"- Retry: delete `{MERGE_MARKER}` in this folder.\n\n"
            f"```text\n{_tail(result)}\n```\n"
        )
        with handoff.open("a", encoding="utf-8") as out:
            out.write(record)


def run_poller(
    root: Path | str,
    *,
    runner: Runner | None = None,
    notify: Notify | None = None,
    once: bool = False,
    interval: float | None = None,
    echo: Callable[[str], Any] | None = None,
) -> int:
    """Run the triage and merge loop, or say automation is off and return 0."""
    echo = echo or log.info
    config = load_config(Path(root))
    if not config.plugins.claude.enabled:
        echo(
            "Claude automation is disabled ([plugins.claude].enabled = false); nothing to poll."
        )
        return 0
    poller = TriagePoller(
        root, runner=runner or subprocess_runner, notify=notify or notify_move
    )
    every = interval if interval is not None else config.engine.poll_interval_seconds
    echo(f"Polling Todo and Complete tickets every {every:g}s. Ctrl-C stops.")
    try:
        while True:
            try:
                poller.tick()
            except TownhallError as exc:
                log.warning("Poll pass failed: %s", exc)
            if once:
                return 0
            time.sleep(every)
    except KeyboardInterrupt:
        echo("Poller stopped.")
        return 0
