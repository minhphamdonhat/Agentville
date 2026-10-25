# Architecture changes

This page shows the package layout, the path from the plugin's `.mcp.json` to the running server, and how Townhall sits beside the installer and the workspace.

## Package layout

One `agentville` distribution at the repository root, with one `pyproject.toml` and `uv.lock`. The installer is in `agentville/cli/`; Townhall is in `agentville/townhall/`. `agentville/cli/app.py` imports Townhall only for `agentville townhall`, so `agentville install` never loads its dependencies.

```mermaid
flowchart TD
  accTitle: agentville package layout
  accDescr: The agentville console script runs agentville/cli/app.py. Its install command uses the installer modules; its townhall command lazily imports the Townhall Typer tree in agentville/townhall/cli/, which uses the board package, the MCP server and core.
  script["agentville console script"] --> app["agentville/cli/app.py"]
  app -->|"install"| inst["agentville/cli/: console, files, targets"]
  app -->|"townhall ... (lazy import)"| thcli["agentville/townhall/cli/: Typer tree"]
  thcli --> board["agentville/townhall/board/: boards, tickets, engine, viewer"]
  thcli --> mcp["agentville/townhall/mcp/: 11 townhall_* tools"]
  mcp --> board
  core["agentville/townhall/core/: config, paths, errors, Temporal client"] --> board
```

In words: the console script runs `agentville/cli/app.py`. `agentville install` uses the installer modules; `agentville townhall ...` imports the Townhall Typer tree, which uses the board package, the MCP server and `core/`. `rag/` and `memory/` hold placeholders for later parts.

## MCP server launch path

```mermaid
sequenceDiagram
  accTitle: MCP server launch sequence
  accDescr: Claude Code calls uvx with Python 3.15 and the git source pinned at 652451a with subdirectory agentville. uvx fetches that commit, builds it and starts agentville engine mcp, which serves its tools over stdio.
  participant CC as Claude Code
  participant UVX as uvx
  participant GH as GitHub at 652451a
  participant S as agentville engine mcp
  CC->>UVX: --python 3.15 --from git+...@652451a#subdirectory=agentville
  UVX->>GH: fetch the pinned commit
  GH-->>UVX: Townhall as it was at 652451a
  UVX->>S: build and start the server
  S-->>CC: stdio MCP tools
```

In words: the pin still starts the pre-move server with `agentville engine mcp`. The next re-pin, to a commit that holds `agentville/townhall/`, drops `#subdirectory` and runs `agentville townhall engine mcp`; whether and when is undecided.

## Boundaries

Townhall does not back `orchestrate` or the `draft`, `plan` and `report` slots. The workspace writes only under `.agentville/topics/`; Townhall owns `.agentville/config.toml`, `.agentville/.gitignore` and `.agentville/townhall/`, created by `agentville townhall init`. Temporal is required: `agentville townhall engine worker` starts a local dev server on first use, and the MCP server never starts it.
