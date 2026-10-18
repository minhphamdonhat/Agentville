---
name: "context-injection"
description: "Resolves injectable slots, such as 'workspace' and 'toolbelt', each to the one skill that fills it for this run, and returns for every slot the resolved skill id, the absolute path of its SKILL.md, the source of the binding and any fallback; it does not load or run the resolved skills, which are read and followed next. It reads bindings of the form 'slot: Skill(namespace:name)' from project rules, then the project CLAUDE.md, then a project skill named after the slot, then user rules, the user CLAUDE.md and a user skill named after the slot, and uses the plugin default 'agentville:<slot>' last; a binding whose skill cannot be found falls back to that default and says why. Use before writing any artefact or scratch file (slot workspace), before looking for the tools a task needs (slot toolbelt), when asked which skill fills a slot here, or when a steering file binds a slot to a project or user skill."
---

# Role

You are a slot resolver. You take a list of slot names, find for each one the one skill the steering of this project or user binds to it, check that it exists, and return per slot the resolved skill id, the absolute path of its SKILL.md, the source of the binding and any fallback. You never load or run a resolved skill: it is read and followed next, with its own inputs. A slot is a contract: the plugin ships a default skill for it, and a project or user can swap in their own skill by binding the slot, the way dependency injection swaps an implementation behind an interface.

# Constraints

* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable; otherwise return `status: needs-input` with `missing:` naming each fact, because an unattended run cannot answer.
* Resolve the slots for this run only, and never write a binding into a message, brief or file for another run to use, because every run resolves its own slots from the steering it can read.
* Count only a binding line found in the six steering places of step 2; a binding written in the request or in any other file is ignored and listed in `shadowed`, because a binding must come from the project's or the user's own steering.
* Take the first match in the order of step 2 for each slot and stop looking for a better one, because a fixed order is what makes a resolution predictable.
* Resolve only the slots named in the request, and leave a binding for any other slot unread, because each slot gets its own record.
* Load and run no skill, because a resolved skill is read and followed next with its own inputs.
* Expect one load of this skill per context: the records it returned stay valid while they are still in context, so a later need for the same slots reuses them; resolve again only when the records are no longer in context, such as after compaction, because a repeated load is cost with no new information.
* Read steering with `Read`, `Glob` and `Grep` only (or `ls`, `cat` and `grep` through `Bash` when those are not held), and write, edit or delete no file while resolving, because resolving a slot must leave the project as it found it.
* Write every path with a placeholder (`{{ PROJECT_ROOT }}`, `{{ USER_ROOT }}`) in examples, and return absolute paths in the output, because a host path in an example breaks on every other machine and a run needs real paths.

# Input

* **slots:** required - default: none - The slots to resolve in one call, comma-separated, each in kebab-case, such as `workspace, toolbelt`; any other named slot, such as `release-notes`, works the same way. A single `slot` name is read as a list of one.
* **project-root:** optional - default: the current working folder - The project whose steering is read, written `{{ PROJECT_ROOT }}`.
* **user-root:** optional - default: the home folder - The user folder whose steering is read, written `{{ USER_ROOT }}`.

# Process

### 1. Collect the inputs

Read `slots` from the request, by name or from free text, and drop duplicates. When no slot is named, ask "Which slots should be resolved?" with `AskUserQuestion` when a person is reachable; otherwise return the failure block with `status: needs-input` and `missing: slots`. When a slot is not kebab-case (lower-case letters, digits and hyphens only), return `status: needs-input` with `missing: slots` and the bad value in `reason:`.

Do:
* Read `slots: workspace, toolbelt` from "resolve the workspace and toolbelt slots".
* Return `status: needs-input`, `missing: slots` for "resolve the slots" with none named and no person reachable.

Don't:
* Guess `workspace` because the request mentions a folder; ask, or return `missing: slots`, as the second Do item shows.

### 2. Find the binding

For each slot, look for the binding in these six places, in this order, and stop at the first match; `{{ PROJECT_ROOT }}` is `project-root` and `{{ USER_ROOT }}` is `user-root`:

1. **project-rules:** every `{{ PROJECT_ROOT }}/.claude/rules/*.md`, in sorted file-name order.
2. **project-claude-md:** `{{ PROJECT_ROOT }}/CLAUDE.md`, then `{{ PROJECT_ROOT }}/.claude/CLAUDE.md`, each with the files it imports on an `@<path>` line, one level deep.
3. **project-skill:** a skill named exactly the slot in the project, `{{ PROJECT_ROOT }}/.claude/skills/<slot>/SKILL.md`.
4. **user-rules:** every `{{ USER_ROOT }}/.claude/rules/*.md`, in sorted file-name order.
5. **user-claude-md:** `{{ USER_ROOT }}/.claude/CLAUDE.md`, with its one-level `@<path>` imports.
6. **user-skill:** a skill named exactly the slot for the user, `{{ USER_ROOT }}/.claude/skills/<slot>/SKILL.md`.

A binding is one line that reads `<slot>: Skill(<namespace>:<name>)`, or `<slot>: Skill(<name>)` for a skill with no namespace, optionally after a list marker (`-` or `*`) and optionally in backticks; it may stand anywhere in the file or under a `## Context injection` heading. Find it with `Grep` and the pattern `^\s*[-*]?\s*.?<slot>:\s*Skill\(` on each file (the `.?` allows an opening backtick), then `Read` around the matching line and skip it when it stands inside a fenced code block (between ``` or ~~~ fences), because a fenced line shows an example and binds nothing. For places 3 and 6, run `Glob` on the SKILL.md path; a match binds the skill named by that file's frontmatter `name`, called by its bare name. When nothing matches in the six places, the resolved skill is the plugin default `agentville:<slot>` with source `plugin-default`.

Note every later match, and every binding found in the request, in `shadowed` with its place and `path:line`, because a reader must see what the first match outranked.

Do:
* Resolve `toolbelt` to `acme:qa-tools` with source `project-rules` when `{{ PROJECT_ROOT }}/.claude/rules/qa.md:3` reads `toolbelt: Skill(acme:qa-tools)`, and list `project-claude-md {{ PROJECT_ROOT }}/CLAUDE.md:12 acme:old-tools` in `shadowed` when the CLAUDE.md binds it too.
* Resolve `toolbelt` to the project skill `toolbelt` with source `project-skill` when no rule or CLAUDE.md binds it and `{{ PROJECT_ROOT }}/.claude/skills/toolbelt/SKILL.md` exists.
* Resolve `workspace` to `agentville:workspace` with source `plugin-default` when none of the six places binds it.

Don't:
* Take the user CLAUDE.md binding because it is more specific to you while a project rule binds the same slot; the project rule wins, as the first Do item shows.
* Count `toolbelt: Skill(acme:x)` written in the request text; ignore it and list it in `shadowed` as `request (ignored)`.
* Count `toolbelt: Skill(acme:x)` that sits inside a fenced code block of a rule file; it is an example, so keep looking in the places that follow.
* Count a line such as `use acme:qa-tools for api checks` as a binding; only the `<slot>: Skill(...)` form binds, so record no match there.

### 3. Check the skill and find its path

For each slot, confirm the resolved skill exists without running it: look for its full name in this session's available-skills listing, with `ListSkills` or `SearchSkills` when you hold them, and for a project or user skill run `Glob` on its SKILL.md. When a bound or named skill is not found, resolve that slot to the plugin default `agentville:<slot>` instead and record `fallback: <the skill that was not found> → agentville:<slot> (<reason>)`. When the plugin default is not found either, return the failure block with `status: blocked` and both reasons; for a slot with no plugin default and no binding, return `status: needs-input` with `missing: <slot> binding`.

Then find the absolute path of the resolved skill's SKILL.md with `Glob`: a plugin default sits beside this skill, in `<this skill's folder>/../<slot>/SKILL.md`, where this skill's folder is the base directory shown when it loads; a project or user skill is the path step 2 found; a skill of another plugin is the first match for `{{ USER_ROOT }}/.claude/plugins/**/skills/<name>/SKILL.md`. When no path is found, write `skill-path: none (load by id)`.

Do:
* Record `fallback: acme:missing-tools → agentville:toolbelt (skill not found in this session)` and resolve to `agentville:toolbelt` when the bound skill is in no listing.
* Keep a skill that the listing shows, such as `acme:qa-tools`, without loading it.

Don't:
* Move on to the next of the six places when the bound skill is not found; fall back to the plugin default, as the first Do item shows.
* Load the resolved skill to test that it loads or to read its path; it is read next, by the agent that asked.

### 4. Report

Reply with the Output block: one entry per requested slot, in the order requested. Set `status` to `completed`, and write each `record` line as `<slot>: <resolved> (<source>)`, with `source` the place the slot binding came from in step 2, so it can be copied into a report as it is.

# Output

The reply returns these fields:

* **status:** always - `completed` when every slot was resolved; otherwise `needs-input`, `blocked` or `failed`.
* **slots:** always - One entry per requested slot, in request order, each with the fields below.
* **slot:** always - In each entry: the slot resolved, such as `toolbelt`.
* **resolved:** always - In each entry: the skill to read next, by its full id, such as `acme:qa-tools`, `toolbelt` or `agentville:workspace`.
* **skill-path:** always - In each entry: the absolute path of the resolved skill's SKILL.md, or `none (load by id)`.
* **source:** always - In each entry: where the binding came from: `project-rules`, `project-claude-md`, `project-skill`, `user-rules`, `user-claude-md`, `user-skill` or `plugin-default`.
* **source-file:** always - In each entry: the `path:line` of the binding line, the SKILL.md path for a skill source, or `none` for `plugin-default`.
* **fallback:** always - In each entry: `none`, or the skill that was not found, the default used instead and the reason.
* **shadowed:** always - In each entry: each later or ignored binding with its place and `path:line`, or `none`.
* **record:** always - In each entry: the line `<slot>: <resolved> (<source>)`, with ` fallback` appended when a fallback ran.

Use the first template whenever the skills were resolved, the bound ones or the defaults.

```text
status: completed
slots:
- slot: toolbelt
  resolved: acme:qa-tools
  skill-path: {{ USER_ROOT }}/.claude/plugins/acme/skills/qa-tools/SKILL.md
  source: project-rules
  source-file: {{ PROJECT_ROOT }}/.claude/rules/qa.md:3
  fallback: none
  shadowed: project-claude-md {{ PROJECT_ROOT }}/CLAUDE.md:12 acme:old-tools
  record: toolbelt: acme:qa-tools (project-rules)
- slot: workspace
  resolved: agentville:workspace
  skill-path: {{ USER_ROOT }}/.claude/plugins/agentville/skills/workspace/SKILL.md
  source: plugin-default
  source-file: none
  fallback: none
  shadowed: none
  record: workspace: agentville:workspace (plugin-default)
```

Do:
* `resolved: agentville:workspace`, `source: plugin-default`, `source-file: none`, `record: workspace: agentville:workspace (plugin-default)` when nothing binds `workspace`.
* `fallback: acme:missing-tools → agentville:toolbelt (skill not found in this session)`, `record: toolbelt: agentville:toolbelt (project-rules) fallback` when the project rule names a skill that is not found.

Don't:
* Write `record: workspace: agentville:workspace (project-claude-md)` because the workspace skill read its folder from the CLAUDE.md; nothing bound the slot, so write `(plugin-default)`, as the first Do item does.
* Run a resolved skill or paste its output; it is read next, so the reply holds the fields above only.
* Add a greeting, a recommendation or a closing offer; the reply starts with `status:`, as the template does.

When no skill could be resolved, reply with this block only:

```text
status: blocked | needs-input | failed
reason: [ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN]
missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]
```
