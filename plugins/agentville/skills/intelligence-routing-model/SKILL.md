---
name: "intelligence-routing-model"
description: Framework to triage any task to the cheapest Claude tier (Haiku, Sonnet, Opus) and effort level that still succeeds. Score ceiling to pick tier, depth to pick effort, adjust for domain, gate Haiku on task shape and a deterministic check. Use whenever an Agent(...) call, worker spawn or fan-out is about to happen, when you must pick a model or effort, budget a run, or decide whether to escalate after a failure, even if nobody says "routing".
---

# intelligence-routing-model

Goal: before every Agent(...) call, pick the cheapest tier and effort cell that passes the task's check, and know which dial to move on failure.

Two dials, two questions.

- **Tier = ceiling.** Can model get this right at all?
- **Effort = autonomy.** How much verification, edge-case hunting and own judgement before handing back. Not an intelligence dial.

Never buy ceiling with effort: effort cuts missed edge cases, not wrong approach, and can worsen wrong-premise failures.

Tiers version-free: **Haiku**, **Sonnet**, **Opus**. Every tier takes effort `low`…`max`; defaults differ, so always set effort explicitly.

## 1. Pipeline

Never skip 1, 2 or 7.

1. **Sharpen spec.** One line: goal + deliverable + check. Underspecified? Interview user or write assumptions. Better spec beats bigger model.
2. **Name the check.** Command, test, schema, exit code. No check → Unverifiability scores 2, effort cannot rescue you, Haiku is out (§5); add external reviewer.
3. **Score** ceiling C and depth D (§2).
4. **Adjust** D for domain (§3); clamp adjusted D to 0–6.
5. **Map** to cell, apply guardrails (§4, §5).
6. **Spawn** with contract (§6).
7. **Grade, classify failure, move** (§7).

## 2. Score

Each dimension 0, 1 or 2; two independent sums.

**Ceiling C (0–10) — is task inside tier ability?**

| Dim | 0 | 1 | 2 |
|---|---|---|---|
| Ambiguity | fully specified | some judgement | goal vague, requirements inferred |
| Novelty | routine pattern | uncommon but documented | no precedent, rules discovered |
| Domain depth | general | professional | expert: proofs, security, architecture, finance modelling |
| Scope / coupling | one file or doc | few files or sources | cross-repo, cross-system, hidden dependencies |
| Consequence | reversible, read-only | branch or sandbox | production, money, data loss, user-facing |

**Depth D (0–6) — how much verification and search inside that ability?**

| Dim | 0 | 1 | 2 |
|---|---|---|---|
| Horizon | one step: one answer or one tool call | few steps, up to 30 min | long loop, >30 min, many tool calls |
| Edge cases | one obvious path | some known cases | many hidden cases, adversarial inputs, perf or security limits |
| Unverifiability | cheap objective check | partial check | no oracle, correctness rests on reasoning |

## 3. Domain adjustment on D

Effort pays unevenly across task families.

| Effort payoff | Families | Adjust |
|---|---|---|
| High | security, hardware, numerical/ML, scientific analysis | D +1 |
| Moderate | general software, debugging | D unchanged |
| Low | ops runbooks, media and layout; inferred, not measured: filings, compliance steps, extraction, classification, formatting, translation | D −1, cap effort at `medium` |

Haiku payoff is unmeasured (table is from the top tier). Haiku exception: strict template or schema output runs at `high`, since below it Haiku follows strict instructions less reliably.

Low-payoff family failing at capped effort is a **ceiling or task problem**: raise tier, decompose, or hand to a human.

## 4. Map

| C | Tier |
|---|---|
| 0–2 | Haiku if the Haiku gate passes (§5.5), else Sonnet |
| 3–5 | Sonnet; Haiku `high` for a contained edit at C≤4 (§5.6) |
| 6–10 | Opus |

| D (adjusted) | Sonnet / Opus effort | Haiku effort |
|---|---|---|
| 0 | `low` | `low` if one step, else `medium` |
| 1 | `low` | `medium` |
| 2–3 | `medium` | `high` |
| 4–5 | `high` | not eligible |
| 6 | decompose first (§5.7); otherwise `high`, `xhigh` only when horizon >30 min, `max` retry-only | not eligible |

Haiku `low` skips searches and checks: one-step work only. Haiku `xhigh`/`max` are never mapped: they cost near Sonnet `medium`/`high` without its ceiling; use only if your evals beat Sonnet.

## 5. Guardrails

Apply in order. Each overrides §4.

1. **Ceiling overrides.** Any single 2 in Novelty, Domain depth or Consequence → minimum Sonnet. Any two of those three at 2 → Opus.
2. **Sonnet ceiling cap.** Sonnet `max` → **Opus `high`**, or Opus `xhigh` where horizon justifies it: Opus matches or beats it at about half the cost or less. Sonnet `xhigh` is a cost trade-off, scoring below Opus `high`: default to **Opus `high`**, keep it only under a budget floor with a deterministic check. Sonnet `high` often beats Opus `low`.
3. **Opus `xhigh` is marginal.** Little over `high` at far more cost. Only for long-horizon runs (>30 min unattended).
4. **`max` is retry-only.** More thinking is not monotonic. Only after a documented `high` failure on a fully autonomous hard problem.
5. **Haiku gate.** Haiku only when every condition holds; one miss → Sonnet.
   - Deterministic check exists (tests, build, schema, exact match, count), not a judgement.
   - No C dimension at 2; Horizon ≤ 1. No long-horizon or iterative autonomous runs.
   - Not terminal-driven shell work, where Haiku trails far.
   - No computer or browser use on untrusted content: most open to prompt injection.
   - No factual claims beyond given inputs: hallucinates more.
   - No sensitive content or security work: over-refuses, handles them worst.
   - Never shown expected outputs or answer keys, never grades its own work: it can silently use leaked answers.
   - Tools and credentials scoped to the task; no production access: it has acted outside its sandbox.
   - Brief well under the long-prompt price threshold; no pasted codebases or document dumps.
6. **Haiku stretch for contained edits.** A single-purpose edit or extraction in a few files, gate otherwise passed, can take Haiku `high` in place of Sonnet `low`/`medium` up to C 4, matching it at a fraction of the cost. Provisional: one benchmark family.
7. **Decompose gate.** C ≥ 6 and D ≥ 5 → do not spawn one worker. Split, re-score each part; parts usually drop two tiers. Merge the parts' results into one answer. Only exception: an unattended end-to-end run that is one dependent chain whose steps cannot be checked separately → one Opus worker at `high` (`xhigh` if >30 min), human gate before anything irreversible.
8. **Prefer newer generation over higher effort.** Current model at `low` often beats prior generation at `xhigh`, cheaper.
9. **Keep planning in one place.** Decomposition, arbitration and merge stay with the planning step; plan errors cascade.
10. **Fan out rather than deepen when parallel.** Breadth-first → many cheap workers, results merged once; Haiku still needs rule 5.
11. **Effort costs wall-clock superlinearly.** Top effort can run tens of times longer than `low`. Latency-bound → cap at `medium`, narrow scope.
12. **Human gate.** Irreversible or production actions need human approval first, on every tier; they never run on Haiku.

## 6. Worker contract

Spawn with all five. Low-effort cells need it most: they scope literally and skip unrequested checks.

- **Scope:** exactly what to do, what not to touch.
- **Inputs:** paths, IDs, prior findings. Never "go find context".
- **Check:** command or criterion that proves done.
- **Budget:** step, tool-call and spawn ceiling, plus stop condition.
- **Output shape:** what to return, plus length cap; low effort does not reliably shorten prose.

Do not add "verify your work again" to high-effort workers; high effort already verifies, so it is likely redundant spend.

**Report format.** Every child report, Haiku included, opens `status: <token>` (completed, partial, blocked or failed) and quotes its evidence. A missing or unknown token, or `completed` over an empty, truncated or contradictory tool result or a failed check, counts as failed: small models fabricate there.

**Haiku additions.** Keep thinking on when a Haiku worker must call tools and return structured output.

**Verifier and audit.** Verify in a fresh context; for judgement checks the verifier sits at or above the worker's tier, and a different tier applies only where a peer-or-higher one exists, so Opus work is verified by Opus in a fresh context. A Haiku verifier runs ground-truth checks only (tests, build, schema, diff against spec), never judges a higher tier's work. Verifiers check independently, not rate rationale. Each run, re-check a random sample of accepted Haiku output on a higher tier.

## 7. Failure classification

Failure type names the dial: **did worker lack knowledge, or lack effort?**

| Symptom | Cause | Move |
|---|---|---|
| Tool timeout, flake, rate limit | environment | retry same cell, once |
| Safety refusal on benign work | environment | same effort, next tier up |
| Skipped a file, never ran tests, bailed partway, missed edge cases it understood | effort | +1 effort, same tier |
| Had full context, clearly tried, still wrong; wrong approach; misread domain | ceiling | +1 tier, restart at that tier's `medium` |
| Went in circles, over-engineered, broke working code, drifted to wrong premise | overthinking | −1 effort, or decompose |
| Second failure at Opus `high` with full context | task or plan | stop, re-plan or return to user, unless horizon >30 min (§5.3) or §5.4 applies |

**Wrong approach does not respond to effort.** Self-review rarely rejects its own premise; use a fresh-context reviewer.

**Haiku escalates on structure, not confidence.** A structural trigger beats an effort raise: failed check, missing status, empty or contradictory tool result, or budget overrun → leave Haiku (`low`/`medium` → Sonnet `medium`, `high` → Sonnet `high`). Only a pure effort failure whose structure passed stays on Haiku at +1 effort. This rule overrides the table's "restart at next tier's `medium`". Flagged ambiguity → back to step 1. Never gate on Haiku's self-reported confidence. Provisional: no Haiku cascade study exists.

**Escalation ladder** (effort and ceiling failures): Haiku `low` (one-step starts only) → Haiku `medium` → Haiku `high` → Sonnet `high` → Opus `medium` → Opus `high` → Opus `xhigh` only if horizon >30 min → Opus `max` only per §5.4. Otherwise stop at Opus `high` per the last failure-table row.

Skipped cells (Sonnet `low`/`medium`, Opus `low`) can score under the rung below; they stay valid *starting* cells, and a Sonnet start climbs `low` → `medium` → `high`.

**De-escalate:** five first-try passes in a family → try one rung down. Never tune Haiku prompts on rejected cases alone; re-test on fresh ones.

**Cheap-first arithmetic:** start cheap only when cost(cheap) + cost(check) + P(fail) × cost(next) < cost(next). Haiku is a small fraction of Sonnet's cost, but Haiku-first pays only when escalation is rare and the check catches failures. Start high where failures will be frequent: ambiguous, reasoning-heavy, novel. Start one tier higher when an undetected error costs more than the next tier's run. One cheap retry at most. Provisional for Haiku.

## 8. Split effort by phase

Generation and verification want different levels.

| Phase | Effort | Why |
|---|---|---|
| Interview and spec | `low` | fast turns, user in loop |
| Draft or implement | `low`–`medium` (Haiku `medium`) | quick reviewable base |
| Review and iterate | `low` | you are the check |
| Verify, test, harden | `high`, fresh context, peer-or-higher | edge-case hunting is what effort buys |
| Unattended end-to-end run | `high`–`xhigh`, never Haiku | model must self-verify |

**Effort tracks how absent you are.**

## 9. Tier versus effort, settled

- Extra compute pays only where tier sometimes solves the task and a cheap verifier exists.
- Ability sets the error floor: weaker tier at high effort stays wrong on judgement work.
- Top tier `high` or `xhigh` matches or beats mid tier `max` at about half the cost or less, and beats mid tier `xhigh` on score.

**Low tier at `medium`/`high` wins when** §5.5 passes.

**Mid tier at high effort wins when:** budget or latency rules out the top tier; narrow verifiable task; terminal-driven work with a clear goal, where it nears parity.

**Top tier at low effort wins when:** ambiguity, novelty, expert domain, heavy coupling, weak verification, high consequence: whenever C does the work, not D.

## 10. Worked cells

| Task | C | D (adj) | Cell |
|---|---|---|---|
| Rename symbol across 3 files, build must pass | 1 | 1 | Haiku `medium` |
| Extract 500 invoices to a JSON schema | 1 | 1 (−1 extraction) | Fan out Haiku `high` (strict-schema exception, §3), Sonnet sample audit |
| Cluster 40 tickets into themes | 2 | 1 (−1 classification) | Sonnet `low`: no deterministic check, external reviewer |
| Add pagination to one endpoint with tests | 4 | 2 | Haiku `high` (stretch, provisional); Sonnet `high` on failure |
| Shell setup until health check passes | 3 | 3 | Sonnet `medium`: terminal-driven |
| Write HTML sanitiser stripping every script-injection route | 5 (Domain 2) | 6 (+1 security) | Sonnet `high`, then verify pass at Opus `high` |
| Multi-file refactor in live service | 6 | 3 | Opus `medium`, human gate on deploy |
| Crash-loop in staging, no repro | 7 | 5 | Decompose: repro harness, diagnosis, fix; parts at Opus `medium`/`high` (parts stay coupled) |
| Fix storage-engine bug from crash report without breaking compaction | 6 | 6 | Decompose: failing repro test, fix, compaction regression check; parts at Opus `medium`/`high` (parts stay coupled) |
| Month-end regulatory filing end to end | 5 (Domain 2, Consequence 2) | 2 (−1 rulebook) | Opus `medium` via §5.1, human review |
| Migrate service to new datastore end to end | 8 | 6 | Decompose; parts at Opus `medium`/`high` (parts stay coupled); human gate before cutover |
| Multi-hop research, 20 sources | 4 | 5 | Sonnet `high`, or fan out per §5.10 with each part's D re-scored; results merged once; untrusted web rules out Haiku |
| Unattended overnight build-and-verify of an app | 7 | 6 | §5.7 exception (one dependent chain): Opus `xhigh`, human gate before deploy |

## 11. Upkeep

Tiers stay version-free, but **effort levels are not portable across versions**: same label, different thinking, moving defaults. Each release, re-sweep effort on your evals and re-check §5.2, §5.3, §5.5, §5.6, the Haiku `xhigh`/`max` rule and §3.

Evidence, benchmark numbers and sources: `RESEARCH-intelligence-routing-model.md`.

## Pre-send check

Run before each Agent(...) call.

1. Spec names a check; cell comes from C and adjusted D (§1–§3).
2. Haiku cell passes the whole gate; no Sonnet `max`, default Sonnet `xhigh` or unevaluated Haiku `xhigh`/`max`; human gate on irreversible steps (§4, §5).
3. Brief has five contract fields, every brief demands `status: <token>` with evidence, verifier is fresh and peer-or-higher (§6).
4. Failure move matches failure class; Haiku left on structure, not confidence (§7).
5. Request fits the tier: Haiku rejects non-default sampling parameters, prefill and the old computer tool, so no shared request template across tiers; forced `tool_choice` yields no thinking; with thinking disabled, a per-message effort change returns 400; confirm the model the worker actually ran on (§5, §6).
