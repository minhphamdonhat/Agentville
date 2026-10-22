# Agentville steering file

**tl;dr:** Agentville is a Claude Code plugin of small, composable utilities for building towns of agents that behave robustly, predictably and steerably. Every agent is a fork of one base worker with a fixed format, so a parent always knows what to send and what comes back. This file tells humans and agents where things live, which rules never bend, and how to change the repository safely. Read it before you touch anything. The root-agent policy is imported at the end of this file.

## What Agentville is

Agentville is to agent towns what Tailwind is to CSS. Each skill and agent does one job and composes with the others, so people assemble a town from parts instead of writing every agent from scratch. The goal is near-100% alignment across a swarm: because every agent has the same shape and the same report format, a parent can predict a child's behaviour without reading its file.

The plugin ships from `plugins/agentville/` and installs as one versioned unit. Its skills are namespaced `agentville:<skill>`.

## Where things live

| Path | Holds |
| --- | --- |
| `plugins/agentville/agents/` | Shipped agents: `worker.md` (the base), `scout.md` (web research only), `validator.md` (independent checks with sealed evidence), `reviewer.md` (read-only diff review) and `pod-lead.md` (standalone orchestrator of a pod's agents, not a worker fork). |
| `plugins/agentville/skills/` | Shipped skills, one folder each, each with a `SKILL.md`. |
| `plugins/agentville/rules/root-agent.md` | Standing policy for the root agent. |
| `plugins/agentville/.claude-plugin/plugin.json` | Plugin manifest and version. |
| `.claude-plugin/marketplace.json` | Marketplace entry that points at the plugin folder. |
| `.claude/skills/agent-smith/`, `.claude/skills/skill-smith/` | Maintainer copies of the smiths, for building Agentville itself. |
| `README.md` | Public description: install steps, skill and agent tables. |
| `tmp/` | Agents' workspace, git-ignored: `tmp/<topic-id>/<agent>/{artefacts,scratch}`. |

The shipped skills are:

* `orchestrate` is a sample workflow: it triages each request and runs the stages it needs from Discuss, Plan, Execute, Validate, Review and Report, sending all stage work through `dispatch`. It is opt-in and nothing in Agentville loads it by default. Users who want it add this line to their own `CLAUDE.md` themselves: "Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it."
* `dispatch` takes one delegated task through to one spawn and reads the report.
* `relay` is the writing standard for text another agent reads.
* `voice` is the writing standard for text a person reads.
* `intelligence-routing-model` picks the cheapest model and effort that still succeeds.
* `context-injection` resolves a slot (`workspace`, `toolbelt` or any named slot) to the skill that fills it for this run. One call takes a list of slots and returns, per slot, the resolved skill id, the absolute path of its SKILL.md, the binding's source and any fallback. It does not load or run the resolved skills.
* `workspace` is the default for the `workspace` slot: it returns the topic folder and a run's artefacts and scratch folders and never asks.
* `draft`, `plan` and `report` are the defaults for the slots of the same names: they record a topic's draft, plan and report as `draft.md`, `plan.md` and `report.md` in the topic folder, writing with `Write` and `Edit` only. Each also has a read-only `locate` mode that returns the path or `none` and writes nothing. They record what they are given and decide nothing.
* `toolbelt` is the default for the `toolbelt` slot: it discovers which tools are present for the checks a task needs, from the steering's and the request's tools first, and reports OS-provided tools for any check type (db, api, ui, office, docs, build, pipeline, infra) when nothing names one. It is discovery only and says nothing about how a tool is used.
* `release-flow` runs the one-way release flow of any repository: starts working branches, promotes development to beta and beta to release after checks, and tags only on request. It depends on no other Agentville skill or slot.
* `skill-smith` creates, improves and converts skills.
* `agent-smith` compiles agents as forks of the base worker.

The shipped agents are `worker` (the base, which also serves the worker, validator and reviewer roles until `dispatch` spawns the next two), `scout` (scout role, web search and fetch only), `validator` (validator role, writes hashed evidence to the resolved `workspace` and finds its tools through the `toolbelt` slot, resolved in two steps), `reviewer` (reviewer role, read-only, locates the evidence through the `workspace` slot and checks the validator's slot records against the steering) and `pod-lead` (the standalone orchestrator of a pod's agents, not a worker fork, which routes every request through `orchestrate` and holds no edit, search or shell tool).

## Agent format

Every agent except `pod-lead` is a fork of `plugins/agentville/agents/worker.md`, with its own personality, workflows and tool allow and deny lists. The format is fixed:

1. **Role:** who the agent is, in a few lines.
2. **Constraints:** the core blocks (`<!-- core:begin ... -->` to `<!-- core:end ... -->`) copied verbatim from the worker, then the agent's own rules numbered from 7.
3. **Workflows:** as many as the agent needs. Each has Input, Process and Output.
4. **Exception handler:** what the agent does when the brief is unclear, a check fails, another agent is needed, or the budget runs out.

`pod-lead` is the standalone orchestrator of a pod's agents, not a worker fork: it holds no core blocks, numbers its own rules from 1 and may hold the `Agent` tool. `measure.py` exempts the agent named `pod-lead` from A3, A5, A6 and A16 only; every other check still runs.

Do:

* Keep the core blocks byte-for-byte as the worker has them. `measure.py` compares them.
* End every report with one status from the shared set: `completed`, `partial`, `needs-input`, `blocked` or `failed`. A `needs-input` report begins its open section with `missing:`.
* Send agent-to-agent text, including `SendMessage` follow-ups, in the shape the `relay` skill sets.

Don't:

* Give a child the `Agent` tool unless the user asked for it by name. Children hand back a `spawn-request:` instead.
* Write `model` or `effort` in an agent's frontmatter. `dispatch` chooses both on every spawn.

`plugins/agentville/agents/worker.md`, `plugins/agentville/skills/agent-smith/assets/base/worker.md` and `.claude/skills/agent-smith/assets/base/worker.md` must stay byte-identical. Edit one, copy it to the others, then run `cmp` on each pair.

## Context injection

Context injection works like dependency injection. Agentville refers to a slot by its contract, and each agent uses its slots in two steps. Step 1: it calls `Skill(agentville:context-injection)` once with every slot the task needs (`slots: workspace, toolbelt`), which returns where each resolved skill lives: its id and the absolute path of its SKILL.md, plus the source and any fallback. Step 2: it reads each resolved skill, by loading it with the `Skill` tool by the returned id or, when it is not loadable by id, with `Read` on the returned path, and follows it to resolve the artefacts directory, the tools, or where and how a topic document is written. An agent never calls a slot's default skill (`Skill(agentville:toolbelt)`) without step 1. It loads `context-injection` once per context and reuses the records, and each resolved skill it has read, while they are still in its context; it loads or reads them again only after compaction or when the earlier load has faded. An agent never resolves a slot for another agent, and briefs carry no bindings, only the topic-id, any steering locations as context and, for a draft, plan or report, the content to record. The plugin ships a default skill for each slot.

| Slot | Contract | Default |
| --- | --- | --- |
| `workspace` | In: topic-id, agent-name. Out: topic path, artefacts path, scratch path, cleanup rule, git-ignore status. | `agentville:workspace`: the folder the steering names, else `{{ PROJECT_ROOT }}/tmp/`, never asking. |
| `toolbelt` | In: needs, mode, workspace, optional brief-tools. Out: surface, os, tools with name, presence, version and source, notes, blockers. Discovery only. | `agentville:toolbelt`: named tools, then tools the OS provides; no network probes. |
| `draft` | In: topic-id, content (not needed for `locate`), mode (`create`, `append`, `update` or `locate`; default `append`), optional sections and topic-folder (default: the workspace topic folder when given, else `{{ PROJECT_ROOT }}/tmp/<topic-id>`). Out: file (`none` for `locate` with no draft), mode, round, sections, kept; `locate` returns the path or `none` and writes nothing. | `agentville:draft`: `<topic-folder>/draft.md`, one `## Round N` per Discuss round, appended. |
| `plan` | In: topic-id, content (not needed for `locate`), approval (a record only; default `not-required` on create, else unchanged), mode (`create`, `append`, `update` or `locate`), optional sections and topic-folder (default as for `draft`). Out: file (`none` for `locate` with no plan), mode, sections, tasks, approval; `locate` returns the path or `none` and writes nothing. | `agentville:plan`: `<topic-folder>/plan.md` with Goal, Tasks (done criteria; progress only when the content gives it) and Approval. |
| `report` | In: topic-id, content (not needed for `locate`), mode (`create`, `append`, `update` or `locate`), optional sections and topic-folder (default as for `draft`). Out: file (`none` for `locate` with no report), mode, sections, evidence; `locate` returns the path or `none` and writes nothing. | `agentville:report`: `<topic-folder>/report.md` with Outcome, Delivered, Evidence, Review, Extra work, Out of scope and Open items. |

Resolution order, first match wins:

1. Project rules, `{{ PROJECT_ROOT }}/.claude/rules/*.md`.
2. Project `CLAUDE.md`, `{{ PROJECT_ROOT }}/CLAUDE.md` then `{{ PROJECT_ROOT }}/.claude/CLAUDE.md`, each with the files it imports on an `@<path>` line, one level deep.
3. A project skill named exactly the slot.
4. User rules, `{{ USER_ROOT }}/.claude/rules/*.md`.
5. User `CLAUDE.md`, `{{ USER_ROOT }}/.claude/CLAUDE.md`, with its one-level `@<path>` imports.
6. A user skill named exactly the slot.
7. The plugin default, `Skill(agentville:<slot>)`.

A binding is one line, `<slot>: Skill(<namespace>:<name>)`, anywhere in a rules file or `CLAUDE.md` or under a `## Context injection` heading. When the bound or named skill cannot be found, `context-injection` falls back to the plugin default and the agent reports the fallback and its reason in `<deviations>`. Every agent records each slot it resolved as a claim `<slot>: <skill> (<source>)`, such as `toolbelt: acme:qa-tools (project-rules)`.

How a tool is used is set by the agent's own file or by the steering, never by the toolbelt.

Both pairs of smiths enforce the two-step use. `measure.py` holds the injectable slots in one `SLOTS` constant (`workspace`, `toolbelt`, `draft`, `plan`, `report`). An agent (rule A18) or a skill (rule 22) that uses a slot must name `Skill(agentville:context-injection)` and must not call `Skill(agentville:<slot>)` directly (nor as `Skill(<slot>)`, `/agentville:<slot>` or a bare `agentville:<slot>`), except where the text reads as a description of the default (the words "the plugin default" right before it, or `(plugin-default)` right after it, and no imperative verb such as call, load, run, invoke or use right before the call) or it is the skill id of a slot record `<slot>: <namespace>:<name> (<source>)` with a known source. A skill scans its `references/` files too. A skill named after a slot is treated as a slot implementation, so it and `context-injection` are exempt. Add a future slot to `SLOTS` in all four `measure.py` files.

This repository binds the `workspace` slot to the default and names the folder the default reads:

* `workspace: Skill(agentville:workspace)`
* `workspace-folder: {{ PROJECT_ROOT }}/tmp/`

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

Drafts, plans and reports go to the topic folder under `{{ PROJECT_ROOT }}/tmp/`, as `tmp/<topic-id>/{draft,plan,report}.md`, written by a worker through the `draft`, `plan` and `report` slots; todos stay in the session task list. Agents' artefacts go to the same workspace, laid out as `tmp/<topic-id>/<agent>/{artefacts,scratch}`. The workspace is git-ignored, and nothing else is written to the repository for plans or todos unless the user asks. Work in the repository root, on the branch the user names; do not create or switch branches on your own.

Commit subjects follow Conventional Commits: `type(scope): summary`, imperative, with `!` before the colon for a breaking change, as in `fix(agent-smith): drop the communication core block` or `feat(dispatch)!: rename the brief fields`. Commit, push and merge only when the user asks.

Bump `version` in `plugins/agentville/.claude-plugin/plugin.json` whenever you change anything that ships, which means anything under `plugins/agentville/`. A change to `README.md`, `CLAUDE.md` or `.claude/` does not need a bump. When you add, remove or rename a skill or agent, update the tables in `README.md` in the same change.

Other workers may have uncommitted edits in the tree. Read them, and touch only the paths your brief names.

## Release flow

Agentville ships from three long-lived branches, and work moves one way only: `main` → `beta` → `release`.

* `main` is the development branch. Working branches start from `main` and merge back into it; `Skill(agentville:release-flow)` sets how they are named.
* `beta` takes `main` once the checks pass; the `agentville-beta` marketplace entry installs from it.
* `release` takes `beta` only, never `main` directly; the `agentville` marketplace entry installs from it.
* `Skill(agentville:release-flow)` runs each step and asks before every merge, push, tag and branch deletion.
* Tags (`agentville--vX.Y.Z`, from `version` in `plugins/agentville/.claude-plugin/plugin.json`) are created on `release` only when the user asks.

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

The standing rules for the root agent are in `plugins/agentville/rules/root-agent.md` and apply to the root agent only, not to spawned agents. Children do not hold the root agent's tool list and follow their own agent file instead. The policy does not route requests through `orchestrate`; that workflow applies only where a user's own `CLAUDE.md` opts in to it.

@plugins/agentville/rules/root-agent.md
