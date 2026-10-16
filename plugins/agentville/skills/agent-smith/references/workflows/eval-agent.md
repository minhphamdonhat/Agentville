Used by SKILL.md step 8.

# Input

* **agent-file:** required - default: none - The validated draft `<STAGING>/<agent-name>.md`.
* **staging:** required - default: none - The staging folder `<STAGING>`.
* **run-mode:** optional - default: ask - `headless` (run the `claude` CLI here, which spends model usage) or `dispatch` (write prompt files and grade the reports someone else returns).
* **models:** optional - default: the session model - The model for headless runs, such as `sonnet`.
* **workdir:** optional - default: none - A checkout the cases read, passed to the CLI with `--add-dir`.

# Process

### 1. Write the cases

Run `python3 {{ SKILL_ROOT }}/scripts/eval.py init <agent-file> <STAGING>/evals/evals.json` with Bash; it writes one case skeleton per workflow. Fill each case with `Edit`: a short relay brief as `prompt`, the `role`, the expected relay `status` token, `expect` strings the report must contain and `forbid` strings it must not. Add at least one case per workflow, and one case whose right answer is `blocked`, such as a reviewer brief that asks for an edit. Then run `python3 {{ SKILL_ROOT }}/scripts/eval.py check <agent-file> <STAGING>/evals/evals.json` until it prints `problems: 0`.

Do:
* Case `triage-1` for workflow `triage`, role `worker`, prompt `Triage the failing test in tests/test_retry.py; edit nothing.`, status `completed`, expect `tests/test_retry.py`.
* Case `review-edit-1`, role `reviewer`, prompt `Fix the typo in README.md.`, status `blocked`, expect `changed: no edits`, forbid `Edit(`.

Don't:
* Leave a workflow without a case; `check` fails it, so add one as the first Do item shows.
* Write a case that needs a paid service, or a web source unless the workflow's role is `scout` and the agent holds `WebSearch` or `WebFetch`; keep every other case local, like the Do items.

### 2. Choose the run mode

Run `claude --help` with Bash. Headless mode needs a `claude` on the path whose help lists `-p`, `--agent`, `--output-format`, `--no-session-persistence`, `--permission-mode`, `--permission-prompts`, `--allowedTools`, `--plugin-dir`, `--model` and `--add-dir`; verify each flag in the help text, never assume it. When `run-mode` is ask, a person is reachable and the flags are present, ask "Run the evals headless here (uses model credit) or hand the prompts back for dispatch?" with `AskUserQuestion`. When no person is reachable, use `dispatch`, because a headless run spends credit nobody approved. When the CLI or a flag is missing, use `dispatch`; return `status: needs-input` with `missing: run-mode` only when the reports cannot be collected either way.

Do:
* Help lists every flag and the user picks headless: set `run-mode` to `headless`.
* `claude: command not found`: set `run-mode` to `dispatch` and note it in `warnings`.

Don't:
* Pass a flag the help does not list, such as a guessed `--agent-file`; use the flags the help shows.
* Start a headless run without the user's yes; ask first, as this step says.

### 3. Run the cases

For `headless`, run `python3 {{ SKILL_ROOT }}/scripts/eval.py run <agent-file> {{ SKILL_ROOT }}/assets/base/worker.md <STAGING>/evals/evals.json <STAGING>/evals/out --execute` with Bash, adding `--model <models>` and `--workdir <workdir>` when given. It passes each agent's own `tools` as `--allowedTools` and the plugin folder that holds this skill as `--plugin-dir` (override with `--plugin-dir <dir>`), so the agent's tools and `Skill(agentville:relay)` resolve. It writes both agents into a sandbox `.claude/agents/` folder and saves each report as `<case>.<label>.out.md`, where the label is `compiled` or `base`. Run it once without `--execute` first and read the printed `command:` lines.

For `dispatch`, run `python3 {{ SKILL_ROOT }}/scripts/eval.py prompts <agent-file> {{ SKILL_ROOT }}/assets/base/worker.md <STAGING>/evals/evals.json <STAGING>/evals/out` with Bash. It prints one `dispatch:` line per case and label with the prompt file and the report path. Return those lines as `eval-dispatch` so each prompt runs in a fresh child and its report is saved to the named path; grade only after every report is saved.

Do:
* `dispatch: triage-1 | compiled | <STAGING>/evals/out/triage-1.compiled.prompt.md | save report to <STAGING>/evals/out/triage-1.compiled.out.md`.
* A headless run that prints `run_errors: 1`: grade anyway, because the failed run is saved as a `failed` report.

Don't:
* Run the compiled agent and the base worker on different prompts; both get the same case, as the script does.
* Write a report file by hand to fill a gap; leave it missing so `grade` reports `not run`.

### 4. Grade

Run `python3 {{ SKILL_ROOT }}/scripts/eval.py grade <agent-file> <STAGING>/evals/evals.json <STAGING>/evals/out` with Bash. Each report passes when its first line holds a relay status token (and the case's `status`, when set), it holds the core fields `changed`, `checks` and `next`, every `always` field of the case's workflow, every `expect` string and no `forbid` string. It prints one `grade:` line per report, a `score:` line and `result: pass` only when every compiled case passed; the base worker's score is the baseline.

Do:
* Record `score: compiled 4/4 vs base 2/4`, `result: pass`.
* Record each failing `grade:` line, such as `missing workflow field verdict`, for the revise loop.

Don't:
* Edit `expect` or `forbid` to make a failing case pass; revise the agent instead.
* Report a score while any report is `not run`; report `not run` for the evals.

# Output

Reply with this block, or with the failure block when the evals cannot run.

```text
run-mode: headless | dispatch
cases: <STAGING>/evals/evals.json
score: compiled <n>/<N> vs base <m>/<N> | not run
result: pass | fail | not run
eval-dispatch: <the dispatch lines, for dispatch mode before grading; otherwise none>
```

Do:
* `run-mode: headless`, `score: compiled 3/3 vs base 1/3`, `result: pass`.
* `run-mode: dispatch`, `score: not run`, `eval-dispatch:` with six lines for three cases.

Don't:
* Report `result: pass` with a `not run` score; the Do items show the two honest forms.
* Add a field the template lacks; return the five fields only.

```text
status: blocked | needs-input | failed
reason: <one sentence>
missing: <run-mode, for needs-input; otherwise none>
```
