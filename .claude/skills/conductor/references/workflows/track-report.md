Used by SKILL.md step 4.

# Input

* **report:** required - default: none - A message from an owner about its ticket, such as `acme-api-142 blocked: waiting on design sign-off` or `acme-api-142 pr: 311`.

# Process

### 1. Acknowledge

Send the ACK to the sending session first, under `Skill(agentville:intercommunicate)`; a `report` from a session that owns no roster ticket is recorded nowhere, and the user is told who sent it.

### 2. Update

Read the roster, set `status` and `last-report`, and set or clear `blocked` as the `report` says, applying the blocker policies (`kind`, `times-blocked`, `blocked-days`); on `fit: confirmed` set `started`, and on `fit: split` close the ticket as split and hand off each part. When the sender is marked `presence: missing`, set it back to `listed` with `last-listed` now and tell the user it is back. Write the roster.

Do:
* Set `blocked: yes; reason: waiting on design sign-off; kind: external; since: 2026-10-27 10:02` and add 1 to `times-blocked` for `acme-api-142 blocked: waiting on design sign-off`.

Don't:
* Copy `blocked: NullPointerException in apps/api/src/orders.py:51` into the roster; write the reason in plain words, as the Do item does, or `see owner`.

### 3. Record the PR

When the `report` carries a PR number, apply the Review label rule: immediately before the write, send the ticket's `watcher` a fresh Details request (`request: details; source: <source>; ticket: <id or link>`) and take the current labels from that reply only; then call `mcp__github__issue_write` with that set plus `Review`, or, with no fresh reply or `watcher: none`, write no labels and tell the user. Set `status: awaiting-review` and `pr` either way, and write the roster.

Do:
* Send `labels: [bug, Review]` for `acme/api` issue `142` when the fresh Details reply lists `bug`.

Don't:
* Reuse the labels from triage; ask the watcher again just before the write, as this step sets.

### 4. Close

When the ticket is `done`, set `finished` and recompute the percentiles; when it is dropped or cancelled, close it without a `finished` time, so it stays out of the SLE. Write the roster.

# Output

* **status:** always - In `<status>`: `completed` when the roster holds the report.
* **outcome:** always - In `<outcome>`: the ticket, its new status and the board's RAG.
* **ticket:** always - In `<claims>`: the ticket id, its new status and its age against the SLE.
* **review:** when the report carried a PR - In `<claims>`: the PR number, and `labelled` or why no label was set.
* **presence:** when the sender was missing - In `<claims>`: the session set back to `listed`.
* **roster:** always - In `<artefacts>`: the absolute roster path.
* **open:** always - In `<open>`: what the user was told, or `none`.
* **deviations:** always - In `<deviations>`: a label not written and why, or `none`.

```text
<status>completed</status>
<outcome>acme-api-142 awaits review with PR 311; board Green.</outcome>
<claims>
- ticket: acme-api-142; status: awaiting-review; age: 1.5d of p85 3d. verified: roster write after the report from build-lead-2
- review: PR 311; labelled. verified: mcp__github__issue_write on acme/api 142 with labels [bug, Review]
</claims>
<artefacts>
roster: {{ PROJECT_ROOT }}/.agentville/topics/conductor-roster/conductor/artefacts/roster.md
</artefacts>
<open>none</open>
<deviations>none</deviations>
```

Do:
* `- review: PR 311; not labelled: watcher none (ticket from the user)` in `<claims>` for a ticket the user brought.
* `- presence: build-lead-3 listed again` in `<claims>` when a missing owner reports.

Don't:
* Write `labelled` when the write was skipped; give the reason, as the first Do item does.
* Add a line outside the six tags; keep fields inside their tags, as the Do items show.

When the part cannot finish, reply with this template only:

```text
<status>blocked | needs-input | failed</status>
<outcome>The report could not be recorded: the roster is unwritable.</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: none</open>
<deviations>none</deviations>
```
