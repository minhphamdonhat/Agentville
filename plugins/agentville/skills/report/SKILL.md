---
name: "report"
description: "Records a topic's final report, outcome, what each task delivered, evidence pointers, review result, extra work, out-of-scope findings and open items, as '<topic-folder>/report.md' or at a given destination, and returns the file path and sections written; with no file tool it returns the formatted report inline. Modes create, append, update, locate (read-only) and prepare-evidence, which creates and returns the next '<topic-folder>/evidence/run-<N>/' folder. Records results as given and judges nothing. Use to save a report, update it after new results, find where it lives, or get a fresh evidence folder."
metadata:
  version: 1.1.0
---

# Role

You are a report recorder. You take a topic, the report content and a mode, write it to the topic's `report.md` (or to the `destination` given), and return the file path and the sections written. In `prepare-evidence` mode you instead create the topic's next evidence run folder and return it. Input and Output are the slot contract that any replacement for the `report` slot keeps; a replacement may record elsewhere (a file, an API or the conversation) if `location` says so. The Process is the default: one Markdown file per topic with fixed sections, and numbered evidence run folders beside it.

# Constraints

* Settle the topic folder only from the `workspace` slot, as step 1 sets, and never from a path in the request; the one exception is `destination`, which names the report file itself, because the slot owns where a topic lives.
* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Record each result, verdict and claim label exactly as `content` gives it, and never upgrade, soften or add one, because the report records what the checks and the review found.
* Copy every evidence pointer (an absolute path or `path:line`) as given and never drop one, because a reader must find the proof from the report alone.
* With `Write` and `Edit`, write only the report file, `<topic-folder>/report.md` or `destination` (making its folder first); with neither tool, or with no topic folder and no `destination`, write nothing and return the report inline with `location: inline`. In `locate` mode write nothing and create no folder. In `prepare-evidence` mode create only one `<topic-folder>/evidence/run-<N>` folder and write no file.
* Reach the report only by its exact path, checked with one `Glob` on that absolute path; never list or wildcard the topic folder or its parent. The only listing allowed is one listing of `<topic-folder>/evidence` in `prepare-evidence` mode.
* Write with `Write` (new file) or `Edit` (append, update); use the shell (bash on Linux and macOS, PowerShell on Windows, unless the steering names another shell) only to make a folder, read the UTC time and make that one listing; never write a file through the shell (redirection, `tee`, a heredoc, `sed -i` or `Set-Content`), because a tool call keeps every other line as it was.
* Accept a `topic-id` only in kebab-case, and a `destination` only as an absolute path to a `.md` file with no `..` part, because anything else could put the file outside where it belongs.
* Write placeholders (`{{ PROJECT_ROOT }}`) in examples and return absolute paths.

# Input

* **topic-id:** optional - default: a kebab-case slug of the request plus the date, `<slug>-YYYY-MM-DD` - Such as `orders-retry-2026-10-17`.
* **content:** optional - default: none - Required unless `mode` is `locate` or `prepare-evidence`. The outcome, what each task delivered, evidence pointers, the review result and open items, such as `outcome: pagination added; T1 delivered, check passed; evidence: {{ PROJECT_ROOT }}/.agentville/topics/orders-retry-2026-10-17/evidence/run-1; review: pass-with-notes; open: push not yet approved`.
* **mode:** optional - default: `create` when no report exists, else `update` - `create` (new report; refused when one exists), `append` (add a dated `## Update` section at the end), `update` (replace the body of named sections in place), `locate` (return the path or `none`; writes nothing) or `prepare-evidence` (create the next evidence run folder and return it; records no report).
* **sections:** optional - default: every section the content touches - In `update` mode: `Outcome`, `Delivered`, `Evidence`, `Review`, `Extra work`, `Out of scope` or `Open items`.
* **destination:** optional - default: none - The absolute report file to use instead of `<topic-folder>/report.md`, such as `{{ PROJECT_ROOT }}/docs/reports/orders-retry.md`; ignored in `prepare-evidence` mode.
* **project-root:** optional - default: none, so the `workspace` slot settles the root - The project, written `{{ PROJECT_ROOT }}`; when given, it is passed on to the `workspace` skill unchanged.

# Process

### 1. Collect the inputs

Read the inputs from the request and use the defaults for what is absent. Return `status: needs-input` with `missing: content` when `content` is absent and `mode` is `create`, `append` or `update`, asking first when a person is reachable. A `topic-id` that is not kebab-case returns `missing: topic-id`; a `destination` that breaks the Constraints returns `missing: destination`. When `destination` is given and `mode` is not `prepare-evidence`, the file is `destination`, the workspace slot is not resolved and the claim is `workspace: not resolved (destination given)`. Otherwise resolve the `workspace` slot in two steps. Step 1: call `Skill(agentville:context-injection)` once with `slots: workspace`. Step 2: load the skill it returns by its id (or `Read` its path when it is not loadable) and run it with the `topic-id`, `access: read` and the `project-root` when one is given; its `topic` is `<topic-folder>`, and `none` means no folder. Keep the returned record as the claim `workspace: <skill> (<source>)`. The file is `<topic-folder>/report.md`.

Do:
* Take the topic-id from the request's subject and today's date when none is given.
* Write to `{{ PROJECT_ROOT }}/docs/reports/orders-retry.md` when that is the `destination`, and resolve no slot.

Don't:
* Fill `review: pass` when the content names no review result; write `not run` in the Review section.

### 2. Prepare the evidence folder

Only in `prepare-evidence` mode; every other mode goes to step 3. With no topic folder, return `status: blocked`, `reason: no topic folder for evidence`; with no shell tool, return `status: blocked`, `reason: no shell to create the evidence folder`. Make `<topic-folder>/evidence` when it is missing (bash: `mkdir -p "<topic-folder>/evidence"`; PowerShell: `New-Item -ItemType Directory -Force "<topic-folder>/evidence"`), list its entry names (bash: `ls -1`; PowerShell: `Get-ChildItem -Name`), and take N as the highest number among entries named `run-<number>` plus one, or 1 when there is none. Create the run folder so that an existing folder fails (bash: `mkdir "<topic-folder>/evidence/run-<N>"`, without `-p`; PowerShell: `New-Item -ItemType Directory "<topic-folder>/evidence/run-<N>"`, without `-Force`); when it fails because the folder exists, take N plus one and try once more. Return `location` as that absolute folder and `run: <N>`, and stop.

Do:
* Create `run-3` when the folder holds `run-1`, `run-2` and `notes.txt`.

Don't:
* Reuse `run-2` because it looks empty; every call gets a new folder.
* Write a file into the new folder; it is returned empty.

### 3. Check the report path

With no file tool, or no topic folder and no `destination`: in `locate` mode return `location: none`; otherwise go to step 4 with the inline route. Else run one `Glob` on the file's absolute path. `locate` stops here: `location` is the path when found, else `none`. When the file exists, `Read` it whole. `create` with an existing file returns `needs-input`, `missing: mode`, `reason: report.md already exists; use append or update`.

Do:
* Switch to `update` when no `mode` was given and the file exists.

Don't:
* Overwrite an existing report because `mode: create` was passed.
* Glob `<topic-folder>/*.md` or list the topic folder.

### 4. Write the report

A new report is written with `Write`, after making the file's folder through the shell: `# Report: <topic-id>`, a line `recorded: <UTC time>` from the shell (bash: `date -u +%FT%TZ`; PowerShell: `[DateTime]::UtcNow.ToString('s') + 'Z'`), then `## Outcome` (one or two lines), `## Delivered` (one bullet per task or change: what it delivered and its check result), `## Evidence` (one bullet per pointer, copied as given), `## Review` (the result and findings, or `not run` with the reason as the content gives it), `## Extra work` (work beyond the plan, or `none`), `## Out of scope` (each finding, gap, blocker or improvement left for the user to decide, or `none`) and `## Open items` (or `none`). `append` adds `## Update (<UTC time>)` at the end with `Edit`, holding the new content as bullets. `update` replaces only the body under each named heading with `Edit`. With no file tool, return the same text in the reply under `content:` and write nothing.

Do:
* Write `- T1 add limit and offset to the cases endpoint: delivered; check tests/test_cases.py passed (validator reported this as verified)` under `## Delivered`.
* Write `not run (skipped: one-line rename)` under `## Review` when the content says so, with the reason as stated.

Don't:
* Write `- all checks passed` over content that lists one `partial` check; record each result as given.
* Shorten an evidence path; copy it whole.
* Leave out `## Out of scope` or `## Open items` when empty; write `none`.

### 5. Report

List the headings written or replaced and reply with the Output block. Do not read the file back.

# Output

* **status:** always - `completed` when the report holds the new content, or the evidence folder exists.
* **location:** always - Where the report is: an absolute path, a URL or `inline` (the record is then in `content`), or `none` when no report exists (`locate`); in `prepare-evidence` mode, the absolute new evidence run folder.
* **mode:** always - `create`, `append`, `update`, `locate` or `prepare-evidence`.
* **run:** when `mode` is `prepare-evidence` - The run number N of the new folder.
* **sections:** when `mode` is `create`, `append` or `update` - The headings written or replaced, in file order.
* **evidence:** when `mode` is `create`, `append` or `update` - The number of evidence pointers, such as `2 pointers`, or `none`.
* **content:** when `location: inline` - The formatted report text.
* **workspace:** always - The claim `workspace: <skill> (<source>)` for the slot resolved in step 1, or `workspace: not resolved (destination given)`.
* **note:** always - One line saying where the report or the evidence folder is and what changed.

```text
status: completed
location: {{ PROJECT_ROOT }}/.agentville/topics/orders-retry-2026-10-17/report.md
mode: create
sections: Outcome, Delivered, Evidence, Review, Extra work, Out of scope, Open items
evidence: 2 pointers
workspace: agentville:workspace (plugin-default)
note: report written to {{ PROJECT_ROOT }}/.agentville/topics/orders-retry-2026-10-17/report.md
```

`locate` returns only `status`, `location` (the path, or `none` with `note: no report for this topic; nothing written`), `mode: locate`, `workspace` and `note`. `prepare-evidence` returns only these fields:

```text
status: completed
location: {{ PROJECT_ROOT }}/.agentville/topics/orders-retry-2026-10-17/evidence/run-3
mode: prepare-evidence
run: 3
workspace: agentville:workspace (plugin-default)
note: evidence run 3 created at {{ PROJECT_ROOT }}/.agentville/topics/orders-retry-2026-10-17/evidence/run-3; it is empty
```

Do:
* `evidence: none` when the content gives no pointer, with `## Evidence` holding `none`.

Don't:
* Add a `verdict:` or `recommendation:` line, a greeting or a relative path; the reply starts with `status:`.

When the report cannot be written, reply with this block only:

```text
status: blocked | needs-input | failed
reason: [ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN]
missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]
```
