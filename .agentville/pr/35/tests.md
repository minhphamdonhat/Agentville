# Tests and evidence

This page lists the round 1 checks (evidence folder `run-1`, `SHA256SUMS` hash `ef189ef95d27`); the body keeps the summary.

| Check | Command | Result | Evidence hash |
| --- | --- | --- | --- |
| CLAUDE.md verify commands (8) | the 8 commands under Verify before you finish | all exit 0 | `ef189ef95d27` |
| Security scan | `python3 .claude/skills/plugin-security/scripts/scan.py` with the accepted rules | critical 0, high 0 | `ef189ef95d27` |
| Measure `pod-lead` and agent-smith | `measure.py` on both | exit 0 | `ef189ef95d27` |
| Removed paths absent | listing check | absent | `ef189ef95d27` |
| Version and import | read `plugin.json`, `CLAUDE.md` | round 1: version 1.0.0; `root-agent` import gone (superseded by round 2) | `ef189ef95d27` |
| Leftover names | search | `build-lead` and `lookout` remain only in `.claude/skills/conductor/` | `ef189ef95d27` |
