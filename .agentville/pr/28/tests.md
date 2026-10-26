# Tests and evidence

This page lists every check run on the branch at `57dc4b6` and its result. The checks were run by the worker that made the change, not by a separate validator.

| Check | Command | Result |
| --- | --- | --- |
| CHK-1 Build | `cd website && npm ci && npm run build` | exit 0, `[SUCCESS] Generated static files in "build"`, no broken links |
| CHK-2 Audit | `cd website && npm audit` | found 0 vulnerabilities |
| CHK-3 Typecheck | `cd website && npx tsc` | exit 0 |
| CHK-4 Contrast | WCAG relative-luminance script over 22 text pairs and 5 admonition pairs per mode | all at least 4.5:1; lowest 4.54 (night button label `#1b1307` on `#9c7845`); body text on panels 7.63 by day, 11.14 by night |
| CHK-5 Layout | Playwright on `/`, `/docs/get-started` and `/docs/technical/claude-code` at 1280, 390 and 320px, light and dark | `scrollWidth` equals the viewport; 0 elements with `scrollWidth > clientWidth`; hero title on one line from 320 to 1280px |
| CHK-6 Fonts | Playwright `document.fonts`; `grep -rlE 'fonts\.googleapis\|fonts\.gstatic' website/build` | VT323 and PressStart2P loaded; 0 requests to another host; no Google Fonts URL in the build |
| CHK-7 Security | `python3 .claude/skills/plugin-security/scripts/scan.py` with the CLAUDE.md accepts and `--fail-on medium` | critical 0, high 0, medium 0, low 17 (all present before this branch); gate pass |
| CHK-8 Steering | the four `test_scripts.py` runs, both `worker.md` comparisons, `gen_agent_variants.py --check`, and `measure.py` on the docs-site skill | all exit 0; measure: failures none, warnings none |

## How to reproduce

```bash
cd website && npm ci && npm run build && npm audit && npx tsc
```

## Notes

* The production CSS minifier (`postcss-discard-unused` in cssnano-preset-advanced) dropped every quoted `'Press Start 2P'` `@font-face`. `custom.css` therefore declares the font under the bare name `PressStart2P`, from the package's own files.
* VT323 has only weight 400, so bold text is synthesised.
* The → arrow (U+2192) is outside Press Start 2P's subsets and falls back to the monospace font.

## Not tested or not verifiable

Safari and Firefox rendering, a screen reader pass, and the live GitHub Pages deploy, which runs only on a docs tag.
