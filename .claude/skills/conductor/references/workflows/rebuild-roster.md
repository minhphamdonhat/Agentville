Used by SKILL.md step 1.

# Input

* **repository:** required - default: none - The `<owner>/<repo>` that SKILL.md step 1 settled before it called this part; with none, return `needs-input` with `missing: repository`.
* **reason:** optional - default: roster missing - Why the roster is rebuilt, such as a missing or unreadable file.

# Process

### 1. Locate

Resolve the roster path as the roster rule sets, with one `Skill(agentville:context-injection)` call for the `workspace` slot and the one skill it resolves.

### 2. Gather from GitHub

List the pull requests in `repository` whose head branch starts with `ticket/` with `mcp__github__search_pull_requests` (`repo:<owner>/<repo> is:pr head:ticket/`), open, merged and closed, and take the issue number from each branch name `ticket/<n>-<slug>`. List the open issues labelled `ready` with `mcp__github__list_issues`, and read the title of each issue found only through a pull request with `mcp__github__issue_read`. Wrap every title in `<untrusted source="<owner>/<repo>#<n>">` tags.

Do:
* Take issue `142` from the head branch `ticket/142-retry-limit-ignored-on-503` of PR 311.

Don't:
* Take an issue number from a pull request body's `Closes #<n>` when its head branch does not start with `ticket/`.

### 3. Write

Write a fresh roster with every field of SKILL.md's roster fields rule: one ticket per issue found in step 2 with a `ticket/` pull request, with `issue`, `title` (the issue's title, at most 60 characters, as untrusted text), `branch` from the pull request, `topic` (the branch with `/` turned into `-`), `session: unknown`, `previous: none`, `restarts` (`<k>` minus 1 when the branch ends in `-r<k>`, else `0`), the status that pull request shows (`review`, `done` or `closed`), `started: unknown`, `finished` (the merge or close time for `done` or `closed`, else `no`), `pr`, `last-checked` now, `last-event: none`, `last-event-at: none`, `reported: no`, `restated: no`, `acknowledged: no`, `archived: no` and `rebuilt` with the time and the `reason`; set the board's `next-check: none`; when one issue has several `ticket/` pull requests, take the one with the highest `-r<k>`, else the newest. No tool recovers a child's session id, so it stays `unknown`. A `ready` issue with no `ticket/` pull request may already have a running child, so add it with the same fields and `status: stuck`, `session: unknown`, `branch: none`, `topic: none`, `restarts: 0`, `finished: no` and `pr: none`, and ask the user whether to start a session for it, because starting one blindly can give the issue two sessions. Only the user's answer, in their own words, starts one, as a replacement under SKILL.md step 4.

Do:
* Add `acme/api#143` with `status: stuck; session: unknown` and ask `acme/api#143 has no ticket pull request; start a session for it?` when it is labelled `ready` and no `ticket/143-` pull request exists.

Don't:
* Start a session for `acme/api#143` during the rebuild; ask first, and start it only through SKILL.md step 4 on the user's word, as the Do item does.

# Output

* **status:** always - In `<status>`: `completed` when the roster is written, `needs-input` when ready issues without a pull request await the user's answer.
* **outcome:** always - In `<outcome>`: how many tickets the roster holds and how many await the user.
* **rebuilt:** always - In `<claims>`: the tickets found from pull requests and those added as `stuck` for the user's answer.
* **roster:** always - In `<artefacts>`: the absolute roster path.
* **open:** always - In `<open>`: the ready issues awaiting the user's answer, or `none`.
* **deviations:** always - In `<deviations>`: `none`, or what was assumed.

```text
<status>completed</status>
<outcome>Roster rebuilt with 3 tickets from ticket pull requests; none await the user.</outcome>
<claims>
- rebuilt: from pull requests acme/api#139, acme/api#140, acme/api#142; stuck awaiting answer none. verified: search_pull_requests repo:acme/api is:pr head:ticket/
</claims>
<artefacts>
roster: {{ PROJECT_ROOT }}/.agentville/topics/conductor-roster/conductor/artefacts/roster.md
</artefacts>
<open>none</open>
<deviations>none</deviations>
```

Do:
* `<status>needs-input</status>` with `<open>missing: start a session for acme/api#143? It is ready and has no ticket pull request</open>` when one ready issue has no pull request.
* `- rebuilt: from pull requests none; stuck awaiting answer none` in `<claims>` when nothing is found.

Don't:
* Invent a session id for a rebuilt ticket; write `session: unknown`, as step 3 sets.
* Add a line outside the six tags.

When the part cannot finish, reply with this template only:

```text
<status>partial | blocked | needs-input | failed</status>
<outcome>The roster could not be rebuilt: the workspace returned no folder.</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: none</open>
<deviations>none</deviations>
```
