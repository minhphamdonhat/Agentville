#!/usr/bin/env python3
"""Generate the model/effort variants of the base agents.

Each variant is a copy of its base agent in plugins/agentville/agents/ with a new
name, `model` and `effort` frontmatter lines and one appended description sentence.

Usage:
    python3 scripts/gen_agent_variants.py            # delete and regenerate all 36 variants
    python3 scripts/gen_agent_variants.py --check    # write nothing; exit 1 on missing, stale, extra or pod-lead gaps

All 36 variants are built in memory first, so a build error changes nothing on disk.
--check also fails when the `tools:` line of pod-lead.md lacks `Agent(agentville:<variant>)` for any
variant. The write mode never edits pod-lead.md: keep it hand-maintained and let --check catch drift.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "plugins" / "agentville" / "agents"
BASES = ("worker", "validator", "reviewer", "scout")
MODELS = ("haiku", "sonnet", "opus")
EFFORTS = ("low", "medium", "high")
POD_LEAD = AGENTS / "pod-lead.md"
FOLDED = ("description: >-", "description: >", "description: |", "description: |-")


def build(base, model, effort):
    """Return the variant text for one base, model and effort."""
    path = AGENTS / (base + ".md")
    if not path.is_file():
        raise SystemExit("%s.md: base agent not found in %s" % (base, AGENTS))
    text = path.read_bytes().decode("utf-8")
    lines = text.split("\n")
    if lines[0] != "---":
        raise SystemExit("%s.md: no frontmatter" % base)
    end = lines.index("---", 1)
    out = ["---"]
    i = 1
    seen_desc = False
    seen_name = False
    while i < end:
        line = lines[i]
        if line.startswith("name:"):
            if line != "name: " + base:
                raise SystemExit("%s.md: expected an unquoted line `name: %s`, found `%s`" % (base, base, line))
            seen_name = True
            out.append("name: %s-%s-%s" % (base, model, effort))
        elif line.startswith("description:"):
            seen_desc = True
            block = [line]
            while i + 1 < end and lines[i + 1].startswith(" "):
                i += 1
                block.append(lines[i])
            if block[0].rstrip() not in FOLDED:
                raise SystemExit("%s.md: unsupported description style" % base)
            block.append(
                "  Variant fixed to %s at %s effort; generated from `%s.md`, do not edit."
                % (model.capitalize(), effort, base)
            )
            if len(" ".join(b.strip() for b in block[1:])) >= 1024:
                raise SystemExit("%s.md: description too long" % base)
            out.extend(block)
            out.append("model: " + model)
            out.append("effort: " + effort)
        else:
            out.append(line)
        i += 1
    if not seen_name:
        raise SystemExit("%s.md: no `name:` line" % base)
    if not seen_desc:
        raise SystemExit("%s.md: no description" % base)
    out.extend(lines[end:])
    return "\n".join(out)


def expected():
    return {"%s-%s-%s.md" % (b, m, e): (b, m, e) for b in BASES for m in MODELS for e in EFFORTS}


def build_all():
    """Build every variant in memory; any build error exits before anything is written."""
    return {name: build(b, m, e) for name, (b, m, e) in expected().items()}


def extras(want):
    """Files whose stem starts with a base name and a dash but are not one of the variants."""
    return sorted(
        p.name
        for p in AGENTS.iterdir()
        if p.suffix == ".md" and p.name not in want and any(p.stem.startswith(b + "-") for b in BASES)
    )


def pod_lead_missing(want):
    if not POD_LEAD.is_file():
        return ["pod-lead missing: pod-lead.md not found"]
    tools = [l for l in POD_LEAD.read_text(encoding="utf-8").split("\n") if l.startswith("tools:")]
    if not tools:
        return ["pod-lead missing: tools line"]
    return ["pod-lead missing: " + n[:-3] for n in want if "Agent(agentville:%s)" % n[:-3] not in tools[0]]


def check():
    built = build_all()
    problems = []
    for name, text in built.items():
        path = AGENTS / name
        if not path.is_file():
            problems.append("missing: " + name)
        elif path.read_bytes().decode("utf-8") != text:
            problems.append("stale: " + name)
    problems.extend("extra: " + n for n in extras(built))
    problems.extend(pod_lead_missing(built))
    for problem in problems:
        print(problem)
    return 1 if problems else 0


def generate():
    built = build_all()
    for name in built:
        (AGENTS / name).unlink(missing_ok=True)
    for name, text in built.items():
        with open(AGENTS / name, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    print("wrote %d variants" % len(built))
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--check"]:
        sys.exit(check())
    if args:
        sys.exit("usage: gen_agent_variants.py [--check]")
    sys.exit(generate())
