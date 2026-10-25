---
title: Claude Code
description: Install Agentville in Claude Code and choose which agent runs it.
---

# Claude Code

## Install

In Claude Code, add the marketplace once, then install the Stable channel:

```text
/plugin marketplace add minhphamdonhat/agentville
/plugin install agentville@minhphamdo
```

Pick a scope when asked, then run `/reload-plugins` if Claude Code prompts you to.

From a shell, the same steps are:

```bash
claude plugin marketplace add minhphamdonhat/agentville
claude plugin install agentville@minhphamdo --scope project
```

In the desktop app's **Code** tab, click **+**, then **Add plugins**. Cloud sessions have no plugin browser.

If you added Agentville in Claude Chat or Cowork, it also syncs to Claude Code as `agentville@synced`.

## Three ways to run it

1. **Claude Code with `pod-lead` as the main agent.** The plugin ships a `settings.json` with `{"agent": "pod-lead"}`, so an installed plugin makes `pod-lead` the main agent of every session. `pod-lead` runs every request through `orchestrate` and follows `root-agent`. To run it for one session only, start `claude --agent agentville:pod-lead`. Your own `agent` setting overrides the plugin's.
2. **Claude Code with another agent.** Start one session with `claude --agent <name>`, or name another agent in your own `agent` key in `~/.claude/settings.json`. To make that agent follow Agentville, add these lines to your project's `CLAUDE.md`:

   ```markdown
   - Load `Skill(agentville:root-agent)` and follow it in every reply.
   - Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it.
   ```

   To use your own workflow, fork `orchestrate` into a new skill and name it in the second line.
3. **Chat or Cowork.** See [Get started](../get-started.md).

## What loads where

| Part | Claude Code | Cowork | Chat |
| --- | --- | --- | --- |
| Skills | Yes | Yes | Yes |
| Agents | Yes | Yes | Ignored per the docs |
| `settings.json` (`agent`) | Yes | Ignored | Ignored |
| Hooks | Yes | Yes | Ignored |

## Updates

Auto-update is off by default for third-party marketplaces. Run `claude plugin marketplace update minhphamdo` to refresh the listings, then `claude plugin update agentville@minhphamdo` (or the channel you installed). A running session keeps the old version until you restart it or run `/reload-plugins`.

---

Last checked: 25 October 2026

Sources:

- [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins)
- [Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude)
- [Agentville README](https://github.com/minhphamdonhat/agentville#readme)
