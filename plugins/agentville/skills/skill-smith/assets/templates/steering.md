---
name: [[skill-name]]
description: '[[The standard this skill sets, then at least two concrete contexts where it applies; at most 1,024 characters; single-quoted, so double every apostrophe.]]'
metadata:
  version: 1.0.0
---

# [[skill-name]]

Goal: [[one sentence: what the reader can do, or what the output must be, once this skill is applied]]. [[Name a supporting file here only when it ships in this skill's folder, as a relative link; otherwise delete this sentence.]]

<!-- Keep `metadata.version` at 1.0.0 for a new skill. Keep this shape: one H1 equal to the name, one Goal line, numbered H2 sections from 1 with no gaps, then the closing Pre-send check of at least three items, each ending with (§N). No Role, Constraints, Input, Process or Output sections and no frontmatter key besides name, description and metadata. Never name a section Overview, Details, Misc, Introduction, Notes or Summary. Pair every Wrong example with a Correct one. Name no file or skill outside this folder, and name nothing that runs this skill, because it must work when invoked alone. If this skill sets how an agent's reply or report is written, say that the reply is the six report tags <status>, <outcome>, <claims>, <artefacts>, <open>, <deviations> in that order, one level and no attributes, with no user-message field. Delete every comment. -->

## 1. [[First section title: the decision the reader makes first]]

[[One sentence that states the rule or the decision this section settles.]]

| [[Case]] | [[What to do]] | [[Why]] |
|---|---|---|
| [[case 1]] | [[action 1]] | [[reason 1]] |
| [[case 2]] | [[action 2]] | [[reason 2]] |

- [[Rule stated as an instruction, with its key term first.]]
- [[Second rule, in the same grammar.]]

## 2. [[Second section title]]

- [[Rule or constraint.]]
- [[Rule or constraint.]]

Correct: "[[a short example that follows the rules]]"

Wrong: "[[a short example that breaks them]]"

## Pre-send check

Run each item before sending or saving. The section holds the rule.

1. [[Check that restates section 1's rule as a yes-or-no test]] (§1).
2. [[Check for section 2]] (§2).
3. [[A cross-section check]] (§[[N]]).
