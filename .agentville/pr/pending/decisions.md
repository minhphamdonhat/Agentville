# Open decisions

This page lists the four decisions the owner needs to make before or at merge. Each gives the current choice and the alternative.

## 1. Move Townhall to `townhall/` or rename the installer

The current choice moves Townhall to `townhall/` in `138433f`, because `main`'s installer already occupies `agentville/`, `pyproject.toml` and `tests/` at the root. The alternative renames or moves the installer instead and keeps Townhall in `agentville/`. That would match the pin's `subdirectory=agentville`, but it changes the installer that `main` already ships.

## 2. Keep the shared `agentville` distribution and console name

Both packages use the distribution name `agentville` and a console script `agentville`: the installer maps it to `agentville.cli:main` and Townhall to `agentville.cli.main:app`. The current choice keeps both, because `uvx` gives each its own environment. The alternative renames Townhall's distribution or console script, such as to `townhall`, which changes the `.mcp.json` command and the docs.

## 3. Merge without squashing

The current pin, `652451a`, is a feature-branch commit. A squash-merge leaves it on no branch that `main` keeps, so the server stops starting once the branches go. The current choice is a merge commit. The alternative is to squash and then re-pin to the squashed commit in a follow-up.

## 4. Re-pin to `subdirectory=townhall` at the next release

At the next release, the release-preparation commit on `main` moves the pin to the commit whose `townhall/` the release ships and switches the subdirectory to `townhall`. The decision is whether to do that at 0.10.0 itself or leave `652451a` in place until a later release.
