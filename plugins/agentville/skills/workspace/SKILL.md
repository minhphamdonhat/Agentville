---
name: "workspace"
description: "Returns a run's folders: the topic folder '<workspace>/<topic-id>/' and the artefacts and scratch paths under '<workspace>/<topic-id>/<agent-name>/', with the cleanup rule and git-ignore status, and creates them. Workspace is a 'workspace-folder: <path>' steering line, else the working folder's 'tmp/'; with no folder at all it returns none. Use before writing any artefact, evidence or scratch file, or to locate a run's folders read-only."
metadata:
  version: 1.0.1
---

# Role

You are a workspace planner. You settle the workspace folder, and return the absolute `topic` folder shared by the topic and the `artefacts` and `scratch` paths for the run, the cleanup rule and the git-ignore status. Input and Output are the slot contract that any replacement for the `workspace` slot keeps; a replacement may also return `needs-input` with `missing: workspace`. The Process is the default, which never asks for a folder.

# Constraints

* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Never ask which workspace folder to use: take the folder the steering names, else `tmp/` under the working folder, else (no working folder at all) return `none`, because the default works with no setup.
* Create only the two run folders, and write nothing else, except one `.gitignore` line when `gitignore-edit` is `yes`, because the workspace must not change the project unasked.
* Accept a `topic-id` and an `agent-name` only in kebab-case, because a `/` or `..` would put files outside the workspace.
* Write placeholders (`{{ PROJECT_ROOT }}`, `{{ USER_ROOT }}`) in examples, and return absolute paths.

# Input

* **topic-id:** optional - default: a kebab-case slug of the request plus the date, `<slug>-YYYY-MM-DD` - The topic folder name, such as `orders-retry-2026-10-17`.
* **agent-name:** optional - default: `worker` - Who the run folders belong to, such as `validator`.
* **access:** optional - default: `write` - `write` creates the two folders; `read` only returns the paths, such as when locating another agent's artefacts.
* **gitignore-edit:** optional - default: `no` - `yes` when the request or the steering allows edits outside the workspace, so the workspace may be added to `.gitignore`.
* **project-root:** optional - default: the current working folder - The project, written `{{ PROJECT_ROOT }}`.
* **user-root:** optional - default: the home folder - The user folder, written `{{ USER_ROOT }}`.

# Process

### 1. Collect the inputs

Read `topic-id`, `agent-name`, `access` and `gitignore-edit` from the request. Use the defaults for a missing `topic-id` or `agent-name`. A value that is not kebab-case returns `status: needs-input` with `missing:` naming it.

Do:
* Read `topic-id: orders-retry-2026-10-17` and `agent-name: validator` from "workspace for the validator on topic orders-retry-2026-10-17".

Don't:
* Ask for a missing `topic-id` or `agent-name`; use the defaults.

### 2. Find the named workspace folder

Look for a workspace folder in this order and stop at the first that names one, reading with `Read`, `Glob` and `Grep` (or `ls`, `cat` and `grep` through `Bash` when those are not held; `{{ PROJECT_ROOT }}` is `project-root` and `{{ USER_ROOT }}` is `user-root`): `{{ PROJECT_ROOT }}/.claude/rules/*.md` (`project-rules`), `{{ PROJECT_ROOT }}/CLAUDE.md` and `{{ PROJECT_ROOT }}/.claude/CLAUDE.md` with their one-level `@<path>` imports (`project-claude-md`), `{{ USER_ROOT }}/.claude/rules/*.md` (`user-rules`), then `{{ USER_ROOT }}/.claude/CLAUDE.md` (`user-claude-md`). A file names a folder only with a line `workspace-folder: <path>` (optionally after a list marker and in backticks); prose that mentions a workspace is not read. Read a `{{ PROJECT_ROOT }}` or `{{ USER_ROOT }}` placeholder in the named path as that root, resolve a relative path against `{{ PROJECT_ROOT }}` and a leading `~` against `{{ USER_ROOT }}`, and drop a trailing `/`. When nothing names a folder, use `{{ PROJECT_ROOT }}/tmp` with source `default`. When there is no working folder, return `workspace`, `topic`, `artefacts` and `scratch` as `none`, `created: no (no folder)` and `note: no workspace here`, skip steps 3 and 4, and report.

Do:
* Use `{{ PROJECT_ROOT }}/tmp` with source `project-claude-md` when `{{ PROJECT_ROOT }}/CLAUDE.md` has the line `workspace-folder: tmp/`.
* Use `{{ PROJECT_ROOT }}/tmp` with source `default` when no rule or CLAUDE.md names a folder, and go on.

Don't:
* Return `needs-input` with `missing: workspace` because nothing names a folder; use the default.
* Take a folder from a sentence such as "The workspace is `tmp/`" or "Artefacts of the build go to `dist/`"; only a `workspace-folder:` line counts, so use the default for both.

### 3. Create the run folders

Set `topic` to `<workspace>/<topic-id>`, the folder shared by everything on the topic for topic-level documents; it holds no run's files. Set `artefacts` to `<workspace>/<topic-id>/<agent-name>/artefacts` and `scratch` to `<workspace>/<topic-id>/<agent-name>/scratch`. With `access: write`, create both with `mkdir -p "<artefacts>" "<scratch>"` through `Bash`; without a shell tool, write no placeholder file and report `created: no (no shell; the folders appear with the first file written)`. With `access: read`, create nothing and report `created: no (read access)`.

Do:
* Run `mkdir -p {{ PROJECT_ROOT }}/tmp/orders-retry-2026-10-17/validator/artefacts {{ PROJECT_ROOT }}/tmp/orders-retry-2026-10-17/validator/scratch` for that topic and agent.

Don't:
* Create `{{ PROJECT_ROOT }}/tmp/orders-retry-2026-10-17/worker/` while resolving for `agent-name: validator`; create only the run's own two folders.

### 4. Check the git-ignore status

Run `git -C "{{ PROJECT_ROOT }}" check-ignore -q "<topic>/x"` through `Bash`: a path inside the folder, because a folder that does not exist yet matches a directory pattern such as `tmp/` only through a path below it. Exit 0 gives `gitignore: ignored`; exit 1 gives `not ignored`; any other exit gives `not a git repository`; a workspace outside `{{ PROJECT_ROOT }}` gives `outside the project`. When it is `not ignored` and `gitignore-edit` is `yes`, append the workspace path relative to the project, such as `tmp/`, to `{{ PROJECT_ROOT }}/.gitignore` and report `added tmp/ to .gitignore`; otherwise change nothing and report `not ignored (add tmp/ to .gitignore to keep artefacts out of commits)`.

Do:
* Report `gitignore: not ignored (add tmp/ to .gitignore to keep artefacts out of commits)` when `check-ignore` exits 1 and `gitignore-edit` is `no`.

Don't:
* Edit `.gitignore` because `tmp/` is not ignored while `gitignore-edit` is `no`; report the status only.

### 5. Report

Reply with the Output block, with the cleanup rule written as the template shows and `note` saying in one line where the artefacts go.

Do:
* State the path and continue.

Don't:
* Add a question or a field beyond the Output list.

# Output

The reply returns these fields:

* **status:** always - `completed` when the paths are settled.
* **workspace:** always - The absolute workspace folder, followed by `(default)` when nothing named one, or `none` when there is no folder.
* **workspace-source:** always - `project-rules`, `project-claude-md`, `user-rules`, `user-claude-md` or `default`, with the `path:line` that named it.
* **topic:** always - The absolute topic folder, `<workspace>/<topic-id>`, shared by the topic for topic-level documents.
* **artefacts:** always - The absolute artefacts folder of the run, for files that are kept and reported by path.
* **scratch:** always - The absolute scratch folder of the run, for throwaway files.
* **created:** always - `yes`, or `no` with the reason.
* **cleanup:** always - The cleanup rule for the two folders.
* **gitignore:** always - `ignored`, `not ignored (...)`, `added ...`, `not a git repository` or `outside the project`.
* **note:** always - One line that says where the artefacts go.

Use the first template on every run that settles the paths.

```text
status: completed
workspace: {{ PROJECT_ROOT }}/tmp (default)
workspace-source: default
topic: {{ PROJECT_ROOT }}/tmp/orders-retry-2026-10-17
artefacts: {{ PROJECT_ROOT }}/tmp/orders-retry-2026-10-17/validator/artefacts
scratch: {{ PROJECT_ROOT }}/tmp/orders-retry-2026-10-17/validator/scratch
created: yes
cleanup: delete scratch/ before reporting; keep artefacts/ until the topic is done; never delete a file this run did not create
gitignore: not ignored (add tmp/ to .gitignore to keep artefacts out of commits)
note: artefacts go to {{ PROJECT_ROOT }}/tmp/orders-retry-2026-10-17/validator/artefacts
```

Do:
* `workspace-source: project-claude-md {{ PROJECT_ROOT }}/CLAUDE.md:42` and `workspace: {{ PROJECT_ROOT }}/tmp` when the CLAUDE.md names `tmp/`.
* `created: no (read access)` with `topic`, `artefacts` and `scratch` filled for `access: read`.
* `gitignore: ignored` when `git check-ignore` exits 0.

Don't:
* Return a relative path such as `tmp/orders-retry/validator/artefacts`; return absolute paths.
* Leave out `note` because the paths are already listed; write the one line.
* Add a question such as "Shall I use tmp/?"; state the path and continue.

When the paths cannot be settled, reply with this block only:

```text
status: blocked | needs-input | failed
reason: [ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN]
missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]
```
