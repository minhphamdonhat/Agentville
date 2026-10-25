# CLI interface rules

The shape every bootstrapped CLI keeps. `{{ SKILL_ROOT }}/assets/cli.py` implements it with `argparse` from the standard library.

## Layout

```text
src/<module-name>/__init__.py    one-line docstring
src/<module-name>/__main__.py    from .cli import main; raise SystemExit(main())
src/<module-name>/cli.py         parser, registry, commands
tests/test_cli.py                unittest, no third-party runner
```

The `src/` layout keeps tests from importing the source folder by accident, so they test the installed package.

## Commands and flags

| Rule | Example for `acme-tool` |
| --- | --- |
| One verb per subcommand, each with its own `--help`. | `acme-tool install`, `acme-tool list` |
| `--version` on the main parser prints `<name> <version>`, read with `importlib.metadata.version`, never a second copy of the number. | `acme-tool 0.1.0` |
| Every subcommand that writes takes `--dry-run`, which prints each change as `would <change>` and writes nothing. | `would create {{ USER_ROOT }}/.acme-tool` |
| A subcommand that acts on a place takes `--target` and `--scope`. With one target, `--target` defaults to it. | `acme-tool install --target vscode --scope project` |
| A second run with the same arguments changes nothing and exits 0. | `nothing to do` |
| Data goes to stdout, one record per line, tab-separated; messages, progress and errors go to stderr. | `acme-tool list \| cut -f1` |
| No prompt when stdin is not a terminal; a flag such as `--yes` answers in scripts. | `acme-tool uninstall --yes` |
| Colour only on a terminal, and never when `NO_COLOR` is set. | `NO_COLOR=1 acme-tool list` |

## Target and scope registry

A target is a place the tool acts on, such as an editor, a shell or a service. A scope is where on disk: `user` (under the home folder) or `project` (under `--project-root`). Each target is one `Target` entry in the `TARGETS` dictionary with its name, a one-line summary, the scopes it supports and a `plan` function that returns the list of `Action`s for a command. Adding a target is adding one entry; the parser, `list`, `--dry-run` and the tests pick it up with no other change.

```python
TARGETS = {t.name: t for t in (
    Target("vscode", "Visual Studio Code settings", ("user", "project"), vscode_plan),
    Target("zed", "Zed settings", ("user",), zed_plan),
)}
```

A plan function only reads the disk and returns actions; `run_actions` applies them, so `--dry-run` and the real run share one code path.

## Exit codes

| Code | Meaning | Raised by |
| --- | --- | --- |
| 0 | Success, including "nothing to do". | `return EXIT_OK` |
| 1 | A failure the user can fix, printed as one `<name>: error: <message>` line. | `raise CliError(...)` |
| 2 | Usage error: unknown command, bad flag, scope a target lacks. | `argparse` and `parser.error(...)` |
| 130 | Interrupted with Ctrl+C. | `KeyboardInterrupt` |

Never print a traceback for an expected failure; a traceback means a bug.
