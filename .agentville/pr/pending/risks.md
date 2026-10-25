# Risks, limits and rollback

This page lists the risks this PR brings and what limits or mitigates each one.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Both packages publish the name `agentville` | Installing both in one environment makes one `agentville` console script replace the other. | `uvx` runs each in its own environment; the [decisions page](decisions.md) asks whether to rename one. |
| The pin `652451a` must stay reachable | A squash-merge drops the commit, so `.mcp.json` points at nothing and the server does not start. | Merge without squashing, or re-pin after the merge. Today only the two feature branches on `origin` hold it. |
| The pin uses `subdirectory=agentville` | A re-pin to a later SHA that keeps this subdirectory likely fails to build (inferred: the installer's `pyproject.toml` sits at the repository root, not in `agentville/`), so the server does not start. | `CLAUDE.md` requires changing the subdirectory to `townhall` in the same edit as the pin. |
| Slow first start | `uvx` downloads Python 3.15 and builds PyYAML from source, so Claude Code can time out. | Raise `MCP_TIMEOUT`, as `README.md` describes. |
| `uv` older than 0.13.5 | Development commands fail, and `uvx` may not enforce `required-version` for `--from` sources. | `README.md` states the minimum; run a newer `uv` through `uvx --from 'uv>=0.13.5'`. |

## Known limits

* The files on disk are the ground truth; Temporal mirrors them on a best-effort basis.
* The viewer imports a private Textual module, as #13 reports; the `textual>=8.2.8,<9` cap in `townhall/pyproject.toml` protects it for now.
* Townhall is not wired into any agent or skill yet.

## Rollback

* Whole PR: `git revert -m 1 <merge-sha>` on `main`, where `<merge-sha>` is this PR's merge commit.
* The merge with `main` only: `git revert -m 1 5273bc9`, then revert the later commits.
* The move to `townhall/` (`138433f` and `4471879`) on its own is not supported: reverting it puts Townhall back in `agentville/`, where it collides with `main`'s installer.
