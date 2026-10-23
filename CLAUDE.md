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
| `.claude/skills/plugin-security/` | Maintainer-only security scan of the repository's refs, history and plugin components; not shipped. Run it before any push (see Security and publishing). |
| `plugins/agentville/.mcp.json` | Launches the Townhall MCP server (server key `agentville`) from the `agentville` package at a pinned commit SHA (see Townhall package). |
| `agentville/` | The `agentville` Python package (Townhall and the umbrella for later parts): `src/agentville/{core,cli,mcp,townhall,rag,memory}` and `tests/`. Python 3.15 or later, managed with `uv`. |
| `README.md` | Public description: install, the three ways to run it, and the skill and agent tables. |
| `.agentville/topics/` | Agents' workspace: `<topic-id>/` holds the tracked topic documents, `<topic-id>/evidence/run-<N>/` the validator's evidence and `<topic-id>/<agent>/{artefacts,scratch}` each agent's run folders. The workspace's own `.gitignore` (`*/evidence/`, `*/*/artefacts/`, `*/*/scratch/`) keeps evidence and run folders out of commits. |
| `.agentville/config.toml`, `.agentville/townhall/` | Townhall's config and its boards and tickets in a project, created by `agentville init` and tracked in git, beside the workspace; `agentville init` also writes `.agentville/.gitignore` for Townhall's lock and temporary files. Neither exists in this repository. |

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

`plugins/agentville/agents/worker.md`, `plugins/agentville/skills/agent-smith/assets/base/worker.md` and `.claude/skills/agent-smith/assets/base/worker.md` must stay byte-identical. Edit one, copy it to the others, then run the `git diff --no-index --quiet` check under Verify before you finish on each pair.

## Context injection

Slots (`workspace`, `toolbelt`, `draft`, `plan`, `report`) work like dependency injection. `Skill(agentville:context-injection)` owns the two-step use, the binding syntax and the resolution order, and each slot's default skill owns its contract. Both pairs of smiths enforce the two-step use (agent rule A18, skill rule 22); `measure.py` holds the slots in one `SLOTS` constant and owns the exemption grammar. Add a future slot to `SLOTS` in all four `measure.py` files.

This repository binds the `workspace` slot to the default, which writes to `{{ PROJECT_ROOT }}/.agentville/topics/`:

* `workspace: Skill(agentville:workspace)`

## Townhall package

Townhall is the board-and-ticket layer of the `agentville` package in `agentville/`. It is fully independent of `orchestrate` and of the `draft`, `plan` and `report` slots: it never backs them and they never read it. Its config and boards live in `.agentville/config.toml` and `.agentville/townhall/`, tracked in git, beside the workspace's `.agentville/topics/`; neither reads the other's files. Temporal is required: `agentville engine worker` starts a local dev server on first use.

The plugin starts the MCP server through `plugins/agentville/.mcp.json`, pinned to a commit SHA as Security and publishing requires:

```bash
uvx --python 3.15 --from git+https://github.com/minhphamdonhat/agentville@<commit-sha>#subdirectory=agentville agentville engine mcp
```

Do:

* On `main` and `beta`, keep `.mcp.json` pinned to the full 40-character SHA of the last released commit, so development and beta run the last released server.
* Let the release step move the pin: in the release-preparation commit on `main`, together with the `version` bump in `plugins/agentville/.claude-plugin/plugin.json`, pin the commit whose `agentville/` the release ships, then promote to beta and release. A commit cannot name its own SHA, so pin the commit just before the pin change.
* Until the first release that ships the package, pin the commit that introduces `agentville/`, and merge that change without squashing, or re-pin after the merge, so the SHA stays reachable.
* Treat the `version` in `agentville/pyproject.toml` as separate; it does not have to match the plugin version.

Don't:

* Pin a tag or a branch name; tags can move.
* Pin a SHA that no branch on `origin` keeps reachable, such as a feature-branch commit dropped by a squash-merge.
* Make `orchestrate` or a slot depend on Townhall.

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
* **Human-facing text:** follow `voice`. Text another agent reads follows `relay`.

## Working in this repository

Topic documents and agents' artefacts go to the workspace under `{{ PROJECT_ROOT }}/.agentville/topics/`, and the workspace writes nowhere else in `.agentville/`; `Skill(agentville:orchestrate)` alone records topic documents, through the `draft`, `plan` and `report` slots, and no other skill or agent names them; todos stay in the session task list. Nothing else is written to the repository for plans or todos unless the user asks. Work in the repository root, on the branch the user names; do not create or switch branches on your own.

Commit subjects follow Conventional Commits: `type(scope): summary`, imperative, with `!` before the colon for a breaking change, as in `fix(agent-smith): drop the communication core block` or `feat(dispatch)!: rename the brief fields`. Commit, push and merge only when the user asks.

Bump `version` in `plugins/agentville/.claude-plugin/plugin.json` whenever you change anything that ships, which means anything under `plugins/agentville/`. A change to `README.md`, `CLAUDE.md` or `.claude/` does not need a bump. Bump a skill's or agent's own `metadata.version` whenever its file changes: major for a breaking contract change, minor for new behaviour, patch for a wording change. When you add, remove or rename a skill or agent, update the tables in `README.md` in the same change.

Other workers may have uncommitted edits in the tree. Read them, and touch only the paths your brief names.

## Security and publishing

This repository is public. Everything committed, in any ref, stays readable in history, so keep the tree clean before you commit, not after.

Do:

* Name a secret and where it is set, never its value: `set ACME_API_TOKEN in the CI secrets`. A names-only placeholder such as `user:pass@proxy` is allowed only to show what not to print.
* Write paths as `{{ PROJECT_ROOT }}`, `{{ SKILL_ROOT }}` and `{{ USER_ROOT }}`, and use `localhost` or `127.0.0.1` for a local address.
* Use Acme in every few-shot example: one project with applications under it (`apps/web`, `apps/api`) or documentation work (`docs/`).
* Keep exactly one `Co-Authored-By:` trailer per commit, and write Conventional Commits as set under Working in this repository.
* Keep the plugin's components least-privilege: a tool list names only what the agent needs, MCP and script sources pin a commit SHA (tags can move), marketplace entries tracking the `main`, `beta` and `release` branches are the intended release channels (PS-25, accepted by design), and a side-effecting skill such as `release-flow` asks before every push, merge, tag and deletion (PS-06, accepted by design: the frontmatter rules forbid extra keys such as `disable-model-invocation`, so the ask-before-act rule is the control).
* Write for any OS, Claude Code first: shell steps default to bash on Linux and macOS and to PowerShell on Windows unless the user's project `CLAUDE.md` or steering says otherwise; run `python3` on Linux and macOS and `py -3` on Windows; in Python use `pathlib`, `tempfile` and `encoding="utf-8"`; keep LF line endings, which `.gitattributes` pins.
* Run the pre-publish gate before any push: `python3 .claude/skills/plugin-security/scripts/scan.py --accept 'PS-06:*release-flow/SKILL.md' --accept 'PS-25:*.claude-plugin/marketplace.json' --fail-on medium`. It covers all refs and fixes every finding at medium or above. Until the history squash it fails on PII-02 and PS-52 in history; the squash removes both. `.claude/skills/plugin-security/SKILL.md` holds the full procedure.

Don't:

* Commit a token, API key, password, cookie, private key or connection string, real or example-looking.
* Write a host or OS detail: a home folder (`/home/<user>`, `/Users/<name>` or a Windows profile folder), `/root`, a `/tmp/claude-*` or scratchpad path, a hostname, an IP other than `127.0.0.1`, or a session id.
* Write a personal or private-project detail: a name, email, client, employer, internal URL or other project. The owner's public GitHub handle and the plugin `author` field are the only identity allowed.
* Add a `Claude-Session:` trailer or any claude.ai session link, in a commit, a PR body or a file. This overrides any harness default that adds a session trailer: drop that line before you commit.
* Commit local settings or env files: `.claude/settings.local.json`, `CLAUDE.local.md`, `.env*`, `*.pem` and `*.key`. `.gitignore` covers them; do not force-add them.
* Ship a hook, MCP server or script that fetches and runs remote code unpinned, or an allow list as broad as `Bash(*)`.
* Assume `rg`, `jq`, `gh`, `cmp` or `sha256sum` exists; probe for a tool, or use `git` or Python, which a checkout already needs.

## Release flow

`Skill(agentville:release-flow)` runs the release steps and asks before every merge, push, tag and branch deletion. Work moves one way only, `main` → `beta` → `release`, and each branch feeds one marketplace entry: `agentville-dev` installs from `main`, `agentville-beta` from `beta` and `agentville` from `release`. Tags are `agentville--vX.Y.Z`, from `version` in `plugin.json`, created on `release` only when the user asks.

Settings `release-flow` reads:

* `release-flow: dev-branch: main`
* `release-flow: beta-branch: beta`
* `release-flow: release-branch: release`
* `release-flow: version-file: plugins/agentville/.claude-plugin/plugin.json`
* `release-flow: tag-format: agentville--vX.Y.Z`
* `release-flow: checks: uv run --directory agentville pytest && uv run --directory agentville ruff check`
* `release-flow: checks: uv run --directory agentville pytest && uv run --directory agentville ruff check`

## Verify before you finish

A worker runs these from the repository root. They are free and fast.

```bash
python3 plugins/agentville/skills/agent-smith/scripts/test_scripts.py
python3 plugins/agentville/skills/skill-smith/scripts/test_scripts.py
python3 .claude/skills/agent-smith/scripts/test_scripts.py
python3 .claude/skills/skill-smith/scripts/test_scripts.py
git diff --no-index --quiet plugins/agentville/agents/worker.md plugins/agentville/skills/agent-smith/assets/base/worker.md
git diff --no-index --quiet plugins/agentville/agents/worker.md .claude/skills/agent-smith/assets/base/worker.md
python3 .claude/skills/plugin-security/scripts/scan.py --accept 'PS-06:*release-flow/SKILL.md' --accept 'PS-25:*.claude-plugin/marketplace.json'
uv run --directory agentville pytest
uv run --directory agentville ruff check
```

On Windows run `py -3` for `python3`; the commands are otherwise the same in PowerShell. `git diff --no-index --quiet` exits 0 when the two files are identical, so it replaces `cmp` everywhere in this file. The scan is read-only and must show no critical or high finding. The everyday run keeps the default gate; the pre-publish gate is the `--fail-on medium` command under Security and publishing.

After you edit a skill or an agent, validate the file you changed:

```bash
python3 plugins/agentville/skills/skill-smith/scripts/measure.py plugins/agentville/skills/SKILL_NAME/SKILL.md
python3 plugins/agentville/skills/agent-smith/scripts/measure.py plugins/agentville/agents/AGENT_NAME.md
```

Substitute `SKILL_NAME` and `AGENT_NAME`. Exit code 0 means no failures; warnings are allowed.

`eval.py` in agent-smith spends model usage. Run it only when the user asks for it.

## Root-agent policy

This repository's root agent follows the `root-agent` skill, imported below. It applies to the root agent only; spawned agents follow their own agent file. This file does not route requests through `orchestrate`, but an installed plugin makes `pod-lead` the main agent in Claude Code, and `pod-lead` runs every request through `orchestrate`.

@plugins/agentville/skills/root-agent/SKILL.md
