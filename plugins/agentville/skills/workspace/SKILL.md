---
name: "workspace"
description: "Gives one run its workspace folders: from a topic id and an agent name it returns the absolute artefacts and scratch paths under '<workspace>/<topic-id>/<agent-name>/', the cleanup rule and whether the workspace is git-ignored, and creates both folders. The default reads a 'workspace-folder: <path>' line in project rules, the project CLAUDE.md, user rules or the user CLAUDE.md, and with none found uses '{{ PROJECT_ROOT }}/tmp/' without asking. Use before writing any artefact, evidence or scratch file, when asked where a run's artefacts go, or to locate another run's artefacts folder read-only."
---

# Role

You are a workspace planner. You take a `topic-id` and an `agent-name`, settle the workspace folder for this project, and return the absolute `artefacts` and `scratch` paths for that run, the cleanup rule and the git-ignore status. The Input and Output sections are the slot contract that any replacement skill for the `workspace` slot keeps; a replacement may also return `status: needs-input` with `missing: workspace`. The Process is the default implementation, which never asks for a folder.

# Constraints

* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable only for a missing `topic-id` or `agent-name`; otherwise return `status: needs-input` with `missing:` naming each, because an unattended run cannot answer.
* Never ask which workspace folder to use: take the folder the steering names, else `{{ PROJECT_ROOT }}/tmp/`, and state the path in `workspace` and `note`, because the default is meant to work with no setup.
* Create only the two run folders, and write, edit or delete nothing else, except one `.gitignore` line when `gitignore-edit` is `yes`, because the workspace must not change the project unasked.
* Accept a `topic-id` and an `agent-name` only in kebab-case (lower-case letters, digits and hyphens), because a `/` or `..` in either would put files outside the workspace.
* Write every path in examples with a placeholder (`{{ PROJECT_ROOT }}`, `{{ USER_ROOT }}`), and return absolute paths in the output, because examples must hold on every machine and a run needs real paths.

# Input

* **topic-id:** required - default: none - The topic folder for the run, such as `orders-retry-20261017`.
* **agent-name:** required - default: none - The agent the run folders belong to, such as `validator`.
* **access:** optional - default: `write` - `write` creates the two folders; `read` only returns the paths, such as when locating another agent's artefacts.
* **gitignore-edit:** optional - default: `no` - `yes` when the request or the steering allows edits outside the workspace, so the workspace may be added to `.gitignore`.
* **project-root:** optional - default: the current working folder - The project, written `{{ PROJECT_ROOT }}`.
* **user-root:** optional - default: the home folder - The user folder, written `{{ USER_ROOT }}`.

# Process

### 1. Collect the inputs

Read `topic-id`, `agent-name`, `access` and `gitignore-edit` from the request. When `topic-id` or `agent-name` is missing or not kebab-case, ask for it with `AskUserQuestion` when a person is reachable; otherwise return the failure block with `status: needs-input` and `missing:` naming it.

Do:
* Read `topic-id: orders-retry-20261017` and `agent-name: validator` from "workspace for the validator on topic orders-retry-20261017".

Don't:
* Make up `topic-id: misc` when none is given; return `missing: topic-id`, as the Constraints say.

### 2. Find the named workspace folder

Look for a workspace folder in this order and stop at the first that names one, reading with `Read`, `Glob` and `Grep` (or `ls`, `cat` and `grep` through `Bash` when those are not held; `{{ PROJECT_ROOT }}` is `project-root` and `{{ USER_ROOT }}` is `user-root`): `{{ PROJECT_ROOT }}/.claude/rules/*.md` (`project-rules`), `{{ PROJECT_ROOT }}/CLAUDE.md` and `{{ PROJECT_ROOT }}/.claude/CLAUDE.md` with their one-level `@<path>` imports (`project-claude-md`), `{{ USER_ROOT }}/.claude/rules/*.md` (`user-rules`), then `{{ USER_ROOT }}/.claude/CLAUDE.md` (`user-claude-md`). A file names a folder only with a line `workspace-folder: <path>` (optionally after a list marker and in backticks); prose that mentions a workspace is not read. Read a `{{ PROJECT_ROOT }}` or `{{ USER_ROOT }}` placeholder in the named path as that root, resolve a relative path against `{{ PROJECT_ROOT }}` and a leading `~` against `{{ USER_ROOT }}`, and drop a trailing `/`. When nothing names a folder, use `{{ PROJECT_ROOT }}/tmp` with source `default`.

Do:
* Use `{{ PROJECT_ROOT }}/tmp` with source `project-claude-md` when `{{ PROJECT_ROOT }}/CLAUDE.md` has the line `workspace-folder: tmp/`.
* Use `{{ PROJECT_ROOT }}/tmp` with source `default` when no rule or CLAUDE.md names a folder, and go on.

Don't:
* Return `needs-input` with `missing: workspace` because nothing names a folder; use the default, as the second Do item does.
* Take a folder from a sentence such as "The workspace is `tmp/`" or "Artefacts of the build go to `dist/`"; only a `workspace-folder:` line counts, so use the default for both.

### 3. Create the run folders

Set `artefacts` to `<workspace>/<topic-id>/<agent-name>/artefacts` and `scratch` to `<workspace>/<topic-id>/<agent-name>/scratch`. With `access: write`, create both with `mkdir -p "<artefacts>" "<scratch>"` through `Bash`; without a shell tool, write no placeholder file and report `created: no (no shell; the folders appear with the first file written)`. With `access: read`, create nothing and report `created: no (read access)`.

Do:
* Run `mkdir -p {{ PROJECT_ROOT }}/tmp/orders-retry-20261017/validator/artefacts {{ PROJECT_ROOT }}/tmp/orders-retry-20261017/validator/scratch` for that topic and agent.

Don't:
* Create `{{ PROJECT_ROOT }}/tmp/orders-retry-20261017/worker/` while resolving for `agent-name: validator`; create only the run's own two folders.

### 4. Check the git-ignore status

Run `git -C "{{ PROJECT_ROOT }}" check-ignore -q "<workspace>"` through `Bash`. Exit 0 gives `gitignore: ignored`; exit 1 gives `not ignored`; any other exit gives `not a git repository`; a workspace outside `{{ PROJECT_ROOT }}` gives `outside the project`. When it is `not ignored` and `gitignore-edit` is `yes`, append the workspace path relative to the project, such as `tmp/`, to `{{ PROJECT_ROOT }}/.gitignore` and report `added tmp/ to .gitignore`; otherwise change nothing and report `not ignored (add tmp/ to .gitignore to keep artefacts out of commits)`.

Do:
* Report `gitignore: not ignored (add tmp/ to .gitignore to keep artefacts out of commits)` when `check-ignore` exits 1 and `gitignore-edit` is `no`.

Don't:
* Edit `.gitignore` because `tmp/` is not ignored while `gitignore-edit` is `no`; report the status only, as the Do item does.

### 5. Report

Reply with the Output block, with the cleanup rule written as the template shows and `note` saying in one line where the artefacts go.

# Output

The reply returns these fields:

* **status:** always - `completed` when the paths are settled.
* **workspace:** always - The absolute workspace folder, followed by `(default)` when nothing named one.
* **workspace-source:** always - `project-rules`, `project-claude-md`, `user-rules`, `user-claude-md` or `default`, with the `path:line` that named it.
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
artefacts: {{ PROJECT_ROOT }}/tmp/orders-retry-20261017/validator/artefacts
scratch: {{ PROJECT_ROOT }}/tmp/orders-retry-20261017/validator/scratch
created: yes
cleanup: delete scratch/ before reporting; keep artefacts/ until the topic is done; never delete a file this run did not create
gitignore: not ignored (add tmp/ to .gitignore to keep artefacts out of commits)
note: artefacts go to {{ PROJECT_ROOT }}/tmp/orders-retry-20261017/validator/artefacts
```

Do:
* `workspace-source: project-claude-md {{ PROJECT_ROOT }}/CLAUDE.md:42` and `workspace: {{ PROJECT_ROOT }}/tmp` when the CLAUDE.md names `tmp/`.
* `created: no (read access)` with both paths filled for `access: read`.
* `gitignore: ignored` when `git check-ignore` exits 0.

Don't:
* Return a relative path such as `tmp/orders-retry/validator/artefacts`; return absolute paths, as the template does.
* Leave out `note` because the paths are already listed; write the one line, as the template does.
* Add a question such as "Shall I use tmp/?"; state the path and continue, as the template does.

When the paths cannot be settled, reply with this block only:

```text
status: blocked | needs-input | failed
reason: [ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN]
missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]
```
