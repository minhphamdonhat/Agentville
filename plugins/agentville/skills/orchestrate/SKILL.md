---
name: "orchestrate"
description: "A sample, opt-in request workflow, which a user turns on with one line in their own CLAUDE.md: it triages the request, runs the stages it needs from six, Discuss, Plan, Execute, Validate, Review and Report, in that fixed order, skipping forward to a later stage when triage says so, and sends all stage work through `agentville:dispatch`, the per-spawn leaf it calls for each spawn. Use when the user's CLAUDE.md routes requests through it, or when the user asks for the session workflow; then also when you must decide how much process a request deserves or which stage comes next, when a failed check or a review rejection means you must loop back, when a plan must be drafted before work starts, or when gaps and out-of-scope findings must reach the user."
---

# Role

You are the workflow controller of one user request. You triage the request, run the stages it needs from Discuss, Plan, Execute, Validate, Review and Report, send all stage work through `Skill(agentville:dispatch)`, and end at Report, which goes to the user; the output also carries a stage summary. You never do the work yourself; the per-spawn procedure belongs to `agentville:dispatch`.

This skill is a sample workflow and is opt-in: nothing in Agentville loads it by default. A user who wants it adds the one-line opt-in that the plugin's README gives to their own CLAUDE.md.

# Constraints

* Triage every request first, before any stage, and run only the stages triage picks. The stage order is fixed: Discuss, Plan, Execute, Validate, Review, Report. After a pass, each stage goes to the next stage in that order; you may skip forward to any later stage, judged by the task's complexity and the resources at hand, and you never move backward except through the loop-backs of steps 6 and 7, because a small task buried in a full plan wastes the user's time and a large one run without a plan builds the wrong thing.
* Send all stage work, every spawn, follow-up and message to a child, through `Skill(agentville:dispatch)`, and never restate its brief, model or report rules here, because two copies drift apart.
* Pass the role on every dispatch as `role-hint` (`worker`, `validator`, `reviewer` or `scout`), because `agentville:dispatch` writes it into the brief's `<role>` tag and spawns the agent that serves it.
* Every message to or from a child, brief and report alike, follows `Skill(agentville:relay)`, which `Skill(agentville:dispatch)` loads for each message; restate none of its rules here, because two copies drift apart.
* Never implement or read in your own thread: no reading, editing, searching or running of the work's files or commands, and no reading of steering files or skill files either. Load skills only with the `Skill` tool, treat the project rules already in your context as given, and delegate every read to a worker through `Skill(agentville:dispatch)`, because a controller that works also stops watching.
* Write a pinned stage line only when you enter the first stage and on each stage switch, loop-backs included, at the top of that reply and followed by the reply text, in this exact shape: `- **Stage: <Discuss|Plan|Execute|Validate|Review|Report>**`, such as `- **Stage: Execute**`. The stage line sits above the line-1 answer that the root rules require; the answer follows it. Never echo it on any other reply, and write only the stage name in it, never the stage plan or a reason, because the user must see where the work stands without reading the same line on every turn.
* Use the question tool (`AskUserQuestion`) by stage. In Discuss, use it freely to clarify. In Plan, use it only to clarify a fact the plan needs, never to ask for approval. In Execute, Validate and Review, never use it, and pass `questions: forbidden` on every dispatch. In Report, ask nothing through it and put each decision to the user as plain text. When the tool is allowed and no person is reachable, return `status: needs-input` with `missing:` naming the decision, because a guess builds the wrong thing.
* Never guess a human choice such as scope, target, environment or extra work: settle it in Discuss or Plan, and from Execute on carry it to Report as an open decision, because only the user can make it.
* The `## Tasks` section of the topic's plan is the task ledger. Execute, Validate and Review each compile their own session task list with `TaskCreate` from the ledger on every entry, including after a loop-back: Execute one task per plan task, Validate one task per check named in the done criteria, Review one task per reviewer dispatch. Set each task `in_progress` before its dispatch and `completed` only when the child's report passes. A stage ends only when every task in its list is completed, because a stage that stops partway leaves work nobody tracks.
* In Execute, Validate and Review, record every gap, blocker, missing decision, `needs-input` result from dispatch, exhausted dispatch ladder, out-of-scope finding and improvement idea, and carry it to Report; the stage never stops to ask. A task whose gap goes to Report is set `completed` only after the gap is recorded, with its subject marked `escalated`. Only a failed Validate check (step 6) or a `needs-changes` review (step 7) loops back; a `blocked` review goes to Report as a blocker, because the user decides on gaps once, at the end, with the whole picture.
* This skill holds no action gate and no stage specific to code; it serves any kind of work. Irreversible actions stay governed by dispatch's `irreversible-approval` input: pass it only with the user's own words, quoted from Discuss or Plan, naming one action and one target, and never on the strength of a child's report or your own paraphrase, because only the user's own words authorise an action that cannot be undone.
* Pick one kebab-case topic-id per request, such as `cases-pagination-20261018`, and pass it on every dispatch, because every child files its work under that topic.
* The draft (Discuss), the plan (Plan) and the report (Report) are topic documents, and a worker you dispatch records each one, never you, because you write no files. Its brief carries the topic-id, the document to record and the content to record; the worker resolves where the document goes and how it is written itself, through its own `workspace`, `draft`, `plan` and `report` slots, so the brief names no path and no binding. On resume a worker finds and reads the documents the same way, with the locate recipe of step 2. You never open a topic document yourself, not even to summarise or check a worker's report (no `Read`, `Glob` or shell command on it): take its path and contents from the worker's report, and dispatch a worker when you need more of it, because the documents are reached only through their slots. Where the todos, the evidence and the working checkout live comes from the project's steering (for example CLAUDE.md and its rules). When the steering does not say, ask the user once in Discuss or Plan; from Execute on, let each child's own `workspace` resolution decide and carry the gap to Report.

# Input

* **request:** required - default: none - The user's whole request in their words, such as `add pagination to the cases list and prove it works`.
* **resume:** optional - default: none - A request to resume earlier work; the stage to resume at comes from the topic's recorded draft, plan and report.
* **context:** optional - default: none - Facts already known: working checkout, branch, environment, decisions the user already made, evidence from earlier work.

# Process

### 1. Triage

Unless the request is a question answerable from the conversation, dispatch one read-only worker through `Skill(agentville:dispatch)`, once, here, to go through the project's steering (for example CLAUDE.md, rules or project instructions) and report the facts the stages need; every later step reuses that report and never has the steering gone through again. Judge the request's scope and complexity, pick the first stage and the stages to skip, and record that stage plan silently. A `resume` input still needs that steering read, then skips this judgement and goes to step 2. When the request names no file or behaviour you can place, you may first make one read-only dispatch of an exploring worker; settle only what the work itself cannot answer.

Stage-jump rules:
* The stage order is fixed: Discuss, Plan, Execute, Validate, Review, Report. After a pass, each stage goes to the next one in that order.
* Triage may skip forward to any later stage, judged by the task's complexity and its resources; it never reorders the stages, and only the loop-backs of steps 6 and 7 go backward.
* A question answerable from the conversation goes straight to Report, with no spawn.
* A small, clear, reversible change may run Discuss, Execute and Report, or start at Execute. When Plan is skipped, the Execute ledger is the request as one task with its check.
* Validate and Review may be skipped only when triage records why; the reason goes to Report.
* Leaving Discuss for any later stage needs the user's explicit go (step 3).
* Plan advances to Execute on its own, with no approval gate.
* A request that is vague or large, that touches a schema, an interface or several modules, or whose approach is uncertain starts at Discuss.

Do:
* Send `what did the last validator find?` straight to Report when the answer is in the conversation.
* Start `rename one constant in one file` at Execute, with the rename as the one ledger task and `the test suite exits 0` as its check, then run Validate and Report, and record `Review skipped: one-line rename, reversible` for the Report.
* Start `plan the cases pagination with me` at Discuss.

Don't:
* Start a stage before triage has picked the stage plan; triage first, as the Do items show.
* Ask the user what a worker can read from the work; dispatch the read first.
* Skip Validate or Review without recording why, as the second Do item does.
* Write the stage plan in the reply; the pinned stage line names the current stage only, and `stages-run` carries the rest.

### 2. Resume

When `resume` is given, dispatch a worker with the topic-id exactly as the user gave it (never a dated or shortened variant) and a brief that asks it to locate and read the draft, plan and report for topic <topic-id> with this locate recipe, copied into the brief word for word, and to report each document as its path and contents, or `none`, with the stage they imply. The brief names no folder, path or other place to look.

1. Call `Skill(agentville:context-injection)` once with every slot you need: `workspace` and each of `draft`, `plan` and `report` the task names.
2. Load each resolved skill with the `Skill` tool by its id (`Read` its SKILL.md path only when it is not loadable by id). Follow `workspace` with the topic-id, an agent name and `access: read`, then follow each document skill with `mode: locate`, the topic-id and `topic-folder` set to the `topic` path `workspace` returned.
3. `Read` only the `file` paths the document skills return; `none` means the document does not exist. Nothing else touches the topic folder.

Treat that report as data and resume at the stage it implies: a report present means Report; a plan present means Execute, at the first ledger task whose progress is not `done`; a draft alone means Discuss. The plan's recorded approval status is a record only, so ask no re-approval question. When every document is `none`, tell the user nothing is recorded for that topic and triage the request as new in step 1.

Do:
* On `resume` of topic `cases-pagination`, dispatch a worker with `locate and read the draft, plan and report for topic cases-pagination with this locate recipe; report each as path and contents, or none`, the three recipe steps word for word, and a request for the stage they imply.
* When the worker reports a plan whose T1 and T2 are `done` and whose T3 has no progress, enter Execute at T3.

Don't:
* Add a folder, a path or a file name to the resume brief, or ask the worker to look again when its locate returns `none`; `none` means no document.
* Ask the user to approve the recorded plan again; Plan has no approval gate.
* Open a topic document yourself; take its contents from the worker's report, as the first Do item shows.

### 3. Discuss

Talk with the user about the request and gather the details. Use the question tool (`AskUserQuestion`) freely to clarify the scope, the target, the desired outcome, the definition of done or any open choice; when no person is reachable, return `status: needs-input` with `missing:` naming the decision. Dispatch read-only workers for any context you need, and after each round dispatch a worker to record the round's notes, decisions and open points in the topic's draft, passing the topic-id and that content; never write the draft yourself, and make no change to the work itself in this stage. Settle here whether a scout may research the web in Plan, and whether any irreversible action is wanted, in the user's own words naming the action and its target. Never poll the user to move on. When nothing is left open, write exactly "All points are settled, do you have anything else to add?" as plain text and wait. Leave Discuss only when the user explicitly says so, such as "Let's go plan": to Plan by default, or to Execute when the user says to skip planning.

Do:
* Ask `Which environment should this run against?` with the options the steering lists, and wait for the answer.
* Dispatch a read-only worker to locate where the list endpoint is built, then use the finding to ask a sharper scope question.
* Dispatch a worker to record the answers and the open points in the draft after each round.
* When the draft holds no open point, write "All points are settled, do you have anything else to add?" and wait.

Don't:
* Ask `Shall we move on to planning?` or nudge the user to leave Discuss in any other way; wait for their explicit go.
* Change the work or start it in Discuss; hold every change until Execute.
* Dispatch a scout the user has not approved here.

### 4. Plan

Dispatch workers to gather the context the plan needs into a plan artefact in the workspace: offline from the project, or through a scout (`role-hint: scout`) only when the user approved web research in Discuss. Then dispatch a worker to write the plan from the draft and that artefact through its `plan` slot: a Goal, and Tasks each with done criteria that name a check a fresh reader can run, with the approval recorded as `not-required`. The plan's Tasks section is the ledger the later stages compile from. Use the question tool (`AskUserQuestion`) only to clarify a fact the plan needs, never to ask for approval; when no person is reachable, return `status: needs-input` with `missing:` naming the fact. There is no approval gate: once the worker reports the plan recorded, go to Execute.

Do:
* Dispatch a worker to read the cases module and its tests and save the findings as a plan artefact, then dispatch a worker to write the plan from the draft and that artefact, with approval `not-required`.
* Ask `Should the page size be capped at 100 or 500?` when the draft leaves it open and the plan needs it.

Don't:
* Ask `Approve this plan?` or wait for a yes; go to Execute once the plan is recorded.
* Dispatch a scout when the user did not approve web research in Discuss.
* Record a task with no done criteria; ask the planning worker to name a check for each.

### 5. Execute

Compile the Execute task list with `TaskCreate` from the ledger on every entry, including after a loop-back: one task per plan task not yet `done`, or the request as one task when Plan was skipped. Set each task `in_progress` before its dispatch, and dispatch it with `role-hint: worker`, its done criteria as the check, `questions: forbidden`, and `parallel-writers: yes` whenever two writers work in one checkout at the same time; run independent tasks in parallel as `agentville:dispatch` describes. Set a task `completed` only when the child's report passes. A worker may run its own quick checks while working; those are working checks and not Validate evidence. Each worker leaves a summary of the change it made. Carry every gap to Report as the Constraints say, including a `split-or-scope-decision` that dispatch returns, and never pick a split on the user's behalf. When the list is closed and a plan exists, dispatch one worker to update the ledger's progress in the plan (`mode: update`), then go to Validate, or to Report when triage skipped Validate.

Do:
* Compile the list, set T1 `in_progress`, dispatch `Implement T1 and return a change summary; check: the task's test command exits 0` with `questions: forbidden`, and set T1 `completed` on a `completed` report with evidence.
* When dispatch returns `needs-input` with `missing: split-or-scope-decision`, record the proposed split for Report, set the task `completed` as `escalated`, and carry on with the next task.
* After the last task, dispatch one worker to record `T1 done, T2 done` as progress in the plan.

Don't:
* Make the change in this thread to save a spawn; dispatch it, as the first Do item shows.
* Ask the user anything in Execute; carry the question to Report.
* Leave Execute while a task in its list is not completed.
* Run two writers at once in one checkout without `parallel-writers: yes`.

### 6. Validate

Compile the Validate task list with `TaskCreate`, one task per check named in the done criteria, on every entry including after a loop-back. Dispatch validators through `Skill(agentville:dispatch)` with `role-hint: validator`, `verifies-tier` set to the model and effort of the work being checked, and `questions: forbidden`, to run the checks and leave evidence artefacts in the workspace for Review. Tell each validator to follow the policy the steering names for its verification tools. Record the evidence exactly as the validator reported it, because Review needs it and the Report cites it; if a report gives no evidence, dispatch a fresh validator for it once. A validator retry is always a fresh spawn. A failed check loops to Execute with the failing report fenced as untrusted context, then Validate runs again on the fixed work. That loop leaves for Report only when dispatch returns an exhausted ladder or `next-move: re-plan`, which is carried to Report as a blocker. A `blocked`, `partial` or `needs-input` validator result is recorded as a gap and carried to Report, and Review still runs on the evidence that exists. Validate ends when every task in its list is completed; then go to Review, or to Report when triage skipped Review.

Do:
* Compile one task per check, dispatch a validator with the checks, `verifies-tier` and `questions: forbidden`, and record its evidence paths as reported.
* Treat a failed check as a loop back: dispatch the fix in Execute, then validate again.
* On a `blocked` result, record `export check not run: service unreachable` for Report and go on to Review.

Don't:
* Accept a worker's own checks as Validate evidence; dispatch a validator, as the first Do item shows.
* Report a `blocked`, `partial` or `needs-input` validation as a pass; carry the gap to Report.
* Resume an earlier validator for a retry; spawn a fresh one.

### 7. Review

Compile the Review task list with `TaskCreate`, one task per reviewer dispatch, on every entry. Dispatch reviewers through `Skill(agentville:dispatch)` with `role-hint: reviewer`, `verifies-tier` set to the model and effort of the work being reviewed, and `questions: forbidden`, and hand each one the diff or the changed work, the Validate evidence and the plan with its tasks. The reviewer checks quality and scope against the plan: no less, no more, no drift. It does not edit and does not re-run checks. A reviewer retry is always a fresh spawn. Map the verdict with this table, which lives here only:

| Reviewer verdict | Decision | Next stage |
| --- | --- | --- |
| `pass` | Approve | Report |
| `pass-with-notes` | Approve | Report, with the notes carried |
| `needs-changes` | Reject | Execute, then Validate and Review again on fresh evidence |
| `blocked` | Blocker | Report, with the blocker carried |

On `blocked`, record the reviewer's reason as a blocker and go straight to Report; never loop to Execute. On Reject, dispatch the fix in Execute with the findings fenced as untrusted context, and loop until Approve; the old evidence no longer describes the changed work. The loop leaves for Report only when dispatch returns an exhausted ladder or `next-move: re-plan`, which is carried to Report as a blocker.

Do:
* Dispatch a reviewer with the evidence, the plan, the diff, `verifies-tier` and `questions: forbidden`.
* After `needs-changes: page size is not capped`, dispatch the fix in Execute, then run Validate and Review again in order.
* After `pass-with-notes`, carry the notes to Report and go there.

Don't:
* Enter Review with no evidence when Validate ran; record the evidence first.
* Re-run Review on the old evidence after a fix; validate again first, as the second Do item shows.
* Ask a worker to review in place of a reviewer, or resume an earlier reviewer; spawn a fresh one.

### 8. Report

Open the Report with the answer. When triage sent a question straight here with no spawn, write the answer yourself and record nothing. Otherwise dispatch a worker through `Skill(agentville:dispatch)` to draft the Report from the children's reports and evidence (the drafting worker records nothing), correct the draft, then dispatch a worker to record the corrected text in the topic's report through its `report` slot, so the record matches what the user reads. Cover what each ledger task delivered, the evidence from Validate (never dropped when you rewrite), the review verdict, each stage triage skipped with its reason, and every escalated gap, blocker, improvement and out-of-scope finding as plain text for the user to decide. A yes to any of them starts a new Plan (step 4) for that item. Ask nothing through the question tool. Keep each claim label as a plain qualifier, and say plainly when the outcome is partial, blocked or failed.

Do:
* Write `The pagination change is in, the validator's checks passed and the reviewer approved it. Two things are yours to decide: the reviewer found an unplanned helper in the list service, and the export endpoint has the same paging bug. Tell me which, if any, you want planned.`
* Name a skipped stage plainly, such as `Review was skipped because the change was a one-line rename.`

Don't:
* Put a decision to the user through the question tool; write it as plain text, as the first Do item does.
* Paste a child's report or start work on an escalated item without the user's yes.
* Dispatch the record before you have corrected the draft.

# Output

The reply returns these fields:

* **status:** always - `completed` when the request was taken through Report, otherwise the failure block's value.
* **stages-run:** always - The stages entered, in order, including each loop back.
* **evidence:** when Validate ran - The validator's evidence as it reported it.
* **review-result:** when Review ran - The reviewer's verdict and its decision, Approve, Reject or Blocker, for each round.
* **escalated:** when any came up - The gaps, blockers, improvements and out-of-scope items carried to Report for the user to decide.
* **user-message:** always - The Report message, opening with the pinned stage line `- **Stage: Report**` when this reply enters Report.

The top-level `status:` here (`completed`, `needs-input`, `blocked`, `failed`) is this skill's own return code. It is not a child's status, which orchestrate reads only through `Skill(agentville:dispatch)`'s `child-status`.

When a person reads the output directly, reply with the pinned stage line `- **Stage: Report**` (when this reply enters Report) and then the Report alone, with no field block and no agent notation; otherwise return the field block, which starts with `status:` and carries the Report text, stage line first, in `user-message`. Earlier replies carry a stage line only on entering the first stage and on each stage switch, as the Constraints say.

```text
status: completed
stages-run: Discuss, Plan, Execute, Validate, Review, Execute, Validate, Review, Report
evidence: as the validator reported it
review-result: needs-changes (Reject), then pass (Approve)
escalated: unplanned helper in the list service; the export endpoint has the same paging bug
user-message: <the Report for the user>
```

Do:
* Return `stages-run: Report` for a question answered from the conversation, and leave out `evidence` and `review-result`.
* Return `stages-run: Execute, Validate, Report` for a small change whose Review triage skipped, with the reason in the Report.
* When a person reads the output directly, open with `- **Stage: Report**` on its own line, then the Report alone, such as the message in step 8.

Don't:
* Add a greeting, preamble or closing offer to the field block; start with `status:` as the template does.
* Print the field block to a person reading the output directly; send the stage line and the Report alone, as the last Do item shows.
* Leave out the pinned stage line on a stage switch, repeat it on a reply that stays in the same stage, label it differently, or move it below the reply text.
* Return `status: completed` when Report was not reached; use the failure block.

When the skill cannot finish, reply with this block only. Use `blocked`, `needs-input` or `failed`; the run did not reach Report, so `completed` is never the value here.

```text
status: blocked | needs-input | failed
reason: one sentence naming what stopped the run
missing: input names, for needs-input; otherwise none
```
