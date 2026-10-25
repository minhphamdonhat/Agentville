---
sidebar_position: 10
title: FAQ
description: Answers to common questions about Agentville in Claude Chat and Cowork.
---

# Frequently asked questions

## Do I need to be technical?

No. You add the plugin once, paste two lines into your Instructions and then talk to Claude as usual. See [Get started](./get-started.md).

## Does it cost anything?

Agentville itself is free and open source under the MIT licence. Plugins need a paid Claude plan: Pro, Max, Team or Enterprise.

## Why do I have to paste two lines into my Instructions?

Chat and Cowork load the plugin's skills, but they do not switch on its way of working by themselves. The two lines tell Claude to use Agentville for every request. Copy them exactly from [Step 2](./get-started.md#step-2-turn-it-on-with-your-instructions).

## Why does every reply start with "Stage:"?

That line tells you which stage of the work Claude has just moved into, such as Discuss or Plan. [How it works](./how-it-works.md) explains each stage.

## Why did it ask me so many questions?

Large or unclear requests start with a short conversation so Claude builds the right thing. Questions only happen early on. Once the work starts, Claude asks nothing and lists any open choice in the final report.

## Why did it not ask me to approve the plan?

By design. Claude shows you a summary of the plan and carries on. If you want to change something, just say so in your next message.

## It answered a simple question without any stages. Is that right?

Yes. A question Claude can answer straight away goes straight to the answer.

## Will it search the web or send things without asking?

No. It asks before any web search and names what it wants to look up. It never publishes, sends, deletes or pays for anything unless you asked for that exact thing.

## Which version should I add?

Add the Stable plugin, `agentville`. The beta and dev versions are for testing, and you should only add one of the three at a time.

## How do I turn it off?

Go to **Customize**, then **Plugins**, and use **Disable plugin** or **Remove**. Also take the two lines out of your Instructions. See [Keep Agentville up to date](./guides/updating.md).

## I use Claude Code. Where are the steps for me?

See [For technical users](./technical/index.md).
