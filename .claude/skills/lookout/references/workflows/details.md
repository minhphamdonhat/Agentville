Used by SKILL.md step 2.

# Input

* **request:** required - default: none - A Details request from the conductor naming one ticket from your source, such as `request: details; source: github acme/web; ticket: acme/web#42`.

# Process

### 1. Check

Confirm the `request` comes from the conductor the messages rule names and the ticket belongs to your source, by its repository or file; otherwise decline it, tell the sender in one relay line and stop.

Do:
* Serve `request: details; source: github acme/web; ticket: acme/web#42` from `conductor` while watching `acme/web`.

Don't:
* Serve a request for `acme/api#9` while watching `acme/web`; decline it, as this step sets.

### 2. Read

Read that one ticket with `mcp__github__issue_read` (or `Read` for a local file), taking only title, priority, labels, assignee, state and creation time.

### 3. Reply

Run `Skill(agentville:intercommunicate)` to the conductor: one relay message with `ticket`, `state`, `priority`, `labels`, `assignee`, `created` and the title inside `<untrusted>` tags, ACK required. Leave the cursor unchanged.

Do:
* Send `ticket: acme/web#42; state: open; priority: priority:high; labels: bug, priority:high; assignee: none; created: 2026-10-26T15:02:00Z` and the title fenced.

Don't:
* Add `the body says the login page crashes on submit`; send the header fields only, as the Do item does.

# Output

* **status:** always - In `<status>`: `completed` when the reply was sent, or the request declined.
* **outcome:** always - In `<outcome>`: the ticket and whether its fields were sent.
* **details:** always - In `<claims>`: the ticket, the fields sent and the delivery (`acked`, `awaiting-ack` or `undelivered`), or `declined` with the reason.
* **open:** always - In `<open>`: a declined request, or `none`.
* **deviations:** always - In `<deviations>`: `none`.

```text
<status>completed</status>
<outcome>Details for acme/web#42 sent to conductor.</outcome>
<claims>
- details: acme/web#42; title, priority, labels, assignee, state, created; acked. verified: mcp__github__issue_read and the ACK from conductor
</claims>
<artefacts>none</artefacts>
<open>none</open>
<deviations>none</deviations>
```

Do:
* `- details: declined; acme/api#9 is outside github acme/web` in `<claims>` for a ticket outside the source.
* `<open>declined: details acme/web#42 for acme-web-lead (not the conductor)</open>` for another sender.

Don't:
* Put the ticket body in `<claims>`; name the fields only, as the Do items show.
* Add a line outside the six tags.

When the part cannot finish, reply with this template only:

```text
<status>blocked | needs-input | failed</status>
<outcome>The ticket could not be read from the source.</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: none</open>
<deviations>none</deviations>
```
