This PR removes the transitional `PS-06:.claude/skills/pr-report/SKILL.md` security-scan exception and its note sentence, now that PR #31 has merged and `main` no longer holds that path.

Verdict: Pending review. Blocking items: 0. Decisions needed: 0.

## Decisions needed

none

## Context

PR #31 renamed the maintainer `pr-report` skill to `report`. Until it merged, `main` still held the old path, so the Verify block accepted its `PS-06` finding. `origin/main` no longer lists `.claude/skills/pr-report/`, so the exception is dead and is dropped from both places that carry the scan command.

## Changes

| Task | Files | Behaviour change | Evidence id |
| --- | --- | --- | --- |
| Drop the exception (`23a3494`) | `CLAUDE.md` | Verify scan command loses one `--accept`; the note sentence is removed | CHK-1 |
| Drop the exception (`23a3494`) | `.claude/skills/docs-site/SKILL.md` | Same `--accept` removed; `metadata.version` 1.5.2 to 1.5.3 | CHK-1 |

## Architecture changes

none

## Tests and evidence

| Check | Command | Result | Evidence hash |
| --- | --- | --- | --- |
| Shipped agent-smith tests | `python3 plugins/agentville/skills/agent-smith/scripts/test_scripts.py` | OK, exit 0 | none |
| Shipped skill-smith tests | `python3 plugins/agentville/skills/skill-smith/scripts/test_scripts.py` | OK, exit 0 | none |
| Maintainer agent-smith tests | `python3 .claude/skills/agent-smith/scripts/test_scripts.py` | OK, exit 0 | none |
| Maintainer skill-smith tests | `python3 .claude/skills/skill-smith/scripts/test_scripts.py` | OK, exit 0 | none |
| Worker identity (shipped copy) | `git diff --no-index --quiet plugins/agentville/agents/worker.md plugins/agentville/skills/agent-smith/assets/base/worker.md` | exit 0 | none |
| Worker identity (maintainer copy) | `git diff --no-index --quiet plugins/agentville/agents/worker.md .claude/skills/agent-smith/assets/base/worker.md` | exit 0 | none |
| Variant drift | `python3 scripts/gen_agent_variants.py --check` | exit 0 | none |
| Security scan | `python3 .claude/skills/plugin-security/scripts/scan.py` with the 4 remaining accepts | critical 0, high 0, medium 1, gate pass | none |

Not tested or not verifiable: the one medium finding is `PS-06` on `.claude/skills/pr-report/SKILL.md` at the stale local `main` ref only; `origin/main` and this branch do not hold the path.

## Risks, limits and rollback

Low risk: a maintainer-only documentation and command change, with no plugin change. Roll back with `git revert -m 1 {merge-sha}` on `main`.

## Reviewer checklist

- [ ] Dropping the accept from both `CLAUDE.md` and `docs-site` is the full set of places that carried it.
- [ ] The `docs-site` patch bump to 1.5.3 suits a wording-only change.

## Review verdicts

Pending: no reviewer has run on this change.

## Evidence index

Head: {head-sha}

| Evidence | Where |
| --- | --- |
| Verify block output | Run in the working session at `23a3494`; no sealed evidence folder |

🤖 Generated with [Claude Code](https://claude.com/claude-code)
