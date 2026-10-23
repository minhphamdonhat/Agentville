# Plan: agentville-agent-variants-2026-10-23

## Goal
Fix three Agentville regressions (no effort on spawn; no file delivery in Claude chat; scout used without explicit confirmation), add 36 model/effort agent variants, validate the plugin, then commit, push and open one PR.

## Tasks

### T0. Pull latest main into claude/practical-mccarthy-hbgryw
- done when: `git fetch origin main && git merge origin/main` succeeded with no conflict; `git status` shows no unmerged paths.
- progress: done - origin/main already at HEAD 3b990d7; merge "Already up to date."

### T1. Generator and variants: scripts/gen_agent_variants.py (repo root, not shipped) regenerates from scratch plugins/agentville/agents/<worker|validator|reviewer|scout>-<haiku|sonnet|opus>-<low|medium|high>.md, each a copy of its base changing only name, model, effort and description; --check mode fails on drift
- done when: `python3 scripts/gen_agent_variants.py --check` exits 0; exactly 36 variant files; the 4 base agent files are unchanged (`git diff --quiet HEAD -- plugins/agentville/agents/{worker,validator,reviewer,scout}.md`).
- progress: done - scripts/gen_agent_variants.py, 36 variants, --check exit 0 (Sonnet medium).
- progress: loop-back fix after review round 1 (needs-changes) - pod-lead.md lists all 36 variants in its Agent(...) tools (version 1.1.0); generator --check fails on a missing pod-lead entry or an extra base-prefixed file, builds before writing, clear errors; README root-agent row and shipped agent-smith SKILL.md wording fixed.

### T2. Steering exemption: CLAUDE.md, both agent-smith SKILL.md copies and both measure.py copies (plus tests) allow model and effort only in files named as variants; base agents still fail A2
- done when: the 4 test_scripts.py commands in CLAUDE.md exit 0; agent-smith measure.py exits 0 on all 36 variants.
- progress: done - A2 variant exemption in both measure.py, 6 new tests each, CLAUDE.md and both agent-smith SKILL.md 1.3.0; four test_scripts.py exit 0 (Sonnet medium).
- progress: loop-back fix after validation round 1 rejected (all 9 scout variants failed A5) - measure.py applies the base role's core exemptions to variants, both copies, new test; 40/40 pass.

### T3. dispatch: spawn rule for an Agent tool without an `effort` parameter (spawn agentville:<role>-<model>-<effort> after the clamp, never also pass a different model; fall back to base + model, effort in the brief's budget, `effort unenforced, variant missing` in spawn:); role table, fallback rules, Do/Don't and spawn: field updated; version bumped; built with the maintainer skill-smith including its evals
- done when: skill-smith measure.py exits 0 on dispatch/SKILL.md; a dry read resolves "Sonnet high, no effort parameter" to agentville:worker-sonnet-high.
- progress: done - dispatch 1.1.0; measure.py exit 0; evals new 10/10 vs old 4/10 (Sonnet), 8/10 vs 4/10 (Haiku; Haiku misses the xhigh clamp) (Sonnet high).

### T4. root-agent: surface check: Claude chat = SendUserFile present AND system prompt lacks the "You are Claude Code" identity line, so SendUserFile is allowed and required for any file the user should receive; Claude Code (local or cloud) = identity line present, so SendUserFile is forbidden and files go by path; unsure = treat as Claude Code. Version bumped; maintainer skill-smith with evals
- done when: skill-smith measure.py exits 0 on root-agent/SKILL.md.
- progress: done - root-agent 1.2.0 Surface section; measure.py exit 0; evals 8/8 vs 3/8 (Sonnet high).

### T5. orchestrate: whenever orchestrate or the user wants a scout or any web access, ask with the question tool for a direct, explicit yes before any scout dispatch, even when the request names the web; one yes covers the named questions and sources for this topic; from Execute on, a scout need without a matching yes goes to Report as needs-input. dispatch unchanged for this. Version bumped; maintainer skill-smith with evals
- done when: skill-smith measure.py exits 0 on orchestrate/SKILL.md.
- progress: done - orchestrate 1.2.0 scout gate; measure.py exit 0; evals 22/22 vs 18/22 (Sonnet high).

### T6. README paragraph on the variant naming pattern; plugin.json version 0.6.0 to 0.7.0
- done when: `claude plugin validate . --strict` and `claude plugin validate plugins/agentville --strict` exit 0; the full Verify block of CLAUDE.md passes with no critical or high scan finding.
- progress: done - README variant text, plugin.json 0.7.0; both validate --strict exit 0 (Haiku high).

### T7. Commit, push branch claude/practical-mccarthy-hbgryw and open one PR, on the user's words "Once resolved all points. Commit & push. Create PR."
- done when: push succeeded and the PR URL exists; runs only after Validate and Review pass.
- progress: done - commit 55df33a pushed, PR https://github.com/minhphamdonhat/Agentville/pull/14 opened.

### T9. orchestrate: stage line in the language of the user's latest message, with a loop-back ordinal from a stage's second entry (e.g. `- **Stage: Execute (2nd loop-back)**`); Plan compiles and updates its own task list (user request, after Plan)
- done when: skill-smith measure.py exits 0 on orchestrate/SKILL.md; evals new beat baseline.
- progress: done - measure.py exit 0; evals 14/14 vs 6/14 (Sonnet high).

## Approval
- status: not-required
- words: none
- recorded: 2026-10-23T06:11:43Z
