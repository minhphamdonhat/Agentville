# Architecture changes

This page shows the installer package layout and the report path after this PR.

```mermaid
flowchart TB
  accTitle: Installer layout and report path
  accDescr: The agentville package keeps __init__.py and __main__.py at its root and holds the installer in agentville/cli. A topic's report goes through the report slot to the pr-report skill, which runs the gate, pushes the working branch and creates or updates the one PR for that branch and its base.
  subgraph pkg["agentville/"]
    init["__init__.py"]
    main["__main__.py"] --> app["cli/app.py"]
    app --> console["cli/console.py"]
    app --> files["cli/files.py"]
    app --> targets["cli/targets/"]
  end
  report["report slot"] --> prr["pr-report"]
  prr --> gate["pre-publish gate"]
  gate --> push["push working branch"]
  push --> pr["one PR per head and base"]
```

In words: the `agentville` package keeps `__init__.py` and `__main__.py` at its root and holds the installer in `agentville/cli/`. A topic's report goes through the `report` slot to `pr-report`, which runs the pre-publish gate, pushes the working branch and creates or updates the one PR for that branch and its base.

The later Townhall move into `agentville/townhall/` is likely to meet this layout at `agentville/__init__.py`.
