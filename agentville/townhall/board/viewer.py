"""Full-screen Textual viewer for a Townhall ticket pack (specification sections 4 and 10.2).

``run_viewer`` launches `TicketViewerApp`: a chapter sidebar on the left, the current
page in the centre and an "On this page" tree on the right. Pages follow the order of
`TownhallStorage.get_ticket_pack`. Frontmatter is stripped, ``review/diff.patch`` renders
through Rich ``Syntax(..., "diff")`` and mermaid fences render as an accessibility panel
plus, for simple ``flowchart LR`` graphs, an ASCII diagram.

The centre uses Textual's ``Markdown`` widget inside a ``VerticalScroll`` rather than
``MarkdownViewer``: the viewer needs its own sidebar, TOC and scroll keys, which
``MarkdownViewer`` would duplicate.
"""

from __future__ import annotations

import asyncio
import logging
import re
from contextlib import suppress
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, ClassVar, Protocol

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Input,
    Label,
    Markdown,
    RadioButton,
    RadioSet,
    Static,
    Tree,
)
from textual.widgets._markdown import MarkdownFence
from textual.widgets.tree import TreeNode

from agentville.townhall.board.markdown_ast import (
    TocEntry,
    generate_toc,
    parse_mermaid_accessibility,
    split_frontmatter,
)
from agentville.townhall.board.storage import (
    Question,
    Stage,
    TaskStatus,
    TicketPack,
    TownhallStorage,
)
from agentville.townhall.core.errors import NotFoundError, TownhallError

DARK_THEME = "textual-dark"
LIGHT_THEME = "textual-light"
REVIEW_SUMMARY_PAGE = "review/review-01-summary.md"
AGENT_FILES = ("HANDOFF.md", "DRAFT.md", "review/diff.patch")
_GROUP_TITLES = {
    "draft": "Draft",
    "plan": "Plan",
    "questions": "Questions",
    "tasks": "Tasks",
    "execution": "Execution",
    "review": "Review",
}
_MAX_BOX_LABEL = 28


# ------------------------------------------------------------------ diff rendering


def diff_renderable(diff_text: str) -> Syntax:
    """The Rich renderable for a unified diff: ``Syntax(diff_text, "diff", theme="monokai")``."""
    return Syntax(diff_text, "diff", theme="monokai", word_wrap=False)


# ---------------------------------------------------------------- mermaid fallback

_ARROW_RE = re.compile(
    r"\s*(?:--\s+([^>\[\]{}()]*?)\s+-->|(?:-->|==>|-\.->)\s*\|([^|]*)\|\s*"
    r"|-->|==>|-\.->|---)\s*"
)
_NODE_RE = re.compile(
    r"""^\s*(?P<id>[A-Za-z0-9_]+)\s*
        (?:(?:\(\(|\[\(|\[|\(|\{)\s*"?(?P<label>.*?)"?\s*(?:\)\)|\)\]|\]|\)|\}))?\s*$""",
    re.VERBOSE,
)
_DIRECTION_RE = re.compile(r"^\s*(?:flowchart|graph)\s+(LR)\s*;?\s*$", re.IGNORECASE)
_SKIPPED_PREFIXES = (
    "acctitle",
    "accdescr",
    "%%",
    "classdef",
    "class ",
    "style ",
    "linkstyle",
    "click ",
    "subgraph",
    "end",
    "direction",
)


@dataclass(frozen=True)
class FlowGraph:
    """A parsed ``flowchart LR``: node labels by id (in order) and edges."""

    labels: dict[str, str]
    edges: tuple[tuple[str, str, str], ...]


def parse_flowchart(source: str) -> FlowGraph | None:
    """Parse a simple ``flowchart LR`` / ``graph LR``; None when it is anything else."""
    lines = [line.strip() for line in source.strip().splitlines() if line.strip()]
    if not lines or not _DIRECTION_RE.match(lines[0]):
        return None
    labels: dict[str, str] = {}
    edges: list[tuple[str, str, str]] = []
    for line in lines[1:]:
        if line.lower().startswith(_SKIPPED_PREFIXES):
            continue
        matches = list(_ARROW_RE.finditer(line))
        parts: list[str] = []
        edge_labels: list[str] = []
        cursor = 0
        for match in matches:
            parts.append(line[cursor : match.start()])
            edge_labels.append((match.group(1) or match.group(2) or "").strip())
            cursor = match.end()
        parts.append(line[cursor:])
        ids: list[str] = []
        for part in parts:
            node = _NODE_RE.match(part)
            if node is None:
                return None
            node_id = node.group("id")
            label = node.group("label")
            if label is not None or node_id not in labels:
                labels[node_id] = label if label else node_id
            ids.append(node_id)
        edges.extend(
            (ids[i], ids[i + 1], edge_labels[i]) for i in range(len(edge_labels))
        )
    if not edges:
        return None
    return FlowGraph(labels, tuple(edges))


def _clip(label: str) -> str:
    label = " ".join(label.split())
    return label if len(label) <= _MAX_BOX_LABEL else label[: _MAX_BOX_LABEL - 1] + "…"


def _box_row(items: list[str], arrows: list[str]) -> list[str]:
    """Three text lines: boxes for `items`, joined by `arrows` on the middle line."""
    top, mid, bottom = "", "", ""
    for index, item in enumerate(items):
        text = _clip(item)
        top += "┌" + "─" * (len(text) + 2) + "┐"
        mid += f"│ {text} │"
        bottom += "└" + "─" * (len(text) + 2) + "┘"
        if index < len(arrows):
            arrow = arrows[index]
            top += " " * len(arrow)
            mid += arrow
            bottom += " " * len(arrow)
    return [top, mid, bottom]


def _arrow(label: str) -> str:
    return f"──{_clip(label)}──>" if label else "──>"


def _chain_order(graph: FlowGraph) -> list[str] | None:
    """Node ids in order when the graph is one straight chain, else None."""
    outgoing: dict[str, tuple[str, str]] = {}
    incoming: set[str] = set()
    for source, target, label in graph.edges:
        if source in outgoing or target in incoming:
            return None
        outgoing[source] = (target, label)
        incoming.add(target)
    starts = [
        node for node in graph.labels if node in outgoing and node not in incoming
    ]
    if len(starts) != 1:
        return None
    order = [starts[0]]
    while order[-1] in outgoing:
        following = outgoing[order[-1]][0]
        if following in order:
            return None
        order.append(following)
    return order if len(order) == len(graph.labels) else None


def render_ascii_flowchart(source: str) -> str | None:
    """Box-drawing text for a simple ``flowchart LR``; None when it cannot be drawn.

    A straight chain ``A --> B --> C`` becomes one row of boxes joined by ``──>``.
    A graph that branches or merges is drawn one edge per row.
    """
    graph = parse_flowchart(source)
    if graph is None:
        return None
    order = _chain_order(graph)
    rows: list[list[str]] = []
    if order is not None:
        labels_by_edge = {(s, t): lab for s, t, lab in graph.edges}
        arrows = [
            _arrow(labels_by_edge[(order[i], order[i + 1])])
            for i in range(len(order) - 1)
        ]
        rows.append(_box_row([graph.labels[n] for n in order], arrows))
    else:
        rows.extend(
            _box_row([graph.labels[s], graph.labels[t]], [_arrow(lab)])
            for s, t, lab in graph.edges
        )
    return "\n\n".join("\n".join(line.rstrip() for line in row) for row in rows)


def mermaid_renderable(source: str) -> RenderableType:
    """A bordered accessibility panel, then the ASCII flowchart when one can be drawn."""
    title, description = parse_mermaid_accessibility(source)
    body = Text()
    body.append("Diagram: ", style="bold")
    body.append(title or "no accTitle given")
    body.append("\n")
    body.append(description or "No accDescr given for this diagram.")
    panel = Panel(body, title="Mermaid (text description)", border_style="cyan")
    ascii_art = render_ascii_flowchart(source)
    if ascii_art is None:
        return panel
    return Group(panel, Text(ascii_art, no_wrap=True, overflow="ignore"))


class TownhallFence(MarkdownFence):
    """A fence block that draws mermaid fences with `mermaid_renderable`."""

    DEFAULT_CSS = """
    TownhallFence > Static { padding: 1 2; width: auto; }
    """

    @property
    def is_mermaid(self) -> bool:
        return (self.lexer or "").strip().lower() == "mermaid"

    def compose(self) -> ComposeResult:
        if self.is_mermaid:
            yield Static(mermaid_renderable(self.code), id="mermaid-content")
        else:
            yield from super().compose()

    def set_content(self, content: Any) -> None:
        if not self.is_mermaid:
            super().set_content(content)
            return
        with suppress(NoMatches):
            self.query_one("#mermaid-content", Static).update(
                mermaid_renderable(self.code)
            )


class TownhallMarkdown(Markdown):
    """Markdown that renders mermaid fences through the fallback."""

    BLOCKS: ClassVar[dict[str, type]] = {**Markdown.BLOCKS, "fence": TownhallFence}


# -------------------------------------------------------------------------- pages

_HEADING_ID_RE = re.compile(r"^(#{1,6}\s.*?)\s+\{#[A-Za-z][\w-]*\}\s*$")


def strip_heading_ids(text: str) -> str:
    """Drop ``{#id}`` suffixes from headings outside code fences, for display."""
    out = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
        elif not in_fence:
            match = _HEADING_ID_RE.match(line)
            if match:
                line = match.group(1)
        out.append(line)
    return "\n".join(out)


@dataclass(frozen=True)
class ViewPage:
    """One page of the handbook sequence."""

    rel_path: str
    group: str
    label: str
    text: str
    kind: str = "markdown"  # markdown | diff

    @property
    def is_question(self) -> bool:
        return self.rel_path.startswith("questions/") and self.rel_path.endswith(".md")


def match_page(rel_paths: list[str], wanted: str) -> int | None:
    """Index of the page `wanted` names: a full path, with or without ``.md``, or a bare file name."""
    needle = wanted.removesuffix(".md")
    for index, rel_path in enumerate(rel_paths):
        stem = rel_path.removesuffix(".md")
        if needle in (stem, PurePosixPath(stem).name):
            return index
    return None


def _group_for(rel_path: str) -> str:
    if "/" not in rel_path:
        return ""
    folder = rel_path.split("/", 1)[0]
    return _GROUP_TITLES.get(folder, folder.title())


def _page_label(rel_path: str, order: int | None) -> str:
    stem = PurePosixPath(rel_path).stem if rel_path.endswith(".md") else rel_path
    if rel_path == "index.md":
        return "00 Overview (index.md)"
    prefix = f"{order:02d} " if order is not None else ""
    return f"{prefix}{stem}"


def _answer_note(question: Question) -> str:
    if question.status == "pending":
        return "\n\n---\n\n**Status:** pending. Press `a` to answer.\n"
    chosen = ", ".join(f"`{key}`" for key in question.selected) or "none"
    note = f"\n\n---\n\n**Status:** answered. Selected: {chosen}."
    if question.other_text:
        note += f" Other: {question.other_text}"
    return note + "\n"


# ------------------------------------------------------------------------- modals


class AnswerModal(ModalScreen["tuple[list[str], str | None] | None"]):
    """Pick an answer: radio buttons for one choice, checkboxes for many, optional "Other"."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    AnswerModal { align: center middle; }
    AnswerModal > Vertical {
        width: 80%; max-width: 90; height: auto; max-height: 90%;
        padding: 1 2; border: thick $primary; background: $surface; overflow-y: auto;
    }
    AnswerModal .title { text-style: bold; margin-bottom: 1; }
    AnswerModal .error { color: $error; }
    AnswerModal Horizontal { height: auto; margin-top: 1; }
    AnswerModal Button { margin-right: 2; }
    """

    def __init__(self, question: Question) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        question = self.question
        with Vertical():
            yield Label(f"{question.header}: {question.title}", classes="title")
            if question.multi_select:
                for index, option in enumerate(question.options):
                    yield Checkbox(self._option_label(option), id=f"opt-{index}")
            else:
                with RadioSet(id="choices"):
                    for index, option in enumerate(question.options):
                        yield RadioButton(self._option_label(option), id=f"opt-{index}")
            if question.allow_other:
                yield Input(placeholder="Other (free text)", id="other")
            yield Label("", id="error", classes="error")
            with Horizontal():
                yield Button("Save", id="save", variant="primary")
                yield Button("Cancel", id="cancel")

    @staticmethod
    def _option_label(option: Any) -> str:
        return (
            f"{option.label} - {option.description}"
            if option.description
            else option.label
        )

    def chosen_keys(self) -> list[str]:
        options = self.question.options
        if self.question.multi_select:
            return [
                options[i].key
                for i in range(len(options))
                if self.query_one(f"#opt-{i}", Checkbox).value
            ]
        index = self.query_one("#choices", RadioSet).pressed_index
        return [options[index].key] if index >= 0 else []

    def other_text(self) -> str | None:
        if not self.question.allow_other:
            return None
        return self.query_one("#other", Input).value.strip() or None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        keys, other = self.chosen_keys(), self.other_text()
        if not keys and not other:
            self.query_one("#error", Label).update(
                "Choose an option or write an answer."
            )
            return
        self.dismiss((keys, other))

    def action_cancel(self) -> None:
        self.dismiss(None)


class ReviewModal(ModalScreen["tuple[str, str] | None"]):
    """Approve or reject a ticket in Review. Rejecting needs a reason."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    ReviewModal { align: center middle; }
    ReviewModal > Vertical {
        width: 70%; max-width: 80; height: auto; padding: 1 2;
        border: thick $primary; background: $surface;
    }
    ReviewModal .title { text-style: bold; margin-bottom: 1; }
    ReviewModal .error { color: $error; }
    ReviewModal Horizontal { height: auto; margin-top: 1; }
    ReviewModal Button { margin-right: 2; }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Review decision", classes="title")
            yield Label(
                "Approve moves the ticket to Complete; reject sends it back to Discuss."
            )
            yield Input(placeholder="Reason (required to reject)", id="reason")
            yield Label("", id="error", classes="error")
            with Horizontal():
                yield Button("Approve", id="approve", variant="success")
                yield Button("Reject", id="reject", variant="error")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        reason = self.query_one("#reason", Input).value.strip()
        match event.button.id:
            case "approve":
                self.dismiss(("approve", reason))
            case "reject":
                if not reason:
                    self.query_one("#error", Label).update("Give a reason to reject.")
                    return
                self.dismiss(("reject", reason))
            case _:
                self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# --------------------------------------------------------------------------- app


LOGGER = logging.getLogger(__name__)


class MoveNotifier(Protocol):
    """Tells a ticket's workflow about a move already made on disk; never raises."""

    def __call__(
        self,
        root: Any,
        board_id: str,
        ticket_id: str,
        from_stage: str | None,
        to_stage: str,
        reason: str = "",
    ) -> object: ...


def _default_notifier(*args: Any) -> object:
    from agentville.townhall.board.workflows import notify_move

    return notify_move(*args)


class TicketViewerApp(App[None]):
    """Three-pane handbook viewer for one ticket pack."""

    TITLE = "Townhall"
    CSS = """
    #topbar { height: 1; background: $primary; color: $text; padding: 0 1; }
    #topbar-title { width: 1fr; text-style: bold; }
    #topbar-stage { width: auto; }
    #panes { height: 1fr; }
    #sidebar-pane { width: 34; border: round $primary-darken-1; }
    #toc-pane { width: 28; border: round $primary-darken-1; }
    #centre { width: 1fr; border: round $primary-darken-1; }
    #sidebar, #toc { height: 1fr; background: transparent; }
    #pagebar { height: 1; padding: 0 1; text-style: bold; }
    #doc { height: 1fr; padding: 0 1; }
    #diff { width: auto; min-width: 100%; }
    #navhints { height: 1; }
    #prev-hint { width: 1fr; padding: 0 1; color: $text-muted; }
    #next-hint { width: 1fr; padding: 0 1; color: $text-muted; text-align: right; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("j,down", "line_down", "Scroll down", show=False),
        Binding("k,up", "line_up", "Scroll up", show=False),
        Binding("h,left", "previous_page", "Prev page", key_display="h"),
        Binding("l,right", "next_page", "Next page", key_display="l"),
        Binding("d", "half_down", "Half page down", show=False),
        Binding("u", "half_up", "Half page up", show=False),
        Binding("g", "top", "Top", show=False),
        Binding("G", "bottom", "Bottom", show=False),
        Binding("t", "focus_toc", "TOC"),
        Binding("s", "focus_sidebar", "Sidebar"),
        Binding("a", "answer", "Answer"),
        Binding("H", "toggle_agent_files", "Agent files"),
        Binding("T", "toggle_theme", "Theme"),
        Binding("q,Q", "quit", "Quit"),
    ]

    def __init__(
        self,
        storage: TownhallStorage,
        board_id: str,
        ticket_id: str,
        page: str | None = None,
        notifier: MoveNotifier | None = None,
    ) -> None:
        super().__init__()
        self.notifier: MoveNotifier = notifier or _default_notifier
        self.storage = storage
        self.board_id = board_id
        self.ticket_id = ticket_id
        self.initial_page = page
        self.show_agent_files = False
        self.pages: list[ViewPage] = []
        self.page_index = 0
        self.toc: list[TocEntry] = []
        self.pack: TicketPack | None = None
        self.questions: list[Question] = []
        self._sidebar_nodes: dict[str, TreeNode[str | None]] = {}
        self._toc_ready = False

    # -- composition --------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Horizontal(id="topbar"):
            yield Static("", id="topbar-title")
            yield Static("", id="topbar-stage")
        with Horizontal(id="panes"):
            with Vertical(id="sidebar-pane"):
                sidebar: Tree[str | None] = Tree("Chapters", id="sidebar")
                sidebar.show_root = False
                yield sidebar
            with Vertical(id="centre"):
                yield Static("", id="pagebar")
                with VerticalScroll(id="doc"):
                    yield TownhallMarkdown("", id="md", open_links=False)
                    yield Static("", id="diff")
                with Horizontal(id="navhints"):
                    yield Static("", id="prev-hint")
                    yield Static("", id="next-hint")
            with Vertical(id="toc-pane"):
                toc: Tree[int] = Tree("On this page", id="toc")
                toc.show_root = False
                toc.auto_expand = False
                yield toc
        yield Footer()

    async def on_mount(self) -> None:
        self.theme = DARK_THEME
        self.query_one("#sidebar-pane").border_title = "CHAPTERS"
        self.query_one("#toc-pane").border_title = "ON THIS PAGE"
        self.query_one("#diff", Static).display = False
        self._load()
        try:
            index = self._find_page(self.initial_page)
        except NotFoundError:
            self.show_agent_files = True  # the page may be an agent-only file
            self._load()
            index = self._find_page(self.initial_page)
        await self.show_page(index)
        self.doc.focus()

    # -- data ---------------------------------------------------------------

    @property
    def doc(self) -> VerticalScroll:
        return self.query_one("#doc", VerticalScroll)

    @property
    def sidebar(self) -> Tree[str | None]:
        return self.query_one("#sidebar", Tree)

    @property
    def toc_tree(self) -> Tree[int]:
        return self.query_one("#toc", Tree)

    @property
    def current_page(self) -> ViewPage:
        return self.pages[self.page_index]

    def _load(self) -> None:
        """Read the pack, build the page sequence and redraw the sidebar and header."""
        pack = self.storage.get_ticket_pack(
            self.board_id, self.ticket_id, include_agent_files=self.show_agent_files
        )
        self.pack = pack
        self.questions = self.storage.list_questions(self.board_id, self.ticket_id)
        questions = {q.file_name: q for q in self.questions}
        grouped: dict[str, list[ViewPage]] = {}
        for page in pack.pages:
            text = page.body
            if page.rel_path.startswith("questions/"):
                question = questions.get(PurePosixPath(page.rel_path).name)
                if question is not None:
                    text += _answer_note(question)
            group = _group_for(page.rel_path)
            if page.rel_path == "GLOSSARY.md":
                group = "Glossary"
            grouped.setdefault(group, []).append(
                ViewPage(
                    page.rel_path,
                    group,
                    _page_label(page.rel_path, page.order),
                    text,
                )
            )
        agent: list[ViewPage] = []
        if self.show_agent_files:
            if pack.handoff is not None:
                agent.append(self._agent_page("HANDOFF.md", pack.handoff))
            if pack.draft is not None:
                agent.append(self._agent_page("DRAFT.md", pack.draft))
            if pack.diff_patch is not None:
                agent.append(
                    ViewPage(
                        "review/diff.patch",
                        "Agent files",
                        "review/diff.patch",
                        pack.diff_patch,
                        "diff",
                    )
                )
        if agent:
            grouped["Agent files"] = agent
        self.pages = [page for pages in grouped.values() for page in pages]
        self._rebuild_sidebar(grouped)
        self._refresh_header()

    @staticmethod
    def _agent_page(rel_path: str, content: str) -> ViewPage:
        _, body = split_frontmatter(content)
        return ViewPage(rel_path, "Agent files", rel_path, body.lstrip("\n"))

    def _find_page(self, wanted: str | None) -> int:
        if wanted is None:
            return 0
        index = match_page(self.sidebar_pages(), wanted)
        if index is None:
            raise NotFoundError(
                f"Page '{wanted}' not found in ticket {self.ticket_id}."
            )
        return index

    def sidebar_pages(self) -> list[str]:
        """Relative paths of the pages listed in the sidebar, in order."""
        return [page.rel_path for page in self.pages]

    def sidebar_groups(self) -> list[str]:
        """Labels of the sidebar's group nodes, in order."""
        return [
            str(node.label) for node in self.sidebar.root.children if node.data is None
        ]

    # -- sidebar and header -------------------------------------------------

    def _group_label(self, group: str) -> str:
        if group == "Questions":
            pending = sum(1 for q in self.questions if q.status == "pending")
            return f"{group} ({pending} Pending!)" if pending else group
        if group == "Tasks" and self.pack is not None:
            done = sum(1 for t in self._tasks() if t.status is TaskStatus.DONE)
            return f"{group} ({done}/{len(self._tasks())})"
        return group

    def _tasks(self) -> list[Any]:
        return self.storage.list_tasks(self.board_id, self.ticket_id)

    def _leaf_label(self, page: ViewPage) -> str:
        suffix = ""
        name = PurePosixPath(page.rel_path).name
        if page.group == "Tasks":
            done = {t.file_name for t in self._tasks() if t.status is TaskStatus.DONE}
            suffix = " ✓" if name in done else ""
        elif page.is_question:
            answered = {q.file_name for q in self.questions if q.status == "answered"}
            suffix = " ✓" if name in answered else " ?"
        marker = "❯ " if self.pages and page is self.current_page else "  "
        return f"{marker}{page.label}{suffix}"

    def _rebuild_sidebar(self, grouped: dict[str, list[ViewPage]]) -> None:
        tree = self.sidebar
        tree.clear()
        self._sidebar_nodes = {}
        for group, pages in grouped.items():
            if group in ("", "Glossary"):
                for page in pages:
                    self._sidebar_nodes[page.rel_path] = tree.root.add_leaf(
                        self._leaf_label(page), data=page.rel_path
                    )
                continue
            parent = tree.root.add(self._group_label(group), expand=True)
            for page in pages:
                self._sidebar_nodes[page.rel_path] = parent.add_leaf(
                    self._leaf_label(page), data=page.rel_path
                )
        tree.root.expand()

    def _refresh_sidebar_labels(self) -> None:
        for page in self.pages:
            node = self._sidebar_nodes.get(page.rel_path)
            if node is not None:
                node.set_label(self._leaf_label(page))
        for node in self.sidebar.root.children:
            if node.data is None:
                node.set_label(self._group_label(self._group_of(node)))

    @staticmethod
    def _group_of(node: TreeNode[str | None]) -> str:
        return str(node.label).split(" (", 1)[0]

    def _refresh_header(self) -> None:
        assert self.pack is not None
        ticket = self.storage.get_ticket(self.board_id, self.ticket_id)
        self.query_one("#topbar-title", Static).update(
            f"{self.board_id} / Ticket {ticket.id}: {ticket.title}"
        )
        self.query_one("#topbar-stage", Static).update(f"Stage: {ticket.stage.value}")

    # -- showing a page -----------------------------------------------------

    async def show_page(self, index: int) -> None:
        """Make page `index` current: render it, rebuild the TOC and sync the sidebar."""
        if not self.pages:
            return
        self.page_index = max(0, min(index, len(self.pages) - 1))
        page = self.current_page
        md = self.query_one("#md", TownhallMarkdown)
        diff = self.query_one("#diff", Static)
        if page.kind == "diff":
            md.display = False
            diff.display = True
            diff.update(diff_renderable(page.text))
            self.toc = []
        else:
            diff.display = False
            md.display = True
            text = strip_heading_ids(page.text)
            self.toc = generate_toc(text)
            await md.update(text)
        self.doc.scroll_home(animate=False)
        self._rebuild_toc()
        self._refresh_chrome()

    def _refresh_chrome(self) -> None:
        page = self.current_page
        total = len(self.pages)
        self.query_one("#pagebar", Static).update(
            f"{page.rel_path} (Page {self.page_index + 1} of {total})"
        )
        before = self.pages[self.page_index - 1] if self.page_index > 0 else None
        after = self.pages[self.page_index + 1] if self.page_index + 1 < total else None
        self.query_one("#prev-hint", Static).update(
            f"← Prev: {self._short(before)} (h)" if before else ""
        )
        self.query_one("#next-hint", Static).update(
            f"Next: {self._short(after)} (l) →" if after else ""
        )
        self._refresh_sidebar_labels()
        node = self._sidebar_nodes.get(page.rel_path)
        if node is not None:
            self.sidebar.move_cursor(node)

    @staticmethod
    def _short(page: ViewPage | None) -> str:
        return PurePosixPath(page.rel_path).stem if page else ""

    def _rebuild_toc(self) -> None:
        tree = self.toc_tree
        tree.clear()
        stack: list[tuple[int, TreeNode[int]]] = []
        for index, entry in enumerate(self.toc):
            while stack and stack[-1][0] >= entry.level:
                stack.pop()
            parent = stack[-1][1] if stack else tree.root
            node = parent.add(entry.title, data=index, expand=True)
            stack.append((entry.level, node))
        tree.root.expand()
        for node in tree.root.children:
            self._prune_leaves(node)

    def _prune_leaves(self, node: TreeNode[int]) -> None:
        node.allow_expand = bool(node.children)
        for child in node.children:
            self._prune_leaves(child)

    async def _jump_to_heading(self, toc_index: int) -> None:
        md = self.query_one("#md", TownhallMarkdown)
        headings = list(md.query("MarkdownH1, MarkdownH2, MarkdownH3"))
        if toc_index >= len(self.toc) or not headings:
            return
        if len(headings) == len(self.toc):
            target = headings[toc_index]
        else:
            title = self.toc[toc_index].title
            target = next(
                (
                    h
                    for h in headings
                    if h.source_range and str(h._content).strip() == title
                ),
                headings[min(toc_index, len(headings) - 1)],
            )
        self.doc.scroll_to_widget(target, top=True, animate=False)

    # -- events -------------------------------------------------------------

    async def on_tree_node_selected(self, event: Tree.NodeSelected[Any]) -> None:
        event.stop()
        if event.control.id == "toc":
            if isinstance(event.node.data, int):
                await self._jump_to_heading(event.node.data)
        elif event.control.id == "sidebar" and isinstance(event.node.data, str):
            await self.show_page(self.sidebar_pages().index(event.node.data))

    async def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        event.stop()
        href = event.href
        if "://" in href or href.startswith("mailto:"):
            self.open_url(href)
            return
        path = href.split("#", 1)[0]
        if not path:
            return
        base = PurePosixPath(self.current_page.rel_path).parent
        parts: list[str] = []
        for part in (base / path).parts:
            if part == "..":
                if parts:
                    parts.pop()
            elif part != ".":
                parts.append(part)
        target = "/".join(parts)
        if target in self.sidebar_pages():
            await self.show_page(self.sidebar_pages().index(target))
        else:
            self.notify(f"{target} is not in this pack.", severity="warning")

    # -- actions: scrolling -------------------------------------------------

    def action_line_down(self) -> None:
        focused = self.focused
        if isinstance(focused, Tree):
            focused.action_cursor_down()
        else:
            self.doc.scroll_to(y=self.doc.scroll_y + 1, animate=False)

    def action_line_up(self) -> None:
        focused = self.focused
        if isinstance(focused, Tree):
            focused.action_cursor_up()
        else:
            self.doc.scroll_to(y=max(0, self.doc.scroll_y - 1), animate=False)

    def action_half_down(self) -> None:
        self.doc.scroll_to(
            y=self.doc.scroll_y + max(1, self.doc.size.height // 2), animate=False
        )

    def action_half_up(self) -> None:
        self.doc.scroll_to(
            y=max(0, self.doc.scroll_y - max(1, self.doc.size.height // 2)),
            animate=False,
        )

    def action_top(self) -> None:
        self.doc.scroll_home(animate=False)

    def action_bottom(self) -> None:
        self.doc.scroll_end(animate=False, immediate=True)

    # -- actions: navigation ------------------------------------------------

    async def action_previous_page(self) -> None:
        if self.page_index > 0:
            await self.show_page(self.page_index - 1)

    async def action_next_page(self) -> None:
        if self.page_index + 1 < len(self.pages):
            await self.show_page(self.page_index + 1)

    def action_focus_toc(self) -> None:
        if self.focused is self.toc_tree:
            self.doc.focus()
        else:
            self.toc_tree.focus()

    def action_focus_sidebar(self) -> None:
        if self.focused is self.sidebar:
            self.doc.focus()
        else:
            self.sidebar.focus()

    async def action_toggle_agent_files(self) -> None:
        keep = self.current_page.rel_path
        self.show_agent_files = not self.show_agent_files
        self._load()
        known = self.sidebar_pages()
        await self.show_page(known.index(keep) if keep in known else 0)

    def action_toggle_theme(self) -> None:
        self.theme = LIGHT_THEME if self.theme == DARK_THEME else DARK_THEME

    # -- actions: answer and review ----------------------------------------

    def action_answer(self) -> None:
        page = self.current_page
        if page.rel_path == REVIEW_SUMMARY_PAGE:
            self.push_screen(ReviewModal(), self._after_review)
            return
        if not page.is_question:
            self.notify("Open a question page to answer it.", severity="warning")
            return
        name = PurePosixPath(page.rel_path).name
        question = next((q for q in self.questions if q.file_name == name), None)
        if question is None:
            self.notify(f"Question {name} not found.", severity="error")
        elif question.status == "answered":
            self.notify("This question is already answered.", severity="warning")
        else:
            self.push_screen(AnswerModal(question), self._after_answer)

    async def _after_answer(self, result: tuple[list[str], str | None] | None) -> None:
        if result is None:
            return
        selected, other = result
        name = PurePosixPath(self.current_page.rel_path).name
        try:
            self.storage.answer_question(
                self.board_id, self.ticket_id, name, selected, other
            )
        except TownhallError as error:
            self.notify(str(error), severity="error")
            return
        self.notify("Answer saved.")
        await self._reload_in_place()

    async def _after_review(self, result: tuple[str, str] | None) -> None:
        if result is None:
            return
        decision, reason = result
        target = Stage.COMPLETE if decision == "approve" else Stage.DISCUSS
        try:
            moved = self.storage.move_ticket(
                self.board_id, self.ticket_id, target, reason
            )
        except TownhallError as error:
            self.notify(str(error), severity="error")
            return
        # notify_move waits up to 1 s for the server, so run it off the UI thread.
        try:
            await asyncio.to_thread(
                self.notifier,
                self.storage.root,
                self.board_id,
                self.ticket_id,
                moved.from_stage.value,
                moved.to_stage.value,
                moved.reason,
            )
        except Exception:  # the move is done; a notifier must not break the UI
            LOGGER.warning("Workflow notification failed", exc_info=True)
        self.notify(f"Ticket moved to {target.value}.")
        await self._reload_in_place()

    async def _reload_in_place(self) -> None:
        keep = self.current_page.rel_path
        self._load()
        known = self.sidebar_pages()
        await self.show_page(known.index(keep) if keep in known else 0)


def run_viewer(
    storage: TownhallStorage,
    board_id: str,
    ticket_id: str,
    page: str | None = None,
) -> None:
    """Launch the full-screen viewer for one ticket; `page` picks the first page shown.

    Raises NotFoundError when the ticket or the page does not exist.
    """
    storage.get_ticket(board_id, ticket_id)
    if page is not None:
        pack = storage.get_ticket_pack(board_id, ticket_id)
        known = [p.rel_path for p in pack.pages] + [
            name
            for name, content in zip(
                AGENT_FILES, (pack.handoff, pack.draft, pack.diff_patch), strict=True
            )
            if content is not None
        ]
        if match_page(known, page) is None:
            raise NotFoundError(f"Page '{page}' not found in ticket {ticket_id}.")
    TicketViewerApp(storage, board_id, ticket_id, page).run()
