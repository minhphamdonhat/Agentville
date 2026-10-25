# Risks and known limits

This page lists the risks this PR brings and what limits or mitigates each one.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Both packages publish the name `agentville` | Installing both in one environment makes one `agentville` console script replace the other. | `uvx` runs each in its own environment; the [decisions page](decisions.md) asks whether to rename one. |
| The pin `652451a` must stay reachable | A squash-merge drops the commit, so `.mcp.json` points at nothing and the server does not start. | Merge without squashing, or re-pin after the merge. Today only the two feature branches on `origin` hold it. |
| The pin uses `subdirectory=agentville` | A re-pin to a later SHA that keeps this subdirectory starts the installer, not Townhall. | `CLAUDE.md` requires changing the subdirectory to `townhall` in the same edit as the pin. |
| Slow first start | `uvx` downloads Python 3.15 and builds PyYAML from source, so Claude Code can time out. | Raise `MCP_TIMEOUT`, as `README.md` describes. |
| `uv` older than 0.13.5 | Development commands fail, and `uvx` may not enforce `required-version` for `--from` sources. | `README.md` states the minimum; run a newer `uv` through `uvx --from 'uv>=0.13.5'`. |

## Known limits

* The files on disk are the ground truth; Temporal mirrors them on a best-effort basis.
* The viewer imports a private Textual module, as #13 reports; the `textual>=8.2.8,<9` cap in `townhall/pyproject.toml` protects it for now.
* `townhall/README.md` still shows `uvx --python 3.15 --from ./agentville`, from before the move; it should read `./townhall`.
* `README.md` says "Version 0.7.0 introduces the package"; the plugin now ships it in 0.10.0.
* Townhall is not wired into any agent or skill yet.
