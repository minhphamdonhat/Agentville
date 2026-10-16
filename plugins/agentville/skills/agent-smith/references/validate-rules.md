# Validate rules

Read by SKILL.md step 7 after measure.py. Report each problem as `rule <id>: <problem>`, one entry per problem. Each rule says whether measure.py checks it (script) or you check it by reading (judged); trust a script result, and judge only the judged rules. measure.py prints a `failures:` line of rule ids and a `warnings:` line; a warning never blocks install. `{{ SKILL_ROOT }}/scripts/test_scripts.py` is the self-test for measure.py, stage.py and eval.py; run it only when changing those scripts.

## Frontmatter

- Rule A1, required keys (script). `name` is kebab-case and at most 64 characters, `description` is non-empty and at most 1,024 characters, and `tools` lists at least one tool.
- Rule A2, no model or effort (script). A `model` or `effort` key fails, because the model and effort are chosen per spawn, not per agent. A key other than `name`, `description`, `tools` and `disallowedTools` is a warning.
- Rule A3, no spawning (script). `Agent` (or its older name `Task`) in `tools` fails unless measure.py runs with `--allow-agent`, which is passed only when the user asked for the tool by name.
- Rule A10, no contradiction (script). A tool listed in both `tools` and `disallowedTools` fails.
- Rule A12, tools match the steps (judged). Every tool a workflow step names is in `tools`, and `tools` holds no tool that no step or core rule needs.

## Body

- Rule A4, sections (script). The body has exactly these H1 headings, in this order: `# Role`, `# Constraints`, `# Workflows`, `# Exception handler`.
- Rule A5, core kept verbatim (script). The core blocks `identity` and `constraints`, each between `<!-- core:begin NAME -->` and `<!-- core:end NAME -->`, are present, sit in their home section (Role, Constraints) and are byte-identical to the same blocks in `{{ SKILL_ROOT }}/assets/base/worker.md`. The constraints core is the first thing in Constraints; extending rules follow it.
- Rule A16, report format (script). The `constraints` core says that every report opens with `status: TOKEN` with a relay token and that every report, `blocked` and `failed` included, carries every output field of the workflow in use, with `none` when empty; measure.py prints `status_line_rule: yes` or fails A16. It guards the base worker's own core, which A5 compares every fork against.
- Rule A6, workflows (script). `# Workflows` holds at least one `## <Name>` (one capitalised word, hyphens allowed), names unique. Each has a `Role:` line naming `worker`, `validator`, `reviewer` or `scout`, then the H3s `### Input`, `### Process` and `### Output` in that order. Input bullets read `* **<name>:** required - default: none - <description>` or `* **<name>:** optional - default: <value> - <description>`. Process holds numbered steps `1.` to `n.` with no gap. Output bullets read `* **<field>:** always - <what>` or `* **<field>:** when <condition> - <what>`.
- Rule A7, exception handler (script). `# Exception handler` holds at least one bullet.
- Rule A8, no leftovers (script). No `[[` fill-in, no `{{ CORE ... }}` line and no HTML comment remains, except the core markers.
- Rule A9, namespace (script). Every skill reference uses the in-house namespace, such as `Skill(agentville:relay)`; any reference to the old namespace fails, and measure.py lists the lines on `foreign_namespace_lines:`. A `Skill(...)` with no namespace is a warning.
- Rule A11, size (script). A file of more than 500 lines fails.
- Rule A13, role scope (judged). No workflow step breaks its role's scope: a reviewer step edits nothing and runs no tests, builds or scripts (read-only `git diff`, `git log`, `git show` and `rg` are allowed), a validator step edits no product code, and a scout step that needs the web returns `blocked` when the agent holds no web tool.
- Rule A14, hand-backs (judged). A step that needs another agent stops and hands back a `spawn-request:` naming the agent type, the role and the brief; no step spawns.
- Rule A15, relay tokens (judged). Every status the agent reports, in the Exception handler and the workflows, is one of relay's tokens: `completed`, `partial`, `blocked` or `failed`.
