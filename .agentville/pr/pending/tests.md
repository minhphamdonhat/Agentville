# Tests and evidence

This page lists every check the validator ran at `7da0f7b` (evidence folder `run-4`, `SHA256SUMS` hash `02cd20c053c9`) and its result.

| Check | Command | Result |
| --- | --- | --- |
| Skill measure, shipped | `python3 plugins/agentville/skills/skill-smith/scripts/measure.py plugins/agentville/skills/intercommunicate/SKILL.md` and the root-agent file | exit 0 |
| Agent measure, shipped | `python3 plugins/agentville/skills/agent-smith/scripts/measure.py plugins/agentville/agents/pod-lead.md` | exit 0 |
| Measure, maintainer copies | the same three files with the `.claude/skills` scripts | exit 0 |
| Verify commands | the 8 commands in `CLAUDE.md` under "Verify before you finish" | all exit 0 |
| Pre-publish gate | `python3 .claude/skills/plugin-security/scripts/scan.py --accept 'PS-06:*release-flow/SKILL.md' --accept 'PS-06:*pr-report/SKILL.md' --accept 'PS-25:*.claude-plugin/marketplace.json' --accept 'PS-09:*agents/worker.md' --accept 'PS-09:*agents/worker-*-*.md' --fail-on medium` | exit 0; critical 0, high 0, medium 0 |
| Versions | intercommunicate 1.2.1, pod-lead 1.5.0, root-agent 2.3.1, plugin 0.11.0 | confirmed |
| Commit hygiene | one `Co-Authored-By:` trailer per commit, no session line | confirmed |
| Remote head | `origin` equals `7da0f7b` | confirmed |

## How to reproduce

```bash
python3 plugins/agentville/skills/skill-smith/scripts/measure.py plugins/agentville/skills/intercommunicate/SKILL.md
python3 plugins/agentville/skills/agent-smith/scripts/measure.py plugins/agentville/agents/pod-lead.md
```

## Not tested or not verifiable

A live two-session ACK run. With-skill vs baseline evals were not run, because a worker holds no `Agent` tool. The standalone eval cases were hand-run only, self-graded, and are stale for mode `await`.
