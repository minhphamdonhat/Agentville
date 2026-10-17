# Agentville steering file

**tl;dr:** Agentville is a Claude Code plugin of small, composable utilities for building towns of agents that behave robustly, predictably and steerably. Every agent is a fork of one base worker with a fixed format, so a parent always knows what to send and what comes back. This file tells humans and agents where things live, which rules never bend, and how to change the repository safely. Read it before you touch anything. The root-agent policy is imported at the end of this file.

## What Agentville is

Agentville is to agent towns what Tailwind is to CSS. Each skill and agent does one job and composes with the others, so people assemble a town from parts instead of writing every agent from scratch. The goal is near-100% alignment across a swarm: because every agent has the same shape and the same report format, a parent can predict a child's behaviour without reading its file.

The plugin ships from `plugins/agentville/` and installs as one versioned unit. Its skills are namespaced `agentville:<skill>`.

## Where things live

| Path | Holds |
| --- | --- |
| `plugins/agentville/agents/` | Shipped agents: `worker.md` (the base) and `scout.md` (web research only). |
| `plugins/agentville/skills/` | Shipped skills, one folder each, each with a `SKILL.md`. |
| `plugins/agentville/rules/root-agent.md` | Standing policy for the root agent. |
| `plugins/agentville/.claude-plugin/plugin.json` | Plugin manifest and version. |
| `.claude-plugin/marketplace.json` | Marketplace entry that points at the plugin folder. |
| `.claude/skills/agent-smith/`, `.claude/skills/skill-smith/` | Maintainer copies of the smiths, for building Agentville itself. |
| `README.md` | Public description: install steps, skill and agent tables. |

The shipped skills are:

* `orchestrate` routes every request to a direct, clarify, fast or plan path and runs the stages that path needs.
* `dispatch` takes one delegated task through to one spawn and reads the report.
* `relay` is the writing standard for text another agent reads.
* `voice` is the writing standard for text a person reads.
* `intelligence-routing-model` picks the cheapest model and effort that still succeeds.
* `toolbelt` finds the verification tools a run can use, asks once for install approval and falls back to OS defaults.
* `skill-smith` creates, improves and converts skills.
* `agent-smith` compiles agents as forks of the base worker.

The shipped agents are `worker` (worker, validator and reviewer roles) and `scout` (scout role, web search and fetch only).

## Agent format

Every agent is a fork of `plugins/agentville/agents/worker.md`, with its own personality, workflows and tool allow and deny lists. The format is fixed:

1. **Role:** who the agent is, in a few lines.
2. **Constraints:** the core blocks (`<!-- core:begin ... -->` to `<!-- core:end ... -->`) copied verbatim from the worker, then the agent's own rules numbered from 7.
3. **Workflows:** as many as the agent needs. Each has Input, Process and Output.
4. **Exception handler:** what the agent does when the brief is unclear, a check fails, another agent is needed, or the budget runs out.

Do:

* Keep the core blocks byte-for-byte as the worker has them. `measure.py` compares them.
* End every report with one status from the shared set: `completed`, `partial`, `needs-input`, `blocked` or `failed`. A `needs-input` report begins its open section with `missing:`.
* Send agent-to-agent text, including `SendMessage` follow-ups, in the shape the `relay` skill sets.

Don't:

* Give a child the `Agent` tool unless the user asked for it by name. Children hand back a `spawn-request:` instead.
* Write `model` or `effort` in an agent's frontmatter. `dispatch` chooses both on every spawn.

`plugins/agentville/agents/worker.md`, `plugins/agentville/skills/agent-smith/assets/base/worker.md` and `.claude/skills/agent-smith/assets/base/worker.md` must stay byte-identical. Edit one, copy it to the others, then run `cmp` on each pair.

## Two pairs of smiths

Agentville holds two independent pairs of `agent-smith` and `skill-smith`. Pick by what you are building.

| Pair | Path | Installs to | Use when |
| --- | --- | --- | --- |
| Shipped | `plugins/agentville/skills/{agent-smith,skill-smith}` | Project or user scope only | Never, for Agentville itself. Users get these. |
| Maintainer | `.claude/skills/{agent-smith,skill-smith}` | Plugin (`plugins/agentville/...`) or project scope | Building or changing Agentville's own agents and skills. |

The shipped pair lets users choose a scope and nothing else. Users never pick a directory, and the scripts refuse any plugin folder. The maintainer pair may write into the plugin. The copies share no code and no sync, so a fix to one does not reach the other; make the change in both when it applies to both.

## Conventions

* **Language:** British English (behaviour, artefact, organise).
* **Skills:** frontmatter holds `name` and `description` only. Keep each `SKILL.md` at 500 lines or fewer and move long material to `references/`.
* **Rules and steps:** write Do and Don't lists, with an example where a rule needs one.
* **Paths:** write placeholders, never host paths: `{{ SKILL_ROOT }}`, `{{ PROJECT_ROOT }}` and `{{ USER_ROOT }}`.
* **Skill references:** use the full namespace, such as `Skill(agentville:relay)`. A bare name is wrong, and the old `anthropic-skills:` namespace fails validation.
* **Human-facing text:** follow `voice`. Text another agent reads follows `relay`.

## Working in this repository

Plans, todos and evidence live in the chat and in the session task list. Write nothing to the repository for them unless the user asks. Work in the repository root, on the branch the user names; do not create or switch branches on your own.

Commit subjects are imperative, with an optional `area:` prefix, as in `agent-smith: drop the communication core block`. Commit, push and merge only when the user asks.

Bump `version` in `plugins/agentville/.claude-plugin/plugin.json` whenever you change anything that ships, which means anything under `plugins/agentville/`. A change to `README.md`, `CLAUDE.md` or `.claude/` does not need a bump. When you add, remove or rename a skill or agent, update the tables in `README.md` in the same change.

Other workers may have uncommitted edits in the tree. Read them, and touch only the paths your brief names.

## Verify before you finish

Run these from the repository root. These are free and fast.

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

The standing rules for the root agent are in `plugins/agentville/rules/root-agent.md` and apply to the root agent only, not to spawned agents. Children do not hold the root agent's tool list and follow their own agent file instead.

@plugins/agentville/rules/root-agent.md
