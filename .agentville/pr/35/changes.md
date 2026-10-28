# Changes

This page lists the earlier rounds' change rows in full; the body keeps the current ones.

| Task | Files | Behaviour change | Evidence id |
| --- | --- | --- | --- |
| T1 Delete `build-lead` and `lookout`, remove references | `.claude/agents/build-lead.md`, `.claude/skills/lookout/`, `CLAUDE.md`, `.claude/skills/agent-smith/references/validate-rules.md`, `.claude/skills/agent-smith/SKILL.md` | Maintainer agent and skill gone; agent-smith 2.1.1 to 2.1.2 | V-CHK-1 |
| T2 Drop the plugin default, bump to 0.15.0 | `plugins/agentville/settings.json`, `plugins/agentville/.claude-plugin/plugin.json`, `README.md`, `website/docs/how-it-works.md`, `website/docs/technical/claude-code.md`, `website/docs/technical/index.md` | Breaking: installing no longer sets `pod-lead` as the main agent (version 0.15.0, not 1.0.0, as the owner chose); docs explain `claude --agent agentville:pod-lead` | V-CHK-1 |
| T5 Update steering and README | `CLAUDE.md`, `README.md` | `root-agent` import removed in the first round, then restored in round 2 without a playbook; README root-agent row reworded | V-CHK-1 |
| T6 Make `root-agent` playbook-neutral | `plugins/agentville/skills/root-agent/SKILL.md`, `CLAUDE.md`, `README.md`, `plugins/agentville/.claude-plugin/plugin.json` | Breaking: `root-agent` 3.0.0 no longer routes through `orchestrate`; plugin version 1.0.0 replaced by 0.15.0 | W-CHK-1 |
