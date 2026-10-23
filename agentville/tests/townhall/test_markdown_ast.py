"""Tests for the Townhall page-budget linter, one per specification 5.2 rule."""

from __future__ import annotations

import pytest

from agentville.townhall.markdown_ast import (
    LintFinding,
    Severity,
    create_townhall_parser,
    generate_toc,
    has_errors,
    lint_markdown,
    parse_document,
    parse_mermaid_accessibility,
    render_document,
)

FRONTMATTER = (
    '---\ntitle: "Page"\nstatus: "draft"\nupdated: 2026-10-22\norder: 20\n---\n'
)
TLDR = "**tl;dr:** This page states one topic. It stays short and plain. Readers get the point fast."
MERMAID = "```mermaid\nflowchart LR\n  accTitle: Flow title\n  accDescr: Flow description.\n  A --> B\n```\n"


def page(body: str, frontmatter: str = FRONTMATTER, title: str = "Page") -> str:
    return f"{frontmatter}\n# {title}\n\n{body}"


def good_body() -> str:
    return f"{TLDR}\n\n## Why\n\nBecause it matters.\n"


def rules(findings: list[LintFinding]) -> set[str]:
    return {f.rule for f in findings}


def test_clean_page_has_no_findings() -> None:
    assert lint_markdown(page(good_body()), "plan/plan-02-x.md") == []


def test_parser_pipeline_builds_with_plugins() -> None:
    tokens = create_townhall_parser().parse(page(good_body()))
    assert tokens[0].type == "front_matter"
    assert any(t.type == "heading_open" and t.tag == "h1" for t in tokens)


# --- Mandatory frontmatter ------------------------------------------------------------


def test_fm001_missing_frontmatter() -> None:
    findings = lint_markdown(f"# Page\n\n{good_body()}", "plan/plan-02-x.md")
    assert "FM001" in rules(findings)


def test_fm001_invalid_yaml() -> None:
    bad = "---\ntitle: [unclosed\n---\n"
    assert "FM001" in rules(lint_markdown(page(good_body(), bad), "plan/plan-02-x.md"))


@pytest.mark.parametrize(
    "frontmatter",
    [
        '---\nstatus: "draft"\nupdated: 2026-10-22\norder: 1\n---\n',  # no title
        '---\ntitle: "T"\nupdated: 2026-10-22\norder: 1\n---\n',  # no status
        '---\ntitle: "T"\nstatus: "d"\norder: 1\n---\n',  # no updated
        '---\ntitle: "T"\nstatus: "d"\nupdated: 2026-10-22\n---\n',  # no order
        '---\ntitle: "T"\nstatus: "d"\nupdated: 2026-10-22\norder: "1"\n---\n',  # order str
        '---\ntitle: "T"\nstatus: "d"\nupdated: 2026-10-22\norder: true\n---\n',  # order bool
        '---\ntitle: "T"\nstatus: "d"\nupdated: "22/10/2026"\norder: 1\n---\n',  # bad date
        '---\ntitle: "T"\nstatus: "d"\nupdated: 2026-10-22 10:00:00\norder: 1\n---\n',  # datetime
        '---\ntitle: 5\nstatus: "d"\nupdated: 2026-10-22\norder: 1\n---\n',  # title int
    ],
)
def test_fm002_required_keys_and_types(frontmatter: str) -> None:
    findings = lint_markdown(page(good_body(), frontmatter), "plan/plan-02-x.md")
    assert "FM002" in rules(findings)


def test_fm002_accepts_quoted_iso_date() -> None:
    fm = '---\ntitle: "T"\nstatus: "d"\nupdated: "2026-10-22"\norder: 1\n---\n'
    assert lint_markdown(page(good_body(), fm), "plan/plan-02-x.md") == []


# --- Mandatory tl;dr ------------------------------------------------------------------


def test_tldr001_missing_marker() -> None:
    body = "A plain paragraph. With two sentences. And three.\n\n## Why\n\nx\n"
    assert "TLDR001" in rules(lint_markdown(page(body), "plan/plan-02-x.md"))


def test_tldr001_not_immediately_after_h1() -> None:
    body = f"## Why\n\nx\n\n{TLDR}\n"
    assert "TLDR001" in rules(lint_markdown(page(body), "plan/plan-02-x.md"))


def test_tldr001_missing_h1() -> None:
    findings = lint_markdown(f"{FRONTMATTER}\n{TLDR}\n", "plan/plan-02-x.md")
    assert "TLDR001" in rules(findings)


def test_tldr002_too_few_sentences() -> None:
    body = "**tl;dr:** Only one sentence here.\n"
    assert "TLDR002" in rules(lint_markdown(page(body), "plan/plan-02-x.md"))


def test_tldr002_too_many_sentences() -> None:
    body = (
        "**tl;dr:** "
        + " ".join(f"Sentence number {n} ends here." for n in range(7))
        + "\n"
    )
    assert "TLDR002" in rules(lint_markdown(page(body), "plan/plan-02-x.md"))


def test_tldr002_ignores_dots_inside_code_and_abbreviations() -> None:
    body = "**tl;dr:** Use `redis.asyncio.ConnectionPool` for pooling, e.g. in workers. It is fast. It is safe.\n"
    assert lint_markdown(page(body), "plan/plan-02-x.md") == []


def test_tldr003_over_one_hundred_words() -> None:
    long_sentence = " ".join(["word"] * 40) + "."
    body = f"**tl;dr:** {long_sentence} {long_sentence} {long_sentence}\n"
    assert "TLDR003" in rules(lint_markdown(page(body), "plan/plan-02-x.md"))


# --- Single topic and length budget ---------------------------------------------------


def test_size001_more_than_four_h2() -> None:
    sections = "".join(f"## Section {n}\n\ntext\n\n" for n in range(5))
    findings = lint_markdown(page(f"{TLDR}\n\n{sections}"), "plan/plan-02-x.md")
    assert "SIZE001" in rules(findings)


def test_size001_exactly_four_h2_is_fine() -> None:
    sections = "".join(f"## Section {n}\n\ntext\n\n" for n in range(4))
    assert lint_markdown(page(f"{TLDR}\n\n{sections}"), "plan/plan-02-x.md") == []


def test_size001_index_is_exempt() -> None:
    sections = "".join(f"## Section {n}\n\ntext\n\n" for n in range(7))
    assert "SIZE001" not in rules(
        lint_markdown(page(f"{TLDR}\n\n{sections}"), "index.md")
    )


def test_size002_heading_deeper_than_h3() -> None:
    body = f"{TLDR}\n\n## A\n\n### B\n\n#### C\n\ntext\n"
    assert "SIZE002" in rules(lint_markdown(page(body), "plan/plan-02-x.md"))


def test_size003_more_than_250_lines() -> None:
    body = f"{TLDR}\n\n" + "\n".join(f"- item {n}" for n in range(260)) + "\n"
    assert "SIZE003" in rules(lint_markdown(page(body), "plan/plan-02-x.md"))


# --- Paragraph budget -----------------------------------------------------------------


def test_para001_seven_sentence_paragraph() -> None:
    paragraph = " ".join(f"Sentence {n} is here." for n in range(7))
    findings = lint_markdown(
        page(f"{TLDR}\n\n## A\n\n{paragraph}\n"), "plan/plan-02-x.md"
    )
    assert "PARA001" in rules(findings)


def test_para001_six_sentences_pass() -> None:
    paragraph = " ".join(f"Sentence {n} is here." for n in range(6))
    assert (
        lint_markdown(page(f"{TLDR}\n\n## A\n\n{paragraph}\n"), "plan/plan-02-x.md")
        == []
    )


# --- Structured decisions table (heuristic, warning) ----------------------------------


def test_table001_warns_on_three_named_bullets() -> None:
    bullets = (
        "- `pool_timeout`: 50ms — prevents stalls\n"
        "- `bucket_capacity`: 100 — allows bursts\n"
        "- `refill_rate`: 10/s — matches throughput\n"
    )
    findings = lint_markdown(
        page(f"{TLDR}\n\n## Fixed decisions\n\n{bullets}"), "plan/plan-02-x.md"
    )
    table = [f for f in findings if f.rule == "TABLE001"]
    assert len(table) == 1
    assert table[0].severity is Severity.WARNING
    assert not has_errors(findings)


def test_table001_ignores_plain_and_link_bullets_and_real_tables() -> None:
    body = (
        f"{TLDR}\n\n## Links\n\n- [a.md](./a.md) — about a\n- [b.md](./b.md) — about b\n- [c.md](./c.md) — about c\n\n"
        "## Todo\n\n- [ ] do one\n- [ ] do two\n- [ ] do three\n\n"
        "## Decisions\n\n| Name | Value | Why |\n|---|---|---|\n| `a` | 1 | x |\n"
    )
    assert "TABLE001" not in rules(lint_markdown(page(body), "plan/plan-02-x.md"))


def test_table001_needs_three_items() -> None:
    bullets = "- `a`: 1 — because\n- `b`: 2 — because\n"
    assert "TABLE001" not in rules(
        lint_markdown(page(f"{TLDR}\n\n## D\n\n{bullets}"), "plan/plan-02-x.md")
    )


# --- Accessible Mermaid ---------------------------------------------------------------


def test_mermaid001_context_page_requires_diagram() -> None:
    findings = lint_markdown(page(good_body()), "plan/plan-01-context.md")
    assert "MERMAID001" in rules(findings)


def test_mermaid001_architecture_page_requires_diagram() -> None:
    findings = lint_markdown(page(good_body()), "plan/plan-02-architecture.md")
    assert "MERMAID001" in rules(findings)


def test_mermaid_accessible_diagram_passes() -> None:
    body = f"{TLDR}\n\n## Diagram\n\n{MERMAID}"
    assert lint_markdown(page(body), "plan/plan-01-context.md") == []


@pytest.mark.parametrize("missing", ["accTitle", "accDescr"])
def test_mermaid002_missing_acc_directive(missing: str) -> None:
    block = (
        "\n".join(line for line in MERMAID.splitlines() if missing not in line) + "\n"
    )
    findings = lint_markdown(
        page(f"{TLDR}\n\n## Diagram\n\n{block}"), "plan/plan-01-context.md"
    )
    assert "MERMAID002" in rules(findings)


def test_mermaid002_applies_to_any_page() -> None:
    body = f"{TLDR}\n\n## Diagram\n\n```mermaid\nflowchart LR\n  A --> B\n```\n"
    assert "MERMAID002" in rules(
        lint_markdown(page(body), "plan/plan-03-verification.md")
    )


def test_parse_mermaid_accessibility_block_form() -> None:
    source = "flowchart LR\n  accTitle: T\n  accDescr {\n    Long\n    text\n  }\n"
    assert parse_mermaid_accessibility(source) == ("T", "Long text")


# --- Explicit heading anchors ---------------------------------------------------------


def task_page(heading: str) -> str:
    return f"{FRONTMATTER}\n{heading}\n\n{TLDR}\n"


def test_anchor001_task_heading_needs_id() -> None:
    findings = lint_markdown(task_page("# T1 — Do it"), "tasks/task-01-do.md")
    assert "ANCHOR001" in rules(findings)


def test_anchor001_task_heading_with_id_passes() -> None:
    assert lint_markdown(task_page("# T1 — Do it {#t1}"), "tasks/task-01-do.md") == []


def test_anchor001_wrong_id_is_flagged() -> None:
    assert "ANCHOR001" in rules(
        lint_markdown(task_page("# T2 — Do it {#t1}"), "tasks/task-02-do.md")
    )


def test_anchor001_task_page_h1_must_be_task_heading() -> None:
    assert "ANCHOR001" in rules(
        lint_markdown(task_page("# Plain title"), "tasks/task-01-do.md")
    )


def test_anchor001_question_heading() -> None:
    assert "ANCHOR001" in rules(
        lint_markdown(task_page("# Q1 — Why?"), "questions/q-01-why.md")
    )
    assert lint_markdown(task_page("# Q1 — Why? {#q1}"), "questions/q-01-why.md") == []


def test_anchor001_glossary_entries() -> None:
    body = f"{TLDR}\n\n## Terms\n\n### R1 — Bucket\n\nA token store.\n"
    assert "ANCHOR001" in rules(
        lint_markdown(page(body, title="Glossary"), "GLOSSARY.md")
    )
    ok = body.replace("Bucket", "Bucket {#r1}")
    assert lint_markdown(page(ok, title="Glossary"), "GLOSSARY.md") == []


# --- Agent-only exemptions ------------------------------------------------------------


@pytest.mark.parametrize("name", ["DRAFT.md", "HANDOFF.md"])
def test_agent_only_files_bypass_linting(name: str) -> None:
    text = "# Handoff\n\n#### deep\n\nNo frontmatter. " + "Sentence. " * 20 + "\n"
    assert lint_markdown(text, name) == []


def test_agent_only_exemption_is_root_only() -> None:
    assert lint_markdown("# X\n", "plan/HANDOFF.md") != []


def test_non_markdown_files_are_ignored() -> None:
    assert lint_markdown("+++ diff", "review/diff.patch") == []


# --- Findings and helpers -------------------------------------------------------------


def test_findings_are_structured_with_lines() -> None:
    findings = lint_markdown(page("**tl;dr:** One.\n"), "plan/plan-02-x.md")
    finding = next(f for f in findings if f.rule == "TLDR002")
    assert finding.file == "plan/plan-02-x.md"
    assert finding.line == 10  # absolute line, frontmatter included
    assert finding.to_dict()["severity"] == "error"


def test_generate_toc_uses_explicit_anchors() -> None:
    toc = generate_toc(
        task_page("# T1 — Do it {#t1}") + "\n## Done criteria\n\n### Sub part\n"
    )
    assert [(e.level, e.title, e.anchor) for e in toc] == [
        (1, "T1 — Do it", "t1"),
        (2, "Done criteria", "done-criteria"),
        (3, "Sub part", "sub-part"),
    ]


def test_document_round_trip_is_deterministic() -> None:
    text = render_document(
        {"id": "1011", "labels": ["a", "b"], "n": None, "order": 3}, "# H\n"
    )
    assert text.endswith("# H\n")
    assert "labels:\n  - a\n  - b\n" in text
    doc = parse_document(text)
    assert doc.frontmatter == {
        "id": "1011",
        "labels": ["a", "b"],
        "n": None,
        "order": 3,
    }
    assert render_document(doc.frontmatter or {}, doc.body) == text
