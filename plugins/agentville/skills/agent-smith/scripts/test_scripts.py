"""Self-test for measure.py, stage.py and eval.py. Run: python3 -I scripts/test_scripts.py"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MEASURE = os.path.join(HERE, "measure.py")
STAGE = os.path.join(HERE, "stage.py")
EVAL = os.path.join(HERE, "eval.py")
ROOT = os.path.dirname(HERE)
BASE = os.path.join(ROOT, "assets", "base", "worker.md")
TEMPLATE = os.path.join(ROOT, "assets", "templates", "agent.md")
# The installed plugin copy, when this skill ships inside a plugin next to an agents/ folder.
PLUGIN_WORKER = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "agents", "worker.md")


def run(script, *args, env=None, cwd=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run([sys.executable, "-I", script, *args], capture_output=True, text=True, env=e, cwd=cwd)
    return p.returncode, p.stdout, p.stderr


def kv(out):
    d = {}
    for line in out.splitlines():
        k, _, v = line.partition(": ")
        d.setdefault(k, []).append(v)
    return d


def fails(out):
    v = kv(out)["failures"][-1]
    return set() if v == "none" else set(v.split(", "))


def warns(out):
    v = kv(out)["warnings"][-1]
    return set() if v == "none" else set(v.split(", "))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


BASE_TEXT = read(BASE)

FILLED = {
    "[[What the agent does and the roles it serves, then when to spawn it; at most 1,024 characters.]]":
        "Triages failing CI jobs. Spawn it when a CI job fails.",
    "[[Comma-separated tools the user approved; never Agent unless the user asked for it by name]]":
        "Read, Grep, Glob, Bash, Skill",
    "[[Comma-separated tools to deny, or delete this line]]": "WebSearch, WebFetch",
    "[[Personality: two to four sentences on how this agent works and what it values.]]":
        "You are patient and precise.",
    "[[Extending rule title]]": "Logs first",
    "[[the rule, with a one-clause reason]]": "read the log before the code, because the log names the test",
    "[[workflow-name]]": "triage",
    "[[worker | validator | reviewer | scout]]": "worker",
    "* **[[input-name]]:** required - default: none - [[What it is, with a literal example.]]":
        "* **log:** required - default: none - The CI log path.",
    "* **[[input-name]]:** optional - default: [[value]] - [[What it is and when the default applies.]]":
        "* **job:** optional - default: the newest - The job name.",
    "1. **[[Step title].]** [[What to do, the tool by name, the literal command; or load `Skill(namespace:name)`; "
    "or stop and hand back a spawn request.]]": "1. **Read the log.** Grep the log for FAILED.",
    "* **[[field-name]]:** always - [[What the field holds.]]": "* **cause:** always - The failing test.",
    "* **[[field-name]]:** when [[condition]] - [[What the field holds.]]":
        "* **fix:** when found - The proposed fix.",
    "* **[[Condition]]:** [[what to do, and the status token to report: completed, partial, blocked or failed]].":
        "* **No log:** return `blocked`.",
}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, text, name="agent.md"):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def measure(self, text, *flags):
        rc, out, err = run(MEASURE, self.write(text), *flags)
        self.assertIn(rc, (0, 1), err)
        return rc, out

    def fork(self, name="ci-triage"):
        out = os.path.join(self.tmp, f"{name}.md")
        rc, o, err = run(STAGE, "fork", TEMPLATE, BASE, out, name)
        self.assertEqual(rc, 0, err)
        return out, o

    def filled(self):
        path, _ = self.fork()
        text = read(path)
        for k, v in FILLED.items():
            text = text.replace(k, v)
        start = text.index("<!-- Drafting")
        text = text[:start] + text[text.index("-->", start) + 4:]
        return text


class TestMeasure(Base):
    def test_01_base_worker_passes(self):
        rc, out = self.measure(BASE_TEXT)
        self.assertEqual(rc, 0, out)
        self.assertEqual(fails(out), set())
        self.assertEqual(kv(out)["workflows"], ["4"])
        for c in ("identity", "constraints", "communication", "return"):
            self.assertIn(f"{c} | identical", kv(out)["core"])

    def test_02_filled_fork_passes(self):
        rc, out = self.measure(self.filled())
        self.assertEqual(rc, 0, out)
        self.assertIn("triage | role=worker | inputs=2 | steps=2 | outputs=cause,fix", kv(out)["workflow"])

    def test_03_template_fork_has_leftovers_only(self):
        path, _ = self.fork()
        rc, out, _ = run(MEASURE, path)
        self.assertEqual(rc, 1)
        self.assertIn("A8", fails(out))
        self.assertNotIn("A5", fails(out))

    def test_04_model_and_effort_fail(self):
        for key in ("model: sonnet", "effort: high"):
            _, out = self.measure(BASE_TEXT.replace("tools:", key + "\ntools:", 1))
            self.assertIn("A2", fails(out))

    def test_05_unknown_key_warns(self):
        rc, out = self.measure(BASE_TEXT.replace("tools:", "color: blue\ntools:", 1))
        self.assertEqual(rc, 0)
        self.assertIn("A2", warns(out))

    def test_06_agent_tool_needs_override(self):
        text = BASE_TEXT.replace("Monitor, Skill\n", "Monitor, Skill, Agent\n", 1)
        _, out = self.measure(text)
        self.assertIn("A3", fails(out))
        rc, out = self.measure(text, "--allow-agent")
        self.assertEqual(rc, 0, out)
        _, out = self.measure(BASE_TEXT.replace("Monitor, Skill\n", "Monitor, Skill, Task\n", 1))
        self.assertIn("A3", fails(out))

    def test_07_missing_tools_fails(self):
        _, out = self.measure(BASE_TEXT.replace("tools: Read, Write, Edit, Bash, Grep, Glob, TodoWrite, Monitor, Skill\n", ""))
        self.assertIn("A1", fails(out))

    def test_08_core_changed_fails(self):
        _, out = self.measure(BASE_TEXT.replace("Do not address the human.", "Address the human."))
        self.assertIn("A5", fails(out))
        self.assertIn("identity | differs", kv(out)["core"])

    def test_09_core_missing_or_misplaced_fails(self):
        start = BASE_TEXT.index("<!-- core:begin communication -->")
        end = BASE_TEXT.index("<!-- core:end communication -->") + len("<!-- core:end communication -->")
        block = BASE_TEXT[start:end]
        _, out = self.measure(BASE_TEXT.replace(block, "1. Talk plainly."))
        self.assertIn("communication | missing", kv(out)["core"])
        moved = BASE_TEXT.replace(block, "1. Talk plainly.").replace("# Exception handler\n", "# Exception handler\n\n" + block + "\n")
        _, out = self.measure(moved)
        self.assertIn("communication | misplaced", kv(out)["core"])

    def test_10_extending_rule_before_core_fails(self):
        _, out = self.measure(BASE_TEXT.replace("# Constraints\n\n", "# Constraints\n\n0. **Extra:** first.\n\n", 1))
        self.assertIn("A5", fails(out))

    def test_11_section_order(self):
        text = BASE_TEXT.replace("# Communication", "# Talk")
        _, out = self.measure(text)
        self.assertIn("A4", fails(out))

    def test_12_workflow_rules(self):
        _, out = self.measure(BASE_TEXT.replace("Role: scout\n", ""))
        self.assertIn("A6", fails(out))
        _, out = self.measure(BASE_TEXT.replace("Role: scout\n", "Role: wizard\n"))
        self.assertIn("A6", fails(out))
        _, out = self.measure(BASE_TEXT.replace("3. **Research.**", "5. **Research.**"))
        self.assertIn("A6", fails(out))
        _, out = self.measure(BASE_TEXT.replace("* **sources:** always -", "* **sources:** sometimes -"))
        self.assertIn("A6", fails(out))
        _, out = self.measure(BASE_TEXT.replace("## Workflow: scout", "## Workflow: review"))
        self.assertIn("A6", fails(out))
        lo = BASE_TEXT.index("## Workflow: implement")
        hi = BASE_TEXT.index("# Exception handler")
        _, out = self.measure(BASE_TEXT[:lo] + BASE_TEXT[hi:])
        self.assertIn("A6", fails(out))

    def test_13_exception_handler_needs_items(self):
        lo = BASE_TEXT.index("# Exception handler") + len("# Exception handler\n")
        hi = BASE_TEXT.index("# Return to parent")
        _, out = self.measure(BASE_TEXT[:lo] + "\n" + BASE_TEXT[hi:])
        self.assertIn("A7", fails(out))

    def test_14_leftovers(self):
        _, out = self.measure(BASE_TEXT + "\n[[fill me]]\n")
        self.assertIn("A8", fails(out))
        _, out = self.measure(BASE_TEXT + "\n<!-- note -->\n")
        self.assertIn("A8", fails(out))

    def test_15_foreign_namespace_fails(self):
        _, out = self.measure(BASE_TEXT.replace("agentville:relay", "anthropic-skills" + ":relay", 1))
        self.assertIn("A9", fails(out))
        rc, out = self.measure(BASE_TEXT.replace("Load `Skill(agentville:relay)`. Restate", "Load `Skill(relay)`. Restate"))
        self.assertEqual(rc, 0)
        self.assertIn("A9", warns(out))

    def test_16_granted_and_denied(self):
        _, out = self.measure(BASE_TEXT.replace("disallowedTools: WebSearch", "disallowedTools: Read, WebSearch"))
        self.assertIn("A10", fails(out))

    def test_17_size(self):
        _, out = self.measure(BASE_TEXT + "\n* **Extra:** line.\n" * 400)
        self.assertIn("A11", fails(out))

    def test_18_usage_and_read_errors(self):
        self.assertEqual(run(MEASURE)[0], 2)
        self.assertEqual(run(MEASURE, os.path.join(self.tmp, "nope.md"))[0], 2)
        self.assertEqual(run(MEASURE, self.write("no frontmatter\n"))[0], 2)
        self.assertEqual(run(MEASURE, self.write(BASE_TEXT), "--base", os.path.join(self.tmp, "x.md"))[0], 2)

    def test_19_base_copy_matches_plugin_worker(self):
        if not (os.path.isfile(PLUGIN_WORKER) and os.path.isfile(BASE)):
            self.skipTest("no plugin agents/worker.md next to this skill")
        with open(PLUGIN_WORKER, "rb") as a, open(BASE, "rb") as b:
            self.assertEqual(a.read(), b.read(), "assets/base/worker.md differs from the plugin's agents/worker.md")


class TestStage(Base):
    def create(self, *args):
        rc, out, err = run(STAGE, "create", *args, env={"TMPDIR": self.tmp})
        self.assertEqual(rc, 0, err)
        return kv(out)["path"][0]

    def test_create_and_clean(self):
        p = self.create("demo")
        self.assertTrue(os.path.isfile(os.path.join(p, ".agent-smith-staging")))
        self.assertIn("demo-", os.path.basename(p))
        self.assertEqual(run(STAGE, "clean", p)[0], 0)
        self.assertFalse(os.path.exists(p))

    def test_create_refuses_agents_folder(self):
        bad = os.path.join(self.tmp, ".claude", "agents")
        os.makedirs(bad)
        rc, _, err = run(STAGE, "create", env={"TMPDIR": bad})
        self.assertEqual(rc, 2)
        self.assertIn("refused", err)

    def test_clean_refuses_unmarked(self):
        d = os.path.join(self.tmp, "plain")
        os.mkdir(d)
        self.assertEqual(run(STAGE, "clean", d)[0], 2)
        self.assertTrue(os.path.isdir(d))
        self.assertEqual(run(STAGE, "clean", os.path.join(self.tmp, "missing"))[0], 2)

    def test_fork_pastes_core_and_name(self):
        path, out = self.fork("ci-triage")
        self.assertEqual(kv(out)["core"], ["communication, constraints, identity, return"])
        text = read(path)
        self.assertNotRegex(text, r"(?m)^\{\{ CORE")
        self.assertIn("name: ci-triage", text)
        self.assertIn("You are **ci-triage**.", text)

    def test_fork_refusals(self):
        out = os.path.join(self.tmp, "x.md")
        self.assertEqual(run(STAGE, "fork", TEMPLATE, BASE, out, "Bad Name")[0], 2)
        inside = os.path.join(self.tmp, ".claude", "agents", "x.md")
        self.assertEqual(run(STAGE, "fork", TEMPLATE, BASE, inside, "x")[0], 2)
        nocore = self.write("---\nname: b\n---\n# Role\n", "nocore.md")
        self.assertEqual(run(STAGE, "fork", TEMPLATE, nocore, out, "x")[0], 2)

    def test_seed_needs_marker(self):
        src = self.write(BASE_TEXT, "ci-triage.md")
        plain = os.path.join(self.tmp, "plain")
        os.mkdir(plain)
        self.assertEqual(run(STAGE, "seed", src, plain)[0], 2)
        p = self.create()
        rc, out, err = run(STAGE, "seed", src, p)
        self.assertEqual(rc, 0, err)
        self.assertEqual(read(os.path.join(p, "ci-triage.md")), BASE_TEXT)

    def test_install_refuses_overwrite(self):
        src = self.write(BASE_TEXT, "ci-triage.md")
        dst = os.path.join(self.tmp, "agents")
        rc, out, err = run(STAGE, "install", src, dst)
        self.assertEqual(rc, 0, err)
        self.assertEqual(kv(out)["replaced"], ["no"])
        self.assertEqual(run(STAGE, "install", src, dst)[0], 2)
        rc, out, _ = run(STAGE, "install", src, dst, "--replace")
        self.assertEqual(rc, 0)
        self.assertEqual(kv(out)["replaced"], ["yes"])
        self.assertEqual(run(STAGE, "install", os.path.join(self.tmp, "nope.md"), dst)[0], 2)

    def test_usage(self):
        self.assertEqual(run(STAGE)[0], 2)
        self.assertEqual(run(STAGE, "bogus")[0], 2)


GOOD_REPORT = """completed
outcome: done.
changed: no edits
checks: none, read-only
next: none
cause: tests/test_retry.py
"""


class TestEval(Base):
    def setUp(self):
        super().setUp()
        self.agent = self.write(self.filled(), "ci-triage.md")
        self.cases = os.path.join(self.tmp, "evals", "evals.json")
        self.out = os.path.join(self.tmp, "out")

    def fill_cases(self):
        rc, out, err = run(EVAL, "init", self.agent, self.cases)
        self.assertEqual(rc, 0, err)
        data = json.loads(read(self.cases))
        c = data["cases"][0]
        c.update(prompt="Triage tests/test_retry.py.", status="completed", expect=["test_retry"], forbid=["Edit("])
        with open(self.cases, "w") as f:
            json.dump(data, f)

    def fake_claude(self, body):
        bindir = os.path.join(self.tmp, "bin")
        os.makedirs(bindir, exist_ok=True)
        p = os.path.join(bindir, "claude")
        with open(p, "w") as f:
            f.write("#!/bin/sh\n" + body + "\n")
        os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
        return {"PATH": bindir + os.pathsep + "/usr/bin:/bin"}

    def test_init_and_check(self):
        rc, out, _ = run(EVAL, "init", self.agent, self.cases)
        self.assertEqual(rc, 0)
        self.assertEqual(kv(out)["cases"], ["1"])
        self.assertEqual(run(EVAL, "init", self.agent, self.cases)[0], 2)
        rc, out, _ = run(EVAL, "check", self.agent, self.cases)
        self.assertEqual(rc, 1)
        self.assertIn("unfilled", out)

    def test_check_needs_case_per_workflow(self):
        rc, out, _ = run(EVAL, "init", BASE, self.cases)
        data = json.loads(read(self.cases))
        self.assertEqual({c["workflow"] for c in data["cases"]}, {"implement", "validate", "review", "scout"})
        data["cases"] = data["cases"][:1]
        with open(self.cases, "w") as f:
            json.dump(data, f)
        rc, out, _ = run(EVAL, "check", BASE, self.cases)
        self.assertEqual(rc, 1)
        self.assertIn("workflow scout has no case", out)

    def test_prompts_for_dispatch(self):
        self.fill_cases()
        rc, out, err = run(EVAL, "prompts", self.agent, BASE, self.cases, self.out)
        self.assertEqual(rc, 0, err)
        lines = kv(out)["dispatch"]
        self.assertEqual(len(lines), 2)
        text = read(os.path.join(self.out, "triage-1.compiled.prompt.md"))
        self.assertIn("<role>worker</role>", text)
        self.assertIn("You are **ci-triage**.", text)

    def test_run_without_cli(self):
        self.fill_cases()
        rc, out, _ = run(EVAL, "run", self.agent, BASE, self.cases, self.out, env={"PATH": "/nonexistent"})
        self.assertEqual(rc, 2)
        self.assertIn("claude_cli: not found", out)

    def test_run_dry_run_executes_nothing(self):
        self.fill_cases()
        env = self.fake_claude("touch \"$0.ran\"; echo '{}'")
        rc, out, err = run(EVAL, "run", self.agent, BASE, self.cases, self.out, "--model", "sonnet", env=env)
        self.assertEqual(rc, 0, err)
        self.assertEqual(kv(out)["mode"], ["dry-run"])
        cmds = kv(out)["command"]
        self.assertEqual(len(cmds), 2)
        self.assertIn('"--agent" "ci-triage"', cmds[0])
        self.assertIn('"--model" "sonnet"', cmds[0])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "bin", "claude.ran")))
        self.assertTrue(os.path.isfile(os.path.join(self.out, "sandbox", ".claude", "agents", "worker.md")))

    def test_run_execute_then_grade(self):
        self.fill_cases()
        report = json.dumps({"result": GOOD_REPORT})
        env = self.fake_claude("cat <<'EOF'\n" + report + "\nEOF")
        rc, out, err = run(EVAL, "run", self.agent, BASE, self.cases, self.out, "--execute", env=env)
        self.assertEqual(rc, 0, err)
        self.assertEqual(kv(out)["run_errors"], ["0"])
        rc, out, err = run(EVAL, "grade", self.agent, self.cases, self.out)
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(kv(out)["score"], ["compiled 1/1 vs base 1/1"])

    def test_grade_failures(self):
        self.fill_cases()
        os.makedirs(self.out)
        with open(os.path.join(self.out, "triage-1.compiled.out.md"), "w") as f:
            f.write("Done!\nchanged: no edits\n")
        with open(os.path.join(self.out, "triage-1.base.out.md"), "w") as f:
            f.write(GOOD_REPORT)
        rc, out, _ = run(EVAL, "grade", self.agent, self.cases, self.out)
        self.assertEqual(rc, 1)
        line = [l for l in kv(out)["grade"] if l.startswith("triage-1 | compiled")][0]
        for reason in ("no status token", "missing core field checks", "missing workflow field cause",
                       "missing expected text"):
            self.assertIn(reason, line)
        self.assertEqual(kv(out)["score"], ["compiled 0/1 vs base 1/1"])

    def test_grade_not_run(self):
        self.fill_cases()
        os.makedirs(self.out)
        rc, out, _ = run(EVAL, "grade", self.agent, self.cases, self.out)
        self.assertEqual(rc, 1)
        self.assertEqual(kv(out)["result"], ["not run"])

    def test_usage(self):
        self.assertEqual(run(EVAL)[0], 2)
        self.assertEqual(run(EVAL, "grade")[0], 2)


if __name__ == "__main__":
    unittest.main()
