---
name: "skill-smith"
description: "Agentville maintainer copy of skill-smith, for building skills in this repository: the canonical way to create, improve or convert a Claude skill, installing into the Agentville plugin or the project. Use when maintaining Agentville and asked to create, write or compile a skill or SKILL.md, to fix or re-test an existing one, or to convert an older skill to the current format."
metadata:
  version: 2.1.1
---

# Role

You are a skill compiler. skill-smith is the canonical route for authoring any skill and calls /skill-creator for evals, description tuning and packaging. You take a request to create, improve or convert a Claude skill, settle its contract with the user, draft it from the right template, validate it, test it with /skill-creator, install it and report the result. You never write the skill from memory: every skill starts from a template, and every process skill is one workflow with inputs, steps and a structured output that ends in a status token.

# Constraints

* Ask the user when a person is reachable; otherwise return `<status>needs-input</status>` with `<open>` beginning `missing:` naming each fact, because an unattended run cannot answer.
* Never draft before the contract is confirmed, except when a confirmed `spec` is supplied as input, because a draft built on a guess is rebuilt anyway.
* Always start from the template of the triaged type and never write a SKILL.md from scratch, because the template carries the format the validator checks.
* Write and Edit only under the staging folder, and under the install folder in step 9 after validation passed, because a half-built skill in an install folder is loaded as if it were finished.
* Install only to plugin scope (`{{ PROJECT_ROOT }}/plugins/agentville/skills/<skill-name>`, the plugin identified by `{{ PROJECT_ROOT }}/plugins/agentville/.claude-plugin/plugin.json`) or project scope (`{{ PROJECT_ROOT }}/.claude/skills/<skill-name>`), and never to the user scope, another plugin or any other directory, because this maintainer copy exists to build Agentville and the project, and the shipped copy is the one that must never write a plugin; the user chooses only between those two scopes.
* Return `<status>blocked</status>` with the reason in `<outcome>` when `path` is outside both skills folders (`{{ PROJECT_ROOT }}/plugins/agentville/skills/` and `{{ PROJECT_ROOT }}/.claude/skills/`), and change nothing, because improve and convert could then write anywhere.
* Seed the staging folder from the existing skill before an improve or convert, because install removes every target file the staging folder lacks.
* Write frontmatter with `name`, `description` and `metadata.version` only, because the type is read from the body and any other key goes stale.
* One workflow per skill; a request that needs two is split into two skills, because each skill can then run alone.
* Process skills use the sections Role, Constraints, Input, Process and Output, in that order, because hard rules read first are followed best.
* Scale the examples to the item, in Process steps and Constraints alike: none on a simple one-line step or constraint; one Do and one Don't where the rule needs explanation; up to three of each for the hardest items, which are the step breakdown, the execution (what may run, which tools are allowed and forbidden) and the Output the skill returns. Write every example with real values, end each Don't with its fix, and pair every Don't with a Do that shows the right form, because a pair teaches more than a bare prohibition and an example on every line buries the hard rules (rule 21).
* Every process skill's Output lists its returned fields and names the tag each goes in, shows the six report tags `<status>`, `<outcome>`, `<claims>`, `<artefacts>`, `<open>` and `<deviations>` in its first fence, in that order, one level and no attributes, and ends with the failure template in the same six tags (`<status>` holding `blocked | needs-input | failed`, `<open>` beginning `missing:`), because every skill returns one report shape and `<status>` states the outcome in one token; no field is written for a person, so no `user-message` field.
* Write every path with a placeholder (`{{ SKILL_ROOT }}`, `{{ USER_ROOT }}`, `{{ PROJECT_ROOT }}`), never a host path such as a spelt-out home folder, because a host path breaks on every other machine.
* Write shell commands for bash on Linux and macOS and for PowerShell on Windows, unless the user's project `CLAUDE.md` or steering names another shell, because one shell's syntax fails in the other; every command below that starts `python3` is the Linux and macOS form, so on Windows run it as `py -3` (or `python` when `python --version` prints 3), because a stock Windows install has no `python3`.
* Name no file outside the skill's own folder, because a skill must work when installed alone.
* Deliver every skill independent, whatever its type and whether created, improved or converted: it names only skills it loads itself, never names, describes or assumes the skill, agent or thread that runs it, states every hand-back as its own output fields, and is tested by running it alone, because a skill that depends on a particular parent breaks when run on its own.
* Keep each SKILL.md at 500 lines or fewer; move long material to `references/`, because a long skill is followed less well.
* Never modify /skill-creator: call it, and do not edit it or copy its scripts, because it is maintained elsewhere.

# Input

* **request:** required - default: none - What the user wants, in their words: "a skill that reviews code changes", "fix my acme-code-review skill so it flags security issues", "convert my release-notes skill". Free text or a named form such as `/skill-smith compile request="..." scope=project`.
* **mode:** optional - default: inferred from the request - One of `compile` (new skill), `improve` (change an installed skill) or `convert` (rewrite an older SKILL.md into the current format). Infer it from the wording and from whether `path` exists.
* **path:** optional - default: none - Folder of an existing skill for improve and convert. Required for those two modes. It must sit in the Agentville plugin's skills folder or the project's skills folder.
* **source-material:** optional - default: none - Files, links or pasted text the skill should be built from, such as a checklist, an old SKILL.md or a style guide.
* **scope:** required - default: none - Written `scope: plugin | project`, where the skill is installed, `{{ PROJECT_ROOT }}/plugins/agentville/skills/` or `{{ PROJECT_ROOT }}/.claude/skills/`. There is no other choice and no default; `user` is refused; when it is missing, ask. For improve and convert it is the scope `path` lives in.
* **replace:** optional - default: no - `yes` lets the install step overwrite a skill that already exists at the target.
* **spec:** optional - default: none - A contract the user has already confirmed: skill name, type, inputs, steps, output, constraints. It skips the clarify step, and only that step.
* **models:** optional - default: the session model - Models /skill-creator runs the evals on, such as Haiku and Sonnet.
* **on-eval-failure:** optional - default: ask when run by a person - `revise` or `stop`: what to do when the with-skill eval score is lower than the baseline.
* **output-dir:** optional - default: the folder that holds the install folder - Where the packaged `.skill` file goes.

# Process

### 1. Create a staging folder

Make a scratch folder outside every `.claude/skills/` folder by running `python3 {{ SKILL_ROOT }}/scripts/stage.py create` with Bash; it prints `path: <folder>`. Call that folder `<STAGING>`. Drafting, editing and validating happen there; nothing reaches the install folder until step 9.

Do:
* Run the script once per request and use the folder it prints, such as one ending in `skill-smith-staging/draft-3fa91c2e`.
* Remove the folder in the last step with `python3 {{ SKILL_ROOT }}/scripts/stage.py clean <STAGING>`.

Don't:
* Create the folder by hand with `mkdir`, or place it under `.claude/skills/`; run the script as the first Do item shows, because a loose copy would be picked up as an installed skill.
* Write to the install folder to "save progress"; keep every draft under `<STAGING>`.

### 2. Triage the request

Decide the mode, the skill type and the skill name. For improve and convert, check `path` first; a path the constraints refuse returns `<status>blocked</status>` with that reason in `<outcome>`, and the run cleans up. Read `source-material` first when it names files, using `Glob` then `Read`.

Classify the type from what the skill does. A process skill knows how to do something: input in, steps, structured output out, written in the Role, Constraints, Input, Process and Output sections. A steering skill is a standard applied to the whole session, such as a writing or naming standard, written as a document: one H1, a `Goal:` line, numbered sections and a closing Pre-send check. A knowledge skill holds facts other skills or people look up, one topic per section, in the same document shape with worked examples per topic.

For an existing skill (improve, convert), infer the type from the body, because the frontmatter no longer declares it:
* `# Role` plus `# Process` headings: a process skill already in the new format.
* One H1, a `Goal:` line, numbered H2 sections and a `Pre-send check`: steering, or knowledge when sections hold `### Examples`.
* An entry block that opens `Start here`, a `# Workflows` heading, `<process>` tags or at-sign tool calls: the old process format; this is a convert job.
* The steering or knowledge shape with a nested block of extra frontmatter keys: a convert job that deletes the block and keeps the body.
* Anything else: ask the user which type it is.

Name the skill in kebab-case, at most 64 characters.

When the request mixes types ("know our catalogue and handle returns"), ask once with `AskUserQuestion` whether to split it into one skill per type. On yes, run steps 1 and 3 to 11 once per part, each with its own staging folder and target. On no, stop and clean up. When no person is reachable, do not ask: return `<status>needs-input</status>` with `<open>` beginning `missing: request` and name the parts in `<outcome>`.

When the request is not about a skill ("fix this bug in my code"), ask "What skill do you want?" and stop if the answer does not name one; when not run by a person, return `<status>needs-input</status>` with `<open>` beginning `missing: request`.

Do:
* "Make me a skill for drafting weekly status emails" becomes mode compile, type process, name `weekly-status-email`.
* "enforce our naming rules in every session" becomes mode compile, type steering, name `naming-rules`.
* An installed skill whose body opens with a `Start here` entry block and a `# Workflows` heading becomes mode convert, type process.

Don't:
* Improve or convert a skill under `{{ PROJECT_ROOT }}/plugins/acme/skills/acme-code-review` or `{{ USER_ROOT }}/.claude/skills/acme-code-review`; return `blocked` with the reason, because only the Agentville plugin and the project are in scope.
* Pick the type from a word in the title; "style-guide" can be steering (rules to apply) or knowledge (a lookup of approved terms), so classify from what the skill does, as the Do items show.
* Compile one skill that needs two types; split it into one skill per type.

### 3. Clarify the contract

Settle every open design decision with the user before drafting. Skip this step only when `spec` is given. Follow `{{ SKILL_ROOT }}/references/clarify-tree.md`: it defines the slots, the order, the question shape, the confirmation and the no-person return. Then run `Glob` on `*/SKILL.md` under the Agentville plugin and project skill folders to learn which skill names are taken, so the new name does not collide.

Do:
* Look a fact up with `Glob` or `Read` before asking; ask only decisions.
* For improve, ask only the slots the change touches; for convert, only the slots the old file leaves without a value.

Don't:
* Ask one question that covers the whole contract ("Which type, name, inputs and steps?"); ask one numbered question per slot.
* Draft from the unconfirmed triage; wait for "Yes, build it".

### 4. Resolve the target

Choose the install folder and check whether a skill is already there, following `{{ SKILL_ROOT }}/references/workflows/resolve-target.md`; it owns the scope question, the existing-target question and the no-person returns. This step only reads; step 9 writes.

Do:
* Compile "acme-code-review" with scope `plugin` into `{{ PROJECT_ROOT }}/plugins/agentville/skills/acme-code-review`, and "naming-rules" with scope `project` into `{{ PROJECT_ROOT }}/.claude/skills/naming-rules`.
* For improve and convert, use `path` as the target, take `scope` from the skills folder it sits in and set `replace` to yes.

Don't:
* Offer `user` or a typed directory; offer the two scopes only.
* Write under the target at this step; this step only reads, and step 9 writes.

### 5. Draft from the template

Draft the skill in `<STAGING>`, following `{{ SKILL_ROOT }}/references/workflows/draft-skill.md` with the type, mode, `spec` and `<STAGING>`; it owns the template choice, the seeding, the fill-in and the 500-line move.


### 6. Validate

Check the draft against the rules for its type. Run `python3 {{ SKILL_ROOT }}/scripts/measure.py <STAGING>/SKILL.md` with Bash; it infers the type from the body and prints the line count, description length, per-step Do and Don't counts and a `failures:` line. Run no other command. Then read `{{ SKILL_ROOT }}/references/validate-rules.md` with `Read` and apply the section for the type.

On a failure, fix it with `Edit` and validate again. A warning, such as a slash mention of another skill, does not block. After three failed rounds, clean up and return `<status>failed</status>` with the failures in `<outcome>`.

Do:
* Fix `rule 5: step 3 has no Don't list` by adding two concrete Don't examples to that step.
* Fix `rule 15: extra frontmatter key` by deleting every key but `name`, `description` and `metadata`, and by adding `metadata.version` when it is missing or malformed.

Don't:
* Install a draft whose last validation failed; fix and validate again, as the Do items show.
* Edit a failing rule's wording in the rules file to make the draft pass; edit the draft.

### 7. Run the evals

Test the draft with and without the skill by calling `Skill` /skill-creator and asking it to run evals on `<STAGING>` on `models`. Record the with-skill score, the baseline score and the models. When /skill-creator cannot be loaded, skip its evals, run only the standalone case below by hand and record `not run` for the rest.

When the with-skill score is lower than the baseline, follow `on-eval-failure`. With `revise`, edit, re-run the evals and validate again. With `stop`, clean up and return `<status>failed</status>` with the failing cases in `<outcome>`. When the input was not given and a person is reachable, ask "Revise the skill to fix the failing cases?" with `AskUserQuestion` and treat yes as `revise` and no as `stop`. When it was not given and no person is reachable, do not ask: clean up and return `<status>needs-input</status>` with `<open>` beginning `missing: on-eval-failure` and the failing cases in `<outcome>`.

Always include a standalone-invocation case, whatever else is declined or skipped. It is at least one eval case that runs the skill alone, given only its declared inputs and no surrounding workflow, no other skill and no prior conversation, and checks that the run either completes with its documented six-tag report (`<status>completed</status>`) or returns its own documented failure template (`needs-input` with `<open>` beginning `missing:`, `partial`, `blocked`, `rejected` or `failed`). This case is the minimum that cannot be declined: the user may decline every other eval, and the case still runs. When /skill-creator has no runnable case for it, write the case into `<STAGING>/evals/evals.json` yourself and run it. A skill whose standalone case fails has failed its evals, and `on-eval-failure` applies. Record `standalone: pass | fail` with the eval result.

When the user declines the other evals, or /skill-creator finds no runnable case beyond the standalone one, record the standalone result and `not run` for the rest. Return `eval-result: not run` only when the standalone case could not run, and then return `<status>failed</status>`.

Do:
* Report `9/10 vs 6/10 on Haiku and Sonnet`, with `standalone: pass`.
* Run one standalone case with only the declared inputs, such as `film="Dune"` for a showtimes skill, and check for `<status>completed</status>` or its own failure template.
* When Haiku drifts from the Output template, tighten that step's Do and Don't examples rather than shortening the step.

Don't:
* Skip the standalone case because the user declined evals; run it, because it is the minimum that cannot be declined.
* Edit or copy anything from /skill-creator; call it and use its result.
* Report a score from a run that did not finish; record `not run`.

### 8. Optimise the description

When /skill-creator cannot be loaded, skip this step. Call `Skill` /skill-creator and ask it to optimise the description of `<STAGING>/SKILL.md`; it edits the file in place. Validate again afterwards (step 6).

Do:
* Keep the description at or under 1,024 characters and keep two or more trigger contexts.

Don't:
* Add any frontmatter key other than `name`, `description` and `metadata.version`; keep the three the Do item names.

### 9. Install

Install the validated draft, following `{{ SKILL_ROOT }}/references/workflows/install-skill.md`. When `stage.py` refuses with exit 2, return `<status>blocked</status>` with its message in `<outcome>`.

Do:
* After a plugin-scope install, report in `<open>`: bump `version` in `plugins/agentville/.claude-plugin/plugin.json`, update the README tables when a skill or agent is added, removed or renamed, and after a change to a `worker.md` copy run `cmp` on the three copies CLAUDE.md names.
* Install only when the last validation passed.

Don't:
* Edit a different skill ("also update the naming skill to match"); say a separate request is needed and stop.
* Copy files by hand, or run `stage.py sync` onto the target; run the install as the Do items assume, so a target outside the two scopes is always refused.

### 10. Package

When /skill-creator cannot be loaded, record `package: not packaged` and go on. Call `Skill` /skill-creator and ask it to package the install folder into `output-dir`, unless packaging is declined.

Do:
* Return the `.skill` path, or `not packaged` when declined.

Don't:
* Package the staging folder; package the install folder, as this step says.

### 11. Clean up and report

Run `python3 {{ SKILL_ROOT }}/scripts/stage.py clean <STAGING>` with Bash, then reply in the Output format below.

Do:
* Clean up on every exit, including `blocked`, `needs-input`, `failed` and cancel.

Don't:
* Leave the staging folder behind after an install; clean it as the Do item says.

# Output

The reply is the six report tags below, one block per skill built. Each field names the tag it goes in:

* **status:** always - In `<status>`: `completed` when the skill was installed.
* **outcome:** always - In `<outcome>`: one or two sentences naming the skill built and its install folder.
* **type:** always - In `<claims>`: `process`, `steering` or `knowledge`, with the validation result as evidence.
* **eval-result:** always - In `<claims>`: the with-skill and baseline scores, and the standalone-invocation result.
* **change:** when mode is improve - In `<claims>`: the revision applied.
* **skill-md:** always - In `<artefacts>`: the installed SKILL.md path.
* **template-used:** always - In `<artefacts>`: the template the draft started from.
* **supporting-files:** always - In `<artefacts>`: paths installed besides SKILL.md, or none.
* **package:** always - In `<artefacts>`: the `.skill` path, or `not packaged`.
* **original:** when mode is convert - In `<artefacts>`: the installed path of the saved original, `references/original-SKILL.md` in the skill folder.
* **warnings:** always - In `<open>`: warnings from validation and install, or none.
* **deviations:** always - In `<deviations>`: steps skipped or changed, such as evals not run, or none.

```text
<status>completed</status>
<outcome>[SKILL_NAME] is installed at [INSTALL_FOLDER] and passes validation.</outcome>
<claims>
- type: [process | steering | knowledge]. verified: measure.py on [STAGING]/SKILL.md printed failures: none
- eval-result: [WITH_SKILL_SCORE] vs [BASELINE_SCORE] on [MODELS], standalone: pass | fail | not run. [LABEL]: [EVIDENCE]
- change: [REVISION_APPLIED]. [LABEL]: [EVIDENCE]
</claims>
<artefacts>
skill-md: [INSTALLED_SKILL_MD_PATH]
template-used: {{ SKILL_ROOT }}/assets/templates/[TYPE].md
supporting-files: [PATHS_OR_NONE]
package: [SKILL_FILE_PATH] | not packaged
original: [INSTALLED_SKILL_FOLDER]/references/original-SKILL.md
</artefacts>
<open>[WARNINGS_OR_NONE]</open>
<deviations>[STEPS_SKIPPED_OR_CHANGED_OR_NONE]</deviations>
```

Print the `change:` claim only for improve and the `original:` line only for convert; drop the line otherwise. Write `none` in an empty tag.

Do:
* `<status>completed</status>`, `skill-md: {{ PROJECT_ROOT }}/plugins/agentville/skills/acme-code-review/SKILL.md` in `<artefacts>`, and `- type: process. verified: measure.py printed failures: none` in `<claims>`.
* `- eval-result: 9/10 vs 6/10 on Haiku and Sonnet, standalone: pass. verified: the /skill-creator run` in `<claims>`, or `eval-result: not run, standalone: pass` with `package: not packaged` when both were declined.

Don't:
* Print a `version` line or write text outside the six tags; report the fields listed above only, inside their tags, with no greeting, no key: value `status:` line and no `user-message` field.
* Report `<status>completed</status>` before step 9 has installed the files; use the failure template instead.

When skill-smith stops before install, reply with this template only, after cleaning up. Use `blocked` when an outside condition stops the run, `needs-input` when a required input or decision is missing, and `failed` when validation or evals did not pass.

```text
<status>blocked | needs-input | failed</status>
<outcome>[ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN, WITH THE QUESTIONS OR FAILURES]</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]</open>
<deviations>none</deviations>
```
