# Draft: agentville-agent-variants-2026-10-23

## Round 1 (2026-10-23)

### Notes
- Effort can be set in agent frontmatter: docs list `model` and `effort` (low|medium|high|xhigh|max) as subagent keys, supported for plugin agents (https://code.claude.com/docs/en/sub-agents, https://code.claude.com/docs/en/plugins/components).
- CLAUDE.md, both agent-smith SKILL.md copies and both measure.py copies (A2, FORBIDDEN_KEYS) forbid model/effort in agent frontmatter.
- `claude plugin validate . --strict` checks the marketplace only; also run `claude plugin validate plugins/agentville --strict`.
- The Agent tool's `effort` parameter is available in Claude Code, not in Claude chat (user, round 1).
- In a Claude Code cloud session followed from the Claude app, SendUserFile is present and the system prompt mentions the Claude app, so that signal alone misdetects chat.

### Decisions
- D1: Exempt variants by name: a file named <worker|validator|reviewer|scout>-<haiku|sonnet|opus>-<low|medium|high> may set model and effort; update CLAUDE.md, both agent-smith SKILL.md, both measure.py and their tests. Base agents still may not.
- D2: Generator at scripts/gen_agent_variants.py (repo root, not shipped), with a --check mode that fails on drift; regenerates every variant from scratch.
- D3: Surface check: Claude chat = SendUserFile present AND system prompt lacks the "You are Claude Code" identity line; Claude Code (local or cloud) = identity line present: SendUserFile forbidden, files delivered by path; when unsure, treat as Claude Code.
- D4: Run skill-smith evals for the dispatch and root-agent edits (user said yes; spends model usage).
- D5: First Execute step: git pull latest main into branch claude/practical-mccarthy-hbgryw (user's words: "Remember to git pull latest main before we do anything!").
- D6: README gets one paragraph on the variant naming pattern, not 36 rows; each variant description gains a sentence naming its model and effort.
- D7: No push, merge or tag without asking the user.

### Open points
- none

## Round 2 (2026-10-23)

### Notes
- Regression 3 (user, round 2): in Discuss, orchestrate found it needed a scout and, without asking, used it in Plan to reach the internet. This session repeated it: a scout researched the Claude Code docs in Discuss without a question-tool confirmation.
- User rule, quoted: "When agent feels the need for `scout` or user explicitly say to use Scout or reach out the internet. Agent must ask with AskQuestion tool for direct, explicit confirmation before proceeding."

### Decisions
- D8: Fix regression 3 in `orchestrate` only (user chose "orchestrate only"; dispatch unchanged): whenever orchestrate, or the user, wants a scout or any web access, orchestrate asks with the question tool for a direct, explicit yes before any scout dispatch, even when the user's request already names the web.
- D9: One confirmation covers the named research questions and sources for this topic only; anything new needs a new yes. From Execute on, where the question tool is forbidden, a scout need without a matching yes goes to Report as needs-input.
- D10: Bump orchestrate's metadata.version (minor) and include it in the skill-smith evals (D4).
- D11: User's words, round 2: "Once resolved all points. Commit & push. Create PR." Approves committing, pushing branch claude/practical-mccarthy-hbgryw and opening one PR for this change after the checks pass.

### Open points
- none
