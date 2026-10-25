"""Tests for the full-screen ticket viewer (specification sections 4 and 10.2)."""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console
from rich.syntax import Syntax
from textual.widgets import Checkbox, Input, RadioButton, Static

from agentville.townhall.board.storage import (
    QuestionInput,
    QuestionOption,
    Stage,
    TownhallStorage,
)
from agentville.townhall.board.viewer import (
    AnswerModal,
    ReviewModal,
    TicketViewerApp,
    diff_renderable,
    match_page,
    mermaid_renderable,
    parse_flowchart,
    render_ascii_flowchart,
    run_viewer,
    strip_heading_ids,
)
from agentville.townhall.core.errors import NotFoundError

SIZE = (140, 40)
FM = '---\ntitle: "{t}"\nstatus: "draft"\nupdated: 2026-10-22\norder: {o}\n---\n'
TLDR = "**tl;dr:** This page states one topic. It stays short and plain. Readers get the point fast."
MERMAID = """flowchart LR
  accTitle: Token bucket flow
  accDescr: A request checks the bucket and then reaches the handler.
  Req["HTTP Request"] --> Check["Bucket"] --> Handler["Handler"]
"""
DIFF = """diff --git a/src/pool.py b/src/pool.py
--- a/src/pool.py
+++ b/src/pool.py
@@ -1,2 +1,2 @@
-old = 1
+new = 2
 same = 3
"""


def page(title: str, order: int, body: str = "") -> str:
    return f"{FM.format(t=title, o=order)}\n# {title}\n\n{TLDR}\n\n{body}"


LONG_BODY = "\n\n".join(
    f"## Section {n} {{#s{n}}}\n\nParagraph {n} has some plain words in it."
    for n in range(1, 41)
)
CONTEXT_BODY = f"""## Why

Burst traffic.

## Fixed decisions

| Name | Value |
|---|---|
| `pool_timeout` | `50ms` |

## Diagram

```mermaid
{MERMAID}```
"""


def question(slug: str, *, multi: bool = False, other: bool = True) -> QuestionInput:
    return QuestionInput(
        header=slug.title(),
        title=f"What about {slug}?",
        tldr="A choice is needed. One option keeps uptime. The other keeps protection.",
        context="The pool times out after 50ms.",
        options=[
            QuestionOption("fail_open", "Fail open", "Let requests through."),
            QuestionOption("fail_closed", "Fail closed", "Return 503."),
        ],
        slug=slug,
        multi_select=multi,
        allow_other=other,
    )


@pytest.fixture
def store(tmp_path: Path) -> TownhallStorage:
    storage = TownhallStorage(tmp_path, enforce_page_budgets=False)
    storage.init_project()
    storage.create_board("B01", "Main board")
    return storage


def make_ticket(store: TownhallStorage, title: str = "Rate limiting") -> str:
    """A ticket in Execute with draft, plan and task pages; one task done."""
    ticket_id = store.create_ticket("B01", title).id
    for stage in (Stage.DISCUSS, Stage.PLANNING):
        store.move_ticket("B01", ticket_id, stage)
    store.write_page("B01", ticket_id, "draft/draft-01-problem.md", page("Problem", 10))
    store.write_page(
        "B01", ticket_id, "plan/plan-01-context.md", page("Context", 20, CONTEXT_BODY)
    )
    store.write_page(
        "B01", ticket_id, "plan/plan-02-long.md", page("Long plan", 21, LONG_BODY)
    )
    for stage in (Stage.TODO, Stage.EXECUTE):
        store.move_ticket("B01", ticket_id, stage)
    for number in (1, 2, 3):
        store.create_task(
            "B01",
            ticket_id,
            f"task-0{number}-step.md",
            f"Step {number}",
            29 + number,
            [],
            f"{TLDR}\n\n## Todo\n\n- [ ] one\n",
        )
    store.update_task_status("B01", ticket_id, "task-01-step.md", "done")
    return ticket_id


@pytest.fixture
def ask_ticket(store: TownhallStorage) -> str:
    """Need Inputs with a single-choice and a multi-choice pending question."""
    ticket_id = make_ticket(store)
    store.request_inputs(
        "B01",
        ticket_id,
        "Execute",
        "Resume at task 2.",
        [question("single"), question("multi", multi=True)],
    )
    return ticket_id


def make_review_ticket(store: TownhallStorage) -> str:
    """A ticket in Review with HANDOFF.md, DRAFT.md and review/diff.patch."""
    ticket_id = make_ticket(store, "Reviewed work")
    store.request_inputs("B01", ticket_id, "Execute", "Paused.", [question("early")])
    store.answer_question("B01", ticket_id, "q-01-early", ["fail_open"])
    store.move_ticket("B01", ticket_id, Stage.EXECUTE)
    store.write_page("B01", ticket_id, "DRAFT.md", "# Scratch\n\nagent notes\n")
    store.submit_review(
        "B01",
        ticket_id,
        f"# Summary\n\n{TLDR}",
        f"# Evidence\n\n{TLDR}",
        DIFF,
        require_tasks_done=False,
    )
    return ticket_id


def app_for(
    store: TownhallStorage,
    ticket_id: str,
    page_name: str | None = None,
    notifier: object = None,
) -> TicketViewerApp:
    return TicketViewerApp(store, "B01", ticket_id, page_name, notifier=notifier)  # type: ignore[arg-type]


async def goto(app: TicketViewerApp, pilot: object, rel_path: str) -> None:
    await app.show_page(app.sidebar_pages().index(rel_path))
    await pilot.pause()  # type: ignore[attr-defined]


def scrolled(app: TicketViewerApp) -> float:
    return app.doc.scroll_y


# --------------------------------------------------------------------- layout


async def test_layout_shows_header_groups_and_page_position(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        title = str(app.query_one("#topbar-title", Static).render())
        assert "B01 / Ticket" in title and "Rate limiting" in title
        assert "Stage: Need Inputs" in str(
            app.query_one("#topbar-stage", Static).render()
        )
        assert app.sidebar_groups() == [
            "Draft",
            "Plan",
            "Questions (2 Pending!)",
            "Tasks (1/3)",
        ]
        assert app.current_page.rel_path == "index.md"
        total = len(app.pages)
        assert f"(Page 1 of {total})" in str(app.query_one("#pagebar", Static).render())
        assert "Next:" in str(app.query_one("#next-hint", Static).render())


async def test_frontmatter_is_stripped_and_mermaid_fence_uses_the_fallback(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket, "plan/plan-01-context.md")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert app.current_page.rel_path == "plan/plan-01-context.md"
        md = app.query_one("#md")
        assert "title:" not in md.source and "---" not in md.source.split("\n")[0]  # type: ignore[attr-defined]
        fences = app.query("TownhallFence")
        assert len(fences) == 1
        assert len(app.query("#mermaid-content")) == 1
        assert [e.title for e in app.toc][:1] == ["Context"]


# ------------------------------------------------------------ scroll keys: j k d u g G


@pytest.mark.parametrize(("down", "up"), [("j", "k"), ("down", "up")])
async def test_j_k_and_arrow_keys_scroll_one_line(
    store: TownhallStorage, ask_ticket: str, down: str, up: str
) -> None:
    app = app_for(store, ask_ticket, "plan/plan-02-long.md")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert scrolled(app) == 0
        await pilot.press(down, down, down)
        await pilot.pause()
        assert scrolled(app) == 3
        await pilot.press(up)
        await pilot.pause()
        assert scrolled(app) == 2


async def test_d_and_u_scroll_half_a_page(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket, "plan/plan-02-long.md")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        half = app.doc.size.height // 2
        await pilot.press("d")
        await pilot.pause()
        assert scrolled(app) == half
        await pilot.press("d", "u")
        await pilot.pause()
        assert scrolled(app) == half


async def test_g_and_capital_g_jump_to_top_and_bottom(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket, "plan/plan-02-long.md")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("G")
        await pilot.pause()
        assert scrolled(app) == app.doc.max_scroll_y > 0
        await pilot.press("g")
        await pilot.pause()
        assert scrolled(app) == 0


# ------------------------------------------------------------ page keys: h l Left Right


@pytest.mark.parametrize(("previous", "following"), [("h", "l"), ("left", "right")])
async def test_h_l_and_arrows_move_between_pages(
    store: TownhallStorage, ask_ticket: str, previous: str, following: str
) -> None:
    app = app_for(store, ask_ticket)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press(previous)
        assert app.page_index == 0  # no wrap at the start
        await pilot.press(following)
        await pilot.pause()
        assert app.page_index == 1
        assert app.current_page.rel_path == app.pages[1].rel_path
        assert "(Page 2 of" in str(app.query_one("#pagebar", Static).render())
        await pilot.press(previous)
        await pilot.pause()
        assert app.page_index == 0


async def test_next_page_resets_scroll_and_clamps_at_the_end(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket, "plan/plan-02-long.md")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        assert scrolled(app) > 0
        await pilot.press("l")
        await pilot.pause()
        assert scrolled(app) == 0
        for _ in range(len(app.pages)):
            await pilot.press("l")
        await pilot.pause()
        assert app.page_index == len(app.pages) - 1


# ----------------------------------------------------------------- focus keys: t s


async def test_t_focuses_toc_and_returns_and_enter_jumps_to_heading(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket, "plan/plan-02-long.md")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert app.focused is app.doc
        await pilot.press("t")
        assert app.focused is app.toc_tree
        start = app.toc_tree.cursor_line
        await pilot.press("j", "j", "j", "j", "j")
        assert app.toc_tree.cursor_line == start + 5
        await pilot.press("k")
        assert app.toc_tree.cursor_line == start + 4
        assert scrolled(app) == 0
        await pilot.press("enter")
        await pilot.pause()
        assert scrolled(app) > 0
        await pilot.press("t")
        assert app.focused is app.doc


async def test_s_focuses_sidebar_and_enter_opens_the_page(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("s")
        assert app.focused is app.sidebar
        target = app._sidebar_nodes["plan/plan-02-long.md"]
        app.sidebar.move_cursor(target)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.current_page.rel_path == "plan/plan-02-long.md"
        assert app.focused is app.sidebar
        await pilot.press("s")
        assert app.focused is app.doc


async def test_sidebar_cursor_follows_page_navigation(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("l", "l")
        await pilot.pause()
        node = app.sidebar.cursor_node
        assert node is not None and node.data == app.current_page.rel_path


# ----------------------------------------------------------------------- H and T


async def test_capital_h_toggles_agent_files_in_the_sidebar(
    store: TownhallStorage,
) -> None:
    ticket_id = make_review_ticket(store)
    app = app_for(store, ticket_id)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        hidden = app.sidebar_pages()
        assert not {"HANDOFF.md", "DRAFT.md", "review/diff.patch"} & set(hidden)
        await pilot.press("H")
        await pilot.pause()
        shown = app.sidebar_pages()
        assert {"HANDOFF.md", "DRAFT.md", "review/diff.patch"} <= set(shown)
        assert "Agent files" in app.sidebar_groups()
        await pilot.press("H")
        await pilot.pause()
        assert app.sidebar_pages() == hidden


async def test_diff_patch_page_renders_with_rich_syntax(store: TownhallStorage) -> None:
    ticket_id = make_review_ticket(store)
    app = app_for(store, ticket_id, "review/diff.patch")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert app.current_page.kind == "diff"
        assert app.query_one("#diff", Static).display is True
        assert app.query_one("#md").display is False
        assert app.toc == []


async def test_capital_t_toggles_the_theme(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert app.theme == "textual-dark"
        await pilot.press("T")
        assert app.theme == "textual-light"
        await pilot.press("T")
        assert app.theme == "textual-dark"


# ------------------------------------------------------------------------- quit


@pytest.mark.parametrize("key", ["q", "Q"])
async def test_q_and_capital_q_quit(
    store: TownhallStorage, ask_ticket: str, key: str
) -> None:
    app = app_for(store, ask_ticket)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press(key)
        await pilot.pause()
        assert app._exit is True


# ------------------------------------------------------------------ a: answering


def saved(store: TownhallStorage, ticket_id: str, name: str) -> object:
    return next(
        q
        for q in store.list_questions("B01", ticket_id)
        if q.file_name.startswith(name)
    )


async def test_a_saves_a_single_choice_answer(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await goto(app, pilot, "questions/q-01-single.md")
        await pilot.press("a")
        await pilot.pause()
        assert isinstance(app.screen, AnswerModal)
        assert len(app.screen.query(RadioButton)) == 2
        assert len(app.screen.query(Input)) == 1  # allow_other
        await pilot.click("#opt-1")
        await pilot.click("#save")
        await pilot.pause()
        assert not isinstance(app.screen, AnswerModal)
    answer = saved(store, ask_ticket, "q-01")
    assert answer.status == "answered" and answer.selected == ("fail_closed",)  # type: ignore[attr-defined]
    assert store.get_ticket("B01", ask_ticket).open_questions == 1


async def test_a_saves_a_multi_choice_answer_with_other_text(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await goto(app, pilot, "questions/q-02-multi.md")
        await pilot.press("a")
        await pilot.pause()
        assert isinstance(app.screen, AnswerModal)
        assert len(app.screen.query(Checkbox)) == 2
        await pilot.click("#opt-0")
        await pilot.click("#opt-1")
        app.screen.query_one("#other", Input).value = "also log it"
        await pilot.click("#save")
        await pilot.pause()
        assert "answered" in app.current_page.text
        assert app.sidebar_groups()[2] == "Questions (1 Pending!)"
    answer = saved(store, ask_ticket, "q-02")
    assert answer.selected == ("fail_open", "fail_closed")  # type: ignore[attr-defined]
    assert answer.other_text == "also log it"  # type: ignore[attr-defined]


async def test_a_keeps_the_modal_open_without_a_choice_and_cancel_saves_nothing(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await goto(app, pilot, "questions/q-01-single.md")
        await pilot.press("a")
        await pilot.pause()
        await pilot.click("#save")
        await pilot.pause()
        assert isinstance(app.screen, AnswerModal)
        await pilot.click("#cancel")
        await pilot.pause()
        assert not isinstance(app.screen, AnswerModal)
    assert saved(store, ask_ticket, "q-01").status == "pending"  # type: ignore[attr-defined]


async def test_a_on_a_plain_page_only_notifies(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        assert not isinstance(app.screen, (AnswerModal, ReviewModal))
        assert len(app._notifications) == 1


# ------------------------------------------------------------------ a: review


async def test_a_on_review_summary_approves_the_ticket(store: TownhallStorage) -> None:
    ticket_id = make_review_ticket(store)
    app = app_for(store, ticket_id, "review/review-01-summary.md")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        assert isinstance(app.screen, ReviewModal)
        await pilot.click("#approve")
        await pilot.pause()
        assert "Stage: Complete" in str(app.query_one("#topbar-stage", Static).render())
    assert store.get_ticket("B01", ticket_id).stage is Stage.COMPLETE


async def test_a_on_review_summary_rejects_with_a_reason(
    store: TownhallStorage,
) -> None:
    ticket_id = make_review_ticket(store)
    app = app_for(store, ticket_id, "review/review-01-summary.md")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        await pilot.click("#reject")
        await pilot.pause()
        assert isinstance(app.screen, ReviewModal)  # a reason is required
        assert store.get_ticket("B01", ticket_id).stage is Stage.REVIEW
        await pilot.pause(0.4)  # let the button's press effect finish
        app.screen.query_one("#reason", Input).value = "tests missing"
        await pilot.click("#reject")
        await pilot.pause()
        assert not isinstance(app.screen, ReviewModal)
    assert store.get_ticket("B01", ticket_id).stage is Stage.DISCUSS


async def test_approve_notifies_the_workflow_once(store: TownhallStorage) -> None:
    ticket_id = make_review_ticket(store)
    calls: list[tuple[object, ...]] = []
    app = app_for(
        store,
        ticket_id,
        "review/review-01-summary.md",
        lambda *a: calls.append(a),
    )
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        await pilot.click("#approve")
        await pilot.pause()
    assert len(calls) == 1
    assert calls[0][:5] == (store.root, "B01", ticket_id, "Review", "Complete")


async def test_reject_notifies_the_workflow_once(store: TownhallStorage) -> None:
    ticket_id = make_review_ticket(store)
    calls: list[tuple[object, ...]] = []
    app = app_for(
        store,
        ticket_id,
        "review/review-01-summary.md",
        lambda *a: calls.append(a),
    )
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        app.screen.query_one("#reason", Input).value = "tests missing"
        await pilot.click("#reject")
        await pilot.pause()
    assert len(calls) == 1
    assert calls[0][:5] == (store.root, "B01", ticket_id, "Review", "Discuss")


async def test_a_raising_notifier_does_not_break_the_review(
    store: TownhallStorage,
) -> None:
    ticket_id = make_review_ticket(store)

    def boom(*args: object) -> None:
        raise RuntimeError("temporal down")

    app = app_for(store, ticket_id, "review/review-01-summary.md", boom)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        await pilot.click("#approve")
        await pilot.pause()
        assert "Stage: Complete" in str(app.query_one("#topbar-stage", Static).render())
    assert store.get_ticket("B01", ticket_id).stage is Stage.COMPLETE


# --------------------------------------------------------------- opening a page


async def test_links_in_index_open_the_target_page(
    store: TownhallStorage, ask_ticket: str
) -> None:
    app = app_for(store, ask_ticket)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await app.on_markdown_link_clicked(
            type(
                "Event",
                (),
                {"href": "./plan/plan-02-long.md", "stop": lambda self: None},
            )()  # type: ignore[arg-type]
        )
        assert app.current_page.rel_path == "plan/plan-02-long.md"


def test_run_viewer_rejects_unknown_pages_and_tickets(
    store: TownhallStorage, ask_ticket: str
) -> None:
    with pytest.raises(NotFoundError):
        run_viewer(store, "B01", ask_ticket, "plan/missing")
    with pytest.raises(NotFoundError):
        run_viewer(store, "B01", "9999")


def test_match_page_accepts_paths_stems_and_names() -> None:
    pages = ["index.md", "plan/plan-01-context.md", "review/diff.patch"]
    assert match_page(pages, "plan/plan-01-context.md") == 1
    assert match_page(pages, "plan-01-context") == 1
    assert match_page(pages, "diff.patch") == 2
    assert match_page(pages, "nope") is None


# ----------------------------------------------------------- mermaid fallback units


def test_ascii_flowchart_draws_a_chain_of_boxes() -> None:
    art = render_ascii_flowchart(MERMAID)
    assert art is not None
    top, mid, bottom = art.split("\n")
    assert "┌" in top and "└" in bottom
    assert mid.startswith("│ HTTP Request │──>│ Bucket │──>│ Handler │")
    assert len(top.rstrip()) == len(bottom.rstrip())


def test_ascii_flowchart_draws_branches_one_edge_per_row_with_labels() -> None:
    source = """flowchart LR
  Req["HTTP Request"] --> Check{"Bucket > 0?"}
  Check -- yes --> Handler["200 OK"]
  Check -->|no| Reject["429"]
"""
    graph = parse_flowchart(source)
    assert graph is not None and len(graph.edges) == 3
    art = render_ascii_flowchart(source)
    assert art is not None
    assert "──yes──>" in art and "──no──>" in art
    assert art.count("┌") == 6


def test_ascii_flowchart_ignores_unsupported_graphs() -> None:
    assert render_ascii_flowchart("flowchart TD\n  A --> B") is None
    assert render_ascii_flowchart("sequenceDiagram\n  A->>B: hi") is None
    assert render_ascii_flowchart("flowchart LR\n  A") is None


def test_mermaid_renderable_has_panel_and_diagram() -> None:
    console = Console(width=100, record=True, force_terminal=False)
    console.print(mermaid_renderable(MERMAID))
    out = console.export_text()
    assert "Token bucket flow" in out
    assert "A request checks the bucket" in out
    assert "──>" in out
    console = Console(width=100, record=True, force_terminal=False)
    console.print(mermaid_renderable("sequenceDiagram\n  A->>B: hi"))
    assert "No accDescr given" in console.export_text()


def test_strip_heading_ids_leaves_code_fences_alone() -> None:
    text = "## Why {#why}\n\n```\n## Not {#a-heading}\n```\n"
    assert strip_heading_ids(text) == "## Why\n\n```\n## Not {#a-heading}\n```\n"


# ------------------------------------------------------------------ diff units


def test_diff_renderable_is_a_monokai_diff_syntax_with_distinct_line_colours() -> None:
    syntax = diff_renderable(DIFF)
    assert isinstance(syntax, Syntax)
    assert syntax.code == DIFF
    assert syntax.lexer is not None and syntax.lexer.name.lower() == "diff"
    console = Console(
        width=80, record=True, force_terminal=True, color_system="truecolor"
    )
    console.print(syntax)
    lines = console.export_text(styles=True).split("\n")
    added = next(line for line in lines if "new = 2" in line)
    removed = next(line for line in lines if "old = 1" in line)
    header = next(line for line in lines if "@@" in line)
    assert len({added.split("\x1b[0m")[0][:30], removed.split("\x1b[0m")[0][:30]}) == 2
    assert header != added
