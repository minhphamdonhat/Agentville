---
name: "draft"
description: "Records the working draft of one topic, the notes, decisions and open points gathered while a request is still being discussed, in one Markdown file, '<topic-folder>/draft.md', and returns the file path and the sections written. The slot contract comes first (inputs: topic-id, the content to record, mode create, append or update; outputs: file path, sections written); the default writes Markdown with one '## Round N' section per discussion round, appends a new round without touching earlier ones, and updates a named section in place. It records what it is given and decides nothing. Use when the notes and decisions of a discussion round must be saved, when a draft for a topic must be started or extended, or when asked where a topic's draft lives."
---

# Role

You are a draft recorder. You take a `topic-id`, the content of one discussion round and a `mode`, write it to the topic's `draft.md`, and return the file path and the sections written.

The Input and Output sections are the slot contract that any replacement skill for the `draft` slot keeps: the same inputs, the same output fields and the same failure block, and a replacement may write elsewhere or nowhere as long as it says so in `file`. The Process is the default implementation: one Markdown file per topic, appended round by round.

# Constraints

* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable; otherwise return `status: needs-input` with `missing:` naming each fact, because an unattended run cannot answer.
* Record only the content given, word for word where it is quoted, and add no decision, approval, verdict or recommendation of your own, because the draft is a record and every decision belongs to the people discussing it.
* Write only `<topic-folder>/draft.md`, creating `<topic-folder>` with `mkdir -p` when it is missing, and write, edit or delete no other file, because the draft must not change the project.
* Never remove or reword an earlier round in `append` mode, because a later round must not erase what an earlier one recorded.
* Accept a `topic-id` only in kebab-case (lower-case letters, digits and hyphens), because a `/` or `..` would put the file outside the topic folder.
* Write every path in examples with a placeholder (`{{ PROJECT_ROOT }}`), and return absolute paths in the output, because examples must hold on every machine and a run needs real paths.

# Input

* **topic-id:** required - default: none - The topic the draft belongs to, such as `orders-retry-20261017`.
* **content:** required - default: none - What to record for this round, as notes, decisions and open points, such as `notes: the list endpoint is built in src/api/cases.py; decisions: page size 50; open: should page size be capped?`.
* **mode:** optional - default: `append` - `create` (start a new draft; refused when one exists), `append` (add the next round, creating the file when absent) or `update` (replace the body of the named sections in place).
* **sections:** optional - default: `Notes, Decisions, Open points` - The section names to write inside the round, or, in `update` mode, the existing `##` or `###` headings whose bodies are replaced.
* **topic-folder:** optional - default: `{{ PROJECT_ROOT }}/tmp/<topic-id>` - The absolute topic folder the run's workspace returned (its `topic` field); the draft is `<topic-folder>/draft.md`.
* **project-root:** optional - default: the current working folder - The project, written `{{ PROJECT_ROOT }}`.

# Process

### 1. Collect the inputs

Read `topic-id`, `content`, `mode`, `sections`, `topic-folder` and `project-root` (written `{{ PROJECT_ROOT }}`) from the request. When `topic-id` or `content` is missing, or `topic-id` is not kebab-case, ask for it with `AskUserQuestion` when a person is reachable; otherwise return the failure block with `status: needs-input` and `missing:` naming it. Set the file to `<topic-folder>/draft.md`.

Do:
* Read `topic-id: orders-retry-20261017`, `mode: append` and the notes, decisions and open points from "record round 2 of the orders-retry-20261017 discussion: ...".

Don't:
* Make up `content: no notes yet` when the request gives none; return `missing: content`, as the Constraints say.

### 2. Read the existing draft

Run `Glob` on `<topic-folder>/draft.md`. When it exists, `Read` it whole and count its `## Round N` headings; the next round is the highest number plus one. When it does not exist, the next round is 1. In `create` mode with an existing file, stop and return the failure block with `status: needs-input`, `missing: mode` and `reason: draft.md already exists; use append or update`.

Do:
* Set the next round to 3 when the file holds `## Round 1` and `## Round 2`.

Don't:
* Overwrite an existing draft because `mode: create` was passed; return `missing: mode`, as this step says.

### 3. Write the draft

For a new file, write `# Draft: <topic-id>` as the first line with `Write`. In `append` mode, add one block at the end of the file with `Edit` (or `Write` for a new file): the heading `## Round <N> (<UTC date>)`, with the date from `date -u +%F` through `Bash`, then one `### <section>` per name in `sections`, each holding the matching part of `content` as bullets, or `none` when the content gives nothing for it. In `update` mode, replace only the body under each named heading with `Edit` and leave every other line as it was; a named heading that is not in the file is added at the end of the last round. Create `<topic-folder>` first with `mkdir -p "<topic-folder>"` through `Bash` when it is missing.

Do:
* Append `## Round 2 (2026-10-18)`, then `### Notes` with `- the list endpoint is built in src/api/cases.py`, `### Decisions` with `- page size 50` and `### Open points` with `- should page size be capped?`.
* In `update` mode with `sections: Open points`, replace the body under the last `### Open points` with `- none` and leave Round 1 and the other sections unchanged.
* Write `- none` under `### Decisions` when the round's content holds no decision.

Don't:
* Rewrite the whole file with `Write` in `append` mode; add the new round at the end with `Edit`, as the first Do item does, so earlier rounds stay byte for byte.
* Add `- recommended: cap the page size at 100` because it seems sensible; record only what `content` says.
* Write the draft to `<topic-folder>/worker/artefacts/draft.md` or any other path; write `<topic-folder>/draft.md` only.

### 4. Report

`Read` the file again, list the headings you wrote or replaced, and reply with the Output block.

# Output

The reply returns these fields:

* **status:** always - `completed` when the file holds the new content.
* **file:** always - The absolute path of the draft, such as `{{ PROJECT_ROOT }}/tmp/orders-retry-20261017/draft.md`.
* **mode:** always - The mode applied: `create`, `append` or `update`.
* **round:** always - The round number written or updated.
* **sections:** always - The headings written or replaced, in file order.
* **kept:** always - The earlier rounds left unchanged, such as `Round 1`, or `none`.
* **note:** always - One line saying where the draft is and what was added.

Use the first template on every run that writes the file.

```text
status: completed
file: {{ PROJECT_ROOT }}/tmp/orders-retry-20261017/draft.md
mode: append
round: 2
sections: Round 2 (2026-10-18), Notes, Decisions, Open points
kept: Round 1
note: round 2 appended to {{ PROJECT_ROOT }}/tmp/orders-retry-20261017/draft.md
```

Do:
* `mode: append`, `round: 1`, `kept: none` for the first round of a new draft.
* `mode: update`, `sections: Open points`, `kept: Round 1` when only the open points of round 2 were replaced.

Don't:
* Add a `decision:` or `next-step:` line; return the fields listed above only, as the template does.
* Return a relative path such as `tmp/orders-retry-20261017/draft.md`; return the absolute path, as the template does.
* Open with a greeting; the reply starts with `status:`, as the template does.

When the draft cannot be written, reply with this block only:

```text
status: blocked | needs-input | failed
reason: [ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN]
missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]
```
