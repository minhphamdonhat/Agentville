# Detection rules

How the scan finds each kind of risk, how a finding is rated, and the manual commands for a machine without Python 3. `python3 {{ SKILL_ROOT }}/scripts/scan.py --list-rules` prints the authoritative rule list.

## Severity scale

| Severity | Meaning | Examples |
| --- | --- | --- |
| critical | A live credential or private key, on a tip or only in history. | SEC-01 private key, SEC-03 GitHub token, a trufflehog hit marked verified. |
| high | Code or config that runs on every user's machine with no pin or review, or a likely secret. | PS-22 server installed from a tag, PS-33 committed `bypassPermissions`, SEC-20 committed `.env`. |
| medium | Personal or project data that should not ship, or a component risk that needs a decision. | PII-02 session link, PS-52 Claude-Session trailers, PS-06 side-effecting skill, PS-45 missing ignore. |
| low | A fictional or harmless value that looks like a leak, or a portability defect. | HOST-01 `/home/<user>/` in an example, HOST-06 `open()` without `encoding`, SEC-10 names-only `user:pass@`. |
| info | A fact the owner should see before publishing; no fix needed by default. | PS-48 unmerged branch, PS-51b noreply identity, PS-19 `.mcp.json` ships. |

Scope: `tip` means the value is in a file at the tip of at least one ref; `history` means only older commits hold it; `commits` means commit metadata; `refs` means the ref list itself. A secret keeps its severity in history, because anyone can read an old commit once the repository is public.

## 1. Project-specific or personal information

Category `personal`. The script flags:

* **PII-01:** email addresses, except noreply, `example.com`, `.test` and `.invalid` addresses; an email in a manifest such as `plugin.json` is info.
* **PII-02:** `claude.ai` session, chat and share links, in files and commit messages.
* **PII-03:** each word passed with `--term`, such as the owner's legal name or a client name.
* **PII-04:** internal host names ending `.internal`, `.corp`, `.lan`, `.intranet` or `.local`.
* **PS-51, PS-51b:** every author and committer identity, from `git log --all --format="%an <%ae> | %cn <%ce>"`.
* **PS-52:** `Claude-Session:` trailers; **PS-52b** counts `Co-Authored-By:` trailers (allowed).

Read as well: example projects named after a real client or employer, real people's names in examples, phone numbers and street addresses. The convention is the Acme example, in [conventions](conventions.md).

## 2. OS or host-machine information

Category `host`. The script flags:

* **HOST-01:** absolute home paths under `/home/<name>` or `/Users/<name>`; low when the name is a stock example such as `user` or `dev`, medium otherwise.
* **HOST-02:** Windows profile paths such as `C:\Users\<name>`.
* **HOST-03:** machine-specific system paths: the root user's home, WSL drive mounts and the macOS per-user temp folders.
* **HOST-04:** private network addresses (10/8, 172.16/12, 192.168/16).
* **HOST-05:** a hard-coded Unix temp folder in Python.
* **HOST-06, HOST-07:** Python text I/O and `subprocess` text mode without `encoding="utf-8"`.
* **HOST-10:** `.DS_Store`, `Thumbs.db` and `desktop.ini` files.

Read as well: commands that work in only one shell (`sha256sum` is missing on macOS, `cmp` and `mkdir -p a b` fail in PowerShell), `python3` on Windows, and tools assumed on PATH such as `rg`, `uv` or `make`.

## 3. Credentials and sensitive data

Category `secret`. The script never prints a value; it shows the length and a 10-character SHA-256 fingerprint so two hits can be matched.

* **SEC-01 to SEC-09:** private key blocks and known token shapes: AWS, GitHub, Anthropic, OpenAI-style, Slack, Google, Stripe live keys and JSON Web Tokens.
* **SEC-10:** credentials inside a URL; low when both parts are obvious names such as `user` and `pass` or `${VAR}`, high otherwise.
* **SEC-11:** a literal value assigned to a name such as `api_key`, `token` or `password`; skipped for placeholders, high when the value is long and random.
* **SEC-12:** a literal `Bearer` or `Basic` header value.
* **SEC-20, SEC-21:** committed `.env` files, keys, keystores, `.netrc`, `.npmrc`, `.pypirc` and `credentials` files, anywhere in history.
* **EXT-gitleaks, EXT-trufflehog:** hits from those tools when they are on PATH, with values dropped.

Deleting a secret does not revoke it. The fix is always: revoke or rotate first, then rewrite history (`git filter-repo`), then force-push every ref, and only the owner runs those.

## 4. Plugin components

Category `component`, rules named by catalogue id: skills PS-01 to PS-06, agents PS-09 to PS-11, hooks PS-14, MCP PS-19 and PS-22, marketplace PS-25 to PS-30, settings PS-33 to PS-39, CLAUDE.md PS-42 and PS-43, hygiene PS-45 to PS-48, metadata PS-51 to PS-53. Every entry and its "Read" checks are in the [catalogue](catalogue.md).

## 5. How the script covers history

1. Lists every ref with `git for-each-ref` (branches, remote-tracking branches, tags) and every stash entry with `git stash list`.
2. Reads each tip tree with `git ls-tree -r`, so it knows which blobs are on a tip and at which ref and path.
3. Reads every blob ever added with `git log --all --raw --no-renames`, plus `git rev-list --objects --all` for blobs only a merge or stash introduced; deleted files are included.
4. Reads blob contents through one `git cat-file --batch` process; binaries and files over `--max-bytes` are counted and skipped.
5. Groups hits by rule and matched value, so one value on five branches is one finding with five locations, and a value on any tip is reported as `tip`.
6. Reads commit metadata with `git log --all --format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B`.

Suppress a reviewed finding only with `--accept RULE:GLOB`, which keeps it visible as accepted. The scan has no inline line marker, because a marker in a file would hide a line from every later scan.

## 6. Manual commands without Python

These print matched lines, so pipe them to a count first and open the hits one by one; never paste a secret line into a report.

bash (Linux, macOS):

```bash
git -C "{{ PROJECT_ROOT }}" for-each-ref --format='%(refname)'
git -C "{{ PROJECT_ROOT }}" log --all --format='%an <%ae> | %cn <%ce>' | sort -u
git -C "{{ PROJECT_ROOT }}" log --all --format=%B | grep -c '^Claude-Session:'
git -C "{{ PROJECT_ROOT }}" grep -c -I -E 'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|sk-ant-|BEGIN [A-Z ]*PRIVATE KEY' $(git -C "{{ PROJECT_ROOT }}" rev-list --all)
git -C "{{ PROJECT_ROOT }}" log --all --diff-filter=A --name-only --format= | grep -E '(^|/)\.env|settings\.local\.json|CLAUDE\.local\.md|\.pem$|\.key$'
```

PowerShell (Windows):

```powershell
git -C "{{ PROJECT_ROOT }}" for-each-ref --format='%(refname)'
git -C "{{ PROJECT_ROOT }}" log --all --format='%an <%ae> | %cn <%ce>' | Sort-Object -Unique
(git -C "{{ PROJECT_ROOT }}" log --all --format=%B | Select-String -Pattern '^Claude-Session:').Count
git -C "{{ PROJECT_ROOT }}" grep -c -I -E 'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|sk-ant-|BEGIN [A-Z ]*PRIVATE KEY' (git -C "{{ PROJECT_ROOT }}" rev-list --all)
git -C "{{ PROJECT_ROOT }}" log --all --diff-filter=A --name-only --format= | Select-String -Pattern '(^|/)\.env|settings\.local\.json|CLAUDE\.local\.md|\.pem$|\.key$'
```

When rg is on PATH it is faster for the working tree: `rg -n -c -e '<pattern>' "{{ PROJECT_ROOT }}"`; it does not read history, so the git commands above still run.
