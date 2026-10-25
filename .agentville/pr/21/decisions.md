# Open decisions

This page lists the decisions the owner can make before or at merge. Each gives the current choice and the alternative.

## 1. State the pr-report push rule as an exception

The current choice leaves `CLAUDE.md:109` as written (`b3ac5b2`): it lets `pr-report` push the working branch and open or update its PR, but it does not say it is an exception to `CLAUDE.md:90`, which says to commit, push and merge only when the user asks. The alternative adds that clause to `CLAUDE.md:109`, so the precedence is written down. The round 2 review raised this as a note, not a blocker.

## 2. Keep orchestrate's worktree-combining step

The current choice keeps the step in `orchestrate` that combines the worktrees of parallel workers. The alternative removes it, now that shipped agents and skills no longer handle commits.

## 3. Align the smith example names

The maintainer copy `.claude/skills/skill-smith` still uses the example name `acme-pr-review`, while the shipped copy `plugins/agentville/skills/skill-smith` says `acme-code-review`. The current choice leaves the maintainer copy for a later change; the alternative aligns it now. The two copies share no code, so each fix is made by hand.
