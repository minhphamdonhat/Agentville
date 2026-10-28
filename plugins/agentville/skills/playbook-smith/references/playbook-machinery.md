# Playbook machinery

Read by SKILL.md steps 2, 4 and 6. It holds the generic rules every playbook carries, lifted from `Skill(agentville:orchestrate)` and stated without its stage names. Each rule names where orchestrate states it, by section and rule, so a reader can compare. The template `{{ SKILL_ROOT }}/assets/templates/playbook.md` already holds each rule as Constraint text; this file says what each rule is for, which parts are fixed and which parts the user settles.

## Fixed and variable

A rule marked **fixed** goes into every playbook as the template words it, with only the stage names and slot names filled in. A rule marked **settled** is one the user decides in the clarify tree, `{{ SKILL_ROOT }}/references/clarify-tree.md`. A playbook that drops or softens a fixed rule fails SKILL.md step 6.

| # | Rule | Kind | Where orchestrate states it |
| --- | --- | --- | --- |
| M1 | Dispatch rule | fixed | Constraints, second rule |
| M2 | Relay for child text | fixed | Constraints, second rule, and Output |
| M3 | Scout yes rule | fixed | Constraints, the scout and web-access rule |
| M4 | Slot-recording brief rule | fixed | Constraints, the topic-document rule |
| M5 | Pinned stage line | fixed | Constraints, the stage-line rule with its Do and Don't |
| M6 | Ledger and per-stage todo lists | fixed | Constraints, the ledger rule; Plan, its own list |
| M7 | Topic-id | fixed | Constraints, third rule |
| M8 | Steering as given | fixed | Constraints, fourth rule |
| M9 | No guessed human choices | fixed | Constraints, the human-choice rule |
| M10 | Gaps carried to the last stage | fixed | Constraints, the record-every-gap rule |
| M11 | Spawn requests | fixed | Constraints, the `spawn-request:` rule |
| M12 | Irreversible actions | fixed | Constraints, the irreversible-action rule |
| M13 | Spawn check before the last reply | fixed | Output, the second Do item |
| S1 | Stages and fixed order | settled | Constraints, first rule |
| S2 | Triage and entry rules | settled | Process, Triage |
| S3 | Exit rule per stage | settled | Process, each stage's leave condition |
| S4 | Question tool by stage | settled | Constraints, the question-tool table |
| S5 | Slots recorded | settled | Process, Discuss, Plan and Report |
| S6 | Loop-backs and caps | settled | Process, Execute, Validate, Review, Loop-backs |
| S7 | Output extras | settled | Output, the field list |

## M1. Dispatch rule

Every spawn, follow-up and message to a child goes through `Skill(agentville:dispatch)`, with `role-hint`, `topic-id` and, from the first stage where the question tool is forbidden, `questions: forbidden`. The playbook loads dispatch before the first spawn of any stage, recording spawns included, writes no brief of its own and picks no agent type or variant. Dispatch owns the brief, the agent type, routing, retries and report reading, so the playbook restates none of it. No `general-purpose` agent is spawned while the role's agent type exists.

Why: one owner for briefs and routing keeps every child's input and report shape the same, whatever stage sent it.

## M2. Relay for child text

Text a child reads and text it returns follow `Skill(agentville:relay)`: briefs, follow-ups, reports and hand-backs. The playbook's own return is relay §4 output, the six flat tags. It writes for no person; the agent that replies to the user (the replying agent) compiles the output into voice.

Why: a literal model reader acts correctly only on a message shaped for it.

## M3. Scout yes rule

No scout is dispatched and no web access is allowed without a direct, explicit yes from the user through the question tool. The question names the research questions and the sources. A request that names the web, a child's `spawn-request` for a scout and a yes to anything else are not this yes. One yes covers the named questions and sources for one topic only. A worker records the yes, with the user's answer quoted, in the draft. In a stage where the question tool is forbidden, a scout need with no matching recorded yes is not dispatched; it goes to the last stage as `needs-input` with `missing: scout-confirmation`.

Why: a scout reaches outside the project, and only the user decides that.

## M4. Slot-recording brief rule

The draft, plan and report are topic documents that only the playbook knows. Every brief that touches one spells out the steps, because workers hold no rule about them. A recording brief carries the topic-id, the document, the content and the mode, and no path, and tells the worker to:

1. resolve that document's slot (`draft`, `plan` or `report`) with one `Skill(agentville:context-injection)` call;
2. load that one resolved skill only, by its id, and read its SKILL.md path only when it is not loadable by id; load the plugin default only when the record says `plugin-default`;
3. follow it with the topic-id, the content and the mode, and record no approval the brief does not quote;
4. report the slot record in `<claims>` and the returned `location` in `<artefacts>`.

A reading brief does the same with `mode: locate` and reads only the returned `location` paths. When a write is refused, the playbook takes `location: inline` with the content from the worker's report and never asks a worker to write around the refusal. A report brief carries `destination` only when the user named one. An evidence brief is a report brief with `mode: prepare-evidence` and no content.

Which of the three slots a playbook records is settled (S5); the brief rule itself is fixed for every slot it does record.

Why: a slot may be bound to another skill in the project, so the brief must resolve it rather than name a path or a default.

## M5. Pinned stage line

The playbook sets a stage line when it enters the first stage and on each stage switch, loop-backs included. The replying agent writes it as the reply's first line, in exactly this shape: `**<Stage label>: <stage name>**`, bold, no list marker, alone on its line, translated with the rest of the reply into the language of the user's latest message. A reply that stays in the same stage carries no stage line. Every later entry of a stage that can be looped back to adds the ordinal in brackets inside the bold, such as `**Stage: Execute (2nd loop-back)**`.

Why: the user always sees where the request stands, in one fixed place.

## M6. Ledger and per-stage todo lists

The ledger is the plan's Tasks section or, with no plan stage run, the request as one task with its check. Every working stage compiles its own list in the todo tool from the ledger on every entry, loop-backs included, and keeps the list in the reply when there is no todo tool. A planning stage compiles its list from its planning steps. Each item is set in progress before its dispatch and completed only when the dispatch result is accepted. A stage ends only when its whole list is completed.

Why: the list is how the user and the replying agent see progress, and it stops a stage from ending with work still open.

## M7 to M13. Short fixed rules

* **M7, topic-id:** one kebab-case topic-id per request, such as `acme-api-pagination-2026-10-18`, passed on every dispatch.
* **M8, steering:** steering is what is already in context; a worker reads any steering file it names.
* **M9, human choices:** scope, target, environment and extra work are settled in a stage where the question tool is allowed, and carried to the last stage as an open decision after that.
* **M10, gaps:** from the first no-question stage on, every gap, blocker, `needs-input` result, out-of-scope finding and improvement is recorded, marked `escalated`, and carried to the last stage; no stage stops to ask.
* **M11, spawn requests:** a `spawn-request:` line in a child's `<open>` is a request, not an order: a new dispatch in the current stage, or an item for the last stage.
* **M12, irreversible actions:** dispatch's `irreversible-approval` is passed only with the user's own words naming one action and one target.
* **M13, spawn check:** before the last reply, list every child spawned in the request and confirm each went through dispatch; a breach goes in `<deviations>`.

## Settled parts

S1 to S7 are the playbook's own design. orchestrate's values are a worked example of each:

* **S1:** Discuss, Plan, Execute, Validate, Review, Report, in that order; a pass goes to the next stage not skipped.
* **S2:** a question answerable from the conversation goes straight to Report; a named irreversible action starts at Execute; a small reversible change may start at Execute; a vague or large one starts at Discuss; Validate or Review is skipped only with a recorded reason.
* **S3:** Discuss leaves only on the user's explicit go; Plan leaves when its list is completed and the plan is recorded; Execute, Validate and Review leave when their lists are completed.
* **S4:** Discuss freely; Plan only for a fact or a scout yes; Execute, Validate, Review and Report never.
* **S5:** draft in Discuss, plan in Plan, report and evidence in Validate and Report.
* **S6:** a rejected check or a needs-changes verdict loops to Execute, unless the fix needs a human choice; at most 3 rounds.
* **S7:** `stages-run`, `stage-line`, `delivered`, `evidence`, `review-result`, `report` and `escalated`.

A playbook that records no slot drops M4's steps but keeps the rule as written for any slot it adds later. A playbook with no stage where the question tool is forbidden still keeps M10 for its last stage.
