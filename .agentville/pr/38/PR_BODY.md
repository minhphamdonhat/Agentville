This PR adds the footer line `Built with Agentville.` at the end of `README.md`, as issue #36 asks. It replaces the earlier closed PR #37 for the same change.

Verdict: Ready to merge. Blocking items: 0. Decisions needed: 0.

## Decisions needed

none

## Context

Closes #36

Issue #36 asks for a one-line note at the end of `README.md`. Ready for review; one file changed. No plugin version bump: the change is `README.md` only, which `CLAUDE.md` exempts.

## Changes

| Task | Files | Behaviour change | Evidence id |
| --- | --- | --- | --- |
| T1: add the footer line | `README.md` | A blank separator line and `Built with Agentville.` at the end of the file; nothing else changes | run-1/01, run-1/02, run-1/03 |
| T2: run the Verify checks | none | No change | run-1/04 to run-1/10 |

## Architecture changes

none

## Tests and evidence

| Check | Command | Result | Evidence hash |
| --- | --- | --- | --- |
| Last line of README | `tail -n 1 README.md` | exit 0; prints `Built with Agentville.` | run-1/01-tail-readme.txt |
| Diff scope | `git diff --stat` | exit 0; `README.md \| 2 ++` only | run-1/02-diff-stat.txt |
| Shipped agent-smith tests | `python3 plugins/agentville/skills/agent-smith/scripts/test_scripts.py` | exit 0; 87 tests OK | run-1/04-agent-smith-tests.txt |
| Shipped skill-smith tests | `python3 plugins/agentville/skills/skill-smith/scripts/test_scripts.py` | exit 0; 84 tests OK | run-1/05-skill-smith-tests.txt |
| Maintainer agent-smith tests | `python3 .claude/skills/agent-smith/scripts/test_scripts.py` | exit 0; 92 tests OK | run-1/06-maint-agent-smith-tests.txt |
| Maintainer skill-smith tests | `python3 .claude/skills/skill-smith/scripts/test_scripts.py` | exit 0; 89 tests OK | run-1/07-maint-skill-smith-tests.txt |
| Worker copy, shipped smith | `git diff --no-index --quiet plugins/agentville/agents/worker.md plugins/agentville/skills/agent-smith/assets/base/worker.md` | exit 0 | run-1/08-worker-pair1.txt |
| Worker copy, maintainer smith | `git diff --no-index --quiet plugins/agentville/agents/worker.md .claude/skills/agent-smith/assets/base/worker.md` | exit 0 | run-1/09-worker-pair2.txt |
| Agent variants | `python3 scripts/gen_agent_variants.py --check` | exit 0 | run-1/10-variants-check.txt |

Not tested or not verifiable: none; the change is text only.

## Risks, limits and rollback

None beyond a revert of one commit: `git revert {commit-sha}`, or `git revert -m 1 {merge-sha}` on `main` after merge.

## Reviewer checklist

- [ ] The footer wording `Built with Agentville.` reads as intended.
- [ ] A footer after the Licence section is the right place for it.
- [ ] Skipping the plugin version bump for a README-only change is acceptable.

## Review verdicts

Round 1: pass. The reviewer confirmed only `README.md` changed, the file ends in a single LF, there are no secrets or host paths, and no table or version change is needed.

## Evidence index

Head: {head-sha}

| Evidence | Where |
| --- | --- |
| PR body source | [PR_BODY.md](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/38/PR_BODY.md) |
| Validator evidence | Folder `run-1` in the topic workspace (git-ignored, not committed), files 01 to 10; `SHA256SUMS` hash not given |

🤖 Generated with [Claude Code](https://claude.com/claude-code)
