# Changes

This page lists the branch's main commits against `main`. The diff is `git diff origin/main...HEAD`.

## Commits

| Commit | Subject | What it changed |
| --- | --- | --- |
| `652451a` | `feat(townhall): add the agentville package with the Townhall MCP server` | Adds Townhall: storage and linter, CLI, 11 `townhall_*` MCP tools, a Textual viewer, Temporal workflows and an optional poller. |
| `f5577f2` | `chore(townhall): pin the MCP server to the package commit` | Adds `plugins/agentville/.mcp.json`, pinned to `652451a` by full SHA. |
| `5273bc9` | `chore(merge): merge origin/main into the Townhall branch` | First merge of `main`, with a merge commit. |
| `138433f`, `4471879` | Move to `townhall/` | Interim layout, replaced by `e674f0a`. |
| `3541038` | `chore(merge): merge origin/main into the Townhall branch` | Syncs with `main` after #21 merged. |
| `e674f0a` | `refactor(townhall)!: move Townhall into agentville/townhall` | Moves Townhall into `agentville/townhall/` (board package in `agentville/townhall/board/`), one `agentville` distribution, `agentville townhall ...` subcommand, Townhall's 9 dependencies made core, tests in `tests/townhall/`, plugin 0.11.0. |
| Review round 1 fix | `docs(townhall): describe the agentville/townhall layout` | Fixes the stale Townhall line in `CLAUDE.md` and rewrites `agentville/townhall/README.md` for the new layout. |
| `docs(pr)` commits | PR pages | Describe the PR under `.agentville/pr/20/`; no runtime change. |

## Files outside the package

* `plugins/agentville/.mcp.json`: launches the Townhall server from `652451a`.
* `plugins/agentville/.claude-plugin/plugin.json`: version 0.11.0.
* `CLAUDE.md`: the layout rows, the "Townhall package" section and the Verify lines.
* `README.md`: the Townhall section and its tool table.
