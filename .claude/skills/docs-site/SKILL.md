---
name: docs-site
description: 'Maintainer standard for the Agentville documentation site, the Docusaurus project in website/: where pages live and how the sidebar lists them, the plain-language Chat and Cowork path versus the technical pages, the Press & Paper magazine design and Excalidraw diagrams, how a page is written (frontmatter, admonitions, screenshot placeholders, the Last checked footer with sources, Instructions copied byte for byte from README.md, British English), how the site is built and checked (npm ci, npm run build with broken links failing, npm audit, the security scan), and how it is deployed and refreshed (the docs workflow, agentville-docs--vX.Y.Z tags, the Pages source and the github-pages environment). Use when adding, editing, moving or reviewing a page under website/, when changing sidebars.ts, docusaurus.config.ts, package.json, the theme or home page there, when fixing a failed docs build or audit finding, or when preparing or checking a docs deploy or re-checking install steps against the Claude help pages.'
metadata:
  version: 1.2.0
---

# docs-site

Goal: a change to the Agentville documentation site keeps the pages where readers expect them, reads plainly to a non-technical Claude Chat or Cowork user, builds with no broken link and no critical or high audit finding, and is deployed only by a tag the user asked for.

## 1. Where content lives

Every page is a Markdown file under `{{ PROJECT_ROOT }}/website/docs/`, and `{{ PROJECT_ROOT }}/website/sidebars.ts` lists each one by its doc id, so a page the sidebar does not list is unreachable from the menu.

| Path | Holds | Reader |
|---|---|---|
| `website/docs/intro.md`, `get-started.md`, `how-it-works.md`, `faq.md` | The main pages, in that sidebar order with `faq` last | Chat and Cowork users |
| `website/docs/guides/` | `index.md` (the category page) plus `good-requests.md`, `following-along.md`, `updating.md` | Chat and Cowork users |
| `website/docs/technical/` | `index.md` (the category page) plus `claude-code.md`, `command-line.md`, `channels.md` | Claude Code and terminal users |
| `website/src/pages/index.tsx`, `website/src/pages/index.module.css` | The home page, a magazine front page | Everyone |
| `website/src/css/custom.css` | The Press & Paper tokens and the theme styles for every page | Everyone |
| `website/static/` | `img/favicon.svg` (the AV badge), `.nojekyll`, `diagrams/` (Excalidraw sources) and `img/diagrams/` (compiled SVGs), served as they are | Everyone |
| `website/scripts/build-diagrams.mjs` | The diagram compiler (§8); not part of the site bundle | Maintainers |
| `website/docusaurus.config.ts` | Site URL, `baseUrl: '/Agentville/'`, locale `en-GB`, navbar, footer, link checks | Maintainers |

- Add a page in the folder of its reader, then add its doc id (the path under `docs/` without `.md`, such as `guides/updating`) to `sidebars.ts` in the same change.
- Keep the two categories as they are: `Guides` links `guides/index` and `For technical users` links `technical/index`; a new page in either folder goes into that category's `items` list.
- Update the navbar or footer in `docusaurus.config.ts` when you rename or move a page they link (`/docs/intro`, `/docs/get-started`, `/docs/how-it-works`, `/docs/faq`, `/docs/technical`).
- Never commit `website/node_modules`, `website/build` or `website/.docusaurus`; `website/.gitignore` ignores them.

Correct: "Add `website/docs/guides/sharing.md` and append `'guides/sharing'` to the `Guides` items in `sidebars.ts`."

Wrong: "Add `website/docs/sharing-advanced.md` and leave `sidebars.ts` unchanged."

## 2. Who each page is for

The Chat and Cowork pages are written for a reader who has never used a terminal, and everything technical lives under `docs/technical/`.

| Reader | Pages | Write |
|---|---|---|
| Claude Chat or Cowork user | Top level and `guides/` | Menu names in bold, such as **Customize**, then **Plugins**; one action per numbered step; no shell, no file paths, no agent names |
| Claude Code or terminal user | `technical/` | Commands in fenced `bash` or `powershell` blocks, slash commands, paths and release channels |

- Explain a term the first time a Chat or Cowork page uses it, or leave it out; send the reader to `technical/` for anything that needs a terminal.
- Open each technical page with who it is for and link the Chat and Cowork reader back to `get-started.md`, as `technical/index.md` does.
- Name the three marketplace entries as a reader sees them: `agentville` (Stable), `agentville-beta` and `agentville-dev`, and say that only one should be added.

Correct: "In the left sidebar, click **Customize**, then open the **Plugins** tab."

Wrong: "Open a terminal and install from the `release` branch with the plugin marketplace command." on `get-started.md`.

## 3. Writing a page

Every page carries frontmatter, uses Docusaurus admonitions for asides, marks missing screenshots with a placeholder and ends with a dated footer that cites its sources.

- Frontmatter holds `title` and `description`, plus `sidebar_position` on the main pages that already carry one; the H1 states the page's subject in full; it may expand a short sidebar title, as `faq.md` does.
- Write asides as admonitions with a bracketed title: `:::note[Before you start]`, `:::tip[Pick Stable]`, `:::info[...]`, closed by `:::` on its own line.
- Mark a screenshot that does not exist yet with an empty info admonition, `:::info[Screenshot coming soon: Settings → Your Claude → Instructions]` followed by `:::`, placed right after the step it shows, and name the menu path in the title.
- End every page that states install or menu steps with a `---` rule, then `Last checked: <date>` written as `25 October 2026`, then `Sources:` and a bullet list of the pages the steps were checked against.
- Copy the two Instructions lines byte for byte from the `README.md` block at the repository root, backticks and leading hyphens included, into a fenced `markdown` block; when `README.md` changes them, change every page that quotes them in the same change.
- Link other pages with relative Markdown paths that include `.md`, such as `./guides/good-requests.md` or `../get-started.md`, so the build checks them.
- Write British English (behaviour, organise, licence) and follow `Skill(agentville:voice)` for register, length and lists; use Acme for every example request.
- Write no secret, host path, personal name or internal URL; the owner's public GitHub handle in links is the only identity allowed.

Correct:

```markdown
- Load `Skill(agentville:root-agent)` and follow it in every reply.
- Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it.
```

Wrong: the same two lines retyped with curly quotes, without the backticks, or with "Use" in place of "Load".

## 4. Building and checking

A docs change is finished only when the site builds clean, the audit shows no critical or high finding and the repository security scan shows no critical or high finding.

| Check | Command, from the repository root | Pass |
|---|---|---|
| Build | `cd website && npm ci && npm run build` | Exits 0; `onBrokenLinks: 'throw'` and `onBrokenAnchors: 'throw'` at the top of `docusaurus.config.ts`, and `onBrokenMarkdownLinks: 'throw'` under `markdown.hooks`, turn any broken link into a failure |
| Audit | `cd website && npm audit` | 0 critical and 0 high |
| Security scan | `python3 .claude/skills/plugin-security/scripts/scan.py --accept 'PS-06:*release-flow/SKILL.md' --accept 'PS-06:*pr-report/SKILL.md' --accept 'PS-25:*.claude-plugin/marketplace.json' --accept 'PS-09:*agents/worker.md' --accept 'PS-09:*agents/worker-*-*.md'` | No critical or high finding |

- Run `npm ci` for every build and check, never `npm install`, so the build uses `website/package-lock.json` exactly as CI does; on Windows run the same npm commands in PowerShell, with `cd website; npm ci; npm run build`, and `py -3` for `python3`.
- Fix an audit finding with an exact-version entry in the `overrides` block of `website/package.json`, as `tinypool`, `serialize-javascript`, `postcss-selector-parser` and `sockjs` > `uuid` already are, then run `npm install` once, only because you changed dependencies or the lock file, to refresh the lock file, and `npm ci` again for the build; never downgrade a Docusaurus or React dependency to clear a finding.
- Pin every dependency to an exact version (`3.10.2`, not `^3.10.2`), and keep the Docusaurus packages on one shared version.
- Fix a broken link in the page that holds it; never relax `onBrokenLinks` or `onBrokenAnchors` to `warn`.

Correct: "`npm audit` reports a high finding in `uuid` under `sockjs`; add `"sockjs": {"uuid": "11.1.1"}` to `overrides`, refresh the lock file, and `npm audit` shows 0 high."

Wrong: "Set `@docusaurus/core` back to an older 3.x release until `npm audit` is quiet."

## 5. Deploying the site

The site deploys only from `{{ PROJECT_ROOT }}/.github/workflows/docs.yml`, on a pushed tag `agentville-docs--vX.Y.Z` or a manual run, and a tag is created only when the user asks for that tag.

- The workflow's `build` job runs `npm ci` and `npm run build` in `website/` on Node 22 and uploads `website/build`; its `deploy` job publishes it to the `github-pages` environment with `pages: write` and `id-token: write`, and the workflow-wide permission stays `contents: read`.
- Pin every action in `docs.yml` to a full commit SHA with its release tag in a trailing comment, such as `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`; never point an action at a moving tag or branch.
- Before pushing a docs tag, run the pre-publish gate from `CLAUDE.md` and push only when it exits 0: `python3 .claude/skills/plugin-security/scripts/scan.py --accept 'PS-06:*release-flow/SKILL.md' --accept 'PS-06:*pr-report/SKILL.md' --accept 'PS-25:*.claude-plugin/marketplace.json' --accept 'PS-09:*agents/worker.md' --accept 'PS-09:*agents/worker-*-*.md' --fail-on medium`.
- Create, push or delete a docs tag only when the user names that tag and asks for it, and never on your own; the docs tag is separate from the plugin tag `agentville--vX.Y.Z`.
- Set the repository's Pages source to GitHub Actions under **Settings**, then **Pages**, then **Source**; a branch source ignores the workflow.
- Allow the docs tags on the `github-pages` environment under **Settings**, then **Environments**, then **github-pages**, then **Deployment branches and tags**, with a tag rule `agentville-docs--v*`; without it the `deploy` job is rejected for a tag-triggered run.
- Check a deploy by the workflow run's result and by opening the published site under `/Agentville/`; a green build job alone does not prove the deploy ran.

Correct: "The user asked for `agentville-docs--v1.2.0`; create that tag on the commit they named and report the workflow run."

Wrong: "The build passed, so I tagged `agentville-docs--v1.2.1` and pushed it."

## 6. Refreshing install steps

Install and menu steps go stale as Claude's apps change, so every page with steps is re-checked against its sources and its `Last checked` date is moved only after the check.

| Page | Check against |
|---|---|
| `get-started.md`, `guides/updating.md` | The support.claude.com articles in each page's `Sources:` list, such as [Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude) |
| `technical/claude-code.md`, `technical/command-line.md` | The code.claude.com pages in each page's `Sources:` list, such as [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins), and the `README.md` install section |

- Compare each numbered step with the source page's current menu names and order; change the step, the screenshot placeholder title and the `Sources:` list together.
- Move `Last checked` to the date of the check only when every step on the page was compared; a page partly checked keeps its old date.
- Add a source to `Sources:` for every page the new steps rely on, and remove a source the steps no longer use.
- Keep a notice such as `:::info[Chat and Cowork are becoming one]` only while its source still says the change is rolling out.

Correct: "support.claude.com now names the tab **Connectors**; step 2 and its screenshot placeholder are updated and `Last checked` reads 2 November 2026."

Wrong: "Moved `Last checked` to today on every page without opening the sources."

## 7. Press & Paper design

The site wears the Press & Paper magazine edition: a white sheet with a soft shadow on a lavender-grey mat, ink type, grey hairlines, four pastel tints, one brick accent for kickers and hover, black buttons, light only and square corners.

The tokens live once, on `:root` in `website/src/css/custom.css`, and every style uses them by name.

| Token | Value | Use |
|---|---|---|
| `--pp-mat` | `#E9E8EE` | The ground around the sheet, on desktop only |
| `--pp-paper` | `#FFFFFF` | The sheet: every page, the navbar and the footer |
| `--pp-panel` | `#F4F3F0` | Code, table heads, example requests, the note admonition |
| `--pp-ink` | `#222020` | Text, headings, links, rules under the active item, ink cards |
| `--pp-ink-soft`, `--pp-ink-muted` | `#5A5856`, `#6E6B68` | Secondary text: navigation, TOC, captions, datelines |
| `--pp-rule` | `#D9D6D0` | Every hairline: navbar, frames, tables, sidebar |
| `--pp-pink`, `--pp-pink-strong` | `#FAD4E6`, `#F2A6C8` | Ticker band, active item, highlighter, link underline, chips |
| `--pp-yellow`, `--pp-mint`, `--pp-sky` | `#F3E3B5`, `#E2F4EA`, `#D4E9F7` | Hero and warning; tip; info and sidebar box |
| `--pp-brick`, `--pp-brick-dark` | `#A32A22`, `#86221B` | Kickers, breadcrumbs, TOC active and hover; never a fill |
| `--pp-black` | `#000000` | Buttons, with white label text |

Set type in five families from exact-pinned `@fontsource` packages, imported as Latin subsets at the top of `custom.css`; never load a font from Google Fonts or another CDN.

| Family | Weights | Use |
|---|---|---|
| Libre Franklin | 400, 600, 800 | Body, the page H1 (800), H2 and H3, lead headlines |
| Oswald | 300 to 600 | Navigation, labels, kickers, masthead, buttons, in tracked uppercase |
| Playfair Display | italic 400 and 700 | The accent tail of a headline (`pp-accent`) and section titles |
| Libre Caslon Text | 400, 700 | The standfirst under the H1, the price line and the drop cap |
| Caveat | 500 | One short script note per view, decorative and `aria-hidden` |

Build every page from these components:

- **Sheet and navigation:** `#__docusaurus` is the sheet, up to 1280px wide on the mat from 997px; the navbar is a white row under a hairline with the round AV badge, and the active link sits on pink with a 2px ink rule beneath.
- **Article:** the breadcrumbs read as a brick kicker, the H1 is Libre Franklin 800, the first paragraph is a Caslon standfirst, tables and code sit on the panel between hairlines, and admonitions are pastel panels with an Oswald heading.
- **Home page:** in mobile reading order, the masthead (badge, nameplate with dateline, price), the pink ticker band, the light uppercase section row, the yellow hero with one black Get started button, the three-column front (short stories with the black promo card, the lead with a drop cap, the sidebar with the sky box, guides and the note), the stages as an archive grid, the three step cards and a folio.
- **Ornaments:** only a ghost numeral, the pink highlighter (`pp-highlight`) and the Caveat note; each is decorative, `aria-hidden` and repeats nothing that is not live text nearby, and rotation stays in the desktop media query.

Do:

- Use a pastel as a ground for ink text, check every new text and ground pair at 4.5:1 or more (3:1 for large text) with a WCAG contrast script, and keep circles for the badge and arrow buttons only.
- Keep every word live text, keep `colorMode` at `defaultMode: 'light'` with `disableSwitch: true`, and keep the code theme `pressPaperCode` in `docusaurus.config.ts` light only.

Don't:

- Set text in brick on a pastel, use a pastel or brick as a text colour, round a box or button, or add a grey shadow other than the sheet's.
- Add a display face outside the five families, a heavy double or thick rule, or an image that carries words a reader needs.

Correct: "Add a guide card to the front as an Oswald title with a Playfair italic tail under a hairline, with a brick kicker on white."

Wrong: "Set the kicker in brick on the yellow hero, round the code blocks and put the step list in a picture."

## 8. Diagrams

Draw each diagram as an Excalidraw scene in ink on white with one pastel tint (pink for the boxes), and compile it to SVG with Excalidraw's own `exportToSvg`, so the fonts are embedded and the page makes no font request.

| Path | Holds |
|---|---|
| `website/static/diagrams/<name>.excalidraw` | The source scene, editable at excalidraw.com or in the Excalidraw app |
| `website/static/img/diagrams/<name>.svg` | The compiled SVG the page shows |
| `website/scripts/build-diagrams.mjs` | The compiler: it bundles Excalidraw with esbuild, opens it in headless Chromium through Playwright, aborts every request outside 127.0.0.1 and writes one SVG per scene |

- Install the compiler's packages outside `website/`, at exact versions, so the site's lock file and bundle stay as they are: `npm install --prefix <deps> --save-exact @excalidraw/excalidraw@0.18.1 react@19.3.1 react-dom@19.3.1 esbuild@0.28.2`, plus Playwright with Chromium. Then run `node website/scripts/build-diagrams.mjs --deps <deps>` from the repository root and commit the scene and the SVG together.
- Show a diagram in a page as `<figure className="pp-figure">` holding a Markdown image with alt text that states the whole flow, a `<figcaption>`, and, right after the figure, a plain numbered list of the same steps.
- Keep diagram text in ink on white or on the one tint, at 4.5:1 or more, and set `"source"` in the scene to `https://excalidraw.com`, never a local address with a port.

Correct: "Edit `six-stages.excalidraw`, run the compiler, commit both files, and update the alt text and the step list in `how-it-works.md` to match."

Wrong: "Export a PNG screenshot of the diagram, or draw it in a Mermaid code block, and skip the step list."

## Pre-send check

Run each item before saving or handing over a docs change. The section holds the rule.

1. Every new or moved page sits in its reader's folder and is listed in `sidebars.ts`, and the navbar and footer links still resolve (§1).
2. Chat and Cowork pages hold no shell command, file path or agent name, and technical detail sits under `docs/technical/` (§2).
3. Each page has `title` and `description` frontmatter, admonitions with bracketed titles, screenshot placeholders in the `Screenshot coming soon:` form, and a `Last checked` footer with sources (§3).
4. The Instructions lines match `README.md` byte for byte (§3).
5. `npm ci && npm run build` exits 0, `npm audit` shows 0 critical and 0 high with fixes in `overrides`, and the security scan shows no critical or high finding (§4).
6. No docs tag was created or pushed unless the user asked for that tag, and every action in `docs.yml` is pinned to a commit SHA (§5).
7. `Last checked` moved only on pages whose steps were compared with their sources today (§6).
8. Styles use the Press & Paper tokens, light only and square, every text pair is 4.5:1 or more, fonts come from pinned `@fontsource` packages, and every ornament is decorative, `aria-hidden` and flat on mobile (§7).
9. Every diagram is an Excalidraw scene compiled to SVG with embedded fonts, committed with its source, and shown with alt text and a plain list of its steps (§8).
