# Changes

This page lists the branch's commits against `main` and what each one changed. The diff is `git diff origin/main...HEAD`: 61 files, 687 insertions and 271 deletions at `b3ac5b2`.

| Commit | Subject | What it changed |
| --- | --- | --- |
| `ff1b6b0` | `refactor(cli): move the installer into agentville/cli` | Moves `cli.py` to `agentville/cli/app.py` and `console.py`, `files.py` and `targets/` under `agentville/cli/`; the entry point becomes `agentville.cli.app:main` in `pyproject.toml` and `agentville/__main__.py`; tests move to `tests/cli/`. `agentville/__init__.py` stays at the package root. |
| `1ad37dc` | `feat(pr-report): add the repo-level PR report skill bound to the report slot` | Adds `.claude/skills/pr-report/` with `SKILL.md`, `references/body-template.md` and `references/page-templates.md`; binds `report: Skill(pr-report)` in `CLAUDE.md`; adds the `.agentville/pr/` row; updates `README.md`. |
| `1111337` | `chore(security): accept PS-06 for the repo-level pr-report skill` | Adds `--accept 'PS-06:*pr-report/SKILL.md'` to the gate commands in `CLAUDE.md`, with the `CLAUDE.md` push rule as the control. |
| `029e707` | `feat(plugin)!: drop commit and pull-request handling from shipped agents and skills` | Removes commit, push, merge and PR handling from the shipped agents and skills under `plugins/agentville/`; renames the validator evidence field `commit:` to `revision:`; `voice` no longer covers commit or PR text; plugin 0.10.0. |
| `b3ac5b2` | `fix(agents)!: bump validator and reviewer to 3.0.0 and tidy the pr-report rules` | Bumps `validator.md` and `reviewer.md` to 3.0.0 and regenerates their variants; tidies the `pr-report` shell rule (1.0.1) and the `CLAUDE.md` push rule. |
