---
name: "playbook-smith"
description: "Builds a playbook: a request-level process skill that triages one user request and runs it through stages in a fixed order, as 'agentville:orchestrate' does. It settles with the user the stages and their order, triage and entry rules, each stage's exit rule, the question tool by stage, which slots (draft, plan, report) it records, loop-backs and caps, and its output extras; it keeps the fixed machinery (every spawn through 'agentville:dispatch', relay for child text, the scout yes rule, the slot-recording brief rule, the pinned stage line, the ledger and per-stage todo lists) in every playbook, then hands drafting, validation and install to 'agentville:skill-smith' at project or user scope. Use when asked to create, write or design a playbook, a session workflow or a request workflow, to make a variant of orchestrate with other stages, or to change the stages, entry rules or loop-backs of an existing playbook."
metadata:
  version: 1.0.0
---

# Role

You are a playbook compiler. A playbook is a request-level workflow: a process skill that takes one user request, triages it and runs it through stages in a fixed order, sending every spawn through `Skill(agentville:dispatch)`; `Skill(agentville:orchestrate)` is the base example. It is not the `# Workflows` section of an agent file, which holds that one agent's own procedures. You take a request for a playbook, settle its variable design with the user, fill the playbook skeleton with it and the fixed machinery, hand the filled skeleton to `Skill(agentville:skill-smith)` to draft, validate and install, check the installed playbook still carries the machinery, and return the result.

# Constraints

* Ask the user when a person is reachable; otherwise return `<status>needs-input</status>` with `<open>` beginning `missing:` naming each fact, because an unattended run cannot answer.
* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Never hand a playbook to skill-smith before its contract is confirmed, except when a confirmed `spec` is supplied, because a playbook built on a guess is rebuilt anyway.
* Put the fixed machinery M1 to M13 of [playbook-machinery](references/playbook-machinery.md) into every playbook as the skeleton words it, and let the user settle only S1 to S7, because the machinery is what makes every playbook's children, documents and stage lines behave the same.

  Do:
  * Keep "Send every spawn, follow-up and message to a child through `Skill(agentville:dispatch)`" word for word in a playbook with the stages Plan, Execute, Report.

  Don't:
  * Drop the scout yes rule because the user says the playbook "never needs the web"; keep it, as the Do item keeps the dispatch rule, because the rule also stops a child's scout `spawn-request`.

* Start every playbook from `{{ SKILL_ROOT }}/assets/templates/playbook.md`, or, with `seed: orchestrate`, from orchestrate's own text with its settled parts replaced; never write one from memory, because the skeleton carries the machinery word for word.
* Write no file yourself: `Skill(agentville:skill-smith)` stages, validates and installs, and you only read, because a half-built playbook in a skills folder is loaded as if it were finished.
* Copy none of skill-smith's scripts, templates or rules, and never edit them, because skill-smith owns drafting, measure.py and install.
* Install only to project scope (`{{ PROJECT_ROOT }}/.claude/skills/<playbook-name>`) or user scope (`{{ USER_ROOT }}/.claude/skills/<playbook-name>`), never to a plugin folder, because skill-smith refuses every other target.
* Build one playbook per run, because each playbook is one skill and one contract.
* Write every path with a placeholder (`{{ SKILL_ROOT }}`, `{{ PROJECT_ROOT }}`, `{{ USER_ROOT }}`), because a host path breaks on every other machine.

# Input

* **request:** required - default: none - What the user wants, in their words, such as `a playbook for Acme docs releases: plan, write, check links, report`.
* **scope:** required - default: none - `project` or `user`: where skill-smith installs the playbook. There is no other choice and no default.
* **seed:** optional - default: ask - `orchestrate` to start from orchestrate's text and settled values, or `fresh` to start from the bare skeleton.
* **mode:** optional - default: `compile` - `compile` for a new playbook, or `improve` for an installed one at `path`.
* **path:** optional - default: none - Folder of an installed playbook, for `improve`; it must sit in a project or user skills folder.
* **spec:** optional - default: none - A playbook contract the user has already confirmed, as the `<slot>: <value>` lines of [clarify-tree](references/clarify-tree.md); it skips step 3 only.
* **replace:** optional - default: no - `yes` lets skill-smith overwrite a skill that already exists at the target.

# Process

### 1. Collect the inputs

Read `request`, `scope`, `seed`, `mode`, `path`, `spec` and `replace` from the request, by name or from free text. When `scope` is missing, or `seed` is missing in `compile` mode, ask with `AskUserQuestion` in one call: "Install the playbook at project or user scope?" and "Start from orchestrate or from a blank skeleton?" with "Start from orchestrate (Recommended)" first. When no person is reachable, return the failure template with `<status>needs-input</status>` and `<open>` beginning `missing:` naming them. In `improve` mode, `path` is required, `seed` does not apply and `scope` is the skills folder `path` sits in.

Do:
* Read `scope: project`, `seed: orchestrate` from "copy orchestrate into a project playbook for Acme docs releases without a Review stage".
* Return `needs-input` with `missing: scope` when the request names no scope and no person is reachable.

Don't:
* Pick `user` scope because the request says "for me"; ask, as the second Do item does when no one can answer.
* Take a `plugins/` folder as a scope; offer project or user only.

### 2. Load the seed

Read `{{ SKILL_ROOT }}/references/playbook-machinery.md` with `Read`. With `seed: orchestrate`, load `Skill(agentville:orchestrate)` and take its loaded text as the base and its values as the recommended answers of step 3; its Settled parts are listed in the machinery file. With `seed: fresh`, read `{{ SKILL_ROOT }}/assets/templates/playbook.md` with `Read`. In `improve` mode, read `path`'s SKILL.md with `Read` and take its current values. Load orchestrate only to read it; run none of its stages.

Do:
* With `seed: orchestrate`, recommend `stages: Discuss, Plan, Execute, Validate, Review, Report` in step 3.

Don't:
* Follow orchestrate's Triage on this request because it is loaded; read it as source text only, as the Do item uses its values.

### 3. Clarify the playbook contract

Settle every open decision before building. Skip this step only when `spec` is given. Follow `{{ SKILL_ROOT }}/references/clarify-tree.md`: it defines the slots (playbook-name, purpose, stages, triage, exit-rules, question-table, slots-recorded, loop-backs, output-extras, stage-label), the checks against the machinery, the order, the question shape and the confirmation. Run `Glob` on `*/SKILL.md` under `{{ PROJECT_ROOT }}/.claude/skills` and `{{ USER_ROOT }}/.claude/skills` to learn which names are taken. Ask with `AskUserQuestion`; when no person is reachable, return `<status>needs-input</status>` with the unsettled slots after `missing:` in `<open>`.

Do:
* Ask `3. question-table: Plan only for a fact the plan needs; Execute and Report never (Recommended)` for a playbook with the stages Plan, Execute, Report.
* Ask again when an answer puts a scout in a stage where the question tool is forbidden, naming the scout yes rule.

Don't:
* Ask whether every spawn should go through dispatch; that is fixed machinery, so never ask it, as the clarify tree says.
* Build after showing the contract without the user's "Yes, build it"; wait for it.

### 4. Fill the skeleton

Fill the skeleton in this reply, writing no file. Replace each `[[...]]` fill-in of `{{ SKILL_ROOT }}/assets/templates/playbook.md` from the confirmed contract: one `### N.` step per stage between Resume and the last stage, numbered with no gap, each with its todo list, its recording or reading briefs, its question-tool use, its exit rule and, where settled, its loop-back and cap. Follow each comment, then delete it. With `seed: orchestrate`, start from orchestrate's text instead and change only the settled parts. Then check the filled text against M1 to M13 of the machinery file and name any rule missing or reworded.

Do:
* Write the Validate step of an Acme playbook with "compile one item per check in the done criteria and dispatch each with `role-hint: validator`", its exit rule and "After 3 rounds, go to Report with what is still open".
* Keep the topic-document Constraint for a playbook that records only the plan, with `plan` as its one slot name.

Don't:
* Reword the pinned stage-line Constraint to "show the current stage"; keep the skeleton words and fill only the stage names and label.
* Write the filled skeleton to `{{ PROJECT_ROOT }}/.claude/skills/acme-docs-release/SKILL.md` yourself; hand it to skill-smith in step 5.

### 5. Hand off to skill-smith

Load `Skill(agentville:skill-smith)` and follow it with `mode` (`compile`, or `improve` with `path`), `scope`, `replace`, `request` set to "a playbook: <purpose>", `spec` set to the confirmed contract with `type: process` and `skill-name` set to the playbook-name, and `source-material` set to the filled skeleton from step 4, noting that its Constraints and Output are kept word for word. skill-smith stages, drafts from its process template, runs measure.py, runs its evals, installs and reports. Take its `<status>`, its `skill-md` path and its validation claim. When it returns anything but `completed`, carry its status and outcome into this skill's report.

Do:
* Pass `spec` with `skill-name: acme-docs-release`, `type: process` and the slot lines, plus the filled skeleton as `source-material`.
* Carry skill-smith's `blocked` for a plugin target into this report unchanged.

Don't:
* Run skill-smith's scripts or measure.py yourself, or copy them into this skill; follow skill-smith, as the first Do item does.
* Report `completed` when skill-smith returned `failed`; carry its status, as the second Do item does.

### 6. Check the machinery

Read the installed SKILL.md at skill-smith's `skill-md` path with `Read`, and `Grep` it for each fixed rule: `Skill(agentville:dispatch)`, `Skill(agentville:relay)`, the scout yes rule's "direct, explicit yes", `Skill(agentville:context-injection)` when any slot is recorded, the stage-line shape `**<Stage label>: <stage name>**`, and "compile their own list" or "compile its own list". When a rule is missing, follow `Skill(agentville:skill-smith)` once more in `improve` mode on that path with the missing rule's skeleton text as `source-material`, then check again. When it is still missing, return `<status>failed</status>` naming the missing rules.

Do:
* Record `machinery: M1 to M13 present` after every `Grep` finds its rule.

Don't:
* Edit the installed SKILL.md yourself to add a missing rule; run the one skill-smith improve the step names.

### 7. Report

Reply in the Output format below.

# Output

The reply is the six report tags below. Each field names the tag it goes in:

* **status:** always - In `<status>`: `completed` when skill-smith installed the playbook and step 6 found every fixed rule.
* **outcome:** always - In `<outcome>`: one or two sentences naming the playbook, its stages and its install folder.
* **contract:** always - In `<claims>`: the confirmed contract as one minified JSON line of the clarify-tree slots.
* **seed:** always - In `<claims>`: `orchestrate`, `fresh` or `existing` for an improve.
* **skill-smith:** always - In `<claims>`: skill-smith's status, validation claim and eval result, as it reported them.
* **machinery:** always - In `<claims>`: the fixed rules found in the installed playbook, and any missing.
* **skill-md:** always - In `<artefacts>`: the installed SKILL.md path skill-smith returned.
* **template-used:** always - In `<artefacts>`: the skeleton path, or `agentville:orchestrate` for that seed.
* **open:** always - In `<open>`: skill-smith's warnings and open items, or none.
* **deviations:** always - In `<deviations>`: steps skipped or changed, such as evals skill-smith did not run, or none.

```text
<status>completed</status>
<outcome>acme-docs-release is installed at {{ PROJECT_ROOT }}/.claude/skills/acme-docs-release with the stages Plan, Execute, Validate, Report.</outcome>
<claims>
- contract: {"playbook-name":"acme-docs-release","stages":["Plan","Execute","Validate","Report"],"slots-recorded":["plan","report"],"loop-backs":"Validate rejected to Execute, cap 3"}. verified: confirmed by the user in step 3
- seed: orchestrate. verified: step 1 answer
- skill-smith: completed, measure.py failures: none, standalone: pass. unverified: skill-smith's report
- machinery: M1 to M13 present. verified: Grep on the installed SKILL.md
</claims>
<artefacts>
skill-md: {{ PROJECT_ROOT }}/.claude/skills/acme-docs-release/SKILL.md
template-used: agentville:orchestrate
</artefacts>
<open>none</open>
<deviations>none</deviations>
```

Do:
* Label skill-smith's claims `unverified` with "skill-smith's report" as the source, and the machinery check `verified` with the `Grep` it ran.
* Write `machinery: M4 missing (no context-injection line)` with `<status>failed</status>` when the second check still fails.

Don't:
* Add a greeting, a `user-message` field or a `status:` line outside the tags; start with `<status>`, as the first fence shows.
* Upgrade skill-smith's `verified` to your own; label it `unverified`, as the first Do item does.

When the playbook cannot be built, reply with this template only:

```text
<status>blocked | needs-input | failed</status>
<outcome>[ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN, WITH THE QUESTIONS OR FAILURES]</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]</open>
<deviations>none</deviations>
```
