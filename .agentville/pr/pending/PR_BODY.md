This PR adds the one-line footer `Built with Agentville.` at the end of README.md, as issue #36 asks. It supersedes no other PR.

Verdict: Ready to merge. Blocking items: 0. Decisions needed: 1.

## Decisions needed

| Question | Options | Agent default | Consequence if unanswered |
| --- | --- | --- | --- |
| Should the line sit under its own footer heading instead of under `## Licence`? | Keep it under `## Licence`, or add a separate footer heading | Under `## Licence`, as its own paragraph | The line stays as the last paragraph of the Licence section. |

## Context

Closes #36

The issue is a test ticket to check that the conductor starts a build session. It asks for one line at the end of README.md and no other change. The plan was recorded from the issue for topic `ticket-36-test-conductor-add-a-one-line-note-to-co`. The line goes as its own paragraph after a blank line under `## Licence`, with no new heading, because the issue says only "at the end of README.md". There is no plugin version bump, because the change is README-only.

## Changes

| Task | Files | Behaviour change | Evidence id |
| --- | --- | --- | --- |
| T1: add the footer line | `README.md` | Gains 2 lines: a blank line, then `Built with Agentville.`; no other file changes | run-1 checks 1-3 |
| Describe the PR | `.agentville/pr/pending/` | No runtime change | none |

## Architecture changes

none

No architectural change: a documentation footer only.

## Tests and evidence

| Check | Command | Result | Evidence hash |
| --- | --- | --- | --- |
| README ending | `tail -n 3 README.md` | Licence line, a blank line, then `Built with Agentville.`, with a single trailing LF | run-1 `01-tail-readme.txt` |
| Changed files | `git diff --stat` | Only README.md (1 file, 2 insertions) | run-1 `02-diff-stat.txt` |
| Shipped agent-smith tests | `python3 plugins/agentville/skills/agent-smith/scripts/test_scripts.py` | exit 0, 87 tests OK | run-1 `04-agent-smith-tests.txt` |
| Shipped skill-smith tests | `python3 plugins/agentville/skills/skill-smith/scripts/test_scripts.py` | exit 0, 84 tests OK | run-1 `05-skill-smith-tests.txt` |
| Maintainer agent-smith tests | `python3 .claude/skills/agent-smith/scripts/test_scripts.py` | exit 0, 92 tests OK | run-1 `06-maint-agent-smith-tests.txt` |
| Maintainer skill-smith tests | `python3 .claude/skills/skill-smith/scripts/test_scripts.py` | exit 0, 89 tests OK | run-1 `07-maint-skill-smith-tests.txt` |
| worker.md byte identity (2 pairs) | `git diff --no-index --quiet ...` | both exit 0 | run-1 `08`, `09` |
| Variants check | `python3 scripts/gen_agent_variants.py --check` | exit 0 | run-1 `10-variants-check.txt` |
| Plugin-security scan | `python3 .claude/skills/plugin-security/scripts/scan.py --accept ...` | critical 0, high 0, medium 0, low 17, info 5, 12 accepted; gate passes. Low PS-07 findings on README.md lines 60, 80 and 81 are also on main | run-1 `11-security-scan.txt` |

Not tested or not verifiable: rendering of the footer on GitHub's README view.

## Risks, limits and rollback

None worth noting. Revert the single commit to undo it, or `git revert -m 1 {merge-sha}` on `main` after merge.

## Reviewer checklist

- [ ] The line `Built with Agentville.` is worded as wanted.
- [ ] Placing it under `## Licence` rather than a separate footer heading is acceptable.
- [ ] No plugin version bump is needed for a README-only change.

## Review verdicts

Round 1: verdict pass (Approve).

## Evidence index

Head: {head-sha}

| Evidence | Where |
| --- | --- |
| PR description source | [PR_BODY.md](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/pending/PR_BODY.md) |
| Validator evidence | Folder `run-1` of the topic workspace (local, git-ignored), 11 checks plus `summary.md`; no `SHA256SUMS` file was written |

Open note: the build playbook ran with the agentville plugin skills (root-agent, dispatch, workspace) not loadable in its session, so its children were spawned directly and the plan was written straight to the topic folder.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
