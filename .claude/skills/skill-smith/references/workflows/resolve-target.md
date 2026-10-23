Used by SKILL.md step 4.

# Input

* **skill-name:** required - default: none - The kebab-case name from SKILL.md step 2, such as `acme-pr-review`.
* **mode:** required - default: none - `compile`, `improve` or `convert`.
* **scope:** required - default: none - `plugin` or `project`; `user` is refused. For improve and convert, the scope `path` lives in.
* **path:** optional - default: none - The existing skill folder, for improve and convert.
* **replace:** optional - default: no - `yes` lets install overwrite an existing skill.

# Process

### 1. Choose the scope

There are two scopes and no other choice. For improve and convert, use `path` as the target, set `replace` to yes and go to step 3; when `path` is in neither `{{ PROJECT_ROOT }}/plugins/agentville/skills/` nor `{{ PROJECT_ROOT }}/.claude/skills/`, return `status: blocked` with `reason: improve and convert work only on a skill in the Agentville plugin or the project skills folder`. For compile, when `scope` is missing, ask "Is the skill for the plugin or the project?" with `AskUserQuestion` and exactly two options, `plugin` and `project`, when a person is reachable; otherwise return `status: needs-input` with `missing: scope`. The recommended option is `plugin` when the request is about the Agentville plugin itself and `project` otherwise. For `plugin`, run `Glob` on `{{ PROJECT_ROOT }}/plugins/agentville/.claude-plugin/plugin.json`; when it does not match, return `status: blocked` with `reason: no Agentville plugin at {{ PROJECT_ROOT }}/plugins/agentville`. Any other value, such as `user`, another plugin or a typed folder, returns `status: blocked` with `reason: scope must be plugin or project`.

Do:
* No `scope`, a request not about the Agentville plugin and a person reachable: ask with `project (Recommended)` and `plugin`.
* No person reachable and no `scope`: return `status: needs-input` and `missing: scope`.

Don't:
* Offer `user`, another plugin or a typed directory; offer the two scopes only, as the first Do item shows.
* Ask when no person is reachable; return `needs-input`, as the second Do item shows.

### 2. Build the path

Set the target to `{{ PROJECT_ROOT }}/plugins/agentville/skills/<skill-name>` for `plugin` or `{{ PROJECT_ROOT }}/.claude/skills/<skill-name>` for `project`.

Do:
* `acme-pr-review` with scope `plugin` gives `{{ PROJECT_ROOT }}/plugins/agentville/skills/acme-pr-review`.
* `naming-rules` with scope `project` gives `{{ PROJECT_ROOT }}/.claude/skills/naming-rules`.

Don't:
* Write a host path such as a home folder spelt out; use the placeholder form the Do items show.
* Add a version to the folder name; the folder is the skill name only.

### 3. Check for an existing skill

Run `Glob` on `<path>/SKILL.md`; a match means the target exists. When it exists and `replace` is no, ask "New name, overwrite or cancel?" with `AskUserQuestion` when a person is reachable; otherwise return `status: needs-input` with `missing: replace`. A new name repeats steps 1 to 3 and, once drafted, also updates `name:` in `<STAGING>/SKILL.md`. Overwrite sets `replace` to yes. Cancel returns `status: blocked` so SKILL.md cleans up and stops. This workflow only reads; it writes nothing under the target.

Do:
* Return `exists: yes` and `replace: yes` after the user picks overwrite.
* Return `exists: no` and `replace: no` for a new name with no folder.

Don't:
* Write under the target at this step; install owns all writes.
* Overwrite silently when `replace` is no; ask or return `needs-input`, as this step says.

# Output

Reply with this block, or with the failure block when the target is not settled.

```text
path: {{ PROJECT_ROOT }}/plugins/agentville/skills/<skill-name> | {{ PROJECT_ROOT }}/.claude/skills/<skill-name>
scope: plugin | project
exists: yes | no
replace: yes | no
```

Do:
* `path: {{ PROJECT_ROOT }}/.claude/skills/naming-rules` with `scope: project`.
* `exists: yes` and `replace: yes` for an improve.

Don't:
* Print `exists: yes` with `replace: no`; settle the conflict first, as step 3 says.
* Add a line the template lacks; return the four fields only.

```text
status: blocked | needs-input
reason: <one sentence>
missing: <scope or replace, for needs-input; otherwise none>
```
