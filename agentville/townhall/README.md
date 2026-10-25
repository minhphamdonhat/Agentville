# agentville.townhall

Townhall, the Kanban and documentation engine for agent towns, as part of the root `agentville` package. `agentville` alone is the installer CLI; `agentville townhall ...` runs Townhall.

Run it without installing, from the repository root:

```bash
uvx --python 3.15 --from . agentville townhall --help
```

Develop locally from the repository root with `uv run pytest tests/townhall` and `uv run ruff check agentville tests`.
