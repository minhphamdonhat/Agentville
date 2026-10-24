"""Tests for the {{ PACKAGE_NAME }} command line; standard library only."""

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from {{ MODULE_NAME }} import cli

TARGET = next(iter(cli.TARGETS))


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(list(argv))
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def test_version_prints_name_and_exits_zero(self):
        code, out, _ = run("--version")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertTrue(out.startswith(cli.PROG + " "))

    def test_unknown_command_is_a_usage_error(self):
        code, _, err = run("no-such-command")
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn("invalid choice", err)

    def test_list_names_every_target(self):
        code, out, _ = run("list")
        self.assertEqual(code, cli.EXIT_OK)
        for name in cli.TARGETS:
            self.assertIn(name, out)

    def test_dry_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = run("install", "--target", TARGET, "--scope", "project",
                               "--project-root", tmp, "--dry-run")
            self.assertEqual(code, cli.EXIT_OK)
            self.assertIn("would ", err)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_install_is_idempotent_and_uninstall_reverts(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = ("--target", TARGET, "--scope", "project", "--project-root", tmp)
            self.assertEqual(run("install", *args)[0], cli.EXIT_OK)
            self.assertEqual(run("install", *args)[0], cli.EXIT_OK)
            self.assertEqual(run("uninstall", *args)[0], cli.EXIT_OK)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_module_entry_point(self):
        result = subprocess.run([sys.executable, "-m", "{{ MODULE_NAME }}", "--version"],
                                capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
