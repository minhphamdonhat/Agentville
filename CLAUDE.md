# Agentville steering file

Agentville is a Claude Code plugin of small, composable skills and agents for building towns of agents that behave robustly, predictably and steerably. Every agent except `pod-lead` is a fork of one base worker with a fixed format, so a parent always knows what to send and what comes back. This file says where things live, which rules never bend and how to change the repository safely; workers read it before they touch anything. The root-agent policy is imported at the end.

The plugin ships from `plugins/agentville/` and installs as one versioned unit. Its skills are namespaced `agentville:<skill>` and its agents `agentville:<agent>`. `README.md` owns the skill and agent tables and the three ways to run the plugin.

## Where things live

| Path | Holds |
| --- | --- |
| `plugins/agentville/agents/` | Shipped agents: `worker.md` (the base), `scout.md`, `validator.md`, `reviewer.md` and `pod-lead.md` (standalone, not a worker fork). |
| `plugins/agentville/skills/` | Shipped skills, one folder each, each with a `SKILL.md`. |
| `plugins/agentville/skills/root-agent/SKILL.md` | Standing rules for an agent that delegates every task; this repository imports it below. |
| `plugins/agentville/settings.json` | Plugin default setting: `{"agent": "pod-lead"}`, read by Claude Code only. |
| `plugins/agentville/.claude-plugin/plugin.json` | Plugin manifest and version. |
| `.claude-plugin/marketplace.json` | Marketplace entries `agentville`, `agentville-beta` and `agentville-dev`, each pointing at the plugin folder on one branch. |
| `.claude/skills/agent-smith/`, `.claude/skills/skill-smith/` | Maintainer copies of the smiths, for building Agentville itself. |
| `README.md` | Public description: install, the three ways to run it, and the skill and agent tables. |
| `tmp/` | Agents' workspace, git-ignored: `tmp/<topic-id>/<agent>/{artefacts,scratch}`. |

## Agent format

Every agent except `pod-lead` is a fork of `plugins/agentville/agents/worker.md`, with its own personality, workflows and tool allow and deny lists. The format is fixed:

1. **Role:** who the agent is, in a few lines.
2. **Constraints:** the core blocks (`<!-- core:begin ... -->` to `<!-- core:end ... -->`) copied verbatim from the worker, then the agent's own rules numbered from 7.
3. **Workflows:** as many as the agent needs. Each has Input, Process and Output.
4. **Exception handler:** what the agent does when the brief is unclear, a check fails, another agent is needed, or the budget runs out.

`pod-lead` holds no core blocks, numbers its own rules from 1 and may hold the `Agent` tool; `measure.py` exempts it from A3, A5, A6 and A16 only.

Do:

* Keep the core blocks byte-for-byte as the worker has them. `measure.py` compares them.
* End every report with a status tag as `Skill(agentville:relay)` section 4 sets it.
* Send agent-to-agent text, including `SendMessage` follow-ups, in the shape `relay` sets.

Don't:

* Give a child the `Agent` tool unless the user asked for it by name. Children hand back a `spawn-request:` instead.
* Write `model` or `effort` in an agent's frontmatter. `dispatch` chooses both on every spawn.

`plugins/agentville/agents/worker.md`, `plugins/agentville/skills/agent-smith/assets/base/worker.md` and `.claude/skills/agent-smith/assets/base/worker.md` must stay byte-identical. Edit one, copy it to the others, then run `cmp` on each pair.

## Context injection

Slots (`workspace`, `toolbelt`, `draft`, `plan`, `report`) work like dependency injection. `Skill(agentville:context-injection)` owns the two-step use, the binding syntax and the resolution order, and each slot's default skill owns its contract. Both pairs of smiths enforce the two-step use (agent rule A18, skill rule 22); `measure.py` holds the slots in one `SLOTS` constant and owns the exemption grammar. Add a future slot to `SLOTS` in all four `measure.py` files.

This repository binds the `workspace` slot to the default and names the folder the default reads:

* `workspace: Skill(agentville:workspace)`
* `workspace-folder: {{ PROJECT_ROOT }}/tmp/`

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
* **Skill references:** use the full namespace, such as `Skill(agentville:relay)`. A bare name is wrong, and the old `anthropic-skills:` namespace fails validation.
* **Human-facing text:** follow `voice`. Text another agent reads follows `relay`.

## Working in this repository

Topic documents and agents' artefacts go to the workspace under `{{ PROJECT_ROOT }}/tmp/`, written by a worker through the `draft`, `plan` and `report` slots; todos stay in the session task list. Nothing else is written to the repository for plans or todos unless the user asks. Work in the repository root, on the branch the user names; do not create or switch branches on your own.

Commit subjects follow Conventional Commits: `type(scope): summary`, imperative, with `!` before the colon for a breaking change, as in `fix(agent-smith): drop the communication core block` or `feat(dispatch)!: rename the brief fields`. Commit, push and merge only when the user asks.

Bump `version` in `plugins/agentville/.claude-plugin/plugin.json` whenever you change anything that ships, which means anything under `plugins/agentville/`. A change to `README.md`, `CLAUDE.md` or `.claude/` does not need a bump. Bump a skill's or agent's own `metadata.version` whenever its file changes: major for a breaking contract change, minor for new behaviour, patch for a wording change. When you add, remove or rename a skill or agent, update the tables in `README.md` in the same change.

Other workers may have uncommitted edits in the tree. Read them, and touch only the paths your brief names.

## Release flow

`Skill(agentville:release-flow)` runs the release steps and asks before every merge, push, tag and branch deletion. Work moves one way only, `main` → `beta` → `release`, and each branch feeds one marketplace entry: `agentville-dev` installs from `main`, `agentville-beta` from `beta` and `agentville` from `release`. Tags are `agentville--vX.Y.Z`, from `version` in `plugin.json`, created on `release` only when the user asks.

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
cmp plugins/agentville/agents/worker.md plugins/agentville/skills/agent-smith/assets/base/worker.md
cmp plugins/agentville/agents/worker.md .claude/skills/agent-smith/assets/base/worker.md
```

After you edit a skill or an agent, validate the file you changed:

```bash
python3 plugins/agentville/skills/skill-smith/scripts/measure.py plugins/agentville/skills/SKILL_NAME/SKILL.md
python3 plugins/agentville/skills/agent-smith/scripts/measure.py plugins/agentville/agents/AGENT_NAME.md
```

Substitute `SKILL_NAME` and `AGENT_NAME`. Exit code 0 means no failures; warnings are allowed. `worker.md` currently warns A9 because its examples mention `Skill(deploy-check)`, which is expected.

`eval.py` in agent-smith spends model usage. Run it only when the user asks for it.

## Root-agent policy

This repository's root agent follows the `root-agent` skill, imported below. It applies to the root agent only; spawned agents follow their own agent file. This file does not route requests through `orchestrate`, but an installed plugin makes `pod-lead` the main agent in Claude Code, and `pod-lead` runs every request through `orchestrate`.

@plugins/agentville/skills/root-agent/SKILL.md
