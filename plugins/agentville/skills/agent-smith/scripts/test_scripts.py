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


NW = "TaskCreate, TaskUpdate, TaskGet, TaskList, TaskStop, Read, Write, Edit, Glob, Grep, Bash, NotebookEdit, Monitor, Skill"
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
    "[[Workflow-name]]": "Triage",
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
    "* **[[Condition]]:** [[what to do, and the status token to report: completed, partial, needs-input, blocked or failed]].":
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
        self.assertEqual(kv(out)["workflows"], ["1"])
        for c in ("identity", "constraints"):
            self.assertIn(f"{c} | identical", kv(out)["core"])

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
        _, out = self.measure(BASE_TEXT.replace("tools: "+NW+"\n", ""))
        self.assertIn("A1", fails(out))

    def test_08_core_changed_fails(self):
        _, out = self.measure(BASE_TEXT.replace("Do not address the human.", "Address the human."))
        self.assertIn("A5", fails(out))
        self.assertIn("identity | differs", kv(out)["core"])

    def test_09_core_missing_or_misplaced_fails(self):
        start = BASE_TEXT.index("<!-- core:begin identity -->")
        end = BASE_TEXT.index("<!-- core:end identity -->") + len("<!-- core:end identity -->")
        block = BASE_TEXT[start:end]
        _, out = self.measure(BASE_TEXT.replace(block, "1. Talk plainly."))
        self.assertIn("identity | missing", kv(out)["core"])
        moved = BASE_TEXT.replace(block, "1. Talk plainly.").replace("# Exception handler\n", "# Exception handler\n\n" + block + "\n")
        _, out = self.measure(moved)
        self.assertIn("identity | misplaced", kv(out)["core"])

    def test_10_extending_rule_before_core_fails(self):
        _, out = self.measure(BASE_TEXT.replace("# Constraints\n\n", "# Constraints\n\n0. **Extra:** first.\n\n", 1))
        self.assertIn("A5", fails(out))

    def test_11_section_order(self):
        text = BASE_TEXT.replace("# Exception handler", "# Talk")
        _, out = self.measure(text)
        self.assertIn("A4", fails(out))

    def test_12_workflow_rules(self):
        _, out = self.measure(BASE_TEXT.replace("Role: worker\n", ""))
        self.assertIn("A6", fails(out))
        _, out = self.measure(BASE_TEXT.replace("Role: worker\n", "Role: wizard\n"))
        self.assertIn("A6", fails(out))
        _, out = self.measure(BASE_TEXT.replace("3. **Break it down.**", "5. **Break it down.**"))
        self.assertIn("A6", fails(out))
        _, out = self.measure(BASE_TEXT.replace("* **steps:** always -", "* **steps:** sometimes -"))
        self.assertIn("A6", fails(out))
        _, out = self.measure(BASE_TEXT.replace("## Execute", "## Bad Name"))
        self.assertIn("A6", fails(out))
        lo = BASE_TEXT.index("## Execute")
        hi = BASE_TEXT.index("# Exception handler")
        _, out = self.measure(BASE_TEXT[:lo] + BASE_TEXT[hi:])
        self.assertIn("A6", fails(out))

    def test_13_exception_handler_needs_items(self):
        lo = BASE_TEXT.index("# Exception handler") + len("# Exception handler\n")
        _, out = self.measure(BASE_TEXT[:lo] + "\n")
        self.assertIn("A7", fails(out))

    def test_14_leftovers(self):
        _, out = self.measure(BASE_TEXT + "\n[[fill me]]\n")
        self.assertIn("A8", fails(out))
        _, out = self.measure(BASE_TEXT + "\n<!-- note -->\n")
        self.assertIn("A8", fails(out))

    def test_15_foreign_namespace_fails(self):
        _, out = self.measure(BASE_TEXT.replace("agentville:relay", "anthropic-skills" + ":relay", 1))
        self.assertIn("A9", fails(out))
        rc, out = self.measure(BASE_TEXT.replace("1. **Read the brief.** Restate", "1. **Read the brief.** Load `Skill(relay)`. Restate"))
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

    def test_20_constraints_core_needs_status_line(self):
        rc, out = self.measure(BASE_TEXT)
        self.assertEqual(kv(out)["status_line_rule"], ["yes"])
        weak = BASE_TEXT.replace("`<status>` comes first and holds one of", "the status comes with one of")
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

    def test_slot_direct_call_fails_a18(self):
        _, out = self.measure(BASE_TEXT + "\n* Resolve with `Skill(agentville:toolbelt)` now.\n")
        self.assertIn("A18", fails(out))
        self.assertTrue(any(l.startswith("slot_direct_calls:") and "Skill(agentville:toolbelt)" in l for l in out.splitlines()))

    def test_slot_plugin_default_mention_allowed(self):
        _, out = self.measure(BASE_TEXT + "\n* The slot default is the plugin default `Skill(agentville:toolbelt)`.\n")
        self.assertNotIn("A18", fails(out))

    def test_slot_plugin_default_then_call_fails_a18(self):
        _, out = self.measure(BASE_TEXT + "\n* Fall back to the plugin default, then call Skill(agentville:toolbelt).\n")
        self.assertIn("A18", fails(out))
        self.assertTrue(any(l.startswith("slot_direct_calls:") and "Skill(agentville:toolbelt)" in l for l in out.splitlines()))

    def test_slot_call_with_source_outside_record_fails_a18(self):
        for text in ("Call `Skill(agentville:toolbelt) (project-x)` now.", "Call `Skill(agentville:toolbelt) (project-rules)` now.",
                     "Write `toolbelt: Skill(agentville:toolbelt) (project-rules)` now."):
            _, out = self.measure(BASE_TEXT + f"\n* {text}\n")
            self.assertIn("A18", fails(out), text)

    def test_slot_call_followed_by_plugin_default_record_allowed(self):
        _, out = self.measure(BASE_TEXT + "\n* Name `Skill(agentville:toolbelt) (plugin-default)` in the claims.\n")
        self.assertNotIn("A18", fails(out))

    def test_slot_imperative_verb_before_default_call_fails_a18(self):
        for text in ("Call `Skill(agentville:toolbelt) (plugin-default)` now.", "Load the plugin default `Skill(agentville:workspace)`.",
                     "Then run Skill(agentville:draft) (plugin-default).", "Invoke the plugin default Skill(agentville:plan).",
                     "Use `Skill(agentville:report)` (plugin-default)."):
            _, out = self.measure(BASE_TEXT + f"\n* {text}\n")
            self.assertIn("A18", fails(out), text)
            self.assertTrue(any(l.startswith("slot_direct_calls:") and "Skill(agentville:" in l for l in out.splitlines()), text)

    def test_slot_non_imperative_default_description_still_allowed_a18(self):
        for text in ("The slot falls back to the plugin default `Skill(agentville:draft)`.", "Name `Skill(agentville:plan) (plugin-default)` in the claims.",
                     "Write `report: agentville:report (plugin-default)` in the claims."):
            _, out = self.measure(BASE_TEXT + f"\n* {text}\n")
            self.assertNotIn("A18", fails(out), text)

    def test_slot_record_needs_known_source_and_own_slot(self):
        for text in ("toolbelt: agentville:toolbelt (project-x)", "workspace: agentville:toolbelt (project-rules)"):
            _, out = self.measure(BASE_TEXT + f"\n* Write `{text}` in the claims.\n")
            self.assertIn("A18", fails(out), text)
        _, out = self.measure(BASE_TEXT + "\n* Write `toolbelt: agentville:toolbelt (project-rules)` in the claims.\n")
        self.assertNotIn("A18", fails(out))

    def test_slot_without_context_injection_fails_a18(self):
        text = BASE_TEXT.replace("Skill(agentville:context-injection)", "Skill(agentville:relay)")
        _, out = self.measure(text + "\n* Use the `toolbelt` slot.\n")
        self.assertIn("A18", fails(out))
        self.assertTrue(any(l.startswith("slot_without_context_injection:") and "toolbelt" in l for l in out.splitlines()), out)

    def test_slot_via_context_injection_passes(self):
        _, out = self.measure(BASE_TEXT + "\n* Use the `toolbelt` slot, resolved with `Skill(agentville:context-injection)`.\n")
        self.assertNotIn("A18", fails(out))

    def test_slot_plugin_default_elsewhere_on_line_does_not_exempt(self):
        old = "and report a fallback to the plugin default in `<deviations>`."
        self.assertIn(old, BASE_TEXT)
        _, out = self.measure(BASE_TEXT.replace(old, old + " Then call Skill(agentville:toolbelt)."))
        self.assertIn("A18", fails(out))
        self.assertTrue(any(l.startswith("slot_direct_calls:") and "Skill(agentville:toolbelt)" in l for l in out.splitlines()))

    def test_slot_other_call_forms_fail_a18(self):
        for form in ("agentville:toolbelt", "/agentville:toolbelt", "Skill(toolbelt)"):
            _, out = self.measure(BASE_TEXT + f"\n* Load {form} first.\n")
            self.assertIn("A18", fails(out), form)

    def test_slot_record_with_source_allowed(self):
        _, out = self.measure(BASE_TEXT + "\n* Write `workspace: agentville:workspace (plugin-default)` in the claims.\n")
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
        path, out = self.fork("ci-triage")
        self.assertEqual(kv(out)["core"], ["constraints, identity"])
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
        src = self.write(BASE_TEXT, "ci-triage.md")
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
        src = self.write(BASE_TEXT, "ci-triage.md")
        self.roots_cache = project, user = self.roots()
        for scope, root in (("project", project), ("user", user)):
            dst = os.path.join(root, ".claude", "agents")
            rc, out, err = self.install(src, dst, scope)
            self.assertEqual(rc, 0, err)
            self.assertEqual(kv(out)["written"], [os.path.join(os.path.realpath(dst), "ci-triage.md")])
            self.assertTrue(os.path.isfile(os.path.join(dst, "ci-triage.md")))

    def test_install_refuses_plugin_target(self):
        src = self.write(BASE_TEXT, "ci-triage.md")
        self.roots_cache = project, user = self.roots()
        plugin = os.path.join(project, "plugins", "acme")
        os.makedirs(os.path.join(plugin, ".claude-plugin"))
        with open(os.path.join(plugin, ".claude-plugin", "plugin.json"), "w") as f:
            f.write("{}")
        for scope in ("project", "user"):
            for dst in (os.path.join(plugin, "agents"), os.path.join(plugin, ".claude", "agents"),
                        os.path.join(project, "plugins", "other", "agents"),
                        os.path.join(plugin, ".claude-plugin")):
                rc, out, err = self.install(src, dst, scope)
                self.assertEqual(rc, 2, dst)
                self.assertIn("refused", err)
                self.assertFalse(os.path.exists(os.path.join(dst, "ci-triage.md")), dst)
        # a project root that is itself a plugin is refused even at its own .claude/agents
        rc, _, err = run(STAGE, "install", src, os.path.join(plugin, ".claude", "agents"), "--scope", "project",
                         "--project-root", plugin, "--user-root", user)
        self.assertEqual(rc, 2)
        self.assertIn("plugin", err)
        self.assertFalse(os.path.exists(os.path.join(plugin, ".claude", "agents", "ci-triage.md")))

    def test_install_accepts_project_root_under_plugins_folder(self):
        src = self.write(BASE_TEXT, "ci-triage.md")
        project = os.path.join(self.tmp, "plugins", "myapp")
        user = os.path.join(self.tmp, "home")
        os.makedirs(project)
        os.makedirs(user)
        dst = os.path.join(project, ".claude", "agents")
        rc, _, err = run(STAGE, "install", src, dst, "--scope", "project",
                         "--project-root", project, "--user-root", user)
        self.assertEqual(rc, 0, err)
        self.assertTrue(os.path.isfile(os.path.join(dst, "ci-triage.md")))

    def test_install_refuses_other_folders_and_missing_scope(self):
        src = self.write(BASE_TEXT, "ci-triage.md")
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
        with open(os.path.join(self.tmp, "plugins", "acme", ".claude-plugin", "plugin.json"), "w") as f:
            f.write("{}")
        with open(plugin_agent, "w") as f:
            f.write(BASE_TEXT)
        rc, _, err = run(STAGE, "seed", plugin_agent, p)
        self.assertEqual(rc, 2)
        self.assertIn("plugin", err)
        self.assertFalse(os.path.exists(os.path.join(p, "x.md")))

    def test_usage(self):
        self.assertEqual(run(STAGE)[0], 2)
        self.assertEqual(run(STAGE, "bogus")[0], 2)


GOOD_REPORT = """<status>completed</status>
<outcome>
Root cause found in tests/test_retry.py.
</outcome>
<claims>
- The failing test is tests/test_retry.py. verified: pytest tests/test_retry.py -q fails.
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
        self.assertEqual({c["workflow"] for c in data["cases"]}, {"Execute"})
        data["cases"] = []
        with open(self.cases, "w") as f:
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
        self.assertIn("You are **ci-triage**.", text)

    def test_prompts_keep_sandbox_with_report(self):
        self.fill_cases()
        rc, out, err = run(EVAL, "prompts", self.agent, BASE, self.cases, self.out)
        self.assertEqual(rc, 0, err)
        sb = os.path.join(self.out, "sandbox", "triage-1.compiled")
        with open(os.path.join(sb, "child.txt"), "w") as f:
            f.write("effect")
        with open(os.path.join(self.out, "triage-1.compiled.out.md"), "w") as f:
            f.write(GOOD_REPORT)
        rc, out, err = run(EVAL, "prompts", self.agent, BASE, self.cases, self.out)
        self.assertEqual(rc, 0, err)
        self.assertTrue(os.path.isfile(os.path.join(sb, "child.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.out, "sandbox", "triage-1.base", "child.txt")))

    def test_case_role_defaults_to_first_workflow(self):
        self.fill_cases()
        data = json.loads(read(self.cases))
        del data["cases"][0]["role"]
        with open(self.cases, "w") as f:
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
        env = self.fake_claude("touch \"$0.ran\"; echo '{}'")
        rc, out, err = run(EVAL, "run", self.agent, BASE, self.cases, self.out, "--model", "sonnet", env=env)
        self.assertEqual(rc, 0, err)
        self.assertEqual(kv(out)["mode"], ["dry-run"])
        cmds = kv(out)["command"]
        self.assertEqual(len(cmds), 2)
        self.assertIn('"--agent" "ci-triage"', cmds[0])
        self.assertIn('"--model" "sonnet"', cmds[0])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "bin", "claude.ran")))
        self.assertTrue(os.path.isfile(os.path.join(self.out, "sandbox", "triage-1.base", ".claude", "agents",
                                                    "worker.md")))
        self.assertEqual(kv(out)["runs"], ["2"])

    def test_run_command_line(self):
        self.fill_cases()
        env = self.fake_claude("echo '{}'")
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
        base_tools = ",".join(t.strip() for t in
                              [l for l in read(BASE).splitlines() if l.startswith("tools:")][0][6:].split(","))
        self.assertEqual(args[args.index("--allowedTools") + 1], base_tools)
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
            f.write("Done!\n<outcome>fine</outcome>\n")
        with open(os.path.join(self.out, "triage-1.base.out.md"), "w") as f:
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
        with open(self.cases, "w") as f:
            json.dump(data, f)

    def grade_one(self, text):
        if not os.path.exists(self.cases):
            self.fill_cases()
        os.makedirs(self.out, exist_ok=True)
        for label in ("compiled", "base"):
            with open(os.path.join(self.out, f"triage-1.{label}.out.md"), "w") as f:
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
        self.assertIn("<status> is not one of completed, partial, needs-input, blocked, failed", compiled)

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
        env = self.fake_claude("test -f b.txt || exit 3; echo new > app/a.txt; touch stale.txt\ncat <<'EOF'\n"
                               + report + "\nEOF")
        rc, out, err = run(EVAL, "run", self.agent, BASE, self.cases, self.out, "--execute", env=env)
        self.assertEqual(kv(out)["run_errors"], ["0"], out + err)
        rc, out, _ = run(EVAL, "grade", self.agent, self.cases, self.out)
        self.assertEqual(rc, 0, out)
        sb = os.path.join(self.out, "sandbox", "triage-1.compiled")
        self.assertTrue(os.path.isfile(os.path.join(sb, "stale.txt")))
        env = self.fake_claude("echo changed > b.txt\ncat <<'EOF'\n" + report + "\nEOF")
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
        env = self.fake_claude("echo '{}'")
        rc, out, err = run(EVAL, "run", self.agent, "none", self.cases, self.out, "--model", "sonnet", env=env)
        self.assertEqual(rc, 0, err)
        self.assertTrue(kv(out)["baseline"][0].startswith("none"))
        compiled, base = kv(out)["command"]
        self.assertIn('"--agent" "ci-triage"', compiled)
        self.assertNotIn('"--agent"', base)
        self.assertIn('"--allowedTools" "Read,Grep,Glob,Bash,Skill"', base)
        self.assertIn('"--disallowedTools" "WebSearch,WebFetch"', base)
        self.assertIn('"--model" "sonnet"', base)
        self.assertTrue(base.endswith(json.dumps("<role>worker</role>\nTriage tests/test_retry.py.")))
        agents = os.listdir(os.path.join(self.out, "sandbox", "triage-1.base", ".claude", "agents"))
        self.assertEqual(agents, ["ci-triage.md"])
        rc, out, err = run(EVAL, "prompts", self.agent, "none", self.cases, self.out)
        self.assertEqual(rc, 0, err)
        text = read(os.path.join(self.out, "triage-1.base.prompt.md"))
        self.assertNotIn("<<<AGENT", text)
        self.assertTrue(text.startswith("<role>worker</role>"))
        self.assertIn("cwd=", kv(out)["dispatch"][0])

    def test_usage(self):
        self.assertEqual(run(EVAL)[0], 2)
        self.assertEqual(run(EVAL, "grade")[0], 2)


if __name__ == "__main__":
    unittest.main()
