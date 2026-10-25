This PR moves the installer into `agentville/cli/`, adds the maintainer-only `pr-report` skill bound to the `report` slot, and drops commit and pull-request handling from the shipped agents and skills. Plugin 0.10.0 is a breaking release: the validator evidence field `commit:` is now `revision:`, validator and reviewer move to 3.0.0, and `voice` no longer covers commit or PR text.

Verdict: Ready to merge. Blocking items: 0. Decisions needed: 0.

## Decisions needed

none. The owner settled all three: commit and push automatically, merge waits for the owner (`CLAUDE.md:93`, `0769ea1`); keep orchestrate's worktree step; align the maintainer `skill-smith` example (`16d3b35`). See the [decisions page](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/21/decisions.md).

## Context

The installer package sat flat at the root of `agentville/`, which leaves no room for the later Townhall move into `agentville/townhall/`; this PR puts it under `agentville/cli/`. Agentville also had no way to publish a topic's report as a PR description, so `pr-report` fills the `report` slot for this repository and pushes its working branch and opens or updates its PR on its own. By the owner's decision, shipped agents and skills no longer handle commits or PRs. PS-06 is accepted for `pr-report`, with the `CLAUDE.md` push rule as the control. When PR #20 syncs from `main`, it moves to plugin 0.11.0.

## Changes

| Task | Files | Behaviour change | Evidence id |
| --- | --- | --- | --- |
| Restructure the installer (`ff1b6b0`) | `agentville/cli/`, `agentville/__main__.py`, `pyproject.toml`, `tests/cli/` | Entry point is `agentville.cli.app:main`; `agentville/__init__.py` stays at the package root | REQ-1 |
| Add `pr-report` (`1ad37dc`) | `.claude/skills/pr-report/`, `CLAUDE.md`, `README.md` | `report: Skill(pr-report)` binding; PRs rendered with a Verdict line and nine sections | REQ-3, REQ-5 |
| Accept PS-06 (`1111337`) | `CLAUDE.md` | Gate accepts `PS-06:*pr-report/SKILL.md` | REQ-2, REQ-3 |
| Drop commit and PR handling (`029e707`) | `plugins/agentville/agents/`, `plugins/agentville/skills/` | Shipped agents and skills no longer commit or open PRs; `commit:` renamed `revision:`; plugin 0.10.0 | REQ-4 |
| Bump validator and reviewer (`b3ac5b2`) | `validator.md`, `reviewer.md`, variants, `pr-report` 1.0.1, `CLAUDE.md` | Validator and reviewer at 3.0.0; push rule tidied | REQ-4 |
| Merge `main` at `0ab7181` (`02caf1a`) and at `8d5d4a3` (`17df5f6`) | `CLAUDE.md`, installers, `website/` | One `CLAUDE.md` conflict, both sides kept; second merge clean; no shipped file changed | worker checks |
| Commit and push rule (`0769ea1`) | `CLAUDE.md` | Agents commit and push automatically; only merging waits for the owner | worker checks |
| Align smith example (`16d3b35`) | `.claude/skills/skill-smith/` | Maintainer example is `acme-code-review`, as shipped; 2.1.1 | worker checks |

https://github.com/minhphamdonhat/Agentville/blob/0769ea192e7a305cebe840f08d90d316ef222e46/CLAUDE.md#L93-L93

https://github.com/minhphamdonhat/Agentville/blob/b3ac5b27805783e03c3e68c76ed1423e5bb49aa9/.claude/skills/pr-report/SKILL.md#L14-L18

Every commit is on the [changes page](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/21/changes.md).

## Architecture changes

```mermaid
flowchart LR
  accTitle: Installer package and report slot after this PR
  accDescr: The installer moves from the agentville package root into agentville/cli, while agentville/__init__.py stays at the root. The report slot binds to the repo-level pr-report skill, which pushes the working branch and writes the GitHub PR.
  root["agentville/__init__.py"] --> cli["agentville/cli/ (app, console, files, targets)"]
  slot["report slot"] --> pr["pr-report skill"]
  pr -->|"push working branch"| gh["GitHub PR"]
```

The installer modules now live in `agentville/cli/`, and `agentville/__init__.py` stays at the package root. The `report` slot binds to the repository-level `pr-report` skill, which pushes the working branch and writes the GitHub PR. See the [architecture page](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/21/architecture.md).

## Tests and evidence

| Check | Command | Result | Evidence hash |
| --- | --- | --- | --- |
| REQ-1 installer under `agentville/cli/` | `pytest`, help, `uv build` | 8 checks, pass | `fa54bd32cbf4` |
| REQ-2 Verify block and gate | `CLAUDE.md` Verify commands, `--fail-on medium` gate, `measure.py` | 23 checks, pass | `1d5bb5355a57` |
| REQ-3 pr-report skill rules | `checks.py` docs checks | 16 checks, pass | `22792e4dd2c7` |
| REQ-4 shipped files and 3.0.0 bumps | `checks.py` docs checks | 17 checks, pass | `4f686fef290a` |
| REQ-5 pr-report content | `checks5.py`, mutated-copy negatives | 23 checks, pass | `9beb3decc2b6` |
| REQ-6 worktree and merge base | `git` checks | 5 checks, pass | `ce59992a7c76` |

92 checks pass at `b3ac5b2` (run-3). Per-check detail is on the [tests page](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/21/tests.md).

Not tested: the `townhall` Verify commands; `townhall/` is on neither this branch nor `main`. After `16d3b35` a worker re-ran the other Verify commands (exit 0), root `pytest` (38 passed), `measure.py` on the maintainer `skill-smith` (exit 0), the shipped-files `git grep` (0 hits) and the `--fail-on medium` gate (exit 0); worker checks, not sealed evidence.

## Risks, limits and rollback

`agentville/__init__.py` stays at the package root and is a likely merge point with the later Townhall move into `agentville/townhall/`. Users of the validator's `commit:` field must read `revision:`. Roll back with `git revert -m 1 {merge-sha}` on `main`; the [risks page](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/21/risks.md) lists each risk.

## Reviewer checklist

- [ ] The breaking rename of `commit:` to `revision:` is acceptable for 0.10.0.
- [ ] The `CLAUDE.md:93` rule (commit and push automatically, merge waits for you) reads as you meant it.
- [ ] Keeping `agentville/__init__.py` at the root is the right place before the Townhall move.
- [ ] The PS-06 acceptance with the `CLAUDE.md` push rule as the control is enough.

## Review verdicts

Round 1: blocked (evidence gap; validator bump too small), fixed in `b3ac5b2`. Round 2: pass-with-notes. Notes: `requirements.md` cites `CLAUDE.md:64`, not `:63`; the `pr-report` push rule did not say it is an exception to the commit and push rule (now `CLAUDE.md:112` and `CLAUDE.md:93`; settled by the owner in `0769ea1`); the `pr-report` 1.0.1 patch bump is defensible. Changes after `b3ac5b2` are not reviewed.

## Evidence index

Head: {head-sha}

| Evidence | Where |
| --- | --- |
| Settled decisions | [Decisions page](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/21/decisions.md) |
| Commits | [Changes page](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/21/changes.md) |
| Architecture | [Architecture page](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/21/architecture.md) |
| Checks and reproduction | [Tests page](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/21/tests.md) |
| Risks and rollback | [Risks page](https://github.com/minhphamdonhat/Agentville/blob/{head-sha}/.agentville/pr/21/risks.md) |
| Validator evidence | Folder `run-3` at `b3ac5b2`, `SHA256SUMS` hash `37622fd28912` |
| Post-merge worker checks | Listed under Tests and evidence; not sealed |

🤖 Generated with [Claude Code](https://claude.com/claude-code)
