# Changes

This page lists the branch's commits against `main` and what each one changed. The diff is `git diff origin/main...HEAD`: 57 files, 12,568 insertions and 4 deletions at `4471879`.

## Commits

The commits appear in the order they were made.

| Commit | Subject | What it changed |
| --- | --- | --- |
| `652451a` | `feat(townhall): add the agentville package with the Townhall MCP server` | Adds the package in `agentville/`: storage and linter, CLI, 11 `townhall_*` MCP tools, a Textual viewer, Temporal workflows and an optional poller; sets plugin version 0.7.0 and describes the package in `CLAUDE.md` and `README.md`. |
| `f5577f2` | `chore(townhall): pin the MCP server to the package commit` | Adds `plugins/agentville/.mcp.json`, pinned to `652451a` by full SHA. |
| `78c6620` | `docs(townhall): describe Townhall's files beside the workspace` | Describes `.agentville/config.toml` and `.agentville/townhall/` in `CLAUDE.md` and `README.md`, beside the workspace's `.agentville/topics/`. |
| `5273bc9` | `chore(merge): merge origin/main into the Townhall branch` | Merges `origin/main` at `5c0986f` with a merge commit; sets plugin version 0.10.0. |
| `138433f` | `fix(townhall): move the package to townhall/ so it no longer shares agentville/ with the installer` | Moves the package to `townhall/` and updates the paths in `CLAUDE.md`, `README.md`, `.gitignore` and the release-flow checks. |
| `7a9125e` | `docs(pr): add the Townhall PR description and detail pages` | Adds the PR description and its detail pages under `.agentville/pr/pending/` (moved to `.agentville/pr/20/` by the last commit below). |
| `4471879` | `docs(townhall): point the docs at townhall/ and version 0.10.0` | Updates `README.md` and `townhall/README.md` to the new folder and version. |
| `74dc5c1` | `docs(pr): restructure the PR description for code-free review` | Restructures the PR description and detail pages; no runtime change. |
| `26c43c8` | `docs(pr): fix the review findings in the PR description` | Fixes the review findings and adds the `.agentville/pr/` row to the layout table in `CLAUDE.md`. |
| `8923fc8` | `docs(pr): drop the partial rollback and cite evidence run-2` | Removes the partial rollback and cites evidence run-2; docs only. |
| `4e542f9` | `docs(pr): restore run-2 evidence hashes in the tests table` | Restores the run-2 evidence hashes in the tests table; docs only. |
| `3c87e29` | `docs(pr): cite the merge check hash in the tests table` | Cites the merge check hash in the tests table; docs only. |
| This commit | `docs(pr): move the PR pages to .agentville/pr/20` | Moves the PR pages from `pending/` to `.agentville/pr/20/` and fills the PR number and head SHA links; docs only. |

Every commit after `4471879` changes only the PR pages and one `CLAUDE.md` table row, so the diff counts above hold at HEAD apart from those files.

## Merge resolution

The merge kept both sides. `CLAUDE.md` takes `main`'s git-ignored topics row and keeps the Townhall rows; its Verify block keeps `main`'s checks and adds the Townhall `pytest` and `ruff check` lines. `README.md` keeps `main`'s installer text and adds the Townhall section. `plugins/agentville/.claude-plugin/plugin.json` moves to 0.10.0, from 0.9.2 on `main` and 0.7.0 on the branch.

## Files outside the package

These shipped and documentation files change:

* `plugins/agentville/.mcp.json`: new, launches the Townhall server.
* `plugins/agentville/.claude-plugin/plugin.json`: version 0.10.0.
* `CLAUDE.md`: Townhall rows, the "Townhall package" section, the release-flow `checks` line and two Verify lines.
* `README.md`: the uv requirement and the "Townhall" section with its tool table.
* `.gitignore`: ignores `townhall/.venv/`, `townhall/.pytest_cache/` and `townhall/.ruff_cache/`.
