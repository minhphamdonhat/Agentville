---
name: "[[skill-name]]"
description: "[[What the skill does, then at least two concrete trigger contexts; at most 1,024 characters; inside the double quotes use single quotes only.]]"
---

<!-- Drafting instructions; delete every comment once followed. Keep five H1 sections in this order and no others: Role, Constraints, Input, Process, Output (no Dependencies, Workflows, Exceptions or Rules). One workflow per skill. Write each step as plain sentences that name the tool inline with the literal query or command; never start a line with a label such as **Action:** or **Tool:**. Every step and the Output carry a Do: list and a Don't: list with at least two concrete examples between them, and every Don't item has a Do item that shows the right form. Every Constraint gives its reason in one clause. A step may ask the user when a person is reachable; otherwise it returns status: needs-input with missing: naming each fact, so every step that names AskUserQuestion also names needs-input. Status values: ok when done; blocked when an outside condition stops the run; needs-input when a required input or decision is missing; failed when the work was tried and did not pass its checks. Long material goes to references/<topic>.md or references/workflows/<name>.md with a relative link. Every path starts with {{ SKILL_ROOT }}, {{ USER_ROOT }} or {{ PROJECT_ROOT }}. Name no file outside this skill's folder. Keep the file at 500 lines or fewer. -->

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
status: ok
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
status: ok | blocked | needs-input | failed
reason: [[one sentence naming what stopped the run]]
missing: [[input names, for needs-input; otherwise none]]
```
