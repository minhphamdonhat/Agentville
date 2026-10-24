---
name: "[[skill-name]]"
description: "[[What the skill does, then at least two concrete trigger contexts; at most 1,024 characters; inside the double quotes use single quotes only.]]"
metadata:
  version: 1.0.0
---

<!-- Drafting instructions; delete every comment once followed. Keep `metadata.version` at 1.0.0 for a new skill. Keep five H1 sections in this order and no others: Role, Constraints, Input, Process, Output (no Dependencies, Workflows, Exceptions or Rules). One workflow per skill. Write each step as plain sentences that name the tool inline with the literal query or command; never start a line with a label such as **Action:** or **Tool:**. Scale the examples to the item, in steps and Constraints alike: none on a simple one-line step or constraint; one Do and one Don't where the rule needs explanation; up to three of each on the step breakdown, the execution step and the Output; concrete, every Don't naming its fix and paired with a Do that shows the right form. Every Constraint gives its reason in one clause. A step may ask the user when a person is reachable; otherwise it returns <status>needs-input</status> with <open> beginning missing: naming each fact, so every step that names AskUserQuestion also names needs-input. Output: the first fence shows the six report tags <status>, <outcome>, <claims>, <artefacts>, <open>, <deviations> in that order, one level, no attributes, plain lines inside, none in an empty tag; paths and locations go in <artefacts> as key: value lines, checkable facts go in <claims> as '- key: value. label: evidence' with the labels verified, inferred, unverified, assumed; a nested list is one minified JSON line in <claims>; an inline document body goes in <artefacts> as content: then its lines; name the tag in every field bullet; never add a user-message field or a key: value status line; the last fence is the failure template in the same six tags. Status values: completed when done; partial when only some of the output exists; blocked when an outside condition stops the run; needs-input when a required input or decision is missing; rejected when the work ran and a check it was asked to run did not pass; failed when the run itself broke. Long material goes to references/<topic>.md or references/workflows/<name>.md with a relative link. Every path starts with {{ SKILL_ROOT }}, {{ USER_ROOT }} or {{ PROJECT_ROOT }}. Name no file outside this skill's folder. Keep the file at 500 lines or fewer. -->

# Role

You are [[a role noun]]. You take [[the inputs in one phrase]], [[what you do in one phrase]], and return [[the output in one phrase]].

# Constraints

* [[A global hard rule]], because [[the one-clause reason]].
* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable; otherwise return `<status>needs-input</status>` with `<open>` beginning `missing:` naming each fact, because an unattended run cannot answer.

# Input

* **[[input-name]]:** required - default: none - [[What it is, with a literal example such as `...`.]]
* **[[input-name]]:** optional - default: [[value]] - [[What it is and when the default applies.]]

# Process

### 1. [[Collect the inputs]]

[[Read the required inputs from the request, by name or from free text. If one is missing, ask for it with `AskUserQuestion` in one call when a person is reachable; otherwise return the failure template with `<status>needs-input</status>` and `<open>` beginning `missing:` naming the absent inputs. Apply the defaults to every optional input you did not receive.]]

Do:
* [[A real request and the inputs it yields.]]
* [[A request missing an input, and the exact question asked or the `<open>` text beginning `missing:` returned.]]

Don't:
* [[Guessing a required input.]]
* [[Inferring an optional input from a weak cue.]]

### 2. [[Step name]]

[[Short plain-English sentences: what to do, the tool by name, the literal query or command inline.]]

Do:
* [[Concrete example with real values.]]

Don't:
* [[Concrete counter-example; the Do item above shows its right form.]]

# Output

The reply is the six report tags below. Each field names the tag it goes in:

* **status:** always - In `<status>`: [[`completed` when the work is done.]]
* **outcome:** always - In `<outcome>`: [[One or two sentences saying what was done.]]
* **[[field-name]]:** always - In `<claims>`: [[A checkable fact; the claim carries a label and its evidence.]]
* **[[field-name]]:** when [[condition]] - In `<artefacts>`: [[A path or location.]]
* **open:** always - In `<open>`: [[What is left, or none.]]
* **deviations:** always - In `<deviations>`: [[Changes outside scope and assumptions made, or none.]]

[[One sentence: when to use which template.]]

```text
<status>completed</status>
<outcome>[[One or two sentences saying what was done.]]</outcome>
<claims>
- [[field-name]]: [[value]]. [[verified | inferred | unverified | assumed]]: [[evidence]]
</claims>
<artefacts>
[[field-name]]: [[path or location]]
</artefacts>
<open>[[What is left, or none.]]</open>
<deviations>[[Changes outside scope and assumptions made, or none.]]</deviations>
```

Do:
* [[A filled example: one `<claims>` line with its label and evidence, and one `<artefacts>` line.]]
* [[A filled edge-case example, such as `none` in an empty tag.]]

Don't:
* [[A line outside the six tags, a greeting, a `user-message` field or a key: value `status:` line; the Do items start with `<status>`.]]
* [[A nested tag or an attribute; the tags stay flat, as the Do items show.]]

When the skill cannot finish, reply with this template only:

```text
<status>blocked | needs-input | failed</status>
<outcome>[[one sentence naming what stopped the run]]</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: [[input names, for needs-input; otherwise none]]</open>
<deviations>none</deviations>
```
