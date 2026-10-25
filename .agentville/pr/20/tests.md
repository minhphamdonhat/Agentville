# Tests and evidence

The validator ran these checks on Linux after the move into `agentville/townhall/`. Evidence: `.agentville/topics/agentville-pr20-sync-2026-10-25/evidence/run-1`, `SHA256SUMS` hash `38014ab84263`. Earlier runs at `26c43c8` are superseded.

| Check | Result |
| --- | --- |
| `uvx --from 'uv>=0.13.5' uv run --locked pytest -q` | 316 passed: 38 installer, 278 Townhall |
| `agentville --help` and `agentville townhall --help` | Pass |
| `ruff check agentville tests` | Pass |
| Package build | Pass |
| "Verify before you finish" in `CLAUDE.md` | Pass |
| Pre-publish gate, `--fail-on medium` | Pass |

The Verify block's ruff scope is now `ruff check agentville tests`, run from the repository root.

## How to reproduce

```bash
uvx --from 'uv>=0.13.5' uv run --locked pytest -q
uvx --from 'uv>=0.13.5' uv run --locked ruff check agentville tests
uvx --from 'uv>=0.13.5' uv run --locked agentville townhall --help
```

## Not tested

* The macOS and Windows CI jobs for the Townhall tests in `.github/workflows/publish.yml`.
* A live MCP launch from `.mcp.json`.
* A live Temporal run.
