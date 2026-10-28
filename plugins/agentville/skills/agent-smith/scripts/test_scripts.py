"""Self-test for measure.py, stage.py and eval.py. Run: python3 -I scripts/test_scripts.py"""
import json
import os
import shutil
import stat
import subprocess
import sys
import re
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
    p = subprocess.run([sys.executable, "-I", script, *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=e, cwd=cwd)
    return p.returncode, p.stdout, p.stderr


def emit(text):
    """Python source for a fake `claude` that prints `text` as UTF-8."""
    return f"sys.stdout.buffer.write(({text!r} + '\\n').encode('utf-8'))"


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


NW = "TaskCreate, TaskUpdate, TaskGet, TaskList, TaskStop, Read, Write, Edit, Glob, Grep, Bash, NotebookEdit, Monitor, Skill"
BASE_TEXT = read(BASE)
# The base worker omits `tools` and inherits every tool. Fork-shaped agents need a list, so tests that
# exercise `tools` start from this copy, which grants NW and keeps the pre-1.3.0 deny list.
OLD_DENY = "WebSearch, WebFetch, EnterPlanMode, ExitPlanMode, CronCreate, CronList, CronDelete, ScheduleWakeup"
WORKER_DENY = OLD_DENY + ", Agent, SendMessage, ListAgents, TaskOutput, AskUserQuestion, SendUserFile, mcp__claude-code-remote__send_later"
assert "\ndisallowedTools: " + WORKER_DENY + "\n" in BASE_TEXT and "\ntools:" not in BASE_TEXT
TOOLS_TEXT = BASE_TEXT.replace("disallowedTools: " + WORKER_DENY, "tools: " + NW + "\ndisallowedTools: " + OLD_DENY, 1)

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
    "[[Workflow-name]]": "Triage",
    "[[worker | validator | reviewer | scout]]": "worker",
    "* **[[input-name]]:** required - default: none - [[What it is, with a literal example.]]":
        "* **log:** required - default: none - The CI log path.",
    "* **[[input-name]]:** optional - default: [[value]] - [[What it is and when the default applies.]]":
        "* **job:** optional - default: the newest - The job name.",
    "1. **[[Step title].]** [[What to do, the tool by name, the literal command; or load `Skill(namespace:name)`; "
    "or stop and hand back a spawn request.]]": "1. **Read the log.** Grep the log for FAILED.",
    "* **[[field-name]]:** always - `<[[tag]]>`: [[What the field holds.]]": "* **cause:** always - `<claims>`: The failing test.",
    "* **[[field-name]]:** when [[condition]] - `<[[tag]]>`: [[What the field holds.]]":
        "* **fix:** when found - `<claims>`: The proposed fix.",
    "* **[[Condition]]:** [[what to do, and the relay §4 status token to report]].":
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

    def fork(self, name="acme-triage"):
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
        rc, out = self.measure_as(BASE_TEXT, "worker")
        self.assertEqual(rc, 0, out)
        self.assertEqual(fails(out), set())
        self.assertEqual(kv(out)["workflows"], ["1"])
        for c in ("identity", "constraints"):
            self.assertIn(f"{c} | identical", kv(out)["core"])

    def test_02b_version_missing_or_malformed_fails(self):
        text = self.filled()
        self.assertIn("  version: 1.0.0\n", text)
        for bad in (text.replace("metadata:\n  version: 1.0.0\n", ""), text.replace("version: 1.0.0", "version: 1.0")):
            rc, out = self.measure(bad)
            self.assertEqual(rc, 1, out)
            self.assertIn("A1", fails(out))
            self.assertIn("version_error:", out)

    def test_02_filled_fork_passes(self):
        rc, out = self.measure(self.filled())
        self.assertEqual(rc, 0, out)
        self.assertIn("Triage | role=worker | inputs=2 | steps=2 | outputs=cause,fix", kv(out)["workflow"])

    def test_03_template_fork_has_leftovers_only(self):
        path, _ = self.fork()
        rc, out, _ = run(MEASURE, path)
        self.assertEqual(rc, 1)
        self.assertIn("A8", fails(out))
        self.assertNotIn("A5", fails(out))

    def test_04_model_and_effort_fail(self):
        for key in ("model: sonnet", "effort: high"):
            _, out = self.measure(TOOLS_TEXT.replace("tools:", key + "\ntools:", 1))
            self.assertIn("A2", fails(out))

    def variant_text(self, name, model="sonnet", effort="high"):
        text = re.sub(r"^name:.*$", f"name: {name}", TOOLS_TEXT, count=1, flags=re.M)
        extra = "".join(f"{k}: {v}\n" for k, v in (("model", model), ("effort", effort)) if v)
        return text.replace("tools:", extra + "tools:", 1)

    def measure_as(self, text, stem):
        rc, out, err = run(MEASURE, self.write(text, stem + ".md"))
        self.assertIn(rc, (0, 1), err)
        return rc, out

    def test_04b_variant_with_matching_keys_passes_a2(self):
        _, out = self.measure_as(self.variant_text("worker-sonnet-high"), "worker-sonnet-high")
        self.assertNotIn("A2", fails(out))

    def test_04c_variant_with_mismatching_effort_fails(self):
        _, out = self.measure_as(self.variant_text("worker-sonnet-high", effort="low"), "worker-sonnet-high")
        self.assertIn("A2", fails(out))

    def test_04d_variant_missing_a_key_fails(self):
        _, out = self.measure_as(self.variant_text("worker-sonnet-high", effort=None), "worker-sonnet-high")
        self.assertIn("A2", fails(out))

    def test_04e_base_agent_with_model_fails(self):
        _, out = self.measure_as(self.variant_text("worker", effort=None), "worker")
        self.assertIn("A2", fails(out))

    def test_04f_non_variant_name_with_model_fails(self):
        _, out = self.measure_as(self.variant_text("worker-gpt-high", model="gpt"), "worker-gpt-high")
        self.assertIn("A2", fails(out))

    def test_04g_variant_name_must_equal_file_stem(self):
        _, out = self.measure_as(self.variant_text("worker-sonnet-high"), "agent")
        self.assertIn("A2", fails(out))

    def test_04h_scout_variant_gets_the_scout_core_exemption(self):
        path = os.path.join(os.path.dirname(PLUGIN_WORKER), "scout-haiku-low.md")
        if not os.path.exists(path):
            self.skipTest("no scout-haiku-low.md next to the plugin worker")
        rc, out, err = run(MEASURE, path)
        self.assertEqual(rc, 0, out + err)
        self.assertNotIn("A5", fails(out))

    def test_05_unknown_key_warns(self):
        rc, out = self.measure(TOOLS_TEXT.replace("tools:", "color: blue\ntools:", 1))
        self.assertEqual(rc, 0)
        self.assertIn("A2", warns(out))

    def test_06_agent_tool_needs_override(self):
        text = TOOLS_TEXT.replace("Monitor, Skill\n", "Monitor, Skill, Agent\n", 1)
        _, out = self.measure(text)
        self.assertIn("A3", fails(out))
        rc, out = self.measure(text, "--allow-agent")
        self.assertEqual(rc, 0, out)
        _, out = self.measure(TOOLS_TEXT.replace("Monitor, Skill\n", "Monitor, Skill, Task\n", 1))
        self.assertIn("A3", fails(out))

    def test_07_missing_tools_fails(self):
        _, out = self.measure(TOOLS_TEXT.replace("tools: "+NW+"\n", ""))
        self.assertIn("A1", fails(out))

    def no_tools_as(self, name, stem=None):
        """BASE_TEXT (no `tools` line) renamed to `name` and measured from the file `<stem>.md`."""
        text = re.sub(r"^name:.*$", f"name: {name}", BASE_TEXT, count=1, flags=re.M)
        return self.measure_as(text, stem or name)[1]

    def test_07b_worker_without_tools_passes(self):
        out = self.no_tools_as("worker")
        self.assertNotIn("A1", fails(out))
        self.assertIn("tools_omitted: yes", out)

    def test_07c_worker_variant_without_tools_passes(self):
        text = self.variant_text("worker-sonnet-high").replace("tools: " + NW + "\n", "")
        self.assertNotIn("\ntools:", text)
        _, out = self.measure_as(text, "worker-sonnet-high")
        self.assertNotIn("A1", fails(out))
        self.assertNotIn("A2", fails(out))

    def test_07d_other_agents_without_tools_fail(self):
        for name in ("validator", "reviewer", "scout", "acme-triage", "validator-sonnet-high", "worker-gpt-high"):
            self.assertIn("A1", fails(self.no_tools_as(name)), name)
        self.assertIn("A1", fails(self.no_tools_as("worker", stem="agent")))

    def test_08_core_changed_fails(self):
        _, out = self.measure(TOOLS_TEXT.replace("Do not address the human.", "Address the human."))
        self.assertIn("A5", fails(out))
        self.assertIn("identity | differs", kv(out)["core"])

    def test_09_core_missing_or_misplaced_fails(self):
        start = TOOLS_TEXT.index("<!-- core:begin identity -->")
        end = TOOLS_TEXT.index("<!-- core:end identity -->") + len("<!-- core:end identity -->")
        block = TOOLS_TEXT[start:end]
        _, out = self.measure(TOOLS_TEXT.replace(block, "1. Talk plainly."))
        self.assertIn("identity | missing", kv(out)["core"])
        moved = TOOLS_TEXT.replace(block, "1. Talk plainly.").replace("# Exception handler\n", "# Exception handler\n\n" + block + "\n")
        _, out = self.measure(moved)
        self.assertIn("identity | misplaced", kv(out)["core"])

    def test_10_extending_rule_before_core_fails(self):
        _, out = self.measure(TOOLS_TEXT.replace("# Constraints\n\n", "# Constraints\n\n0. **Extra:** first.\n\n", 1))
        self.assertIn("A5", fails(out))

    def test_11_section_order(self):
        text = TOOLS_TEXT.replace("# Exception handler", "# Talk")
        _, out = self.measure(text)
        self.assertIn("A4", fails(out))

    def test_12_workflow_rules(self):
        _, out = self.measure(TOOLS_TEXT.replace("Role: worker\n", ""))
        self.assertIn("A6", fails(out))
        _, out = self.measure(TOOLS_TEXT.replace("Role: worker\n", "Role: wizard\n"))
        self.assertIn("A6", fails(out))
        _, out = self.measure(TOOLS_TEXT.replace("3. **Break it down.**", "5. **Break it down.**"))
        self.assertIn("A6", fails(out))
        _, out = self.measure(TOOLS_TEXT.replace("* **steps:** always -", "* **steps:** sometimes -"))
        self.assertIn("A6", fails(out))
        _, out = self.measure(TOOLS_TEXT.replace("## Execute", "## Bad Name"))
        self.assertIn("A6", fails(out))
        lo = TOOLS_TEXT.index("## Execute")
        hi = TOOLS_TEXT.index("# Exception handler")
        _, out = self.measure(TOOLS_TEXT[:lo] + TOOLS_TEXT[hi:])
        self.assertIn("A6", fails(out))

    def test_13_exception_handler_needs_items(self):
        lo = TOOLS_TEXT.index("# Exception handler") + len("# Exception handler\n")
        _, out = self.measure(TOOLS_TEXT[:lo] + "\n")
        self.assertIn("A7", fails(out))

    def test_14_leftovers(self):
        _, out = self.measure(TOOLS_TEXT + "\n[[fill me]]\n")
        self.assertIn("A8", fails(out))
        _, out = self.measure(TOOLS_TEXT + "\n<!-- note -->\n")
        self.assertIn("A8", fails(out))

    def test_15_foreign_namespace_fails(self):
        _, out = self.measure(TOOLS_TEXT.replace("agentville:relay", "anthropic-skills" + ":relay", 1))
        self.assertIn("A9", fails(out))
        rc, out = self.measure(TOOLS_TEXT.replace("1. **Read the brief.** Restate", "1. **Read the brief.** Load `Skill(relay)`. Restate"))
        self.assertEqual(rc, 0)
        self.assertIn("A9", warns(out))

    def test_16_granted_and_denied(self):
        _, out = self.measure(TOOLS_TEXT.replace("disallowedTools: WebSearch", "disallowedTools: Read, WebSearch"))
        self.assertIn("A10", fails(out))

    def test_17_size(self):
        _, out = self.measure(TOOLS_TEXT + "\n* **Extra:** line.\n" * 400)
        self.assertIn("A11", fails(out))

    def test_18_usage_and_read_errors(self):
        self.assertEqual(run(MEASURE)[0], 2)
        self.assertEqual(run(MEASURE, os.path.join(self.tmp, "nope.md"))[0], 2)
        self.assertEqual(run(MEASURE, self.write("no frontmatter\n"))[0], 2)
        self.assertEqual(run(MEASURE, self.write(TOOLS_TEXT), "--base", os.path.join(self.tmp, "x.md"))[0], 2)

    def test_20_constraints_core_needs_status_line(self):
        rc, out = self.measure(TOOLS_TEXT)
        self.assertEqual(kv(out)["status_line_rule"], ["yes"])
        weak = TOOLS_TEXT.replace("`<status>` comes first and holds one of", "the status comes with one of")
        base = self.write(weak, "weak-base.md")
        rc, out = self.measure(weak, "--base", base)
        self.assertEqual(rc, 1)
        self.assertEqual(fails(out), {"A16"})
        self.assertEqual(kv(out)["status_line_rule"], ["no"])

    def test_19_base_copy_matches_plugin_worker(self):
        if not (os.path.isfile(PLUGIN_WORKER) and os.path.isfile(BASE)):
            self.skipTest("no plugin agents/worker.md next to this skill")
        with open(PLUGIN_WORKER, "rb") as a, open(BASE, "rb") as b:
            self.assertEqual(a.read(), b.read(), "assets/base/worker.md differs from the plugin's agents/worker.md")

    def test_21_pod_lead_is_standalone(self):
        text = ("---\nname: pod-lead\ndescription: Standalone lead of a pod's agents.\n"
                "tools: Skill, Agent(worker)\nmetadata:\n  version: 1.0.0\n---\n\n# Role\n\nYou are pod-lead.\n\n"
                "# Constraints\n\n1. **Orchestrate:** route every request through `Skill(agentville:orchestrate)`.\n\n"
                "# Workflows\n\n## Conduct\n\nRole: pod-lead\n\n### Input\n\n"
                "* **request:** required - default: none - The request.\n\n### Process\n\n"
                "1. **Route.** Load `Skill(agentville:orchestrate)`.\n\n### Output\n\n"
                "* **reply:** always - The reply.\n\n# Exception handler\n\n* **Unclear:** ask.\n")
        # standalone skips A5, A6 and A16 only: holding Agent fails A3 unless --allow-agent is given
        rc, out = self.measure(text)
        self.assertEqual(rc, 1, out)
        self.assertEqual(fails(out), {"A3"}, out)
        rc, out = self.measure(text, "--allow-agent")
        self.assertEqual(rc, 0, out)
        self.assertIn("standalone", kv(out))
        # standalone comes from declaring no base and holding no core block, not from the name
        rc, out = self.measure(text.replace("name: pod-lead", "name: other"), "--allow-agent")
        self.assertEqual(rc, 0, out)
        self.assertIn("standalone", kv(out))
        rc, out = self.measure(text.replace("model", "x").replace("---\n\n", "model: opus\n---\n\n", 1))
        self.assertIn("A2", fails(out))

    def test_22_message_lead_is_standalone(self):
        text = ("---\nname: acme-lead\ndescription: Standalone lead over several pod-leads.\n"
                "tools: Skill, ListAgents, SendMessage\nmetadata:\n  version: 1.0.0\n---\n\n# Role\n\nYou are acme-lead.\n\n"
                "# Constraints\n\n1. **Never spawn:** move work only by message.\n\n"
                "# Workflows\n\n## Triage-Alert\n\nRole: acme-lead\n\n### Input\n\n"
                "* **alert:** required - default: none - The alert.\n\n### Process\n\n"
                "1. **Hand off.** Message a pod-lead.\n\n### Output\n\n"
                "* **assignment:** always - The assignment.\n\n# Exception handler\n\n* **Unclear:** ask.\n")
        rc, out = self.measure(text)
        self.assertEqual(rc, 0, out)
        self.assertIn("standalone", kv(out))
        rc, out = self.measure(text.replace("name: acme-lead", "name: other"))
        self.assertEqual(rc, 0, out)
        self.assertIn("standalone", kv(out))
        # a single core marker makes it a worker fork again, held to the core-block checks
        rc, out = self.measure(text.replace("# Constraints\n\n", "# Constraints\n\n<!-- core:begin constraints -->\n", 1))
        self.assertTrue({"A5", "A16"} <= fails(out), out)

    STANDALONE_BASE = ("---\nname: pod-lead\ndescription: Standalone lead of a pod's agents.\n"
                       "tools: Skill, Agent(worker)\nmetadata:\n  version: 1.0.0\n---\n\n# Role\n\nYou are pod-lead.\n\n"
                       "# Constraints\n\n1. **Orchestrate:** route every request through `Skill(agentville:orchestrate)`.\n\n"
                       "   Do:\n   * Route the question `Which file sets the retry limit?` too.\n\n"
                       "2. **Delegate:** do no work yourself.\n\n"
                       "# Workflows\n\n## Conduct\n\nRole: pod-lead\n\n### Input\n\n"
                       "* **request:** required - default: none - The request.\n\n### Process\n\n"
                       "1. **Route.** Load `Skill(agentville:orchestrate)`.\n\n### Output\n\n"
                       "* **reply:** always - The reply.\n\n# Exception handler\n\n* **Unclear:** ask.\n")

    def measure_isolated(self, path, *flags):
        """Measure `path` with the project and home folders inside the test folder, so only fixtures resolve."""
        rc, out, err = run(MEASURE, path, *flags, env={"CLAUDE_PROJECT_DIR": self.tmp, "HOME": self.tmp})
        self.assertIn(rc, (0, 1), err)
        return rc, out

    def fork_from(self, base_path, name):
        """Fork the template from `base_path` with stage.py and fill it as `filled` does."""
        out = os.path.join(self.tmp, f"{name}.md")
        rc, o, err = run(STAGE, "fork", TEMPLATE, base_path, out, name)
        self.assertEqual(rc, 0, err)
        text = read(out)
        for k, v in FILLED.items():
            text = text.replace(k, v)
        start = text.index("<!-- Drafting")
        text = text[:start] + text[text.index("-->", start) + 4:]
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return out, o

    def test_23_default_worker_fork_passes(self):
        text = self.filled()
        self.assertNotIn("base:", text.split("\n---\n", 1)[0])
        rc, out = self.measure(text)
        self.assertEqual(rc, 0, out)
        self.assertTrue(kv(out)["base"][0].startswith("worker (default)"), out)
        rc, out = self.measure(text.replace("  version: 1.0.0\n", "  version: 1.0.0\n  base: worker\n", 1))
        self.assertEqual(rc, 0, out)
        self.assertNotIn("standalone", kv(out))

    def test_24_standalone_without_base_passes(self):
        text = self.STANDALONE_BASE.replace("name: pod-lead", "name: acme-lead")
        # a standalone agent holding Agent fails A3 without the flag and passes with it
        rc, out = self.measure(text)
        self.assertEqual(rc, 1, out)
        self.assertEqual(fails(out), {"A3"}, out)
        rc, out = self.measure(text, "--allow-agent")
        self.assertEqual(rc, 0, out)
        self.assertEqual(kv(out)["base"], ["none"])
        self.assertIn("standalone", kv(out))

    def test_25_fork_of_standalone_base(self):
        base = self.write(self.STANDALONE_BASE, "pod-lead.md")
        path, o = self.fork_from(base, "acme-lead")
        self.assertIn("core: base pod-lead", o)
        self.assertEqual(kv(o)["next-rule"], ["3"])
        text = read(path)
        self.assertIn("  base: pod-lead\n", text)
        self.assertIn("\n3. **Logs first:**", text)
        self.assertNotIn("core:begin", text)
        rc, out = self.measure_isolated(path)
        self.assertEqual(rc, 0, out)
        self.assertEqual(kv(out)["core"], ["base pod-lead | identical"])
        self.assertNotIn("standalone", kv(out))
        # a changed copy fails A5
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace("do no work yourself.", "do some work yourself."))
        rc, out = self.measure_isolated(path)
        self.assertEqual(rc, 1, out)
        self.assertEqual(fails(out), {"A5"})
        self.assertEqual(kv(out)["core"], ["base pod-lead | differs"])
        # a missing copy and an extending rule before the copy fail A5 too
        lo, hi = text.index("<!-- base:begin pod-lead -->"), text.index("<!-- base:end pod-lead -->") + 26
        for bad, state in ((text[:lo] + "1. **Talk plainly.**" + text[hi:], "missing"),
                           (text.replace("# Constraints\n\n", "# Constraints\n\n0. **Extra:** first.\n\n", 1),
                            "not first in Constraints")):
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(bad)
            rc, out = self.measure_isolated(path)
            self.assertIn("A5", fails(out), out)
            self.assertEqual(kv(out)["core"], [f"base pod-lead | {state}"])
        # the base's Agent tool is not inherited: A3 still needs --allow-agent
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace("tools: Read, Grep", "tools: Agent(worker), Read, Grep", 1))
        self.assertIn("A3", fails(self.measure_isolated(path)[1]))
        self.assertEqual(self.measure_isolated(path, "--allow-agent")[0], 0)

    def test_25b_inline_metadata_declares_base_and_version(self):
        base = self.write(self.STANDALONE_BASE, "pod-lead.md")
        path, o = self.fork_from(base, "acme-lead")
        text = read(path)
        head, body = text.split("\n---\n", 1)
        block = re.search(r"metadata:\n(?:[ \t]+\S.*\n?)+", head + "\n").group(0)
        for inline in ("metadata: {version: 1.0.0, base: pod-lead}\n", "metadata: {base: pod-lead, version: 1.0.0}\n"):
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write((head + "\n").replace(block, inline, 1).rstrip("\n") + "\n---\n" + body)
            rc, out = self.measure_isolated(path)
            self.assertEqual(rc, 0, out)
            self.assertEqual(kv(out)["core"], ["base pod-lead | identical"], out)
            self.assertTrue(kv(out)["base"][0].startswith("pod-lead |"), out)

    def test_26_fork_of_a_worker_fork_keeps_core_check(self):
        base = self.write(self.filled().replace("name: acme-triage", "name: acme-base", 1), "acme-base.md")
        path, o = self.fork_from(base, "acme-child")
        self.assertIn("core: constraints, identity", o)
        self.assertIn("  base: acme-base\n", read(path))
        rc, out = self.measure_isolated(path)
        self.assertEqual(rc, 0, out)
        self.assertTrue(kv(out)["base"][0].endswith("| worker fork"), out)
        changed = read(path).replace("Do not address the human.", "Address the human.")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(changed)
        rc, out = self.measure_isolated(path)
        self.assertEqual(fails(out), {"A5"})

    def test_27_unknown_base_fails_a19(self):
        for value, message in (("no-such-base", "not found"), ("../pod-lead", "kebab-case")):
            text = TOOLS_TEXT.replace("  version: ", "  base: " + value + "\n  version: ", 1)
            self.assertIn("base: " + value, text)
            rc, out = self.measure_isolated(self.write(text, "acme-x.md"))
            self.assertEqual(rc, 1, out)
            self.assertIn("A19", fails(out))
            self.assertIn(message, kv(out)["base_error"][0])

    def test_slot_direct_call_fails_a18(self):
        _, out = self.measure(TOOLS_TEXT + "\n* Resolve with `Skill(agentville:toolbelt)` now.\n")
        self.assertIn("A18", fails(out))
        self.assertTrue(any(l.startswith("slot_direct_calls:") and "Skill(agentville:toolbelt)" in l for l in out.splitlines()))

    def test_slot_plugin_default_mention_allowed(self):
        _, out = self.measure(TOOLS_TEXT + "\n* The slot default is the plugin default `Skill(agentville:toolbelt)`.\n")
        self.assertNotIn("A18", fails(out))

    def test_slot_plugin_default_then_call_fails_a18(self):
        _, out = self.measure(TOOLS_TEXT + "\n* Fall back to the plugin default, then call Skill(agentville:toolbelt).\n")
        self.assertIn("A18", fails(out))
        self.assertTrue(any(l.startswith("slot_direct_calls:") and "Skill(agentville:toolbelt)" in l for l in out.splitlines()))

    def test_slot_call_with_source_outside_record_fails_a18(self):
        for text in ("Call `Skill(agentville:toolbelt) (project-x)` now.", "Call `Skill(agentville:toolbelt) (project-rules)` now.",
                     "Write `toolbelt: Skill(agentville:toolbelt) (project-rules)` now."):
            _, out = self.measure(TOOLS_TEXT + f"\n* {text}\n")
            self.assertIn("A18", fails(out), text)

    def test_slot_call_followed_by_plugin_default_record_allowed(self):
        _, out = self.measure(TOOLS_TEXT + "\n* Name `Skill(agentville:toolbelt) (plugin-default)` in the claims.\n")
        self.assertNotIn("A18", fails(out))

    def test_slot_imperative_verb_before_default_call_fails_a18(self):
        for text in ("Call `Skill(agentville:toolbelt) (plugin-default)` now.", "Load the plugin default `Skill(agentville:workspace)`.",
                     "Then run Skill(agentville:draft) (plugin-default).", "Invoke the plugin default Skill(agentville:plan).",
                     "Use `Skill(agentville:report)` (plugin-default)."):
            _, out = self.measure(TOOLS_TEXT + f"\n* {text}\n")
            self.assertIn("A18", fails(out), text)
            self.assertTrue(any(l.startswith("slot_direct_calls:") and "Skill(agentville:" in l for l in out.splitlines()), text)

    def test_slot_non_imperative_default_description_still_allowed_a18(self):
        for text in ("The slot falls back to the plugin default `Skill(agentville:draft)`.", "Name `Skill(agentville:plan) (plugin-default)` in the claims.",
                     "Write `report: agentville:report (plugin-default)` in the claims."):
            _, out = self.measure(TOOLS_TEXT + f"\n* {text}\n")
            self.assertNotIn("A18", fails(out), text)

    def test_slot_record_needs_known_source_and_own_slot(self):
        for text in ("toolbelt: agentville:toolbelt (project-x)", "workspace: agentville:toolbelt (project-rules)"):
            _, out = self.measure(TOOLS_TEXT + f"\n* Write `{text}` in the claims.\n")
            self.assertIn("A18", fails(out), text)
        _, out = self.measure(TOOLS_TEXT + "\n* Write `toolbelt: agentville:toolbelt (project-rules)` in the claims.\n")
        self.assertNotIn("A18", fails(out))

    def test_slot_without_context_injection_fails_a18(self):
        text = TOOLS_TEXT.replace("Skill(agentville:context-injection)", "Skill(agentville:relay)")
        _, out = self.measure(text + "\n* Use the `toolbelt` slot.\n")
        self.assertIn("A18", fails(out))
        self.assertTrue(any(l.startswith("slot_without_context_injection:") and "toolbelt" in l for l in out.splitlines()), out)

    def test_slot_via_context_injection_passes(self):
        _, out = self.measure(TOOLS_TEXT + "\n* Use the `toolbelt` slot, resolved with `Skill(agentville:context-injection)`.\n")
        self.assertNotIn("A18", fails(out))

    def test_slot_plugin_default_elsewhere_on_line_does_not_exempt(self):
        old = "and report a fallback to the plugin default in `<deviations>`."
        self.assertIn(old, TOOLS_TEXT)
        _, out = self.measure(TOOLS_TEXT.replace(old, old + " Then call Skill(agentville:toolbelt)."))
        self.assertIn("A18", fails(out))
        self.assertTrue(any(l.startswith("slot_direct_calls:") and "Skill(agentville:toolbelt)" in l for l in out.splitlines()))

    def test_slot_other_call_forms_fail_a18(self):
        for form in ("agentville:toolbelt", "/agentville:toolbelt", "Skill(toolbelt)"):
            _, out = self.measure(TOOLS_TEXT + f"\n* Load {form} first.\n")
            self.assertIn("A18", fails(out), form)

    def test_slot_record_with_source_allowed(self):
        _, out = self.measure(TOOLS_TEXT + "\n* Write `workspace: agentville:workspace (plugin-default)` in the claims.\n")
        self.assertNotIn("A18", fails(out))


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
        path, out = self.fork("acme-triage")
        self.assertEqual(kv(out)["core"], ["constraints, identity"])
        text = read(path)
        self.assertNotRegex(text, r"(?m)^\{\{ CORE")
        self.assertIn("name: acme-triage", text)
        self.assertIn("You are **acme-triage**.", text)

    def test_fork_refusals(self):
        out = os.path.join(self.tmp, "x.md")
        self.assertEqual(run(STAGE, "fork", TEMPLATE, BASE, out, "Bad Name")[0], 2)
        inside = os.path.join(self.tmp, ".claude", "agents", "x.md")
        self.assertEqual(run(STAGE, "fork", TEMPLATE, BASE, inside, "x")[0], 2)
        nocore = self.write("---\nname: b\n---\n# Role\n", "nocore.md")
        self.assertEqual(run(STAGE, "fork", TEMPLATE, nocore, out, "x")[0], 2)

    def test_seed_needs_marker(self):
        src = self.write(TOOLS_TEXT, "acme-triage.md")
        plain = os.path.join(self.tmp, "plain")
        os.mkdir(plain)
        self.assertEqual(run(STAGE, "seed", src, plain)[0], 2)
        p = self.create()
        rc, out, err = run(STAGE, "seed", src, p)
        self.assertEqual(rc, 0, err)
        self.assertEqual(read(os.path.join(p, "acme-triage.md")), TOOLS_TEXT)

    def roots(self):
        project, user = os.path.join(self.tmp, "proj"), os.path.join(self.tmp, "home")
        os.makedirs(project)
        os.makedirs(user)
        return project, user

    def install(self, src, folder, scope, *extra):
        project, user = self.roots_cache
        return run(STAGE, "install", src, folder, "--scope", scope,
                   "--project-root", project, "--user-root", user, *extra)

    def test_install_refuses_overwrite(self):
        src = self.write(TOOLS_TEXT, "acme-triage.md")
        self.roots_cache = self.roots()
        dst = os.path.join(self.roots_cache[0], ".claude", "agents")
        rc, out, err = self.install(src, dst, "project")
        self.assertEqual(rc, 0, err)
        self.assertEqual(kv(out)["replaced"], ["no"])
        self.assertEqual(self.install(src, dst, "project")[0], 2)
        rc, out, _ = self.install(src, dst, "project", "--replace")
        self.assertEqual(rc, 0)
        self.assertEqual(kv(out)["replaced"], ["yes"])
        self.assertEqual(self.install(os.path.join(self.tmp, "nope.md"), dst, "project")[0], 2)

    def test_install_accepts_project_and_user_scope(self):
        src = self.write(TOOLS_TEXT, "acme-triage.md")
        self.roots_cache = project, user = self.roots()
        for scope, root in (("project", project), ("user", user)):
            dst = os.path.join(root, ".claude", "agents")
            rc, out, err = self.install(src, dst, scope)
            self.assertEqual(rc, 0, err)
            self.assertEqual(kv(out)["written"], [os.path.join(os.path.realpath(dst), "acme-triage.md")])
            self.assertTrue(os.path.isfile(os.path.join(dst, "acme-triage.md")))

    def test_install_refuses_plugin_target(self):
        src = self.write(TOOLS_TEXT, "acme-triage.md")
        self.roots_cache = project, user = self.roots()
        plugin = os.path.join(project, "plugins", "acme")
        os.makedirs(os.path.join(plugin, ".claude-plugin"))
        with open(os.path.join(plugin, ".claude-plugin", "plugin.json"), "w", encoding="utf-8", newline="\n") as f:
            f.write("{}")
        for scope in ("project", "user"):
            for dst in (os.path.join(plugin, "agents"), os.path.join(plugin, ".claude", "agents"),
                        os.path.join(project, "plugins", "other", "agents"),
                        os.path.join(plugin, ".claude-plugin")):
                rc, out, err = self.install(src, dst, scope)
                self.assertEqual(rc, 2, dst)
                self.assertIn("refused", err)
                self.assertFalse(os.path.exists(os.path.join(dst, "acme-triage.md")), dst)
        # a project root that is itself a plugin is refused even at its own .claude/agents
        rc, _, err = run(STAGE, "install", src, os.path.join(plugin, ".claude", "agents"), "--scope", "project",
                         "--project-root", plugin, "--user-root", user)
        self.assertEqual(rc, 2)
        self.assertIn("plugin", err)
        self.assertFalse(os.path.exists(os.path.join(plugin, ".claude", "agents", "acme-triage.md")))

    def test_install_accepts_project_root_under_plugins_folder(self):
        src = self.write(TOOLS_TEXT, "acme-triage.md")
        project = os.path.join(self.tmp, "plugins", "myapp")
        user = os.path.join(self.tmp, "home")
        os.makedirs(project)
        os.makedirs(user)
        dst = os.path.join(project, ".claude", "agents")
        rc, _, err = run(STAGE, "install", src, dst, "--scope", "project",
                         "--project-root", project, "--user-root", user)
        self.assertEqual(rc, 0, err)
        self.assertTrue(os.path.isfile(os.path.join(dst, "acme-triage.md")))

    def test_install_refuses_other_folders_and_missing_scope(self):
        src = self.write(TOOLS_TEXT, "acme-triage.md")
        self.roots_cache = project, user = self.roots()
        free = os.path.join(self.tmp, "elsewhere")
        self.assertEqual(self.install(src, free, "project")[0], 2)
        self.assertEqual(self.install(src, os.path.join(project, ".claude", "skills"), "project")[0], 2)
        self.assertEqual(self.install(src, os.path.join(project, ".claude", "agents", "sub"), "project")[0], 2)
        # the user root is not the project root
        self.assertEqual(self.install(src, os.path.join(user, ".claude", "agents"), "project")[0], 2)
        self.assertEqual(self.install(src, os.path.join(project, ".claude", "agents"), "plugin")[0], 2)
        self.assertEqual(run(STAGE, "install", src, os.path.join(project, ".claude", "agents"),
                             "--project-root", project)[0], 2)
        self.assertFalse(os.path.exists(free))

    def test_seed_refuses_plugin_source(self):
        p = self.create()
        plugin_agent = os.path.join(self.tmp, "plugins", "acme", "agents", "x.md")
        os.makedirs(os.path.dirname(plugin_agent))
        os.makedirs(os.path.join(self.tmp, "plugins", "acme", ".claude-plugin"))
        with open(os.path.join(self.tmp, "plugins", "acme", ".claude-plugin", "plugin.json"), "w", encoding="utf-8", newline="\n") as f:
            f.write("{}")
        with open(plugin_agent, "w", encoding="utf-8", newline="\n") as f:
            f.write(TOOLS_TEXT)
        rc, _, err = run(STAGE, "seed", plugin_agent, p)
        self.assertEqual(rc, 2)
        self.assertIn("plugin", err)
        self.assertFalse(os.path.exists(os.path.join(p, "x.md")))

    def test_usage(self):
        self.assertEqual(run(STAGE)[0], 2)
        self.assertEqual(run(STAGE, "bogus")[0], 2)


GOOD_REPORT = """<status>completed</status>
<outcome>
Root cause found in apps/api/tests/test_retry.py.
</outcome>
<claims>
- The failing test is apps/api/tests/test_retry.py. verified: pytest apps/api/tests/test_retry.py -q fails.
</claims>
<artefacts>
none
</artefacts>
<open>
none
</open>
<deviations>
none
</deviations>
"""


class TestEval(Base):
    def setUp(self):
        super().setUp()
        self.agent = self.write(self.filled(), "acme-triage.md")
        self.cases = os.path.join(self.tmp, "evals", "evals.json")
        self.out = os.path.join(self.tmp, "out")

    def fill_cases(self):
        rc, out, err = run(EVAL, "init", self.agent, self.cases)
        self.assertEqual(rc, 0, err)
        data = json.loads(read(self.cases))
        c = data["cases"][0]
        c.update(prompt="Triage apps/api/tests/test_retry.py.", status="completed", expect=["test_retry"], forbid=["Edit("])
        with open(self.cases, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f)

    def fake_claude(self, body):
        """Put a stand-in `claude` first on PATH; `body` is Python source run by the test interpreter.

        POSIX gets an executable sh shim, Windows a claude.cmd shim, and both call claude.py next to them.
        The host's own PATH follows the shim folder, so no system folder is hard-coded.
        """
        bindir = os.path.join(self.tmp, "bin")
        os.makedirs(bindir, exist_ok=True)
        with open(os.path.join(bindir, "claude.py"), "w", encoding="utf-8", newline="\n") as f:
            f.write("import os, sys\n" + body + "\n")
        if os.name == "nt":
            shim, text = "claude.cmd", f'@echo off\r\n"{sys.executable}" "%~dp0claude.py" %*\r\n'
        else:
            shim, text = "claude", f'#!/bin/sh\nexec "{sys.executable}" "$(dirname "$0")/claude.py" "$@"\n'
        p = os.path.join(bindir, shim)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        if os.name != "nt":
            os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
        return {"PATH": bindir + os.pathsep + os.environ.get("PATH", "")}

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
        self.assertEqual({c["workflow"] for c in data["cases"]}, {"Execute"})
        data["cases"] = []
        with open(self.cases, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f)
        rc, out, _ = run(EVAL, "check", BASE, self.cases)
        self.assertEqual(rc, 1)
        self.assertIn("workflow Execute has no case", out)

    def test_prompts_for_dispatch(self):
        self.fill_cases()
        rc, out, err = run(EVAL, "prompts", self.agent, BASE, self.cases, self.out)
        self.assertEqual(rc, 0, err)
        lines = kv(out)["dispatch"]
        self.assertEqual(len(lines), 2)
        text = read(os.path.join(self.out, "triage-1.compiled.prompt.md"))
        self.assertIn("<role>worker</role>", text)
        self.assertIn("You are **acme-triage**.", text)

    def test_prompts_keep_sandbox_with_report(self):
        self.fill_cases()
        rc, out, err = run(EVAL, "prompts", self.agent, BASE, self.cases, self.out)
        self.assertEqual(rc, 0, err)
        sb = os.path.join(self.out, "sandbox", "triage-1.compiled")
        with open(os.path.join(sb, "child.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write("effect")
        with open(os.path.join(self.out, "triage-1.compiled.out.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(GOOD_REPORT)
        rc, out, err = run(EVAL, "prompts", self.agent, BASE, self.cases, self.out)
        self.assertEqual(rc, 0, err)
        self.assertTrue(os.path.isfile(os.path.join(sb, "child.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.out, "sandbox", "triage-1.base", "child.txt")))

    def test_case_role_defaults_to_first_workflow(self):
        self.fill_cases()
        data = json.loads(read(self.cases))
        del data["cases"][0]["role"]
        with open(self.cases, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f)
        rc, out, err = run(EVAL, "check", self.agent, self.cases)
        self.assertEqual(rc, 0, err)
        self.assertIn("role=worker", out)

    def test_run_without_cli(self):
        self.fill_cases()
        rc, out, _ = run(EVAL, "run", self.agent, BASE, self.cases, self.out, env={"PATH": "/nonexistent"})
        self.assertEqual(rc, 2)
        self.assertIn("claude_cli: not found", out)

    def test_run_dry_run_executes_nothing(self):
        self.fill_cases()
        env = self.fake_claude("open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'claude.ran'), 'w', encoding='utf-8').close()\n"
                               "print('{}')")
        rc, out, err = run(EVAL, "run", self.agent, BASE, self.cases, self.out, "--model", "sonnet", env=env)
        self.assertEqual(rc, 0, err)
        self.assertEqual(kv(out)["mode"], ["dry-run"])
        cmds = kv(out)["command"]
        self.assertEqual(len(cmds), 2)
        self.assertIn('"--agent" "acme-triage"', cmds[0])
        self.assertIn('"--model" "sonnet"', cmds[0])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "bin", "claude.ran")))
        self.assertTrue(os.path.isfile(os.path.join(self.out, "sandbox", "triage-1.base", ".claude", "agents",
                                                    "worker.md")))
        self.assertEqual(kv(out)["runs"], ["2"])

    def test_run_command_line(self):
        self.fill_cases()
        env = self.fake_claude("print('{}')")
        work = os.path.join(self.tmp, "work")
        os.makedirs(work)
        rc, out, err = run(EVAL, "run", self.agent, BASE, self.cases, self.out, "--model", "sonnet",
                           "--workdir", work, env=env)
        self.assertEqual(rc, 0, err)
        plugin = os.path.dirname(os.path.dirname(ROOT))
        if os.path.isfile(os.path.join(plugin, ".claude-plugin", "plugin.json")):
            self.assertEqual(kv(out)["plugin_dir"], [plugin])
        self.assertEqual(kv(out)["model"], ["sonnet"])
        compiled, base = kv(out)["command"]
        args, rest, dec = [], base.split(" | ", 3)[-1], json.JSONDecoder()
        while rest.strip():
            v, i = dec.raw_decode(rest.strip())
            args.append(v)
            rest = rest.strip()[i:]
        # The base worker omits `tools` and inherits every tool, but dontAsk auto-denies tools that are not
        # pre-approved, so its run passes the session-safe built-in set as --allowedTools.
        self.assertFalse([l for l in read(BASE).splitlines() if l.startswith("tools:")])
        self.assertEqual(args[args.index("--allowedTools") + 1], NW.replace(", ", ","))
        self.assertEqual(args[args.index("--add-dir") + 1], work)
        self.assertEqual(args[args.index("--model") + 1], "sonnet")
        self.assertEqual(args[args.index("--permission-mode") + 1], "dontAsk")
        # Variadic flags are followed by a single-value flag, so the prompt stays the last argument.
        self.assertEqual(args[args.index("--add-dir") + 2], "--output-format")
        self.assertTrue(args[-1].startswith("<role>worker</role>"))
        self.assertIn('"--allowedTools"', compiled)
        rc, out, err = run(EVAL, "run", self.agent, BASE, self.cases, self.out, "--plugin-dir", work, env=env)
        self.assertEqual(rc, 0, err)
        self.assertEqual(kv(out)["plugin_dir"], [work])
        self.assertIn('"--plugin-dir" ' + json.dumps(work), kv(out)["command"][0])
        self.assertEqual(kv(out)["model"], ["session default"])
        self.assertNotIn('"--model"', kv(out)["command"][0])

    def test_run_execute_then_grade(self):
        self.fill_cases()
        report = json.dumps({"result": GOOD_REPORT})
        env = self.fake_claude(emit(report))
        rc, out, err = run(EVAL, "run", self.agent, BASE, self.cases, self.out, "--execute", env=env)
        self.assertEqual(rc, 0, err)
        self.assertEqual(kv(out)["run_errors"], ["0"])
        rc, out, err = run(EVAL, "grade", self.agent, self.cases, self.out)
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(kv(out)["score"], ["compiled 1/1 vs base 1/1"])

    def test_grade_failures(self):
        self.fill_cases()
        os.makedirs(self.out)
        with open(os.path.join(self.out, "triage-1.compiled.out.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("Done!\n<outcome>fine</outcome>\n")
        with open(os.path.join(self.out, "triage-1.base.out.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(GOOD_REPORT)
        rc, out, _ = run(EVAL, "grade", self.agent, self.cases, self.out)
        self.assertEqual(rc, 1)
        line = [l for l in kv(out)["grade"] if l.startswith("triage-1 | compiled")][0]
        for reason in ("first line is not <status>TOKEN</status>", "missing tag <status>", "missing tag <claims>",
                       "missing expected text"):
            self.assertIn(reason, line)
        self.assertEqual(kv(out)["score"], ["compiled 0/1 vs base 1/1"])

    def test_grade_not_run(self):
        self.fill_cases()
        os.makedirs(self.out)
        rc, out, _ = run(EVAL, "grade", self.agent, self.cases, self.out)
        self.assertEqual(rc, 1)
        self.assertEqual(kv(out)["result"], ["not run"])

    def set_case(self, **kw):
        self.fill_cases()
        data = json.loads(read(self.cases))
        data["cases"][0].update(kw)
        with open(self.cases, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f)

    def grade_one(self, text):
        if not os.path.exists(self.cases):
            self.fill_cases()
        os.makedirs(self.out, exist_ok=True)
        for label in ("compiled", "base"):
            with open(os.path.join(self.out, f"triage-1.{label}.out.md"), "w", encoding="utf-8", newline="\n") as f:
                f.write(GOOD_REPORT if label == "base" else text)
        rc, out, _ = run(EVAL, "grade", self.agent, self.cases, self.out)
        compiled, base = kv(out)["grade"]
        self.assertIn("| base | pass", base)
        return rc, compiled

    def test_tagged_report_passes(self):
        rc, compiled = self.grade_one(GOOD_REPORT)
        self.assertEqual(rc, 0)
        self.assertIn("| compiled | pass", compiled)

    def test_missing_tag_fails(self):
        rc, compiled = self.grade_one(GOOD_REPORT.replace("<open>\nnone\n</open>\n", ""))
        self.assertEqual(rc, 1)
        self.assertIn("missing tag <open>", compiled)

    def test_bad_status_token_fails(self):
        rc, compiled = self.grade_one(GOOD_REPORT.replace("<status>completed", "<status>ok"))
        self.assertEqual(rc, 1)
        self.assertIn("<status> is not one of completed, partial, needs-input, blocked, rejected, failed", compiled)

    def test_old_status_format_fails(self):
        old = "status: completed\noutcome: done.\nchanged: no edits\nchecks: none\nnext: none\n"
        rc, compiled = self.grade_one(old)
        self.assertEqual(rc, 1)
        self.assertIn("first line is not <status>TOKEN</status>", compiled)
        self.assertIn("missing tag <status>", compiled)

    def test_status_must_come_first_and_order_holds(self):
        swapped = GOOD_REPORT.replace("<status>completed</status>\n", "") + "<status>completed</status>\n"
        rc, compiled = self.grade_one(swapped)
        self.assertEqual(rc, 1)
        self.assertIn("first line is not <status>TOKEN</status>", compiled)
        self.assertIn("tags out of order", compiled)

    def test_nested_tags_and_attributes_fail(self):
        nested = GOOD_REPORT.replace("<artefacts>\nnone\n</artefacts>", "<artefacts><open>x</open></artefacts>")
        rc, compiled = self.grade_one(nested)
        self.assertEqual(rc, 1)
        self.assertIn("<open> nested in <artefacts>", compiled)
        rc, compiled = self.grade_one(GOOD_REPORT.replace("<outcome>", '<outcome kind="x">'))
        self.assertEqual(rc, 1)
        self.assertIn("attributes on <outcome>", compiled)

    def test_check_rejects_bad_files(self):
        for kw in ({"files": {"../x": "a"}}, {"files": {".claude/agents/x.md": "a"}}, {"files": {"/abs": "a"}},
                   {"files": {"a.txt": 1}}, {"files": {"a.txt": "a"}, "unchanged": ["b.txt"]},
                   {"expect_files": {"../y": "z"}}):
            self.set_case(**kw)
            rc, out, _ = run(EVAL, "check", self.agent, self.cases)
            self.assertEqual(rc, 1, kw)
            os.remove(self.cases)
        self.set_case(files={"app/a.txt": "old\n", "b.txt": "keep\n"}, expect_files={"app/a.txt": "new"},
                      unchanged=["b.txt"])
        rc, out, _ = run(EVAL, "check", self.agent, self.cases)
        self.assertEqual(rc, 0, out)

    def test_fixture_files_and_file_checks(self):
        self.set_case(files={"app/a.txt": "old\n", "b.txt": "keep\n"}, expect_files={"app/a.txt": "NEW"},
                      unchanged=["b.txt"])
        report = json.dumps({"result": GOOD_REPORT})
        # The fake edits the fixture only when it sees it in its cwd, and leaves a stale file behind.
        env = self.fake_claude("if not os.path.isfile('b.txt'):\n    sys.exit(3)\n"
                               "open(os.path.join('app', 'a.txt'), 'w', encoding='utf-8', newline='\\n').write('new\\n')\n"
                               "open('stale.txt', 'w', encoding='utf-8').close()\n" + emit(report))
        rc, out, err = run(EVAL, "run", self.agent, BASE, self.cases, self.out, "--execute", env=env)
        self.assertEqual(kv(out)["run_errors"], ["0"], out + err)
        rc, out, _ = run(EVAL, "grade", self.agent, self.cases, self.out)
        self.assertEqual(rc, 0, out)
        sb = os.path.join(self.out, "sandbox", "triage-1.compiled")
        self.assertTrue(os.path.isfile(os.path.join(sb, "stale.txt")))
        env = self.fake_claude("open('b.txt', 'w', encoding='utf-8', newline='\\n').write('changed\\n')\n" + emit(report))
        run(EVAL, "run", self.agent, BASE, self.cases, self.out, "--execute", env=env)
        self.assertFalse(os.path.exists(os.path.join(sb, "stale.txt")))
        rc, out, _ = run(EVAL, "grade", self.agent, self.cases, self.out)
        self.assertEqual(rc, 1)
        self.assertIn("file app/a.txt lacks: NEW", kv(out)["grade"][0])
        self.assertIn("file changed: b.txt", kv(out)["grade"][0])
        shutil.rmtree(os.path.join(self.out, "sandbox"))
        rc, out, _ = run(EVAL, "grade", self.agent, self.cases, self.out)
        self.assertIn("no sandbox for file checks", kv(out)["grade"][0])

    def test_no_agent_baseline(self):
        self.fill_cases()
        env = self.fake_claude("print('{}')")
        rc, out, err = run(EVAL, "run", self.agent, "none", self.cases, self.out, "--model", "sonnet", env=env)
        self.assertEqual(rc, 0, err)
        self.assertTrue(kv(out)["baseline"][0].startswith("none"))
        compiled, base = kv(out)["command"]
        self.assertIn('"--agent" "acme-triage"', compiled)
        self.assertNotIn('"--agent"', base)
        self.assertIn('"--allowedTools" "Read,Grep,Glob,Bash,Skill"', base)
        self.assertIn('"--disallowedTools" "WebSearch,WebFetch"', base)
        self.assertIn('"--model" "sonnet"', base)
        self.assertTrue(base.endswith(json.dumps("<role>worker</role>\nTriage apps/api/tests/test_retry.py.")))
        agents = os.listdir(os.path.join(self.out, "sandbox", "triage-1.base", ".claude", "agents"))
        self.assertEqual(agents, ["acme-triage.md"])
        rc, out, err = run(EVAL, "prompts", self.agent, "none", self.cases, self.out)
        self.assertEqual(rc, 0, err)
        text = read(os.path.join(self.out, "triage-1.base.prompt.md"))
        self.assertNotIn("<<<AGENT", text)
        self.assertTrue(text.startswith("<role>worker</role>"))
        self.assertIn("cwd=", kv(out)["dispatch"][0])

    def test_inheriting_agent_keeps_tools_under_dontask(self):
        """An agent without `tools` and the no-agent baseline both get the built-in set as --allowedTools."""
        text = self.filled()
        line = "tools: Read, Grep, Glob, Bash, Skill\n"
        self.assertTrue(("\n" + line) in text)
        inheriting = self.write(text.replace(line, "", 1), "acme-triage.md")
        self.fill_cases()
        env = self.fake_claude("print('{}')")
        rc, out, err = run(EVAL, "run", inheriting, "none", self.cases, self.out, env=env)
        self.assertEqual(rc, 0, err)
        for cmd in kv(out)["command"]:
            self.assertIn('"--allowedTools" "' + NW.replace(", ", ",") + '"', cmd)
            self.assertIn('"--permission-mode" "dontAsk"', cmd)

    def test_usage(self):
        self.assertEqual(run(EVAL)[0], 2)
        self.assertEqual(run(EVAL, "grade")[0], 2)


if __name__ == "__main__":
    unittest.main()
