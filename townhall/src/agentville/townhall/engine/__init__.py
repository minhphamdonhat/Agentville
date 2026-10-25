"""Townhall's durable engine, split by what each part may import.

* `workflow`: the lifecycle workflow and its activities; sandbox-safe.
* `client`: ids, signal-with-start and the best-effort `notify_move`.
* `worker`: the Temporal worker process.
* `poller`: the triage poller and the Complete-stage auto-merge.

Keep this file free of imports: the workflow sandbox re-imports the package.
"""
