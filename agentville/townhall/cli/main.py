"""Typer root application for Townhall, run as `agentville townhall ...`.

The installer CLI in `agentville.cli.app` hands every argument after `townhall` to
`app`. The root is the board group itself, so `agentville townhall list` and
`agentville townhall BOARD_ID ...` work directly; `init` and `engine` are static
commands beside the board ids, and a static command wins over a board id of the
same name.
"""

import asyncio
import inspect
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import typer

from agentville import __version__
from agentville.townhall.board.cli import (
    BOARD_META,
    ROOT_META,
    _dynamic_group,
    board_app,
    format_finding,
    project_root,
    townhall_app,
)
from agentville.townhall.board.storage import TownhallStorage
from agentville.townhall.core.errors import AgentvilleError, PageBudgetError


class RootGroup(_dynamic_group(BOARD_META, lambda: board_app)):  # type: ignore[misc]
    """Root group: board ids as dynamic commands, Agentville errors as one line and exit 1."""

    def invoke(self, ctx: Any) -> Any:
        try:
            return super().invoke(ctx)
        except PageBudgetError as error:
            typer.echo(f"Error: {error}", err=True)
            for finding in error.findings:
                typer.echo(f"  {format_finding(finding)}", err=True)
            raise typer.Exit(1) from None
        except (AgentvilleError, OSError) as error:
            typer.echo(f"Error: {error}", err=True)
            raise typer.Exit(1) from None


app = typer.Typer(
    cls=RootGroup,
    name="townhall",
    help="Townhall Kanban and documentation engine.",
    epilog=townhall_app.info.epilog,
    no_args_is_help=True,
)
engine_app = typer.Typer(
    help="Temporal engine and MCP server management.", no_args_is_help=True
)

# The board commands (`list`, `create`) sit on the root, beside `init` and `engine`.
app.registered_commands.extend(townhall_app.registered_commands)
app.add_typer(engine_app, name="engine")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Print the version and exit.",
    ),
    root_dir: Annotated[
        Path | None,
        typer.Option(
            "--root",
            help="Project root. Default: $AGENTVILLE_ROOT, $CLAUDE_PROJECT_DIR, the nearest parent folder holding .agentville/, else the current folder.",
        ),
    ] = None,
) -> None:
    """Townhall Kanban and documentation engine."""
    ctx.meta[ROOT_META] = root_dir.resolve() if root_dir else None


@app.command()
def init(
    ctx: typer.Context,
    path: Annotated[
        Path | None,
        typer.Argument(
            help="Folder to initialise. Default: --root, else the current folder."
        ),
    ] = None,
) -> None:
    """Initialise `.agentville/` and the Townhall template in a project."""
    explicit = ctx.meta.get(ROOT_META)
    target = path.resolve() if path else (Path(explicit) if explicit else Path.cwd())
    result = TownhallStorage(target).init_project()
    if result.created:
        typer.echo(
            f"Initialised .agentville/ in {target} ({len(result.created)} files created)."
        )
        for name in result.created:
            typer.echo(f"  {name}")
    else:
        typer.echo(f"Already initialised: {target}")


class Transport(StrEnum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


def _run_engine(call: Any, *args: Any, **kwargs: Any) -> None:
    result = call(*args, **kwargs)
    if inspect.iscoroutine(result):
        asyncio.run(result)


@engine_app.command("worker")
def engine_worker(ctx: typer.Context) -> None:
    """Start the Temporal worker process."""
    from agentville.townhall.board.workflows import run_worker

    _run_engine(run_worker, project_root(ctx))


@engine_app.command("poller")
def engine_poller(ctx: typer.Context) -> None:
    """Run the background triage polling loop."""
    from agentville.townhall.board.workflows import run_poller

    _run_engine(run_poller, project_root(ctx))


@engine_app.command("mcp")
def engine_mcp(
    ctx: typer.Context,
    transport: Annotated[
        Transport,
        typer.Option("--transport", help="How the MCP server talks to its client."),
    ] = Transport.STDIO,
) -> None:
    """Run the MCP server (stdio by default) for the same project root as the worker."""
    from agentville.townhall.mcp.server import run

    run(transport=transport.value, root=project_root(ctx))
