#!/usr/bin/env python3
"""Measure a SKILL.md against the script-checked rules of references/validate-rules.md.

Usage: measure.py <path-to-SKILL.md>
Prints key: value lines; the last is failures: <rule numbers or none>.
Output rules follow relay section 4: the first Output fence holds the six report tags, the last is the failure template.
For a process skill it also checks every references/workflows/*.md file as a part.
Exit: 0 no failures (warnings allowed), 1 rule failures, 2 usage or read error.
Stdlib only; runs under python3 -I.
"""
import os
import re
import sys

FENCE_RE = re.compile(r"^\s*(`{3,})(.*)$")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
BULLET_RE = re.compile(r"^\s*[*-]\s+")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
SLOT = r"\[\[[^\]]+\]\]"
NAME = r"(?:[a-z0-9][a-z0-9-]*|" + SLOT + r")"
INPUT_RE = re.compile(r"^\* \*\*(" + NAME + r"):\*\* (required|optional) - default: (.+?) - (.+)$")
RETURN_RE = re.compile(r"^\* \*\*(" + NAME + r"):\*\* (always|when .+?) - (.+)$")
STEP_RE = re.compile(r"^(\d+)\.\s+(.+)$")
# Relay section 4 output: six flat tags, in this order, each opened and closed, no attributes.
TAGS = ("status", "outcome", "claims", "artefacts", "open", "deviations")
TAG_TOKEN_RE = re.compile(r"<(/?)(" + "|".join(TAGS) + r")(\s[^>]*)?>")
FIELD_TAG_RE = re.compile(r"<(?:" + "|".join(TAGS) + r")>")
STATUS_LINE_RE = re.compile(r"^<status>\s*(?:partial \| )?blocked \| needs-input \| (?:rejected \| )?failed\s*</status>$")
MISSING_RE = re.compile(r"<open>\s*missing:")
LEGACY_OUT_RE = re.compile(r"^(?:status|user-message):")
LEGACY_RE = re.compile(
    r"^\s*(?:[*-]\s+)?\**\s*(Start\s+here:|@(?:Tool|Skill|Process|Return|ThrowError|MCP|Import)\b)")
XML_SCOPE_RE = re.compile(r"^\s*<[a-z][\w-]*\s+scope=")
XML_TAG_RE = re.compile(r"^\s*</?(process|trigger|output)\b[^>]*>")
LABEL_RE = re.compile(r"^\s*[*-]\s+(?:\*\*)?(Action|Tool|Query|Extract):")
LEGACY_H1 = {"Workflows", "Dependencies", "Exceptions", "Rules"}
PROCESS_H1 = ["Role", "Constraints", "Input", "Process", "Output"]
PART_H1 = ["Input", "Process", "Output"]
BANNED_TITLES = {"overview", "details", "misc", "introduction", "notes", "summary"}
HOST_RE = re.compile(r"(?<![\w}])(/home/|/Users/|/tmp/|[A-Za-z]:\\)")
MD_LINK_RE = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)\)")
ROOT_PATH_RE = re.compile(r"\{\{ SKILL_ROOT \}\}/([^\s`'\")]+)")
MENTION_RE = re.compile(r"(?<![\w/.{}<\[])/[a-z][a-z0-9-]+(?![\w/.>\]])")
STEP_REF_RE = re.compile(r"(SKILL\.md\s+)?\bsteps?\s+(\d+(?:\s*(?:,|and|or|to|-|–)\s*\d+)*)", re.I)
MAX_LINES = 500
# Rule 20, independence. A skill never names what invokes it.
INDEP_TOKENS = ["caller", "calling agent", "calling skill", "invoker", "invoked by", "orchestrator",
                "parent agent", "parent skill", "root agent", "main thread", "top-level",
                "another skill call", "another skill invokes", "in a subagent", "runs in a subagent",
                "inside another agent", "Siblings:"]
INDEP_RE = re.compile("|".join(r"\b" + re.escape(t) + (r"s?\b" if t.isalpha() else "")
                               if t[-1].isalpha() else re.escape(t) for t in INDEP_TOKENS), re.I)
INDEP_NAMED_RE = re.compile(
    r"\bcalled\s+by\b|\binvoked\s+by\b|\bthat\s+`?Skill\(.*?\bcalls\b"
    r"|\b(?:used|run|triggered)\s+by\s+(?:the\s+|a\s+|an\s+)?(?:`?Skill\(|`?/[\w:-]+|`?[\w:-]+`?\s+skill\b)", re.I)
# Exemption: only skill-smith's own files, which quote the banned tokens on purpose. Documented in
# references/validate-rules.md under Rule 20. Applies only when the frontmatter name is skill-smith.
INDEP_ALLOWLIST = {"references/validate-rules.md", "scripts/measure.py", "scripts/test_scripts.py"}
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
# Rule 22, injectable slots.
SLOTS = ("workspace", "toolbelt", "draft", "plan", "report")  # injectable slots; add a future slot here only
CI_CALL = "Skill(agentville:context-injection)"
SLOT_ALT = "|".join(SLOTS)
# A direct use of a slot's default: Skill(agentville:<slot>), Skill(<slot>), /agentville:<slot> or a bare agentville:<slot>.
SLOT_CALL_RE = re.compile(r"Skill\((?:agentville:)?(" + SLOT_ALT + r")\)|(?<![\w:-])/?agentville:(" + SLOT_ALT + r")(?![\w-])")
SLOT_USE_RE = re.compile(r"`(" + SLOT_ALT + r")` (?:slot|skill)\b")
# Exempt a hit only when the text reads exactly as a description of the default or as a slot record:
#   * "the plugin default" right before it, with at most backticks or spaces between (the plugin default `Skill(agentville:<slot>)`);
#   * the call right before "(plugin-default)", with at most backticks or a space between;
#   * a record "<slot>: <ns>:<name> (<source>)" with <source> in SLOT_SOURCES, written without Skill( or a slash.
# A hit that merely shares a line with these words, or carries another parenthesis, is a direct call.
# A hit preceded by an imperative verb (call, load, run, invoke or use), with at most backticks, spaces or
# "the plugin default" between, is a direct call even when "(plugin-default)" follows it.
SLOT_SOURCES = ("plugin-default", "project-rules", "project-claude-md", "project-skill", "user-rules", "user-claude-md", "user-skill")
PLUGIN_DEFAULT_BEFORE_RE = re.compile(r"the plugin default[`\s]*$")
PLUGIN_DEFAULT_AFTER_RE = re.compile(r"`*\s?\(plugin-default\)")
IMPERATIVE_BEFORE_RE = re.compile(r"(?i)\b(?:call|load|run|invoke|use)\b[`\s]*(?:the plugin default[`\s]*)?$")
RECORD_AFTER_RE = re.compile(r"\s\((?:" + "|".join(SLOT_SOURCES) + r")\)")


def slot_default_described(line, m):
    """True when the hit only describes the plugin default or stands as the skill id of a slot record."""
    before, after = line[:m.start()], line[m.end():]
    if IMPERATIVE_BEFORE_RE.search(before):
        return False
    if PLUGIN_DEFAULT_BEFORE_RE.search(before) or PLUGIN_DEFAULT_AFTER_RE.match(after):
        return True
    slot = m.group(1) or m.group(2)
    bare = bool(m.group(2)) and not m.group(0).startswith("/")
    return bare and bool(re.search(r"(?<![\w-])" + slot + r":\s+$", before)) and bool(RECORD_AFTER_RE.match(after))


def reference_lines(folder, name):
    """(relative path, lines) for each Markdown file under references/, minus skill-smith's own quoting files."""
    found = []
    base = os.path.join(folder, "references")
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, folder).replace(os.sep, "/")
            if name == "skill-smith" and rel in INDEP_ALLOWLIST:
                continue
            try:
                with open(full, encoding="utf-8") as f:
                    found.append((rel, f.read().splitlines()))
            except (OSError, UnicodeError):
                continue
    return found


def slot_hits(lines, exempt=False, extra=()):
    """Slot rule: a file that uses an injectable slot names CI_CALL and never calls Skill(agentville:<slot>) itself.
    `extra` holds (relative path, lines) pairs for the skill's reference files, which are scanned the same way."""
    if exempt:
        return [], []
    sets = [("", lines)] + [(rel + ":", ls) for rel, ls in extra]
    direct = [f"{pre}{i + 1}:{m.group(0)}" for pre, ls in sets for i, l in enumerate(ls)
              for m in SLOT_CALL_RE.finditer(l) if not slot_default_described(l, m)]
    used = sorted({m.group(1) for _, ls in sets for l in ls for m in SLOT_USE_RE.finditer(l)})
    every = "\n".join("\n".join(ls) for _, ls in sets)
    return direct, ([] if CI_CALL in every else used)


def independence_hits(folder, name, doc, lines, desc, kind):
    """Return 'path:line | token' for each banned token in any text file, plus invoker-naming in the
    description or Role."""
    hits = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for fn in sorted(files):
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, folder).replace(os.sep, "/")
            if name == "skill-smith" and rel in INDEP_ALLOWLIST:
                continue
            try:
                with open(full, encoding="utf-8") as f:
                    text = f.read()
            except (OSError, UnicodeError):
                continue
            for n, line in enumerate(text.splitlines(), 1):
                for m in INDEP_RE.finditer(line):
                    hits.append(f"{rel}:{n} | {m.group(0)}")
    skill_md = [i for i, l in enumerate(lines, 1) if re.match(r"^description:", l)]
    dline = skill_md[0] if skill_md else 1
    for m in INDEP_NAMED_RE.finditer(desc):
        hits.append(f"SKILL.md:{dline} | description: {m.group(0)}")
    if kind == "process":
        b = section_bounds(doc, PROCESS_H1)[1]
        if "Role" in b:
            for i, line, _ in doc.plain(*b["Role"]):
                for m in INDEP_NAMED_RE.finditer(line):
                    hits.append(f"SKILL.md:{i + 1} | role: {m.group(0)}")
    return list(dict.fromkeys(hits))


def die(msg, code=2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def read(path):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    except (OSError, UnicodeError) as e:
        die(f"cannot read {path}: {e}")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def parse_frontmatter(lines):
    """Return (ordered keys, values, nested flag, index of first body line)."""
    if not lines or lines[0].strip() != "---":
        die("no frontmatter: file must start with ---")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        die("unterminated frontmatter")
    keys, vals, nested, key, block = [], {}, False, None, False
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0] not in " \t":
            m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
            if not m:
                continue
            key, val = m.group(1), m.group(2)
            block = val.strip() in (">", "|", ">-", "|-")
            keys.append(key)
            vals[key] = "" if block or not val.strip() else val
        elif key and (block or vals[key]):
            vals[key] = (vals[key] + " " + raw.strip()).strip()
        elif key == "metadata" and re.match(r"^[ \t]+version:\s*\S", raw) and "metadata.version" not in vals:
            vals["metadata.version"] = raw.split(":", 1)[1].strip()
        else:
            nested = True
    return keys, {k: unquote(v) for k, v in vals.items()}, nested, end + 1


class Doc:
    """Body lines classified: fence state, headings, Do/Don't list membership."""

    def __init__(self, lines, start):
        self.lines = lines
        self.start = start
        self.rows = []  # (index, line, in_fence, list_kind)
        self.fences = []  # (open index, close index or None, tag)
        fence, kind, open_i, tag = None, None, None, ""
        for i in range(start, len(lines)):
            line = lines[i]
            m = FENCE_RE.match(line)
            if fence is None:
                if m:
                    fence, open_i, tag, kind = len(m.group(1)), i, m.group(2).strip(), None
                    self.rows.append((i, line, True, None))
                    continue
                s = line.strip()
                if s == "Do:":
                    kind = "do"
                elif s == "Don't:":
                    kind = "dont"
                elif not s:
                    pass
                elif HEAD_RE.match(line) or not BULLET_RE.match(line):
                    kind = None
                item = kind if (kind and BULLET_RE.match(line)) else None
                self.rows.append((i, line, False, item))
            else:
                if m and len(m.group(1)) >= fence and not m.group(2).strip():
                    self.fences.append((open_i, i, tag))
                    fence = None
                self.rows.append((i, line, True, None))
        if fence is not None:
            self.fences.append((open_i, None, tag))

    def headings(self, level, lo=0, hi=None):
        hi = len(self.lines) if hi is None else hi
        out = []
        for i, line, fen, _ in self.rows:
            if fen or i < lo or i >= hi:
                continue
            m = HEAD_RE.match(line)
            if m and len(m.group(1)) == level:
                out.append((i, m.group(2)))
        return out

    def plain(self, lo, hi, skip_dont=True):
        """Rows outside fences in [lo, hi), optionally without Don't items."""
        return [(i, l, k) for i, l, f, k in self.rows
                if lo <= i < hi and not f and not (skip_dont and k == "dont")]

    def fences_in(self, lo, hi):
        return [f for f in self.fences if lo <= f[0] < hi]


def section_bounds(doc, names):
    """Map H1 title -> (start, end) for the H1s present."""
    h1 = doc.headings(1)
    out = {}
    for n, (i, t) in enumerate(h1):
        end = h1[n + 1][0] if n + 1 < len(h1) else len(doc.lines)
        out.setdefault(t, (i, end))
    return h1, out


def do_dont(doc, lo, hi):
    do = sum(1 for i, l, f, k in doc.rows if lo <= i < hi and k == "do")
    dont = sum(1 for i, l, f, k in doc.rows if lo <= i < hi and k == "dont")
    has_do = any(l.strip() == "Do:" for i, l, f, k in doc.rows if lo <= i < hi and not f)
    has_dont = any(l.strip() == "Don't:" for i, l, f, k in doc.rows if lo <= i < hi and not f)
    ok = has_do and has_dont and do >= 1 and dont >= 1 and do + dont >= 2
    return do, dont, ok


def bare_step(doc, lo, hi):
    """A step whose body is one line with no Do:/Don't: heading carries no examples and passes rule 5."""
    body = [l for i, l, f, k in doc.rows if lo < i < hi and l.strip()]
    return len(body) <= 1 and not any(l.strip() in ("Do:", "Don't:") for l in body)


def legacy_forms(doc):
    found = []
    for i, line, kind in doc.plain(doc.start, len(doc.lines)):
        m = LEGACY_RE.match(line)
        if m:
            found.append(m.group(1).split()[0] if m.group(1).startswith("@") else "Start here")
        elif XML_SCOPE_RE.match(line) or XML_TAG_RE.match(line):
            found.append("xml tag")
        elif LABEL_RE.match(line):
            found.append("labelled bullet")
        h = HEAD_RE.match(line)
        if h and len(h.group(1)) == 1 and h.group(2) in LEGACY_H1:
            found.append("# " + h.group(2))
    return list(dict.fromkeys(f.rstrip(":") for f in found))


def common_checks(doc, folder, template, fails, warns, unresolved, mentions, base_dir):
    """Rules 3, 6, 11 (non-template), 14 and the skill-mention warning."""
    lines = doc.lines
    if len(lines) > MAX_LINES:
        fails.add(6)
    if any(not tag for _, _, tag in doc.fences) or any(c is None for _, c, _ in doc.fences):
        fails.add(3)
    unfilled = 0
    for i in range(doc.start, len(lines)):
        bare = INLINE_CODE_RE.sub("", lines[i])
        unfilled += bare.count("[[") + bare.count("<!--")
    if not template:
        if unfilled:
            fails.add(11)
        for i, line, kind in doc.plain(doc.start, len(lines)):
            if kind in ("do", "dont"):
                continue
            if HOST_RE.search(line):
                fails.add(11)
                break
    for i, line, kind in doc.plain(doc.start, len(lines)):
        targets = []
        for m in MD_LINK_RE.finditer(INLINE_CODE_RE.sub("", line)):
            t = m.group(1).split("#")[0]
            if t and not re.match(r"^[a-z]+:", t) and not t.startswith("/"):
                targets.append(os.path.normpath(os.path.join(base_dir, t)))
        for m in ROOT_PATH_RE.finditer(line):
            t = m.group(1).rstrip(".,;:")
            targets.append(os.path.normpath(os.path.join(folder, t)))
        for t in targets:
            if re.search(r"[<>\[\]{}*]", t):
                continue
            if not os.path.exists(t):
                unresolved.append(os.path.relpath(t, folder))
        bare = INLINE_CODE_RE.sub(lambda m: re.sub(r"\{\{[^}]*\}\}\S*", "", m.group(0)), line)
        bare = re.sub(r"\S*\{\{ \w+ \}\}\S*", "", bare)
        bare = re.sub(r"https?://\S+", "", bare)
        for m in MENTION_RE.finditer(bare):
            if not HOST_RE.match(bare[m.start():]):
                mentions.append(m.group(0))
    if unresolved:
        fails.add(14)
    if mentions:
        warns.add(14)
    return unfilled


def check_steps(doc, lo, hi, fails, warns, out, emit):
    """Rules 5, 8, 17 for the steps under a Process section [lo, hi)."""
    steps = []
    h3 = doc.headings(3, lo, hi)
    for n, (i, title) in enumerate(h3):
        end = h3[n + 1][0] if n + 1 < len(h3) else hi
        m = STEP_RE.match(title)
        if not m:
            fails.add(8)
            continue
        do, dont, ok = do_dont(doc, i, end)
        if not ok and not bare_step(doc, i, end):
            fails.add(5)
        body = [l for _, l, _ in doc.plain(i, end)]
        text = "\n".join(body)
        if "AskUserQuestion" in text and "needs-input" not in text:
            fails.add(17)
        steps.append((int(m.group(1)), m.group(2), do, dont))
        if emit:
            out.append(f"step: {m.group(1)} | {m.group(2)} | do={do} dont={dont}")
    if not steps or [s[0] for s in steps] != list(range(1, len(steps) + 1)):
        fails.add(8)
    return steps


def step_refs(doc, n_steps, fails):
    for i, line, kind in doc.plain(doc.start, len(doc.lines)):
        for m in STEP_REF_RE.finditer(INLINE_CODE_RE.sub("", line)):
            if m.group(1):
                continue
            for num in re.findall(r"\d+", m.group(2)):
                if not 1 <= int(num) <= n_steps:
                    fails.add(8)


def check_inputs(doc, bounds, fails, warns, out, emit, process_text):
    lo, hi = bounds
    inputs = []
    for i, line, kind in doc.plain(lo + 1, hi):
        if not BULLET_RE.match(line):
            continue
        m = INPUT_RE.match(line.rstrip())
        if not m:
            fails.add(4)
            continue
        name, req, default = m.group(1), m.group(2), m.group(3)
        if req == "required" and default != "none":
            fails.add(4)
        inputs.append((name, req, default))
        if emit:
            out.append(f"input: {name} | {req} | {default}")
        if not name.startswith("[[") and not re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", process_text):
            warns.add(4)
    if not inputs:
        fails.add(4)
    return inputs


def six_tags(body):
    """True when body holds the six relay tags once each, in order, each opened and closed, flat, no attributes."""
    found = [(m.group(1) == "/", m.group(2), bool(m.group(3))) for m in TAG_TOKEN_RE.finditer("\n".join(body))]
    return found == [(close, tag, False) for tag in TAGS for close in (False, True)]


def check_output(doc, bounds, fails, warns, out, emit, full):
    """Rules 5, 7, 16, 18 and 23 for the Output section [lo, hi). Rule 7: the first fence holds the six relay tags.
    Rule 16: the last fence is the failure template. Rule 18: field bullets (full only), each naming its tag
    (a warning). Rule 23: no key: value status line and no user-message field."""
    lo, hi = bounds
    fences = doc.fences_in(lo, hi)
    do, dont, ok = do_dont(doc, lo, hi)
    if not ok:
        fails.add(5)
    first_ok = bool(fences) and fences[0][1] is not None and six_tags(doc.lines[fences[0][0] + 1:fences[0][1]])
    if not first_ok:
        fails.add(7)
    for o, c, _ in fences:
        if c is not None and any(LEGACY_OUT_RE.match(l) for l in doc.lines[o + 1:c]):
            fails.add(23)
    if emit:
        out.append(f"output_templates: {len(fences)}")
        out.append(f"output: do={do} dont={dont}")
        out.append(f"output_tags: {'yes' if first_ok else 'no'}")
    status = False
    if fences and fences[-1][1] is not None:
        o, c, _ = fences[-1]
        body = doc.lines[o + 1:c]
        status = (six_tags(body)
                  and any(STATUS_LINE_RE.match(l.strip()) for l in body)
                  and bool(MISSING_RE.search("\n".join(body)))
                  and all(not l.strip() for l in doc.lines[c + 1:hi]))
    if not status:
        fails.add(16)
    if full:
        first = fences[0][0] if fences else hi
        returns = 0
        for i, line, kind in doc.plain(lo + 1, first):
            if re.match(r"^\* \*\*", line):
                m = RETURN_RE.match(line.rstrip())
                if not m:
                    fails.add(18)
                    continue
                returns += 1
                if m.group(1) == "user-message":
                    fails.add(23)
                if not FIELD_TAG_RE.search(line):
                    warns.add(18)
                out.append(f"returns: {m.group(1)} | {m.group(2)}")
                out.append(f"output_field: {m.group(1)}")
        if not returns:
            fails.add(18)
        out.append(f"failure_template: {'yes' if status else 'no'}")


def measure_part(path, folder):
    lines = read(path)
    doc = Doc(lines, 0)
    fails, warns, unresolved, mentions, out = set(), set(), [], [], []
    if not lines or not re.match(r"^Used by SKILL\.md step \d+\.$", lines[0].strip()):
        fails.add(1)
    h1, b = section_bounds(doc, PART_H1)
    if [t for _, t in h1] != PART_H1:
        fails.add(1)
    if legacy_forms(doc):
        fails.add(2)
    if "Input" in b:
        ptext = "\n".join(l for _, l, _ in doc.plain(*b["Process"])) if "Process" in b else ""
        check_inputs(doc, b["Input"], fails, warns, out, False, ptext)
    steps = check_steps(doc, *b["Process"], fails, warns, out, False) if "Process" in b else []
    if "Process" not in b:
        fails.add(8)
    step_refs(doc, len(steps), fails)
    if "Output" in b:
        check_output(doc, b["Output"], fails, warns, out, False, False)
    else:
        fails.add(7)
    common_checks(doc, folder, False, fails, warns, unresolved, mentions, os.path.dirname(path))
    return len(steps), fails, unresolved


def infer_type(doc, legacy):
    h1 = [t for _, t in doc.headings(1)]
    line_forms = [f for f in legacy if not f.startswith("# ")]
    if line_forms or "Workflows" in h1:
        return "legacy-process"
    if "Role" in h1 and "Process" in h1:
        return "process"
    first = next((l for i, l, f, k in doc.rows if l.strip() and not f and not HEAD_RE.match(l)), "")
    numbered = [t for _, t in doc.headings(2) if re.match(r"^\d+\.\s", t)]
    if len(h1) == 1 and first.startswith("Goal:") and numbered:
        if any(t == "Examples" for _, t in doc.headings(3)):
            return "knowledge"
        return "steering"
    return "unknown"


def main(argv):
    if len(argv) != 2:
        die("usage: measure.py <path-to-SKILL.md>")
    path = os.path.abspath(argv[1])
    lines = read(path)
    keys, fm, nested, start = parse_frontmatter(lines)
    folder = os.path.dirname(path)
    doc = Doc(lines, start)
    name, desc = fm.get("name", ""), fm.get("description", "")
    template = "[[" in name
    fails, warns, unresolved, mentions, out = set(), set(), [], [], []

    if nested or any(k not in ("name", "description", "metadata") for k in keys) or "name" not in keys \
            or "description" not in keys:
        fails.add(15)
    version = fm.get("metadata.version", "")
    if not template and not re.match(r"^\d+\.\d+\.\d+$", version):
        fails.add(15)
        out.append("version_error: metadata.version is " + ("missing" if not version else f"malformed ({version!r})")
                   + "; frontmatter needs 'metadata:' then an indented 'version: X.Y.Z' (semver, such as 1.0.0)")
    if not template:
        if not desc or len(desc) > 1024:
            fails.add(12)
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", name) or len(name) > 64:
            fails.add(13)

    legacy = legacy_forms(doc)
    kind = infer_type(doc, legacy)
    if legacy:
        fails.add(2)
    out += [f"type: {kind}", f"lines: {len(lines)}", f"name: {name}",
            f"description_chars: {len(desc)}", "frontmatter_keys: " + (", ".join(keys) or "none")]

    parts = []
    if kind == "process":
        h1, b = section_bounds(doc, PROCESS_H1)
        titles = [t for _, t in h1]
        out.append("sections: " + ", ".join(titles))
        if titles != PROCESS_H1:
            fails.add(1)
        ptext = "\n".join(l for _, l, _ in doc.plain(*b["Process"])) if "Process" in b else ""
        inputs = []
        if "Input" in b:
            inputs = check_inputs(doc, b["Input"], fails, warns, out, True, ptext)
        else:
            fails.add(4)
        req = [n for n, r, _ in inputs if r == "required"]
        out.append("inputs_required: " + (", ".join(req) or "none"))
        steps = []
        step_lines = []
        if "Process" in b:
            steps = check_steps(doc, *b["Process"], fails, warns, step_lines, True)
        else:
            fails.add(8)
        out.append(f"steps: {len(steps)}")
        out += step_lines
        step_refs(doc, len(steps), fails)
        if "Output" in b:
            check_output(doc, b["Output"], fails, warns, out, True, True)
        else:
            fails.update({7, 16, 18})
        wf = os.path.join(folder, "references", "workflows")
        if not template and os.path.isdir(wf):
            for fn in sorted(os.listdir(wf)):
                if fn.endswith(".md"):
                    n, pf, pu = measure_part(os.path.join(wf, fn), folder)
                    unresolved += pu
                    rel = os.path.join("references", "workflows", fn)
                    parts.append(f"part: {rel} | steps={n} | failures="
                                 + (", ".join(map(str, sorted(pf))) or "none"))
                    fails.update(pf)
    elif kind in ("steering", "knowledge"):
        h1 = doc.headings(1)
        if len(h1) != 1 or h1[0][1] != name:
            fails.add(1)
        first = next((l for i, l, f, k in doc.rows if i > h1[0][0] and l.strip() and not f), "") if h1 else ""
        if not first.startswith("Goal:"):
            fails.add(1)
        if any(t in PROCESS_H1 for _, t in h1):
            fails.add(2)
        h2 = doc.headings(2)
        for _, t in h2:
            out.append(f"h2: {t}")
        nums = []
        for _, t in h2[:-1]:
            m = re.match(r"^(\d+)\.\s+\S", t)
            if not m:
                fails.add(2)
            else:
                nums.append(int(m.group(1)))
        if nums != list(range(1, len(nums) + 1)) or not nums:
            fails.add(2)
        for _, t in doc.headings(2) + doc.headings(3):
            if re.sub(r"^\d+\.\s*", "", t).strip().lower() in BANNED_TITLES:
                fails.add(2)
        items = 0
        if h2 and h2[-1][1] == "Pre-send check":
            lo = h2[-1][0]
            for i, line, k in doc.plain(lo + 1, len(lines)):
                if re.match(r"^\d+\.\s", line):
                    items += 1
                for ref in re.findall(r"\(§(\d+)\)", line):
                    if int(ref) not in nums:
                        fails.add(2)
        else:
            fails.add(2)
        if items < 3:
            fails.add(2)
        out.append(f"presend_items: {items}")
        if kind == "knowledge":
            for n, (i, t) in enumerate(h2[:-1]):
                end = h2[n + 1][0]
                ex = [j for j, tt in doc.headings(3, i, end) if tt == "Examples"]
                count = 0
                if ex:
                    h3s = [j for j, _ in doc.headings(3, ex[0] + 1, end)]
                    stop = h3s[0] if h3s else end
                    count = sum(1 for j, l, k in doc.plain(ex[0] + 1, stop) if BULLET_RE.match(l))
                out.append(f"examples: {t} = {count}")
                if count < 2:
                    fails.add(5)
    elif kind == "unknown":
        fails.add(1)

    unfilled = common_checks(doc, folder, template, fails, warns, unresolved, mentions, folder)
    indep = [] if template else independence_hits(folder, name, doc, lines, desc, kind)
    if indep:
        fails.add(20)
    for h in indep:
        out.append("independence_hit: " + h)
    direct, no_ci = ([], []) if template else slot_hits(lines, name in SLOTS or name == "context-injection", reference_lines(folder, name))
    out.append("slot_direct_calls: " + (", ".join(direct) or "none"))
    out.append("slot_without_context_injection: " + (", ".join(no_ci) or "none"))
    if direct or no_ci:
        fails.add(22)
    out.append("unresolved_links: " + (", ".join(dict.fromkeys(unresolved)) or "none"))
    out.append("skill_mentions: " + (", ".join(dict.fromkeys(mentions)) or "none"))
    out.append("legacy: " + (", ".join(legacy) or "none"))
    out.append(f"unfilled: {unfilled}")
    out += parts
    if template:
        out.append("template: yes")
    out.append("warnings: " + (", ".join(map(str, sorted(warns))) or "none"))
    out.append("failures: " + (", ".join(map(str, sorted(fails))) or "none"))
    print("\n".join(out))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
