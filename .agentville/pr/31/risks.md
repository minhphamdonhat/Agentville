# Risks, limits and rollback

This page lists the risks and open limits of the conductor and build-lead change, and what limits each one.

| Risk | Impact | Mitigation |
| --- | --- | --- |
| No live cloud run yet | `create_session` parameters, build-lead tool loading and conductor's cloud detection are unconfirmed. | Run conductor once in a cloud session and watch the first ticket. |
| `issue_write` can close or retitle issues | A wrong call could change a ticket beyond its labels. | Limited by conductor rule 19 only: `labels` alone, never `state`, `title` or `body`. |
| Race between the fresh label read and the write | A label set between the two is overwritten. | The read comes immediately before each write. |
| `eval.py` grades the worker report shape | Eval results for pod-lead forks are not meaningful. | Do not rely on eval for build-lead until it is extended. |

## Rollback

* Whole PR: `git revert -m 1 {merge-sha}` on `main`.
