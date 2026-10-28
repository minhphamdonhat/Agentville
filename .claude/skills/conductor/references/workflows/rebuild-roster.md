Used by SKILL.md step 2.

# Input

* **reason:** optional - default: roster missing - Why the roster is rebuilt, such as a missing or unreadable file.

# Process

### 1. Locate

Resolve the roster path as the roster rule sets, with one `Skill(agentville:context-injection)` call for the `workspace` slot and the one skill it resolves.

### 2. Ask

Call `ListAgents`, then ask each listed `build-lead` by message under `Skill(agentville:intercommunicate)` for its open ticket with status, started time, any blocker and any PR number, and for any ticket it finished with its started and finished times.

Do:
* Ask `build-lead-2` `request: roster-rebuild; send your open ticket (status, started, blocker, pr) and finished tickets (started, finished)`.

Don't:
* Ask the watcher `lookout` for tickets it owns; a watcher owns none, so ask only the `build-lead` sessions, as the Do item does.

### 3. Write

Write a fresh roster from the answers, marking each ticket `rebuilt` with the time and the `reason`, and list sessions that sent no ACK as `unknown`. With fewer finished tickets than `sle-min-items`, the SLE falls back to the best guess.

# Output

* **status:** always - In `<status>`: `completed` when the roster is written, `partial` when some sessions did not answer.
* **outcome:** always - In `<outcome>`: how many tickets and sessions the roster holds.
* **rebuilt:** always - In `<claims>`: the sessions that answered, those marked `unknown`, and whether the SLE is a best guess.
* **roster:** always - In `<artefacts>`: the absolute roster path.
* **open:** always - In `<open>`: the sessions that did not answer, or `none`.
* **deviations:** always - In `<deviations>`: `none`, or what was assumed.

```text
<status>completed</status>
<outcome>Roster rebuilt with 3 tickets and 2 sessions.</outcome>
<claims>
- rebuilt: answered build-lead-1, build-lead-2; unknown none; SLE best guess (2 of 10 finished). verified: ACKs and replies this turn
</claims>
<artefacts>
roster: {{ PROJECT_ROOT }}/.agentville/topics/conductor-roster/conductor/artefacts/roster.md
</artefacts>
<open>none</open>
<deviations>none</deviations>
```

Do:
* `<status>partial</status>` with `<open>build-lead-3 sent no ACK; marked unknown</open>` when one session is silent.
* `- rebuilt: answered none; SLE best guess (0 of 10 finished)` in `<claims>` when no `build-lead` is listed.

Don't:
* Invent a ticket for a silent session; mark it `unknown`, as the first Do item does.
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
