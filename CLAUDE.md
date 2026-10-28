# Agentville steering file

Agentville is a Claude Code plugin of small, composable skills and agents for building towns of agents that behave robustly, predictably and steerably. Every agent is either standalone or a fork of a base agent (the worker by default) with a fixed format, so a parent always knows what to send and what comes back. This file says where things live, which rules never bend and how to change the repository safely; workers read it before they touch anything. The root-agent policy is imported at the end.

The plugin ships from `plugins/agentville/` and installs as one versioned unit. Its skills are namespaced `agentville:<skill>` and its agents `agentville:<agent>`. `README.md` owns the skill and agent tables and the three ways to run the plugin.

## Where things live

| Path | Holds |
| --- | --- |
| `plugins/agentville/agents/` | Shipped agents: `worker.md` (the base), `scout.md`, `validator.md`, `reviewer.md` and `pod-lead.md` (standalone, not a fork). |
| `plugins/agentville/agents/<base>-<model>-<effort>.md` | Generated variants of `worker`, `validator`, `reviewer` and `scout` (for example `worker-sonnet-high.md`), 36 in all. The only agents that set `model` and `effort`. Never hand-edited; `scripts/gen_agent_variants.py` writes them from their base, and its `--check` flag reports drift. |
| `scripts/gen_agent_variants.py` | Maintainer script that generates and checks the variants. Run `python3 scripts/gen_agent_variants.py` after any base agent edit. |
| `plugins/agentville/skills/` | Shipped skills, one folder each, each with a `SKILL.md`. |
| `plugins/agentville/skills/root-agent/SKILL.md` | Standing rules for an agent that delegates every task; this repository imports it below. |
| `plugins/agentville/settings.json` | Plugin default setting: `{"agent": "pod-lead"}`, read by Claude Code only. |
| `plugins/agentville/.claude-plugin/plugin.json` | Plugin manifest and version. |
| `.claude-plugin/marketplace.json` | Marketplace entries `agentville`, `agentville-beta` and `agentville-dev`, each pointing at the plugin folder on one branch. |
| `.claude/skills/agent-smith/`, `.claude/skills/skill-smith/` | Maintainer copies of the smiths, for building Agentville itself. |
| `.claude/skills/release-flow/` | Maintainer-only release flow; not shipped. |
| `.claude/skills/plugin-security/` | Maintainer-only security scan of the repository's refs, history and plugin components; not shipped. Run it by hand when you want a check; no push or commit waits for it. |
| `.claude/skills/report/` | Maintainer-only report skill bound to the `report` slot; not shipped. It renders the report as the GitHub PR description for the current branch and its base, with overflow pages in `.agentville/pr/<pr-number>/`, and, in a Claude Code cloud session only (`CLAUDE_CODE_REMOTE` is `true`), pushes the branch and creates or updates that one PR; anywhere else it writes `report.md` to the topic folder and pushes nothing (see Security and publishing). |
| `.claude/skills/docs-site/` | Maintainer-only standard for the documentation site in `website/`: page layout and sidebar, writing a page, build and audit checks, deploy and refresh; not shipped. |
| `.claude/skills/blueprint/` | Maintainer-only playbook that runs Discuss and Plan for a request, records the plan, then stops; not shipped. |
| `.claude/skills/build/` | Maintainer-only playbook that runs Execute, Validate, Review and Report from a recorded plan; not shipped. |
| `.claude/skills/conductor/` | Maintainer-only skill that makes the session that loads it (`/conductor`) the conductor: it keeps a roster of tickets, hands each to an idle `build-lead` session found with `ListAgents` by a message with an ACK, reports a blocker when none is idle, ages tickets against an SLE, takes alerts from the watchers the steering names (default `lookout`) and sets the `Review` label when an owner reports its PR; not shipped. |
| `.claude/skills/lookout/` | Maintainer-only skill that makes the session that loads it (`/lookout`) the watcher of one task source, alerting `conductor` and answering its Details requests; not shipped. |
| `.claude/agents/build-lead.md` | Maintainer-only fork of `pod-lead` that runs the `build` playbook where `pod-lead` runs `orchestrate`: it takes a ticket `conductor` hands it by message, records a plan, builds it, at Report commits, pushes its working branch and creates or updates the PR automatically, and reports the PR number to `conductor`; not shipped. |
| `agentville/`, `agentville/cli/`, `tests/`, `pyproject.toml`, `install.*` | The installer CLI (`uvx agentville install`): the `agentville` distribution and console script. `agentville/__init__.py` holds `__version__` and `agentville/__main__.py` runs `python -m agentville`; the installer code is in `agentville/cli/` (`app.py` the command, `console.py`, `files.py`, `targets/`), its tests in `tests/cli/`. Later parts of the package, such as `agentville/townhall/`, sit beside `cli/`. |
| `README.md` | Public description: install, the three ways to run it, and the skill and agent tables. |
| `website/` | Docusaurus documentation site for Claude Chat and Cowork users, with technical pages for Claude Code and the command-line installer; not shipped with the plugin. |
| `.github/workflows/docs.yml` | Builds `website/` and deploys it to GitHub Pages. |
| `.agentville/topics/` | Agents' workspace: `<topic-id>/` holds the topic documents, which stay local and git-ignored, `<topic-id>/evidence/run-<N>/` the validator's evidence and `<topic-id>/<agent>/{artefacts,scratch}` each agent's run folders. The workspace's own `.gitignore` (`*/evidence/`, `*/*/artefacts/`, `*/*/scratch/`) keeps evidence and run folders out of commits, and the root `.gitignore` ignores everything else under `.agentville/topics/`. |
| `.agentville/pr/<pr-number>/` | Tracked PR description pages, written by `report`: `PR_BODY.md` and the detail pages a PR body links to, under `pending/` until the PR has a number. |

## Agent format

Every agent is either standalone or a fork. A standalone agent has no base and holds no core or base markers: `pod-lead` is the only one. A fork names its base in `metadata.base` (absent means `worker`, `plugins/agentville/agents/worker.md`) and copies the base's core or base-marked Constraints verbatim, which `measure.py` checks; it has its own personality, workflows and tool allow and deny lists. The format is fixed:

1. **Role:** who the agent is, in a few lines.
2. **Constraints:** the base's Constraints copied verbatim, then the agent's own rules numbered on. For a fork of the worker these are the core blocks (`<!-- core:begin ... -->` to `<!-- core:end ... -->`), then rules from 7; for a fork of a standalone base they are the base's whole Constraints between `<!-- base:begin <base> -->` and `<!-- base:end <base> -->`, then rules numbered on. A standalone agent numbers its own rules from 1.
3. **Workflows:** as many as the agent needs. Each has Input, Process and Output.
4. **Exception handler:** what the agent does when the brief is unclear, a check fails, another agent is needed, or the budget runs out.

`measure.py` gives the standalone exemption (A5, A6 and A16 only) to any agent that declares no `metadata.base` and holds no core or base marker; A3 applies to every agent, standalone or not, and passes for an agent holding `Agent` only with `--allow-agent`, so `pod-lead` and `build-lead` are measured with that flag. A fork of a standalone base is not exempt: A5 checks its base copy and A6 also accepts its base's workflow roles. Only `pod-lead` and the maintainer-only `build-lead` (a fork of `pod-lead`) may hold the `Agent` tool. `conductor` and `lookout` are maintainer-only project skills, not agents, so they hold no tools of their own and limit the session's tools by rule: `conductor` to `ListAgents` and `SendMessage` for messages, plus `mcp__github__issue_write` (the `Review` label only), and `lookout` to `ListAgents` and `SendMessage` plus the read-only GitHub issue tools.

Do:

* Keep the core blocks byte-for-byte as the worker has them. `measure.py` compares them.
* End every report with a status tag as `Skill(agentville:relay)` section 4 sets it.
* Send agent-to-agent text, including `SendMessage` follow-ups, in the shape `relay` sets.
* Return every skill and agent output, failures included, as relay section 4 XML: the six flat tags `<status>`, `<outcome>`, `<claims>`, `<artefacts>`, `<open>`, `<deviations>`, in that order, with each field inside the tag that fits it and `none` in an empty tag. Never return a bare field block or a `user-message` field.

Don't:

* Give a child the `Agent` tool unless the user asked for it by name. Children hand back a `spawn-request:` instead.
* Write `model` or `effort` in an agent's frontmatter, except in a generated variant. `dispatch` chooses both on every spawn for every other agent.
* Hand-edit a variant or build one with `agent-smith`; `scripts/gen_agent_variants.py` writes them.
* Make a shipped agent or skill commit, push, open or merge a pull request, or mention doing so. The one exception is the maintainer-only `conductor` skill: it may tell the `build-lead` sessions it hands tickets to to open their pull request and may set the `Review` label on the ticket's issue; it never commits, pushes, opens or merges itself.

A variant is a file named `<base>-<model>-<effort>.md`, with `<base>` one of `worker`, `validator`, `reviewer` or `scout`, `<model>` one of `haiku`, `sonnet` or `opus`, and `<effort>` one of `low`, `medium` or `high`. Its `name` equals the file stem, and it is the only agent that sets `model` and `effort`, both, equal to the parts of its name; `measure.py` fails rule A2 otherwise. After any edit to a base agent, regenerate the variants with `python3 scripts/gen_agent_variants.py`.

`plugins/agentville/agents/worker.md`, `plugins/agentville/skills/agent-smith/assets/base/worker.md` and `.claude/skills/agent-smith/assets/base/worker.md` must stay byte-identical. Edit one, copy it to the others, then run the `git diff --no-index --quiet` check under Verify before you finish on each pair.

## Context injection

Slots (`workspace`, `toolbelt`, `draft`, `plan`, `report`) work like dependency injection. `Skill(agentville:context-injection)` owns the two-step use, the binding syntax and the resolution order, and each slot's default skill owns its contract. Both pairs of smiths enforce the two-step use (agent rule A18, skill rule 22); `measure.py` holds the slots in one `SLOTS` constant and owns the exemption grammar. Add a future slot to `SLOTS` in all four `measure.py` files.

This repository binds the `workspace` slot to the default, which writes to `{{ PROJECT_ROOT }}/.agentville/topics/`, and the `report` slot to the maintainer `report` project skill, which publishes the report as the PR for the current branch and its base:

* `workspace: Skill(agentville:workspace)`
* `report: Skill(report)`

This repository's `report` is a project skill in `.claude/skills/report/` that is distinct from the plugin's `agentville:report`, which the explicit binding overrides. It picks its route by surface: when the environment variable `CLAUDE_CODE_REMOTE` is `true` (Claude Code on the web), it commits and pushes the working branch at once and creates or updates the one PR for that branch and its base, without asking; in a local session, or when the variable is absent or not `true`, it writes the report to `report.md` in the topic folder and returns that path, with no commit, push or PR.

## Two pairs of smiths

Agentville holds two independent pairs of `agent-smith` and `skill-smith`. Pick by what you are building.

| Pair | Path | Installs to | Use when |
| --- | --- | --- | --- |
| Shipped | `plugins/agentville/skills/{agent-smith,skill-smith}` | Project or user scope only | Never, for Agentville itself. Users get these. |
| Maintainer | `.claude/skills/{agent-smith,skill-smith}` | Plugin (`plugins/agentville/...`) or project scope | Building or changing Agentville's own agents and skills. |

The shipped pair lets users choose a scope and nothing else; its scripts refuse any plugin folder. The maintainer pair may write into the plugin. The copies share no code and no sync, so make a fix in both when it applies to both.

## Conventions

* **Language:** British English (behaviour, artefact, organise).
* **Skills:** frontmatter holds `name`, `description` and `metadata.version` only (semver, such as `1.0.0`). Keep each `SKILL.md` at 500 lines or fewer and move long material to `references/`.
* **Rules and steps:** write Do and Don't lists, with an example where a rule needs one.
* **Paths:** write placeholders, never host paths: `{{ SKILL_ROOT }}`, `{{ PROJECT_ROOT }}` and `{{ USER_ROOT }}`.
* **Skill references:** use the full namespace, such as `Skill(agentville:relay)`. A bare name is wrong, and the old `anthropic-skills:` namespace fails validation. An external skill with no valid namespace in this repository, such as `/skill-creator`, keeps its bare name.
* **Power mode:** only `dispatch` and `intelligence-routing-model` name or invoke `Skill(agentville:power)`, which reads the mode from a `power: <mode>` steering line; no other skill or agent mentions power, and no chat command sets it.
* **Human-facing text:** follow `voice`. Text another agent reads follows `relay`. Every skill and agent returns relay §4 XML output (the six tags, fields inside them, failure in the same tags); only the root agent writes for a person, compiling relay into `voice`. skill-smith enforces this by script, and agent-smith by its judged rules.

## Working in this repository

Topic documents and agents' artefacts go to the workspace under `{{ PROJECT_ROOT }}/.agentville/topics/`, and the workspace writes nowhere else in `.agentville/`; `Skill(agentville:orchestrate)` alone records topic documents, through the `draft`, `plan` and `report` slots, and no other skill or agent names them; todos stay in the session task list. Nothing else is written to the repository for plans or todos unless the user asks. Work in the repository root, on the branch the user names; do not create or switch branches on your own.

Commit subjects follow Conventional Commits: `type(scope): summary`, imperative, with `!` before the colon for a breaking change, as in `fix(agent-smith): drop the communication core block` or `feat(dispatch)!: rename the brief fields`. In this repository, agents commit and push their work automatically, without asking; only merging a pull request waits for the owner's manual review and approval.

Bump `version` in `plugins/agentville/.claude-plugin/plugin.json` whenever you change anything that ships, which means anything under `plugins/agentville/`. Before any plugin `version` bump, ask the user with the question tool and propose the new version; ask at triage or in Plan, because `orchestrate` forbids questions from Execute on. A change to `README.md`, `CLAUDE.md` or `.claude/` does not need a bump. Bump a skill's or agent's own `metadata.version` whenever its file changes: major for a breaking contract change, minor for new behaviour, patch for a wording change. When you add, remove or rename a skill or agent, update the tables in `README.md` in the same change.

Other workers may have uncommitted edits in the tree. Read them, and touch only the paths your brief names.

## Security and publishing

This repository is public. Everything committed, in any ref, stays readable in history, so keep the tree clean before you commit, not after.

Do:

* Name a secret and where it is set, never its value: `set ACME_API_TOKEN in the CI secrets`. A names-only placeholder such as `user:pass@proxy` is allowed only to show what not to print.
* Write paths as `{{ PROJECT_ROOT }}`, `{{ SKILL_ROOT }}` and `{{ USER_ROOT }}`, and use `localhost` or `127.0.0.1` for a local address.
* Use Acme in every few-shot example: one project with applications under it (`apps/web`, `apps/api`) or documentation work (`docs/`).
* Keep exactly one `Co-Authored-By:` trailer per commit, and write Conventional Commits as set under Working in this repository.
* Keep the plugin's components least-privilege: a tool list names only what the agent needs (the one exception is `worker`, with its generated variants: it omits `tools` and inherits every tool, MCP included, with its `disallowedTools` list as the control; PS-09, accepted by design for worker files only), MCP and script sources pin a commit SHA (tags can move), marketplace entries tracking the `main`, `beta` and `release` branches are the intended release channels (PS-25, accepted by design), and the maintainer-only `release-flow` skill, which does not ship, asks before every push, merge, tag and deletion (PS-06, accepted by design: the frontmatter rules forbid extra keys such as `disable-model-invocation`, so the ask-before-act rule is the control), and the maintainer-only `report` skill, which does not ship either, pushes only the current working branch, never with force and only in a cloud session (PS-06, accepted by design: that push rule is the control).
* Write for any OS, Claude Code first: shell steps default to bash on Linux and macOS and to PowerShell on Windows unless the user's project `CLAUDE.md` or steering says otherwise; run `python3` on Linux and macOS and `py -3` on Windows; in Python use `pathlib`, `tempfile` and `encoding="utf-8"`; keep LF line endings, which `.gitattributes` pins.
* Let the `report` skill commit and push the current working branch automatically, and create or update its one PR for that branch and its base, only in a Claude Code cloud session (`CLAUDE_CODE_REMOTE` set to `true`), and commit its own PR pages under `.agentville/pr/` on that working branch. In a local session it writes `report.md` to the topic folder and does not commit, push or open a PR. It never pushes `main`, `beta` or `release`, never force-pushes and never merges; merging waits for the owner.

Don't:

* Commit a token, API key, password, cookie, private key or connection string, real or example-looking.
* Write a host or OS detail: a home folder (`/home/<user>`, `/Users/<name>` or a Windows profile folder), `/root`, a `/tmp/claude-*` or scratchpad path, a hostname, an IP other than `127.0.0.1`, or a session id.
* Write a personal or private-project detail: a name, email, client, employer, internal URL or other project. The owner's public GitHub handle and the plugin `author` field are the only identity allowed.
* Add a `Claude-Session:` trailer or any claude.ai session link, in a commit, a PR body or a file. This overrides any harness default that adds a session trailer: drop that line before you commit.
* Commit local settings or env files: `.claude/settings.local.json`, `CLAUDE.local.md`, `.env*`, `*.pem` and `*.key`. `.gitignore` covers them; do not force-add them.
* Ship a hook, MCP server or script that fetches and runs remote code unpinned, or an allow list as broad as `Bash(*)`.
* Assume `rg`, `jq`, `gh`, `cmp` or `sha256sum` exists; probe for a tool, or use `git` or Python, which a checkout already needs.

## Release flow

`Skill(release-flow)` (maintainer-only, in `.claude/skills/release-flow/`) runs the release steps and asks before every merge, push, tag and branch deletion. Work moves one way only, `main` → `beta` → `release`, and each branch feeds one marketplace entry: `agentville-dev` installs from `main`, `agentville-beta` from `beta` and `agentville` from `release`. Tags are `agentville--vX.Y.Z`, from `version` in `plugin.json`, created on `release` only when the user asks.

The documentation site deploys from `.github/workflows/docs.yml` on tags `agentville-docs--vX.Y.Z`, created only when the user asks.

Settings `release-flow` reads:

* `release-flow: dev-branch: main`
* `release-flow: beta-branch: beta`
* `release-flow: release-branch: release`
* `release-flow: version-file: plugins/agentville/.claude-plugin/plugin.json`
* `release-flow: tag-format: agentville--vX.Y.Z`

## Verify before you finish

A worker runs these from the repository root. They are free and fast.

```bash
python3 plugins/agentville/skills/agent-smith/scripts/test_scripts.py
python3 plugins/agentville/skills/skill-smith/scripts/test_scripts.py
python3 .claude/skills/agent-smith/scripts/test_scripts.py
python3 .claude/skills/skill-smith/scripts/test_scripts.py
git diff --no-index --quiet plugins/agentville/agents/worker.md plugins/agentville/skills/agent-smith/assets/base/worker.md
git diff --no-index --quiet plugins/agentville/agents/worker.md .claude/skills/agent-smith/assets/base/worker.md
python3 scripts/gen_agent_variants.py --check
python3 .claude/skills/plugin-security/scripts/scan.py --accept 'PS-06:*release-flow/SKILL.md' --accept 'PS-06:*.claude/skills/report/SKILL.md' --accept 'PS-25:*.claude-plugin/marketplace.json' --accept 'PS-09:*agents/worker.md' --accept 'PS-09:*agents/worker-*-*.md'
```

On Windows run `py -3` for `python3`; the commands are otherwise the same in PowerShell. `git diff --no-index --quiet` exits 0 when the two files are identical, so it replaces `cmp` everywhere in this file. The scan is read-only and must show no critical or high finding. The scan is optional and manual; no rule makes a push or commit wait for it.

After you edit a skill or an agent, validate the file you changed:

```bash
python3 plugins/agentville/skills/skill-smith/scripts/measure.py plugins/agentville/skills/SKILL_NAME/SKILL.md
python3 plugins/agentville/skills/agent-smith/scripts/measure.py plugins/agentville/agents/AGENT_NAME.md
python3 plugins/agentville/skills/agent-smith/scripts/measure.py --allow-agent plugins/agentville/agents/pod-lead.md
python3 .claude/skills/agent-smith/scripts/measure.py --allow-agent .claude/agents/build-lead.md
python3 .claude/skills/skill-smith/scripts/measure.py .claude/skills/SKILL_NAME/SKILL.md
```

Substitute `SKILL_NAME` and `AGENT_NAME`. The maintainer-only `build-lead` holds the `Agent` tool and forks `pod-lead`, so it is measured with the maintainer `measure.py` and `--allow-agent`, and its output must show `core: base pod-lead | identical`. `pod-lead` holds `Agent` too and is measured with the shipped `measure.py` and `--allow-agent`. A maintainer-only skill, such as `conductor` or `lookout`, is measured with the maintainer skill-smith `measure.py`. Exit code 0 means no failures; warnings are allowed.

`eval.py` in agent-smith spends model usage. Run it only when the user asks for it.

## Root-agent policy

This repository's root agent follows the `root-agent` skill, imported below. It applies to the root agent only; spawned agents follow their own agent file. The imported `root-agent` routes every request, questions included, through `orchestrate`, which owns the stages and every spawn. An installed plugin also makes `pod-lead` the main agent in Claude Code, and `pod-lead` runs every request through `orchestrate`.

@plugins/agentville/skills/root-agent/SKILL.md
