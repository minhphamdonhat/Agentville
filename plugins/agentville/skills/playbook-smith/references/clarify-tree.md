# Playbook clarify tree

Read by SKILL.md step 3. It lists the decisions that settle a playbook's contract, the order in which to ask them, the question shape and the confirmation. The fixed machinery of `{{ SKILL_ROOT }}/references/playbook-machinery.md` (M1 to M13) is never asked: it goes into every playbook as written.

## Slots

A slot here is one decision of the playbook's contract, not an injectable slot. It is settled when the user has answered it or accepted its recommended answer, or when it does not apply (`n/a`). With `seed: orchestrate`, each recommended answer is orchestrate's value, from the Settled parts of the machinery file; with `seed: fresh`, it comes from the request.

| Slot | Prerequisites | What it settles | Recommended answer |
| --- | --- | --- | --- |
| playbook-name | none | The skill name, kebab-case, at most 64 characters | From the request, such as `acme-docs-release` |
| purpose | playbook-name | What kind of request the playbook takes and what it returns, in one sentence | From the request |
| stages | purpose | The stage names and their fixed order (S1); the last stage returns the relay output | orchestrate's six stages, trimmed to what the purpose needs |
| triage | stages | Which stage each kind of request enters at, and which stages may be skipped and with what recorded reason (S2) | One rule per entry stage, plus "a question answerable from the conversation goes straight to the last stage" |
| exit-rules | stages | For each stage, the condition that ends it and the stage it goes to (S3) | "Its whole todo list is completed", plus an explicit user go for a talking stage |
| question-table | stages | One row per stage: freely, only for named needs, or never (S4); the last stage is always never | Freely before the first working stage; never from it on |
| slots-recorded | stages | Which of draft, plan and report the playbook records, and in which stage each is written or read (S5) | Draft in a talking stage, plan in a planning stage, report in the last stage |
| loop-backs | stages, exit-rules | Which results send work back to which earlier stage, the cap on rounds and what goes to the last stage when the cap is hit (S6) | A rejected check loops to the working stage, at most 3 rounds |
| output-extras | stages, slots-recorded | Fields the last stage returns beyond `status`, `outcome`, `stages-run`, `escalated` and `deviations` (S7) | `stage-line`, `delivered`, plus `evidence` and `review-result` when those stages exist |
| stage-label | stages | The English stage-line label, such as `Stage`; the replying agent translates it | `Stage` |

Settle the install `scope` (project or user) outside this tree: SKILL.md step 1 owns it.

## Checks on the answers

Before the confirmation round, check the answers against the machinery and ask again when one breaks it:

* The stage order is one sequence with no branch; a backward move appears only in `loop-backs`.
* Every stage in `stages` has an exit rule and a question-table row.
* A stage that spawns writers compiles a todo list from the ledger (M6); a planning stage compiles its own.
* A stage that needs a scout or web access sits where the question tool is allowed, or the playbook carries the scout need to the last stage (M3).
* Every slot in `slots-recorded` is written and read through a recording or reading brief (M4).
* Every loop-back has a cap, and a loop-back whose fix needs a human choice goes to the last stage instead.

## Frontier order

Ask the open slots whose prerequisites are settled, in this order, at most four questions per `AskUserQuestion` call:

1. playbook-name, purpose and stages.
2. triage, exit-rules and question-table.
3. slots-recorded and loop-backs.
4. output-extras and stage-label.

## Question shape

* Ask one numbered question per slot: `<n>. <slot>: <question>`.
* Make option 1 the recommended answer, labelled "(Recommended)", and quote its value in full, such as `stages: Plan, Execute, Validate, Report`. Follow it with one to three alternatives.
* Look a fact up with `Read` before asking; ask only decisions.
* For an improve, ask only the slots the change touches; every other slot keeps the value read from the existing playbook.
* After the last round, show the whole contract as `<slot>: <value>` lines, in the table's order, followed by the line `fixed: M1 to M13 as written`, and ask "Build it?" with the options "Yes, build it (Recommended)" and "Change something". Ask nothing further after a yes.
* When no person is reachable, do not ask: return `<status>needs-input</status>` with the unsettled slots after `missing:` in `<open>` and the questions in `<outcome>`.
