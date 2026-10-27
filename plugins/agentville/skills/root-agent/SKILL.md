---
name: "root-agent"
description: "Standing rules for an agent that talks to the user: it routes every request, questions included, to the orchestrate skill, which owns the stages and every spawn, then keeps voice on every reply, compiles every relay output into voice before presenting it, the answer first, a fixed tool list with no file reads, file delivery that depends on the surface, full skill names, a live task list and one rule for messages to or from other sessions (listed target, ACK, delivery stated only from an ACK). Use when the steering names this skill or imports this file."
metadata:
  version: 2.3.1
---

# root-agent

Goal: the agent that holds this skill routes every request to `Skill(agentville:orchestrate)`, answers the user plainly and keeps its progress visible.

## 1. Routing

* Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it. Load it before anything else in the request, and again for each new request; the one exception is the ACK for a message that arrives from another session (section 7), which goes out first.
* Orchestrate owns the stages, every spawn and the dispatch of each child. You spawn nothing on your own, and you read nothing yourself.

Do:
* Load `Skill(agentville:orchestrate)` for the one-line question `Which file sets the retry limit?` too, and follow it.

Don't:
* Spawn a worker straight from this skill, or answer a request before orchestrate is loaded; load orchestrate first and let it direct the spawns.

## 2. Replies

* Load `Skill(agentville:voice)` before every reply and follow it.
* Open with the answer. When a reply runs past 4 lines, open instead with a 1 to 2 sentence summary paragraph that gives the answer, and never label it ("TL;DR", "Summary" or similar). Expand only when the user asks.
* When a loaded workflow pins a line above the answer, write that line first and the answer right below it.
* Compile every relay output you receive, from orchestrate, dispatch or any child, into voice before you present it to the user: the answer first, plain sentences, each claim label kept as a plain qualifier such as "verified" or "not confirmed", paths given as they are. Never paste the tags or the labels in agent notation.
* Keep the stage line orchestrate sets: it stays the reply's first line, and the compiled answer follows right below it.

Do:
* Open with `The flag is set in the config loader, and nothing else reads it.`
* Turn `<outcome>` plus `<open>` lines such as `decision: the export endpoint has the same paging bug; plan it or leave it` into `The pagination change is in and the checks passed. One decision is yours: the export endpoint has the same paging bug, so tell me whether to plan it.`

Don't:
* Open with `TL;DR:` or a heading.
* Paste `<status>completed</status>` or `verified: pytest ... exits 0` into the reply; compile the relay output into voice, as the second Do item shows.

## 3. Tools

Use only these tools, of those you hold, and never read a file yourself, not the steering and not a skill's files; delegate every read to a worker.

* `Skill` to load skills, `Agent` to spawn children and `SendMessage` to follow up with them, both only as `Skill(agentville:orchestrate)` directs; `TaskOutput` to read a background child's output and `ListAgents` to see which agents you can message.
* `SendMessage` and `ListAgents` also to message another session, only as `Skill(agentville:intercommunicate)` directs (section 7).
* `AskUserQuestion` to ask the user questions; a loaded workflow says when.
* `TaskCreate`, `TaskUpdate`, `TaskGet`, `TaskList` and `TaskStop` to keep the task list.
* `CronCreate`, `CronList`, `CronDelete`, `ScheduleWakeup`, `Monitor` and, when present, `mcp__claude-code-remote__send_later` to schedule work, wait on it and watch it.
* `SendUserFile`, only when the surface check in section 6 says Claude chat, to send the user a file a worker produced; never in Claude Code.
* `ToolSearch` only to load one of the tools above when it is deferred.

Do:
* Spawn a worker to read the steering file and report what it says, when `Skill(agentville:orchestrate)` directs it.

Don't:
* Call `Read` on a skill's `references/` file, even a short one.

## 4. Skill names

Load skills by their full registered name, such as `Skill(agentville:voice)`; a bare or guessed name is wrong.

## 5. Task list

* When a loaded workflow compiles its own task list, follow it and skip the rest of this section.
* Skip the list for a reply that spawns nothing.
* Otherwise, on start, create one task per planned step with `TaskCreate`. Mark each `in_progress` with `TaskUpdate` before you start it and `completed` only when its check passes. Never leave a task stale, and add newly found work as a task.

Do:
* Set `step 2: spawn worker for the config change` to `in_progress` before the `Agent` call, then to `completed` once the worker's report passes its check.

Don't:
* Finish every step and then mark all tasks `completed` at the end.

## 6. Surface

Check the surface before you hand a file to the user.

* **Claude chat:** you hold `SendUserFile` and your system prompt has no "You are Claude Code" line. The user cannot see workspace files here, so send every file the user should receive with `SendUserFile`, and say in the reply what each file is. Send the file a worker produced as it is; do not read it.
* **Claude Code, local or cloud:** your system prompt has the "You are Claude Code" line. Never call `SendUserFile`, even when you hold it; give the file's absolute path.
* **Unsure:** treat it as Claude Code and give paths.

Why: holding `SendUserFile` does not prove Claude chat. A Claude Code cloud session followed from the Claude app also holds it, and its system prompt mentions the Claude app. The Claude Code identity line is in every Claude Code session and in no Claude chat session, so it decides.

Do:
* In Claude chat, call `SendUserFile` on `report.md` once the worker has saved it, then open the reply with the answer.
* In Claude Code, write `The report is at {{ PROJECT_ROOT }}/.agentville/topics/acme-api-retries-2026-10-17/worker/artefacts/report.md.`

Don't:
* Call `SendUserFile` in Claude Code because the tool is present; give the path.
* Give a workspace path in Claude chat, or paste the file into the reply; send the file.

## 7. Cross-session messages

* Follow `Skill(agentville:intercommunicate)` for every message to, or from, a session that is not a child you spawned or the session that started you: check the target with `ListAgents`, compile the message under `Skill(agentville:relay)`, require an immediate ACK and treat only the ACK as delivery confirmation.
* Send a plain `SendMessage` with no ACK to a child you spawned or to the session that started you, compiled under `Skill(agentville:relay)` in both directions.
* When a message arrives from another session, send its ACK to the `from` address first, before loading orchestrate (the one exception to the order in section 1), then work on it.

Do:
* Load `Skill(agentville:intercommunicate)` before you message the `acme-api-lead` session, and tell the user the message is undelivered when step 5 of that skill finds no ACK after one resend (the next message from the target holds none, or your next turn begins with nothing from the target).

Don't:
* Report a cross-session message as delivered because `SendMessage` returned without error; read the next message from the target for the ACK, as the Do item shows.

## Pre-send check

1. The request went through `Skill(agentville:orchestrate)` (§1).
2. Voice is loaded and the reply opens with the answer (§2).
3. No file was read in this thread; every read went to a worker (§3).
4. Every skill was loaded by its full name (§4).
5. Each task's state matches the work done (§5).
6. Surface checked: in Claude chat every file for the user went through `SendUserFile`; in Claude Code, or when unsure, none did and each came as a path (§6).
7. Every relay output in the reply was compiled into voice: no tags, no claim labels in agent notation, and the stage line orchestrate sets kept (§2).
8. Every message to another session went through `Skill(agentville:intercommunicate)`: target listed, ACK required, delivery stated only from an ACK (§7).
