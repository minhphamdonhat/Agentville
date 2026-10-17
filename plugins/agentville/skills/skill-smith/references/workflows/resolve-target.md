Used by SKILL.md step 4.

# Input

* **skill-name:** required - default: none - The kebab-case name from SKILL.md step 2, such as `pr-review`.
* **mode:** required - default: none - `compile`, `improve` or `convert`.
* **scope:** required - default: none - `project` or `user`; for improve and convert, the scope `path` lives in.
* **path:** optional - default: none - The existing skill folder, for improve and convert.
* **replace:** optional - default: no - `yes` lets install overwrite an existing skill.

# Process

### 1. Choose the scope

There are two scopes and no other choice. For improve and convert, use `path` as the target, set `replace` to yes and go to step 3; when `path` is inside a plugin (the path has a `.claude-plugin` component, or an ancestor folder holds `.claude-plugin/plugin.json`) or in neither skills folder, return `status: blocked` with that reason. For compile, when `scope` is missing, ask "Is the skill for the project or the user?" with `AskUserQuestion` and exactly two options, `project` and `user`, when a person is reachable; otherwise return `status: needs-input` with `missing: scope`. Run `Glob` on `{{ PROJECT_ROOT }}/.git/HEAD` only to pick the recommended option: `project` when it matches, `user` otherwise. Any other value, such as a plugin or a typed folder, returns `status: blocked` with `reason: scope must be project or user`.

Do:
* No `scope`, a repository and a person reachable: ask with `project (Recommended)` and `user`.
* No person reachable and no `scope`: return `status: needs-input` and `missing: scope`.

Don't:
* Offer a plugin folder or a typed directory; offer the two scopes only, as the first Do item shows.
* Ask when no person is reachable; return `needs-input`, as the second Do item shows.

### 2. Build the path

Set the target to `{{ USER_ROOT }}/.claude/skills/<skill-name>` for `user` or `{{ PROJECT_ROOT }}/.claude/skills/<skill-name>` for `project`.

Do:
* `pr-review` with scope `user` gives `{{ USER_ROOT }}/.claude/skills/pr-review`.
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
path: {{ USER_ROOT }}/.claude/skills/<skill-name>
scope: user | project
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
