# Agentville

Agentville is a Claude Code plugin that packages fourteen skills for running work through agents: a workflow that triages each request into six stages, a procedure that delegates one task at a time, writing standards for what agents and people read, and five swappable slots, a workspace, a tool finder for verification checks and the draft, plan and report documents of a topic, that each agent resolves for itself. It installs as one versioned unit, and every skill is namespaced `agentville:<skill>`.

## Install

Add the marketplace once, then install one channel:

```text
/plugin marketplace add minhphamdonhat/agentville
/plugin install agentville@minhphamdo
```

| Channel | Install id | Branch |
| --- | --- | --- |
| Release | `agentville@minhphamdo` | `release` |
| Beta | `agentville-beta@minhphamdo` | `beta` |
| Development | `agentville-dev@minhphamdo` | `main` |

Install one channel at a time; all three load the same skills under `agentville:`. To switch, uninstall the one you have and install the other, for example `/plugin uninstall agentville@minhphamdo` then `/plugin install agentville-beta@minhphamdo`.

## Skills

Each skill is invoked as `/agentville:<name>`.

| Skill | Purpose |
| --- | --- |
| `/agentville:orchestrate` | Sample workflow, opt-in from your own `CLAUDE.md`. Triages each request and runs the stages it needs from Discuss, Plan, Execute, Validate, Review and Report, sending all stage work through `dispatch`. |
| `/agentville:dispatch` | Takes one delegated task through sharpening, role choice, model and effort routing, brief, spawn, report reading and failure handling. |
| `/agentville:relay` | Sets the writing standard for text another agent reads, such as briefs, hand-backs and tool results. |
| `/agentville:voice` | Sets the writing standard for Markdown a person reads, such as chat replies, reports, commit text and document files. |
| `/agentville:intelligence-routing-model` | Triages a task to the cheapest Claude tier and effort level that still succeeds. |
| `/agentville:context-injection` | Resolves a slot, such as `workspace` or `toolbelt`, to the skill that fills it in this project or for this user, and returns, for every slot in one call, the skill's id, the absolute path of its SKILL.md, the source of the binding and any fallback. It does not load or run those skills; the agent reads each one next. |
| `/agentville:workspace` | Default for the `workspace` slot: returns a run's artefacts and scratch folders under `<workspace>/<topic-id>/<agent-name>/`, using the folder the steering names or `tmp/` in the project without asking. |
| `/agentville:draft` | Default for the `draft` slot: records a topic's Discuss notes, decisions and open points in `<workspace>/<topic-id>/draft.md`, one round per section, appending without touching earlier rounds. |
| `/agentville:plan` | Default for the `plan` slot: records a topic's plan in `<workspace>/<topic-id>/plan.md`, with each task and its done criteria (and its progress when given) as the topic's task ledger, and the approval status as a record only (default `not-required`). |
| `/agentville:report` | Default for the `report` slot: records a topic's final report in `<workspace>/<topic-id>/report.md`, with what was delivered, the evidence pointers, the review result, an out-of-scope section for findings and gaps left for you to decide, and the open items. |
| `/agentville:toolbelt` | Default for the `toolbelt` slot: discovers which verification tools are present for the checks a task needs, from the tools the steering or the request names first, and reports OS-provided tools for any check type (db, api, ui, office, docs, build, pipeline, infra) when nothing names one. Discovery only; it probes no network. |
| `/agentville:release-flow` | Runs a one-way release flow in any repository: starts nested working branches (`<type>/<short-kebab-name>`) from the development branch, promotes development to beta and beta to release after the configured checks pass, and tags a release only when asked. Every merge, push, tag and branch deletion waits for your yes. |
| `/agentville:skill-smith` | Creates, improves or converts a Claude skill from a template, then validates it and installs it to project or user scope. |
| `/agentville:agent-smith` | Compiles a Claude Code agent as a fork of the base worker, then validates it, evals it against the worker and installs it to project or user scope. |

## Agents

Each agent reads its role from a `<role>ROLE</role>` tag on the first line of the brief.

| Agent | Purpose |
| --- | --- |
| `agentville:worker` | Serves the worker, validator and reviewer roles: implements, explores and drafts, runs independent checks, or reviews a diff. Its scout workflow is local-only; `dispatch` sends web research to `agentville:scout`. |
| `agentville:scout` | Serves the scout role: researches external questions with web search and fetch only, and holds no file or shell tool. |
| `agentville:validator` | Serves the validator role: runs targeted independent checks against a running system or built artefact with the tools the project's steering names, finds its tools through the `toolbelt` slot for any check that needs a command-line tool, maps each requirement to its checks, writes hashed raw evidence to the artefacts folder of the `workspace` slot, and never edits product code. `dispatch` does not spawn it yet and still sends this role to `agentville:worker`. |
| `agentville:reviewer` | Serves the reviewer role: reads a diff and the validator's sealed evidence (files listed in its `SHA256SUMS`) against the plan, checks that the validator recorded the slots the steering binds, and returns a pass, pass-with-notes, needs-changes or blocked verdict with file and line findings, read-only. `dispatch` does not spawn it yet and still sends this role to `agentville:worker`. |

## Rules

The standing rules for the root agent ship in `rules/root-agent.md`.

## Context injection

The jobs agents share, a place to write their files, a set of check tools and the way a topic's draft, plan and report are written, are slots rather than fixed rules. Agentville refers to each slot by its contract, and each agent uses its slots for itself on every run in two steps. Step 1: it calls `context-injection` once with every slot the task needs, which returns where each resolved skill lives: its id, the absolute path of its SKILL.md, the source and any fallback. Step 2: it reads each resolved skill (by id, or by path when it cannot be loaded by id) and follows it to resolve the artefacts directory, the tools or the topic documents. An agent never calls a slot's default skill directly, and both smiths fail an agent or skill that does. The plugin ships a default skill for each slot, and a project or user swaps in their own by binding the slot in their steering.

A binding is one line, `<slot>: Skill(<namespace>:<name>)`, in a rules file or `CLAUDE.md`, optionally under a `## Context injection` heading. The first match wins, in this order: project rules, project `CLAUDE.md` (with the files it imports on an `@<path>` line, one level deep), a project skill named after the slot, user rules, user `CLAUDE.md` (with its one-level `@<path>` imports), a user skill named after the slot, then the plugin default `agentville:<slot>`. A bound skill that cannot be found falls back to the default, and the agent reports the fallback. Each agent records what it resolved as `<slot>: <skill> (<source>)`, so a reviewer can check it against the steering.

For example, to have every Agentville agent use your own QA tools, put this line in your project's `CLAUDE.md`:

```markdown
## Context injection

toolbelt: Skill(acme:qa-tools)
```

With no binding, the default `workspace` uses the folder your steering names, else `tmp/` in the project, and says so in its report. The default `toolbelt` only discovers the tools that are present, naming OS-provided tools for any check type when nothing names one; bind your own skill when your checks need a specific database, HTTP or browser automation tool.

The `draft`, `plan` and `report` slots say how a topic's documents are written, and `workspace` says where: the defaults write `draft.md`, `plan.md` and `report.md` in the topic folder, `<workspace>/<topic-id>/`, shared by every agent on the topic. `orchestrate` never writes them itself; it dispatches a worker in Discuss, Plan and Report, and that worker resolves `workspace` and the stage's slot in one `context-injection` call. Questions come to you only in Discuss and Plan, and the Report still reaches you in chat. Bind your own skill, such as `draft: Skill(acme:notes)`, to keep the notes somewhere else or not at all.

## How they fit

`orchestrate` triages each request and runs the stages it needs. It sends every delegated piece of work through `dispatch`, one spawn at a time. It is a sample workflow and is opt-in: nothing loads it by default, and the root agent reads no files itself. To use it, add this line to your own `CLAUDE.md`:

```markdown
Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it.
```

`dispatch` writes each brief to the `relay` standard and picks the model and effort with `intelligence-routing-model`.

`dispatch` spawns `agentville:worker` for the worker, validator and reviewer roles and `agentville:scout` for the scout role, naming the role in a `<role>` tag on the brief's first line. It falls back to the built-in `general-purpose` agent only when those agent types are unavailable, and records the fallback.

`skill-smith` stands alone. `agent-smith` compiles new agents as forks of `worker`.

## External dependencies

`skill-smith` calls `/skill-creator` for evals and description tuning, so install that skill alongside it if you want `skill-smith` to test what it drafts. Its helper scripts need `python3`.

Both smiths install only to project scope (`.claude/` in the project) or user scope (`.claude/` in the home folder). They refuse any plugin folder, Agentville included, and the helper scripts enforce that.
