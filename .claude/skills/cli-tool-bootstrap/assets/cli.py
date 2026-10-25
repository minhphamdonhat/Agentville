"""Command-line interface of {{ PACKAGE_NAME }}: {{ SUMMARY }}.

Layout:
    {{ PACKAGE_NAME }} --version
    {{ PACKAGE_NAME }} list
    {{ PACKAGE_NAME }} install   [--target NAME] [--scope user|project] [--project-root PATH] [--dry-run]
    {{ PACKAGE_NAME }} uninstall [--target NAME] [--scope user|project] [--project-root PATH] [--dry-run]

Exit codes: 0 success, 1 failure, 2 usage error, 130 interrupted.
Data goes to stdout; messages and errors go to stderr.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Callable

PROG = "{{ PACKAGE_NAME }}"

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130

SCOPES = ("user", "project")


class CliError(Exception):
    """A failure the user can fix; printed as one line, without a traceback."""


@dataclass(frozen=True)
class Action:
    """One change on disk: a description for --dry-run and the function that makes it."""

    describe: str
    apply: Callable[[], None]


@dataclass(frozen=True)
class Target:
    """One place the tool acts on. Add a target by adding one entry to TARGETS."""

    name: str
    summary: str
    scopes: tuple[str, ...]
    plan: Callable[[str, str, Path], list[Action]]  # (command, scope, project_root) -> actions


def package_version() -> str:
    try:
        return version(PROG)
    except PackageNotFoundError:
        return "0+unknown"


def scope_folder(scope: str, project_root: Path) -> Path:
    """The folder a scope writes to: the user's home or the project."""
    base = Path.home() if scope == "user" else project_root
    return base / ".{{ PACKAGE_NAME }}"


def default_plan(command: str, scope: str, project_root: Path) -> list[Action]:
    folder = scope_folder(scope, project_root)
    if command == "install":
        if folder.is_dir():
            return []
        return [Action(f"create {folder}", lambda: folder.mkdir(parents=True, exist_ok=True))]
    if command == "uninstall":
        if not folder.is_dir():
            return []
        return [Action(f"remove {folder} (only when empty)", folder.rmdir)]
    raise CliError(f"no plan for command {command!r}")


TARGETS: dict[str, Target] = {
    target.name: target
    for target in (
        Target("{{ TARGET_NAME }}", "{{ TARGET_SUMMARY }}", SCOPES, default_plan),
    )
}


def run_actions(actions: list[Action], dry_run: bool) -> None:
    if not actions:
        print("nothing to do", file=sys.stderr)
    for action in actions:
        print(("would " if dry_run else "") + action.describe, file=sys.stderr)
        if not dry_run:
            try:
                action.apply()
            except OSError as exc:
                raise CliError(f"{action.describe}: {exc.strerror or exc}") from exc


def cmd_list(args: argparse.Namespace) -> int:
    for target in TARGETS.values():
        print(f"{target.name}\t{','.join(target.scopes)}\t{target.summary}")
    return EXIT_OK


def cmd_change(args: argparse.Namespace) -> int:
    target = TARGETS[args.target]
    if args.scope not in target.scopes:
        args.parser.error(f"target {target.name!r} has no scope {args.scope!r}")
    run_actions(target.plan(args.command, args.scope, args.project_root.resolve()), args.dry_run)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROG, description="{{ SUMMARY }}")
    parser.add_argument("--version", action="version", version=f"%(prog)s {package_version()}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    change = argparse.ArgumentParser(add_help=False)
    only_target = next(iter(TARGETS)) if len(TARGETS) == 1 else None
    change.add_argument("--target", choices=sorted(TARGETS), default=only_target,
                        required=only_target is None, help="where to act (see the list command)")
    change.add_argument("--scope", choices=SCOPES, default="user",
                        help="user: the home folder; project: --project-root (default: user)")
    change.add_argument("--project-root", type=Path, default=Path.cwd(),
                        help="project folder for --scope project (default: current folder)")
    change.add_argument("--dry-run", action="store_true",
                        help="print what would change and change nothing")

    list_parser = sub.add_parser("list", help="list the targets and their scopes")
    list_parser.set_defaults(func=cmd_list, parser=list_parser)
    for name, text in (("install", "install into a target"), ("uninstall", "remove from a target")):
        command_parser = sub.add_parser(name, parents=[change], help=text)
        command_parser.set_defaults(func=cmd_change, parser=command_parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CliError as exc:
        print(f"{PROG}: error: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    except KeyboardInterrupt:
        print(file=sys.stderr)
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
