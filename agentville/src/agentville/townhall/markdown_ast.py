"""Markdown parsing, frontmatter handling and the Townhall page-budget linter.

The linter implements the handbook page-budget rules of the Townhall
specification (section 5.2) on top of a ``markdown-it-py`` token stream.
Every finding is structured: a rule id, the file, a 1-based line and a message.

Rule ids
--------
``FM001``      frontmatter block missing or not valid YAML.
``FM002``      a required frontmatter key is missing or has the wrong type.
``TLDR001``    the first paragraph after the H1 is not a ``**tl;dr:**`` paragraph.
``TLDR002``    the tl;dr does not hold 3 to 6 sentences.
``TLDR003``    the tl;dr exceeds 100 words.
``SIZE001``    more than 4 ``h2`` sections (``index.md`` is exempt).
``SIZE002``    a heading deeper than ``h3``.
``SIZE003``    more than 250 lines.
``PARA001``    a prose paragraph with more than 6 sentences.
``TABLE001``   three or more named items written as bullets (warning, heuristic).
``MERMAID001`` a page that must carry a diagram has no ``mermaid`` block.
``MERMAID002`` a ``mermaid`` block lacks ``accTitle:`` or ``accDescr:``.
``ANCHOR001``  a T/Q/R heading lacks its explicit ``{#id}`` anchor.

``DRAFT.md`` and ``HANDOFF.md`` are agent-only and bypass every rule.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.tasklists import tasklists_plugin

__all__ = [
    "AGENT_ONLY_FILES",
    "Document",
    "LintFinding",
    "Severity",
    "TocEntry",
    "create_townhall_parser",
    "generate_toc",
    "has_errors",
    "is_agent_only",
    "lint_markdown",
    "parse_document",
    "parse_mermaid_accessibility",
    "render_document",
    "split_frontmatter",
]

REQUIRED_FRONTMATTER_KEYS: tuple[str, ...] = ("title", "status", "updated", "order")
AGENT_ONLY_FILES: frozenset[str] = frozenset({"DRAFT.md", "HANDOFF.md"})
TLDR_MARKER = "**tl;dr:**"
TLDR_MIN_SENTENCES = 3
TLDR_MAX_SENTENCES = 6
TLDR_MAX_WORDS = 100
MAX_H2 = 4
MAX_HEADING_LEVEL = 3
MAX_LINES = 250
MAX_PARAGRAPH_SENTENCES = 6
DECISION_ITEMS_THRESHOLD = 3

_FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\n(.*?)(?:\n)?^---[ \t]*(?:\n|\Z)", re.DOTALL | re.MULTILINE
)
_ANCHOR_RE = re.compile(r"\s*\{#([A-Za-z][A-Za-z0-9_-]*)\}\s*$")
_NAMED_HEADING_RE = re.compile(r"^([TQR])(\d+)\s*[—–-]\s*\S")
_ABBREVIATION_RE = re.compile(
    r"\b(e\.g|i\.e|etc|vs|cf|approx|incl|resp)\.", re.IGNORECASE
)
_SENTENCE_END_RE = re.compile(r"(?<=[.!?…])[\"')\]*_]*\s+(?=[A-Z0-9\"'(\[`\x00*_])")
_ARCHITECTURE_PAGE_RE = re.compile(r"^plan-\d+-.*architecture.*\.md$")
_ACC_TITLE_RE = re.compile(r"^[ \t]*accTitle[ \t]*:[ \t]*(\S.*)$", re.MULTILINE)
_ACC_DESCR_RE = re.compile(r"^[ \t]*accDescr[ \t]*:[ \t]*(\S.*)$", re.MULTILINE)
_ACC_DESCR_BLOCK_RE = re.compile(
    r"^[ \t]*accDescr[ \t]*\{(.*?)\}", re.MULTILINE | re.DOTALL
)
_NAMED_ITEM_RE = re.compile(
    r"^(?:\*\*[^*]+\*\*|`[^`]+`)\s*(?::|=|->|—|–)\s*\S.*?(?:\s[—–]\s|;\s|\bbecause\b|\bso that\b)\s*\S"
)


class Severity(StrEnum):
    """How seriously a finding is treated."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class LintFinding:
    """One linter finding. `line` is 1-based; 1 for file-level findings."""

    rule: str
    file: str
    line: int
    message: str
    severity: Severity = Severity.ERROR

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly mapping."""
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


def has_errors(findings: Sequence[LintFinding]) -> bool:
    """Return True when any finding has error severity."""
    return any(f.severity is Severity.ERROR for f in findings)


# --------------------------------------------------------------------------- parser


def create_townhall_parser() -> MarkdownIt:
    """Build the shared parser (specification 5.1).

    Deviation: ``anchors_plugin`` only generates slug ids from heading text and does
    not read ``{#id}`` suffixes, so explicit anchors are recognised by this module
    (see ``generate_toc`` and the ``ANCHOR001`` rule).
    """
    return (
        MarkdownIt("gfm-like", {"linkify": True, "typographer": True})
        .use(front_matter_plugin)
        .use(anchors_plugin, min_level=1, max_level=3, permalink=False)
        .use(tasklists_plugin, enabled=True)
        .use(footnote_plugin)
    )


# ----------------------------------------------------------------------- frontmatter


@dataclass
class Document:
    """A Markdown file split into frontmatter and body."""

    frontmatter: dict[str, Any] | None
    body: str
    error: str | None = field(default=None)


class _StableDumper(yaml.SafeDumper):
    """YAML dumper with indented sequences, for stable and readable output."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (raw YAML, body) or (None, text) when there is no frontmatter block."""
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return None, text
    return match.group(1), text[match.end() :]


def parse_document(text: str) -> Document:
    """Parse `text`; `frontmatter` is None when absent or invalid (`error` says why)."""
    raw, body = split_frontmatter(text)
    body = body.lstrip("\n")
    if raw is None:
        return Document(None, text, "no frontmatter block")
    try:
        data = yaml.safe_load(raw) if raw.strip() else {}
    except yaml.YAMLError as error:
        return Document(None, body, f"invalid YAML: {str(error).splitlines()[0]}")
    if not isinstance(data, dict):
        return Document(None, body, "frontmatter is not a mapping")
    return Document({str(k): v for k, v in data.items()}, body)


def render_document(frontmatter: dict[str, Any], body: str) -> str:
    """Serialise deterministically: stable key order, one trailing newline."""
    dumped = yaml.dump(
        frontmatter,
        Dumper=_StableDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=1_000_000,
    )
    return f"---\n{dumped}---\n\n{body.strip(chr(10))}\n"


# ------------------------------------------------------------------------- text help


def _inline_text(inline: Token) -> tuple[str, str]:
    """Return (plain text, text with inline code collapsed) for an inline token."""
    plain: list[str] = []
    collapsed: list[str] = []
    for child in inline.children or []:
        if child.type == "code_inline":
            plain.append(child.content)
            collapsed.append("\x00")
        elif child.type in {"text", "image"}:
            plain.append(child.content)
            collapsed.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            plain.append(" ")
            collapsed.append(" ")
    return "".join(plain), "".join(collapsed)


def _count_sentences(collapsed: str) -> int:
    text = _ABBREVIATION_RE.sub(lambda m: m.group(1), collapsed).strip()
    if not text:
        return 0
    return len([part for part in _SENTENCE_END_RE.split(text) if part.strip()])


def _heading_title_and_id(inline_content: str) -> tuple[str, str | None]:
    match = _ANCHOR_RE.search(inline_content)
    if match is None:
        return inline_content.strip(), None
    return inline_content[: match.start()].strip(), match.group(1)


def _slug(title: str) -> str:
    return re.sub(r"[^\w]+", "-", title.lower()).strip("-")


def is_agent_only(rel_path: str) -> bool:
    """True for ``DRAFT.md`` and ``HANDOFF.md`` at the pack root."""
    return rel_path.replace("\\", "/") in AGENT_ONLY_FILES


@dataclass(frozen=True)
class TocEntry:
    """One heading of a page: level 1-3, display title and anchor id."""

    level: int
    title: str
    anchor: str
    line: int


def generate_toc(text: str) -> list[TocEntry]:
    """Return the H1-H3 headings of `text`, using explicit ``{#id}`` anchors when given."""
    tokens = create_townhall_parser().parse(text)
    entries: list[TocEntry] = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        level = int(token.tag[1])
        if level > MAX_HEADING_LEVEL:
            continue
        title, explicit = _heading_title_and_id(tokens[index + 1].content)
        entries.append(
            TocEntry(level, title, explicit or _slug(title), (token.map or [0])[0] + 1)
        )
    return entries


def parse_mermaid_accessibility(source: str) -> tuple[str | None, str | None]:
    """Return the ``accTitle`` and ``accDescr`` values of a mermaid block, or None."""
    title = _ACC_TITLE_RE.search(source)
    descr = _ACC_DESCR_RE.search(source) or _ACC_DESCR_BLOCK_RE.search(source)
    return (
        title.group(1).strip() if title else None,
        " ".join(descr.group(1).split()) if descr else None,
    )


# ---------------------------------------------------------------------------- linter


def _check_frontmatter(doc: Document, rel_path: str) -> list[LintFinding]:
    if doc.frontmatter is None:
        return [
            LintFinding("FM001", rel_path, 1, f"Frontmatter is required: {doc.error}.")
        ]
    findings: list[LintFinding] = []
    data = doc.frontmatter
    for key in REQUIRED_FRONTMATTER_KEYS:
        if key not in data:
            findings.append(
                LintFinding(
                    "FM002", rel_path, 1, f"Frontmatter key '{key}' is missing."
                )
            )
    for key in ("title", "status"):
        if key in data and not (isinstance(data[key], str) and data[key].strip()):
            findings.append(
                LintFinding(
                    "FM002",
                    rel_path,
                    1,
                    f"Frontmatter '{key}' must be a non-empty string.",
                )
            )
    if "order" in data and (
        isinstance(data["order"], bool) or not isinstance(data["order"], int)
    ):
        findings.append(
            LintFinding("FM002", rel_path, 1, "Frontmatter 'order' must be an integer.")
        )
    if "updated" in data and not _valid_date(data["updated"]):
        findings.append(
            LintFinding(
                "FM002", rel_path, 1, "Frontmatter 'updated' must be a YYYY-MM-DD date."
            )
        )
    return findings


def _valid_date(value: object) -> bool:
    if isinstance(value, datetime):
        return False
    if isinstance(value, date):
        return True
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True
    return False


def _line(token: Token) -> int:
    return (token.map[0] + 1) if token.map else 1


def _check_tldr(tokens: list[Token], rel_path: str) -> list[LintFinding]:
    h1 = next(
        (i for i, t in enumerate(tokens) if t.type == "heading_open" and t.tag == "h1"),
        None,
    )
    if h1 is None:
        return [
            LintFinding(
                "TLDR001",
                rel_path,
                1,
                "The page needs an H1 followed by a **tl;dr:** paragraph.",
            )
        ]
    after = h1 + 3  # heading_open, inline, heading_close
    if after + 1 >= len(tokens) or tokens[after].type != "paragraph_open":
        line = _line(tokens[h1])
        return [
            LintFinding(
                "TLDR001",
                rel_path,
                line,
                "A **tl;dr:** paragraph must directly follow the H1.",
            )
        ]
    inline = tokens[after + 1]
    line = _line(tokens[after])
    if not inline.content.startswith(TLDR_MARKER):
        return [
            LintFinding(
                "TLDR001",
                rel_path,
                line,
                "The first paragraph after the H1 must start with **tl;dr:**.",
            )
        ]
    plain, collapsed = _inline_text(inline)
    prefix = "tl;dr:"
    plain = plain.removeprefix(prefix) if plain.startswith(prefix) else plain
    collapsed = (
        collapsed.removeprefix(prefix) if collapsed.startswith(prefix) else collapsed
    )
    findings: list[LintFinding] = []
    sentences = _count_sentences(collapsed)
    if not TLDR_MIN_SENTENCES <= sentences <= TLDR_MAX_SENTENCES:
        findings.append(
            LintFinding(
                "TLDR002",
                rel_path,
                line,
                f"The tl;dr has {sentences} sentences; it needs {TLDR_MIN_SENTENCES} to {TLDR_MAX_SENTENCES}.",
            )
        )
    words = len(plain.split())
    if words > TLDR_MAX_WORDS:
        findings.append(
            LintFinding(
                "TLDR003",
                rel_path,
                line,
                f"The tl;dr has {words} words; the limit is {TLDR_MAX_WORDS}.",
            )
        )
    return findings


def _check_size(tokens: list[Token], text: str, rel_path: str) -> list[LintFinding]:
    findings: list[LintFinding] = []
    h2s = [t for t in tokens if t.type == "heading_open" and t.tag == "h2"]
    if len(h2s) > MAX_H2 and rel_path != "index.md":
        findings.append(
            LintFinding(
                "SIZE001",
                rel_path,
                _line(h2s[MAX_H2]),
                f"The page has {len(h2s)} '##' sections; the limit is {MAX_H2}. Split it into more pages.",
            )
        )
    for token in tokens:
        if token.type == "heading_open" and int(token.tag[1]) > MAX_HEADING_LEVEL:
            findings.append(
                LintFinding(
                    "SIZE002",
                    rel_path,
                    _line(token),
                    f"Heading level {token.tag} is deeper than h3.",
                )
            )
    lines = len(text.splitlines())
    if lines > MAX_LINES:
        findings.append(
            LintFinding(
                "SIZE003",
                rel_path,
                MAX_LINES + 1,
                f"The page has {lines} lines; the limit is {MAX_LINES}.",
            )
        )
    return findings


def _check_paragraphs(tokens: list[Token], rel_path: str) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for index, token in enumerate(tokens):
        if token.type != "paragraph_open" or token.hidden:
            continue
        _, collapsed = _inline_text(tokens[index + 1])
        if collapsed.startswith("tl;dr:"):
            collapsed = collapsed.removeprefix("tl;dr:")
        count = _count_sentences(collapsed)
        if count > MAX_PARAGRAPH_SENTENCES:
            findings.append(
                LintFinding(
                    "PARA001",
                    rel_path,
                    _line(token),
                    f"The paragraph has {count} sentences; the limit is {MAX_PARAGRAPH_SENTENCES}.",
                )
            )
    return findings


def _check_decision_lists(tokens: list[Token], rel_path: str) -> list[LintFinding]:
    """Warn on bullet lists of three or more `name: value, rationale` items (heuristic)."""
    findings: list[LintFinding] = []
    depth = 0
    for index, token in enumerate(tokens):
        if token.type == "bullet_list_open":
            depth += 1
            if depth != 1:
                continue
            named = 0
            level = 0
            for inner in tokens[index + 1 :]:
                if (
                    inner.type == "bullet_list_open"
                    or inner.type == "ordered_list_open"
                ):
                    level += 1
                elif inner.type in {"bullet_list_close", "ordered_list_close"}:
                    if level == 0:
                        break
                    level -= 1
                elif (
                    inner.type == "inline"
                    and level == 0
                    and _NAMED_ITEM_RE.match(inner.content.strip())
                ):
                    named += 1
            if named >= DECISION_ITEMS_THRESHOLD:
                findings.append(
                    LintFinding(
                        "TABLE001",
                        rel_path,
                        _line(token),
                        f"{named} named items with values and reasons look like decisions; "
                        "use a table (| Name | Value | Why |).",
                        Severity.WARNING,
                    )
                )
        elif token.type == "bullet_list_close":
            depth -= 1
    return findings


def _requires_diagram(rel_path: str) -> bool:
    name = rel_path.rsplit("/", 1)[-1]
    return name == "plan-01-context.md" or bool(_ARCHITECTURE_PAGE_RE.match(name))


def _check_mermaid(tokens: list[Token], rel_path: str) -> list[LintFinding]:
    findings: list[LintFinding] = []
    blocks = [
        t for t in tokens if t.type == "fence" and t.info.split()[:1] == ["mermaid"]
    ]
    if _requires_diagram(rel_path) and not blocks:
        findings.append(
            LintFinding(
                "MERMAID001",
                rel_path,
                1,
                "This page must carry a ```mermaid block with accTitle and accDescr.",
            )
        )
    for block in blocks:
        title, descr = parse_mermaid_accessibility(block.content)
        missing = [
            name
            for name, value in (("accTitle:", title), ("accDescr:", descr))
            if not value
        ]
        if missing:
            findings.append(
                LintFinding(
                    "MERMAID002",
                    rel_path,
                    _line(block),
                    f"The mermaid block lacks {' and '.join(missing)}.",
                )
            )
    return findings


def _check_anchors(tokens: list[Token], rel_path: str) -> list[LintFinding]:
    findings: list[LintFinding] = []
    folder = rel_path.split("/", 1)[0] if "/" in rel_path else ""
    expected_letter = {"tasks": "T", "questions": "Q"}.get(folder)
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        level = int(token.tag[1])
        title, explicit = _heading_title_and_id(tokens[index + 1].content)
        named = _NAMED_HEADING_RE.match(title)
        line = _line(token)
        if named is None:
            if level == 1 and expected_letter is not None:
                findings.append(
                    LintFinding(
                        "ANCHOR001",
                        rel_path,
                        line,
                        f"The H1 of a {folder[:-1]} page must read '# {expected_letter}<n> — <title> {{#{expected_letter.lower()}<n>}}'.",
                    )
                )
            elif level == 3 and rel_path == "GLOSSARY.md":
                findings.append(
                    LintFinding(
                        "ANCHOR001",
                        rel_path,
                        line,
                        "Glossary entries must read '### R<n> — <term> {#r<n>}'.",
                    )
                )
            continue
        want = f"{named.group(1).lower()}{int(named.group(2))}"
        if explicit != want:
            problem = (
                "lacks" if explicit is None else f"has '{{#{explicit}}}' instead of"
            )
            findings.append(
                LintFinding(
                    "ANCHOR001",
                    rel_path,
                    line,
                    f"Heading '{title}' {problem} the anchor {{#{want}}}.",
                )
            )
    return findings


def lint_markdown(
    text: str, rel_path: str, *, parser: MarkdownIt | None = None
) -> list[LintFinding]:
    """Lint one page. `rel_path` is its POSIX path inside the ticket pack.

    Agent-only files (``DRAFT.md``, ``HANDOFF.md``) and non-Markdown files return no findings.
    """
    rel_path = rel_path.replace("\\", "/")
    if is_agent_only(rel_path) or not rel_path.endswith(".md"):
        return []
    doc = parse_document(text)
    tokens = (parser or create_townhall_parser()).parse(text)
    findings: list[LintFinding] = []
    findings += _check_frontmatter(doc, rel_path)
    findings += _check_tldr(tokens, rel_path)
    findings += _check_size(tokens, text, rel_path)
    findings += _check_paragraphs(tokens, rel_path)
    findings += _check_decision_lists(tokens, rel_path)
    findings += _check_mermaid(tokens, rel_path)
    findings += _check_anchors(tokens, rel_path)
    return sorted(findings, key=lambda f: (f.line, f.rule))
