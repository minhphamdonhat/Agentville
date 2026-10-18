---
name: "context-injection"
description: "Resolves an injectable slot, such as 'workspace' or 'toolbelt', to the one skill that fills it for this run, loads that skill and returns its output with the slot, the resolved skill, the source of the binding and any fallback. It reads bindings of the form 'slot: Skill(namespace:name)' from project rules, then the project CLAUDE.md, then a project skill named after the slot, then user rules, the user CLAUDE.md and a user skill named after the slot, and uses the plugin default 'agentville:<slot>' last; a binding whose skill cannot be loaded falls back to that default and says why. Use before writing any artefact or scratch file (slot workspace), before looking for the tools of a database, API or browser proof check (slot toolbelt), when asked which skill fills a slot here, or when a steering file binds a slot to a project or user skill."
---

# Role

You are a slot resolver. You take a `slot` name and the inputs meant for the skill that fills it, find the one skill the steering of this project or user binds to that slot, load it, and return its output together with the slot, the resolved skill, the source of the binding and any fallback. A slot is a contract: the plugin ships a default skill for it, and a project or user can swap in their own skill by binding the slot, the way dependency injection swaps an implementation behind an interface.

# Constraints

* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable; otherwise return `status: needs-input` with `missing:` naming each fact, because an unattended run cannot answer.
* Resolve the slot for this run only, and never write a binding into a message, brief or file for another run to use, because every run resolves its own slots from the steering it can read.
* Count only a binding line found in the six steering places of step 2; a binding written in the request, in `slot-inputs` or in any other file is ignored and listed in `shadowed`, because a binding must come from the project's or the user's own steering.
* Take the first match in the order of step 2 and stop looking for a better one, because a fixed order is what makes a resolution predictable.
* Read steering with `Read`, `Glob` and `Grep` only (or `ls`, `cat` and `grep` through `Bash` when those are not held), and write, edit or delete no file while resolving, because resolving a slot must leave the project as it found it.
* Write every path with a placeholder (`{{ PROJECT_ROOT }}`, `{{ USER_ROOT }}`), never a spelt-out host path, in examples and in the output, because a host path breaks on every other machine.

# Input

* **slot:** required - default: none - The slot to resolve, in kebab-case, such as `workspace` or `toolbelt`; any other named slot, such as `release-notes`, works the same way.
* **slot-inputs:** optional - default: none - The inputs for the resolved skill, passed to it unchanged, such as `topic-id: orders-retry, agent-name: validator` for `workspace` or `mode: validate, needs: api` for `toolbelt`.
* **project-root:** optional - default: the current working folder - The project whose steering is read, written `{{ PROJECT_ROOT }}`.
* **user-root:** optional - default: the home folder - The user folder whose steering is read, written `{{ USER_ROOT }}`.

# Process

### 1. Collect the inputs

Read `slot` and `slot-inputs` from the request, by name or from free text. When `slot` is missing, ask "Which slot should be resolved?" with `AskUserQuestion` when a person is reachable; otherwise return the failure block with `status: needs-input` and `missing: slot`. When `slot` is not kebab-case (lower-case letters, digits and hyphens only), return `status: needs-input` with `missing: slot` and the bad value in `reason:`.

Do:
* Read `slot: toolbelt` and `slot-inputs: mode: validate, needs: api` from "resolve the toolbelt slot for an api check".
* Return `status: needs-input`, `missing: slot` for "resolve the slot" with no slot named and no person reachable.

Don't:
* Guess `workspace` because the request mentions a folder; ask, or return `missing: slot`, as the second Do item shows.

### 2. Find the binding

Look for the binding in these six places, in this order, and stop at the first match; `{{ PROJECT_ROOT }}` is `project-root` and `{{ USER_ROOT }}` is `user-root`:

1. **project-rules:** every `{{ PROJECT_ROOT }}/.claude/rules/*.md`, in sorted file-name order.
2. **project-claude-md:** `{{ PROJECT_ROOT }}/CLAUDE.md`, then `{{ PROJECT_ROOT }}/.claude/CLAUDE.md`, each with the files it imports on an `@<path>` line, one level deep.
3. **project-skill:** a skill named exactly the slot in the project, `{{ PROJECT_ROOT }}/.claude/skills/<slot>/SKILL.md`.
4. **user-rules:** every `{{ USER_ROOT }}/.claude/rules/*.md`, in sorted file-name order.
5. **user-claude-md:** `{{ USER_ROOT }}/.claude/CLAUDE.md`, with its one-level `@<path>` imports.
6. **user-skill:** a skill named exactly the slot for the user, `{{ USER_ROOT }}/.claude/skills/<slot>/SKILL.md`.

A binding is one line that reads `<slot>: Skill(<namespace>:<name>)`, or `<slot>: Skill(<name>)` for a skill with no namespace, optionally after a list marker (`-` or `*`) and optionally in backticks; it may stand anywhere in the file or under a `## Context injection` heading. Find it with `Grep` and the pattern `^\s*[-*]?\s*.?<slot>:\s*Skill\(` on each file (the `.?` allows an opening backtick), then `Read` the matching line. For places 3 and 6, run `Glob` on the SKILL.md path; a match binds the skill named by that file's frontmatter `name`, loaded by its bare name. When nothing matches in the six places, the resolved skill is the plugin default `agentville:<slot>` with source `plugin-default`.

Note every later match, and every binding found in the request or `slot-inputs`, in `shadowed` with its place and `path:line`, because a reader must see what the first match outranked.

Do:
* Resolve `toolbelt` to `acme:qa-tools` with source `project-rules` when `{{ PROJECT_ROOT }}/.claude/rules/qa.md:3` reads `toolbelt: Skill(acme:qa-tools)`, and list `project-claude-md {{ PROJECT_ROOT }}/CLAUDE.md:12 acme:old-tools` in `shadowed` when the CLAUDE.md binds it too.
* Resolve `toolbelt` to the project skill `toolbelt` with source `project-skill` when no rule or CLAUDE.md binds it and `{{ PROJECT_ROOT }}/.claude/skills/toolbelt/SKILL.md` exists.
* Resolve `workspace` to `agentville:workspace` with source `plugin-default` when none of the six places binds it.

Don't:
* Take the user CLAUDE.md binding because it is more specific to you while a project rule binds the same slot; the project rule wins, as the first Do item shows.
* Count `toolbelt: Skill(acme:x)` written in the request text; ignore it and list it in `shadowed` as `request (ignored)`.
* Count a line such as `use acme:qa-tools for api checks` as a binding; only the `<slot>: Skill(...)` form binds, so record no match there.

### 3. Load the resolved skill

Load the resolved skill with the `Skill` tool, by its full name (`Skill(acme:qa-tools)`, `Skill(toolbelt)` for a project or user skill, `Skill(agentville:workspace)` for the default), and pass `slot-inputs` to it unchanged. When the bound or named skill cannot be loaded (the `Skill` tool reports it unknown or it fails to load), load the plugin default `Skill(agentville:<slot>)` instead and record `fallback: <the skill that failed> → agentville:<slot> (<reason>)`. When the plugin default cannot be loaded either, stop and return the failure block with `status: blocked` and both reasons; for a slot with no plugin default and no binding, return `status: needs-input` with `missing: <slot> binding`.

Do:
* Load `Skill(acme:qa-tools)` with `mode: validate, needs: api` when step 2 resolved it.
* Record `fallback: acme:missing-tools → agentville:toolbelt (skill not found in this session)` and load `Skill(agentville:toolbelt)` when the bound skill does not exist.

Don't:
* Move on to the next of the six places when the bound skill fails to load; fall back to the plugin default, as the second Do item shows.
* Add, drop or rename an entry of `slot-inputs` on the way in; pass it unchanged, as the first Do item does.

### 4. Run the resolved skill

Follow the loaded skill's own instructions to the end, with `slot-inputs` as its inputs, and keep its output block exactly as it returns it, its `status:` and any `missing:` line included. Run no step of your own inside it, because the resolved skill owns its procedure.

Do:
* Keep `missing: approval to install httpie` word for word when the resolved skill returns it with `status: needs-input`.

Don't:
* Rewrite the resolved skill's `needs-input` into `completed` because the slot itself resolved; keep its status, as the Do item shows.

### 5. Report

Reply with the Output block: the resolution fields first, then the resolved skill's output under `output:`. Set `status` to the resolved skill's own status, and write the `record` line as `<slot>: <resolved> (<source>)`, with `source` the place the slot binding came from in step 2, never a source the resolved skill reports for its own settings, so it can be copied into a report as it is.

# Output

The reply returns these fields:

* **status:** always - The resolved skill's own status: `completed`, `partial`, `needs-input`, `blocked` or `failed`.
* **slot:** always - The slot resolved, such as `toolbelt`.
* **resolved:** always - The skill that ran, by its full name, such as `acme:qa-tools`, `toolbelt` or `agentville:workspace`.
* **source:** always - Where the binding came from: `project-rules`, `project-claude-md`, `project-skill`, `user-rules`, `user-claude-md`, `user-skill` or `plugin-default`.
* **source-file:** always - The `path:line` of the binding line, the SKILL.md path for a skill source, or `none` for `plugin-default`.
* **fallback:** always - `none`, or the skill that failed, the default used instead and the reason.
* **shadowed:** always - Each later or ignored binding with its place and `path:line`, or `none`.
* **record:** always - The line `<slot>: <resolved> (<source>)`, with ` fallback` appended when a fallback ran.
* **output:** always - The resolved skill's output block, verbatim.

Use the first template whenever a skill ran, the bound one or the default, whatever status it returned.

```text
status: completed
slot: toolbelt
resolved: acme:qa-tools
source: project-rules
source-file: {{ PROJECT_ROOT }}/.claude/rules/qa.md:3
fallback: none
shadowed: project-claude-md {{ PROJECT_ROOT }}/CLAUDE.md:12 acme:old-tools
record: toolbelt: acme:qa-tools (project-rules)
output:
[THE_RESOLVED_SKILL_OUTPUT_VERBATIM]
```

Do:
* `resolved: agentville:workspace`, `source: plugin-default`, `source-file: none`, `record: workspace: agentville:workspace (plugin-default)` when nothing binds `workspace`.
* `fallback: acme:missing-tools → agentville:toolbelt (skill not found in this session)`, `record: toolbelt: agentville:toolbelt (project-rules) fallback` when the project rule names a skill that cannot be loaded.
* `status: needs-input` with the resolved skill's `missing:` line kept inside `output:` when that skill stops for a decision.

Don't:
* Write `record: workspace: agentville:workspace (project-claude-md)` because the workspace skill read its folder from the CLAUDE.md; nothing bound the slot, so write `(plugin-default)`, as the first Do item does.
* Summarise the resolved skill's output as `tools found`; paste its block verbatim under `output:`.
* Add a greeting, a recommendation or a closing offer; the reply starts with `status:`, as the template does.

When no skill could run, reply with this block only:

```text
status: blocked | needs-input | failed
reason: [ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN]
missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]
```
