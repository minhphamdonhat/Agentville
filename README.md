# Agentville

Agentville is a plugin of skills and agents for running work through agents: a workflow that triages each request and runs the stages it needs, a procedure that delegates one task at a time, writing standards for what agents and people read, standing rules for a delegating agent, and five swappable slots that each agent resolves for itself. It installs as one versioned unit; skills are namespaced `agentville:<skill>` and agents `agentville:<agent>`.

## Requirements

Agentville runs out of the box on Linux, macOS and Windows, on a laptop or a bare VPS, with Claude Code as the main platform.

* **Claude Code**, with the plugin installed as described below.
* **Git**, for the release flow and the workspace's git-ignore check. The release flow's `git switch` needs Git 2.23 or newer; older Git uses `git checkout`.
* **Python 3.8 or newer**, only for the helper scripts of `agent-smith`, `skill-smith` and the maintainer skills. They use the standard library alone. Run them as `python3` on Linux and macOS and as `py -3` (or `python`) on Windows.
* **A shell:** bash on Linux and macOS, PowerShell on Windows. Skills and agents write commands in that form and give a PowerShell form where the two differ. A project's `CLAUDE.md` or steering can name another shell, and that wins.
* **uv** 0.13.5 or newer, only for the Townhall MCP server (see Townhall).

Nothing else is required. `rg`, `jq` and `gh` are optional: where an agent could use one, it uses Claude Code's own `Grep` and `Read` tools or a shell built-in when the tool is missing.

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

1. **Chat.** Install the plugin through Customize, then put these lines at the top of your custom instructions:

   ```markdown
   - Load `Skill(agentville:root-agent)` and follow it in every reply.
   - Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it.
   ```

2. **Claude Code with pod-lead as the main agent.** The plugin ships a `settings.json` with `{"agent": "pod-lead"}`, so an installed plugin makes `pod-lead` the main agent of every session. `pod-lead` runs every request through `orchestrate` and follows `root-agent`. To run it for one session only, start `claude --agent agentville:pod-lead`. Your own `agent` setting overrides the plugin's.

3. **Claude Code with another agent.** The documented ways to use an agent other than `pod-lead`:

   * Start one session with `claude --agent <name>`.
   * Name another agent in your own `agent` key in `~/.claude/settings.json`; it overrides the plugin's.
   * Disable the plugin with `claude plugin disable agentville@minhphamdo` (`claude plugin disable --help`: "Disable an enabled plugin"). Inferred, not documented: this drops its defaults along with its skills. No documented value unsets `agent` back to the built-in agent.

   To make that agent follow Agentville, add these lines to your project's `CLAUDE.md`:

   ```markdown
   - Load `Skill(agentville:root-agent)` and follow it in every reply.
   - Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it.
   ```

   To use your own workflow, fork `orchestrate` into a new skill and name it in the second line.

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
| `/agentville:draft` | Used by `orchestrate` only. Default for the `draft` slot: records a topic's notes, decisions and open points in rounds. |
| `/agentville:plan` | Used by `orchestrate` only. Default for the `plan` slot: records a topic's goal, tasks with done criteria, and approval as a record only. |
| `/agentville:report` | Used by `orchestrate` only. Default for the `report` slot: records a topic's outcome, evidence, review result, out-of-scope findings and open items. |
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

## Townhall

Townhall is a Python package in `agentville/` that keeps tickets on boards under `.agentville/` in your project (tracked in git) and moves them through a fixed set of stages. The plugin starts its MCP server for you through `plugins/agentville/.mcp.json`, so the tools below appear as `mcp__plugin_agentville_agentville__townhall_*` with no setup.

The server launches with `uvx` from a pinned commit SHA of this repository, with Python 3.15, so it runs on any OS whatever Python the host has. On `main` and `beta`, `.mcp.json` pins the SHA of the last released commit, so development and beta run the last released server; the release step moves the pin, never a tag, because tags can move. Version 0.7.0 introduces the package, so until it is released `.mcp.json` pins the commit that adds `agentville/`, and the server starts once that commit is on GitHub.

Townhall keeps its files beside the workspace: `.agentville/config.toml`, `.agentville/.gitignore` for its lock and temporary files, and the boards under `.agentville/townhall/`.

Requirements: `git`, network access on the first run, and `uv` new enough to offer Python 3.15.1 (0.13.5 does). Developing the package needs `uv` 0.13.5 or newer (`[tool.uv] required-version` in `agentville/pyproject.toml`); `uvx` may not enforce `required-version` for `--from` sources, so check your version yourself.

The first start downloads Python and the dependencies and builds PyYAML from source, because Python 3.15 has no prebuilt wheel yet. It can be slow. If Claude Code times out while starting the server, raise the limit, for example `MCP_TIMEOUT=60000 claude` in bash on Linux and macOS, or `$env:MCP_TIMEOUT = "60000"; claude` in PowerShell on Windows (milliseconds).

Behaviour to know:

* The files on disk are the ground truth; Temporal mirrors them on a best-effort basis.
* The decisions-table check (`TABLE001`) is a warning, not an error.
* Complete-stage auto-merge needs `[plugins.claude].enabled = true` and `[plugins.claude].auto_merge = true` (both off by default), plus `branch` and `target_branch` in the ticket's `index.md`. A merge cannot be undone, so it never guesses branches. Turning `auto_merge` on merges, on the first poller pass, every existing Complete ticket that has branch keys and no `.merge` marker.
* A failed triage leaves the ticket in Execute (not Todo) and unclaimed. Each `claude -p` run is limited by `[engine].claude_timeout_seconds` (default 1800).
* The plugin starts only the MCP server, which never starts Temporal. `agentville engine worker` starts the dev server, which keeps its data under `${CLAUDE_PLUGIN_DATA}/temporal/` when that variable is set, else in the per-user data folder.

| Tool | Purpose |
| --- | --- |
| `townhall_list_tickets` | Lists a board's ticket summaries, optionally only those in one stage. |
| `townhall_pick_ticket` | Claims the lowest-numbered eligible ticket in one stage and moves it to the next. |
| `townhall_get_ticket_pack` | Loads a ticket: its summary and every Markdown page in reading order. |
| `townhall_write_page` | Lints and writes a page under `draft/`, `plan/` or `execution/`, or `GLOSSARY.md` or `DRAFT.md`. |
| `townhall_list_tasks` | Lists a ticket's tasks with status and target files. |
| `townhall_create_task` | Creates a task file and registers it in the ticket index. |
| `townhall_update_task_status` | Sets a task's status; `done` ticks its checkboxes. |
| `townhall_request_inputs` | Stops and asks the user: writes `HANDOFF.md` and the question files, then moves the ticket to Need Inputs. |
| `townhall_get_handoff` | Reads `HANDOFF.md` and the answered and pending questions so work can resume. |
| `townhall_submit_review` | Writes the review summary, evidence and `diff.patch`, then moves the ticket from Execute to Review. |
| `townhall_move_ticket` | Moves a ticket to a target stage if the state machine allows it. |

## Context injection

The jobs agents share, a place to write files, a set of check tools and the way a topic's draft, plan and report are recorded, are slots rather than fixed rules. The plugin ships a default skill for each slot, and you swap in your own by binding the slot in your steering. `context-injection` sets the binding syntax and the order in which bindings are found.

For example, to have every Agentville agent use your own QA tools, put this in your project's `CLAUDE.md`:

```markdown
## Context injection

toolbelt: Skill(acme:qa-tools)
```

In Chat, bindings in custom instructions do not count, and every slot uses the plugin default.

## Where agents write

The workspace (agents' topic documents, evidence and run folders) writes only under `.agentville/topics/` in the project root:

```text
.agentville/topics/
  .gitignore                 # */evidence/, */*/artefacts/, */*/scratch/
  <topic-id>/                # topic documents: tracked
    evidence/run-<N>/        # validator evidence with SHA256SUMS: ignored
    <agent>/artefacts/       # what an agent keeps: ignored
    <agent>/scratch/         # throwaway files, deleted before the report: ignored
```

The workspace writes its `.gitignore` on first use when it is missing. Townhall owns `.agentville/config.toml`, `.agentville/.gitignore` and `.agentville/townhall/`, created by `agentville init`; the workspace and Townhall never read each other's files.

## External dependencies

`skill-smith` calls `/skill-creator` for evals and description tuning, so install that skill alongside it if you want `skill-smith` to test what it drafts. Its helper scripts need Python 3 (see Requirements).

Both smiths install only to project scope (`.claude/` in the project) or user scope (`.claude/` in the home folder). They refuse any plugin folder, Agentville included, and the helper scripts enforce that.
