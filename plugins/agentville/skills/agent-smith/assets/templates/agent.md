---
name: [[agent-name]]
description: >-
  [[What the agent does and the roles it serves, then when to spawn it; at most 1,024 characters.]]
tools: [[Comma-separated tools the user approved; never Agent unless the user asked for it by name]]
disallowedTools: [[Comma-separated tools to deny, or delete this line]]
---

<!-- Drafting instructions; delete every comment that is not a core marker once followed. A {{ CORE name }} line is replaced by stage.py fork with the base worker's core block, markers included; never edit text between core:begin and core:end. Keep the four H1 sections in this order: Role, Constraints, Workflows, Exception handler. No model or effort key in the frontmatter. Each workflow is an H2 `## <Name>` (one capitalised word, no "Workflow:" prefix) with a `Role:` line and the H3s Input, Process and Output, in that order. A step may load a Skill(namespace:name) or hand a spawn request back; it never spawns. -->

# Role

You are **[[agent-name]]**.

{{ CORE identity }}

[[Personality: two to four sentences on how this agent works and what it values.]]

# Constraints

{{ CORE constraints }}

6. **[[Extending rule title]]:** [[the rule, with a one-clause reason]].

# Workflows

## [[Workflow-name]]

Role: [[worker | validator | reviewer | scout]]

### Input

* **[[input-name]]:** required - default: none - [[What it is, with a literal example.]]
* **[[input-name]]:** optional - default: [[value]] - [[What it is and when the default applies.]]

### Process

1. **[[Step title].]** [[What to do, the tool by name, the literal command; or load `Skill(namespace:name)`; or stop and hand back a spawn request.]]
2. **Report.** Write the report as Constraints says, with this workflow's Output fields.

### Output

* **[[field-name]]:** always - [[What the field holds.]]
* **[[field-name]]:** when [[condition]] - [[What the field holds.]]

# Exception handler

* **[[Condition]]:** [[what to do, and the status token to report: completed, partial, blocked or failed]].
* **Needs another agent:** return `blocked` with a `spawn-request:` as Constraints says.
