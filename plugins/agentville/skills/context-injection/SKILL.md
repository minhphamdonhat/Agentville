---
name: "context-injection"
description: "Resolves injectable slots, such as 'workspace' and 'toolbelt', each to the one skill that fills it: the id, the absolute SKILL.md path, the binding's source and any fallback. Reads bindings ('slot: Skill(namespace:name)') from project and user steering files, else the plugin default 'agentville:{slot}'; with no readable files it returns the defaults. Use before a slot's skill, or when asked which skill fills a slot."
metadata:
  version: 2.0.1
---

# Role

You are a slot resolver. You take a list of slot names, find for each the one skill the project or user steering binds to it, check that it exists, and return its id, SKILL.md path, binding source and any fallback. A slot is a contract with a plugin default; a project or user can bind their own skill to it, as dependency injection swaps an implementation. You load and run no resolved skill: it is read and followed next, with its own inputs. The resolved skill is the only skill that fills the slot: the reader of the record loads that one skill and no other.

# Constraints

* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable and `AskUserQuestion` is held; otherwise return `<status>needs-input</status>` with `<open>` beginning `missing:` and naming each fact.
* Resolve for this run only and write no binding into a message or file, because every run resolves its own slots.
* Count only a binding line found in the six places of step 2. A binding in the request, in a custom instruction typed in a chat settings page, or in any other file is not read; list a request binding in `shadowed` as `request (ignored)`, because a binding must come from steering files.
* Take the first match in step 2's order and stop, because a fixed order makes a resolution predictable.
* Resolve only the slots named, and leave other bindings unread.
* Read steering with `Read`, `Glob` and `Grep` only (or `ls`, `cat` and `grep` through `Bash`, or `Get-ChildItem`, `Get-Content` and `Select-String` in PowerShell, when those are not held), and write, edit or delete nothing, because resolving must leave the project as found.
* Look only at the six places, each by its own path or pattern, and never list a folder (`**/*`, `ls -R`, `find`), because a listing reaches files that are not steering.
* Write placeholders (`{{ PROJECT_ROOT }}`, `{{ USER_ROOT }}`) in examples and return absolute paths in the output.
* The resolved skill is the only skill that fills the slot: hand it back as the one skill to read, name the plugin default `agentville:<slot>` only as `resolved` after a fallback, and let the reader load the plugin default only when the record names it as the fallback because the resolved skill failed to load, because two skills for one slot would give two contracts.
* Resolve once per context: the records stay valid while in context, so reuse them; resolve again only after compaction.

# Input

* **slots:** required - default: none - The slots, comma-separated, in kebab-case, such as `workspace, toolbelt`; any named slot works the same way. One name is a list of one.
* **project-root:** optional - default: the current working folder - Written `{{ PROJECT_ROOT }}`. With no working folder at all (a chat with no file tools), there is no project.
* **user-root:** optional - default: the home folder - Written `{{ USER_ROOT }}`.

# Process

### 1. Collect the inputs

Read `slots` from the request, by name or from free text, and drop duplicates. When none is named, ask "Which slots should be resolved?" when a person is reachable, else return the failure template with `missing: slots`. A slot that is not kebab-case returns `needs-input` with `missing: slots` in `<open>` and the bad value in `<outcome>`.

Do:
* Read `slots: workspace, toolbelt` from "resolve the workspace and toolbelt slots".

Don't:
* Guess a slot from a folder the request mentions; ask, or return `missing: slots` in `<open>`.

### 2. Find the binding

With no file tool or no readable project or home folder, skip this step: every slot resolves to its plugin default `agentville:<slot>` with source `plugin-default`, and `<deviations>` says "no readable steering; plugin defaults apply".

Otherwise, for each slot look in these six places in order and stop at the first match:

1. **project-rules:** every `{{ PROJECT_ROOT }}/.claude/rules/*.md`, in sorted order.
2. **project-claude-md:** `{{ PROJECT_ROOT }}/CLAUDE.md`, then `{{ PROJECT_ROOT }}/.claude/CLAUDE.md`, each with the files it imports on an `@<path>` line, one level deep.
3. **project-skill:** `{{ PROJECT_ROOT }}/.claude/skills/<slot>/SKILL.md`.
4. **user-rules:** every `{{ USER_ROOT }}/.claude/rules/*.md`, in sorted order.
5. **user-claude-md:** `{{ USER_ROOT }}/.claude/CLAUDE.md`, with its one-level imports.
6. **user-skill:** `{{ USER_ROOT }}/.claude/skills/<slot>/SKILL.md`.

A binding is one line, `<slot>: Skill(<namespace>:<name>)` (or `Skill(<name>)` with no namespace), optionally after a list marker and in backticks, anywhere in the file. Find it with `Grep` and `^\s*[-*]?\s*.?<slot>:\s*Skill\(` on each file, then `Read` around the match and skip it inside a fenced code block, because a fenced line is an example. For places 3 and 6, `Glob` the path; a match binds the skill named by its frontmatter `name`. With no match anywhere, the skill is `agentville:<slot>`, source `plugin-default`.

List every later match in `shadowed` with its place and `path:line`.

Do:
* Resolve `toolbelt` to `acme:qa-tools` (`project-rules`) when `{{ PROJECT_ROOT }}/.claude/rules/qa.md:3` reads `toolbelt: Skill(acme:qa-tools)`, and list a CLAUDE.md binding of the same slot in `shadowed`.

Don't:
* Take a user binding while a project file binds the same slot.
* Count `toolbelt: Skill(acme:x)` in the request or in a fenced block.
* Count prose such as `use acme:qa-tools for api checks`; only the `<slot>: Skill(...)` form binds.

### 3. Check the skill and find its path

Confirm each resolved skill exists without running it: look for its full name in this session's available-skills listing (or `ListSkills`/`SearchSkills` when held), and `Glob` a project or user skill's SKILL.md. When a bound skill is not found, resolve to `agentville:<slot>` and record `fallback: <missing skill> → agentville:<slot> (<reason>)`. When the default is not found either, return `<status>blocked</status>` with both reasons in `<outcome>`; a slot with no default and no binding returns `needs-input` with `missing: <slot> binding` in `<open>`.

Then find the SKILL.md path with `Glob`: a plugin default sits at `<this skill's folder>/../<slot>/SKILL.md` (this skill's folder is the base directory shown when it loads); a project or user skill is the path step 2 found; another plugin's skill is the first match for `{{ USER_ROOT }}/.claude/plugins/**/skills/<name>/SKILL.md`. With no path, write `none (load by id)`.

Do:
* Record `fallback: acme:missing-tools → agentville:toolbelt (skill not found in this session)` when a bound skill is in no listing.

Don't:
* Move to the next place when a bound skill is missing; fall back to the default.
* Load the skill to test it or read its path.

### 4. Report

Reply with the Output block, one entry per slot in request order, `<status>completed</status>`.

Do:
* Copy each `record` line into a report as it is.

Don't:
* Add fields beyond the Output list.

# Output

* **status:** always - In `<status>`: `completed`, else `needs-input`, `blocked` or `failed`.
* **outcome:** always - In `<outcome>`: one sentence naming how many slots resolved and to which skills, or what stopped the run.
* **slots:** always - In `<claims>`: one `- slots: [...]` line holding a minified JSON array, one object per slot in request order, each with `slot`, `resolved` (full skill id), `source` (`project-rules`, `project-claude-md`, `project-skill`, `user-rules`, `user-claude-md`, `user-skill` or `plugin-default`), `source-file` (the binding's `path:line`, the SKILL.md path for a skill source, or `none`), `fallback` (`none`, or the skill not found, the default used and the reason) and `shadowed` (later or ignored bindings with place and `path:line`, or `none`); labelled `verified`, with the binding's `path:line` as evidence or, when nothing bound, the six places searched.
* **record:** always - In `<claims>`: one `- record: <slot>: <resolved> (<source>)` line per slot, with ` fallback` appended when a fallback ran, labelled `verified` with the same evidence.
* **skill-path:** always - In `<artefacts>`: one `skill-path: <slot> <path>` line per slot, the absolute SKILL.md path or `none (load by id)`.
* **open:** always - In `<open>`: `none` when the status is `completed`.
* **deviations:** always - In `<deviations>`: each fallback and the no-steering note of step 2, or `none`.

```text
<status>completed</status>
<outcome>2 slots resolved: toolbelt to acme:qa-tools, workspace to agentville:workspace.</outcome>
<claims>
- slots: [{"slot":"toolbelt","resolved":"acme:qa-tools","source":"project-rules","source-file":"{{ PROJECT_ROOT }}/.claude/rules/qa.md:3","fallback":"none","shadowed":"project-claude-md {{ PROJECT_ROOT }}/CLAUDE.md:12 acme:old-tools"},{"slot":"workspace","resolved":"agentville:workspace","source":"plugin-default","source-file":"none","fallback":"none","shadowed":"none"}]. verified: {{ PROJECT_ROOT }}/.claude/rules/qa.md:3 binds toolbelt; no workspace binding in the six places
- record: toolbelt: acme:qa-tools (project-rules). verified: {{ PROJECT_ROOT }}/.claude/rules/qa.md:3
- record: workspace: agentville:workspace (plugin-default). verified: no binding in the six places
</claims>
<artefacts>
skill-path: toolbelt {{ USER_ROOT }}/.claude/plugins/acme/skills/qa-tools/SKILL.md
skill-path: workspace <this skill's folder>/../workspace/SKILL.md, as an absolute path
</artefacts>
<open>none</open>
<deviations>none</deviations>
```

`resolved` is the only skill that fills its slot. The reader loads that one skill, by its id, else by its `skill-path`, and loads the plugin default `agentville:<slot>` only when the record names it as the fallback because the resolved skill failed to load.

Do:
* Load only `resolved`, by id, else by its `skill-path`, never both: for `"resolved":"acme:qa-tools"` load `acme:qa-tools`, else read `{{ USER_ROOT }}/.claude/plugins/acme/skills/qa-tools/SKILL.md`.
* Write `- record: toolbelt: agentville:toolbelt (project-rules) fallback` when a rule names a skill that is not found.
* Write `(plugin-default)` for a slot nothing bound, even when the default skill reads a folder from a CLAUDE.md.

Don't:
* Run a resolved skill or paste its output.
* Load `agentville:toolbelt` after a resolution to `acme:qa-tools`; the default is loaded only when `resolved` is the default and `fallback` names the skill that failed to load.
* Add a greeting, recommendation or closing offer; the reply starts with `<status>`.

When no skill could be resolved, reply with this block only:

```text
<status>blocked | needs-input | failed</status>
<outcome>[ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN]</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]</open>
<deviations>none</deviations>
```
