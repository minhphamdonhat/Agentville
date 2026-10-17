# Clarify tree

Read by SKILL.md step 3. It defines the slots of a skill's contract, the order in which to ask them and the question shape. Adapted from the grilling skill by Matt Pocock (MIT licence, Copyright (c) 2026 Matt Pocock): https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md

## Slots

A slot is one decision of the contract. A slot is settled when the user has answered it or accepted its recommended answer, or when it does not apply to the type (`n/a`). The final round shows every slot as `<slot>: <value>`, in the order below.

| Slot | Applies to | Prerequisites | Recommended answer comes from |
|---|---|---|---|
| skill-name | all | none | Triage; kebab-case, at most 64 characters |
| type | all | none | Triage; process, steering or knowledge |
| description | all | type | What the skill does, then at least two trigger contexts; at most 1,024 characters |
| role | process | type | The job and what it returns, in one or two sentences |
| constraints | process | role | Global hard rules, each with a one-clause reason |
| inputs | process | role | Each as `name: required or optional - default - description` |
| steps | process | inputs | Numbered step titles, the tool each names, and one Do and one Don't example each |
| output | process | steps | The returned fields, the literal template and the failure block with `status`, `reason` and `missing` |
| interaction | process | steps | Which steps may ask a person with `AskUserQuestion`; each such step returns `status: needs-input` with `missing:` when no person is reachable |
| sections | steering | type | One numbered section per decision the reader makes, then the Pre-send check |
| topics | knowledge | type | One topic per section, each titled as a reader would ask for it |
| sources | knowledge | topics | Relative links to files the skill ships, or external URLs, or none |
| supporting-files | all | steps, sections or topics | Files under `references/` or `scripts/` that the skill itself ships |

Settle the install `scope` (plugin or project, never user) outside this tree: SKILL.md step 4 owns it, so never ask it here.

## Frontier order

The frontier is every open slot whose prerequisites are settled. Ask it in this order, at most four questions per `AskUserQuestion` call:

1. skill-name and type.
2. description, then role, sections or topics and sources.
3. constraints and inputs.
4. steps and output.
5. interaction.
6. supporting-files.

A slot that a settled answer unlocks joins the next round. A slot whose answer says it does not apply becomes `n/a`.

## Scope by mode

| Mode | Slots asked |
|---|---|
| compile | Every slot of the type |
| improve | Only the slots the change touches, plus any of their prerequisites still open; every other slot keeps the value read from the existing skill |
| convert | Only the slots the old file leaves without a value; every slot it states keeps that value |

## Question shape

- Ask one numbered question per slot: `<n>. <slot>: <question>`.
- Make option 1 the recommended answer, labelled "(Recommended)", and quote its value in full so the user can accept it unchanged, such as `inputs: diff (required), strictness (optional, default normal)`. Follow it with one to three alternatives.
- Look a fact up with `Glob` or `Read` before asking; ask only decisions.
- After the last round, show the whole contract and ask "Build it?" with the options "Yes, build it (Recommended)" and "Change something". Ask nothing further after a yes.
- When no person is reachable, do not ask: return `status: needs-input` with the unsettled slots on `missing:` and the questions in `reason:`.
