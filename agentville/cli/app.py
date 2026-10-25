"""The `agentville` command: one subcommand per job, `install` first."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentville import __version__
from agentville.cli.console import Console
from agentville.cli.targets import DEFAULT_TARGET, TARGETS, get_target
from agentville.cli.targets.base import (
    CHANNELS,
    EXIT_OK,
    EXIT_USAGE,
    SCOPES,
    InstallOptions,
)

EXIT_CODES = "exit codes: 0 success, 1 an install step failed, 2 usage error"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentville",
        description="Install and manage Agentville, a plugin of skills and agents.",
        epilog=EXIT_CODES,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    install = commands.add_parser(
        "install",
        help="install the Agentville plugin into an agent platform",
        description=(
            "Install the Agentville plugin and add its two steering lines to CLAUDE.md. "
            "With the claude command on PATH it runs `claude plugin marketplace add` and "
            "`claude plugin install`; without it, it writes Claude Code's settings.json."
        ),
        epilog=EXIT_CODES,
    )
    install.add_argument(
        "--target",
        choices=sorted(TARGETS),
        default=DEFAULT_TARGET,
        help=f"platform to install into (default: {DEFAULT_TARGET})",
    )
    install.add_argument(
        "--scope",
        choices=SCOPES,
        default="user",
        help="user: your home folder; project: the project folder (default: user)",
    )
    install.add_argument(
        "--channel",
        choices=CHANNELS,
        default="stable",
        help="stable: release branch; beta: beta branch; dev: main branch (default: stable)",
    )
    install.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="project folder for --scope project (default: the current folder)",
    )
    install.add_argument("--dry-run", action="store_true", help="print the actions without running or writing anything")
    install.set_defaults(handler=run_install)

    # Listed for --help only: main() hands `agentville townhall ...` to Townhall before parsing.
    commands.add_parser(
        "townhall",
        add_help=False,
        help="run Townhall, the board-and-ticket engine (see `agentville townhall --help`)",
    )
    return parser


def run_townhall(argv: list[str]) -> int:
    """Run Townhall's command tree with the arguments after `townhall`."""
    from agentville.townhall.cli.main import app as townhall_app

    try:
        townhall_app(args=argv, prog_name="agentville townhall")
    except SystemExit as exit_:
        code = exit_.code
        if code is None:
            return EXIT_OK
        return code if isinstance(code, int) else 1
    return EXIT_OK


def run_install(args: argparse.Namespace, console: Console) -> int:
    if args.project_dir is not None and args.scope != "project":
        console.warn("--project-dir is used only with --scope project; ignoring it.")
    project_dir = (args.project_dir or Path.cwd()).expanduser().resolve()
    if args.scope == "project" and not project_dir.is_dir():
        console.error(f"project folder not found: {project_dir}")
        return EXIT_USAGE
    options = InstallOptions(
        scope=args.scope,
        channel=args.channel,
        project_dir=project_dir,
        home=Path.home(),
        dry_run=args.dry_run,
    )
    target = get_target(args.target)
    place = project_dir if args.scope == "project" else options.home
    console.info(
        f"Installing Agentville ({args.channel} channel) into {target.name}, {args.scope} scope at {place}"
        + (" [dry run: nothing is changed]" if args.dry_run else "")
    )
    code = target.install(options, console)
    if code == EXIT_OK:
        if args.dry_run:
            console.info("Dry run finished; run again without --dry-run to apply.")
        else:
            console.info("Done. Restart Claude Code, or run /reload-plugins in a running session.")
    return code


def main(argv: list[str] | None = None) -> int:
    args_in = sys.argv[1:] if argv is None else argv
    if args_in[:1] == ["townhall"]:
        return run_townhall(args_in[1:])
    parser = build_parser()
    args = parser.parse_args(args_in)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return EXIT_USAGE
    return handler(args, Console(dry_run=getattr(args, "dry_run", False)))
