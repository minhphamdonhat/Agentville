Used by SKILL.md step 5.

# Input

* **type:** required - default: none - `process`, `steering` or `knowledge`, from SKILL.md step 2.
* **spec:** required - default: none - The confirmed contract from SKILL.md step 3, or the supplied `spec` input.
* **staging:** required - default: none - The staging folder `<STAGING>` printed by SKILL.md step 1.
* **mode:** required - default: none - `compile`, `improve` or `convert`.
* **source-folder:** optional - default: none - The folder of the existing skill, for improve and convert.
* **source-material:** optional - default: none - Files or text the skill is built from.

# Process

### 1. Seed the staging folder

For improve and convert, copy the existing skill folder into `<STAGING>` first by running `python3 {{ SKILL_ROOT }}/scripts/stage.py sync <source-folder> <STAGING>` with Bash. The install step mirrors `<STAGING>` onto the target and removes every file `<STAGING>` lacks, so a skill's `references/`, `scripts/` and `evals/` survive only if they are seeded here. For convert, then copy the old SKILL.md to `<STAGING>/references/original-SKILL.md` with `Read` and `Write` before any edit. For compile, skip this step.

Do:
* Improve `pr-review`: run `python3 {{ SKILL_ROOT }}/scripts/stage.py sync {{ USER_ROOT }}/.claude/skills/pr-review <STAGING>` and keep its `references/checklist.md`.
* Convert `release-notes`: seed, then save `<STAGING>/references/original-SKILL.md`.

Don't:
* Start an improve from the bare template; seed first, as the Do items show.
* Copy the folder with `cp -r`; the script keeps the staging marker that clean-up relies on.

### 2. Copy the template

Read the template for `type` from `{{ SKILL_ROOT }}/assets/templates/<type>.md` with `Read`. For compile, and for convert when the type is process, write it to `<STAGING>/SKILL.md` with `Write`. For improve, keep the seeded SKILL.md and edit it in place, using the template only as the shape to match.

Do:
* Compile a knowledge skill from `{{ SKILL_ROOT }}/assets/templates/knowledge.md`.
* Improve a process skill by editing `<STAGING>/SKILL.md` and leaving its unchanged steps word for word.

Don't:
* Overwrite an improved skill's SKILL.md with the template; edit the seeded copy instead.
* Write a SKILL.md from memory; copy the template first.

### 3. Fill the fill-ins

Replace every `[[...]]` fill-in from `spec` with `Edit`, brackets included. Follow each HTML comment, then delete it. Text outside fill-ins and comments stays word for word. Write the frontmatter with `name` and `description` only. For a process skill, keep the template's `status: needs-input` wording wherever a step names `AskUserQuestion`, and keep the failure block at the end of `# Output`.

Then scale the examples of a process skill to each step and Constraint: none on a simple one-line item; one Do and one Don't where the rule needs explanation; up to three of each on the step breakdown, the execution step (what may run, which tools are allowed and forbidden) and the Output. Use real values, and end each Don't with its fix.

Do:
* Fill the first Input line as `* **diff:** required - default: none - The unified diff to review, such as the output of git diff main.`
* Give every Constraint a reason: "Never print a street address, because the user only needs the ward."
* Leave the step "Read the diff with `Read`." bare, and give the execution step three Do and three Don't, such as Do "Run `git diff main` read-only" and Don't "Run `git checkout`; read the diff with `git diff` instead".

Don't:
* Add a Do and a Don't under a one-line step such as the diff read; leave it bare, as the third Do item shows.
* Add a `version`, `type`, `template` or `allowed-tools` key; keep `name` and `description` only.
* Leave a Don't item with no Do item that shows the right form.

### 4. Map the old format

For convert only, keep the old skill's behaviour in the new shape. Each old workflow step becomes a numbered step, each old input an Input line, each old output an Output template, and each old rule or exception a Constraint or a Do and Don't pair in the step that can hit it. For a steering or knowledge file that already has the new body but a nested frontmatter block, delete the block and keep the body.

For improve and convert, also strip every reference to what runs the old skill (an outer skill, agent or thread, or a description saying a named skill uses it): rewrite each as an input the skill reads or an output field it returns, because Rule 20 fails the skill otherwise.

Do:
* Turn an old exception "target exists" into a Don't item in the step that writes the target, with its Do pair.
* Turn an old rule "never guess a time" into the Constraint "Never guess a time window, because the ranking depends on it."

Don't:
* Drop an old rule because it has no section; map it to a Constraint, as the Do items show.
* Keep a Rules, Workflows or Exceptions heading; move their content as this step says.

### 5. Keep it short

If SKILL.md would pass 500 lines, move long material to `<STAGING>/references/<topic>.md` with `Write` and link it from the step that needs it with a relative link such as `[prices](references/prices.md)`.

Do:
* Move a 120-line price table to `<STAGING>/references/prices.md`.
* Keep the steps themselves in SKILL.md and move only reference data.

Don't:
* Link a file that the skill does not ship; write it under `<STAGING>` first.
* Split one workflow into two files to save lines; move reference data instead.

### 6. Count what is left

Search `<STAGING>/SKILL.md` and every file this workflow wrote for `[[` and `<!--` with `Grep`. Skip files that seeding copied in unchanged and `<STAGING>/references/original-SKILL.md`, because they are the user's own text. The count must be 0 before you return; fill or delete each hit.

Do:
* Report `unfilled-placeholders: 0` after the search finds nothing.
* Fill a stray `[[value]]` in `references/prices.md` before returning.

Don't:
* Return with a count above 0; fix each hit first.
* Edit a seeded file only to clear a comment the user wrote; search only SKILL.md and the files this workflow wrote.

# Output

Reply with this block, or with the failure block when the draft cannot be finished.

```text
draft: <STAGING>/SKILL.md
template: {{ SKILL_ROOT }}/assets/templates/<type>.md
files: <every path written under STAGING, comma-separated>
unfilled-placeholders: 0
```

Do:
* `files: <STAGING>/SKILL.md, <STAGING>/references/prices.md`
* `template: {{ SKILL_ROOT }}/assets/templates/steering.md`

Don't:
* List a file written outside `<STAGING>`; write only under it, as the Do items show.
* Add a `version` line or any field the template lacks; report the four fields only.

```text
status: blocked | needs-input | failed
reason: <one sentence>
missing: <input names, for needs-input; otherwise none>
```
