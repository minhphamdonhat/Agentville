Adds the centred wordmark above the README title and corrects the workspace tree line that called topic documents tracked. This is a new PR; the earlier PR for this branch is merged.

Verdict: Pending review. Blocking items: 0. Decisions needed: 0.

## Decisions needed

none

## Context

The README had no wordmark, and its `.agentville/topics/` tree line described topic documents as tracked although `.gitignore:25` ignores them. This PR fixes both. The skill table (15 skills) and the agent table (5 agents plus 36 variants) were checked against the folders and needed no change. No plugin file changed, so there is no version bump.

## Changes

| Task | Files | Behaviour change | Evidence id |
| --- | --- | --- | --- |
| Add wordmark and fix tree line (`9e6ccc9`) | `README.md`, `website/static/img/wordmark.png` (referenced, 480px) | README shows the centred wordmark above the H1; the topics tree line says topic documents are ignored. No runtime change. | CHK-1 |

## Architecture changes

none

## Tests and evidence

| Check | Command | Result | Evidence hash |
| --- | --- | --- | --- |
| Pre-publish gate (worker-run) | `python3 .claude/skills/plugin-security/scripts/scan.py --fail-on medium` with the accepted findings from `CLAUDE.md` | exit 0 | none |

Not tested or not verifiable: the rendered README on GitHub. Validate and Review were skipped because the change is README-only (4 insertions, 2 deletions) and reversible.

## Risks, limits and rollback

Documentation only; the wordmark image must stay at `website/static/img/wordmark.png`. Roll back with `git revert -m 1 {merge-sha}` on `main`.

## Reviewer checklist

- [ ] The wordmark looks right above the H1 at 480px, centred.
- [ ] The reworded `.agentville/topics/` tree line reads accurately.
- [ ] Skipping Validate and Review is acceptable for a README-only change.

## Review verdicts

Pending: no review ran; the change was judged README-only and reversible.

## Evidence index

Head: {head-sha}

| Evidence | Where |
| --- | --- |
| Pre-publish gate | Worker-run, exit 0; no evidence folder was recorded |

🤖 Generated with [Claude Code](https://claude.com/claude-code)
