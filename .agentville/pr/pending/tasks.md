# Tasks done

This page lists the branch's commits against `main` and what each one changed. The diff is `git diff origin/main...HEAD`: 51 files, 12,336 insertions and 4 deletions.

## Commits

The commits appear in the order they were made.

| Commit | Subject | What it changed |
| --- | --- | --- |
| `652451a` | `feat(townhall): add the agentville package with the Townhall MCP server` | Adds the package in `agentville/`: storage and linter, CLI, 11 `townhall_*` MCP tools, a Textual viewer, Temporal workflows and an optional poller; sets plugin version 0.7.0 and describes the package in `CLAUDE.md` and `README.md`. |
| `f5577f2` | `chore(townhall): pin the MCP server to the package commit` | Adds `plugins/agentville/.mcp.json`, pinned to `652451a` by full SHA. |
| `78c6620` | `docs(townhall): describe Townhall's files beside the workspace` | Describes `.agentville/config.toml` and `.agentville/townhall/` in `CLAUDE.md` and `README.md`, beside the workspace's `.agentville/topics/`. |
| `5273bc9` | `chore(merge): merge origin/main into the Townhall branch` | Merges `origin/main` at `5c0986f` with a merge commit; sets plugin version 0.10.0. |
| `138433f` | `fix(townhall): move the package to townhall/ so it no longer shares agentville/ with the installer` | Moves the package to `townhall/` and updates the paths in `CLAUDE.md`, `README.md`, `.gitignore` and the release-flow checks. |

## Merge resolution

The merge kept both sides. `CLAUDE.md` takes `main`'s git-ignored topics row and keeps the Townhall rows; its Verify block keeps `main`'s checks and adds the Townhall `pytest` and `ruff check` lines. `README.md` keeps `main`'s installer text and adds the Townhall section. `plugins/agentville/.claude-plugin/plugin.json` moves to 0.10.0, from 0.9.2 on `main` and 0.7.0 on the branch.

## Files outside the package

These shipped and documentation files change:

* `plugins/agentville/.mcp.json`: new, launches the Townhall server.
* `plugins/agentville/.claude-plugin/plugin.json`: version 0.10.0.
* `CLAUDE.md`: Townhall rows, the "Townhall package" section, the release-flow `checks` line and two Verify lines.
* `README.md`: the uv requirement and the "Townhall" section with its tool table.
* `.gitignore`: ignores `townhall/.venv/`, `townhall/.pytest_cache/` and `townhall/.ruff_cache/`.
