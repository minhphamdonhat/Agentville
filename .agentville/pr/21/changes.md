# Changes

This page lists the branch's commits against `main` and what each one changed. The diff is `git diff origin/main...HEAD`: 61 files, 687 insertions and 271 deletions at `b3ac5b2`; 67 files, 870 insertions and 271 deletions at `02caf1a`, the extra 6 files being these PR pages.

| Commit | Subject | What it changed |
| --- | --- | --- |
| `ff1b6b0` | `refactor(cli): move the installer into agentville/cli` | Moves `cli.py` to `agentville/cli/app.py` and `console.py`, `files.py` and `targets/` under `agentville/cli/`; the entry point becomes `agentville.cli.app:main` in `pyproject.toml` and `agentville/__main__.py`; tests move to `tests/cli/`. `agentville/__init__.py` stays at the package root. |
| `1ad37dc` | `feat(pr-report): add the repo-level PR report skill bound to the report slot` | Adds `.claude/skills/pr-report/` with `SKILL.md`, `references/body-template.md` and `references/page-templates.md`; binds `report: Skill(pr-report)` in `CLAUDE.md`; adds the `.agentville/pr/` row; updates `README.md`. |
| `1111337` | `chore(security): accept PS-06 for the repo-level pr-report skill` | Adds `--accept 'PS-06:*pr-report/SKILL.md'` to the gate commands in `CLAUDE.md`, with the `CLAUDE.md` push rule as the control. |
| `029e707` | `feat(plugin)!: drop commit and pull-request handling from shipped agents and skills` | Removes commit, push, merge and PR handling from the shipped agents and skills under `plugins/agentville/`; renames the validator evidence field `commit:` to `revision:`; `voice` no longer covers commit or PR text; plugin 0.10.0. |
| `b3ac5b2` | `fix(agents)!: bump validator and reviewer to 3.0.0 and tidy the pr-report rules` | Bumps `validator.md` and `reviewer.md` to 3.0.0 and regenerates their variants; tidies the `pr-report` shell rule (1.0.1) and the `CLAUDE.md` push rule. |
| `d84b17f` | `docs(pr): describe the cli restructure, pr-report and commit handling change` | Adds the PR description pages. |
| `072f598` | `docs(pr): move the PR pages to .agentville/pr/21` | Moves the PR pages from `pending/` to `.agentville/pr/21/`. |
| `02caf1a` | `chore(merge): merge origin/main into feat/pr-report` | Merges `main` at `0ab7181` (PR #19, documentation site). The one conflict, in `CLAUDE.md`, keeps both sides: main's `docs-site`, `website/` and docs workflow rows, and this branch's `pr-report` and installer rows. No file under `plugins/agentville/` changed on `main`; plugin stays 0.10.0, above main's 0.9.2. |
