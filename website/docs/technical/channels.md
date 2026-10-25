---
title: Channels
description: The Stable, Beta and Development channels and how to switch between them.
---

# Channels

Agentville ships on three channels. Work moves one way only, from Development to Beta to Stable.

| Channel | Install id | Branch |
| --- | --- | --- |
| Stable (release) | `agentville@minhphamdo` | `release` |
| Beta | `agentville-beta@minhphamdo` | `beta` |
| Development | `agentville-dev@minhphamdo` | `main` |

Install one channel at a time: all three load the same names under `agentville:`, so two would clash. To switch in Claude Code, uninstall the one you have and install the other:

```text
/plugin uninstall agentville@minhphamdo
/plugin install agentville-beta@minhphamdo
```

In Chat and Cowork, remove the plugin in **Customize**, then **Plugins**, and add the other one from the **Discover** tab.
