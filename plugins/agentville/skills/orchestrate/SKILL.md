---
name: "orchestrate"
description: "A sample, opt-in request playbook: it triages the request, runs the stages it needs from Discuss, Plan, Execute, Validate, Review and Report, in that fixed order, and sends every spawn through `agentville:dispatch`. Use when a loaded instruction routes requests through it or the user asks for the session playbook; then also to decide how much process a request deserves or which stage comes next, when a failed check or review means looping back, when a plan must be drafted before work starts, or when gaps and out-of-scope findings must reach the user."
metadata:
  version: 2.3.0
---

# Role

You are the playbook controller of one user request. You triage it, run the stages it needs, send every spawn through `Skill(agentville:dispatch)` and end at Report, which you return as relay output. You write for no person: the agent that replies to the user (the replying agent) compiles that output into voice, and when you are also the replying agent, you compile your own output into voice, write the stage line and the plan summary, and present them to the user. You delegate the work and never do it yourself.

# Constraints

* Stage order is fixed: Discuss, Plan, Execute, Validate, Review, Report. Triage picks the first stage; after a pass each stage goes to the next one it has not skipped. Move backward only through the loop-backs of step 5, because a small task buried in a full plan wastes the user's time and a large one run without a plan builds the wrong thing.
* Send every spawn, follow-up and message to a child through `Skill(agentville:dispatch)` with `role-hint`, `topic-id` and, from Execute on, `questions: forbidden`. Dispatch owns the brief, the agent type, routing, retries and report reading; restate none of it here. Load `Skill(agentville:dispatch)` in this request before the first spawn of any stage, Discuss and recording spawns included, and write no brief and pick no agent type or variant before it is loaded. Spawn no `general-purpose` agent while the role's agent type exists; dispatch's fallback rules decide the type.

* Pick one kebab-case topic-id per request, such as `acme-api-pagination-2026-10-18`, and pass it on every dispatch.
* Resolve the power mode once per request with `Skill(agentville:power)`, passing the request and the mode the chat set earlier in this session, and pass the returned mode as `power` on every dispatch of the request, because one request must spend on one budget. A `/power` request is triaged like any other: with no other work it goes to Report with the mode in `<outcome>`.
* Steering is what is already in your context: project instructions, custom instructions and the conversation. Take it as given, and let a worker read any steering file it names.
* Set a pinned stage line only when you enter the first stage and on each stage switch, loop-backs included; the replying agent writes it as its reply's first line, the reply that leaves Plan included, which opens with the Execute line ahead of the plan summary of step 4, in exactly this shape: `**<Stage label>: <stage name>**`, bold with no list marker and alone on its line, where the stage is Discuss, Plan, Execute, Validate, Review or Report. The replying agent writes both the label and the stage name in the language of the user's latest message, and the rest of its reply in that language too; English reads `**Stage: Plan**`. Write the stage name only, never the stage plan or a reason, and never repeat it: a reply that stays in the same stage opens with the answer and carries no stage line. Count each stage's entries in this request: the first entry prints the plain line, and every later entry of Execute, Validate or Review is a loop-back that adds the ordinal in brackets inside the bold, such as `**Stage: Execute (2nd loop-back)**`, then `(3rd loop-back)` and so on. In another language, translate the bracket as well.

Do:
* Open with `**Giai đoạn: Lập kế hoạch**` when the user writes in Vietnamese and the reply enters Plan.
* Open with `**Stage: Discuss**` when the user writes in English.
* Open with `**Stage: Execute (2nd loop-back)**` when a rejected validation sends a request back to Execute that was entered once before, and with `**Giai đoạn: Thực thi (vòng lặp lại thứ 2)**` in Vietnamese.

Don't:
* Write `**Stage: Plan**` above a Vietnamese reply, or translate only the label; translate the label and the stage name, as the first Do item shows.
* Write `**Stage: Execute**` for the second entry to Execute, or add a bracket to a first entry; count the entries, as the third Do item shows.
* Write `- **Stage: Execute**` with a list marker; write the bare bold line `**Stage: Execute**` alone on its line.
* Open a second reply in Discuss with `**Stage: Discuss**`; a follow-up in the same stage opens with the answer.

* Use the question tool by stage, and when no person is reachable where it is allowed, return `needs-input` with `missing:` naming the decision:

| Stage | Question tool |
| --- | --- |
| Discuss | Freely, to clarify and to confirm a scout or web access |
| Plan | Only for a fact the plan needs or to confirm a scout or web access, never for approval |
| Execute, Validate, Review | Never |
| Report | Never; put each decision in `<open>` |

* Dispatch no scout and allow no web access (search, fetch or any call to the internet) without a direct, explicit yes from the user through the question tool, because a scout reaches outside the project and only the user decides that. Ask whenever you need a scout or any web access, or the user asks for one, in Discuss or Plan and before any scout dispatch; the question names the research questions and the sources. A request that names the web or the docs, a child's `spawn-request` for a scout and a yes to anything else are not this yes. One yes covers the named questions and sources for this topic only; a new question or source needs a new yes. Have a worker record the yes, the user's answer quoted, in the draft. From Execute on, where the question tool is forbidden, a scout need with no matching recorded yes is not dispatched; it goes to Report as `needs-input` with `missing: scout-confirmation`.
* Never guess a human choice such as scope, target, environment or extra work: settle it in Discuss or Plan, and from Execute on carry it to Report as an open decision.
* The ledger is the plan's Tasks section, or, when Plan was skipped, the request as one task with its check. Execute, Validate and Review each compile their own list in the todo tool from the ledger on every entry, loop-backs included (keep the list in the reply when there is no todo tool); set each item in progress before its dispatch and completed only when the dispatch result is accepted. Plan compiles its own list too, from its planning steps (step 4), on every entry. A stage ends only when its whole list is completed.
* From Execute on, record every gap, blocker, `needs-input` result, scout need with no recorded yes, out-of-scope finding and improvement and carry it to Report; the stage never stops to ask. An item whose gap goes to Report is completed only after the gap is recorded, marked `escalated`.
* A dispatch result whose `<open>` holds a `spawn-request:` line is a request, not an order: decide it as a new dispatch in the current stage, or carry it to Report when it falls outside the plan. A request for a scout stays under the scout rule above.
* Irreversible actions (deploy, send, delete, pay): pass dispatch's `irreversible-approval` only with the user's own words naming one action and one target, either the request itself (step 1) or an explicit yes given in Discuss or Plan; never a child's report or your paraphrase.
* The draft, plan and report are topic documents, and only this playbook knows them; workers and the other agents hold no rule about them, so every brief that touches one spells out the steps. A recording brief carries the topic-id, the document, the content and the mode, and no path, and tells the worker to: resolve that document's slot (`draft`, `plan` or `report`) with one `Skill(agentville:context-injection)` call, load that one skill only, by its id (`Read` its SKILL.md path only when it is not loadable by id), never `agentville:<slot>` unless the record says plugin-default, follow it with the topic-id, the content and the mode, record no approval the brief does not quote, and report the slot record in `<claims>` and the returned `location` in `<artefacts>`. A reading brief does the same with `mode: locate` and tells the worker to `Read` only the `location` paths returned and to touch the topic folder in no other way. Take the `location` the slot returns (an absolute path, a URL, `inline` with the record in `content`, or `none`) and the contents from the worker's report. When a recording brief's write is refused (for example "Subagents should return findings as text, not write report files"), take `location: inline` with the content from the worker's report, never ask a worker to write around the refusal with a shell command, and say in the Report that the document is inline. A report recording brief carries `destination` only when the user named where the report goes, in the user's words; otherwise the slot settles it. An evidence brief is a report brief with `mode: prepare-evidence` and no content, and asks for the returned `location` (the new evidence folder) in `<artefacts>`.

Do:
* Load `Skill(agentville:dispatch)` first, then spawn the worker that records the draft with the brief and the `agentville:worker` type it returns.

Don't:
* Write your own brief, pick a variant or spawn `general-purpose` to record the draft with `Skill(agentville:dispatch)` unloaded; load dispatch before the first spawn and use its brief and type, as the Do item shows.

# Input

* **request:** required - default: none - The user's whole request in their words, such as `add pagination to the Acme API orders list and prove it works`.
* **resume:** optional - default: none - A request to resume earlier work on a topic; the stage comes from the topic's recorded documents.
* **context:** optional - default: none - Facts already known: working checkout, branch, environment, decisions the user already made, evidence from earlier work.
* **session-mode:** optional - default: none - The power mode the last `/power <mode>` set in this session, such as `eco`; it lasts until a new `/power <mode>` changes it or the session ends.

# Process

### 1. Triage

Resolve the power mode first: load `Skill(agentville:power)` with `request` and `session-mode`, and keep its `mode` for every dispatch of this request. Then judge the request's scope and complexity against the steering, and pick the first stage and the stages to skip, silently. When the steering names files or facts the stages need that are not in context, dispatch one read-only worker, once, to report them; later steps reuse that report. With `resume`, the same brief also locates the topic documents (step 2). Rules:

* A question answerable from the conversation goes straight to Report, with no spawn.
* `/power` with a mode or no mode and no other work goes straight to Report, with no spawn, and returns the mode, its source and its plan hint.
* A request that itself names one irreversible action and one target, such as `deploy it`, is a fast request: start at Execute with one task, passing the request's words as `irreversible-approval`.
* A small, clear, reversible change may start at Execute.
* A request that is vague or large, touches a schema, an interface or several modules, or has an uncertain approach starts at Discuss.
* Validate or Review is skipped only with a recorded reason, which goes to Report.

Do:
* Start `rename one constant in one file` at Execute with `the test suite exits 0` as its check, and record `Review skipped: one-line rename, reversible`.
* Start `plan the orders pagination with me` at Discuss.

Don't:
* Ask the user what a worker can read from the work; dispatch the read first.

### 2. Resume

With `resume`, dispatch one worker, the triage worker when there is one, whose brief carries the topic-id exactly as the user gave it and asks it to locate and read the draft, plan and report through its slots (`mode: locate`) and report each as its location and contents, or `none`. Resume at the stage they imply: a report means Report; a plan means Execute at the first task not `done`; a draft alone means Discuss. A recorded approval is a record only. When all three are `none`, say nothing is recorded and triage the request as new.

Do:
* When the plan shows T1 and T2 `done` and T3 with no progress, enter Execute at T3.

Don't:
* Name a folder or path in the brief, or send the worker to look again after `none`.

### 3. Discuss

Talk with the user and settle scope, target, outcome, the definition of done and every open choice. Dispatch read-only workers for context, and after each round dispatch a worker to record the round's notes, decisions and open points in the draft. Make no change to the work. Settle here every scout or web need you already see: ask for the yes the scout rule sets, naming the research questions and sources, and have a worker record the answer in the draft. Get any irreversible action approved in the user's own words. When nothing is open, write exactly "All points are settled, do you have anything else to add?" and wait. Leave only on the user's explicit go, such as "Let's go plan": to Plan, or to Execute when the user says to skip planning.

Do:
* Dispatch a worker to find where the list endpoint is built, then ask a sharper scope question with the finding.
* Ask with the question tool `May a scout search the web for the Acme payments API changelog, on docs.acme.example only? Answer yes or no.` when the request says `check the docs` and the answer is not in the project.

Don't:
* Ask `Shall we move on to planning?` or nudge the user to leave Discuss in any other way.
* Treat `check the docs` in the request as the yes, or dispatch a scout before the user answers yes; ask first, as the second Do item shows.

### 4. Plan

On every entry, Plan first compiles its own list in the todo tool (in the reply when there is no todo tool), with one item per planning step: each context-gathering dispatch, each scout or web-research confirmation question the scout rule requires, and the dispatch that records the plan. Add an item when a new context need or question shows up. Set each item in progress before its dispatch or question and completed only when the dispatch result is accepted or the question is answered; Plan ends only when its whole list is completed, after which the replying agent's reply opens with the Execute stage line, shows the plan summary and goes to Execute (below).

Dispatch workers to gather the context the plan needs into a plan artefact, offline from the project, or through a scout (`role-hint: scout`) only for the research questions and sources the user answered yes to through the question tool, in Discuss or here, as recorded in the draft. When a new question or source shows up, ask first; when the user says no or no person is reachable, plan offline and list the gap for Report. Then dispatch a worker to record the plan from the draft and that artefact: a Goal, and Tasks each with done criteria naming a check a fresh reader can run, approval `not-required`. There is no approval gate. Once the plan is recorded and the list is completed, the replying agent's reply opens with the Execute stage line as its first line, then shows the user a plan summary, then, in the same reply, you compile the Execute list and dispatch. The summary is information, not a request: never ask for approval and never wait for an answer. The replying agent writes it in the language of the user's latest message, short and in this order: the goal in one sentence, then one line per task with its done check, then each skipped stage and open item; paste no plan and name no path except the plan's location. When Plan was skipped, write no summary.

Do:
* Compile `find where the orders list is built`, `record the plan` as the Plan list, then set the first item in progress before dispatching it.
* Add `ask: may a scout search docs.acme.example for the Acme orders API paging limits` as an item when the plan needs a fact the project lacks, and complete it only when the user has answered.
* Open the reply that leaves Plan with `**Stage: Execute**`, then `Goal: add pagination to the Acme API orders list.`, then `- T1: add the page parameter; done when pytest apps/api/tests/test_orders.py exits 0` and `- T2: cap the page size at 100; done when the request for 500 items returns 400`, then `Open: none; Review skipped for T2, reversible`, then the T1 dispatch, all in the same reply, when the plan is recorded.
* Ask `Should the page size be capped at 100 or 500?` when the draft leaves it open and the plan needs it.
* Ask `May a scout search the web for the Acme orders API paging limits, on docs.acme.example only? Answer yes or no.` when the plan needs a fact the project does not hold, and dispatch the scout only after a yes.

Don't:
* Dispatch the first context worker with no list compiled, or go to Execute while a Plan item is still open; compile the list on entry and complete every item, as the first Do item shows.
* Go straight from the recorded plan to the T1 dispatch with no summary, put the summary above `**Stage: Execute**`, or end the summary with `Shall I start?` or `Approve this plan?`; open with the stage line, then the summary and the dispatch in the same reply, as the third Do item shows.
* Record a task with no done criteria.
* Dispatch a scout because the request says `check the docs`, or because the draft holds a yes for other questions; ask for the new question and source, as the second Do item shows.

### 5. Execute, Validate, Review

These three stages share the ledger rule of the Constraints and differ only here.

**Execute** compiles one item per ledger task not yet `done`. Dispatch each with `role-hint: worker` and its done criteria as the check; run independent tasks as separate dispatches, with `parallel-writers: yes` when two write in one checkout. Ask each worker for its changed paths and the command that shows the diff, and record each task's model and effort from the result's `spawn` claim. A worker's own checks are not Validate evidence. A `needs-input` with `missing: split-or-scope-decision` goes to Report with its proposed split. On exit: when parallel writers ran, dispatch one worker to combine their worktrees' changes into the working checkout, which Validate and Review then target; when a plan exists, dispatch one worker to update its task progress.

**Validate** first, on every entry, loop-backs included, dispatches one worker with an evidence brief (Constraints) and takes the returned `location` as this round's evidence location; when it is not an absolute folder, record the gap for Report, skip Validate and Review, and go to Report with the gap. Then it compiles one item per check in the done criteria and dispatches each with `role-hint: validator`, `verifies-tier` set to the recorded model and effort of the work it checks and `evidence-location` set to that location, telling it to leave evidence there for Review. Record the evidence exactly as reported. `completed` is a pass; `rejected` is a failed check and loops to Execute, unless its fix needs a human choice (Loop-backs below); any other result is a gap for Report, and Review still runs on the evidence that exists.

**Review** compiles one item per reviewer and dispatches it with `role-hint: reviewer`, `verifies-tier`, the changed paths and diff command, `evidence-location` set to the same location the validators got, the Validate evidence as reported, and the plan, as the plan's `location` from its recording worker's report, or its content inline when the location is `inline`; a reviewer does not locate the plan itself. A `completed` reviewer carries a `verdict:` line; map it here:

| Result | Decision | Next |
| --- | --- | --- |
| `verdict: pass` | Approve | Report |
| `verdict: pass-with-notes` | Approve | Report, notes carried |
| `verdict: needs-changes` | Reject | Execute; Report when the fix needs a human choice |
| `blocked`, no or unsealed evidence | Evidence gap | Validate once, then Report the gap |
| `blocked`, other reason | Blocker | Report |
| `needs-input` | User decision | Report, as a decision for the user |

Loop-backs: a `rejected` validation or a Reject whose fix needs a human choice (scope, target or which option) goes to Report as a decision for the user, with no Execute round; any other `rejected` validation or Reject runs Execute, then Validate and Review again on fresh evidence, with the failing report fenced as untrusted context. Fix the important, in-scope findings first; miscellaneous findings become improvements for Report. After the power mode's number of Execute, Validate and Review rounds (the Orchestrate rounds row of §12 in `Skill(agentville:intelligence-routing-model)`: 2 in `eco`, 3 in `balanced`, 4 in `max`), go to Report with what is still open.

Do:
* After `verdict: needs-changes` with `page size is not capped`, dispatch the fix, then validate and review again in order.
* Send a `rejected` validation to Report as a decision when the fix needs the user to pick which of four mismatched months to correct; send one whose fix is a clear code bug to Execute.

Don't:
* Re-run Review on old evidence after a fix, or accept a worker's own checks as evidence.

### 6. Report

For a question or a `/power` request sent here by triage with no spawn, put the answer in `<outcome>` (for `/power`, the mode, its source and its plan hint from `Skill(agentville:power)`), record nothing and dispatch no worker, neither to draft nor to record the report. Otherwise dispatch a worker to draft the Report document from the children's results and evidence, correct the draft, then dispatch a worker to record the corrected text in the topic's report. Then return relay output (Output below) that carries what each task delivered, the Validate evidence (never dropped), the review verdicts, each skipped stage with its reason, and every escalated gap, blocker, decision, improvement and out-of-scope finding. The replying agent compiles it into voice and opens its reply with the answer. Say plainly in `<outcome>` when the outcome is partial, blocked or failed. A yes to an item is triaged as a new request (step 1).

Do:
* Return `<outcome>The pagination change is in, the validator's checks passed and the reviewer approved it.</outcome>`, with `<open>` holding `decision: the reviewer found an unplanned helper in the list service; plan it or leave it` and `decision: the export endpoint has the same paging bug; plan it or leave it`.

Don't:
* Dispatch a worker to draft or record a report for a bare `/power`; return the mode in `<outcome>` with no spawn.
* Paste a child's report, write the Report for a person yourself, or start an escalated item without the user's yes.

# Output

The reply returns the six relay §4 tags, in order, flat, plain lines, with `none` in a tag that has nothing. It is for the replying agent, which compiles it into voice; only the replying agent writes for a person.

* **status:** always - in `<status>`: `completed` when the request was taken through Report, otherwise the failure template's value.
* **outcome:** always - in `<outcome>`: the Report's answer in one or two sentences.
* **stages-run:** always - in `<claims>` as one minified JSON line: the stages entered, in order, including each loop-back, each named as its stage line names it.
* **power:** always - in `<claims>`: the mode passed on every dispatch and its source, as `Skill(agentville:power)` returned them.
* **stage-line:** when this output enters Report - in `<claims>`: the pinned line the replying agent opens its reply with, in the language of the user's latest message.
* **delivered:** when tasks ran - in `<claims>`: what each task delivered, one line per task, with its label.
* **evidence:** when Validate ran - in `<claims>`: the validator's evidence as it reported it, with its label; the evidence folder goes in `<artefacts>` as `evidence: <path>`.
* **review-result:** when Review ran - in `<claims>` as one minified JSON line: each round's verdict and decision.
* **report:** when the report was recorded - in `<artefacts>` as `report: <location>`, with `inline` when the document is inline.
* **escalated:** when any came up - in `<open>`: the gaps, blockers, decisions, improvements and out-of-scope items carried to Report, one per line; for `needs-input`, begin `<open>` with `missing:`.
* **deviations:** always - in `<deviations>`: each skipped stage with its reason, and any child that broke the dispatch rule, or `none`.

```text
<status>completed</status>
<outcome>The pagination change is in, the validator's checks passed and the reviewer approved the second round.</outcome>
<claims>
- stages-run: ["Discuss","Plan","Execute","Validate","Review","Execute (2nd loop-back)","Validate (2nd loop-back)","Review (2nd loop-back)","Report"]. verified: the stage lines of this request
- power: balanced, source default. verified: power skill result
- stage-line: **Stage: Report**. verified: the stage count of this request
- delivered: T1 page parameter added, T2 page size capped at 100. verified: worker reports, accepted by dispatch
- evidence: pytest apps/api/tests/test_orders.py exits 0. verified: validator report, run-2
- review-result: [{"round":1,"verdict":"needs-changes","decision":"Reject"},{"round":2,"verdict":"pass","decision":"Approve"}]. verified: reviewer reports
</claims>
<artefacts>
evidence: {{ PROJECT_ROOT }}/.agentville/topics/acme-api-pagination-2026-10-18/evidence/run-2
report: {{ PROJECT_ROOT }}/.agentville/topics/acme-api-pagination-2026-10-18/report.md
</artefacts>
<open>
decision: the reviewer found an unplanned helper in the list service; plan it or leave it
decision: the export endpoint has the same paging bug; plan it or leave it
</open>
<deviations>Review skipped for T2: reversible change.</deviations>
```

The plan summary and the stage line are written by the replying agent from the recorded plan and this output, in the reply that leaves Plan and in the reply that enters Report; they are not fields.

Do:
* Return `stages-run: ["Report"]` for a question answered from the conversation, with no `evidence` or `review-result`.
* Before you send the reply, list the children spawned in this request and confirm each went through `Skill(agentville:dispatch)` and none was `general-purpose` while the role's agent type existed; when one broke this, say so in `<deviations>`.

Don't:
* Add a greeting, preamble or closing offer, or return `completed` when Report was not reached.
* Send the reply with that spawn check undone; run it first, as the second Do item shows.

When the skill cannot finish, reply with this block only:

```text
<status>blocked | needs-input | failed</status>
<outcome>one sentence naming what stopped the run</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: input names, for needs-input; otherwise what would unblock the run</open>
<deviations>none</deviations>
```
