# Tests and evidence

This page lists the checks run for the conductor, build-lead and agent-smith changes. The validator ran run-1 and run-2 against the working tree before commit `4dded05` (`SHA256SUMS` hashes `edb4842a9845` and `33bf5005ffcd`); the checks below were re-run on head `88f5b92` after merging `main` (PR #32, power mode) and the power change.

| Check | Command | Result |
| --- | --- | --- |
| Validator run-1 | 6 requirements (agent-smith, measure, negatives, conductor, build-lead, host paths) | 6/6 pass |
| Validator run-2 | 7 requirements, including versions and negatives on scratch copies | 7/7 pass |
| Test scripts | `python3 plugins/agentville/skills/agent-smith/scripts/test_scripts.py`, the same for `skill-smith`, and for both under `.claude/skills/` | 4 exit 0 (87, 84, 92 and 89 tests OK) |
| Measure conductor | `python3 plugins/agentville/skills/agent-smith/scripts/measure.py plugins/agentville/agents/conductor.md` | exit 0 |
| Measure pod-lead | the same script on `plugins/agentville/agents/pod-lead.md --allow-agent` | exit 0 |
| Measure build-lead | `python3 .claude/skills/agent-smith/scripts/measure.py .claude/agents/build-lead.md --allow-agent` | exit 0 |
| Measure agent-smith | `python3 plugins/agentville/skills/skill-smith/scripts/measure.py` on both agent-smith `SKILL.md` files | 2 exit 0 |
| Security scan | `python3 .claude/skills/plugin-security/scripts/scan.py` with the accepts from `CLAUDE.md` | exit 0, no critical or high finding |
| Variants and worker copies | `python3 scripts/gen_agent_variants.py --check`; `git diff --no-index --quiet` on both worker pairs | exit 0 |

## How to reproduce

```bash
python3 plugins/agentville/skills/agent-smith/scripts/test_scripts.py
python3 .claude/skills/agent-smith/scripts/test_scripts.py
python3 plugins/agentville/skills/agent-smith/scripts/measure.py plugins/agentville/agents/conductor.md
python3 plugins/agentville/skills/agent-smith/scripts/measure.py plugins/agentville/agents/pod-lead.md --allow-agent
python3 .claude/skills/agent-smith/scripts/measure.py .claude/agents/build-lead.md --allow-agent
```

## Not tested or not verifiable

A live cloud run: the `create_session` parameters, whether "act as build-lead" loads build-lead's tools, and conductor's cloud detection. The validator runs predate the merge of `main` and the power change; the Verify block covers both.
