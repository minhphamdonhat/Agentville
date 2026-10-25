# Tests and evidence

This page lists every check the validator ran at `26c43c8` (evidence folder `run-2`, `SHA256SUMS` hash `810454535056`; run-1 at `4471879` is superseded) and its result. All ran on 2026-10-25, on Linux, in a clean clone except the two scans, which read all refs in the checkout. The commits after `26c43c8` (`8923fc8`, `4e542f9`, `3c87e29` and the page move) change only the PR pages, so those results stand. Evidence run-4 at `3c87e29` re-checked the review findings R1 to R3.

## Verify before you finish

These are the commands under "Verify before you finish" in `CLAUDE.md`. Each exited 0.

| Check | Result |
| --- | --- |
| `plugins/agentville/skills/agent-smith/scripts/test_scripts.py` | 80 tests, OK |
| `plugins/agentville/skills/skill-smith/scripts/test_scripts.py` | 84 tests, OK |
| `.claude/skills/agent-smith/scripts/test_scripts.py` | 85 tests, OK |
| `.claude/skills/skill-smith/scripts/test_scripts.py` | 89 tests, OK |
| Two `git diff --no-index --quiet` checks on `worker.md` | Identical |
| `scripts/gen_agent_variants.py --check` | Exit 0 |
| `plugin-security/scripts/scan.py`, default gate | Exit 0; no critical or high finding |
| `uv run --directory townhall pytest` | 277 passed, 1 warning |
| `uv run --directory townhall ruff check` | All checks passed |
| `uv run pytest` (installer, repository root) | 38 passed |

## Pre-publish gate

The gate from "Security and publishing" in `CLAUDE.md` exited 0 with `--fail-on medium` and the four `--accept` options. Its only remaining output is an informational note on `Co-Authored-By` trailers, which the rules allow.

## How to reproduce

The local `uv` was 0.11.32, below the package's `required-version = ">=0.13.5"`. The `uv` commands ran through a newer `uv` without changing the installed one:

```bash
uvx --from 'uv>=0.13.5' uv run --directory townhall pytest -q
uvx --from 'uv>=0.13.5' uv run --directory townhall ruff check
uvx --from 'uv>=0.13.5' uv run pytest -q
```

## Not tested or not verifiable

The MCP server was not started from the pinned `.mcp.json`, and no live Temporal run was made. No check ran on macOS or Windows, or with `uv` older than 0.13.5. #13 reports earlier validation against MCP over stdio, a live Temporal dev server and the headless viewer; those results were not repeated on this branch.
