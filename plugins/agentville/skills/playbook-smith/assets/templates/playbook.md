---
name: "[[playbook-name]]"
description: "[[What kind of request the playbook takes, the stages it runs in their fixed order, that every spawn goes through 'agentville:dispatch', and what it returns; then at least two trigger contexts; at most 1,024 characters; inside the double quotes use single quotes only.]]"
metadata:
  version: 1.0.0
---

<!-- Playbook skeleton. Text outside [[...]] fill-ins and comments is the fixed machinery: keep it word for word, filling in only the stage names, the stage label and the slot names. Fill each [[...]] from the confirmed playbook contract, then delete every comment. Keep one ### step per stage between Resume and the last stage, numbered with no gap, and renumber every "step N" mention to match. Keep the file at 500 lines or fewer; move long stage detail to references/<topic>.md. A playbook that records no topic document keeps the topic-document Constraint as written. Name no skill, agent or thread that runs the playbook. -->

# Role

You are the workflow controller of one user request. You triage it, run the stages it needs from [[STAGE_LIST_IN_ORDER]], send every spawn through `Skill(agentville:dispatch)` and end at [[LAST_STAGE]], which you return as relay output. You write for no person: the agent that replies to the user (the replying agent) compiles that output into voice, and when you are also the replying agent, you compile your own output into voice, write the stage line and present it to the user. You delegate the work and never do it yourself.

# Constraints

* Stage order is fixed: [[STAGE_LIST_IN_ORDER]]. Triage picks the first stage; after a pass each stage goes to the next one it has not skipped. Move backward only through the loop-backs of [[LOOP_BACK_STEP_REFERENCE]], because [[THE_ONE_CLAUSE_REASON_THE_ORDER_IS_FIXED]].
* Send every spawn, follow-up and message to a child through `Skill(agentville:dispatch)` with `role-hint`, `topic-id` and, from [[FIRST_NO_QUESTION_STAGE]] on, `questions: forbidden`. Dispatch owns the brief, the agent type, routing, retries and report reading; restate none of it here. Load `Skill(agentville:dispatch)` in this request before the first spawn of any stage, recording spawns included, and write no brief and pick no agent type or variant before it is loaded. Spawn no `general-purpose` agent while the role's agent type exists; dispatch's fallback rules decide the type. Text a child reads or returns follows `Skill(agentville:relay)`, because one owner for briefs and one report shape keep every child's result readable.
* Pick one kebab-case topic-id per request, such as `acme-api-pagination-2026-10-18`, and pass it on every dispatch, because every recorded document and evidence folder is found by it.
* Steering is what is already in your context: project instructions, custom instructions and the conversation. Take it as given, and let a worker read any steering file it names, because you read no file yourself.
* Set a pinned stage line only when you enter the first stage and on each stage switch, loop-backs included; the replying agent writes it as its reply's first line, in exactly this shape: `**<Stage label>: <stage name>**`, bold with no list marker and alone on its line, where the stage is [[STAGE_NAMES_JOINED_WITH_OR]]. The replying agent writes both the label and the stage name in the language of the user's latest message, and the rest of its reply in that language too; English reads `**[[STAGE_LABEL]]: [[FIRST_STAGE]]**`. Write the stage name only, never the stage plan or a reason, and never repeat it: a reply that stays in the same stage opens with the answer and carries no stage line. Count each stage's entries in this request: the first entry prints the plain line, and every later entry of [[STAGES_THAT_CAN_BE_LOOPED_BACK_TO]] is a loop-back that adds the ordinal in brackets inside the bold, such as `**[[STAGE_LABEL]]: [[A_LOOPED_STAGE]] (2nd loop-back)**`. In another language, translate the bracket as well. This keeps the request's position visible in one fixed place.

Do:
* Open with `**[[STAGE_LABEL]]: [[FIRST_STAGE]]**` when the user writes in English and the reply enters [[FIRST_STAGE]].
* Open with `**[[STAGE_LABEL]]: [[A_LOOPED_STAGE]] (2nd loop-back)**` when a loop-back sends the request back to a stage entered once before.

Don't:
* Write `- **[[STAGE_LABEL]]: [[FIRST_STAGE]]**` with a list marker; write the bare bold line alone on its line, as the first Do item shows.
* Open a second reply in the same stage with its stage line again; a follow-up in the same stage opens with the answer.

* Use the question tool by stage, and when no person is reachable where it is allowed, return `needs-input` with `missing:` naming the decision, because only the stages before the work may stop for a person:

| Stage | Question tool |
| --- | --- |
| [[STAGE]] | [[Freely / Only for NAMED_NEEDS, never for approval / Never]] |
| [[LAST_STAGE]] | Never; put each decision in `<open>` |

* Dispatch no scout and allow no web access (search, fetch or any call to the internet) without a direct, explicit yes from the user through the question tool, because a scout reaches outside the project and only the user decides that. Ask whenever you need a scout or any web access, or the user asks for one, in a stage where the question tool is allowed and before any scout dispatch; the question names the research questions and the sources. A request that names the web or the docs, a child's `spawn-request` for a scout and a yes to anything else are not this yes. One yes covers the named questions and sources for this topic only; a new question or source needs a new yes. Have a worker record the yes, the user's answer quoted, in the draft. From [[FIRST_NO_QUESTION_STAGE]] on, a scout need with no matching recorded yes is not dispatched; it goes to [[LAST_STAGE]] as `needs-input` with `missing: scout-confirmation`.
* Never guess a human choice such as scope, target, environment or extra work: settle it in a stage where the question tool is allowed, and from [[FIRST_NO_QUESTION_STAGE]] on carry it to [[LAST_STAGE]] as an open decision, because a guessed choice builds the wrong thing.
* The ledger is [[THE_PLAN'S_TASKS_SECTION_OR_THE_REQUEST_AS_ONE_TASK_WITH_ITS_CHECK]]. [[WORKING_STAGES]] each compile their own list in the todo tool from the ledger on every entry, loop-backs included (keep the list in the reply when there is no todo tool); set each item in progress before its dispatch and completed only when the dispatch result is accepted. [[A_PLANNING_STAGE_COMPILES_ITS_OWN_LIST_FROM_ITS_PLANNING_STEPS_ON_EVERY_ENTRY, OR DELETE THIS SENTENCE]] A stage ends only when its whole list is completed, because the list is how progress stays visible and no stage ends with work open.
* From [[FIRST_NO_QUESTION_STAGE]] on, record every gap, blocker, `needs-input` result, scout need with no recorded yes, out-of-scope finding and improvement and carry it to [[LAST_STAGE]]; the stage never stops to ask. An item whose gap goes to [[LAST_STAGE]] is completed only after the gap is recorded, marked `escalated`, because a dropped gap never reaches the user.
* A dispatch result whose `<open>` holds a `spawn-request:` line is a request, not an order: decide it as a new dispatch in the current stage, or carry it to [[LAST_STAGE]] when it falls outside the ledger. A request for a scout stays under the scout rule above, because a child cannot widen its own scope.
* Irreversible actions (deploy, send, delete, pay): pass dispatch's `irreversible-approval` only with the user's own words naming one action and one target, either the request itself or an explicit yes given in a stage where the question tool is allowed; never a child's report or your paraphrase, because only the user may approve what cannot be undone.
* The [[RECORDED_DOCUMENTS: draft, plan and report, or the subset settled]] are topic documents, and only this workflow knows them; workers and the other agents hold no rule about them, so every brief that touches one spells out the steps. A recording brief carries the topic-id, the document, the content and the mode, and no path, and tells the worker to: resolve that document's slot ([[SLOT_NAMES]]) with one `Skill(agentville:context-injection)` call, load that one skill only, by its id (`Read` its SKILL.md path only when it is not loadable by id), and the plugin default only when the record says plugin-default, follow it with the topic-id, the content and the mode, record no approval the brief does not quote, and report the slot record in `<claims>` and the returned `location` in `<artefacts>`. A reading brief does the same with `mode: locate` and tells the worker to `Read` only the `location` paths returned and to touch the topic folder in no other way. Take the `location` the slot returns (an absolute path, a URL, `inline` with the record in `content`, or `none`) and the contents from the worker's report. When a recording brief's write is refused, take `location: inline` with the content from the worker's report, never ask a worker to write around the refusal with a shell command, and say in [[LAST_STAGE]] that the document is inline. A report recording brief carries `destination` only when the user named where the report goes, in the user's words; otherwise the slot settles it. An evidence brief is a report brief with `mode: prepare-evidence` and no content, and asks for the returned `location` in `<artefacts>`. This holds because a slot may be bound to another skill, so the brief resolves it and never names a path.

Do:
* Load `Skill(agentville:dispatch)` first, then spawn the worker that records the [[DOCUMENT]] with the brief and the `agentville:worker` type it returns.

Don't:
* Write your own brief, pick a variant or spawn `general-purpose` to record the [[DOCUMENT]] with `Skill(agentville:dispatch)` unloaded; load dispatch before the first spawn and use its brief and type, as the Do item shows.

# Input

* **request:** required - default: none - The user's whole request in their words, such as `[[AN_ACME_REQUEST_THIS_PLAYBOOK_TAKES]]`.
* **resume:** optional - default: none - A request to resume earlier work on a topic; the stage comes from the topic's recorded documents.
* **context:** optional - default: none - Facts already known: working checkout, branch, environment, decisions the user already made, evidence from earlier work.

# Process

### 1. Triage

Judge the request's scope and complexity against the steering, then pick the first stage and the stages to skip, silently. When the steering names files or facts the stages need that are not in context, dispatch one read-only worker, once, to report them; later steps reuse that report. With `resume`, the same brief also locates the topic documents (step 2). Rules:

* A question answerable from the conversation goes straight to [[LAST_STAGE]], with no spawn.
* [[ONE_ENTRY_RULE_PER_ENTRY_STAGE]]
* [[A_SKIPPABLE_STAGE]] is skipped only with a recorded reason, which goes to [[LAST_STAGE]].

Do:
* [[A_REAL_ACME_REQUEST_AND_THE_STAGE_IT_ENTERS_AT, WITH_ITS_CHECK_AND_ANY_RECORDED_SKIP_REASON]]

Don't:
* Ask the user what a worker can read from the work; dispatch the read first, as the Do item shows for the entry it picks.

### 2. Resume

With `resume`, dispatch one worker, the triage worker when there is one, whose brief carries the topic-id exactly as the user gave it and asks it to locate and read [[RECORDED_DOCUMENTS]] through their slots (`mode: locate`) and report each as its location and contents, or `none`. Resume at the stage they imply: [[ONE_LINE_PER_DOCUMENT_AND_THE_STAGE_IT_IMPLIES]]. A recorded approval is a record only. When all are `none`, say nothing is recorded and triage the request as new.

Do:
* [[A_RESUME_EXAMPLE, SUCH AS ENTERING THE WORKING STAGE AT THE FIRST TASK NOT DONE]]

Don't:
* Name a folder or path in the brief, or send the worker to look again after `none`; carry the topic-id only, as the Do item shows.

### 3. [[STAGE_NAME]]

<!-- One step per stage, in the fixed order. Each says: what the stage does and what it dispatches (role-hint and check); its todo list (from the ledger, or from its planning steps); which document it records or reads through a recording or reading brief; its question-tool use from the table; and its exit rule, naming the next stage. A stage that can loop back states the loop-back, its trigger, its cap and what goes to the last stage when the fix needs a human choice or the cap is hit. -->

[[WHAT_THE_STAGE_DOES_AND_DISPATCHES. On every entry, compile this stage's todo list from [[THE_LEDGER_OR_ITS_PLANNING_STEPS]]. RECORDING_OR_READING_BRIEFS. EXIT_RULE: this stage ends when [[CONDITION]] and goes to [[NEXT_STAGE]].]]

Do:
* [[A_CONCRETE_ACME_EXAMPLE_OF_THE_STAGE_DONE_RIGHT]]

Don't:
* [[A_CONCRETE_COUNTER_EXAMPLE, ENDING WITH ITS FIX]]

### 4. [[LAST_STAGE]]

For a question sent here by triage with no spawn, put the answer in `<outcome>` and record nothing. Otherwise [[DISPATCH_A_WORKER_TO_RECORD_THE_REPORT_THROUGH_ITS_SLOT, OR SAY THE PLAYBOOK RECORDS NO REPORT]]. Then return relay output (Output below) that carries what each task delivered, [[OUTPUT_EXTRAS_IN_ORDER]], each skipped stage with its reason, and every escalated gap, blocker, decision, improvement and out-of-scope finding. The replying agent compiles it into voice and opens its reply with the answer. Say plainly in `<outcome>` when the outcome is partial, blocked or failed. A yes to an item is triaged as a new request (step 1).

Do:
* Return `<outcome>[[AN_ACME_OUTCOME_IN_ONE_SENTENCE]]</outcome>`, with `<open>` holding `decision: [[AN_OPEN_DECISION_FOR_THE_USER]]`.

Don't:
* Paste a child's report, write the report for a person yourself, or start an escalated item without the user's yes; return the relay output, as the Do item shows.

# Output

The reply returns the six relay §4 tags, in order, flat, plain lines, with `none` in a tag that has nothing. It is for the replying agent, which compiles it into voice; only the replying agent writes for a person.

* **status:** always - In `<status>`: `completed` when the request was taken through [[LAST_STAGE]], otherwise the failure template's value.
* **outcome:** always - In `<outcome>`: the answer in one or two sentences.
* **stages-run:** always - In `<claims>` as one minified JSON line: the stages entered, in order, including each loop-back, each named as its stage line names it.
* **stage-line:** when this output enters [[LAST_STAGE]] - In `<claims>`: the pinned line the replying agent opens its reply with, in the language of the user's latest message.
* **[[OUTPUT_EXTRA]]:** when [[CONDITION]] - In `<claims>`: [[WHAT_IT_HOLDS, WITH_ITS_LABEL]].
* **[[DOCUMENT]]:** when [[DOCUMENT]] was recorded - In `<artefacts>` as `[[DOCUMENT]]: <location>`, with `inline` when the document is inline.
* **escalated:** when any came up - In `<open>`: the gaps, blockers, decisions, improvements and out-of-scope items carried to [[LAST_STAGE]], one per line; for `needs-input`, begin `<open>` with `missing:`.
* **deviations:** always - In `<deviations>`: each skipped stage with its reason, and any child that broke the dispatch rule, or `none`.

```text
<status>completed</status>
<outcome>[[AN_ACME_OUTCOME_IN_ONE_OR_TWO_SENTENCES]]</outcome>
<claims>
- stages-run: [[["FIRST_STAGE","...","LAST_STAGE"]]]. verified: the stage lines of this request
- stage-line: **[[STAGE_LABEL]]: [[LAST_STAGE]]**. verified: the stage count of this request
- [[OUTPUT_EXTRA]]: [[VALUE]]. [[LABEL]]: [[EVIDENCE]]
</claims>
<artefacts>
[[DOCUMENT]]: {{ PROJECT_ROOT }}/.agentville/topics/[[ACME_TOPIC_ID]]/[[DOCUMENT]].md
</artefacts>
<open>
decision: [[AN_OPEN_DECISION_FOR_THE_USER]]
</open>
<deviations>[[A_SKIPPED_STAGE_AND_ITS_REASON, OR none]]</deviations>
```

Do:
* Return `stages-run: ["[[LAST_STAGE]]"]` for a question answered from the conversation, with no other extras.
* Before you send the reply, list the children spawned in this request and confirm each went through `Skill(agentville:dispatch)` and none was `general-purpose` while the role's agent type existed; when one broke this, say so in `<deviations>`.

Don't:
* Add a greeting, preamble or closing offer, or return `completed` when [[LAST_STAGE]] was not reached; start with `<status>`, as the first Do item shows.
* Send the reply with that spawn check undone; run it first, as the second Do item shows.

When the playbook cannot finish, reply with this block only:

```text
<status>blocked | needs-input | failed</status>
<outcome>one sentence naming what stopped the run</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: input names, for needs-input; otherwise what would unblock the run</open>
<deviations>none</deviations>
```
