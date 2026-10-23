# Conventions

What a plugin repository holds before it goes public. `project-rules` overrides any item here. Each item names the category a breach is reported under.

## 1. Examples use Acme

Category `personal`. Every few-shot example is about one fictional project, Acme, rooted at `{{ PROJECT_ROOT }}`, with applications such as `apps/web` and `apps/api`, or documentation work under `docs/`. No example uses a real client, employer, colleague or private project name.

* Do: "Add `--retries` to the Acme API CLI in `apps/api/src/cli.py`."
* Do: "Fix the broken links in `docs/setup.md` for Acme."
* Don't: "Add pagination to the Northwind orders service"; rewrite it as the Acme `apps/api` orders list.

## 2. Host paths become placeholders

Category `host`. Write `{{ PROJECT_ROOT }}`, `{{ SKILL_ROOT }}` and `{{ USER_ROOT }}`, never a spelt-out home folder, a Windows profile path or a machine's temp folder. A deliberate host-path literal in a test that proves a host-path rule fires stays, recorded as accepted.

* Do: `{{ PROJECT_ROOT }}/.agentville/topics/acme-web-checkout-2026-10-17/worker/artefacts/report.md`.
* Don't: a path under `/home/<user>/acme/`; write `{{ PROJECT_ROOT }}/apps/...` instead.

## 3. No session links in commits

Category `personal`. Commit messages carry no `Claude-Session:` trailer and no `claude.ai` session, chat or share link. A `Co-Authored-By:` trailer is allowed.

* Do: end a commit message with `Co-Authored-By: Claude <noreply@anthropic.com>` only.
* Don't: add `Claude-Session: https://claude.ai/code/session_<id>`; drop the line.

## 4. No local settings or env files

Category `secret` for env and key files, `component` for Claude files. Never commit `.claude/settings.local.json`, `CLAUDE.local.md`, `.env` or `.env.*` (except `.env.example`), keys or keystores, agent transcripts (`*.jsonl`) or the agent run folders under `.agentville/topics/` (evidence, artefacts and scratch). An ignore file covers each of them.

* Do: commit `.env.example` holding `ACME_API_TOKEN=` with no value.
* Don't: commit `.env` "with test values only"; ignore it and commit the example file.

## 5. Placeholder credentials are names only

Category `secret`. An example credential uses obvious names, such as `user:pass@proxy.example.com` or `${ACME_API_TOKEN}`, never a value that looks real. The scan reports a names-only URL credential as low so a person confirms it.

* Do: `https://${ACME_USER}:${ACME_TOKEN}@git.example.com/acme/api.git`.
* Don't: a random-looking 40-character string "for illustration"; write `${ACME_TOKEN}`.

## 6. OS-neutral commands

Category `host`. Commands are written for bash on Linux and macOS and for PowerShell on Windows, unless the project's own rules say otherwise. A tool that is not on every machine, such as `rg`, `sha256sum`, `uv` or `make`, is used only after a presence check, with a fallback.

* Do: "bash: `shasum -a 256 file` or `sha256sum file`; PowerShell: `Get-FileHash file -Algorithm SHA256`."
* Don't: `cmp a b` as the only check; add `git diff --no-index --quiet a b`, which works in both shells.

## 7. Python is portable

Category `host`. Scripts use `pathlib` for paths, `tempfile` for temp folders, and `encoding="utf-8"` on every text read, write and `subprocess` call; they need only the standard library and git.

* Do: `Path(tempfile.mkdtemp(prefix="acme-"))` and `path.read_text(encoding="utf-8")`.
* Don't: `open("/tmp/acme.txt", "w")`; use `tempfile` and pass `encoding="utf-8"`.

## 8. Lessons from the Agentville repository

A scan of Agentville before it went public found the following; each is a check worth repeating on any plugin repository.

* No secrets in any branch or in history. Expect the same, and still scan history, because a clean tip proves nothing.
* 74 `Claude-Session:` trailer lines in commit messages linked private sessions. They come from the harness's commit attribution, so turn it off before the first commit, not after.
* Fictional host paths such as `/home/<user>/acme/...` filled the examples. They are not leaks, but they look like leaks; placeholders and Acme examples avoid the question.
* The owner's name and public GitHub handle sit in the manifests and in noreply commit identities. That is expected for a public plugin; accept it with `--accept`.
* Placeholder credentials such as `user:pass@proxy` appeared in examples. They are allowed only as names-only examples.
* An unmerged branch added a plugin `.mcp.json` that installs a server through `uvx` from `git+https` pinned to a tag. Unmerged branches go public too, and a tag can move; pin a commit SHA.
* `release-flow` merges, pushes and tags. Use `disable-model-invocation: true` on a side-effecting skill where the project's frontmatter rules allow it; where they forbid extra keys, the skill must ask before every side effect and the PS-06 finding is accepted.
* The `.gitignore` covered only a temp folder and Python caches; it did not cover `.claude/settings.local.json`, `CLAUDE.local.md`, `.env` or key files.
