#!/usr/bin/env python3
"""Measure a compiled agent file against the script-checked rules of references/validate-rules.md.

Usage: measure.py <agent.md> [--base <base-worker.md>] [--allow-agent]
--base defaults to assets/base/worker.md in this skill. --allow-agent permits the Agent tool,
only when the user asked for it by name.
Prints key: value lines; the last is failures: <rule ids or none>.
Exit: 0 no failures (warnings allowed), 1 rule failures, 2 usage or read error.
Stdlib only; runs under python3 -I.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BASE = os.path.join(os.path.dirname(HERE), "assets", "base", "worker.md")
SECTIONS = ["Role", "Constraints", "Workflows", "Exception handler"]
CORE_HOME = {"identity": "Role", "constraints": "Constraints"}
ROLES = {"worker", "validator", "reviewer", "scout"}
ALLOWED_KEYS = {"name", "description", "tools", "disallowedTools"}
FORBIDDEN_KEYS = {"model", "effort"}
SPAWN_TOOLS = {"Agent", "Task"}
MAX_LINES = 500
FOREIGN_NS = "anthropic-skills" + ":"
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
CORE_BEGIN_RE = re.compile(r"^<!-- core:begin ([a-z-]+) -->\s*$")
CORE_END_RE = re.compile(r"^<!-- core:end ([a-z-]+) -->\s*$")
WF_TITLE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*$")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
INPUT_RE = re.compile(r"^\* \*\*([a-z0-9][a-z0-9-]*):\*\* (required|optional) - default: (.+?) - (.+)$")
RETURN_RE = re.compile(r"^\* \*\*([a-z0-9][a-z0-9-]*):\*\* (always|when .+?) - (.+)$")
STEP_RE = re.compile(r"^(\d+)\.\s+\S")
SKILL_REF_RE = re.compile(r"Skill\(([^)]*)\)")
STATUS_LINE = "`<status>` comes first and holds one of"
EVERY_FIELD = "each wrapped in one flat tag"

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
SLOT_SOURCES = ("plugin-default", "project-rules", "project-claude-md", "project-skill", "user-rules", "user-claude-md", "user-skill")
PLUGIN_DEFAULT_BEFORE_RE = re.compile(r"the plugin default[`\s]*$")
PLUGIN_DEFAULT_AFTER_RE = re.compile(r"`*\s?\(plugin-default\)")
RECORD_AFTER_RE = re.compile(r"\s\((?:" + "|".join(SLOT_SOURCES) + r")\)")


def slot_default_described(line, m):
    """True when the hit only describes the plugin default or stands as the skill id of a slot record."""
    before, after = line[:m.start()], line[m.end():]
    if PLUGIN_DEFAULT_BEFORE_RE.search(before) or PLUGIN_DEFAULT_AFTER_RE.match(after):
        return True
    slot = m.group(1) or m.group(2)
    bare = bool(m.group(2)) and not m.group(0).startswith("/")
    return bare and bool(re.search(r"(?<![\w-])" + slot + r":\s+$", before)) and bool(RECORD_AFTER_RE.match(after))


def slot_hits(lines, exempt=False):
    """Slot rule: a file that uses an injectable slot names CI_CALL and never calls Skill(agentville:<slot>) itself."""
    if exempt:
        return [], []
    direct = [f"{i + 1}:{m.group(0)}" for i, l in enumerate(lines) for m in SLOT_CALL_RE.finditer(l)
              if not slot_default_described(l, m)]
    used = sorted({m.group(1) for l in lines for m in SLOT_USE_RE.finditer(l)})
    return direct, ([] if CI_CALL in "\n".join(lines) else used)


class ReadError(Exception):
    pass


def read_lines(path):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    except (OSError, UnicodeError) as e:
        raise ReadError(f"cannot read {path}: {e}")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def split_list(v):
    return [t.strip() for t in re.split(r"[,\s]+", v.strip().strip("[]")) if t.strip()]


def parse_frontmatter(lines):
    """Return (ordered keys, values, index of first body line) or raise ReadError."""
    if not lines or lines[0].strip() != "---":
        raise ReadError("no frontmatter: file must start with ---")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ReadError("unterminated frontmatter")
    keys, vals, key = [], {}, None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if m and raw[0] not in " \t":
            key, val = m.group(1), m.group(2).strip()
            keys.append(key)
            vals[key] = "" if val in (">", "|", ">-", "|-") else val
        elif key:
            vals[key] = (vals[key] + " " + raw.strip()).strip()
    for k, v in vals.items():
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            vals[k] = v[1:-1]
    return keys, vals, end + 1


def body_rows(lines, start):
    """(index, line, in_fence) for each body line."""
    rows, fence = [], None
    for i in range(start, len(lines)):
        m = FENCE_RE.match(lines[i])
        if fence is None and m:
            fence = m.group(1)[0]
            rows.append((i, lines[i], True))
        elif fence is not None:
            if m and m.group(1)[0] == fence:
                fence = None
            rows.append((i, lines[i], True))
        else:
            rows.append((i, lines[i], False))
    return rows


def headings(rows, level):
    out = []
    for i, line, fen in rows:
        m = HEAD_RE.match(line) if not fen else None
        if m and len(m.group(1)) == level:
            out.append((i, m.group(2)))
    return out


def spans(heads, end):
    return [(t, i, heads[n + 1][0] if n + 1 < len(heads) else end) for n, (i, t) in enumerate(heads)]


def core_blocks(lines):
    """Map core name -> (begin index, end index, text) and a list of marker errors."""
    out, errors, open_ = {}, [], None
    for i, line in enumerate(lines):
        b, e = CORE_BEGIN_RE.match(line), CORE_END_RE.match(line)
        if b:
            if open_:
                errors.append(f"nested core block {b.group(1)} inside {open_[0]}")
            open_ = (b.group(1), i)
        elif e:
            if not open_ or open_[0] != e.group(1):
                errors.append(f"stray core end {e.group(1)}")
            else:
                name, s = open_
                if name in out:
                    errors.append(f"duplicate core block {name}")
                out[name] = (s, i, "\n".join(lines[s:i + 1]))
            open_ = None
    if open_:
        errors.append(f"unterminated core block {open_[0]}")
    return out, errors


def parse_agent(path):
    """Parse an agent file into a dict; raises ReadError on unreadable input."""
    lines = read_lines(path)
    keys, fm, start = parse_frontmatter(lines)
    rows = body_rows(lines, start)
    h1 = headings(rows, 1)
    sec = {t: (i, e) for t, i, e in spans(h1, len(lines))}
    workflows = []
    if "Workflows" in sec:
        lo, hi = sec["Workflows"]
        sub = [r for r in rows if lo < r[0] < hi]
        for title, i, e in spans(headings(sub, 2), hi):
            m = WF_TITLE_RE.match(title)
            wf = {"title": title, "name": title if m else None, "role": None,
                  "h3": [], "inputs": [], "bad_inputs": 0, "steps": [], "outputs": [], "bad_outputs": 0}
            part = [r for r in rows if i < r[0] < e]
            for _, line, fen in part:
                rm = re.match(r"^Role:\s*(\S+)\s*$", line)
                if rm and not fen and wf["role"] is None:
                    wf["role"] = rm.group(1)
            h3 = spans(headings(part, 3), e)
            wf["h3"] = [t for t, _, _ in h3]
            for t, a, b in h3:
                examples = False
                for _, line, fen in [r for r in part if a < r[0] < b]:
                    if fen:
                        continue
                    if re.match(r"^(Do|Don't):\s*$", line):
                        examples = True
                    if examples:
                        continue
                    if t == "Input" and line.startswith("* "):
                        mm = INPUT_RE.match(line.rstrip())
                        if mm and not (mm.group(2) == "required" and mm.group(3) != "none"):
                            wf["inputs"].append((mm.group(1), mm.group(2), mm.group(3)))
                        else:
                            wf["bad_inputs"] += 1
                    elif t == "Process":
                        sm = STEP_RE.match(line)
                        if sm:
                            wf["steps"].append(int(sm.group(1)))
                    elif t == "Output" and line.startswith("* "):
                        om = RETURN_RE.match(line.rstrip())
                        if om:
                            wf["outputs"].append((om.group(1), om.group(2)))
                        else:
                            wf["bad_outputs"] += 1
            workflows.append(wf)
    exc_items = 0
    if "Exception handler" in sec:
        lo, hi = sec["Exception handler"]
        exc_items = sum(1 for i, l, f in rows if lo < i < hi and not f and re.match(r"^\s*[*-]\s+\S", l))
    blocks, marker_errors = core_blocks(lines)
    return {"lines": lines, "keys": keys, "fm": fm, "start": start, "rows": rows,
            "h1": [t for _, t in h1], "sections": sec, "workflows": workflows,
            "exception_items": exc_items, "core": blocks, "core_errors": marker_errors}


def section_of(agent, index):
    for t, (lo, hi) in agent["sections"].items():
        if lo < index < hi:
            return t
    return None


def measure(path, base_path, allow_agent):
    a = parse_agent(path)
    out, fails, warns = [], set(), set()
    fm, keys, lines = a["fm"], a["keys"], a["lines"]
    name, desc = fm.get("name", ""), fm.get("description", "")
    tools, denied = split_list(fm.get("tools", "")), split_list(fm.get("disallowedTools", ""))
    out += [f"lines: {len(lines)}", f"name: {name}", f"description_chars: {len(desc)}",
            "frontmatter_keys: " + (", ".join(keys) or "none"),
            "tools: " + (", ".join(tools) or "none"), "disallowed: " + (", ".join(denied) or "none")]

    # A1 required frontmatter
    if not NAME_RE.match(name) or len(name) > 64 or not desc or len(desc) > 1024 or not tools:
        fails.add("A1")
    # A2 forbidden and unknown keys
    if FORBIDDEN_KEYS & set(keys):
        fails.add("A2")
        out.append("forbidden_keys: " + ", ".join(sorted(FORBIDDEN_KEYS & set(keys))))
    unknown = [k for k in keys if k not in ALLOWED_KEYS | FORBIDDEN_KEYS]
    if unknown:
        warns.add("A2")
        out.append("unknown_keys: " + ", ".join(unknown))
    # A3 no spawning tool unless explicitly allowed
    spawn = [t for t in tools if t.split("(")[0] in SPAWN_TOOLS]
    out.append("spawn_tools: " + (", ".join(spawn) or "none") + (" (allowed)" if spawn and allow_agent else ""))
    if spawn and not allow_agent:
        fails.add("A3")
    # A10 a tool both granted and denied
    both = sorted(set(tools) & set(denied))
    if both:
        fails.add("A10")
        out.append("granted_and_denied: " + ", ".join(both))

    # A4 sections
    out.append("sections: " + ", ".join(a["h1"]))
    if a["h1"] != SECTIONS:
        fails.add("A4")

    # A5 core blocks identical to the base worker and in their home section
    try:
        base = parse_agent(base_path)
    except ReadError as e:
        raise ReadError(f"base: {e}")
    if a["core_errors"]:
        fails.add("A5")
        out += ["core_error: " + e for e in a["core_errors"]]
    for cname in sorted(set(base["core"]) | set(CORE_HOME)):
        mine, theirs = a["core"].get(cname), base["core"].get(cname)
        if theirs is None:
            state = "missing in base"
        elif mine is None:
            state = "missing"
        elif mine[2] != theirs[2]:
            state = "differs"
        elif CORE_HOME.get(cname) and section_of(a, mine[0]) != CORE_HOME[cname]:
            state = "misplaced"
        else:
            state = "identical"
        if state != "identical":
            fails.add("A5")
        out.append(f"core: {cname} | {state}")
    if "constraints" in a["core"] and "Constraints" in a["sections"]:
        lo, _ = a["sections"]["Constraints"]
        first = next((i for i, l, f in a["rows"] if i > lo and l.strip()), None)
        if first != a["core"]["constraints"][0]:
            fails.add("A5")
            out.append("core_error: constraints core is not first in Constraints")

    # A16 the constraints core makes every report a set of flat tags that opens with the status tag
    ret = a["core"].get("constraints")
    status_rule = bool(ret) and STATUS_LINE in ret[2] and EVERY_FIELD in ret[2]
    out.append("status_line_rule: " + ("yes" if status_rule else "no"))
    if not status_rule:
        fails.add("A16")

    # A6 workflows
    wfs = a["workflows"]
    out.append(f"workflows: {len(wfs)}")
    names = []
    for wf in wfs:
        ok = (wf["name"] is not None and wf["role"] in ROLES
              and wf["h3"] == ["Input", "Process", "Output"] and wf["inputs"] and not wf["bad_inputs"]
              and wf["steps"] and wf["steps"] == list(range(1, len(wf["steps"]) + 1))
              and wf["outputs"] and not wf["bad_outputs"])
        names.append(wf["name"])
        if not ok:
            fails.add("A6")
        out.append(f"workflow: {wf['name'] or wf['title']} | role={wf['role']} | inputs={len(wf['inputs'])} | "
                   f"steps={len(wf['steps'])} | outputs=" + (",".join(f for f, _ in wf["outputs"]) or "none")
                   + ("" if ok else " | invalid"))
    if not wfs or len(set(names)) != len(names):
        fails.add("A6")

    # A7 exception handler
    out.append(f"exception_items: {a['exception_items']}")
    if a["exception_items"] < 1:
        fails.add("A7")

    # A8 leftovers, A9 namespace, A11 size
    leftovers, foreign, bare = 0, [], []
    for i, line, fen in a["rows"]:
        stripped = re.sub(r"<!-- core:(begin|end) [a-z-]+ -->", "", line)
        leftovers += stripped.count("[[") + stripped.count("{{ CORE") + stripped.count("<!--")
        if FOREIGN_NS in line:
            foreign.append(str(i + 1))
        for m in SKILL_REF_RE.finditer(line):
            if ":" not in m.group(1):
                bare.append(m.group(0))
    for i, line in enumerate(lines[:a["start"]]):
        leftovers += line.count("[[")
        if FOREIGN_NS in line:
            foreign.append(str(i + 1))
    out.append(f"unfilled: {leftovers}")
    if leftovers:
        fails.add("A8")
    out.append("foreign_namespace_lines: " + (", ".join(foreign) or "none"))
    if foreign:
        fails.add("A9")
    out.append("bare_skill_refs: " + (", ".join(dict.fromkeys(bare)) or "none"))
    if bare:
        warns.add("A9")
    direct, no_ci = slot_hits(lines)
    out.append("slot_direct_calls: " + (", ".join(direct) or "none"))
    out.append("slot_without_context_injection: " + (", ".join(no_ci) or "none"))
    if direct or no_ci:
        fails.add("A18")
    if len(lines) > MAX_LINES:
        fails.add("A11")

    order = lambda s: int(s[1:])
    out.append("warnings: " + (", ".join(sorted(warns, key=order)) or "none"))
    out.append("failures: " + (", ".join(sorted(fails, key=order)) or "none"))
    return out, fails


def main(argv):
    args = argv[1:]
    allow_agent = "--allow-agent" in args
    args = [x for x in args if x != "--allow-agent"]
    base = DEFAULT_BASE
    if "--base" in args:
        k = args.index("--base")
        if k + 1 >= len(args):
            print("usage: measure.py <agent.md> [--base <file>] [--allow-agent]", file=sys.stderr)
            return 2
        base = args[k + 1]
        del args[k:k + 2]
    if len(args) != 1:
        print("usage: measure.py <agent.md> [--base <file>] [--allow-agent]", file=sys.stderr)
        return 2
    try:
        out, fails = measure(os.path.abspath(args[0]), os.path.abspath(base), allow_agent)
    except ReadError as e:
        print(str(e), file=sys.stderr)
        return 2
    print("\n".join(out))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
