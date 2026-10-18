---
name: "toolbelt"
description: "Finds the verification tools a run can use before any database, HTTP or API, UI or docs check: detects the surface (chat, local Code, cloud Code), the OS, the package manager, Python and Node.js, takes the tools the project's or user's CLAUDE.md and rules name first, then looks for dbvr, Bruno CLI (bru) and agent-browser, resolves the dbvr release for the OS and architecture with its SHA-256, asks for one install approval with exact OS-specific commands when they are missing, and otherwise falls back to OS defaults such as curl, sqlite3 or psql and python3. Use before running validation checks that need a tool, when asked which check tools are installed here, when a tool such as bru or agent-browser is missing, or when choosing a fallback on a host with a restricted network."
---

# Role

You are a tool scout for verification work. You take a `mode`, the check types in `needs` and any install approval, find out where you run and which tools are present, install only with approval, and return a tool inventory with the source of each tool, the installs still needed, the fallbacks in use and the blockers.

# Constraints

* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable; otherwise return `status: needs-input` with `missing:` naming each fact, because an unattended run cannot answer.
* In `lookup` mode install nothing, change nothing and only report what is present, because lookup is read-only by contract.
* Install only in `validate` mode and only when `install-approval` carries the user's yes, because an install changes the host for every later run.
* Install dbvr, Bruno CLI and agent-browser together, all three that are missing, once approved, because the user chose one install round over one per check.
* Propose an npm install command only for a package you confirmed exists with `npm view <name> version` or the package manager's search, and report any other as `unconfirmed`, because an invented package name can install the wrong code.
* Resolve the dbvr release at install time from the latest-release lookup and never write a version, tag, asset name or checksum from memory, because a pinned value goes stale and a wrong checksum defeats the check.
* Install dbvr only after the SHA-256 of the download equals the one the release lists; when the checksum is missing, unreadable or different, install nothing and fall back, because an unverified binary must not run on the host.
* Print environment variable names only, never their values, and never print a token, password or proxy credential, because the output is read by others and logs are kept.
* Run only read-only probes (`command -v`, `--version`, `id -u`, `uname`, `ldd --version`, `sw_vers`, `java -version`, `npm view`, `npm ping`, `cat /etc/os-release`, and one GET of the dbvr release metadata) outside step 7, because a probe must leave the host as it found it.

# Input

* **mode:** optional - default: `lookup` - `validate` (find tools for checks that are about to run; may stop for install approval and may install with it) or `lookup` (read-only report of the tools already present; never installs).
* **needs:** optional - default: `db, api, ui, docs` - The check types to cover, any of `db`, `api`, `ui` and `docs`, such as `api, ui`. Pass the types explicitly; a work type with no ladder tool (such as build, pipeline or infra) goes in `brief-tools` or in the steering instead.
* **install-approval:** optional - default: none - The user's explicit yes to install the missing tools, such as `user approved: install dbvr, bruno and agent-browser`. A yes relayed from the user, or that a person gives to `AskUserQuestion` where it is held, counts. It may add `dbvr from <url> sha256 <hex>` to name a dbvr source when the release could not be resolved, or `dbvr: skip` to use the fallback. Without it, nothing is installed.
* **brief-tools:** optional - default: none - Tools the brief names for a check type, as `type=tool` pairs such as `build=make, infra=terraform`; they cover check types the ladder has no tool for.
* **project-root:** optional - default: the current working folder - The project whose steering is read, written `{{ PROJECT_ROOT }}`.

### Tool map

| Check type | Ladder tool | Binary | Known package | OS-default fallback |
| --- | --- | --- | --- | --- |
| `db` | dbvr (DBeaver Corp CLI, `dbvr-ce` build) | `dbvr` | GitHub release `dbeaver/dbvr`, asset resolved at install time (step 5); `brew install --cask dbvr` on macOS; not an npm package | `sqlite3`, `psql`, `mysql`, python3 `sqlite3` module |
| `api` | Bruno CLI | `bru` | `npm install -g @usebruno/cli` | `curl -sS -i`, PowerShell `Invoke-WebRequest`, python3 `urllib.request` |
| `ui` | agent-browser | `agent-browser` | check with `npm view agent-browser version`; when found, `npm install -g agent-browser` | `chromium --headless`, `google-chrome --headless`, `firefox --headless` |
| `docs` | none needed | - | - | `curl -sS -I` for links, python3 stdlib, reading the files |

### dbvr use

dbvr has no assert feature and documents no exit codes, so a check asserts by comparing output with a value written before the run. Run `dbvr sql -ds <datasource-id> -format json "<query>"` (also `--input-file <file>` and `-output-file <file>`), compare the JSON with the expected value, and run one control, a deliberately bad query, to learn whether a SQL error gives a non-zero exit code. Run `dbvr --help` and `dbvr sql --help` for the options on this build, and `dbvr driver list` and `dbvr datasource create --help` to set up a datasource, because those syntaxes are not confirmed here.

# Process

### 1. Detect the surface

Decide where you run. When you hold no shell tool (no `Bash` and no PowerShell), the surface is `chat`: only docs checks by reading are in reach, so record a blocker for each of `db`, `api` and `ui` in `needs`, skip steps 2 to 7 and go to step 8. With a shell, list the variable names that mark a cloud session with `env | cut -d= -f1 | grep -E '^(CLAUDE_CODE_REMOTE|CCR_|HTTPS?_PROXY$|https?_proxy$)'` (PowerShell: `Get-ChildItem Env: | Where-Object Name -match '^(CLAUDE_CODE_REMOTE|CCR_|HTTPS?_PROXY$)' | Select-Object Name`). Any `CLAUDE_CODE_REMOTE` or `CCR_` name gives `cloud-code`, and a proxy name there means the network is likely restricted; otherwise the surface is `local-code`.

Do:
* Record `surface: cloud-code (CLAUDE_CODE_REMOTE, HTTPS_PROXY set; network likely restricted)` when those names print.
* Record `surface: chat` and `blockers: db, api, ui checks need a shell; only docs checks by reading are in reach` when no shell tool exists.

Don't:
* Run `env` or `printenv HTTPS_PROXY` and copy the values; print names only with the `cut -d=` command above.
* Guess `local-code` without running the probe; run it and record what it printed.

### 2. Detect the OS, package manager, Python and Node.js

Run `uname -s` and `uname -m`, and map the machine to an arch token: `x86_64` or `amd64` gives `x86_64`, `aarch64` or `arm64` gives `aarch64`, and any other value stays as printed and is unsupported for dbvr. On Linux, run `cat /etc/os-release` and keep `ID` and `VERSION_ID`, run `ldd --version 2>&1 | head -1` for the libc (`musl` when `ID=alpine` or the line names musl, otherwise `glibc`), then run `command -v apt-get dnf yum pacman zypper apk brew npm` and `command -v dpkg rpm sudo` and keep the first OS package manager it finds. On macOS (`Darwin`), run `sw_vers -productVersion` and `command -v brew npm`. On Windows, use PowerShell: `[System.Environment]::OSVersion.VersionString`, `$env:PROCESSOR_ARCHITECTURE` (`AMD64` gives `x86_64`, `ARM64` gives `aarch64`) and `Get-Command winget,choco,scoop,npm -ErrorAction SilentlyContinue | Select-Object Name`. Then record the runtimes with `python3 --version` (Windows: `py --version`), `node --version` and `npm --version`, writing `absent` for any that fails.

Do:
* Record `os: linux ubuntu 24.04 x86_64 glibc`, `package-manager: apt-get (dpkg, sudo), npm 10.9.4`, `python: 3.12.3`, `node: v22.22.0`.

Don't:
* Assume `apt-get` because the host is Linux; record only what `command -v` printed, as the Do item does.

### 3. Take the steering's tools first

Read the steering of `project-root` with `Read` and `Glob` (or `ls` and `find` through `Bash` when `Glob` is not held): `{{ PROJECT_ROOT }}/CLAUDE.md`, `{{ PROJECT_ROOT }}/.claude/CLAUDE.md`, `{{ PROJECT_ROOT }}/.claude/rules/*.md`, `{{ USER_ROOT }}/.claude/CLAUDE.md` and `{{ USER_ROOT }}/.claude/rules/*.md`. Note every tool or skill they name for a check type in `needs`, with any version, profile or permission rule. Check each named tool with `command -v <tool>` and its version command. A present one covers its check type with `source: steering`, and the ladder tool for that type is not needed. Check each tool in `brief-tools` the same way; a present one covers its check type with `source: brief`, and it outranks a steering tool for the same type because the brief is the more specific instruction.

Do:
* Record `- name=httpie binary=http present=yes version=3.2.2 source=steering covers=api` when `CLAUDE.md` says `use httpie for API checks` and `command -v http` finds it.

Don't:
* Skip a steering tool because `bru` is also installed; the steering wins, as the Do item shows.

### 4. Check the ladder tools

For every check type in `needs` that step 3 left uncovered, and always for all three in `lookup` mode, run `command -v dbvr bru agent-browser` (Windows: `Get-Command dbvr,bru,agent-browser -ErrorAction SilentlyContinue`). For each found, run `bru --version` or `agent-browser --version` and record it with `source: preinstalled`; for dbvr, whose `--version` is undocumented, run `dbvr --help` (it must exit 0) and then `dbvr --version`, and record `version=unknown` when `--version` prints nothing useful. A present tool covers its check type.

Do:
* Record `- name=bruno binary=bru present=yes version=4.2.1 source=preinstalled covers=api`.
* Record `- name=dbvr binary=dbvr present=no version=none source=none covers=db` when `command -v dbvr` prints nothing.
* Record `- name=dbvr binary=dbvr present=yes version=unknown source=preinstalled covers=db` when `dbvr --help` exits 0 and `dbvr --version` fails.

Don't:
* Look for `bruno` on the path; the Bruno CLI binary is `bru`, as the Do item shows.

### 5. Check install feasibility

Skip this step in `lookup` mode and when every check type in `needs` is covered. Otherwise run two sets of read-only probes and judge each set on its own. On `cloud-code`, expect a block at any probe and treat a set as infeasible unless every probe in it passes.

**npm set (Bruno CLI and agent-browser):** a package manager or `npm` from step 2; write rights with `test -w "$(npm config get prefix)" && echo writable` (Windows: run `npm config get prefix` and check the folder is not under `Program Files`, or note that the shell needs admin rights); registry reach with `timeout 20 npm ping`, or `curl -sS -I --max-time 10 https://registry.npmjs.org/` when `npm` is absent, both of which use any configured proxy; and package existence with `npm view @usebruno/cli version` and `npm view agent-browser version`. The set is feasible when a package manager exists, the prefix is writable and the registry answers.

**dbvr set:** dbvr is a release asset, not an npm package. Work through these four checks in order and stop at the first that fails.

1. **Platform.** dbvr supports Linux, macOS and Windows on `x86_64` and `aarch64`. It is unsupported on Linux with `musl` (Alpine), on any other arch, on macOS below 11 and on Windows below 10 (8.1, Server 2012 and earlier). Record `dbvr: unsupported (<reason>)`; no source can fix that, so the fallback in step 8 applies and step 6 does not ask for `dbvr-source`.
2. **Package type.** Use the os token `linux`, `macos` or `windows` and the arch token from step 2. On Linux pick `.deb` when `dpkg` and `apt-get` exist, `.rpm` when `dnf`, `yum` or `rpm` exists, in both cases only with root or `sudo`; otherwise `.tar.gz` into a user folder. On macOS pick the `brew install --cask dbvr` cask when `brew` exists, otherwise `.dmg`. On Windows pick `.zip` into a user folder, and `.exe` only when the release has no `.zip` for the arch.
3. **Release.** Read the latest release once, through the configured proxy and without a token: `curl -sS --max-time 15 https://api.github.com/repos/dbeaver/dbvr/releases/latest` (Windows: `Invoke-RestMethod`). Parse `tag_name`, and for the asset named `dbvr-ce-<tag>-<os>-<arch>.<ext>` its `browser_download_url` and its `digest` (`sha256:<hex>`), with `python3 -I -c`. When `digest` is absent, read the SHA-256 shown beside the asset on `https://github.com/dbeaver/dbvr/releases/expanded_assets/<tag>`. Use the tag exactly as returned; it has had no `v` prefix. For the cask, run `brew info --cask dbvr` and record its version beside the release tag, because the cask can lag; brew checks its own pinned checksum, which counts as the checksum. When the lookup is blocked or times out, the asset is absent or no checksum can be read, record `dbvr: unresolved (<reason>)`.
4. **Placement.** `.deb` and `.rpm` need root (`id -u` prints `0`) or a `sudo` that `command -v sudo` finds; run no `sudo` command before the approval, not even `sudo -n true`. The user-folder types need a writable `{{ USER_ROOT }}/.local` (Windows: `$env:LOCALAPPDATA`).

Do:
* Record `install-feasible: yes (npm 10.9.4, prefix writable, npm ping PONG 134ms)` and `dbvr-plan: linux debian 12 x86_64 glibc → dbvr-ce-<tag>-linux-x86_64.deb, sha256 read from the release digest`.
* Record `dbvr: unsupported (musl libc on alpine)` on Alpine and `dbvr: unresolved (release lookup → 403 from proxy)` when GitHub is blocked.
* Record `install-feasible: no (cloud-code; npm ping → 403 from proxy)` for the npm set and go to step 8 for its tools.

Don't:
* Write a tag, asset name or checksum from memory or from an earlier run; read them in this run, as the first Do item does.
* Run `sudo -n true` to test for sudo rights in this step; `command -v sudo` and `id -u` answer it without elevating.
* Propose `npm install -g dbvr`; it is not an npm package, so use the release asset or report it `unresolved`.
* Run `npm install` here to test the network, download the asset, or start `npm ping` in the background; run `timeout 20 npm ping`, the `curl -I` probe or the one release GET in the foreground, because this step changes nothing and its answer is needed now.

### 6. Ask for install approval

Skip this step in `lookup` mode, when every check type in `needs` is covered, when step 5 found every set infeasible, or when nothing installable is missing. A tool is installable when step 5 gave it a command. When any installable one of dbvr, Bruno CLI and agent-browser is missing and `install-approval` carries no yes, install nothing and stop: when a person is reachable, ask "Install the missing verification tools with these commands?" with `AskUserQuestion`; otherwise return the needs-input block of the Output with `missing: install-approval`. List every missing installable one of the three, not only the one `needs` asks for, with its exact commands for the OS. Bruno CLI is `npm install -g @usebruno/cli` (binary `bru`), and agent-browser is `npm install -g agent-browser` only when `npm view agent-browser version` confirmed it. dbvr is the download, checksum and install commands for the package type of step 5, filled from the release lookup:

* `.deb`: `curl -sSL -o <asset> <url>`, `echo "<sha256>  <asset>" | sha256sum -c -`, `sudo apt-get install -y ./<asset>`.
* `.rpm`: the same download and check, then `sudo dnf install -y ./<asset>` (or `sudo rpm -i <asset>` with only `rpm`).
* `.tar.gz`: the same download and check, then `mkdir -p {{ USER_ROOT }}/.local/opt/dbvr {{ USER_ROOT }}/.local/bin`, `tar -xzf <asset> -C {{ USER_ROOT }}/.local/opt/dbvr` and a symlink of the `dbvr` executable that `find {{ USER_ROOT }}/.local/opt/dbvr -name dbvr -type f` prints into `{{ USER_ROOT }}/.local/bin`, with `{{ USER_ROOT }}/.local/bin` named as the folder to add to `PATH`.
* macOS: `brew install --cask dbvr`; without `brew`, the `.dmg` with `shasum -a 256 -c`, `hdiutil attach`, a copy of `dbvr.app` into `{{ USER_ROOT }}/Applications` and `hdiutil detach`, and mark the path of its CLI as unconfirmed until `find` locates it.
* Windows (PowerShell): `Invoke-WebRequest -Uri <url> -OutFile <asset>`, `(Get-FileHash <asset> -Algorithm SHA256).Hash` compared with `<sha256>`, `Expand-Archive <asset> -DestinationPath $env:LOCALAPPDATA\dbvr`, and the folder holding `dbvr.exe` added to the user `PATH`.

When dbvr is `unresolved`, list it as `dbvr unresolved (<reason>)` and add `dbvr-source` to `missing:`, written plainly, whether or not `needs` holds `db`, because the reader of this block passes `missing:` on word for word. The user answers `dbvr-source` with a URL and its SHA-256, or with `dbvr: skip`, and the run falls back for `db` when the answer is `skip`. When dbvr is `unsupported`, list it as `dbvr unsupported (<reason>)` with no `dbvr-source`. When Node.js is absent, put its install first: `sudo apt-get install -y nodejs npm`, `sudo dnf install -y nodejs npm`, `brew install node` or `winget install OpenJS.NodeJS.LTS`. With a yes in `install-approval`, go to step 7.

Do:
* Return `status: needs-input`, `missing: install-approval` and `install-needed: npm install -g @usebruno/cli; npm install -g agent-browser; curl -sSL -o dbvr-ce-<tag>-linux-x86_64.deb <url>; echo "<sha256>  dbvr-ce-<tag>-linux-x86_64.deb" | sha256sum -c -; sudo apt-get install -y ./dbvr-ce-<tag>-linux-x86_64.deb` for `needs: api` on Debian x86_64 with none of the three, with `<tag>`, `<url>` and `<sha256>` filled from the lookup.
* Add `dbvr unresolved (release lookup → 403 from proxy)` to `install-needed` and a plain `dbvr-source` to `missing:` when GitHub is blocked but npm answers, even for `needs: api, ui`.
* Put `sudo apt-get install -y nodejs npm` first in `install-needed` when `node --version` failed on Ubuntu.

Don't:
* Ask to install only `bru` because `needs` is `api`; list all three missing installable tools, because they are installed together.
* Ask for approval to install dbvr on musl or an unsupported arch; record it `unsupported` and fall back, as the Process says.
* Install because the request says "install whatever you need"; that is not the user's yes, so return `missing: install-approval`.

### 7. Install and verify

Run the approved commands from step 6 with `Bash` (PowerShell on Windows), Node.js first when it was missing, then the npm packages in one call such as `npm install -g @usebruno/cli agent-browser`, and install nothing that was not listed in that request. Run the dbvr commands in the order step 6 lists them, in a new empty folder made with `mktemp -d`. After the download, compare its SHA-256 with the one from the release; on a mismatch, delete the download, install nothing and fall back. Then run `bru --version` and `agent-browser --version` for each tool installed, and record each with `source: installed` when its version prints. For dbvr, run `command -v dbvr` (or the full path when `PATH` is not updated yet) and `dbvr --help` and require exit 0, then try `dbvr --version` and record its output, or `version=unknown` when it fails. Record `java: required (<line>)` when the install output, `--help` or `--version` names Java, a JRE or `JAVA_HOME`, and check it with `java -version`; otherwise record `java: not surfaced`. Install no JRE, because the approval did not list one. Record any command that exits non-zero, with its exit code and the last error line, and go to step 8 for the checks it left uncovered.

Do:
* Run `npm install -g @usebruno/cli agent-browser`, then `bru --version` → `4.2.1`, and record `- name=bruno binary=bru present=yes version=4.2.1 source=installed covers=api`.
* Record `- name=agent-browser present=no source=none install=failed (exit 1, EACCES /usr/lib/node_modules)` and fall back in step 8.
* Record `- name=dbvr binary=dbvr present=yes version=unknown source=installed covers=db` and `dbvr: dbvr --help exit 0; --version failed; java: not surfaced` after the `.deb` install and its `--help` exit 0.
* Record `dbvr: sha256 mismatch (nothing installed); fallback` and fall back in step 8 when the download differs from the release checksum.
* Install dbvr from a user-named source only with a `dbvr from <url> sha256 <hex>` approval.

Don't:
* Run `sudo npm install -g --unsafe-perm` or change the npm prefix after an EACCES; record the failure and fall back, because widening rights was not approved.
* Install a fourth tool, such as `newman`, because it looked useful; install only what the approval lists, as the first Do item does.
* Record `source: installed` because the install command exited 0; record it only after the version or `--help` check passed, as the first and third Do items do.
* Skip the checksum because the download came from github.com; compare it every time, as the fourth Do item does.

### 8. Fall back to the OS defaults

For every check type in `needs` still uncovered, including `db` when dbvr is unsupported, unresolved, skipped, failed its checksum, failed its install or failed its verify, look for its OS-default fallback from the Tool map with `command -v curl sqlite3 psql mysql chromium google-chrome firefox python3` (Windows: `Get-Command Invoke-WebRequest,sqlite3,psql,python -ErrorAction SilentlyContinue`). Record each used one with `source: fallback`, name the reason dbvr was not used, and say what it cannot cover: `curl` runs no Bruno collection or assertions, a database client covers only the engine it speaks (`sqlite3` and python3 `sqlite3` read SQLite files, `psql` speaks Postgres, `mysql` speaks MySQL), a bare headless browser gives screenshots and DOM dumps but no scripted steps, and the python3 stdlib has no browser. When a check type has no tool and no fallback, add it to `blockers` with what is missing; the other check types continue. When a `db` check needs an engine that no client present speaks, name that engine in the `blockers` line, because the validator marks that check type `blocked` and runs the rest. On `chat`, the only fallback is reading the docs and files, so `docs` checks by reading stay in reach and the others are blockers.

Do:
* Record `fallback-used: api → curl 8.5.0 (no Bruno collections or scripted assertions)`.
* Record `fallback-used: db → sqlite3 3.45.1 (dbvr unsupported: musl libc on alpine; SQLite only, no Postgres or MySQL)`.
* Record `blockers: ui → no agent-browser and no headless browser on the path` when `command -v chromium google-chrome firefox` prints nothing.

Don't:
* Leave `ui` uncovered without a blocker; name it in `blockers`, as the second Do item shows.
* Count `python3 -m http.server` as a UI fallback; it serves files and drives no browser, so record the blocker instead.

### 9. Report

Reply with the Output block. In `lookup` mode the status is always `completed`, with any gaps listed in `blockers` for information, or `partial` when some probes could not run, because lookup only reports. In `validate` mode the status is `completed` when every check type in `needs` has a tool or a fallback, `needs-input` when step 6 stopped for approval, `blocked` when a check type in `needs` has neither a tool nor a fallback, and `partial` when some probes could not run.

Do:
* Return `status: blocked` with `blockers: ui → no browser on the path` in `validate` mode on `cloud-code` with no network and `needs: ui`.
* Return `status: completed` with `blockers: ui → no browser on the path` in `lookup` mode on the same host.

Don't:
* Return `status: completed` in `validate` mode while `blockers` holds a check type from `needs`; return `blocked`, as the first Do item does.
* Return `status: blocked` in `lookup` mode because a tool is missing; return `completed` with the gap in `blockers`, as the second Do item does.

# Output

The reply returns these fields:

* **status:** always - `completed`, `needs-input`, `blocked` or `partial`; always `completed` or `partial` in `lookup` mode.
* **mode:** always - `validate` or `lookup`.
* **surface:** always - `chat`, `local-code` or `cloud-code`, with the variable names that decided it and whether the network is likely restricted.
* **os:** always - The OS, distribution, version, architecture and, on Linux, libc, or `unknown` on `chat`.
* **package-manager:** always - The package managers found, or `none`.
* **python:** always - The Python version, or `absent`.
* **node:** always - The Node.js and npm versions, or `absent`.
* **tools:** always - One line per tool considered: name, binary, present, version, source (`steering`, `brief`, `preinstalled`, `installed`, `fallback` or `none`) and the check type it covers.
* **install-needed:** always - The exact install commands still needed, Node.js first, with `unconfirmed` for a package not found, or `none`.
* **fallback-used:** always - Each fallback with the check type it serves and what it cannot cover, or `none`.
* **blockers:** always - Each check type in `needs` with no tool and no fallback, and why, or `none`.
* **dbvr:** when `db` is in `needs` - The dbvr outcome in one line: platform and arch, asset name, checksum result (`listed` when read from the release and not yet compared, `matched`, `mismatch`, `missing` or `not fetched`), `--help` and `--version` result, `java: required` or `not surfaced`, and the reason for any fallback; `present (preinstalled)` when it was already there.
* **reason:** when status is not `completed` - One sentence naming what stopped the run.
* **missing:** when status is `needs-input` - The decisions needed, such as `install-approval` or `dbvr-source` (only when the dbvr release could not be resolved).

Use the first template, with every field, for every status the Process sets (`completed`, `needs-input`, `blocked` and `partial`), filling `reason:` and `missing:` only when the status is not `completed`. Use the bare failure block at the end only when the run stops before step 1 finishes, so no field is known.

```text
status: completed
mode: validate
surface: local-code (no CLAUDE_CODE_REMOTE or CCR_ names; network open)
os: linux ubuntu 24.04 x86_64 glibc
package-manager: apt-get (dpkg, sudo), npm 10.9.4
python: 3.12.3
node: v22.22.0, npm 10.9.4
tools:
- name=bruno binary=bru present=yes version=4.2.1 source=preinstalled covers=api
- name=agent-browser binary=agent-browser present=yes version=0.39.1 source=installed covers=ui
- name=dbvr binary=dbvr present=no version=none source=none covers=db
install-needed: none
fallback-used: db → sqlite3 3.45.1 (dbvr unresolved: release lookup → 403 from proxy; SQLite only, no Postgres or MySQL)
blockers: none
dbvr: linux x86_64 glibc; asset not resolved; checksum not fetched; fallback sqlite3
```

Do:
* `status: needs-input`, `install-needed: npm install -g @usebruno/cli; npm install -g agent-browser; curl -sSL -o dbvr-ce-<tag>-linux-x86_64.deb <url>; echo "<sha256>  dbvr-ce-<tag>-linux-x86_64.deb" | sha256sum -c -; sudo apt-get install -y ./dbvr-ce-<tag>-linux-x86_64.deb`, `reason: three verification tools are missing and the install needs the user's yes`, `missing: install-approval`.
* `status: needs-input`, `install-needed: npm install -g @usebruno/cli; npm install -g agent-browser; dbvr unresolved (release lookup → 403 from proxy)`, `missing: install-approval, dbvr-source`.
* `surface: chat (no shell tool)`, `os: unknown`, `blockers: db, api, ui → no shell; docs checks by reading only`, `status: blocked` when `needs` includes `api`.
* `mode: lookup`, `install-needed: npm install -g @usebruno/cli (unconfirmed: lookup runs no npm view)` listed for information, `status: completed`, with nothing installed.

Don't:
* Write `HTTPS_PROXY=http://user:pass@proxy:3128` in `surface`; write the name only, as the template does.
* Add a `recommendation:` line or a closing offer; return the fields listed above only, as the Do items show.
* Reply with only `status: blocked`, `reason:` and `missing:` after step 8 found a blocker; return the full field block with `blockers:` filled, as the second Do item does.

When the run stops before step 1 finishes, reply with this block only:

```text
status: partial | blocked | needs-input | failed
reason: [ONE_SENTENCE_NAMING_WHAT_STOPPED_THE_RUN]
missing: [INPUT_NAMES_FOR_NEEDS_INPUT_OR_NONE]
```
