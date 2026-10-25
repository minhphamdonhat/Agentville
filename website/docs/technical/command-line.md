---
title: Command-line installer
description: Install Agentville into Claude Code from a terminal with uvx or the install scripts.
---

# Command-line installer

The `agentville` command does the Claude Code install for you: it adds the marketplace, installs one channel and adds the two steering lines to `CLAUDE.md`. It needs [uv](https://docs.astral.sh/uv/) 0.13 or later and Python 3.15; uv downloads that Python when you do not have it.

## Run it with uvx

`uvx` runs the latest published `agentville` without keeping it installed:

```bash
uvx agentville install
uvx agentville install --scope project
uvx agentville install --channel beta
```

If your uv is older than 0.13, run `uv self update`. Failing that, add `--python 3.15` after `uvx`.

## Install the agentville command

The install script puts a persistent `agentville` command on your `PATH` with `uv tool install`, for your user only. When uv is missing, it downloads Astral's official uv installer, pinned to one uv version, to a temporary file and runs it; it asks first only when you run it at a terminal. It never uses `sudo` or administrator rights, and running it again upgrades the command.

On Linux and macOS:

```bash
curl --proto '=https' --tlsv1.2 -LsSf https://raw.githubusercontent.com/minhphamdonhat/agentville/main/install.sh | bash
```

On Windows, in PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/minhphamdonhat/agentville/main/install.ps1 | iex"
```

Then open a new terminal and run `agentville install`.

## Options

| Option | Values | Default |
| --- | --- | --- |
| `--scope` | `user` (your home folder) or `project` (the current folder, or `--project-dir PATH`) | `user` |
| `--channel` | `stable`, `beta` or `dev` | `stable` |
| `--target` | `claude-code` | `claude-code` |
| `--dry-run` | Prints the actions and changes nothing | Off |

The exit code is 0 on success, 1 when a step fails and 2 for a usage error. The [README](https://github.com/minhphamdonhat/agentville#readme) has the full details, including version pinning and environment variables.

---

Last checked: 25 October 2026

Sources:

- [Agentville README](https://github.com/minhphamdonhat/agentville#readme)
- [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins)
