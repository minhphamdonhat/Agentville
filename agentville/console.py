"""Plain console output shared by the CLI and the targets."""

from __future__ import annotations

import sys
from typing import TextIO


class Console:
    """Prints progress to stdout and problems to stderr, one line each."""

    def __init__(self, dry_run: bool = False, out: TextIO | None = None, err: TextIO | None = None) -> None:
        self.dry_run = dry_run
        self._out = out if out is not None else sys.stdout
        self._err = err if err is not None else sys.stderr

    def info(self, message: str) -> None:
        print(message, file=self._out)

    def action(self, message: str) -> None:
        """Report an action: done, or only planned under --dry-run."""
        prefix = "[dry-run] would " if self.dry_run else ""
        print(f"{prefix}{message}", file=self._out)

    def warn(self, message: str) -> None:
        print(f"warning: {message}", file=self._err)

    def error(self, message: str) -> None:
        print(f"error: {message}", file=self._err)
