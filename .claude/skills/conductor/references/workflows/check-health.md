Used by SKILL.md step 4.

# Input

* **trigger:** optional - default: the user's turn - What started the check, such as the daily review or the user asking `how are we doing?`.

# Process

### 1. Check presence

Call `ListAgents`, read the roster and compare them by the presence rule: mark each missing owner, set `listed` again on one that came back, add any new listed `build-lead` with zero tickets, and write the roster.

Do:
* Mark `build-lead-3` `missing` with `since: 2026-10-28 08:00` when `ListAgents` no longer shows it and it owns open `acme-web-150`.

Don't:
* Message `build-lead-3` to ask where it went; a missing session cannot ACK, so tell the user, as the presence rule sets.

### 2. Measure

Recompute the 50th, 70th and 85th percentiles and the four flow metrics, derive `age` for each open ticket and place it against the percentiles.

### 3. Check in

Ask an owner for status only where the check-in rule allows it, under `Skill(agentville:intercommunicate)`, and send nothing to a missing session.

### 4. Apply blocker policies

Apply the blocker policies to each blocked ticket: nudge the owner, or ask the user about escalation or the cut-off with `AskUserQuestion`, naming the ticket, owner, reason, kind, how long it has stood and the options; with no person reachable, put the question in `<open>` as `needs-input`.

Do:
* Ask the user `acme-web-150 has waited 4 days on design sign-off (external), past the 85th percentile of 3 days: cancel, re-scope or keep?`.

Don't:
* Cancel `acme-web-150` yourself at the cut-off; the user decides, as the Do item asks.

### 5. Report

Rate the board by the RAG rule against `trigger`'s period and build the one-page report of that rule, with each missing session, its ticket and options, and any pattern across tickets. Set `last-rag` and `last-review` and write the roster.

# Output

* **status:** always - In `<status>`: `completed` when the report is built.
* **outcome:** always - In `<outcome>`: the overall RAG, its trend and whether the SLE is a best guess.
* **board:** always - In `<claims>`: the one-page report of the RAG rule as one minified JSON line.
* **presence:** always - In `<claims>`: each session found `missing`, back or added, or `no change`.
* **roster:** always - In `<artefacts>`: the absolute roster path.
* **open:** always - In `<open>`: the escalation and cut-off questions, or `none`.
* **deviations:** always - In `<deviations>`: `none`, or what was skipped.

```text
<status>completed</status>
<outcome>Board Amber, trend down; the SLE is a best guess (4 of 10 tickets finished).</outcome>
<claims>
- board: {"rag":"amber","trend":"down","wip":[{"ticket":"acme-api-142","owner":"build-lead-2"}],"urgent":["acme-web-150 2.5d of p70 2d"],"blockers":[],"awaiting-review":["acme-api-139 PR 307"],"throughput":"3 this week","decisions":[]}. verified: roster read and ListAgents this turn
- presence: no change. verified: ListAgents matched every owner
</claims>
<artefacts>
roster: {{ PROJECT_ROOT }}/.agentville/topics/conductor-roster/conductor/artefacts/roster.md
</artefacts>
<open>none</open>
<deviations>none</deviations>
```

Do:
* `- presence: build-lead-3 missing since 2026-10-28 08:00, holds acme-web-150; options wait, hand to another build-lead, drop` in `<claims>`.
* `<open>decision: acme-web-150 past p85 while blocked; cancel, re-scope or keep</open>` at the cut-off.

Don't:
* Rank sessions in the board; name patterns only, as the flow-health rule sets and the Do items show.
* Add a line outside the six tags; keep fields inside their tags.

When the part cannot finish, reply with this template only:

```text
<status>blocked | needs-input | failed</status>
<outcome>The health check could not run: the roster is unreadable and the rebuild got no answers.</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: none</open>
<deviations>none</deviations>
```
