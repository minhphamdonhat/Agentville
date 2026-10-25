# Risks, limits and rollback

This page lists the risks this PR brings and what limits or mitigates each one.

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Validator evidence field `commit:` renamed `revision:` | Anything that reads `commit:` from validator evidence stops finding it. | Plugin 0.10.0 marks the break; validator and reviewer are at 3.0.0. |
| `voice` no longer covers commit or PR text | Commit and PR text written with the shipped plugin follow no shipped standard. | The owner's decision; the repo-level `pr-report` renders this repository's PRs. |
| `agentville/__init__.py` stays at the package root | Likely merge point with the later Townhall move into `agentville/townhall/`. | Resolve it when that move lands. |
| PR #20 is on the old plugin version | It needs a version bump when it syncs from `main`. | PR #20 moves to plugin 0.11.0 then. |

## Rollback

* Whole PR: `git revert -m 1 {merge-sha}` on `main`.
