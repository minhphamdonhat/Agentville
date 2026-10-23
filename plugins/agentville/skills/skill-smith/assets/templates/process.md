---
name: "[[skill-name]]"
description: "[[What the skill does, then at least two concrete trigger contexts; at most 1,024 characters; inside the double quotes use single quotes only.]]"
metadata:
  version: 1.0.0
---

<!-- Drafting instructions; delete every comment once followed. Keep `metadata.version` at 1.0.0 for a new skill. Keep five H1 sections in this order and no others: Role, Constraints, Input, Process, Output (no Dependencies, Workflows, Exceptions or Rules). One workflow per skill. Write each step as plain sentences that name the tool inline with the literal query or command; never start a line with a label such as **Action:** or **Tool:**. Scale the examples to the item, in steps and Constraints alike: none on a simple one-line step or constraint; one Do and one Don't where the rule needs explanation; up to three of each on the step breakdown, the execution step and the Output; concrete, every Don't naming its fix and paired with a Do that shows the right form. Every Constraint gives its reason in one clause. A step may ask the user when a person is reachable; otherwise it returns status: needs-input with missing: naming each fact, so every step that names AskUserQuestion also names needs-input. Status values: completed when done; partial when only some of the output exists; blocked when an outside condition stops the run; needs-input when a required input or decision is missing; rejected when the work ran and a check it was asked to run did not pass; failed when the run itself broke. Long material goes to references/<topic>.md or references/workflows/<name>.md with a relative link. Every path starts with {{ SKILL_ROOT }}, {{ USER_ROOT }} or {{ PROJECT_ROOT }}. Name no file outside this skill's folder. Keep the file at 500 lines or fewer. -->

# Role

You are [[a role noun]]. You take [[the inputs in one phrase]], [[what you do in one phrase]], and return [[the output in one phrase]].

# Constraints

* [[A global hard rule]], because [[the one-clause reason]].
* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable; otherwise return `status: needs-input` with `missing:` naming each fact, because an unattended run cannot answer.

# Input

* **[[input-name]]:** required - default: none - [[What it is, with a literal example such as `...`.]]
* **[[input-name]]:** optional - default: [[value]] - [[What it is and when the default applies.]]

# Process

### 1. [[Collect the inputs]]

[[Read the required inputs from the request, by name or from free text. If one is missing, ask for it with `AskUserQuestion` in one call when a person is reachable; otherwise return the failure block with `status: needs-input` and `missing:` naming the absent inputs. Apply the defaults to every optional input you did not receive.]]

Do:
* [[A real request and the inputs it yields.]]
* [[A request missing an input, and the exact question asked or the `missing:` line returned.]]

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

The reply returns these fields:

* **[[field-name]]:** always - [[What the field holds.]]
* **[[field-name]]:** when [[condition]] - [[What the field holds.]]

[[One sentence: when to use which template.]]

```text
status: completed
[[field-name]]: [[value]]
[[field-name]]: [[value]]
```

Do:
* [[A filled example line.]]
* [[A filled edge-case line.]]

Don't:
* [[A line the template lacks; the Do items show the lines it has.]]
* [[A greeting, preamble or closing offer; the Do items start with the first field.]]

When the skill cannot finish, reply with this block only:

```text
status: partial | blocked | needs-input | rejected | failed
reason: [[one sentence naming what stopped the run]]
missing: [[input names, for needs-input; otherwise none]]
```
