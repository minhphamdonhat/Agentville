# Plugin security catalogue

Risks of a public Claude Code plugin repository, PS-01 to PS-53, researched 2026-10-23. **verified** means the claim was read in a fetched page; **unverified** means it came from search summaries, a page that could not be fetched, or general practice. Keep the label on every finding that cites an entry. Version numbers and CVE fix versions change often; re-check them against the docs on release day.

"Script" names the `scan.py` rule that flags the pattern. "Read" means the check needs a person or a model to read the file at each tip ref; step 4 of the skill does it.

Doc base: `https://code.claude.com/docs/en/`. Short names: SEC `security`, PERM `permissions`, SET `settings`, SKL `skills`, SUB `sub-agents`, HK `hooks`, MCP `mcp`, MKR `plugins/marketplace-reference`, LOAD `plugins/loading`, MEM `memory`.

## Skills

| ID | Risk | Check | Fix | Status |
| --- | --- | --- | --- | --- |
| PS-01 | `allowed-tools` pre-approves tools for the turn; workspace trust does not gate it, even in `-p` runs. | Script PS-01; high for bare `Bash`, `Bash(*)`, `Write` without a path or `mcp__*`. | List exact, narrow commands, or drop the field. | verified (SKL) |
| PS-02 | The bang-backtick form (an exclamation mark right before an inline command) in a skill body runs a shell command before the model reads the skill. | Script PS-02 over `skills/`, `commands/`, `agents/`. | Avoid it, or keep it read-only with fixed arguments. | verified (SKL) |
| PS-03 | `hooks` in skill frontmatter register on invocation and run for the rest of the session. | Script PS-03. | Do not ship frontmatter hooks; document any that must exist. | verified (SKL, HK) |
| PS-04 | Bundled scripts run unreviewed; an allow rule plus the same path lets a later malicious edit run silently. | Script PS-04 (`shell=True`, `os.system`, `eval`, `pickle`); Read every script for network calls and writes outside the workspace. | Review each script per release; no network; validate path arguments (reject `..`, absolute paths, symlinks out of the root). | verified (behaviour), unverified (patterns) |
| PS-05 | Hidden instructions in Markdown: credential-reading directions, override text, invisible Unicode (tag characters, zero-width, bidi). | Script PS-05 (characters) and PS-05b (phrasing) over every `.md`, JSON and script. | Strip invisible characters in CI; read every skill as untrusted prose before release. | unverified |
| PS-06 | Without `disable-model-invocation: true`, the model can load a skill that pushes, tags, merges or deletes when injected text asks. | Script PS-06; Read to confirm the skill performs the action. | Set the field on every skill with irreversible or external effects, and keep its ask-before-act rule. | verified (SKL) |
| PS-07 | `Bash(curl *)` removes the network guard; argument rules are bypassed by option order, redirects and variables. | Script PS-07 (a download piped into a shell); Read each agent's tools and each `allowed-tools` for network tools. | Deny `curl` and `wget`; give network tools to one agent only. | verified (PERM, SEC) |
| PS-08 | Skill folders reload live, so an agent that can write under `skills/` can change the rules it runs under. | Read agents that may `Write` or `Edit` under `skills/` or `.claude/`. | Keep read-only agents read-only. | verified (SKL) |

## Agents

| ID | Risk | Check | Fix | Status |
| --- | --- | --- | --- | --- |
| PS-09 | No `tools:` line means every tool, MCP included. | Script PS-09. | Write an explicit allowlist; add `mcp__*` to `disallowedTools` when no MCP is needed. | verified (SUB) |
| PS-10 | A child with `Agent` can spawn more agents; the `Agent(type)` list is ignored inside a subagent. | Script PS-10 (info); Read to confirm only the main agent holds it. | Keep `Agent` out of child tool lists. | verified (SUB) |
| PS-11 | `permissionMode` such as `bypassPermissions` is honoured for project agents. | Script PS-11. | Never set it in shipped agents. | verified (SUB) |
| PS-12 | `hooks` or `mcpServers` in agent frontmatter are ignored for plugin agents but go live when copied to `.claude/agents/`. | Script PS-03; Read for `mcpServers:`. | Put hooks in `hooks/hooks.json` and servers in the plugin's `.mcp.json`. | verified (SUB) |
| PS-13 | `disallowedTools: Bash(git push *)` removes all of Bash, not one command. | Read `disallowedTools:` entries that hold `(`. | Put command-level denies in `permissions.deny`. | verified (SUB) |

## Hooks

| ID | Risk | Check | Fix | Status |
| --- | --- | --- | --- | --- |
| PS-14 | Hooks are arbitrary commands with the user's environment; plugin hooks merge with the user's. | Script PS-14 (network or `eval` in a command); Read every `hooks.json` and `"hooks"` block. | Ship no hooks unless required; keep commands local, fixed and documented. | verified (HK) |
| PS-15 | A crashing or timed-out `PreToolUse` hook lets the call through unless `onFailure: block`; `if` is best effort. | Read hooks used as the only gate. | Enforce with `permissions`; set `onFailure: block`. | verified (HK) |
| PS-16 | Unquoted `${CLAUDE_PLUGIN_ROOT}` in shell form breaks on spaces and metacharacters. | Read hook `command` strings. | Use exec form, or double-quote each placeholder. | verified (HK) |
| PS-17 | A malicious marketplace plugin reportedly used a hook to pass the approval prompt and exfiltrate files. | As PS-14, plus third-party marketplaces. | Install only from marketplaces you control. | unverified |

## MCP servers

| ID | Risk | Check | Fix | Status |
| --- | --- | --- | --- | --- |
| PS-18 | MCP servers are not audited; servers that fetch content can inject instructions. | Read every `.mcp.json` and `mcpServers` block, and docs that tell users to add a server. | Write your own or use a trusted provider; document data flows. | verified (SEC, MCP) |
| PS-19 | Project `.mcp.json` loads without a prompt in `-p`, SDK and cloud sessions. | Script PS-19 (info). | Tell headless users to use `--setting-sources user` or `disabledMcpjsonServers`. | verified (MCP, PERM) |
| PS-20 | Tokens in `env` or `headers` get committed; `headersHelper` runs shell. | Script SEC-11, SEC-12, PS-37. | Reference environment variables only; never ship `headersHelper`. | verified (MCP) |
| PS-21 | Plugin-declared servers do not show in a review of the root `.mcp.json`. | Read `mcpServers` in `plugin.json` and marketplace entries. | List every shipped server in the README. | verified (SEC, LOAD) |
| PS-22 | `uvx`, `npx -y` or `git+https://…@tag` pulls whatever the ref points to at launch; a moved tag is a rug pull. | Script PS-22 (tag or branch ref), PS-22b (`@latest`), PS-22c (package runner; cleared when the launched package's own spec in that server entry (`--from`, `-p`, `--spec` or the first positional arg, not `--with` values or later args) pins `pkg@X.Y.Z`, `pkg==X.Y.Z` or a git source at a full 40-hex SHA). | Pin a 40-character commit SHA or a hash-locked package. | unverified for MCP; SHA pinning verified for plugin sources (MKR) |
| PS-23 | Tool poisoning: hidden instructions in tool descriptions; descriptions can change after approval. | Read the server's tool docstrings and schemas. | Keep descriptions short and static; snapshot-test them. | unverified |
| PS-24 | The server's own code: path traversal, `shell=True`, `eval`, SSRF, secrets in logs. | Script PS-04; Read file access for resolve-then-contain checks. | Resolve paths and check containment; argument lists; run `bandit` and `pip-audit` in CI. | unverified |

## Marketplace

| ID | Risk | Check | Fix | Status |
| --- | --- | --- | --- | --- |
| PS-25 | A `ref` (branch or tag) or no ref tracks a moving target; only `sha` pins content. | Script PS-25. | Pin `sha` for the stable entry, or protect its branch; say which entries move. | verified (MKR) |
| PS-26 | `version` decides who gets new code; third-party marketplaces do not auto-update by default. | Read `version` in `plugin.json` against what shipped. | Bump `version` on every shipped change; keep a changelog. | verified (LOAD) |
| PS-27 | Names that imitate official marketplaces are refused or warned; non-ASCII names are rejected. | Read `name` fields; avoid `claude-`, `anthropic-`, `official`. | Run `claude plugin validate`. | verified (MKR) |
| PS-28 | `archive` without `sha256`, unversioned `npm` and `command` sources fetch or run code on every install. | Script PS-28. | Use relative or `github` sources with `sha`; never `command`. | verified (MKR) |
| PS-29 | `..` paths and symlinks that leave the plugin are rejected; a symlink to a private path leaks layout. | Script PS-29 and PS-29b. | No symlinks out of the repository; run `claude plugin validate`. | verified (LOAD, MKR) |
| PS-30 | Plugin `package.json` dependencies install and run when hooks or servers load them. | Script PS-30 (info). | Avoid dependencies, or commit and audit the lockfile. | verified (LOAD) |
| PS-31 | Third-party skill ecosystems carry malware at scale (reported study of about 4,000 skills). | Read vendored or copied skills for provenance. | Do not vendor without review; record source and licence. | unverified |

## Settings

| ID | Risk | Check | Fix | Status |
| --- | --- | --- | --- | --- |
| PS-32 | Over-broad `permissions.allow` such as `Bash(git *)` or bare `Bash` reaches every teammate once trusted. | Read `allow` lists in committed settings. | Allow exact read-only commands; deny `git push`, `curl`, `wget`. | verified (PERM, SET) |
| PS-33 | Committed `bypassPermissions` or `defaultMode`; older versions honoured them from project settings. | Script PS-33. | Never commit them. | verified (PERM, SET) |
| PS-34 | CVE-2026-33068: before 2.1.53 the permission mode was read from repository settings before the trust dialog. | Script PS-33. | Update to 2.1.53 or later; do not commit `defaultMode`. | verified (GHSA-mmgp-wc2j-qcv7) |
| PS-35 | CVE-2026-40068: a crafted worktree `commondir` bypassed folder trust (2.1.63 to 2.1.84). | Script PS-35 (tracked `.git` file). | Update to 2.1.84 or later; ship no hooks in committed settings. | verified (GHSA-q5hj-mxqh-vv77) |
| PS-36 | CVE-2025-59536 and CVE-2026-21852: project code before trust, and `ANTHROPIC_BASE_URL` redirecting API keys. | Script PS-36. | Keep Claude Code current; never set endpoint or credential variables in committed config. | unverified |
| PS-37 | `env`, `apiKeyHelper` and `awsAuthRefresh` in committed settings apply before full trust and with `--bare`. | Script PS-37 and PS-37b. | Commit none of them; keep them in user settings. | verified (PERM) |
| PS-38 | Committed `enableAllProjectMcpServers` or `enabledMcpjsonServers` defeats the per-server prompt. | Script PS-38. | Do not commit them. | verified (MCP) |
| PS-39 | `.claude/settings.local.json` collects allow rules with hosts, paths and tokens; a hand-made one is not ignored. | Script PS-39 (tracked anywhere in history) and PS-45 (not ignored). | Ignore `**/.claude/settings.local.json`; purge history if it was committed. | verified (SET, PERM) |
| PS-40 | Without `Read` deny rules the model can read `.env` and key files; `.claudeignore` has no effect. | Read shared settings for `Read(./.env)` denies. | Ship a sample deny block in the README. | verified (PERM, SET) |

## CLAUDE.md

| ID | Risk | Check | Fix | Status |
| --- | --- | --- | --- | --- |
| PS-41 | CLAUDE.md is context, not enforcement; a cloned repository's CLAUDE.md is an injection point. | Read for security rules that exist only as prose. | Back each critical rule with a `permissions.deny` rule or a hook. | verified (MEM) |
| PS-42 | An `@` import or a `.claude/rules/` symlink outside the repository needs one approval, then loads silently. | Script PS-42; Script PS-29b for symlinks. | Keep imports inside the repository. | verified (MEM) |
| PS-43 | `CLAUDE.local.md` holds personal notes and gets committed when not ignored. | Script PS-43 and PS-45. | Add it to `.gitignore`. | verified (MEM) |

## Repository hygiene

| ID | Risk | Check | Fix | Status |
| --- | --- | --- | --- | --- |
| PS-44 | Every reachable commit goes public; a secret deleted from the tip stays in history. Deleting is not revoking. | Script SEC-01 to SEC-21 over all blobs; gitleaks or trufflehog when present. | Rotate first, then rewrite history with `git filter-repo`; enable secret scanning and push protection. | unverified |
| PS-45 | Missing ignores for local and agent files. | Script PS-45 (probes the working-tree `.gitignore`; skipped with a note on a bare repository). | Ignore the agent run folders (`.agentville/topics/.gitignore`: `*/evidence/`, `*/*/artefacts/`, `*/*/scratch/`), `.env`, `.env.*`, `*.pem`, `*.key`, `.claude/settings.local.json`, `CLAUDE.local.md`. | verified for the two Claude files |
| PS-46 | Host paths, usernames, emails and internal hosts reveal identity and layout; fictional paths look like leaks. | Script HOST-01 to HOST-04, PII-01, PII-04. | Use `{{ PROJECT_ROOT }}`, `{{ SKILL_ROOT }}`, `{{ USER_ROOT }}` and example.com. | unverified |
| PS-47 | Agent workspaces, transcripts and logs hold prompts, paths and tool output. | Script PS-47. | Ignore workspace folders; review eval fixtures before commit. | unverified |
| PS-48 | Every branch, tag and fork-reachable object goes public at the switch, unmerged branches included. | Script PS-48 (unmerged refs) and PS-48b (stash). | Review or delete unwanted refs first; `git gc --prune=now` after a rewrite. | unverified |
| PS-49 | `pull_request_target`, `${{ github.event.* }}` in `run:` and secrets on fork PRs are exploitable once public; unprotected branches let a stolen account change what a marketplace serves. | Read `.github/workflows/`; check rulesets with `gh api repos/<owner>/<repo>/rulesets`. | Least-privilege `permissions:`, actions pinned to SHAs, protected release branches, 2FA. | unverified |
| PS-50 | Without `SECURITY.md` reporters open public issues. | Read for `SECURITY.md` and `LICENSE`. | Add `SECURITY.md` with a private contact. | unverified |

## Commit metadata

| ID | Risk | Check | Fix | Status |
| --- | --- | --- | --- | --- |
| PS-51 | Every commit exposes author and committer name and email for good. | Script PS-51 and PS-51b list every identity. | Commit with the GitHub noreply address; rewrite with a mailmap if needed. | unverified |
| PS-52 | `Claude-Session:` trailers link private session transcripts; `Co-Authored-By` names the model. | Script PS-52 (trailers), PII-02 (session links), PS-52b (co-authors, allowed). | Stop adding the trailer; strip it with `git filter-repo --message-callback` if wanted. | unverified |
| PS-53 | Tags can move unless protected; unsigned commits and tags prove no origin. | Script PS-53 (lightweight tags); Read `git tag -v <tag>`. | Sign release tags, protect release tags, pin installs by SHA. | unverified |

## Sources

Fetched and verified: the doc pages named by short name above; `https://github.com/advisories/GHSA-mmgp-wc2j-qcv7`; `https://github.com/advisories/GHSA-q5hj-mxqh-vv77`. Seen only in search summaries: `https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/`, `https://promptarmor.substack.com/p/hijacking-claude-code-via-injected`, the Cloud Security Alliance research notes on SKILL.md context poisoning and MCP tool poisoning, and the CVE-2026-21852 write-ups.
