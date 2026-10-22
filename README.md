# Agentville

Agentville is a plugin of skills and agents for running work through agents: a workflow that triages each request and runs the stages it needs, a procedure that delegates one task at a time, writing standards for what agents and people read, standing rules for a delegating agent, and five swappable slots that each agent resolves for itself. It installs as one versioned unit; skills are namespaced `agentville:<skill>` and agents `agentville:<agent>`.

## Install

In Claude Code, add the marketplace once, then install one channel:

```text
/plugin marketplace add minhphamdonhat/agentville
/plugin install agentville@minhphamdo
```

| Channel | Install id | Branch |
| --- | --- | --- |
| Release | `agentville@minhphamdo` | `release` |
| Beta | `agentville-beta@minhphamdo` | `beta` |
| Development | `agentville-dev@minhphamdo` | `main` |

Install one channel at a time: all three load the same names under `agentville:`, so two would clash. To switch, uninstall the one you have and install the other, for example `/plugin uninstall agentville@minhphamdo` then `/plugin install agentville-beta@minhphamdo`.

In Chat, open Customize, then Plugins, choose Add marketplace, enter `minhphamdonhat/agentville` and install one channel.

## Three ways to run it

In Claude Code, installing Agentville makes `pod-lead` the main agent by default, so `orchestrate` runs on every request. Chat and Cowork ignore plugin settings, so there you opt in. Pick one way:

1. **Chat.** Install the plugin through Customize, then put this line at the top of your custom instructions:

   ```markdown
   Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it.
   ```

2. **Claude Code with pod-lead as the main agent.** The plugin ships a `settings.json` with `{"agent": "pod-lead"}`, so an installed plugin makes `pod-lead` the main agent of every session. `pod-lead` runs every request through `orchestrate` and follows `root-agent`. To run it for one session only, start `claude --agent agentville:pod-lead`. Your own `agent` setting overrides the plugin's.

3. **Claude Code with another agent.** The documented ways to use an agent other than `pod-lead`:

   * Start one session with `claude --agent <name>`.
   * Name another agent in your own `agent` key in `~/.claude/settings.json`; it overrides the plugin's.
   * Inferred, not documented: disable the plugin with `claude plugin disable agentville@minhphamdo`, which drops its defaults along with its skills. No documented value unsets `agent` back to the built-in agent.

   To make that agent follow Agentville, add the line from way 1 to your project's `CLAUDE.md`. To have it delegate every task as `pod-lead` does, add a second line:

   ```markdown
   Follow `Skill(agentville:root-agent)`.
   ```

### What loads where

| Part | Claude Code | Cowork | Chat |
| --- | --- | --- | --- |
| Skills | Yes | Yes | Yes |
| Agents | Yes | Yes | Ignored per the docs |
| `settings.json` (`agent`) | Yes | Ignored | Ignored |
| Hooks | Yes | Yes | Ignored |

Chat now shares Cowork's Agent tool and file writing in some accounts, so `dispatch` can still spawn there; when an `agentville:` agent type is missing, it falls back to `general-purpose`.

### Updates

In Claude Code, auto-update is off by default for third-party marketplaces. Run `claude plugin marketplace update minhphamdo` to refresh the listings, which leaves installed plugins as they are. Then run `claude plugin update agentville@minhphamdo` (or the channel you installed, such as `agentville-beta@minhphamdo`), or choose Update now in the Installed tab. A running session keeps the old version until you restart it or run `/reload-plugins`. In Chat, turn on Sync automatically for a github.com marketplace, or use Check for updates.

## Skills

Each skill is invoked as `/agentville:<name>`.

| Skill | Purpose |
| --- | --- |
| `/agentville:orchestrate` | Workflow that `pod-lead` runs on every request: triages each request, runs the stages it needs from Discuss, Plan, Execute, Validate, Review and Report, and sends every spawn through `dispatch`. |
| `/agentville:dispatch` | Takes one delegated task through sharpening, agent choice, model and effort routing, brief, spawn, report reading and failure handling. |
| `/agentville:root-agent` | Standing rules for an agent that delegates every task: voice on every reply, the answer first, a fixed tool list with no file reads, full skill names and a live task list. |
| `/agentville:relay` | Writing standard for text another agent reads, such as briefs, hand-backs and tool results; owns the report status tokens. |
| `/agentville:voice` | Writing standard for Markdown a person reads, such as chat replies, reports, commit text and document files. |
| `/agentville:intelligence-routing-model` | Picks the cheapest Claude tier and effort level that still succeeds. |
| `/agentville:context-injection` | Resolves slots to the skills that fill them and owns the binding syntax and resolution order. |
| `/agentville:workspace` | Default for the `workspace` slot: a run's topic, artefacts and scratch folders. |
| `/agentville:draft` | Default for the `draft` slot: records a topic's notes, decisions and open points in rounds. |
| `/agentville:plan` | Default for the `plan` slot: records a topic's goal, tasks with done criteria, and approval as a record only. |
| `/agentville:report` | Default for the `report` slot: records a topic's outcome, evidence, review result, out-of-scope findings and open items. |
| `/agentville:toolbelt` | Default for the `toolbelt` slot: discovers which verification tools are present for the checks a task needs. Discovery only; no network probes. |
| `/agentville:release-flow` | Runs a one-way release flow in any repository; every merge, push, tag and branch deletion waits for your yes. |
| `/agentville:skill-smith` | Creates, improves or converts a Claude skill, validates it and installs it to project or user scope. |
| `/agentville:agent-smith` | Compiles an agent as a fork of the base worker, validates it, evals it against the worker and installs it to project or user scope. |

## Agents

Each agent reads its role from a `<role>ROLE</role>` tag on the first line of the brief. `dispatch` picks the agent for each role.

| Agent | Purpose |
| --- | --- |
| `agentville:worker` | The base agent: implements, explores and drafts. Its scout workflow is local-only. |
| `agentville:scout` | Researches external questions with web search and fetch only; holds no file or shell tool. |
| `agentville:validator` | Proves a behaviour with independent checks and writes hashed evidence; never edits product code. |
| `agentville:reviewer` | Reviews a diff against a plan, read-only, and reads the validator's evidence when present. |
| `agentville:pod-lead` | Standalone lead, not a worker fork: runs every request through `orchestrate`, delegates all work and holds no edit, search or shell tool. |

## Context injection

The jobs agents share, a place to write files, a set of check tools and the way a topic's draft, plan and report are recorded, are slots rather than fixed rules. The plugin ships a default skill for each slot, and you swap in your own by binding the slot in your steering. `context-injection` sets the binding syntax and the order in which bindings are found.

For example, to have every Agentville agent use your own QA tools, put this in your project's `CLAUDE.md`:

```markdown
## Context injection

toolbelt: Skill(acme:qa-tools)
```

In Chat, bindings in custom instructions do not count, and every slot uses the plugin default.

## External dependencies

`skill-smith` calls `/skill-creator` for evals and description tuning, so install that skill alongside it if you want `skill-smith` to test what it drafts. Its helper scripts need `python3`.

Both smiths install only to project scope (`.claude/` in the project) or user scope (`.claude/` in the home folder). They refuse any plugin folder, Agentville included, and the helper scripts enforce that.
