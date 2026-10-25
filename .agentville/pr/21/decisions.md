# Decisions

This page records the three decisions raised on this PR. The owner has settled all three; none is open.

## 1. Commit and push rule (settled)

The round 2 review noted that the `pr-report` push rule did not say it was an exception to the `CLAUDE.md` rule to commit, push and merge only when the user asks. The owner settled it: "commit and push automatically for this repository. Only merge awaits my manuall approval & review." `CLAUDE.md:93` now says that agents commit and push their work automatically in this repository, and only merging a pull request waits for the owner's manual review and approval. The `pr-report` rule at `CLAUDE.md:112` matches it: it pushes the current working branch after the pre-publish gate, never pushes `main`, `beta` or `release`, never force-pushes and never merges. No exception clause is needed (`0769ea1`).

## 2. Keep orchestrate's worktree-combining step (settled)

The owner answered yes: the step in `orchestrate` that combines the worktrees of parallel workers stays as it is. Nothing changed.

## 3. Align the smith example names (settled)

The owner answered yes. The maintainer copy `.claude/skills/skill-smith` now uses `acme-code-review` and "a skill that reviews code changes", as the shipped copy `plugins/agentville/skills/skill-smith` does, in `SKILL.md`, its workflow references and `scripts/test_scripts.py`; its version moves to 2.1.1 (`16d3b35`).
