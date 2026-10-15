Used by SKILL.md step 4.

# Input

* **skill-name:** required - default: none - The kebab-case name from SKILL.md step 2, such as `pr-review`.
* **mode:** required - default: none - `compile`, `improve` or `convert`.
* **location:** optional - default: ask - `user` or `project`.
* **path:** optional - default: none - The existing skill folder, for improve and convert.
* **replace:** optional - default: no - `yes` lets install overwrite an existing skill.

# Process

### 1. Choose the location

For improve and convert, use `path` as the target, set `replace` to yes and go to step 3. For compile, run `Glob` on `{{ PROJECT_ROOT }}/.git/HEAD`; a match means the project is a repository. When `location` is ask and the project is a repository, ask "Is the skill for the user or the project?" with `AskUserQuestion` when a person is reachable; otherwise return `status: needs-input` with `missing: location`. When `location` is ask and the project is not a repository, use `user`.

Do:
* No `.git/HEAD` and location ask: use `user` without asking.
* No person reachable, a repository and location ask: return `status: needs-input` and `missing: location`.

Don't:
* Ask when the project is not a repository; use `user`, as the first Do item shows.
* Ask when no person is reachable; return `needs-input`, as the second Do item shows.

### 2. Build the path

Set the target to `{{ USER_ROOT }}/.claude/skills/<skill-name>` for `user` or `{{ PROJECT_ROOT }}/.claude/skills/<skill-name>` for `project`.

Do:
* `pr-review` with location `user` gives `{{ USER_ROOT }}/.claude/skills/pr-review`.
* `naming-rules` with location `project` gives `{{ PROJECT_ROOT }}/.claude/skills/naming-rules`.

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
location: user | project
exists: yes | no
replace: yes | no
```

Do:
* `path: {{ PROJECT_ROOT }}/.claude/skills/naming-rules` with `location: project`.
* `exists: yes` and `replace: yes` for an improve.

Don't:
* Print `exists: yes` with `replace: no`; settle the conflict first, as step 3 says.
* Add a line the template lacks; return the four fields only.

```text
status: blocked | needs-input
reason: <one sentence>
missing: <location or replace, for needs-input; otherwise none>
```
