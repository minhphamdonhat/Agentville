# Agentville

Agentville is a Claude Code plugin that packages seven skills for running work through agents: a workflow that routes each request, a procedure that delegates one task at a time, and writing standards for what agents and people read. It installs as one versioned unit, and every skill is namespaced `agentville:<skill>`.

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
| `/agentville:skill-smith` | Creates, improves or converts a Claude skill from a template, then validates and installs it. |
| `/agentville:agent-smith` | Compiles a Claude Code agent as a fork of the base worker, then validates it, evals it against the worker and installs it. |

## Agents

Both agents read their role from a `<role>ROLE</role>` tag on the first line of the brief.

| Agent | Purpose |
| --- | --- |
| `agentville:worker` | Serves the worker, validator and reviewer roles: implements, explores and drafts, runs independent checks, or reviews a diff. |
| `agentville:scout` | Serves the scout role: researches external questions with web search and fetch only, and holds no file or shell tool. |

## Rules

The standing rules for the root agent ship in `rules/root-agent.md`.

## How they fit

`orchestrate` decides how much process a request deserves and runs its stages. It sends every delegated piece of work through `dispatch`, one spawn at a time.

`dispatch` writes each brief to the `relay` standard and picks the model and effort with `intelligence-routing-model`.

`dispatch` spawns `agentville:worker` for the worker, validator and reviewer roles and `agentville:scout` for the scout role, naming the role in a `<role>` tag on the brief's first line. It falls back to the built-in `general-purpose` agent only when those agent types are unavailable, and records the fallback.

`skill-smith` stands alone. `agent-smith` compiles new agents as forks of `worker`.

## External dependencies

`skill-smith` calls `/skill-creator` for evals and description tuning, so install that skill alongside it if you want `skill-smith` to test what it drafts. Its helper scripts need `python3`.
