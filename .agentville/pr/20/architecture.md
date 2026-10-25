# Architecture changes

This page shows the Townhall package, the path from the plugin's `.mcp.json` to the running server, and how Townhall sits beside `main`'s installer and the workspace.

## Package layout

The package lives in `townhall/` with its own `pyproject.toml` and `uv.lock`. Its import package is `agentville`, so the code sits under `townhall/src/agentville/`. The `rag` and `memory` folders hold placeholder modules for later parts.

```mermaid
flowchart TD
  accTitle: Townhall package layout
  accDescr: The agentville console script in cli/main.py feeds the Townhall CLI and the FastMCP root, which mounts 11 townhall_* tools. The CLI, the MCP tools and the Textual viewer all use storage.py, which uses the page linter and the Temporal engine. The core folder supplies config, paths, errors and the Temporal client to storage and the engine.
  cli["cli/main.py: agentville console script"] --> th_cli["townhall/cli.py"]
  cli --> mcp["mcp/server.py: FastMCP root"]
  mcp --> th_mcp["townhall/mcp.py: 11 townhall_* tools"]
  th_cli --> storage["townhall/storage.py: ticket packs, locks, atomic writes"]
  th_mcp --> storage
  viewer["townhall/viewer.py: Textual viewer"] --> storage
  storage --> lint["townhall/markdown_ast.py: page linter"]
  storage --> engine["townhall/engine/: Temporal client, worker, workflow, poller"]
  core["core/: config, paths, errors, temporal"] --> storage
  core --> engine
```

In words: the `agentville` console script in `cli/main.py` feeds the Townhall CLI and the FastMCP root, which mounts 11 `townhall_*` tools. The CLI, the MCP tools and the Textual viewer all go through `storage.py`, which uses the page linter and the Temporal engine. The `core/` folder supplies config, paths, errors and the Temporal client to storage and the engine.

## MCP server launch path

Claude Code reads `plugins/agentville/.mcp.json` when the plugin loads. The server key is `agentville`, so the tools appear as `mcp__plugin_agentville_agentville__townhall_*`.

```mermaid
sequenceDiagram
  accTitle: MCP server launch sequence
  accDescr: Claude Code calls uvx with Python 3.15 and the git source pinned at 652451a with subdirectory agentville. uvx fetches that commit from GitHub, builds the environment and starts agentville engine mcp, which serves its tools to Claude Code over stdio and reads and writes the Townhall files in the project.
  participant CC as Claude Code
  participant UVX as uvx
  participant GH as GitHub at 652451a
  participant S as agentville engine mcp
  CC->>UVX: --python 3.15 --from git+...@652451a#subdirectory=agentville
  UVX->>GH: fetch the pinned commit
  GH-->>UVX: agentville/ at 652451a (Townhall, before the move)
  UVX->>S: build the environment and start the server
  S-->>CC: stdio MCP tools
  Note over S: reads and writes .agentville/config.toml and .agentville/townhall/
```

In words: Claude Code calls `uvx` with Python 3.15 and the git source pinned at `652451a`. `uvx` fetches that commit, builds the environment and starts `agentville engine mcp`, which serves its tools over stdio and reads and writes `.agentville/config.toml` and `.agentville/townhall/`.

The pin uses `subdirectory=agentville` because `652451a` predates the move to `townhall/`. At that commit `agentville/` holds Townhall, not the installer. The next pin change switches the subdirectory to `townhall` in the same edit.

## Beside the installer and the workspace

Three parts share the repository and the project folder, and none reads another's files.

```mermaid
flowchart LR
  accTitle: Townhall beside the installer and the workspace
  accDescr: In the repository, the installer CLI installs the plugin, and the plugin's .mcp.json launches the Townhall package. In a user's project, Townhall writes config.toml, .gitignore and townhall/ under .agentville/, while the plugin's workspace skill writes .agentville/topics/. No part reads another's files.
  subgraph repo["Repository"]
    inst["agentville/, pyproject.toml, install.*: installer CLI"]
    th["townhall/: Townhall package"]
    plug["plugins/agentville/: plugin, .mcp.json"]
  end
  subgraph project["A user's project"]
    ws[".agentville/topics/: workspace"]
    thfiles[".agentville/config.toml, .agentville/.gitignore, .agentville/townhall/"]
  end
  inst -->|"uvx agentville install"| plug
  plug -->|".mcp.json launches"| th
  th -->|"agentville init, tools"| thfiles
  plug -->|"workspace skill"| ws
```

In words: the installer installs the plugin, and the plugin's `.mcp.json` launches Townhall. In a user's project, Townhall writes `.agentville/config.toml`, `.agentville/.gitignore` and `.agentville/townhall/`, while the workspace skill writes `.agentville/topics/`.

The installer and Townhall both publish the distribution name `agentville` and the console script `agentville`. The [decisions page](decisions.md) covers that choice.

## Boundaries

Townhall does not back `orchestrate` or the `draft`, `plan` and `report` slots, and they never read Townhall. The workspace writes only under `.agentville/topics/`; Townhall owns `.agentville/config.toml`, `.agentville/.gitignore` and `.agentville/townhall/`. Neither exists in this repository. Temporal is required for the lifecycle workflows: `agentville engine worker` starts a local dev server on first use, and the MCP server never starts it.
