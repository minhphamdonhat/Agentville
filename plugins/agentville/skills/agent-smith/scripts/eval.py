#!/usr/bin/env python3
"""Eval helper for agent-smith: run a compiled agent and the base worker on the same cases and grade
each report against the six flat report tags.

eval.py init <agent.md> <evals.json>                  write one case skeleton per workflow
eval.py check <agent.md> <evals.json>                 check every workflow has a filled case
eval.py prompts <agent.md> <base.md|none> <evals.json> <out>
        write one prompt file per case and agent, for dispatch by whoever runs the skill
eval.py run <agent.md> <base.md|none> <evals.json> <out> [--execute] [--model M] [--workdir D] [--plugin-dir P]
        [--timeout S]
        headless runs with the claude CLI; without --execute it only prints the commands. Each run gets the
        agent's own tools as --allowedTools and --plugin-dir P (default: the plugin folder holding this skill).
eval.py grade <agent.md> <evals.json> <out>           grade <out>/<case>.<label>.out.md files
Labels: `compiled` is the agent under test, `base` is the baseline: the base worker, or with `none` as
<base.md> plain `claude -p` with no agent, given the compiled agent's tools and the same model.
Each run (case and label) gets its own sandbox <out>/sandbox/<case>.<label>/, rebuilt before the run, holding
the agents under .claude/agents/ and the case's `files` fixtures ({"rel/path": "content"}). A case's
`expect_files` ({"rel/path": "text it must contain"}) and `unchanged` (fixture paths) are graded against
that sandbox after the run.
Exit: 0 success (grade: every compiled case passed; the base score is the baseline), 1 check or grade failure, 2 usage or read error.
Stdlib only; runs under python3 -I.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("agent_measure", os.path.join(HERE, "measure.py"))
measure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(measure)

LABELS = ("compiled", "base")
TOKENS = ("completed", "partial", "needs-input", "blocked", "failed")
REPORT_TAGS = ("status", "outcome", "claims", "artefacts", "open", "deviations")
TAG_RE = re.compile(r"<(/?)(" + "|".join(REPORT_TAGS) + r")\b([^<>]*)>", re.I)
NO_BASE = "none"


def die(msg, code=2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load_agent(path):
    try:
        return measure.parse_agent(path)
    except measure.ReadError as e:
        die(str(e))


def body(agent):
    return "\n".join(agent["lines"][agent["start"]:]).strip() + "\n"


def load_base(path):
    return None if path == NO_BASE else load_agent(path)


def safe_rel(path):
    """True for a relative path inside the sandbox that does not touch .claude/."""
    if not isinstance(path, str) or not path or os.path.isabs(path) or "\\" in path:
        return False
    parts = path.split("/")
    return ".." not in parts and "" not in parts and parts[0] != ".claude"


def check_files(cid, c):
    problems = []
    files = c.get("files", {})
    if not isinstance(files, dict) or not all(safe_rel(k) and isinstance(v, str) for k, v in files.items()):
        problems.append(f"{cid}: files must map relative paths (no .., not under .claude) to text")
        files = {}
    ef = c.get("expect_files", {})
    if not isinstance(ef, dict) or not all(safe_rel(k) and isinstance(v, str) for k, v in ef.items()):
        problems.append(f"{cid}: expect_files must map relative paths to text")
    un = c.get("unchanged", [])
    if not isinstance(un, list) or not all(isinstance(u, str) and u in files for u in un):
        problems.append(f"{cid}: unchanged must list paths from files")
    return problems


def sandbox_dir(out, cid, label):
    return os.path.join(out, "sandbox", f"{cid}.{label}")


def build_sandbox(out, case, label, agents):
    """Rebuild the run's sandbox: agent copies under .claude/agents/ and the case's fixture files."""
    root = os.path.join(out, "sandbox")
    d = sandbox_dir(out, case["id"], label)
    if os.path.dirname(d) != root:
        die(f"refused: sandbox {d} outside {root}")
    if os.path.isdir(d):
        shutil.rmtree(d)
    adir = os.path.join(d, ".claude", "agents")
    os.makedirs(adir)
    for a, new_name in agents:
        write_agent_copy(a["lines"], a["start"], new_name, os.path.join(adir, f"{new_name}.md"))
    for rel, text in case.get("files", {}).items():
        p = os.path.join(d, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    return d


def load_cases(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        die(f"cannot read {path}: {e}")
    cases = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(cases, list):
        die(f"{path}: expected an object with a cases list")
    return data, cases


def init(args):
    if len(args) != 2:
        die("usage: eval.py init <agent.md> <evals.json>")
    agent, out = load_agent(args[0]), args[1]
    if os.path.exists(out):
        die(f"refused: {out} exists")
    cases = []
    for wf in agent["workflows"]:
        cases.append({
            "id": f"{wf['name'].lower()}-1", "workflow": wf["name"], "role": wf["role"] or "worker",
            "prompt": f"[[A relay brief that exercises the {wf['name']} workflow]]",
            "status": "[[completed | partial | needs-input | blocked | failed]]",
            "expect": ["[[text the report must contain]]"], "forbid": [],
        })
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"agent": agent["fm"].get("name", ""), "cases": cases}, f, indent=2)
        f.write("\n")
    print(f"written: {os.path.abspath(out)}")
    print(f"cases: {len(cases)}")
    return 0


def case_role(agent, case):
    """The case's role, else the Role of the agent's first workflow (the agent's own default), else worker."""
    if case.get("role"):
        return case["role"]
    wfs = agent["workflows"]
    return (wfs[0]["role"] if wfs else None) or "worker"


def check_cases(agent, cases):
    """Return a list of problems; print one case: line per case."""
    problems, seen = [], set()
    names = {wf["name"] for wf in agent["workflows"]}
    covered = set()
    for c in cases:
        cid = c.get("id")
        if not isinstance(cid, str) or not re.match(r"^[a-z0-9][a-z0-9-]*$", cid) or cid in seen:
            problems.append(f"bad or duplicate id: {cid}")
            continue
        seen.add(cid)
        if c.get("workflow") not in names:
            problems.append(f"{cid}: unknown workflow {c.get('workflow')}")
        else:
            covered.add(c["workflow"])
        if case_role(agent, c) not in measure.ROLES:
            problems.append(f"{cid}: unknown role {c.get('role')}")
        if not isinstance(c.get("prompt"), str) or not c["prompt"].strip():
            problems.append(f"{cid}: empty prompt")
        if c.get("status") is not None and c["status"] not in TOKENS:
            problems.append(f"{cid}: status must be one of {', '.join(TOKENS)}")
        problems += check_files(cid, c)
        if "[[" in json.dumps(c):
            problems.append(f"{cid}: unfilled [[...]]")
        print(f"case: {cid} | {c.get('workflow')} | role={case_role(agent, c)}")
    for n in sorted(names - covered):
        problems.append(f"workflow {n} has no case")
    return problems


def check(args):
    if len(args) != 2:
        die("usage: eval.py check <agent.md> <evals.json>")
    agent = load_agent(args[0])
    _, cases = load_cases(args[1])
    problems = check_cases(agent, cases)
    for p in problems:
        print(f"problem: {p}")
    print("problems: " + str(len(problems)))
    return 1 if problems else 0


def case_prompt(case, agent):
    role = case_role(agent, case)
    text = case["prompt"].strip()
    return text if "<role>" in text else f"<role>{role}</role>\n{text}"


def prepared(args, usage):
    if len(args) < 4:
        die(usage)
    agent, base = load_agent(args[0]), load_base(args[1])
    _, cases = load_cases(args[2])
    problems = check_cases(agent, cases)
    if problems:
        for p in problems:
            print(f"problem: {p}")
        die("refused: fix the cases first (eval.py check)", 1)
    out = os.path.abspath(args[3])
    os.makedirs(out, exist_ok=True)
    return agent, base, cases, out


def prompts(args):
    usage = "usage: eval.py prompts <agent.md> <base.md|none> <evals.json> <out>"
    if len(args) != 4:
        die(usage)
    agent, base, cases, out = prepared(args, usage)
    print("baseline: " + ("none (no agent)" if base is None else base["fm"].get("name", "worker")))
    for c in cases:
        for label, a in (("compiled", agent), ("base", base)):
            pf = os.path.join(out, f"{c['id']}.{label}.prompt.md")
            with open(pf, "w", encoding="utf-8") as f:
                if a is None:
                    f.write(case_prompt(c, agent) + "\n")
                else:
                    f.write("Act as the agent defined between the AGENT markers, then do the task.\n\n"
                            "<<<AGENT\n" + body(a) + "AGENT>>>\n\n" + case_prompt(c, agent) + "\n")
            of = os.path.join(out, f"{c['id']}.{label}.out.md")
            if os.path.isfile(of) and os.path.isdir(sandbox_dir(out, c["id"], label)):
                cwd = sandbox_dir(out, c["id"], label)
            else:
                cwd = build_sandbox(out, c, label, [])
            print(f"dispatch: {c['id']} | {label} | {pf} | cwd={cwd} | save report to {of}")
    return 0


def agent_names(agent, base):
    name = agent["fm"].get("name", "agent")
    if base is None:
        return name, None
    bname = base["fm"].get("name", "worker")
    return name, (bname + "-base" if bname == name else bname)


def write_agent_copy(src_lines, start, new_name, path):
    lines = list(src_lines)
    for i in range(1, start):
        if lines[i].startswith("name:"):
            lines[i] = f"name: {new_name}"
            break
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def plugin_root(start=HERE):
    """The nearest folder above start that holds .claude-plugin/plugin.json, or None."""
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, ".claude-plugin", "plugin.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def build_command(cli, agent_name, tools, prompt, workdir=None, model=None, plugin_dir=None, denied=None):
    """Headless command for one case; agent_name None runs plain `claude -p` with no agent. Variadic flags
    (--allowedTools, --disallowedTools, --add-dir) come before a single-value flag so they never swallow
    the prompt, which is the last argument."""
    cmd = [cli, "-p"] + (["--agent", agent_name] if agent_name else [])
    if tools:
        cmd += ["--allowedTools", ",".join(tools)]
    if denied:
        cmd += ["--disallowedTools", ",".join(denied)]
    if workdir:
        cmd += ["--add-dir", workdir]
    cmd += ["--output-format", "json", "--no-session-persistence",
            "--permission-mode", "dontAsk", "--permission-prompts", "none"]
    if plugin_dir:
        cmd += ["--plugin-dir", plugin_dir]
    if model:
        cmd += ["--model", model]
    cmd.append(prompt)
    return cmd


def run(args):
    usage = ("usage: eval.py run <agent.md> <base.md|none> <evals.json> <out> "
             "[--execute] [--model M] [--workdir D] [--plugin-dir P] [--timeout S]")
    execute = "--execute" in args
    args = [a for a in args if a != "--execute"]
    opts = {"--model": None, "--workdir": None, "--plugin-dir": None, "--timeout": "900"}
    for k in list(opts):
        if k in args:
            i = args.index(k)
            if i + 1 >= len(args):
                die(usage)
            opts[k] = args[i + 1]
            del args[i:i + 2]
    if len(args) != 4:
        die(usage)
    agent, base, cases, out = prepared(args, usage)
    cli = shutil.which("claude")
    print("claude_cli: " + (cli or "not found"))
    if not cli:
        print("mode: dispatch (run eval.py prompts instead)")
        return 2
    name, bname = agent_names(agent, base)
    copies = [(agent, name)] + ([] if base is None else [(base, bname)])
    workdir = os.path.abspath(opts["--workdir"]) if opts["--workdir"] else None
    pdir = os.path.abspath(opts["--plugin-dir"]) if opts["--plugin-dir"] else plugin_root()
    print("plugin_dir: " + (pdir or "none (no .claude-plugin/plugin.json above this skill)"))
    print("model: " + (opts["--model"] or "session default"))
    atools = measure.split_list(agent["fm"].get("tools", ""))
    adenied = measure.split_list(agent["fm"].get("disallowedTools", ""))
    # The no-agent baseline gets the compiled agent's tools, allowed and denied; an agent applies its own denials.
    tools = {"compiled": (name, atools, None),
             "base": (None, atools, adenied) if base is None
             else (bname, measure.split_list(base["fm"].get("tools", "")), None)}
    print("baseline: " + ("none (plain claude -p, the compiled agent's tools)" if base is None else bname))
    print("mode: " + ("execute" if execute else "dry-run"))
    failed = 0
    for c in cases:
        for label in LABELS:
            aname, allowed, denied = tools[label]
            sandbox = build_sandbox(out, c, label, copies)
            cmd = build_command(cli, aname, allowed, case_prompt(c, agent), workdir, opts["--model"], pdir, denied)
            of = os.path.join(out, f"{c['id']}.{label}.out.md")
            print(f"command: {c['id']} | {label} | cwd={sandbox} | " + " ".join(json.dumps(x) for x in cmd[1:]))
            if not execute:
                continue
            try:
                p = subprocess.run(cmd, cwd=sandbox, capture_output=True, text=True,
                                   timeout=int(opts["--timeout"]))
                text = p.stdout
                try:
                    data = json.loads(text)
                    if isinstance(data, dict) and isinstance(data.get("result"), str):
                        text = data["result"]
                except ValueError:
                    pass
                if p.returncode != 0:
                    failed += 1
                    text = run_error(f"exit {p.returncode}\n{p.stderr[-2000:]}\n{text}")
            except subprocess.TimeoutExpired:
                failed += 1
                text = run_error("timeout")
            with open(of, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"output: {c['id']} | {label} | {of}")
    print(f"runs: {len(cases) * len(LABELS)}")
    print(f"run_errors: {failed}")
    return 0


def run_error(detail):
    return ("<status>failed</status>\n<outcome>run error</outcome>\n<claims>\nnone\n</claims>\n"
            f"<artefacts>\nnone\n</artefacts>\n<open>\n{detail.strip()}\n</open>\n<deviations>\nnone\n</deviations>\n")


def grade_report(text):
    """Return (status token or None, reasons) for the six flat tags in order, plain lines inside."""
    reasons = []
    first = next((l for l in text.splitlines() if l.strip()), "")
    if not re.match(r"\s*<status>", first, re.I):
        reasons.append("first line is not <status>TOKEN</status>")
    opened, closed, bodies, order, cur, last = {}, {}, {}, [], None, 0
    for m in TAG_RE.finditer(text):
        end, name, attrs = m.group(1) == "/", m.group(2).lower(), m.group(3).strip()
        if attrs:
            reasons.append(f"attributes on <{name}>")
        if not end:
            if cur:
                reasons.append(f"<{name}> nested in <{cur}>")
            opened[name] = opened.get(name, 0) + 1
            order.append(name)
            cur, last = name, m.end()
        else:
            if cur != name:
                reasons.append(f"stray </{name}>")
            else:
                bodies[name] = text[last:m.start()]
            closed[name] = closed.get(name, 0) + 1
            cur = None
    for t in REPORT_TAGS:
        if not opened.get(t):
            reasons.append(f"missing tag <{t}>")
        elif opened[t] > 1:
            reasons.append(f"repeated tag <{t}>")
        elif closed.get(t, 0) != 1:
            reasons.append(f"unclosed tag <{t}>")
    seen = [t for t in dict.fromkeys(order) if t in REPORT_TAGS]
    if seen != [t for t in REPORT_TAGS if t in seen]:
        reasons.append("tags out of order")
    token = bodies.get("status", "").strip().lower()
    if token not in TOKENS:
        reasons.append(f"<status> is not one of {', '.join(TOKENS)}")
        token = None
    return token, reasons


def grade_text(text, case, wf):
    token, reasons = grade_report(text)
    if case.get("status") and token != case["status"]:
        reasons.append(f"status {token} != expected {case['status']}")
    low = text.lower()
    for s in case.get("expect", []):
        if s.lower() not in low:
            reasons.append(f"missing expected text: {s}")
    for s in case.get("forbid", []):
        if s.lower() in low:
            reasons.append(f"has forbidden text: {s}")
    return token, reasons


def grade_files(case, sandbox):
    """Reasons from the case's expect_files and unchanged, read from the run's sandbox."""
    ef, un = case.get("expect_files", {}), case.get("unchanged", [])
    if not ef and not un:
        return []
    if not os.path.isdir(sandbox):
        return [f"no sandbox for file checks: {sandbox}"]
    reasons = []

    def content(rel):
        try:
            with open(os.path.join(sandbox, *rel.split("/")), encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            return None
    for rel, want in ef.items():
        got = content(rel)
        if got is None:
            reasons.append(f"file missing: {rel}")
        elif want.lower() not in got.lower():
            reasons.append(f"file {rel} lacks: {want}")
    for rel in un:
        if content(rel) != case["files"][rel]:
            reasons.append(f"file changed: {rel}")
    return reasons


def grade(args):
    if len(args) != 3:
        die("usage: eval.py grade <agent.md> <evals.json> <out>")
    agent = load_agent(args[0])
    _, cases = load_cases(args[1])
    out = os.path.abspath(args[2])
    wfs = {wf["name"]: wf for wf in agent["workflows"]}
    score = {label: 0 for label in LABELS}
    graded, results = 0, []
    for c in cases:
        for label in LABELS:
            path = os.path.join(out, f"{c['id']}.{label}.out.md")
            if not os.path.isfile(path):
                print(f"grade: {c['id']} | {label} | not run")
                results.append({"id": c["id"], "label": label, "result": "not run"})
                continue
            with open(path, encoding="utf-8", errors="replace") as f:
                token, reasons = grade_text(f.read(), c, wfs.get(c.get("workflow")))
            reasons += grade_files(c, sandbox_dir(out, c["id"], label))
            ok = not reasons
            score[label] += ok
            graded += label == "compiled"
            print(f"grade: {c['id']} | {label} | {'pass' if ok else 'fail'} | status={token}"
                  + ("" if ok else " | " + "; ".join(reasons)))
            results.append({"id": c["id"], "label": label, "result": "pass" if ok else "fail",
                            "status": token, "reasons": reasons})
    with open(os.path.join(out, "grades.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        f.write("\n")
    n = len(cases)
    print(f"score: compiled {score['compiled']}/{n} vs base {score['base']}/{n}")
    if not graded:
        print("result: not run")
        return 1
    ok = score["compiled"] == n
    print("result: " + ("pass" if ok else "fail"))
    return 0 if ok else 1


def main(argv):
    cmds = {"init": init, "check": check, "prompts": prompts, "run": run, "grade": grade}
    if len(argv) < 2 or argv[1] not in cmds:
        die("usage: eval.py init | check | prompts | run | grade (see the module docstring)")
    return cmds[argv[1]](argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
