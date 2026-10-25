# Tests and evidence

This page lists every requirement the validator checked at `b3ac5b2` (evidence folder `run-3`, `SHA256SUMS` hash `37622fd28912`) and its result. All 92 checks pass; `summary.txt` (hash `228820aff473`) holds one line per check and `requirements.md` (hash `96a186eff011`) maps checks to requirements.

| Requirement | What it checks | Checks | Result | First check file and hash |
| --- | --- | --- | --- | --- |
| REQ-1 | Installer under `agentville/cli/`, pytest, help, `uv build` | 8 (5 positive, 2 negatives, 1 control) | pass | `build/REQ-1-CHK-1-01.txt` `fa54bd32cbf4` |
| REQ-2 | `CLAUDE.md` Verify commands, `--fail-on medium` gate, `measure.py` on changed files | 23 (3 negatives) | pass | `build/REQ-2-gate-command.txt` `1d5bb5355a57` |
| REQ-3 | `pr-report` location, frontmatter, binding, push rule, forbidden patterns, trailers | 16 (5 negatives, 1 control) | pass | `docs/REQ-3-CHK-1-01.txt` `22792e4dd2c7` |
| REQ-4 | Shipped files free of commit and PR handling; `validator.md` and `reviewer.md` at 3.0.0 | 17 (6 negatives, 2 controls) | pass | `docs/REQ-4-CHK-1-01.txt` `4f686fef290a` |
| REQ-5 | `pr-report` content: modes, relay output and PR URL location, Verdict and 9 H2s, Blockers rows, 8000 limit, Mermaid `accTitle` and `accDescr`, head-SHA links, lookup by head and base, local `report.md` fallback, refusals, `python3` in the shell allow-list | 23 (11 positive, 11 mutated-copy negatives, 1 control) | pass | `docs/REQ-5-CHK-1-01.txt` `9beb3decc2b6` |
| REQ-6 | Worktree on `feat/pr-report`; merge base `5c0986f3e5b3` | 5 (2 negatives, 1 control) | pass | `build/REQ-6-CHK-1-01.txt` `ce59992a7c76` |

## How to reproduce

```bash
python3 plugins/agentville/skills/agent-smith/scripts/test_scripts.py
python3 plugins/agentville/skills/skill-smith/scripts/test_scripts.py
python3 .claude/skills/agent-smith/scripts/test_scripts.py
python3 .claude/skills/skill-smith/scripts/test_scripts.py
python3 scripts/gen_agent_variants.py --check
python3 .claude/skills/plugin-security/scripts/scan.py --accept 'PS-06:*release-flow/SKILL.md' --accept 'PS-06:*pr-report/SKILL.md' --accept 'PS-25:*.claude-plugin/marketplace.json' --accept 'PS-09:*agents/worker.md' --accept 'PS-09:*agents/worker-*-*.md' --fail-on medium
uv run pytest
```

## Not tested or not verifiable

None, as run-3 records.
