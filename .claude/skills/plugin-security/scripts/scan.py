#!/usr/bin/env python3
"""Read-only security scan of a git repository that holds Claude Code plugins.

Scans every local branch, remote-tracking branch, tag and stash entry, the full history (deleted files
included) and the commit metadata (authors, committers, trailers). Needs only Python 3.8+ and git, and
runs on Linux, macOS and Windows. Uses gitleaks or trufflehog as an extra pass when they are on PATH.
Never prints a secret value: a secret is shown as its length and a short SHA-256 fingerprint.

Usage:
  scan.py [--repo PATH] [--refs all|REF[,REF...]] [--format text|json] [--out FILE]
          [--term WORD]... [--accept RULE:GLOB]... [--fail-on LEVEL] [--external auto|off]
          [--max-bytes N] [--list-rules]

Exit codes: 0 no open finding at or above --fail-on, 1 at least one, 2 the scan could not run.
A reviewed finding is suppressed only through `--accept RULE:GLOB`, which keeps it visible as accepted.
"""
import argparse
import fnmatch
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SEVERITIES = ["info", "low", "medium", "high", "critical"]
RANK = {s: i for i, s in enumerate(SEVERITIES)}
ZERO = "0" * 40
SHA40 = re.compile(r"^[0-9a-f]{40}$")
PLACEHOLDER = re.compile(
    r"^(\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|<[^>]*>|\{\{[^}]*\}\}|\[\[.*\]\]|%[A-Za-z_]+%|[xX*.#-]+"
    r"|(your|my|example|dummy|fake|test|sample|changeme|placeholder|redacted|replace)[-_a-z0-9]*"
    r"|user(name)?|pass(word|wd)?|secret|token|key|value|foo|bar|baz|none|null|true|false)$", re.I)
SAFE_MAIL = re.compile(r"(noreply|no-reply)@|@(users\.)?noreply\.github\.com$|@([\w-]+\.)*example\.(com|org|net)$"
                       r"|\.(example|test|invalid|localhost)$|^git@", re.I)
FICTIONAL_USERS = {"user", "dev", "me", "you", "username", "name", "example", "runner", "alice", "bob"}
MANIFEST = r"(^|/)(plugin\.json|marketplace\.json|package\.json|pyproject\.toml|setup\.cfg|CITATION\.cff)$"
JSONISH = r"\.(json|jsonc|ya?ml|toml)$"
SETTINGS = r"(^|/)(settings[^/]*\.json|\.mcp\.json|hooks\.json|plugin\.json|marketplace\.json)$"
SKILL_MD = r"(^|/)SKILL\.md$"
AGENT_MD = r"(^|/)agents/[^/]+\.md$"
PY = r"\.py$"
DOCS = r"\.(md|mdx|markdown|txt|json|ya?ml|toml)$"


def entropy(s):
    if not s:
        return 0.0
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in (s.count(ch) for ch in set(s)))


def secret_value(v, high="high"):
    """Severity for a literal value assigned to a secret-looking name, or None when it is a placeholder."""
    if PLACEHOLDER.match(v) or "${" in v or "{{" in v or "<" in v or len(set(v)) < 4:
        return None
    return high if len(v) >= 16 and entropy(v) >= 3.5 else "low"


def check_url_creds(m):
    user, pw = m.group(1), m.group(2)
    if all(re.search(r"\$|\{\{|<", part) for part in (user, pw)):
        return None
    if (PLACEHOLDER.match(user) or "$" in user) and (PLACEHOLDER.match(pw) or "$" in pw):
        return "low"
    return "high"


def check_home(m):
    if m.group(1).startswith("<"):
        return None
    return "low" if m.group(1).lower() in FICTIONAL_USERS or m.group(1).startswith("<") else "medium"


def check_email(m, line, path):
    addr = m.group(0)
    if m.start() > 0 and line[m.start() - 1] in ":/":
        return None
    if SAFE_MAIL.search(addr) or re.search(r"\.(png|jpe?g|gif|svg|webp)$", addr, re.I):
        return None
    return "info" if path and re.search(MANIFEST, path) else "medium"


def check_open(m, line):
    if "encoding=" in line or re.search(r"""['"][rwax+]*b[rwax+]*['"]""", line):
        return None
    if re.search(r"\b(os|io\.|urllib\.request|url|webbrowser|tarfile|zipfile|gzip)\.?open\(", line):
        return None
    return "low"


def check_subprocess_text(m, line):
    return None if "encoding=" in line else "low"


def check_allowed_tools(m, line):
    return "high" if re.search(r"Bash\(\s*\*\s*\)|\bBash\b(?!\()|\bWrite\b(?!\()|mcp__\*", line) else "medium"


def check_git_ref(m):
    return None if SHA40.match(m.group(1)) else "high"


# id, category, severity, pattern, path filter (regex or None), message, fix, check(match, line, path) -> sev|None
RULES = [
    ("SEC-01", "secret", "critical", r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----", None,
     "Private key block", "Revoke the key, remove the file and rewrite history before publishing.", None),
    ("SEC-02", "secret", "critical", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", None,
     "AWS access key id", "Deactivate the key in IAM, then rewrite history.", None),
    ("SEC-03", "secret", "critical", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})", None,
     "GitHub token", "Revoke the token on GitHub, then rewrite history.", None),
    ("SEC-04", "secret", "critical", r"\bsk-ant-[A-Za-z0-9_-]{20,}", None,
     "Anthropic API key", "Revoke the key in the Anthropic Console, then rewrite history.", None),
    ("SEC-05", "secret", "high", r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}\b", None,
     "OpenAI-style secret key", "Revoke the key with its provider, then rewrite history.", None),
    ("SEC-06", "secret", "critical", r"\bxox[abposr]-[A-Za-z0-9-]{10,}", None,
     "Slack token", "Revoke the token in Slack, then rewrite history.", None),
    ("SEC-07", "secret", "high", r"\bAIza[0-9A-Za-z_-]{35}\b", None,
     "Google API key", "Restrict or delete the key in Google Cloud, then rewrite history.", None),
    ("SEC-08", "secret", "critical", r"\b[sr]k_live_[0-9A-Za-z]{16,}", None,
     "Stripe live key", "Roll the key in Stripe, then rewrite history.", None),
    ("SEC-09", "secret", "high", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", None,
     "JSON Web Token", "Invalidate the token's session or signing key, then remove it.", None),
    ("SEC-10", "secret", "high", r"\b[a-z][a-z0-9+.-]*://([^\s/:@'\"<>]+):([^\s/@'\"<>]+)@", None,
     "Credentials inside a URL", "Read credentials from an environment variable; an example keeps "
     "obvious names only, such as user:pass.", lambda m, l, p: check_url_creds(m)),
    ("SEC-11", "secret", "high",
     r"(?i)\b[A-Za-z0-9_.-]*(?:api[_-]?key|secret|token|passw(?:or)?d|access[_-]?key|private[_-]?key"
     r"|client[_-]?secret)\b[\"']?\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']", None,
     "Literal value assigned to a secret-looking name", "Move the value to an environment variable "
     "or a git-ignored local file and reference it by name.", lambda m, l, p: secret_value(m.group(1))),
    ("SEC-12", "secret", "high", r"(?i)\b(?:bearer|basic)\s+([A-Za-z0-9._~+/=-]{20,})", None,
     "Literal Authorization header value", "Reference ${TOKEN_NAME} instead of the value.",
     lambda m, l, p: secret_value(m.group(1))),
    ("PII-01", "personal", "medium", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b",
     None, "Email address", "Use a noreply or example.com address; keep a real one only in a manifest "
     "that is meant to be public.", lambda m, l, p: check_email(m, l, p)),
    ("PII-02", "personal", "medium",
     r"\bclaude\.ai/(?:code/)?(?:session_[A-Za-z0-9]{6,}|chat/[0-9a-f-]{36}|share/[0-9a-f-]{36})", None,
     "Link to a claude.ai session or chat", "Delete the link; a session id is private context.", None),
    ("PII-04", "personal", "medium", r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:internal|corp|lan|intranet|local)\b"
     r"(?![.\w-])", None, "Internal host name", "Replace with an example.com host.", None),
    ("HOST-01", "host", "medium", r"(?<![\w}])(?:/home|/Users)/([A-Za-z0-9._-]+)", None,
     "Absolute home-folder path", "Write {{ PROJECT_ROOT }}, {{ SKILL_ROOT }} or {{ USER_ROOT }} instead.",
     lambda m, l, p: check_home(m)),
    ("HOST-02", "host", "medium", r"\b[A-Za-z]:(?:\\\\|\\|/)Users(?:\\\\|\\|/)([^\\/\s\"'`]+)", None,
     "Windows user-profile path", "Write {{ USER_ROOT }} or a project placeholder instead.",
     lambda m, l, p: check_home(m)),
    ("HOST-03", "host", "low", r"(?<![\w}])(?:\/root\/|\/mnt\/[a-z]\/|\/var\/folders\/|\/private\/var\/)", None,
     "Machine-specific system path", "Use a placeholder or tempfile.gettempdir().", None),
    ("HOST-04", "host", "low", r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}"
     r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b", None,
     "Private network address", "Use localhost or a documentation range such as 192.0.2.0/24.", None),
    ("HOST-05", "host", "low", r"[\"'](?:/tmp|/var/tmp)(?:/|[\"'])", PY,
     "Hard-coded Unix temp folder", "Use tempfile.gettempdir() or tempfile.mkdtemp().", None),
    ("HOST-06", "host", "low", r"(?<![\w.])open\(|\.(?:read|write)_text\(", PY,
     "Text file I/O without an explicit encoding", "Pass encoding=\"utf-8\" (and newline=\"\\n\" "
     "when writing).", lambda m, l, p: check_open(m, l)),
    ("HOST-07", "host", "low", r"\bsubprocess\.\w+\(.*\b(?:text|universal_newlines)=True", PY,
     "Subprocess text decoding uses the locale codec", "Add encoding=\"utf-8\", errors=\"replace\".",
     lambda m, l, p: check_subprocess_text(m, l)),
    ("PS-01", "component", "medium", r"^allowed-tools:", SKILL_MD,
     "Skill pre-approves tools with allowed-tools", "List exact, narrow commands or drop the field.",
     lambda m, l, p: check_allowed_tools(m, l)),
    ("PS-02", "component", "medium", r"(?:^|\s)!`[^`]+`", r"(^|/)(skills|commands|agents)/.*\.md$",
     "Skill shell injection runs before the model reads the file", "Remove it or keep it read-only "
     "with fixed arguments.", None),
    ("PS-03", "component", "medium", r"^hooks:", SKILL_MD + "|" + AGENT_MD,
     "Hooks declared in skill or agent frontmatter", "Ship hooks in hooks/hooks.json, documented, or not at all.",
     None),
    ("PS-04", "component", "medium", r"\bshell=True\b|\bos\.system\(|\beval\(|\bpickle\.loads?\(", PY,
     "Script runs shell strings or evaluates data", "Pass argument lists to subprocess and parse data "
     "with json.", None),
    ("PS-05", "component", "high", "[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\U000e0000-\U000e007f]",
     None, "Invisible or bidirectional Unicode character", "Delete the character; strip them in CI.", None),
    ("PS-05b", "component", "medium", r"(?i)ignore (?:all )?(?:previous|prior|above) instructions"
     r"|do not (?:tell|inform|mention to) the user|<IMPORTANT>", DOCS,
     "Prompt-injection phrasing", "Rewrite the text as a plain task instruction or delete it.", None),
    ("PS-07", "component", "low", r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:ba|z)?sh\b", None,
     "Pipe from the network into a shell", "Keep it only as a clearly marked Don't example.", None),
    ("PS-11", "component", "high", r"^permissionMode:", AGENT_MD,
     "Agent sets permissionMode", "Delete the key; never ship bypassPermissions.", None),
    ("PS-33", "component", "high", r"\"(?:defaultMode|skipDangerousModePermissionPrompt)\"|bypassPermissions",
     JSONISH, "Committed permission mode or bypass", "Delete it; set modes in user settings only.", None),
    ("PS-36", "component", "high", r"ANTHROPIC_(?:BASE_URL|API_KEY|AUTH_TOKEN)", JSONISH,
     "Endpoint or credential variable in committed config", "Delete it; set it in the user's environment.",
     None),
    ("PS-37", "component", "high", r"\"(?:apiKeyHelper|awsAuthRefresh|awsCredentialExport|otelHeadersHelper"
     r"|headersHelper)\"", JSONISH, "Helper command in committed config runs shell",
     "Delete it; keep helpers in user settings.", None),
    ("PS-37b", "component", "medium", r"^\s*\"env\"\s*:", r"(^|/)settings[^/]*\.json$",
     "env block in committed settings", "Move variables to user settings or document each one.", None),
    ("PS-38", "component", "high", r"enableAllProjectMcpServers|enabledMcpjsonServers", JSONISH,
     "Committed auto-approval of project MCP servers", "Delete it; let each user approve servers.", None),
    ("PS-22", "component", "high", r"git\+https?://[^\"\s#]*@([^\"#\s]+)", JSONISH + r"|\.mcp\.json$",
     "Server installs from a git tag or branch, which can move", "Pin the full 40-character commit SHA.",
     lambda m, l, p: check_git_ref(m)),
    ("PS-22b", "component", "high", r"@latest\b", SETTINGS, "Unpinned @latest package in a launch command",
     "Pin an exact version or hash.", None),
    ("PS-22c", "component", "medium", r"\"(?:npx|uvx|bunx|pipx)\"", SETTINGS,
     "Server launched through a package runner", "Pin an exact version or commit in its arguments.", None),
    ("PS-25", "component", "medium", r"\"ref\"\s*:", r"(^|/)marketplace\.json$",
     "Marketplace entry tracks a branch or tag", "Pin a sha for the stable entry, or protect the branch.",
     None),
    ("PS-28", "component", "high", r"\"source\"\s*:\s*\"(?:command|archive|npm)\"", r"(^|/)marketplace\.json$",
     "Marketplace source that runs a command or downloads unpinned code", "Use a relative or github "
     "source with sha.", None),
    ("PS-29", "component", "medium", r"\"\.\./", r"(^|/)(marketplace|plugin)\.json$",
     "Path escapes the plugin folder", "Keep every path inside the plugin.", None),
    ("PS-14", "component", "high", r"\"command\"\s*:\s*\"[^\"]*\b(?:curl|wget|nc|base64|eval)\b",
     SETTINGS, "Hook or server command uses network or eval", "Keep hook commands local, fixed and short.",
     None),
    ("PS-42", "component", "medium", r"^\s*@(?:/|~|\.\./)", r"(^|/)CLAUDE(\.local)?\.md$|(^|/)\.claude/rules/",
     "CLAUDE.md imports a file outside the repository", "Import only paths inside the repository.", None),
]
COMPILED = [(r[0], r[1], r[2], re.compile(r[3], re.M), re.compile(r[4]) if r[4] else None, r[5], r[6], r[7])
            for r in RULES]

# id, category, severity, path pattern, message, fix
PATH_RULES = [
    ("SEC-20", "secret", "high", r"(^|/)\.env(\.(?!example$|sample$|template$|dist$)[^/]+)?$",
     "Environment file committed", "Delete it, rotate its values, ignore .env* and rewrite history."),
    ("SEC-21", "secret", "high", r"\.(pem|key|p12|pfx|jks|keystore|ppk)$|(^|/)id_(rsa|dsa|ecdsa|ed25519)$"
     r"|(^|/)(\.netrc|\.npmrc|\.pypirc|credentials(\.json)?)$",
     "Key, keystore or credentials file committed", "Delete it, rotate it and rewrite history."),
    ("PS-39", "component", "high", r"(^|/)\.claude/settings\.local\.json$",
     "Local Claude settings committed", "Delete it, ignore **/.claude/settings.local.json, rewrite history."),
    ("PS-43", "component", "medium", r"(^|/)CLAUDE\.local\.md$",
     "Personal CLAUDE.local.md committed", "Delete it and ignore CLAUDE.local.md."),
    ("PS-47", "component", "medium", r"\.jsonl$|\.log$|(^|/)\.agentville/topics/[^/]+/(evidence|[^/]+/(artefacts|scratch))/|(^|/)\.claude/projects/",
     "Agent workspace, transcript or log committed", "Delete it and ignore the folder."),
    ("PS-35", "component", "high", r"(^|/)\.git$", "A .git file is tracked", "Delete it."),
    ("PS-30", "component", "info", r"(^|/)plugins/[^/]+/(package\.json|package-lock\.json|bun\.lockb?)$",
     "Plugin installs package dependencies", "Avoid dependencies or audit the lockfile."),
    ("PS-19", "component", "info", r"(^|/)\.mcp\.json$",
     "MCP server configuration ships", "List every shipped server and its launch command in the README."),
    ("HOST-10", "host", "low", r"(^|/)(\.DS_Store|Thumbs\.db|desktop\.ini)$",
     "Operating-system metadata file committed", "Delete it and ignore it."),
]
PATH_COMPILED = [(r[0], r[1], r[2], re.compile(r[3]), r[4], r[5]) for r in PATH_RULES]

META = {
    "PS-52": ("personal", "medium", "Claude-Session trailer in a commit message",
              "Stop adding the trailer; strip it with git filter-repo --message-callback before publishing."),
    "PS-52b": ("personal", "info", "Co-Authored-By trailer in a commit message", "Allowed; no action."),
    "PS-51": ("personal", "low", "Author or committer email that is not a noreply address",
              "Commit with the GitHub noreply address; rewrite with a mailmap if it must stay private."),
    "PS-51b": ("personal", "info", "Noreply author or committer identity", "No action."),
    "PS-48": ("component", "info", "Ref not merged into HEAD goes public too",
              "Review the ref, or delete it before the repository turns public."),
    "PS-48b": ("component", "info", "Stash entry (local only, never pushed)", "Drop it when no longer needed."),
    "PS-53": ("component", "info", "Lightweight tag (no tagger, no signature)", "Create annotated, signed tags."),
    "PS-09": ("component", "medium", "Agent file has no tools allowlist, so it inherits every tool",
              "Write an explicit tools: line."),
    "PS-10": ("component", "info", "Agent holds the Agent tool", "Confirm it is the main agent; children "
              "hand back a spawn request instead."),
    "PS-06": ("component", "medium", "Side-effecting skill lacks disable-model-invocation: true",
              "Set the field, or confirm the skill only forbids the action."),
    "PS-45": ("component", "medium", "Sensitive file name is not git-ignored", "Add the pattern to .gitignore."),
    "PS-29b": ("component", "medium", "Symlink tracked", "Replace it with a real file inside the repository."),
}


class ScanError(Exception):
    pass


def git(repo, *args, check=True, data=None):
    r = subprocess.run(["git", "-C", str(repo), "-c", "core.quotePath=false", *args], input=data,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and r.returncode != 0:
        raise ScanError("git %s: %s" % (args[0], r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout.decode("utf-8", "replace")


def short_ref(ref):
    for pre, rep in (("refs/heads/", ""), ("refs/remotes/", ""), ("refs/tags/", "tag:")):
        if ref.startswith(pre):
            return rep + ref[len(pre):]
    return ref


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:10]


class Scan:
    def __init__(self, args):
        self.args = args
        self.repo = Path(args.repo).resolve()
        self.findings = {}
        self.stats = {}
        self.tools = []

    def add(self, rule, cat, sev, msg, fix, where, loc, fp, detail=""):
        key = (rule, fp)
        f = self.findings.get(key)
        if f is None:
            f = self.findings[key] = {"rule": rule, "category": cat, "severity": sev, "where": where,
                                      "message": msg, "fix": fix, "locations": [], "detail": detail}
        if RANK[sev] > RANK[f["severity"]]:
            f["severity"] = sev
        if where == "tip" and f["where"] != "tip":
            f["where"], f["locations"] = "tip", []
        if where == f["where"] and loc not in f["locations"]:
            f["locations"].append(loc)

    def refs(self):
        out = git(self.repo, "for-each-ref", "--format=%(refname)%00%(objecttype)%00%(*objecttype)")
        refs = []
        for line in out.splitlines():
            name, otype, peeled = (line.split("\0") + ["", ""])[:3]
            if name.endswith("/HEAD") or name == "refs/stash":
                continue
            if self.args.refs != "all" and short_ref(name) not in self.args.refs and name not in self.args.refs:
                continue
            refs.append(name)
            if name.startswith("refs/tags/") and otype == "commit":
                self.add("PS-53", *META["PS-53"][:2], *META["PS-53"][2:], "refs", short_ref(name), name)
        if not refs:
            raise ScanError("no refs match --refs %s" % ",".join(self.args.refs))
        stash = [] if self.args.refs != "all" else git(self.repo, "stash", "list", "--format=%H").split()
        for i, sha in enumerate(stash):
            self.add("PS-48b", *META["PS-48b"][:2], *META["PS-48b"][2:], "refs", "stash@{%d} %s" % (i, sha[:12]),
                     sha)
        head = git(self.repo, "rev-parse", "-q", "--verify", "HEAD", check=False).strip()
        if head:
            unmerged = git(self.repo, "for-each-ref", "--no-merged", "HEAD", "--format=%(refname)").split()
            for name in unmerged:
                if name in refs:
                    self.add("PS-48", *META["PS-48"][:2], *META["PS-48"][2:], "refs", short_ref(name), name)
        kinds = {"branches": "refs/heads/", "remote": "refs/remotes/", "tags": "refs/tags/"}
        self.stats["refs"] = {k: sum(r.startswith(p) for r in refs) for k, p in kinds.items()}
        self.stats["refs"]["other"] = len(refs) - sum(self.stats["refs"].values())
        self.stats["stash"] = len(stash)
        return refs, stash

    def tips(self, refs):
        tip = {}
        for ref in refs:
            out = git(self.repo, "ls-tree", "-r", "-z", "--full-tree", ref, check=False)
            for entry in out.split("\0"):
                if "\t" not in entry:
                    continue
                meta, path = entry.split("\t", 1)
                mode, otype, sha = meta.split()
                if mode == "120000":
                    self.add("PS-29b", *META["PS-29b"][:2], *META["PS-29b"][2:], "tip",
                             "%s @ %s" % (path, short_ref(ref)), path)
                if otype == "blob":
                    tip.setdefault(sha, []).append((short_ref(ref), path))
        return tip

    def history(self, revs):
        first = {}
        out = git(self.repo, "log", *revs, "--no-renames", "--raw", "--no-abbrev", "--format=%x00%H")
        commit = None
        for line in out.splitlines():
            if line.startswith("\0"):
                commit = line[1:]
            elif line.startswith(":") and "\t" in line:
                meta, path = line.split("\t", 1)
                parts = meta.split()
                if len(parts) >= 4 and parts[3] != ZERO:
                    first[parts[3]] = (commit, path.strip('"'))
        objs = git(self.repo, "rev-list", "--objects", *revs)
        extra = {}
        for line in objs.splitlines():
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[0] not in first:
                extra[parts[0]] = parts[1]
        if extra:
            check = git(self.repo, "cat-file", "--batch-check", data="\n".join(extra).encode() + b"\n")
            for line in check.splitlines():
                p = line.split()
                if len(p) >= 2 and p[1] == "blob":
                    first[p[0]] = (None, extra[p[0]])
        self.stats["commits"] = int(git(self.repo, "rev-list", "--count", *revs).strip() or 0)
        return first

    def read_blobs(self, shas):
        """Yield (sha, text) for each text blob within --max-bytes; binaries and large files are skipped."""
        if not shas:
            return
        sizes = {}
        check = git(self.repo, "cat-file", "--batch-check", data="\n".join(shas).encode() + b"\n")
        for line in check.splitlines():
            p = line.split()
            if len(p) == 3 and p[1] == "blob":
                sizes[p[0]] = int(p[2])
        wanted = [s for s in shas if 0 < sizes.get(s, 0) <= self.args.max_bytes]
        self.stats["skipped-large"] = sum(1 for s in shas if sizes.get(s, 0) > self.args.max_bytes)
        proc = subprocess.Popen(["git", "-C", str(self.repo), "cat-file", "--batch"], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        binary = 0
        try:
            for sha in wanted:
                proc.stdin.write(sha.encode() + b"\n")
                proc.stdin.flush()
                header = proc.stdout.readline().split()
                size = int(header[2])
                data = proc.stdout.read(size)
                proc.stdout.read(1)
                if b"\0" in data[:8000]:
                    binary += 1
                    continue
                yield sha, data.decode("utf-8", "replace")
        finally:
            proc.stdin.close()
            proc.wait()
        self.stats["skipped-binary"] = binary

    def locate(self, sha, first, tip, line_no):
        if sha in tip:
            groups = {}
            for ref, path in tip[sha]:
                groups.setdefault(path, []).append(ref)
            return "tip", ["%s:%d @ %s" % (p, line_no, ", ".join(r[:4]) + (" (+%d refs)" % (len(r) - 4)
                                                                       if len(r) > 4 else ""))
                           for p, r in sorted(groups.items())]
        commit, path = first.get(sha, (None, "?"))
        if commit is None:
            hit = git(self.repo, "log", "--all", "-m", "--format=%H", "--find-object=" + sha, check=False).split()
            commit = hit[-1] if hit else "unknown"
        return "history", ["%s %s:%d" % (commit[:12], path, line_no)]

    def scan_content(self, first, tip):
        paths = {}
        for sha, locs in tip.items():
            paths.setdefault(sha, set()).update(p for _, p in locs)
        for sha, (_, p) in first.items():
            paths.setdefault(sha, set()).add(p)
        for sha, p_set in paths.items():
            for p in p_set:
                for rid, cat, sev, rx, msg, fix in PATH_COMPILED:
                    if rx.search(p):
                        where = "tip" if sha in tip and any(q == p for _, q in tip[sha]) else "history"
                        loc = p if where == "tip" else "%s %s" % (((first.get(sha) or ("?",))[0] or "?")[:12], p)
                        self.add(rid, cat, sev, msg, fix, where, loc[:200], fingerprint(p))
        terms = [re.compile(r"(?i)\b%s\b" % re.escape(t)) for t in self.args.term]
        count = 0
        for sha, text in self.read_blobs(sorted(paths)):
            count += 1
            p_set = paths[sha]
            any_path = sorted(p_set)[0]
            if re.search(r"\.(lock|min\.js|map|svg)$|(^|/)package-lock\.json$", any_path):
                continue
            for n, line in enumerate(text.splitlines(), 1):
                for rid, cat, sev, rx, prx, msg, fix, chk in COMPILED:
                    if prx and not any(prx.search(p) for p in p_set):
                        continue
                    for m in rx.finditer(line):
                        s = chk(m, line, any_path) if chk else sev
                        if s is None:
                            continue
                        where, locs = self.locate(sha, first, tip, n)
                        detail = ("redacted, %d chars, sha256 %s" % (len(m.group(0)), fingerprint(m.group(0)))
                                  if cat == "secret" else line.strip()[:120])
                        fp = fingerprint(m.group(0))
                        for loc in locs:
                            self.add(rid, cat, s, msg, fix, where, loc, fp, detail)
                for t in terms:
                    if t.search(line):
                        where, locs = self.locate(sha, first, tip, n)
                        for loc in locs:
                            self.add("PII-03", "personal", "medium", "Project-specific or personal term '%s'"
                                     % t.pattern[6:-2].replace("\\", ""), "Replace it with the Acme example.",
                                     where, loc, fingerprint(t.pattern), line.strip()[:120])
            if sha in tip:
                self.structure(sha, text, tip)
        self.stats["blobs"] = count

    def structure(self, sha, text, tip):
        fm = re.match(r"^---\n(.*?)\n---", text, re.S)
        front = fm.group(1) if fm else ""
        for ref, path in tip[sha][:1]:
            loc = "%s @ %s" % (path, ", ".join(r for r, p in tip[sha] if p == path)[:120])
            if re.search(AGENT_MD, path) and fm:
                if not re.search(r"^tools:", front, re.M):
                    self.add("PS-09", *META["PS-09"][:2], *META["PS-09"][2:], "tip", loc, path)
                elif re.search(r"^tools:.*\bAgent\b", front, re.M):
                    self.add("PS-10", *META["PS-10"][:2], *META["PS-10"][2:], "tip", loc, path)
            if re.search(SKILL_MD, path) and "disable-model-invocation: true" not in front:
                if re.search(r"\bgit (?:push|tag|merge|branch -D)\b|\bgh release\b|\bnpm publish\b", text):
                    self.add("PS-06", *META["PS-06"][:2], *META["PS-06"][2:], "tip", loc, path)

    def metadata(self, revs):
        out = git(self.repo, "log", *revs, "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e")
        idents, session, coauth, trailers = {}, [], 0, 0
        for rec in out.split("\x1e"):
            parts = rec.strip("\n").split("\x1f")
            if len(parts) < 6:
                continue
            sha, an, ae, cn, ce, body = parts
            for name, mail in ((an, ae), (cn, ce)):
                idents.setdefault((name, mail), []).append(sha)
            for t in self.args.term:
                if re.search(r"(?i)\b%s\b" % re.escape(t), "\n".join((an, ae, cn, ce, body))):
                    self.add("PII-03", "personal", "medium", "Project-specific or personal term '%s' (commit "
                             "metadata)" % t, "Rewrite the identity or message with a mailmap or "
                             "git filter-repo if it must not ship.", "commits", sha[:12], "term-" + t)
            hits = len(re.findall(r"(?mi)^Claude-Session:", body))
            if hits:
                session.append(sha)
                trailers += hits
            coauth += len(re.findall(r"(?mi)^Co-Authored-By:", body))
            for n, line in enumerate(body.splitlines(), 1):
                for rid, cat, sev, rx, prx, msg, fix, chk in COMPILED:
                    if prx or cat not in ("secret", "personal", "host") or rid == "PII-01":
                        continue
                    for m in rx.finditer(line):
                        s = chk(m, line, None) if chk else sev
                        if s is None:
                            continue
                        detail = ("redacted, %d chars, sha256 %s" % (len(m.group(0)), fingerprint(m.group(0)))
                                  if cat == "secret" else "")
                        fp = fingerprint(m.group(0)) if cat == "secret" else rid
                        self.add(rid, cat, s, msg + " (commit message)", fix, "commits",
                                 "%s message line %d" % (sha[:12], n), fp, detail)
        for (name, mail), shas in sorted(idents.items()):
            rid = "PS-51b" if SAFE_MAIL.search(mail) else "PS-51"
            cat, sev, msg, fix = META[rid]
            self.add(rid, cat, sev, msg, fix, "commits", "%s <%s> in %d commits" % (name, mail, len(set(shas))),
                     fingerprint(name + mail))
        if session:
            cat, sev, msg, fix = META["PS-52"]
            self.add("PS-52", cat, sev, msg, fix, "commits", "%d trailer lines in %d commits, oldest %s" % (
                trailers, len(set(session)), ", ".join(s[:12] for s in reversed(session[-3:]))), "trailer")
        if coauth:
            cat, sev, msg, fix = META["PS-52b"]
            self.add("PS-52b", cat, sev, msg, fix, "commits", "%d trailers" % coauth, "coauthor")

    def ignore_check(self):
        if git(self.repo, "rev-parse", "--is-bare-repository", check=False).strip() == "true":
            return
        for probe in (".claude/settings.local.json", "CLAUDE.local.md", ".env", ".agentville/topics/x/evidence/x",
                      ".agentville/topics/x/worker/artefacts/x", ".agentville/topics/x/worker/scratch/x", "x.pem", "x.key"):
            r = subprocess.run(["git", "-C", str(self.repo), "check-ignore", "-q", "--no-index", probe],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if r.returncode == 1:
                cat, sev, msg, fix = META["PS-45"]
                self.add("PS-45", cat, sev, msg, fix, "tip", "%s (working tree .gitignore)" % probe, probe)

    def external(self):
        if self.args.external == "off":
            return
        tmp = Path(tempfile.mkdtemp(prefix="plugin-security-"))
        try:
            if shutil.which("gitleaks"):
                report = tmp / "gitleaks.json"
                for cmd in (["gitleaks", "git", "--redact", "--no-banner", "--log-opts=--all", "--report-format",
                             "json", "--report-path", str(report), str(self.repo)],
                            ["gitleaks", "detect", "--source", str(self.repo), "--redact", "--no-banner",
                             "--log-opts=--all", "--report-format", "json", "--report-path", str(report)]):
                    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if r.returncode in (0, 1) and report.exists():
                        break
                items = json.loads(report.read_text(encoding="utf-8") or "[]") if report.exists() else []
                self.tools.append("gitleaks (%d hits)" % len(items))
                for it in items:
                    loc = "%s %s:%s" % (str(it.get("Commit", "?"))[:12], it.get("File", "?"), it.get("StartLine", "?"))
                    self.add("EXT-gitleaks:" + str(it.get("RuleID", "?")), "secret", "high",
                             "gitleaks: " + str(it.get("Description", "secret")), "Rotate it, then rewrite history.",
                             "history", loc, str(it.get("Fingerprint", loc)), "redacted by gitleaks")
            if shutil.which("trufflehog"):
                r = subprocess.run(["trufflehog", "git", "file://" + self.repo.as_posix(), "--json", "--no-update"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                n = 0
                for line in r.stdout.decode("utf-8", "replace").splitlines():
                    try:
                        it = json.loads(line)
                    except ValueError:
                        continue
                    n += 1
                    g = it.get("SourceMetadata", {}).get("Data", {}).get("Git", {})
                    loc = "%s %s:%s" % (str(g.get("commit", "?"))[:12], g.get("file", "?"), g.get("line", "?"))
                    sev = "critical" if it.get("Verified") else "high"
                    self.add("EXT-trufflehog:" + str(it.get("DetectorName", "?")), "secret", sev,
                             "trufflehog: %s%s" % (it.get("DetectorName", "secret"), " (verified live)"
                                                   if it.get("Verified") else ""),
                             "Rotate it, then rewrite history.", "history", loc, fingerprint(loc), "redacted")
                self.tools.append("trufflehog (%d hits)" % n)
        except (OSError, ValueError) as e:
            self.tools.append("external scanner error: %s" % e)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if not self.tools:
            self.tools.append("none found (gitleaks, trufflehog)")

    def accepted(self, f):
        for spec in self.args.accept:
            rule, _, glob = spec.partition(":")
            if fnmatch.fnmatch(f["rule"], rule) and all(
                    fnmatch.fnmatch(re.split(r"[: @]", loc.split(" ", 1)[-1] if f["where"] == "history" else loc)[0],
                                    glob or "*") for loc in f["locations"]):
                return True
        return False

    def run(self):
        if git(self.repo, "rev-parse", "--git-dir", check=False).strip() == "":
            raise ScanError("%s is not a git repository" % self.repo)
        refs, stash = self.refs()
        revs = ["--all"] + stash if self.args.refs == "all" else refs
        tip = self.tips(refs)
        first = self.history(revs)
        self.scan_content(first, tip)
        self.metadata(revs)
        self.ignore_check()
        self.external()
        out = sorted(self.findings.values(), key=lambda f: (-RANK[f["severity"]], f["category"], f["rule"]))
        for f in out:
            f["accepted"] = self.accepted(f)
        return out


def render_text(scan, findings, gate):
    s = scan.stats
    counts = {k: sum(1 for f in findings if f["severity"] == k and not f["accepted"]) for k in SEVERITIES}
    lines = ["plugin-security scan", "repo: %s" % scan.repo,
             "refs: %d branches, %d remote-tracking, %d tags, %d other, %d stash" % (
                 s["refs"]["branches"], s["refs"]["remote"], s["refs"]["tags"], s["refs"]["other"], s["stash"]),
             "commits: %d, text blobs scanned: %d, skipped binary: %d, skipped large: %d" % (
                 s.get("commits", 0), s.get("blobs", 0), s.get("skipped-binary", 0), s.get("skipped-large", 0)),
             "external: %s" % "; ".join(scan.tools),
             "findings: " + ", ".join("%s %d" % (k, counts[k]) for k in reversed(SEVERITIES)) +
             " (accepted %d)" % sum(f["accepted"] for f in findings),
             "gate: %s (fail-on %s)" % (gate, scan.args.fail_on), ""]
    for f in findings:
        mark = " accepted" if f["accepted"] else ""
        lines.append("[%s] %s %s %s%s  %s" % (f["severity"].upper(), f["category"], f["rule"], f["where"], mark,
                                             f["message"]))
        shown = f["locations"][:5]
        for loc in shown:
            lines.append("  at: " + loc)
        if len(f["locations"]) > 5:
            lines.append("  at: (+%d more)" % (len(f["locations"]) - 5))
        if f["detail"]:
            lines.append("  value: " + f["detail"] if f["category"] == "secret" else "  line: " + f["detail"])
        lines.append("  fix: " + f["fix"])
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description="Read-only security scan of a plugin repository's refs and history.")
    p.add_argument("--repo", default=".")
    p.add_argument("--refs", default="all", help="all, or a comma list such as main,origin/beta,tag:1.0.0")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--out", help="also write the report to this file (UTF-8)")
    p.add_argument("--term", action="append", default=[], help="project or personal word to flag; repeatable")
    p.add_argument("--accept", action="append", default=[], help="RULE:GLOB accepted risk, e.g. PII-01:*plugin.json")
    p.add_argument("--fail-on", choices=SEVERITIES, default="high")
    p.add_argument("--external", choices=["auto", "off"], default="auto")
    p.add_argument("--max-bytes", type=int, default=2000000)
    p.add_argument("--list-rules", action="store_true")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.list_rules:
        for r in RULES:
            print("%s\t%s\t%s\t%s" % (r[0], r[1], r[2], r[5]))
        for r in PATH_RULES:
            print("%s\t%s\t%s\t%s (path)" % (r[0], r[1], r[2], r[4]))
        for k, v in META.items():
            print("%s\t%s\t%s\t%s" % (k, v[0], v[1], v[2]))
        return 0
    if args.refs != "all":
        args.refs = [r.strip().replace("tag:", "refs/tags/") if r.strip().startswith("tag:") else r.strip()
                     for r in args.refs.split(",") if r.strip()]
    if not shutil.which("git"):
        print("error: git is not on PATH", file=sys.stderr)
        return 2
    scan = Scan(args)
    try:
        findings = scan.run()
    except ScanError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    open_hits = [f for f in findings if not f["accepted"] and RANK[f["severity"]] >= RANK[args.fail_on]]
    gate = "fail" if open_hits else "pass"
    if args.format == "json":
        text = json.dumps({"repo": str(scan.repo), "stats": scan.stats, "external": scan.tools, "gate": gate,
                           "findings": findings}, indent=2) + "\n"
    else:
        text = render_text(scan, findings, gate)
    sys.stdout.write(text)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return 1 if open_hits else 0


if __name__ == "__main__":
    sys.exit(main())
