---
sidebar_position: 2
title: Get started in Claude Chat and Cowork
description: Add Agentville to Claude Chat or Cowork, turn it on and make your first request.
---

# Get started in Claude Chat and Cowork

Getting started takes three steps and about five minutes: add the plugin, paste two lines into your Instructions, then ask for something.

:::note[Before you start]

Plugins need a paid Claude plan: Pro, Max, Team or Enterprise. On a Team or Enterprise plan, an Owner may limit which plugin sources you can add; if you cannot add Agentville, ask them.

:::

:::info[Chat and Cowork are becoming one]

Claude is merging Chat and Cowork into one experience. This is rolling out now, to Pro and Max first and to Team as a beta. If your message box still shows separate Chat and Cowork options, your menus may look a little different from the steps below.

:::

## Step 1: Add the plugin

1. In the left sidebar, click **Customize**. In Cowork, open the **Cowork** tab first.
2. Open the **Plugins** tab.
3. Click **Add**, then **Add marketplace**, then **Add from a repository**.
4. Enter `minhphamdonhat/agentville` and confirm.
5. Open the **Discover** tab, find the **Stable** plugin, which is called `agentville`, and click **Add**.

:::info[Screenshot coming soon: Customize → Plugins]
:::

:::info[Screenshot coming soon: Add → Add marketplace → Add from a repository]
:::

:::info[Screenshot coming soon: Discover → agentville → Add]
:::

:::tip[Pick Stable]

You may also see `agentville-beta` and `agentville-dev`. These are early versions for testing. Add only one of the three, because they clash with each other. Stable is the one to use.

:::

If you also use Claude Code, the plugin syncs there too, where it shows up as `agentville@synced`.

## Step 2: Turn it on with your Instructions

Chat and Cowork do not switch Agentville on by themselves. You switch it on by adding two lines to your **Instructions**, which Claude reads before every conversation. Chat and Cowork share the same Instructions, so you only do this once.

1. Click your initials in the lower left.
2. Choose **Settings**, then **Your Claude**, then **Instructions**.
   In the older layout, this is **Settings**, then **Account**, then **Instructions for Claude**.
3. Paste these two lines at the very top, above anything already there:

```markdown
- Load `Skill(agentville:root-agent)` and follow it in every reply.
- Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it.
```

4. Save.

Copy the lines exactly as they are, including the backticks and the hyphens at the start. Use the copy button in the corner of the box above to be sure.

:::info[Screenshot coming soon: Settings → Your Claude → Instructions]
:::

## Step 3: Make your first request

Start a new conversation and ask for something real. For example:

> Write a one-page welcome guide for new staff at Acme. Ask me anything you need to know first.

The first line of each reply shows where Claude is, in bold, such as **Stage: Discuss**. For a request like this one, Claude will ask you a few questions first, then write a short plan, then do the work and check it, and finish with a short report.

Not sure what to ask for? See [Write a good request](./guides/good-requests.md). To learn what each stage means, see [How it works](./how-it-works.md).

## Managing the plugin

You can manage Agentville from **Customize**, then **Plugins**:

- **Disable plugin** turns it off for now without removing it.
- **Remove** takes it away completely.
- **Check for updates** fetches the newest version now.
- **Sync automatically** keeps it up to date for you.

If you turn Agentville off, also remove the two lines from your Instructions. See [Keep Agentville up to date](./guides/updating.md) for more.

---

Last checked: 25 October 2026

Sources:

- [Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude)
- [Understanding Claude's personalisation features](https://support.claude.com/en/articles/10185728-understanding-claude-s-personalization-features)
- [Claude Cowork and Chat are one Claude](https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude)
