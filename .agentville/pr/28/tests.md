# Tests and evidence

This page lists the validation runs on the branch. A separate validator ran both. No review has run.

## Run-1 at `26a3698`: 7 of 10 requirements pass

| Requirement | Result |
| --- | --- |
| R3 footer hover contrast | fail, 3.27:1 |
| R5 hero | fail, the hero shows two scenes (wordmark art plus the house) |
| R8 code colours | fail, Dracula colours |
| Other 7 | pass |

Evidence: the local, untracked `evidence/run-1` folder, `SHA256SUMS` hash `c83e164be079`.

## Run-2 at `a59ca7b`

| Requirement | Command or method | Result |
| --- | --- | --- |
| R3 footer hover contrast | contrast scan over 13 pages including hover | pass, minimum 5.51:1 |
| R9 build and audit | `cd website && npm ci && npm run build && npm audit` | pass, build exit 0, 0 vulnerabilities |
| R8 code colours | contrast of every Prism token against the palette | rejected: all tokens at least 7.36:1, but 7 of 10 are lighter tints, not exact palette hexes |

Latent finding on R8: `#d4bd98` (4.48:1) and `#f4a597` (4.15:1) fall below 4.5:1 on the highlighted-line background. No page uses a highlighted line.

Evidence: the local, untracked `evidence/run-2` folder, `SHA256SUMS` hash `93b0577481d9`.

## Not tested or not verifiable

Safari and Firefox rendering, a screen reader pass, the live GitHub Pages deploy, and any review of the visuals against the mockup.
