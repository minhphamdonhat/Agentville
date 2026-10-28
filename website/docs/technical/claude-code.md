---
title: Claude Code
description: Install Agentville in Claude Code and choose which agent runs it.
---

# Claude Code

## Install

In Claude Code, add the marketplace once, then install the Stable channel:

```text
/plugin marketplace add minhphamdonhat/Agentville
/plugin install agentville@minhphamdo
```

Pick a scope when asked, then run `/reload-plugins` if Claude Code prompts you to.

From a shell, the same steps are:

```bash
claude plugin marketplace add minhphamdonhat/Agentville
claude plugin install agentville@minhphamdo --scope project
```

In the desktop app's **Code** tab, click **+**, then **Add plugins**. Cloud sessions have no plugin browser.

If you added Agentville in Claude Chat or Cowork, it also syncs to Claude Code as `agentville@synced`.

## Three ways to run it

1. **Claude Code with `pod-lead` as the main agent.** `pod-lead` runs every request through `orchestrate` and follows `root-agent`. To run it for one session, start `claude --agent agentville:pod-lead`. To make it the main agent of every session, set the `agent` key in your own `~/.claude/settings.json` or the project's `.claude/settings.json`. The subagents docs show that key with a bare agent name, as in `{ "agent": "code-reviewer" }`, and the plugin docs give a plugin agent's full name as `<plugin>:<name>`; for this plugin's agent, `claude --agent agentville:pod-lead` is the documented form. The plugin itself ships no default settings, so installing it changes no main agent.
2. **Claude Code with another agent.** Start one session with `claude --agent <name>`, or name another agent in your own `agent` key in `~/.claude/settings.json`. To make that agent follow Agentville, add these lines to your project's `CLAUDE.md`:

   ```markdown
   - Load `Skill(agentville:root-agent)` and follow it in every reply.
   - Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it.
   ```

   To use your own playbook, fork `orchestrate` into a new skill and name it in the second line.
3. **Chat or Cowork.** See [Get started](../get-started.md).

## What loads where

| Part | Claude Code | Cowork | Chat |
| --- | --- | --- | --- |
| Skills | Yes | Yes | Yes |
| Agents | Yes | Yes | Ignored per the docs |
| Hooks | Yes | Yes | Ignored |

## Where its notes go

Agentville keeps each request's notes, plan, report and evidence under `.agentville/topics/` in the project folder, one folder per request. Its own `.gitignore` keeps evidence and the helpers' run folders out of commits.

## Updates

Auto-update is off by default for third-party marketplaces. Run `claude plugin marketplace update minhphamdo` to refresh the listings, then `claude plugin update agentville@minhphamdo` (or the channel you installed). A running session keeps the old version until you restart it or run `/reload-plugins`.

---

Last checked: 25 October 2026

Sources:

- [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins)
- [Create custom subagents](https://code.claude.com/docs/en/sub-agents)
- [Plugin components reference](https://code.claude.com/docs/en/plugins/components.md)
- [Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude)
- [Agentville README](https://github.com/minhphamdonhat/Agentville#readme)
