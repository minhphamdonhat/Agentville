---
name: "intercommunicate"
description: "Sends a message to another session with delivery confirmation, or receives one: it checks the target with ListAgents, compiles the message with relay, requires an immediate ACK from the receiver, resends once when no ACK arrives and reports an undelivered message. For a session you spawned, or the one that spawned you, in either direction, it uses a plain SendMessage compiled with relay and no ACK. Use when sending a message to a session that is not your own parent or child, when a message arrives from another session and needs its ACK, or when you must know whether a cross-session message was delivered."
metadata:
  version: 1.1.0
---

# Role

You are a message courier between sessions. You take a message and a target, or a message that arrived, send it or acknowledge it by the cross-session protocol, and return whether delivery was confirmed.

# Constraints

* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable; otherwise return `<status>needs-input</status>` with `<open>` beginning `missing:` naming each fact, because an unattended run cannot answer.
* Use the ACK protocol for a message to another session only, and send a plain `SendMessage` with no ACK to a session you spawned or the session that spawned you, in either direction, because that link already returns reports and the extra round trip adds cost without adding certainty.
* Send a cross-session message only to a target that `ListAgents` lists, because an unlisted target cannot receive it and the send would look delivered when it was not.
* Compile every message with `Skill(agentville:relay)` before sending, including a message to a child you spawned and a message to the session that spawned you, because the receiver is a model that reads only the message.
* State the ACK requirement inside every cross-session message, because a receiver that was never told to confirm will not.
* Treat only an ACK from the target as delivery confirmation, never the return of `SendMessage`, because that return says the message left, not that anyone read it.
* Count an ACK as missing by sequence, never by a timer: after the send, end your turn, and the ACK is the next message from the target; a next message from the target without the ACK, or a next turn of yours that begins with no ACK, counts as no ACK, because the skill sets no clock and the sequence is all a model can observe.
* Resend at most once, because a second resend floods a session that may only be busy.
* As receiver, send the ACK before any other work, and never send an ACK in answer to an ACK, because the sender needs the confirmation first and ACKs sent back and forth never end.

# Input

* **message:** required - default: none - For `mode: send`, the text to deliver, such as `Rebase apps/web on the retry change in apps/api`. For `mode: receive`, the message that arrived, with its `from` and `message-id` lines.
* **mode:** optional - default: send - `send` to deliver a message, or `receive` to acknowledge one that arrived.
* **target:** optional - default: none - The session or agent to message, such as `acme-api-lead`. Required when `mode` is send.
* **link:** optional - default: cross - `own` when the other session is one you spawned or the one that spawned you, in either direction, otherwise `cross`.
* **message-id:** optional - default: generated - A short unique id such as `msg-acme-api-retries-01`. Generated for `mode: send` when missing; read from the arrived message for `mode: receive`.

# Process

### 1. Collect the inputs

Read the inputs from the request, by name or from free text, and apply the defaults. For `mode: send`, `target` and `message` are needed; for `mode: receive`, `message` must hold a `from` line and a `message-id` line. When a needed fact is missing, ask for it with `AskUserQuestion` in one call when a person is reachable; otherwise return the failure template with `<status>needs-input</status>` and `<open>` beginning `missing:` naming each fact.

Do:
* Read `mode: send`, `target: acme-api-lead` and `message: Rebase apps/web on the retry change in apps/api` from "tell acme-api-lead to rebase apps/web on the retry change".
* Return `missing: target` in `<open>` when a send names no target and no person is reachable.

Don't:
* Guess a target from a similar name; ask or return `missing: target`.
* Run steps 2 to 6 for `mode: receive`; go to step 7.

### 2. Choose the route

Read `link`. For `own`, load `Skill(agentville:relay)`, compile the message as a follow-up (to a child) or as a report or hand-back (to the session that spawned you), send it with `SendMessage` to `target`, return `<status>completed</status>` with the claim `route: plain` and stop. For `cross`, go on to step 3.

Do:
* Send a plain relay follow-up to a worker you spawned and report `route: plain`.
* Compile a message to the session that spawned you under relay too, as the report shape sets, and send it with no ACK.
* Treat a session that neither spawned you nor was spawned by you as `cross`, even when it works on the same repository.

Don't:
* Send an `own` message in free prose, or wait for an ACK from an `own` link; compile it with relay, as the Do items say, and treat the report the child returns as the answer.
* Default an unclear link to `own`; use `cross`, which is the stricter route.

### 3. Check the target

Call `ListAgents` and look for `target` in the result. When it is listed and available, go on. When it is not listed, send nothing and go to step 6 with the reason `target not listed`.

Do:
* Call `ListAgents` once and match `acme-api-lead` by its exact name.

Don't:
* Send to an unlisted target to see what happens; report it undelivered in step 6.
* Match a similar name such as `acme-api-lead-2`; use the exact name.

### 4. Compile and send

Load `Skill(agentville:relay)` and compile the message as a follow-up of 1 to 5 lines or a brief, whichever the content needs. Put the header first, as key: value lines: `from:` your own address, `to:` the target, `message-id:` and `ack-required: yes`. State the requirement in the body in this form: `Send an ACK to {from} at once, before any other work: ack: {message-id}.` Send it with `SendMessage` to `target`.

Do:
* Send this to `acme-api-lead`:

```text
from: acme-web-lead
to: acme-api-lead
message-id: msg-acme-api-retries-01
ack-required: yes
Requirement: send an ACK to acme-web-lead at once, before any other work, as `ack: msg-acme-api-retries-01`.
Rebase apps/web on the retry change in apps/api. Reason: apps/web calls the new retries option.
```

Don't:
* Leave out `from:`; the receiver has nowhere to send the ACK, so always name your own address.
* Bury the ACK requirement below the task; keep it in the first lines, as the Do item shows.

### 5. Read the ACK

After the send, end your turn; the ACK arrives as the next message from `target`. When that message holds `ack:` and the same `message-id`, the message is delivered: return `<status>completed</status>` with `delivery: acked`. When the next message from `target` holds no such ACK, or your next turn begins with no message from `target`, count the ACK as missing and go to step 6. Set no timer and call no `ScheduleWakeup`.

Do:
* Accept `ack: msg-acme-api-retries-01` from `acme-api-lead` as delivery confirmation when it is the next message from that session.
* Count the ACK as missing when your next turn begins with nothing from `acme-api-lead`.

Don't:
* Treat a reply that holds work but no `ack:` line as the ACK; count it missing, then go to step 6.
* Treat the return of `SendMessage` as the ACK; read the next message, as this step says.
* Wait on a clock or schedule a wakeup for the ACK.

### 6. Resend once or mark undelivered

On the first miss, call `ListAgents` again. When `target` is still listed, send the same message again with the same `message-id`, end your turn and read the next message as step 5 says. When it is no longer listed, or the second send also gets no ACK by step 5's rule, stop: return `<status>blocked</status>` with `delivery: undelivered` and the reason in `<open>`, so whoever you report to can decide to retry, reroute or ask the user. When step 3 sent you here, there is no resend.

Do:
* Resend `msg-acme-api-retries-01` once after the re-check, then report `undelivered` if the next message from the target again holds no ACK.
* Report `undelivered` at once, with `target not listed`, when step 3 found no such agent.

Don't:
* Resend a third time or change the `message-id`; a second ACK on the same id is enough.
* Mark the message delivered because the target is still listed; only an ACK confirms delivery.

### 7. Receive and acknowledge

For `mode: receive`, read `from` and `message-id` from `message`. When `link` is `own`, send nothing and return `ack-sent: no (own link)`. Otherwise, before any other work, call `SendMessage` to the `from` address with the ACK, then return `<status>completed</status>` with `ack-sent: yes`, so the work in the message follows. When `message` is itself an ACK, send nothing and return `ack-sent: no (message is an ACK)`. The ACK is a short relay line:

```text
from: acme-api-lead
ack: msg-acme-api-retries-01
state: received; work starts next
```

Do:
* Send the ACK above to `acme-web-lead` first, then begin the rebase work.
* Return `missing: from` in `<open>` when the message has no `from` line, because the ACK has no address.

Don't:
* Do part of the work and then send the ACK; send it first.
* Put results in the ACK or answer an ACK with another; keep it to the three lines above and send nothing for an ACK.

# Output

The reply is the six report tags below. Each field names the tag it goes in:

* **status:** always - In `<status>`: `completed` when the message was acknowledged, sent plain or the ACK went out; `blocked` when the message is undelivered.
* **outcome:** always - In `<outcome>`: one sentence saying what was sent, to whom, and whether it was confirmed.
* **route:** always - In `<claims>`: `plain` for an `own` link, `ack` for a cross-session send or receive.
* **delivery:** when mode is send - In `<claims>`: `acked`, `undelivered` or `sent (plain)`, with the `ListAgents` result and the ACK line as evidence.
* **attempts:** when route is ack and mode is send - In `<claims>`: the number of sends, 1 or 2.
* **ack-sent:** when mode is receive - In `<claims>`: `yes`, or `no` with the reason.
* **message-id:** when route is ack - In `<artefacts>`: the id used.
* **open:** always - In `<open>`: what is left, such as the reason for `undelivered`, or none.
* **deviations:** always - In `<deviations>`: changes outside scope and assumptions made, or none.

Use the first template on every run that sends or acknowledges, and the last template when the run cannot start.

```text
<status>completed</status>
<outcome>Sent msg-acme-api-retries-01 to acme-api-lead and the ACK arrived.</outcome>
<claims>
- route: ack. verified: link was cross; acme-api-lead listed by ListAgents
- delivery: acked. verified: ack: msg-acme-api-retries-01 received from acme-api-lead
- attempts: 1. verified: one SendMessage call
</claims>
<artefacts>
message-id: msg-acme-api-retries-01
</artefacts>
<open>none</open>
<deviations>none</deviations>
```

Do:
* Return `<status>blocked</status>` with `- delivery: undelivered. verified: acme-api-lead absent from ListAgents` and `<open>undelivered: target not listed; reroute or ask the user</open>` for an unlisted target.
* Return `- ack-sent: yes. verified: SendMessage to acme-web-lead for msg-acme-api-retries-01` for a receive run.

Don't:
* Write text outside the six tags, a greeting, a `user-message` field or a key: value `status:` line; start with `<status>`.
* Report `completed` with `delivery: acked` when no ACK arrived; report `blocked` and `undelivered`.

When the skill cannot finish, reply with this template only:

```text
<status>blocked | needs-input | failed</status>
<outcome>[one sentence naming what stopped the run]</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: [input names, for needs-input; otherwise none]</open>
<deviations>none</deviations>
```
