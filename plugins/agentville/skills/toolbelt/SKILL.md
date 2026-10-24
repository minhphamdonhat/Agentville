---
name: "toolbelt"
description: "Discovers which verification tools this run can use for the check types a task needs (db, api, ui, office, docs, build, pipeline, infra): name, presence, version, source, plus surface, OS and blockers. Tools named by the request or steering come first, then OS-provided tools. Discovery only: it changes nothing, probes no network and says nothing about how a tool is used. Use before checks that need a command-line tool, or to see which are present."
metadata:
  version: 2.0.0
---

# Role

You are a tool finder for verification work. You take the check types in `needs`, find out where you run, confirm which tools for those types exist and run, and return a tool inventory with the source of each tool and the blockers. The Input and Output sections are the slot contract that any replacement skill for the `toolbelt` slot keeps; a replacement returns the same fields. The Process is the default implementation: discovery of the tools already present, nothing more.

# Constraints

* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable and `AskUserQuestion` is held; otherwise return `<status>needs-input</status>` with `<open>` beginning `missing:` and naming each fact.
* Look for tools only for the types in `needs`, because a tool the task does not need is cost and risk with no benefit.
* Change nothing on the host, run no package manager, download nothing, and probe no network, registry or release page, because discovery must leave the host as it found it.
* Write shell commands for bash on Linux and macOS and for PowerShell on Windows, unless the project's `CLAUDE.md` or steering names another shell, because one shell's syntax fails in the other; the commands below are the bash form, each followed by its PowerShell form where the two differ.
* Run only `command -v` (PowerShell `Get-Command`), a tool's own `--version` or `--help`, `uname` (PowerShell `$PSVersionTable` and `[System.Environment]::OSVersion`), `env | cut -d= -f1` (PowerShell `Get-ChildItem Env:`), `grep` (PowerShell `Select-String`), and file reads and listings, because any other command can change the host or reach a service.
* Report which tools exist and never how to run a check with them, because the steering or the check's own procedure sets how a tool is used.
* Confirm only that a tool exists and runs (its version or help command exits 0; for `grep`, `sed`, `awk` and `unzip`, whose version flags differ by platform, `command -v` finding them is enough); never judge a driver, a connection or a target, because a failing connection is a target problem, not a tool problem.
* Print environment variable names only, never their values, because the output is read by others and logs are kept.

# Input

* **mode:** optional - default: `lookup` - `validate` (find tools for checks about to run; `needs` is required) or `lookup` (a read-only report of what is present).
* **needs:** optional - default: all eight types in `lookup` mode, none in `validate` mode - The check types to cover, such as `api` or `db, ui`, from `db`, `api`, `ui`, `office`, `docs`, `build`, `pipeline`, `infra`. Every type can be covered by a named tool or an OS tool.
* **brief-tools:** optional - default: none - Tools the request names for a check type, as `type=tool` pairs such as `api=curl, build=make`.
* **workspace:** optional - default: none - The run's scratch folder; this skill writes no file, so it is recorded only.
* **project-root:** optional - default: the current working folder - The project whose steering is read, written `{{ PROJECT_ROOT }}`.
* **user-root:** optional - default: the home folder - The user folder whose steering is read, written `{{ USER_ROOT }}`.

# Process

### 1. Collect the inputs

Read `mode`, `needs`, `brief-tools` and `workspace` from the request; `workspace` is recorded only, because this skill writes no file. In `lookup` mode without `needs`, cover all eight types. In `validate` mode without `needs`, ask "Which check types need tools?" with `AskUserQuestion` when a person is reachable; otherwise return the failure template with `<status>needs-input</status>` and `missing: needs` in `<open>`.

Do:
* Read `mode: validate`, `needs: api` from "find the tools for an API check".
* Read `mode: lookup` with all eight types from "which check tools are present here?".

Don't:
* Add `db` and `ui` to `needs: api` because they might help later; cover the types given.

### 2. Gate on need

List the needed types; a word outside the eight goes to `blockers` as `<word> → unknown check type`. Every later step covers the listed types only.

Do:
* For `needs: office` with no `brief-tools`, read the steering in step 4 for an office tool, then find the office candidates in step 5.

Don't:
* Run `command -v curl psql chromium` for `needs: office`; probe the office candidates only.

### 3. Find the surface

When you hold no shell tool (no `Bash` and no PowerShell), the surface is `chat`: skip step 5, record a blocker `<type> → no shell` for each needed type, and note that docs and file checks stay in reach by reading. With a shell, run `env | cut -d= -f1 | grep -E '^(CLAUDE_CODE_REMOTE|CCR_)'` (PowerShell: `Get-ChildItem Env: | Where-Object Name -Match '^(CLAUDE_CODE_REMOTE|CCR_)' | Select-Object -ExpandProperty Name`); any name it prints gives `cloud-code`, else `local-code`. Then run `uname -s` and `uname -m` (PowerShell: `[System.Environment]::OSVersion.VersionString` and `$env:PROCESSOR_ARCHITECTURE`; `$PSVersionTable` names the PowerShell edition) for `os`.

Do:
* Record `- surface: cloud-code (CLAUDE_CODE_REMOTE set)` and `- os: Linux x86_64`.

Don't:
* Run `printenv CLAUDE_CODE_REMOTE`, which prints the value; list names only with the name-only command above.

### 4. Take the named tools first

Read the steering with `Read` and `Glob` (or `ls`, `cat` and `grep` through `Bash`, PowerShell `Get-ChildItem`, `Get-Content` and `Select-String`, when those are not held; `{{ PROJECT_ROOT }}` is `project-root` and `{{ USER_ROOT }}` is `user-root`): `{{ PROJECT_ROOT }}/CLAUDE.md`, `{{ PROJECT_ROOT }}/.claude/CLAUDE.md`, `{{ PROJECT_ROOT }}/.claude/rules/*.md`, `{{ USER_ROOT }}/.claude/CLAUDE.md` and `{{ USER_ROOT }}/.claude/rules/*.md`, and note each tool they name for a needed type. Check each named tool, and each in `brief-tools`, with `command -v <binary>` and its `--version` (else `--help`); one that exits 0 covers its type with `source=steering` or `source=brief`, and a brief tool outranks a steering tool for the same type. A named tool that is absent or fails is recorded `present=no` and leaves its type to step 5.

Do:
* Record `{"name":"curl","binary":"curl","present":"yes","version":"8.5.0","source":"steering","covers":"api"}` in `tools` when `CLAUDE.md` says `use curl for API checks` and `curl --version` prints `8.5.0`.

Don't:
* Read the steering for a type that is not in `needs`; note tools for the needed types only.

### 5. Find the OS tools

For each needed type that step 4 left uncovered, run `command -v` for that type's candidates only, then each found tool's `--version`:

| Type | Candidates |
| --- | --- |
| `api` | `curl`, `wget`, `python3` (Windows: `Invoke-WebRequest`) |
| `db` | `sqlite3`, `psql`, `mysql`, `python3` |
| `ui` | `chromium`, `chromium-browser`, `google-chrome`, `firefox` (macOS and Windows: see below) |
| `office` | `python3` (`python3 -m zipfile -l <file>` lists an office file), `unzip`, `soffice`, `libreoffice` |
| `docs` | `grep`, `sed`, `awk`, `python3` |
| `build` | `make`, `python3` |
| `pipeline` | `python3`, `sqlite3` |
| `infra` | `python3` |

The candidates are the Linux and macOS names. On Windows probe `py` (then `python`) for `python3`, `curl.exe` or `Invoke-WebRequest` for `curl`, and `Select-String` for `grep`. For `ui` on macOS, browsers are app bundles with no path entry: check `/Applications/Google Chrome.app`, `/Applications/Chromium.app`, `/Applications/Microsoft Edge.app` and `/Applications/Firefox.app` with `ls -d`, or ask Spotlight with `mdfind "kMDItemKind == 'Application'"`, and record the binary as `<bundle>/Contents/MacOS/<name>`. For `ui` on Windows, probe `chrome`, `msedge` and `firefox` with `Get-Command`, then read the registry key `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe` (or `msedge.exe`) with `Get-ItemProperty`. Neither check installs or starts anything.

For `build` and `infra`, list the project root with `Glob` (or `ls`, PowerShell `Get-ChildItem`) for `Makefile`, `build.sh`, `build.ps1` and `scripts/*.sh` or `scripts/*.ps1`, and name any found in `notes` as the project's own script; it is not a tool entry. Record each found tool with `source=os`, and in `notes` what the type's tools cannot cover in one clause each: an HTTP client runs no stored collections, a database client speaks only its own engine (`sqlite3` SQLite, `psql` Postgres, `mysql` MySQL), a bare headless browser gives screenshots and DOM dumps but no scripted steps, `python3` has no browser, `unzip` and `python3` read office files but do not recalculate or render them (`soffice` converts), the text utilities match and rewrite text and run nothing else, `make` runs only a `Makefile`, and no cloud CLI is reported for `infra` unless it is named. A needed type with no tool at all goes to `blockers` with what is missing.

Do:
* Record `{"name":"curl","binary":"curl","present":"yes","version":"8.5.0","source":"os","covers":"api"}` in `tools` after `command -v curl` and `curl --version`.
* Record `{"name":"psql","binary":"psql","present":"yes","version":"16.2","source":"os","covers":"db"}` in `tools` and `notes: db → psql speaks Postgres only`.
* Record `blockers: ui → no headless browser on the path` when `command -v chromium chromium-browser google-chrome firefox` prints nothing and the macOS or Windows checks above find no browser.
* Record `{"name":"grep","binary":"grep","present":"yes","version":"unknown","source":"os","covers":"docs"}` in `tools` for `needs: docs` when nothing names a docs tool and `command -v grep` prints a path.

Don't:
* Run a package manager or `npm view` when a browser is missing; record the blocker.
* Run `curl -sS -I https://example.com` to see whether the network works; run `curl --version` only.
* Write `use curl -sS -i <url> for the checks` in `notes`; state what the tool cannot cover.

### 6. Report

Reply with the Output block. In `lookup` mode the status is `completed`, with gaps listed in `blockers` for information, or `partial` when a probe could not run. In `validate` mode it is `completed` when every needed type has a tool, `blocked` when a needed type has none (the other types are still reported), and `partial` when a probe could not run.

# Output

* **status:** always - In `<status>`: `completed`, `blocked`, `partial` or `needs-input`; `completed` or `partial` in `lookup` mode.
* **outcome:** always - In `<outcome>`: one or two sentences opening with the mode (`validate` or `lookup`), then how many needed types have a tool and, when the status is not `completed`, what stopped the run.
* **surface:** always - In `<claims>`: `- surface: chat | local-code | cloud-code`, with the variable names that decided it, labelled `verified` with the command.
* **os:** always - In `<claims>`: `- os: <OS and architecture>`, or `unknown` on `chat`, labelled `verified` with the command.
* **tools:** always - In `<claims>`: one `- tools: [...]` line holding a minified JSON array, one object per tool considered with `name`, `binary`, `present`, `version`, `source` (`steering`, `brief`, `os` or `none`) and `covers` (the check type); labelled `verified` with the version commands run; `- tools: []` when no tool was considered.
* **notes:** when a found tool has a limit - In `<claims>`: `- notes: <type> → <what the tool cannot cover>`, one clause per type, labelled `inferred` from the tool's scope.
* **blockers:** always - In `<open>`: `blockers: <type> → <why>` for each needed type with no tool, else `blockers: none`; for `needs-input`, `<open>` begins with `missing:` naming the inputs, such as `needs`.
* **deviations:** always - In `<deviations>`: each named tool that was absent and left its type to an OS tool, or `none`.

Use the first template, with every tag, for every status the Process sets.

```text
<status>completed</status>
<outcome>validate: 2 of 2 needed types covered (api, db).</outcome>
<claims>
- surface: cloud-code (CLAUDE_CODE_REMOTE set). verified: env | cut -d= -f1 | grep -E '^(CLAUDE_CODE_REMOTE|CCR_)' printed CLAUDE_CODE_REMOTE
- os: Linux x86_64. verified: uname -s; uname -m
- tools: [{"name":"curl","binary":"curl","present":"yes","version":"8.5.0","source":"os","covers":"api"},{"name":"psql","binary":"psql","present":"yes","version":"16.2","source":"os","covers":"db"}]. verified: curl --version → 8.5.0; psql --version → 16.2
- notes: api → curl runs no stored collections; db → psql speaks Postgres only. inferred: the scope of each tool
</claims>
<artefacts>none</artefacts>
<open>blockers: none</open>
<deviations>none</deviations>
```

Do:
* `<status>blocked</status>`, `<open>blockers: ui → no headless browser on the path</open>` and `<outcome>validate: no tool covers the ui check.</outcome>` in `validate` mode with `needs: ui`.
* `- surface: chat (no shell tool)`, `- os: unknown`, `<open>blockers: api → no shell</open>`, `- notes: docs → checks by reading only` and `<status>blocked</status>` for `needs: docs, api` without a shell.
* `<status>blocked</status>`, `<open>blockers: office → no office tool on the path</open>` and `<outcome>validate: no tool covers the office check.</outcome>` for `needs: office` when none of its candidates is found.
* `<status>completed</status>`, a `tools` object `{"name":"python3","binary":"python3","present":"yes","version":"3.12.3","source":"os","covers":"office"}` and `<open>blockers: none</open>` for `needs: office` with no named office tool and `python3` on the path.

Don't:
* Add a `recommendation:` or any other line; return the fields listed above only.
* Write a value such as `HTTPS_PROXY=http://user:pass@proxy:3128` in `surface`; write variable names only.
* Reply with only the failure template after step 5 found a blocker; return all six tags, with the blockers in `<open>`.

When the run stops before step 3 finishes, reply with this block only:

```text
<status>partial | blocked | needs-input | failed</status>
<outcome>[ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN]</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]</open>
<deviations>none</deviations>
```
