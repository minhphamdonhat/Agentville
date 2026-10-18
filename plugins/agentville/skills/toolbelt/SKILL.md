---
name: "toolbelt"
description: "Finds which verification tools this run can use, for the check types a task needs and no others (db, api, ui, office, docs, build, pipeline, infra), and reports each tool's name, binary, presence, version, source and the check type it covers, with the surface, the OS and any blockers. For every type, the tools the steering or the request names come first; where nothing names a tool, it reports the OS-provided tools that are present for that type (a database client, an HTTP client, a headless browser, python3, unzip, grep, make). It only discovers: it changes nothing on the host, probes no network or registry, and says nothing about how a tool is used. Use before proof checks that need a command-line tool, when asked which check tools are present here, or when a named check tool may be missing."
---

# Role

You are a tool finder for verification work. You take the check types in `needs`, find out where you run, confirm which tools for those types exist and run, and return a tool inventory with the source of each tool and the blockers. The Input and Output sections are the slot contract that any replacement skill for the `toolbelt` slot keeps; a replacement returns the same fields. The Process is the default implementation: discovery of the tools already present, nothing more.

# Constraints

* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable; otherwise return `status: needs-input` with `missing:` naming each fact, because an unattended run cannot answer.
* Look for tools only for the types in `needs`, because a tool the task does not need is cost and risk with no benefit.
* Change nothing on the host, run no package manager, download nothing, and probe no network, registry or release page, because discovery must leave the host as it found it.
* Run only `command -v` (PowerShell `Get-Command`), a tool's own `--version` or `--help`, `uname`, `env | cut -d= -f1`, and file reads and listings, because any other command can change the host or reach a service.
* Report which tools exist and never how to run a check with them, because the steering or the check's own procedure sets how a tool is used.
* Confirm only that a tool exists and runs (its version or help command exits 0; for `grep`, `sed`, `awk` and `unzip`, whose version flags differ by platform, `command -v` finding them is enough); never judge a driver, a connection or a target, because a failing connection is a target problem, not a tool problem.
* Print environment variable names only, never their values, because the output is read by others and logs are kept.

# Input

* **mode:** optional - default: `lookup` - `validate` (find tools for checks about to run; `needs` is required) or `lookup` (a read-only report of what is present).
* **needs:** optional - default: `db, api, ui` in `lookup` mode, none in `validate` mode - The check types to cover, such as `api` or `db, ui`, from `db`, `api`, `ui`, `office`, `docs`, `build`, `pipeline` and `infra`. Every type can be covered by a named tool or by an OS tool.
* **brief-tools:** optional - default: none - Tools the request names for a check type, as `type=tool` pairs such as `api=curl, build=make`.
* **workspace:** optional - default: none - The run's scratch folder; this skill writes no file, so it is recorded only.
* **project-root:** optional - default: the current working folder - The project whose steering is read, written `{{ PROJECT_ROOT }}`.
* **user-root:** optional - default: the home folder - The user folder whose steering is read, written `{{ USER_ROOT }}`.

# Process

### 1. Collect the inputs

Read `mode`, `needs`, `brief-tools` and `workspace` from the request; `workspace` is recorded only, because this skill writes no file. In `validate` mode without `needs`, ask "Which check types need tools?" with `AskUserQuestion` when a person is reachable; otherwise return the failure block with `status: needs-input` and `missing: needs`.

Do:
* Read `mode: validate`, `needs: api` from "find the tools for an API check".

Don't:
* Add `db` and `ui` to `needs: api` because they might help later; cover the types given.

### 2. Gate on need

List the needed types, each one of `db`, `api`, `ui`, `office`, `docs`, `build`, `pipeline` or `infra`; a word outside the eight goes to `blockers` as `<word> → unknown check type`. Every later step covers the listed types only.

Do:
* For `needs: office` with no `brief-tools`, read the steering in step 4 for an office tool, then find the office candidates in step 5.

Don't:
* Run `command -v curl psql chromium` for `needs: office`; probe the office candidates only.

### 3. Find the surface

When you hold no shell tool (no `Bash` and no PowerShell), the surface is `chat`: skip step 5, record a blocker `<type> → no shell` for each needed type, and note that docs and file checks stay in reach by reading. With a shell, run `env | cut -d= -f1 | grep -E '^(CLAUDE_CODE_REMOTE|CCR_)'`; any name it prints gives `cloud-code`, else `local-code`. Then run `uname -s` and `uname -m` (Windows: `[System.Environment]::OSVersion.VersionString` and `$env:PROCESSOR_ARCHITECTURE`) for `os`.

Do:
* Record `surface: cloud-code (CLAUDE_CODE_REMOTE set)` and `os: Linux x86_64`.

Don't:
* Run `printenv CLAUDE_CODE_REMOTE`, which prints the value; list names only with the `cut -d=` command above.

### 4. Take the named tools first

Read the steering with `Read` and `Glob` (or `ls`, `cat` and `grep` through `Bash` when those are not held; `{{ PROJECT_ROOT }}` is `project-root` and `{{ USER_ROOT }}` is `user-root`): `{{ PROJECT_ROOT }}/CLAUDE.md`, `{{ PROJECT_ROOT }}/.claude/CLAUDE.md`, `{{ PROJECT_ROOT }}/.claude/rules/*.md`, `{{ USER_ROOT }}/.claude/CLAUDE.md` and `{{ USER_ROOT }}/.claude/rules/*.md`, and note each tool they name for a needed type. Check each named tool, and each in `brief-tools`, with `command -v <binary>` and its `--version` (else `--help`); one that exits 0 covers its type with `source=steering` or `source=brief`, and a brief tool outranks a steering tool for the same type. A named tool that is absent or fails is recorded `present=no` and leaves its type to step 5.

Do:
* Record `- name=curl binary=curl present=yes version=8.5.0 source=steering covers=api` when `CLAUDE.md` says `use curl for API checks` and `curl --version` prints `8.5.0`.

Don't:
* Read the steering for a type that is not in `needs`; note tools for the needed types only.

### 5. Find the OS tools

For each needed type that step 4 left uncovered, run `command -v` for that type's candidates only, then each found tool's `--version`:

| Type | Candidates |
| --- | --- |
| `api` | `curl`, `wget`, `python3` (Windows: `Invoke-WebRequest`) |
| `db` | `sqlite3`, `psql`, `mysql`, `python3` |
| `ui` | `chromium`, `chromium-browser`, `firefox` |
| `office` | `python3`, `unzip`, `soffice`, `libreoffice` |
| `docs` | `grep`, `sed`, `awk`, `python3` |
| `build` | `make`, `python3` |
| `pipeline` | `python3`, `sqlite3` |
| `infra` | `python3` |

Add a headless browser binary or any other tool the steering names for the type. For `build` and `infra`, list the project root with `Glob` (or `ls`) for `Makefile`, `build.sh` and `scripts/*.sh`, and name any found in `notes` as the project's own script; it is not a tool entry. Record each found tool with `source=os`, and in `notes` what the type's tools cannot cover in one clause each: an HTTP client runs no stored collections, a database client speaks only its own engine (`sqlite3` SQLite, `psql` Postgres, `mysql` MySQL), a bare headless browser gives screenshots and DOM dumps but no scripted steps, `python3` has no browser, `unzip` and `python3` read office files but do not recalculate or render them (`soffice` converts), the text utilities match and rewrite text and run nothing else, `make` runs only a `Makefile`, and no cloud CLI is reported for `infra` unless it is named. A needed type with no tool at all goes to `blockers` with what is missing.

Do:
* Record `- name=curl binary=curl present=yes version=8.5.0 source=os covers=api` after `command -v curl` and `curl --version`.
* Record `- name=psql binary=psql present=yes version=16.2 source=os covers=db` and `notes: db → psql speaks Postgres only`.
* Record `blockers: ui → no headless browser on the path` when `command -v chromium chromium-browser firefox` prints nothing.
* Record `- name=grep binary=grep present=yes version=unknown source=os covers=docs` for `needs: docs` when nothing names a docs tool and `command -v grep` prints a path.

Don't:
* Run a package manager or `npm view` when a browser is missing; record the blocker, as the third Do item does.
* Run `curl -sS -I https://example.com` to see whether the network works; run `curl --version` only, as the first Do item does.
* Write `use curl -sS -i <url> for the checks` in `notes`; state what the tool cannot cover, as the second Do item does.

### 6. Report

Reply with the Output block. In `lookup` mode the status is `completed`, with gaps listed in `blockers` for information, or `partial` when a probe could not run. In `validate` mode it is `completed` when every needed type has a tool, `blocked` when a needed type has none (the other types are still reported), and `partial` when a probe could not run.

# Output

The reply returns these fields:

* **status:** always - `completed`, `blocked`, `partial` or `needs-input`; `completed` or `partial` in `lookup` mode.
* **mode:** always - `validate` or `lookup`.
* **surface:** always - `chat`, `local-code` or `cloud-code`, with the variable names that decided it.
* **os:** always - The OS and architecture, or `unknown` on `chat`.
* **tools:** always - One line per tool considered: name, binary, present, version, source (`steering`, `brief`, `os` or `none`) and the check type it covers.
* **notes:** always - What each found tool cannot cover, one clause per type, or `none`.
* **blockers:** always - Each needed type with no tool and why, or `none`.
* **reason:** when status is not `completed` - One sentence naming what stopped the run.
* **missing:** when status is `needs-input` - The inputs or decisions needed, such as `needs`.

Use the first template, with every field, for every status the Process sets.

```text
status: completed
mode: validate
surface: cloud-code (CLAUDE_CODE_REMOTE set)
os: Linux x86_64
tools:
- name=curl binary=curl present=yes version=8.5.0 source=os covers=api
- name=psql binary=psql present=yes version=16.2 source=os covers=db
notes: api → curl runs no stored collections; db → psql speaks Postgres only
blockers: none
```

Do:
* `status: blocked`, `blockers: ui → no headless browser on the path`, `reason: no tool covers the ui check` in `validate` mode with `needs: ui`.
* `surface: chat (no shell tool)`, `os: unknown`, `blockers: api → no shell`, `notes: docs checks by reading only`, `status: blocked` for `needs: docs, api` without a shell.
* `status: completed`, `- name=unzip binary=unzip present=yes version=unknown source=os covers=office`, `blockers: none` for `needs: office` with no named office tool and `unzip` on the path.
* `status: blocked`, `blockers: office → no office tool on the path`, `reason: no tool covers the office check` for `needs: office` when none of its candidates is found.

Don't:
* Add a `recommendation:` or any other line; return the fields listed above only, as the template does.
* Write a value such as `HTTPS_PROXY=http://user:pass@proxy:3128` in `surface`; write variable names only.
* Reply with only `status:` and `reason:` after step 5 found a blocker; return the full field block, as the first Do item does.

When the run stops before step 3 finishes, reply with this block only:

```text
status: partial | blocked | needs-input | failed
reason: [ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN]
missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]
```
