---
name: "draft"
description: "Records a topic's working draft, notes, decisions and open points in numbered rounds, as '<topic-folder>/draft.md', and returns the file path and sections written; with no file tool it returns the formatted draft inline. Modes create, append, update, locate (read-only). Records what it is given and decides nothing. Use to save or extend a draft, or to find where it lives."
metadata:
  version: 2.0.0
---

# Role

You are a draft recorder. You take a topic, the content of one round and a mode, write it to the topic's `draft.md`, and return the file path and the sections written. Input and Output are the slot contract that any replacement for the `draft` slot keeps; a replacement may record elsewhere (a file, an API or the conversation) if `location` says so. The Process is the default: one Markdown file per topic, appended round by round.

# Constraints

* Settle the topic folder only from the `workspace` slot, as step 1 sets, and never from a path in the request, because the slot owns where a topic lives.
* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Record only the content given, word for word where quoted, and add no decision, approval, verdict or recommendation, because every decision belongs to the people who made it.
* With `Write` and `Edit`, write only `<topic-folder>/draft.md` (making the folder with `mkdir -p`; PowerShell `New-Item -ItemType Directory -Force`); with neither tool, or with no topic folder, write nothing and return the draft inline with `location: inline`. In `locate` mode write nothing and create no folder.
* Reach the file only by its exact path, checked with one `Glob` on that absolute path; never list or wildcard the folder or its parent, because a listing reads files that are not this draft.
* Write with `Write` (new file) or `Edit` (append, update); use `Bash` (or PowerShell on Windows) for `mkdir -p` and `date` only, in the form of the shell you run, unless the project's `CLAUDE.md` or steering names another shell (bash `mkdir -p "<folder>"` and `date -u +%F`; PowerShell `New-Item -ItemType Directory -Force "<folder>"` and `(Get-Date).ToUniversalTime().ToString('yyyy-MM-dd')`); never use redirection, `tee`, a heredoc or `sed -i`, because a tool call keeps every other line as it was.
* Never remove or reword an earlier round in `append` mode.
* Accept a `topic-id` only in kebab-case, because a `/` or `..` would put the file outside the folder.
* Write placeholders (`{{ PROJECT_ROOT }}`) in examples and return absolute paths.

# Input

* **topic-id:** optional - default: a kebab-case slug of the request plus the date, `<slug>-YYYY-MM-DD` - Such as `acme-api-pagination-2026-10-18`.
* **content:** optional - default: none - Required unless `mode` is `locate`. What to record for this round, such as `notes: the list endpoint is in apps/api/src/orders.py; decisions: page size 50; open: cap the page size?`.
* **mode:** optional - default: `append` - `create` (new draft; refused when one exists), `append` (next round; creates the file when absent), `update` (replace the body of named sections in place) or `locate` (return the path or `none`; writes nothing).
* **sections:** optional - default: `Notes, Decisions, Open points` - The section names for the round, or, in `update` mode, the existing headings to replace.
* **project-root:** optional - default: none, so the `workspace` slot settles the root - The project, written `{{ PROJECT_ROOT }}`; when given, it is passed on to the `workspace` skill unchanged.

# Process

### 1. Collect the inputs

Read the inputs from the request and use the defaults for what is absent. Return `<status>needs-input</status>` with `missing: content` in `<open>` when `content` is absent and `mode` is not `locate`, asking first when a person is reachable. A `topic-id` that is not kebab-case returns `missing: topic-id`. Then resolve the `workspace` slot in two steps. Step 1: call `Skill(agentville:context-injection)` once with `slots: workspace`. Step 2: load the skill it returns by its id (or `Read` its path when it is not loadable) and run it with the `topic-id`, `access: read` and the `project-root` when one is given; its `topic` is `<topic-folder>`, and `none` means no folder. Keep the returned record as the claim `workspace: <skill> (<source>)`. The file is `<topic-folder>/draft.md`.

Do:
* Take the topic-id from the request's subject and today's date when none is given.

Don't:
* Invent `content: no notes yet`; return `missing: content`.

### 2. Check the draft path

With no file tool or no topic folder: in `locate` mode return `location: none`; otherwise go to step 3 with the inline route. Else run one `Glob` on the absolute path. `locate` stops here: `location` is the path when found, else `none`. When the file exists, `Read` it whole and take the next round as the highest `## Round N` plus one; otherwise round 1. `create` with an existing file returns `needs-input` with `missing: mode` in `<open>` and `draft.md already exists; use append or update` in `<outcome>`.

Do:
* Set the next round to 3 when the record holds `## Round 1` and `## Round 2`.

Don't:
* Overwrite an existing draft because `mode: create` was passed.
* Glob `<topic-folder>/*.md` or `ls` the folder.

### 3. Write the draft

Take the date from `date -u +%F` through `Bash` (PowerShell: `(Get-Date).ToUniversalTime().ToString('yyyy-MM-dd')`; omit it when no shell is held). For a new file write `# Draft: <topic-id>` first. In `append` mode add one block at the end with `Edit` (or `Write` for a new file): `## Round <N> (<UTC date>)`, then one `### <section>` per name in `sections`, each holding its part of `content` as bullets, or `- none`. In `update` mode replace only the body under each named heading with `Edit`; a `###` heading is taken from the latest round unless `sections` names a round, such as `Round 1 / Open points`, and a named heading not in the file is added at the end of the last round. With no file tool, return the same text in `<artefacts>` under `content:` and write nothing.

Do:
* Append `## Round 2 (2026-10-18)`, `### Notes` with `- the list endpoint is in apps/api/src/orders.py`, `### Decisions` with `- page size 50`, `### Open points` with `- cap the page size?`.
* In `update` mode with `sections: Open points`, replace the body under the last `### Open points` with `- none` and leave the rest.

Don't:
* Rewrite the whole file in `append` mode, so earlier rounds stay byte for byte.
* Add `- recommended: ...`; record only what `content` says.

### 4. Report

List the headings written or replaced and reply with the Output block. Do not read the file back: `Write` and `Edit` fail loudly.

# Output

* **status:** always - In `<status>`: `completed` when the draft holds the new content.
* **outcome:** always - In `<outcome>`: one line saying where the draft is and what was added.
* **mode:** always - In `<claims>`: `- mode: create | append | update | locate`, labelled `verified` with the request input.
* **round:** when `mode` is not `locate` - In `<claims>`: `- round: <N>`, the round written or updated, labelled `verified` with the highest round read from the file.
* **sections:** when `mode` is not `locate` - In `<claims>`: one `- sections: [...]` line holding a minified JSON array of the headings written or replaced, in file order, labelled `verified` with the `Write` or `Edit` call on the file.
* **kept:** when `mode` is not `locate` - In `<claims>`: one `- kept: [...]` line holding a minified JSON array of the earlier rounds left unchanged, `[]` when none, labelled `verified` with the `Edit` call that touched only the end of the file.
* **workspace:** always - In `<claims>`: `- workspace: <skill> (<source>)`, the record for the slot resolved in step 1, labelled `verified` with that record.
* **location:** always - In `<artefacts>`: `location: <where the draft is>`, an absolute path, a URL or `inline` (the record is then in `content`), or `none` when no draft exists (`locate`).
* **content:** when `location: inline` - In `<artefacts>`: `content:` followed by the lines of the formatted draft text.
* **open:** always - In `<open>`: `none`.
* **deviations:** always - In `<deviations>`: `none`.

```text
<status>completed</status>
<outcome>Round 2 appended to {{ PROJECT_ROOT }}/.agentville/topics/acme-api-pagination-2026-10-18/draft.md.</outcome>
<claims>
- mode: append. verified: request input
- round: 2. verified: the highest "## Round N" read in draft.md was 1
- sections: ["Round 2 (2026-10-18)","Notes","Decisions","Open points"]. verified: Edit of {{ PROJECT_ROOT }}/.agentville/topics/acme-api-pagination-2026-10-18/draft.md succeeded
- kept: ["Round 1"]. verified: the Edit added text after the last line only
- workspace: agentville:workspace (plugin-default). verified: Skill(agentville:context-injection) record
</claims>
<artefacts>location: {{ PROJECT_ROOT }}/.agentville/topics/acme-api-pagination-2026-10-18/draft.md</artefacts>
<open>none</open>
<deviations>none</deviations>
```

`locate` returns only `status`, `outcome` (`no draft for this topic; nothing written` when the location is `none`), `mode: locate`, `workspace` and `location`.

Do:
* `- mode: locate` with `location: none` in `<artefacts>` when `Glob` finds no draft.
* `location: inline`, then `content:` and the draft lines in `<artefacts>`, when no file tool is held.

Don't:
* Add a `decision:` or `next-step:` line.
* Return a relative path or open with a greeting; the reply starts with `<status>`.

When the draft cannot be written, reply with this block only:

```text
<status>blocked | needs-input | failed</status>
<outcome>[ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN]</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]</open>
<deviations>none</deviations>
```
