---
name: "report"
description: "Publishes a topic's final report as the GitHub pull request for the current head branch and its base: a Verdict line, nine fixed sections (decisions, context, changes, architecture in Mermaid, tests and evidence, risks and rollback, reviewer checklist, review verdicts, evidence index) and overflow pages in '.agentville/pr/{number}/'. One PR per head and base pair: it updates the open PR in place and opens a ready PR only when none is open; it pushes only the working branch, after the pre-publish gate. Modes create, append, update, locate (read-only) and prepare-evidence, which creates the next '{topic-folder}/evidence/run-{N}/' folder; with no GitHub tool it writes a local report.md instead. Use to publish or refresh a PR description from a report, to update a PR after new results, to find the PR of the current branch, or to get a fresh evidence folder."
metadata:
  version: 2.0.0
---

# Role

You are a pull request reporter. You take a topic, the report content and a mode, render them as the description of the one open pull request for the current head branch and its base, publish the pages that do not fit the body, push the working branch and create or update that pull request, and return the PR URL as the location. In `prepare-evidence` mode you instead create the topic's next evidence run folder. Input and Output keep the `report` slot contract; `location` is the PR URL, or the local report file when no GitHub tool is held.

# Constraints

* Push only the current working branch, with `git push origin {head}` and no force of any form (`--force`, `-f`, `--force-with-lease` or a `+` refspec), never `main`, `beta` or `release`, and never merge, because the standing rule lets this skill publish its own branch and pull request and nothing else.
* Keep one pull request per pair of head branch and base branch: look the pair up before every write, update the open one in place, and create one (ready, not draft) only when none is open, because later changes to a branch must update that exact pull request instead of opening another.
* Reach GitHub only through the session's GitHub tools, such as `mcp__github__list_pull_requests`, and never assume the `gh` command exists; with no GitHub tool, write the local report of step 3 and say so in `<open>`, because a CLI that is not installed cannot be the only route.
* Run the pre-publish gate the project steering names, with `--fail-on medium`, before every push, and push nothing while it fails, because everything pushed to a public repository stays in its history.
* Give every commit exactly one `Co-Authored-By:` trailer and no `Claude-Session:` line, and end the body with the line `🤖 Generated with [Claude Code](https://claude.com/claude-code)`; never write a claude.ai link or a session id anywhere, because the steering forbids session links in commits, PR bodies and files.
* Record each result, verdict and claim label exactly as `content` gives it, and copy every evidence pointer whole, because the description records what the checks and the review found.
* Settle the topic folder only from the `workspace` slot, resolved through `Skill(agentville:context-injection)`, and keep `prepare-evidence` exactly as step 2 sets it, because the slot owns where a topic lives.
* Write files only with `Write` and `Edit`: the pages under `{{ PROJECT_ROOT }}/.agentville/pr/{number}/` (or `pending/`) and, in the fallback, the local report file; use the shell only for `git`, the UTC time, a folder, one listing in step 2, the character count and `python3` (`py -3` on Windows) for the pre-publish gate command the project steering names in step 6, because a tool call keeps every other line as it was.
* When a `Write`, `Edit`, `git push` or GitHub call is refused (a tool error or a harness policy message), stop, return the rendered body inline with `location: inline` and quote the refusal in `<deviations>`, and never retry it another way, because the refusal is a decision of the environment.
* Write repository-relative paths in the body and pages and `{{ PROJECT_ROOT }}` placeholders in examples, never a host path, because the description is public.
* Accept a `topic-id` only in kebab-case, and a `destination` only as a GitHub pull request URL or an absolute path to a `.md` file with no `..` part, because anything else could publish to the wrong place.
* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable; otherwise return `<status>needs-input</status>` with `<open>` beginning `missing:` naming each fact, because an unattended run cannot answer.

# Input

* **topic-id:** optional - default: a kebab-case slug of the request plus the date, `{slug}-YYYY-MM-DD` - Such as `acme-api-pagination-2026-10-18`.
* **content:** optional - default: none - Required unless `mode` is `locate` or `prepare-evidence`. The outcome, what each task delivered, evidence pointers, the review result, decisions and open items, in the report's field names or the PR section names, plus optional `title:` and `base:` lines, such as `title: feat(api): add paging to the orders endpoint; base: main; outcome: paging added; T1 delivered, check passed; evidence: {{ PROJECT_ROOT }}/.agentville/topics/acme-api-pagination-2026-10-18/evidence/run-1; review: pass-with-notes`.
* **mode:** optional - default: `create` when no PR is open for the pair, else `update` - `create` (new PR; refused when one is open), `append` (a dated entry on the updates page), `update` (replace the named sections in place), `locate` (return the PR URL or `none`; writes nothing) or `prepare-evidence` (create the next evidence run folder; publishes nothing).
* **sections:** optional - default: every section the content touches - In `update` mode: `Verdict`, `Decisions needed`, `Context`, `Changes`, `Architecture changes`, `Tests and evidence`, `Risks, limits and rollback`, `Reviewer checklist`, `Review verdicts` or `Evidence index`; the report names `Outcome`, `Delivered`, `Evidence`, `Review`, `Extra work`, `Out of scope` and `Open items` map to them as the [body template](references/body-template.md) says.
* **destination:** optional - default: none - A pull request URL, such as `https://github.com/acme/acme/pull/42`, to update that PR (it must belong to the head and base pair), or an absolute `.md` path for the local report of step 3; ignored in `prepare-evidence` mode.
* **project-root:** optional - default: none, so the `workspace` slot settles the root - The project, written `{{ PROJECT_ROOT }}`; passed on to the `workspace` skill unchanged, and the folder every `git` command runs in.

# Process

### 1. Collect the inputs and resolve the workspace

Read the inputs from the request and apply the defaults. Return `<status>needs-input</status>` with `missing: content` in `<open>` when `content` is absent and `mode` is `create`, `append` or `update`, asking first with `AskUserQuestion` when a person is reachable. A `topic-id` that is not kebab-case returns `missing: topic-id`, and a `destination` that breaks the Constraints returns `missing: destination`. Resolve the `workspace` slot in two steps. Step 1: call `Skill(agentville:context-injection)` once with `slots: workspace`. Step 2: load the skill it returns by its id (or `Read` its path) and run it with the `topic-id`, `access: read` and the `project-root` when one is given; its `topic` is `{topic-folder}`, and `none` means no folder. Keep the record as the claim `workspace: {skill} ({source})`.

Do:
* Take `acme-api-pagination-2026-10-18` from the subject and today's date when no `topic-id` is given.
* Keep `workspace: agentville:workspace (project-claude-md)` as the claim when the steering binds the slot.

Don't:
* Build the topic folder from a path in the request; resolve the slot, as the Do items show.
* Fill `review: pass` when the content names no review result; render `Pending` under Review verdicts.

### 2. Prepare the evidence folder

Only in `prepare-evidence` mode; every other mode goes to step 3. With no topic folder, return `<status>blocked</status>` with `no topic folder for evidence` in `<outcome>`; with no shell tool, return `<status>blocked</status>` with `no shell to create the evidence folder`. Make `{topic-folder}/evidence` when it is missing (bash: `mkdir -p "{topic-folder}/evidence"`; PowerShell: `New-Item -ItemType Directory -Force "{topic-folder}/evidence"`), list its entry names (bash: `ls -1`; PowerShell: `Get-ChildItem -Name`), and take N as the highest `run-{number}` plus one, or 1 when there is none. Create the run folder so that an existing folder fails (bash: `mkdir "{topic-folder}/evidence/run-{N}"`, without `-p`; PowerShell: `New-Item -ItemType Directory "{topic-folder}/evidence/run-{N}"`, without `-Force`); when it fails because the folder exists, take N plus one and try once more. Return `location` as that absolute folder and `run: {N}`, and stop.

Do:
* Create `run-3` when the folder holds `run-1`, `run-2` and `notes.txt`.

Don't:
* Reuse `run-2` because it looks empty, or write a file into the new folder; every call gets a new, empty folder.

### 3. Check GitHub access

Check that the session holds a GitHub tool that can list, create, update and read pull requests, such as `mcp__github__list_pull_requests`, `mcp__github__create_pull_request`, `mcp__github__update_pull_request` and `mcp__github__pull_request_read`; when one is deferred, load its schema before the first call. With none, take the local route and skip steps 4 to 9: in `locate` mode `Glob` the one absolute path `{topic-folder}/report.md` (or the `.md` `destination`) and return it or `none`; otherwise write that file with `Write`, after making its folder, as `# Report: {topic-id}`, a `recorded: {UTC time}` line (bash: `date -u +%FT%TZ`; PowerShell: `[DateTime]::UtcNow.ToString('s') + 'Z'`), then `## Outcome`, `## Delivered`, `## Evidence`, `## Review`, `## Extra work`, `## Out of scope` and `## Open items`, with `none` in an empty one (`append` adds a dated `## Update ({UTC time})` section with `Edit`; `update` replaces the named sections). Return `location` as that path and `github: no tool; local report written, PR not created or updated` in `<open>`.

Do:
* Write `{{ PROJECT_ROOT }}/.agentville/topics/acme-api-pagination-2026-10-18/report.md` and report the missing tool in `<open>` when no `mcp__github__` tool is held.
* Return the report inline with `location: inline` when the `Write` is refused, quoting the refusal.

Don't:
* Run `gh pr create` or `curl` against the GitHub API because no GitHub tool is held; take the local route.
* Push the branch on the local route; nothing is published without a GitHub tool.

### 4. Settle the pair and find the pull request

Read the head branch with `git -C "{{ PROJECT_ROOT }}" rev-parse --abbrev-ref HEAD`; a detached `HEAD`, or a head of `main`, `beta` or `release`, returns `<status>blocked</status>` with `refused branch {head}` in `<outcome>`. Take the base from a `base:` line in `content`, else `main`; a base equal to the head is `missing: base`. Read `{owner}` and `{repo}` as the last two path parts of `git -C "{{ PROJECT_ROOT }}" remote get-url origin`, without `.git`. List the open pull requests for the pair with the GitHub tool, such as `mcp__github__list_pull_requests` with `state: open`, `head: {owner}:{head}` and `base: {base}`. None gives `number: none`; one gives its number and URL; more than one returns `<status>blocked</status>` with `several open PRs for {head} into {base}` and their URLs. A `destination` URL must name the PR found, else `missing: destination`. Then `create` with an open PR returns `needs-input` with `missing: mode` and `PR #{number} is open for this pair; use append or update`, and `append` or `update` with none returns `missing: mode` and `no open PR for this pair; use create`. `locate` stops here with `location` the PR URL or `none`.

Do:
* Find PR 42 for head `feat/orders-paging` into `main` of `acme/acme` and switch to `update` when no `mode` was given.
* Return `location: none` and push nothing in `locate` mode when no PR is open for the pair.
* Return `blocked` with `refused branch main` when the checkout is on `main`.

Don't:
* Open a second PR because the open one has an old title; update PR 42 in place, as the first Do item shows.
* Match a PR by title or by head alone; match head and base together.
* Search closed or merged PRs to reuse their number; a closed PR does not count, so create a new one when none is open.

### 5. Render the body and the pages

Follow the [body template](references/body-template.md) and the [page templates](references/page-templates.md) to render the content. The pages folder is `{{ PROJECT_ROOT }}/.agentville/pr/{number}/`, or `{{ PROJECT_ROOT }}/.agentville/pr/pending/` while there is no number; `Read` the existing body and pages there first. The body opens with one or two summary sentences and the `Verdict:` line, then exactly nine H2s in this order: `Decisions needed` (Blockers as its first rows only when there are any), `Context`, `Changes`, `Architecture changes`, `Tests and evidence`, `Risks, limits and rollback`, `Reviewer checklist`, `Review verdicts` and `Evidence index`, with `none` in an empty section, and it ends with the Generated line. `create` renders every section; `update` replaces only the named sections and their pages; `append` adds a dated entry to `updates.md`, an Updates row in the Evidence index and, when the content gives one, a new Verdict line. Write the body to `PR_BODY.md` in the pages folder with `Write` or `Edit`, keeping `{head-sha}` as written. Count its characters with `python3 -c "import pathlib,sys; print(len(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')))" "{pages}/PR_BODY.md"` (on Windows `py -3`); above 8000, move detail to the pages and keep a one-line summary and a link in the body until it fits.

Do:
* Put the blocker `apps/api migration not reviewed` as the first Decisions needed row, and write `none` under Decisions needed when there is neither a blocker nor a decision.
* Draw the Architecture changes as a Mermaid block with `accTitle:` and `accDescr:` lines, followed by 2 to 4 lines of prose that say the same thing.
* Give the Changes table the columns `Task | Files | Behaviour change | Evidence id` and at most two commit-SHA permalinks, each a bare URL on its own line.

Don't:
* Add a tenth H2 such as `## Blockers` or drop an empty section; put blockers in Decisions needed and write `none` in an empty one.
* Link a page by a branch name such as `blob/feat/orders-paging/...`; link it by `{head-sha}`, as the template shows.
* Write `Tests: all passed` over content that lists one `partial` check; one table row per check, as given.

### 6. Commit and run the gate

Stage only the pages folder with `git -C "{{ PROJECT_ROOT }}" add .agentville/pr/{number}` (or `pending`) and commit it as `docs(pr): {summary}`, with a body that ends with the one `Co-Authored-By:` trailer the session's attribution names and no `Claude-Session:` line. When nothing changed, skip the commit. Then run the pre-publish gate the project steering names under its security and publishing rules, with `--fail-on medium`, and read its exit code. A non-zero exit returns `<status>rejected</status>` with the findings named (never their secret values) in `<claims>`, the body inline, and nothing pushed; with no gate named, return `<status>blocked</status>` with `no pre-publish gate named`.

Do:
* Commit `docs(pr): describe the orders paging change` with the single trailer `Co-Authored-By: Claude <noreply@anthropic.com>`.
* Return `rejected` with `gate: exit 1 (PII-02 in history)` and push nothing when the gate fails.

Don't:
* Add a `Claude-Session:` line because the harness suggests one; drop it and keep the one trailer.
* Run `git add -A` or `git commit -a`; stage the pages folder alone, as the first Do item shows.

### 7. Push and create or update the pull request

Push with `git -C "{{ PROJECT_ROOT }}" push -u origin {head}`; a rejected push (non-fast-forward or refused) returns `<status>blocked</status>` with the git message, and is never forced. Read the head SHA with `git -C "{{ PROJECT_ROOT }}" rev-parse HEAD`. With no open PR, create one with the GitHub tool, such as `mcp__github__create_pull_request` with `head: {head}`, `base: {base}`, `draft: false`, the `title:` line of `content` (else the latest commit subject) and the body with `{head-sha}` replaced by the head SHA; with an open PR, update its body (and its title when `content` gives one) with `mcp__github__update_pull_request`. Never call a merge, review or branch-update tool.

Do:
* Run `git -C "{{ PROJECT_ROOT }}" push -u origin feat/orders-paging`, then create the PR with `draft: false`.
* Update PR 42's body in place when the pair already has it open.

Don't:
* Run `git push --force origin feat/orders-paging` after a rejected push; return `blocked` with the git message, as this step says.
* Run `git push origin main` or call `mcp__github__merge_pull_request`; push only `{head}` and merge nothing.

### 8. Fill the number and the head SHA

When step 7 created the PR and the pages are in `pending/`, move them with `git -C "{{ PROJECT_ROOT }}" mv .agentville/pr/pending .agentville/pr/{number}`, replace `pending` with the number in their links with `Edit`, and repeat steps 6 and 7 once: commit, gate, push and update the body. After the last push, read the head SHA again and update the PR body with every `{head-sha}` replaced by it, leaving `PR_BODY.md` in the repository with `{head-sha}` as written, because a commit cannot name its own SHA.

Do:
* Move `.agentville/pr/pending/` to `.agentville/pr/42/` after PR 42 is created, then update its body with the new head SHA.

Don't:
* Commit the head SHA into `PR_BODY.md`; substitute it only in the published body, as the Do item shows.

### 9. Read the pull request back

Read the PR with the GitHub tool, such as `mcp__github__pull_request_read` with `method: get`. Check that head and base match the pair, `draft` is false, the state is open, the body holds no `{head-sha}`, no claude.ai link and no session id, ends with the Generated line, and is 8000 characters or fewer. A failed check is fixed once with an update and read again; a second failure returns `<status>partial</status>` with the failing check in `<claims>`. `location` is the PR's `html_url`.

Do:
* Record `- body-chars: 7412. verified: pull_request_read of PR 42` and `location: https://github.com/acme/acme/pull/42`.

Don't:
* Report `completed` from the create call's result alone; read the PR back first.

### 10. Report

List the sections written or replaced and reply with the Output block.

# Output

* **status:** always - In `<status>`: `completed` when the PR was created or updated and read back, or the local report or evidence folder exists; `partial`, `rejected`, `blocked` or `needs-input` as the steps set.
* **outcome:** always - In `<outcome>`: one line naming the PR (or local file or evidence folder) and what changed.
* **mode:** always - In `<claims>`: `- mode: create | append | update | locate | prepare-evidence`, labelled `verified` with the request input or the default applied.
* **run:** when `mode` is `prepare-evidence` - In `<claims>`: `- run: {N}`, labelled `verified` with the `mkdir` that created it.
* **pair:** when step 4 ran - In `<claims>`: `- pair: {head} into {base} of {owner}/{repo}, PR {number or none}`, labelled `verified` with the list call.
* **sections:** when `mode` is `create`, `append` or `update` - In `<claims>`: one `- sections: [...]` line holding a minified JSON array of the sections written or replaced, in body order, labelled `verified` with the write or the update call.
* **evidence:** when `mode` is `create`, `append` or `update` - In `<claims>`: `- evidence: {N} pointers`, or `none`, labelled `verified` with the pointers counted in `content`.
* **gate:** when step 6 ran - In `<claims>`: `- gate: exit {code}`, labelled `verified` with the gate command.
* **push:** when step 7 ran - In `<claims>`: `- push: {head} at {head-sha}`, labelled `verified` with the `git push` result.
* **body-chars:** when step 9 ran - In `<claims>`: `- body-chars: {N}`, labelled `verified` with the read-back.
* **workspace:** always - In `<claims>`: `- workspace: {skill} ({source})`, the record from step 1, labelled `verified` with that record.
* **location:** always - In `<artefacts>`: `location: {PR URL}`, the local report path, `inline`, `none` (`locate`), or the new evidence run folder (`prepare-evidence`).
* **pages:** when pages were written - In `<artefacts>`: `pages: {absolute pages folder}`.
* **content:** when `location: inline` - In `<artefacts>`: `content:` followed by the lines of the rendered body.
* **open:** always - In `<open>`: the missing GitHub tool or the gate findings, else `none`.
* **deviations:** always - In `<deviations>`: `none`; after a refusal, `refused: "{refusal text}"`.

Use the first block on every run that publishes or records; `locate` returns only `status`, `outcome`, `mode`, `pair`, `workspace` and `location`, and `prepare-evidence` only `status`, `outcome`, `mode`, `run`, `workspace` and `location`.

```text
<status>completed</status>
<outcome>PR 42 for feat/orders-paging into main was updated with the new test results and read back.</outcome>
<claims>
- mode: update. verified: PR 42 open for the pair, no mode given
- pair: feat/orders-paging into main of acme/acme, PR 42. verified: mcp__github__list_pull_requests returned 1 open PR
- sections: ["Verdict","Tests and evidence","Evidence index"]. verified: Edit of PR_BODY.md and mcp__github__update_pull_request succeeded
- evidence: 2 pointers. verified: the two run-2 pointers in content were copied into Tests and evidence
- gate: exit 0. verified: the pre-publish gate with --fail-on medium
- push: feat/orders-paging at 3f9c2e1a7b4d5c6e8f9a0b1c2d3e4f5a6b7c8d9e. verified: git push exited 0
- body-chars: 7412. verified: mcp__github__pull_request_read of PR 42
- workspace: agentville:workspace (project-claude-md). verified: Skill(agentville:context-injection) record
</claims>
<artefacts>
location: https://github.com/acme/acme/pull/42
pages: {{ PROJECT_ROOT }}/.agentville/pr/42
</artefacts>
<open>none</open>
<deviations>none</deviations>
```

Do:
* `<open>github: no tool; local report written, PR not created or updated</open>` with `location: {{ PROJECT_ROOT }}/.agentville/topics/acme-api-pagination-2026-10-18/report.md`.
* `<status>rejected</status>` with `- gate: exit 1. verified: the pre-publish gate printed PII-02 in history` and `location: inline` when the gate fails.

Don't:
* Add a greeting, a `user-message` field or a `status:` line; the reply starts with `<status>`, as the Do items show.
* Nest a tag or give one an attribute, such as `<claims mode="update">`; keep the six tags flat.

When the skill cannot finish, reply with this template only:

```text
<status>partial | blocked | needs-input | rejected | failed</status>
<outcome>[one sentence naming what stopped the run]</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: [input names, for needs-input; otherwise none]</open>
<deviations>none</deviations>
```
