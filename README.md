# Agentville

Agentville is a Claude Code plugin that packages ten skills for running work through agents: a workflow that routes each request, a procedure that delegates one task at a time, writing standards for what agents and people read, and two swappable slots, a workspace and a tool finder for verification checks, that each agent resolves for itself. It installs as one versioned unit, and every skill is namespaced `agentville:<skill>`.

## Install

```bash
claude plugin marketplace add minhphamdonhat/Agentville
claude plugin install agentville@agentville
```

## Skills

Each skill is invoked as `/agentville:<name>`.

| Skill | Purpose |
| --- | --- |
| `/agentville:orchestrate` | Routes every user request to a direct, clarify, fast or plan path and runs the stages that path needs. |
| `/agentville:dispatch` | Takes one delegated task through sharpening, role choice, model and effort routing, brief, spawn, report reading and failure handling. |
| `/agentville:relay` | Sets the writing standard for text another agent reads, such as briefs, hand-backs and tool results. |
| `/agentville:voice` | Sets the writing standard for Markdown a person reads, such as chat replies, reports, commit text and document files. |
| `/agentville:intelligence-routing-model` | Triages a task to the cheapest Claude tier and effort level that still succeeds. |
| `/agentville:context-injection` | Resolves a slot, such as `workspace` or `toolbelt`, to the skill that fills it in this project or for this user, and returns, for every slot in one call, the skill's id, the absolute path of its SKILL.md, the source of the binding and any fallback. It does not load or run those skills; the agent reads each one next. |
| `/agentville:workspace` | Default for the `workspace` slot: returns a run's artefacts and scratch folders under `<workspace>/<topic-id>/<agent-name>/`, using the folder the steering names or `tmp/` in the project without asking. |
| `/agentville:toolbelt` | Default for the `toolbelt` slot: discovers which verification tools are present for the db, api or ui checks a task needs, from the tools the steering or the request names, then a database client, an HTTP client or a headless browser the OS already provides. Discovery only; it probes no network. |
| `/agentville:skill-smith` | Creates, improves or converts a Claude skill from a template, then validates it and installs it to project or user scope. |
| `/agentville:agent-smith` | Compiles a Claude Code agent as a fork of the base worker, then validates it, evals it against the worker and installs it to project or user scope. |

## Agents

Each agent reads its role from a `<role>ROLE</role>` tag on the first line of the brief.

| Agent | Purpose |
| --- | --- |
| `agentville:worker` | Serves the worker, validator and reviewer roles: implements, explores and drafts, runs independent checks, or reviews a diff. Its scout workflow is local-only; `dispatch` sends web research to `agentville:scout`. |
| `agentville:scout` | Serves the scout role: researches external questions with web search and fetch only, and holds no file or shell tool. |
| `agentville:validator` | Serves the validator role: runs targeted independent checks against a running system or built artefact with the tools the project's steering names, finds its tools through the `toolbelt` slot, maps each requirement to its checks, writes hashed raw evidence to the artefacts folder of the `workspace` slot, and never edits product code. `dispatch` does not spawn it yet and still sends this role to `agentville:worker`. |
| `agentville:reviewer` | Serves the reviewer role: reads a diff and the validator's sealed evidence (files listed in its `SHA256SUMS`) against the plan, checks that the validator recorded the slots the steering binds, and returns a pass, pass-with-notes, needs-changes or blocked verdict with file and line findings, read-only. `dispatch` does not spawn it yet and still sends this role to `agentville:worker`. |

## Rules

The standing rules for the root agent ship in `rules/root-agent.md`.

## Context injection

Two jobs every agent needs, a place to write its files and a set of check tools, are slots rather than fixed rules. Agentville refers to each slot by its contract, and each agent uses its slots for itself on every run in two steps. Step 1: it calls `context-injection` once with every slot the task needs, which returns where each resolved skill lives: its id, the absolute path of its SKILL.md, the source and any fallback. Step 2: it reads each resolved skill (by id, or by path when it cannot be loaded by id) and follows it to resolve the artefacts directory or the tools. An agent never calls a slot's default skill directly, and both smiths fail an agent or skill that does. The plugin ships a default skill for each slot, and a project or user swaps in their own by binding the slot in their steering.

A binding is one line, `<slot>: Skill(<namespace>:<name>)`, in a rules file or `CLAUDE.md`, optionally under a `## Context injection` heading. The first match wins, in this order: project rules, project `CLAUDE.md`, a project skill named after the slot, user rules, user `CLAUDE.md`, a user skill named after the slot, then the plugin default `agentville:<slot>`. A bound skill that cannot be found falls back to the default, and the agent reports the fallback. Each agent records what it resolved as `<slot>: <skill> (<source>)`, so a reviewer can check it against the steering.

For example, to have every Agentville agent use your own QA tools, put this line in your project's `CLAUDE.md`:

```markdown
## Context injection

toolbelt: Skill(acme:qa-tools)
```

With no binding, the default `workspace` uses the folder your steering names, else `tmp/` in the project, and says so in its report. The default `toolbelt` only discovers the tools that are present; bind your own skill when your checks need a specific database, HTTP or browser automation tool.

## How they fit

`orchestrate` decides how much process a request deserves and runs its stages. It sends every delegated piece of work through `dispatch`, one spawn at a time.

`dispatch` writes each brief to the `relay` standard and picks the model and effort with `intelligence-routing-model`.

`dispatch` spawns `agentville:worker` for the worker, validator and reviewer roles and `agentville:scout` for the scout role, naming the role in a `<role>` tag on the brief's first line. It falls back to the built-in `general-purpose` agent only when those agent types are unavailable, and records the fallback.

`skill-smith` stands alone. `agent-smith` compiles new agents as forks of `worker`.

## External dependencies

`skill-smith` calls `/skill-creator` for evals and description tuning, so install that skill alongside it if you want `skill-smith` to test what it drafts. Its helper scripts need `python3`.

Both smiths install only to project scope (`.claude/` in the project) or user scope (`.claude/` in the home folder). They refuse any plugin folder, Agentville included, and the helper scripts enforce that.
