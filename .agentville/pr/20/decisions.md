# Decisions

The owner's PR #20 comment raised four decisions. Three are settled; the re-pin stays open.

## 1. Layout: settled

Townhall lives in `agentville/townhall/` inside the root `agentville` package, beside the installer in `agentville/cli/`. The inner board package is `agentville/townhall/board/`. Done in `e674f0a`.

## 2. Keep the shared `agentville` name: settled

There is now one `agentville` distribution and one console script. `agentville` alone is the installer CLI; `agentville townhall ...` runs Townhall. This renames `agentville init` and `agentville engine` to `agentville townhall init` and `agentville townhall engine`, a breaking change. Done in `e674f0a`.

## 3. Merge: settled

The owner merges the PR manually.

## 4. Re-pin `.mcp.json`: open

`.mcp.json` still pins `652451a` with `#subdirectory=agentville` and the command `agentville engine mcp`, because that commit predates both moves. The next re-pin, to a commit that holds `agentville/townhall/`, drops the subdirectory and uses `agentville townhall engine mcp`. Whether to re-pin in the next release-preparation commit or keep `652451a` until a later release is undecided. Until then the plugin runs Townhall as it was at `652451a`.
