# Clarify tree

Read by SKILL.md step 3. It defines the slots of an agent's contract, the order in which to ask them and the question shape. Adapted from the grilling skill by Matt Pocock (MIT licence, Copyright (c) 2026 Matt Pocock): https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md

## Slots

A slot is one decision of the contract. A slot is settled when the user has answered it or accepted its recommended answer. The final round shows every slot as `<slot>: <value>`, in the order below. The core sections (identity, core constraints) are fixed by the base worker and are never a slot.

| Slot | Prerequisites | Recommended answer comes from |
|---|---|---|
| agent-name | none | The analysis; kebab-case, at most 64 characters, not taken by an existing agent |
| description | agent-name | What the agent does and the roles it serves, then when to spawn it; at most 1,024 characters |
| personality | description | Two to four sentences on how the agent works and what it values |
| workflows | description | Workflow names, each with its `Role:` (worker, validator, reviewer or scout) and when it applies |
| workflow-inputs | workflows | Per workflow, each input as `name: required or optional - default - description` |
| workflow-steps | workflow-inputs | Per workflow, numbered steps; each names its tool or `Skill(namespace:name)`, or hands back a spawn request |
| workflow-outputs | workflow-steps | Per workflow, the returned fields as `name: always or when <condition> - <tag>: what it holds`, each in one of the six relay §4 tags |
| rules | workflows | Extending rules, each with a one-clause reason; they follow the core constraints and never contradict them |
| exceptions | workflow-steps | Each condition the agent can hit and the relay §4 status token it reports |
| tools | workflow-steps | Every tool a step names, and nothing else; asked as its own explicit question, always last |
| disallowed-tools | tools | The base worker's denied tools minus any the user granted |

Settle the install `scope` (plugin or project, never user) outside this tree: SKILL.md step 4 owns it, so never ask it here.

## Frontier order

The frontier is every open slot whose prerequisites are settled. Ask it in this order, at most four questions per `AskUserQuestion` call:

1. agent-name, description and personality.
2. workflows.
3. workflow-inputs, workflow-steps and workflow-outputs, one workflow per round when there are several.
4. rules and exceptions.
5. tools and disallowed-tools, in a round of their own.

## The tools question

Ask it explicitly, even when the steps make the answer obvious: "Which tools may `<agent-name>` use?". Option 1 (Recommended) is the list the steps need, quoted in full, such as `Read, Grep, Glob, Skill`. Offer the base worker's list `TaskCreate, TaskUpdate, TaskGet, TaskList, TaskStop, Read, Write, Edit, Glob, Grep, Bash, NotebookEdit, Monitor, Skill` as an alternative. Never offer `Agent`: a compiled agent holds no spawn tool by default, and a step that needs another agent hands a spawn request back instead. Add `Agent` only when the user names it unprompted, and then set `allow-agent` to yes.

## Scope by mode

| Mode | Slots asked |
|---|---|
| compile | Every slot |
| improve | Only the slots the change touches, plus any of their prerequisites still open; every other slot keeps the value read from the existing agent; the tools question is asked again whenever a step changes |

## Question shape

- Ask one numbered question per slot: `<n>. <slot>: <question>`.
- Make option 1 the recommended answer, labelled "(Recommended)", and quote its value in full so the user can accept it unchanged. Follow it with one to three alternatives.
- Look a fact up with `Glob` or `Read` before asking; ask only decisions.
- After the last round, show the whole contract and ask "Build it?" with the options "Yes, build it (Recommended)" and "Change something". Ask nothing further after a yes.
- When no person is reachable, do not ask: return `status: needs-input` with the unsettled slots on `missing:` and the questions in `reason:`.
