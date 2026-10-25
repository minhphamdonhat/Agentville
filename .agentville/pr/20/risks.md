# Risks, limits and rollback

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Breaking CLI rename | Scripts calling `agentville init` or `agentville engine` fail. | Use `agentville townhall init` and `agentville townhall engine`; `CLAUDE.md` and `README.md` show the new commands. |
| Townhall's 9 dependencies are core | `uvx agentville install` downloads more packages. | They are imported lazily, only for `agentville townhall`. |
| `.mcp.json` pins `652451a` | The plugin runs the pre-move server with `agentville engine mcp`. | The re-pin is an open decision; it must drop `#subdirectory` and use `agentville townhall engine mcp` in the same edit. |
| The pin must stay reachable | A squash-merge could drop `652451a`, so the server does not start. | The owner merges manually; keep `652451a` on a branch `origin` keeps. |
| Slow first start | `uvx` fetches Python 3.15, so Claude Code can time out. | Raise `MCP_TIMEOUT`, as `README.md` describes. |
| `uv` older than 0.13.5 | `uv run --locked` fails on `required-version`. | Run `uvx --from 'uv>=0.13.5' uv ...`. |

## Known limits

* The files on disk are the ground truth; Temporal mirrors them on a best-effort basis.
* The Townhall tests were not run on macOS or Windows.

## Rollback

* Whole PR: `git revert -m 1 <merge-sha>` on `main`, where `<merge-sha>` is this PR's merge commit.
