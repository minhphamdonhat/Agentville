# Validate rules

Read by SKILL.md step 6 after measure.py. Report each problem as `rule <n>: <problem>`, one entry per problem. Each rule says whether measure.py checks it (script) or you check it by reading (judged); trust a script result, and judge only the judged rules. Text inside a Don't example, or inside inline code in a sentence that names a forbidden form on purpose, is exempt from the judged rules. measure.py prints a `failures:` line of rule numbers and a `warnings:` line; a warning never blocks install. `{{ SKILL_ROOT }}/scripts/test_scripts.py` is the self-test for measure.py and stage.py; run it only when changing those scripts.

## All types

- Rule 3, fences (script). Every fenced block opens with a language tag such as `text`, `markdown`, `python` or `mermaid`.
- Rule 6, size (script). A file of more than 500 lines fails, counting every line including the frontmatter. This applies to SKILL.md and to each file in `references/workflows/`. Move long material to `references/<topic>.md` and link it relatively.
- Rule 11, placeholders and paths (script). No `[[` fill-in and no HTML comment remains, outside inline code. No host path (one under `/home/`, `/Users/`, `/tmp/` or a drive letter) appears outside a Do or Don't item. Every path starts with `{{ SKILL_ROOT }}`, `{{ USER_ROOT }}` or `{{ PROJECT_ROOT }}`, or is a runtime folder written `<STAGING>` or `<PATH>` (judged).
- Rule 12, description (script for length, judged for content). The description is non-empty and at most 1,024 characters. It says what the skill does, then names at least two trigger contexts.
- Rule 13, name (script). The name is kebab-case and at most 64 characters.
- Rule 14, self-contained (script). Every relative Markdown link and every `{{ SKILL_ROOT }}/...` path names a file that exists in the skill folder; measure.py lists the others on `unresolved_links:` and fails. A path holding a `<...>` or `[...]` slot is not checked. A mention of another skill by slash name is listed on `skill_mentions:` as a warning only; keep such mentions to skills the user agreed to call.
- Rule 15, frontmatter keys (script). The frontmatter holds `name` and `description` and no other key. A `version`, `type`, `template` or `allowed-tools` key fails, as does any block of nested keys. The type is read from the body, never from the frontmatter.
- Rule 20, independence (script, every type). A skill names only skills it loads itself. It never names, describes or assumes the skill, agent or thread that runs it, and it states every hand-back as its own output fields. measure.py fails rule 20 on any of the tokens below, case-insensitive, in SKILL.md and every text file of the skill, and on a description or Role that says a named skill calls, uses or runs it (such as "called by" or "that `Skill(` ... calls"). It prints each hit as `independence_hit: path:line | token`. A fix rewrites the reference as the skill's own input or output field. The skill must also pass the standalone-invocation eval of SKILL.md step 7.

```text
caller, calling agent, calling skill, invoker, invoked by, orchestrator, conductor,
parent agent, parent skill, root agent, main thread, another skill call,
another skill invokes, in a subagent, runs in a subagent, inside another agent, Siblings:
```

Exception, explicit and minimal: when the frontmatter name is `skill-smith`, measure.py skips three of this skill's own files, which quote the tokens on purpose: `references/validate-rules.md`, `scripts/measure.py` and `scripts/test_scripts.py`. No other skill and no other file is exempt; the allowlist is `INDEP_ALLOWLIST` in measure.py.

## Process skills

- Rule 1, sections (script). The body has exactly these H1 headings, in this order: `# Role`, `# Constraints`, `# Input`, `# Process`, `# Output`. No other H1 appears.
- Rule 2, legacy forms (script). No line starts with an old-format form: the entry label Start here, an at-sign call (at sign followed by Tool, Skill, Process, Return, ThrowError, MCP or Import), an XML workflow tag with a scope attribute, or a process, trigger or output tag. No H1 is Workflows, Dependencies, Exceptions or Rules. No bullet starts with a label such as `Action:`, `Tool:`, `Query:` or `Extract:`, bold or plain. Items under a `Don't:` list and text inside fences are exempt. measure.py lists what it found on `legacy:`.
- Rule 4, inputs (script). Every bullet under `# Input` reads `* **<name>:** required - default: none - <description>` or `* **<name>:** optional - default: <value> - <description>`, with a kebab-case name. There is at least one input. A required input has `default: none`. measure.py warns (rule 4) when an input name never appears in `# Process`.
- Rule 5, Do and Don't (script). A `### N.` step whose body is one non-blank line with no `Do:` or `Don't:` heading passes. Any other step holds a `Do:` list and a `Don't:` list, each with at least one `*` item and at least two items between them. The `# Output` section always holds both lists.
- Rule 7, output templates (script). `# Output` holds at least one fenced template. measure.py prints `output_field:` for each `KEY:` line inside a `text` template.
- Rule 8, steps (script). Steps are `### N. Title`, numbered from 1 with no gap, and `# Process` holds no other H3. Every "step N" or "steps N to M" in the body names a step that exists; a mention that starts with "SKILL.md step" points at this skill's own SKILL.md and is not checked.
- Rule 9, one workflow (judged). The Process is one sequence. A request that needs two is split into two skills.
- Rule 10, plain English (judged). Each step body says what to do in short sentences and names the tool inline with the literal query or command.
- Rule 16, failure template (script). `# Output` ends with a fenced template holding the line `status: partial | blocked | needs-input | failed` (a skill that never reports `partial` may drop the leading `partial | `; the other three stay in that order), a `reason:` line and a `missing:` line. Use `completed` in the success template, `partial` when only some of the output exists, `blocked` when an outside condition stops the run, `needs-input` when a required input or decision is missing, and `failed` when the work was tried and did not pass its checks. `missing:` lists input names, for `needs-input` only.
- Rule 17, asking (script for the pairing, judged for the rest). A skill asks the user when a person is reachable; otherwise it returns `status: needs-input` with `missing:` naming each fact. measure.py fails any step that names `AskUserQuestion` without also naming `needs-input`. A decision a person would be asked for, such as whether to revise after failing evals, is an optional input, so it can be supplied as input or reported by `needs-input`. Judge that no step asks in any other way, such as by ending its reply with a question.
- Rule 18, returned fields (script). `# Output` opens, before its first fence, with one bullet per returned field: `* **<field>:** always - <what it holds>` or `* **<field>:** when <condition> - <what it holds>`. measure.py prints one `returns:` line per field.
- Rule 19, reasons and pairs (judged). Every Constraint gives its reason in one clause, such as "because an unattended run cannot answer". Every Don't item has a Do item in the same list pair that shows the right form.
- Rule 21, scaled examples (judged). Applies to steps and Constraints alike. A simple one-line step or constraint carries no example. One whose rule needs explanation carries one Do and one Don't. Only the step breakdown, the execution (what may run, which tools are allowed and forbidden) and the Output carry more, up to three Do and three Don't each. Every example uses real values and every Don't names its fix.


## Workflow parts

A file under `references/workflows/` is part of the process skill that links it. It has no frontmatter. Its first line is `Used by SKILL.md step <N>.`, and it has exactly the H1s `# Input`, `# Process` and `# Output`, in that order; the skill's Constraints apply to it. measure.py checks it under rules 1 to 8, 11, 14 and 17 and prints one `part:` line per file; a part's failures also fail the skill.

## Steering and knowledge skills

- Rule 1, opening (script). The body has exactly one H1, equal to `name`. The first non-blank line after it starts with `Goal:`.
- Rule 2, sections (script). Every H2 but the last is `## <n>. <title>`, numbered from 1 with no gap. The last H2 is `## Pre-send check` with at least three numbered items, and each `(§N)` in it names an existing section. No H2 or H3 is titled Overview, Details, Misc, Introduction, Notes or Summary, with or without a number. No Role, Constraints, Input, Process or Output H1 appears.
- Rule 5, examples (script, knowledge only). Every numbered section holds `### Examples` with at least two bullets.
- Rule 10, register (judged). Headings use sentence case. A steering skill states rules to apply; a knowledge skill states facts only, with no steps.
