Used by SKILL.md step 8.

# Input

* **agent-file:** required - default: none - The validated draft `<STAGING>/<agent-name>.md`.
* **staging:** required - default: none - The staging folder `<STAGING>`.
* **run-mode:** optional - default: ask - `headless` (run the `claude` CLI here, which spends model usage) or `dispatch` (write prompt files and grade the reports someone else returns).
* **models:** optional - default: the session model - The model for headless runs, such as `sonnet`.
* **workdir:** optional - default: none - A checkout the cases read, passed to the CLI with `--add-dir`.
* **baseline:** optional - default: `{{ SKILL_ROOT }}/assets/base/worker.md` - The agent the compiled one is scored against; `none` when the agent under test is the base worker itself, so the baseline is plain `claude -p` with no agent, the compiled agent's `tools` allowed, its `disallowedTools` denied and the same model.

# Process

### 1. Write the cases

Run `python3` on Linux and macOS and `py -3` on Windows wherever this workflow shows `python3`.

Run `python3 {{ SKILL_ROOT }}/scripts/eval.py init <agent-file> <STAGING>/evals/evals.json` with Bash; it writes one case skeleton per workflow. Fill each case with `Edit`: a short relay brief as `prompt`, the `role`, the expected relay `status` token, `expect` strings the report must contain and `forbid` strings it must not. Add at least one case per workflow, and one case whose right answer is `blocked`, such as a reviewer brief that asks for an edit. When a case reads or edits a file, give the file as a fixture in the case's `files` map (`{"rel/path": "content"}`); eval.py writes it into a fresh sandbox `<STAGING>/evals/out/sandbox/<case>.<label>/` before each run, so both agents see the same file. Grade file effects with `expect_files` (`{"rel/path": "text the file must contain after the run"}`, for an edit or an artefact) and `unchanged` (fixture paths that must stay byte-identical, for a run that must not edit). Then run `python3 {{ SKILL_ROOT }}/scripts/eval.py check <agent-file> <STAGING>/evals/evals.json` until it prints `problems: 0`.

Do:
* Case `triage-1` for workflow `triage`, role `worker`, prompt `Triage the failing test in apps/api/tests/test_retry.py; edit nothing.`, status `completed`, expect `apps/api/tests/test_retry.py`.
* Case `review-edit-1`, role `reviewer`, prompt `Fix the typo in README.md.`, status `blocked`, expect `README.md`, forbid `Edit(`.
* Case `implement-1`, role `worker`, `files` `{"apps/web/greet.py": "...Helo..."}`, prompt `Fix the typo Helo in apps/web/greet.py.`, `expect_files` `{"apps/web/greet.py": "Hello"}`.

Don't:
* Leave a workflow without a case; `check` fails it, so add one as the first Do item shows.
* Point a case at a file of the real checkout that the sandbox lacks; the run cannot read it, so add it to `files` as the third Do item shows.
* Write a case that needs a paid service, or a web source unless the workflow's role is `scout` and the agent holds `WebSearch` or `WebFetch`; keep every other case local, like the Do items.

### 2. Choose the run mode

Run `claude --help` with Bash. Headless mode needs a `claude` on the path whose help lists `-p`, `--agent`, `--output-format`, `--no-session-persistence`, `--permission-mode`, `--permission-prompts`, `--allowedTools`, `--disallowedTools`, `--plugin-dir`, `--model` and `--add-dir`; verify each flag in the help text, never assume it. When `run-mode` is ask, a person is reachable and the flags are present, ask "Run the evals headless here (uses model credit) or hand the prompts back for dispatch?" with `AskUserQuestion`. When no person is reachable, use `dispatch`, because a headless run spends credit nobody approved. When the CLI or a flag is missing, use `dispatch`; return `status: needs-input` with `missing: run-mode` only when the reports cannot be collected either way.

Do:
* Help lists every flag and the user picks headless: set `run-mode` to `headless`.
* `claude: command not found`: set `run-mode` to `dispatch` and note it in `warnings`.

Don't:
* Pass a flag the help does not list, such as a guessed `--agent-file`; use the flags the help shows.
* Start a headless run without the user's yes; ask first, as this step says.

### 3. Run the cases

For `headless`, run `python3 {{ SKILL_ROOT }}/scripts/eval.py run <agent-file> <baseline> <STAGING>/evals/evals.json <STAGING>/evals/out --execute` with Bash, adding `--model <models>` and `--workdir <workdir>` when given. It passes each agent's own `tools` as `--allowedTools` (an agent with no `tools` line, the worker and its variants, gets the built-in set `INHERIT_TOOLS` instead: TaskCreate, TaskUpdate, TaskGet, TaskList, TaskStop, Read, Write, Edit, Glob, Grep, Bash, NotebookEdit, Monitor and Skill, because `--permission-mode dontAsk` denies any tool that is not pre-approved) and the plugin folder that holds this skill as `--plugin-dir` (override with `--plugin-dir <dir>`), so the agent's tools and `Skill(agentville:relay)` resolve; with `baseline` `none` the base run drops `--agent` and gets the compiled agent's tools. Each run gets its own sandbox `<STAGING>/evals/out/sandbox/<case>.<label>/`, rebuilt before the run with the agents under `.claude/agents/` and the case's `files`, and its report is saved as `<case>.<label>.out.md`, where the label is `compiled` or `base`. Run it once without `--execute` first and read the printed `command:` lines and the `runs:` count.

For `dispatch`, run `python3 {{ SKILL_ROOT }}/scripts/eval.py prompts <agent-file> <baseline> <STAGING>/evals/evals.json <STAGING>/evals/out` with Bash. It keeps the sandbox of a case and label whose report is already saved, so rerunning it never erases a child's file effects before grade. It prints one `dispatch:` line per case and label with the prompt file, the sandbox `cwd=` the child must work in and the report path. Return those lines as `eval-dispatch` so each prompt runs in a fresh child and its report is saved to the named path; grade only after every report is saved.

Do:
* `dispatch: triage-1 | compiled | <STAGING>/evals/out/triage-1.compiled.prompt.md | cwd=<STAGING>/evals/out/sandbox/triage-1.compiled | save report to <STAGING>/evals/out/triage-1.compiled.out.md`.
* A headless run that prints `run_errors: 1`: grade anyway, because the failed run is saved as a `failed` report.

Don't:
* Run the compiled agent and the base worker on different prompts; both get the same case, as the script does.
* Write a report file by hand to fill a gap; leave it missing so `grade` reports `not run`.

### 4. Grade

Run `python3 {{ SKILL_ROOT }}/scripts/eval.py grade <agent-file> <STAGING>/evals/evals.json <STAGING>/evals/out` with Bash. Each report passes when its `<status>` tag holds a relay §4 token (and the case's `status`, when set), it follows the worker core's report shape, it holds every output field of the case's workflow (`always` and `when` alike, as the constraints core demands), every `expect` string and no `forbid` string, and its sandbox meets the case's `expect_files` and `unchanged`. It prints one `grade:` line per report, a `score:` line and `result: pass` only when every compiled case passed; the base worker's score is the baseline.

Do:
* Record `score: compiled 4/4 vs base 2/4`, `result: pass`.
* Record each failing `grade:` line, such as `missing workflow field verdict`, for the revise loop.

Don't:
* Edit `expect` or `forbid` to make a failing case pass; revise the agent instead.
* Report a score while any report is `not run`; report `not run` for the evals.

# Output

Reply with the six relay §4 tags, in order, flat, plain lines, with `none` in a tag that has nothing, or with the failure template when the evals cannot run:

* **status:** always - in `<status>`: `completed` when the evals ran, `partial` when some did not.
* **outcome:** always - in `<outcome>`: the result in one or two sentences.
* **score:** always - in `<claims>` as `- score: <value>. <label>: <evidence>`: `compiled <n>/<N> vs base <m>/<N>` or `not run`.
* **result:** always - in `<claims>` as `- result: <pass|fail|not run>. <label>: <evidence>`.
* **run-mode:** always - in `<claims>` as `- run-mode: <headless|dispatch>. <label>: <evidence>`.
* **cases:** always - in `<artefacts>` as `cases: <STAGING>/evals/evals.json`.
* **eval-dispatch:** when `run-mode` is dispatch, in `<artefacts>` as `eval-dispatch:` then the dispatch lines, before grading.
* **failing-grades:** when a case failed, in `<open>`: each failing `grade:` line for the revise loop, or `none`.

```text
<status>completed</status>
<outcome>The compiled agent scored 3/3 against 1/3 for the base worker.</outcome>
<claims>
- run-mode: headless. verified: eval.py run output
- score: compiled 3/3 vs base 1/3. verified: eval.py grade output
- result: pass. verified: eval.py grade output
</claims>
<artefacts>
cases: <STAGING>/evals/evals.json
eval-dispatch: none
</artefacts>
<open>none</open>
<deviations>none</deviations>
```

Do:
* Record `- score: compiled 3/3 vs base 1/3. verified: eval.py grade output` and `- result: pass. verified: eval.py grade output`.
* Record `- run-mode: dispatch. verified: the run-mode input`, `- score: not run. verified: no report graded` and `eval-dispatch:` with six lines for three cases.

Don't:
* Report `result: pass` with a `not run` score; the Do items show the two honest forms.
* Add a tag the template lacks; return the six tags only.

When the evals cannot run, reply with this block only:

```text
<status>blocked | needs-input | failed</status>
<outcome>one sentence naming what stopped the run</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: run-mode, for needs-input; otherwise what would unblock the run</open>
<deviations>none</deviations>
```
