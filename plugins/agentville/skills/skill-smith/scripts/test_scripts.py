"""Self-test for measure.py and stage.py. Run: python3 -I scripts/test_scripts.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MEASURE = os.path.join(HERE, "measure.py")
STAGE = os.path.join(HERE, "stage.py")
ROOT = os.path.dirname(HERE)
REAL = os.path.join(ROOT, "SKILL.md")
TEMPLATES = os.path.join(ROOT, "assets", "templates")


def run(script, *args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run([sys.executable, "-I", script, *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=e)
    return p.returncode, p.stdout, p.stderr


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def kv(out):
    d = {}
    for line in out.splitlines():
        k, _, v = line.partition(": ")
        d.setdefault(k, []).append(v)
    return d


def fails(out):
    v = kv(out)["failures"][-1]
    return set() if v == "none" else {int(x) for x in v.split(", ")}


def warns(out):
    v = kv(out)["warnings"][-1]
    return set() if v == "none" else {int(x) for x in v.split(", ")}


SIX = ("<status>completed</status>\n<outcome>Done.</outcome>\n<claims>\n- x: 1. verified: Read x\n</claims>\n"
       "<artefacts>none</artefacts>\n<open>none</open>\n<deviations>none</deviations>\n")
FAIL = ("<status>blocked | needs-input | failed</status>\n<outcome>Stopped.</outcome>\n<claims>none</claims>\n"
        "<artefacts>none</artefacts>\n<open>missing: none</open>\n<deviations>none</deviations>\n")
FAIL_LINE = "<status>partial | blocked | needs-input | rejected | failed</status>"

GOOD = '''---
name: "demo"
description: "Ranks showtimes for one film. Use when asked for showtimes, or for which slot to book."
metadata:
  version: 1.0.0
---

# Role

You are a showtime ranker. You take a film and an area, rank the screenings and return a list.

# Constraints

* Never guess a time, because the ranking depends on it.

# Input

* **film:** required - default: none - The film title, such as `Dune`.
* **area:** optional - default: all areas - The area to search, such as `Quận 7`.

# Process

### 1. Collect the inputs

Read `film` and `area` from the request. If `film` is missing and a person runs the skill, ask with `AskUserQuestion`; otherwise return `<status>needs-input</status>` with `<open>` beginning `missing: film`.

Do:
* "Dune in Quận 7" gives film `Dune`, area `Quận 7`.

Don't:
* Guess the film; ask or return needs-input.

### 2. Rank

Search with `WebSearch` for `lịch chiếu "Dune"` and rank by start time, as step 1 collected.

Do:
* Rank 21:40 above 22:30.

Don't:
* Rank by price alone.

# Output

* **ranked-list:** always - In `<claims>`: the numbered screenings.
* **note:** when a page failed - In `<open>`: which page failed.

```text
<status>completed</status>
<outcome>Screenings ranked.</outcome>
<claims>
- ranked-list: [LIST]. verified: [SOURCE]
</claims>
<artefacts>none</artefacts>
<open>none</open>
<deviations>none</deviations>
```

Do:
* `ranked-list: 1. CGV 21:40` in `<claims>`

Don't:
* A greeting; start with `<status>`.

```text
<status>partial | blocked | needs-input | rejected | failed</status>
<outcome>[ONE_SENTENCE]</outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: [NAMES_OR_NONE]</open>
<deviations>none</deviations>
```
'''

STEERING = '''---
name: naming
description: 'Sets naming rules. Use when naming files, or naming branches.'
metadata:
  version: 1.0.0
---

# naming

Goal: every name follows one pattern.

## 1. Files

- Use kebab-case.

## 2. Branches

- Prefix with the ticket.

Correct: "abc-12-fix"

Wrong: "Fix_Stuff"

## Pre-send check

1. Files are kebab-case (§1).
2. Branches carry a ticket (§2).
3. No name mixes cases (§1).
'''

KNOWLEDGE = '''---
name: prices
description: 'Ticket prices by chain. Use when pricing a ticket, or comparing chains.'
metadata:
  version: 1.0.0
---

# prices

Goal: answer what a ticket costs.

## 1. CGV prices

- A 2D ticket costs 95,000đ.

### Examples

- Two tickets cost 190,000đ.
- One IMAX ticket costs 180,000đ.

## 2. Galaxy prices

- A 2D ticket costs 85,000đ.

### Examples

- Two tickets cost 170,000đ.
- A matinee costs 65,000đ.

## Pre-send check

1. Each section names one chain.
2. Each fact is stated once.
3. Each topic has two examples.
'''


class MeasureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def m(self, text, name="SKILL.md", folder=None, newline="\n"):
        folder = folder or self.tmp
        path = os.path.join(folder, name)
        with open(path, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
        return run(MEASURE, path)

    def test_01_minimal_process(self):
        rc, out, err = self.m(GOOD)
        self.assertEqual(rc, 0, out + err)
        lines = out.splitlines()
        self.assertEqual(lines[0], "type: process")
        self.assertEqual(lines[-1], "failures: none")
        self.assertIn("sections: Role, Constraints, Input, Process, Output", lines)
        self.assertIn("failure_template: yes", lines)

    def test_01b_version_missing_or_malformed_fails(self):
        for bad in (GOOD.replace("metadata:\n  version: 1.0.0\n", ""), GOOD.replace("version: 1.0.0", "version: v1")):
            rc, out, _ = self.m(bad)
            self.assertEqual(rc, 1, out)
            self.assertIn(15, fails(out))
            self.assertIn("version_error:", out)

    def test_02_inputs_parsed(self):
        out = self.m(GOOD)[1]
        self.assertIn("input: film | required | none", out.splitlines())
        self.assertIn("input: area | optional | all areas", out.splitlines())
        self.assertEqual(kv(out)["inputs_required"], ["film"])

    def test_03_step_without_dont(self):
        rc, out, _ = self.m(GOOD.replace("Don't:\n* Rank by price alone.\n", ""))
        self.assertEqual(rc, 1)
        self.assertIn(5, fails(out))
        self.assertIn("step: 2 | Rank | do=1 dont=0", out)

    def test_03b_bare_one_line_step_passes(self):
        text = GOOD.replace("Do:\n* Rank 21:40 above 22:30.\n\nDon't:\n* Rank by price alone.\n\n", "")
        self.assertNotEqual(text, GOOD)
        rc, out, _ = self.m(text)
        self.assertEqual(rc, 0, out)
        self.assertEqual(kv(out)["failures"], ["none"])
        self.assertIn("step: 2 | Rank | do=0 dont=0", out)

    def test_03c_step_with_only_do_fails(self):
        text = GOOD.replace("Don't:\n* Rank by price alone.\n\n", "")
        self.assertNotEqual(text, GOOD)
        rc, out, _ = self.m(text)
        self.assertEqual(rc, 1)
        self.assertIn(5, fails(out))

    def test_03d_multi_line_step_without_examples_fails(self):
        text = GOOD.replace("as step 1 collected.\n\nDo:\n* Rank 21:40 above 22:30.\n\nDon't:\n* Rank by price alone.\n\n",
                            "as step 1 collected.\n\nThen drop duplicates.\n\n")
        self.assertNotEqual(text, GOOD)
        rc, out, _ = self.m(text)
        self.assertEqual(rc, 1)
        self.assertIn(5, fails(out))

    def test_04_dont_heading_without_items(self):
        rc, out, _ = self.m(GOOD.replace("Don't:\n* Rank by price alone.\n", "Don't:\n\nMore prose.\n"))
        self.assertIn(5, fails(out))

    def test_05_output_without_fence(self):
        text = GOOD.split("```text\n<status>completed</status>\n")[0] + "Do:\n* a\n\nDon't:\n* b\n"
        out = self.m(text)[1]
        self.assertIn(7, fails(out))
        self.assertIn(16, fails(out))

    def test_06_sections_order_and_forbidden(self):
        swapped = GOOD.replace("# Input", "# TMP").replace("# Process", "# Input").replace("# TMP", "# Process")
        self.assertIn(1, fails(self.m(swapped)[1]))
        extra = GOOD.replace("# Input", "# Dependencies\n\n- none\n\n# Input")
        out = self.m(extra)[1]
        self.assertIn(1, fails(out))
        self.assertIn(2, fails(out))

    def test_06b_old_order_fails_d3(self):
        con = "# Constraints\n\n* Never guess a time, because the ranking depends on it.\n\n"
        old = GOOD.replace(con, "") + "\n" + con
        out = self.m(old)[1]
        self.assertIn("sections: Role, Input, Process, Output, Constraints", out)
        self.assertIn(1, fails(out))

    def test_07_step_gap(self):
        self.assertIn(8, fails(self.m(GOOD.replace("### 2. Rank", "### 3. Rank"))[1]))

    def test_07b_bad_step_reference(self):
        self.assertIn(8, fails(self.m(GOOD.replace("as step 1 collected", "as step 4 collected"))[1]))

    def test_08_malformed_input(self):
        bad = GOOD.replace("* **area:** optional", "* **area:** maybe")
        self.assertIn(4, fails(self.m(bad)[1]))
        bad = GOOD.replace("required - default: none", "required - default: Dune")
        self.assertIn(4, fails(self.m(bad)[1]))

    def test_09_metadata_block(self):
        text = GOOD.replace('---\n\n# Role', 'metadata:\n  type: "steering"\n---\n\n# Role', 1)
        rc, out, _ = self.m(text)
        self.assertEqual(rc, 1)
        self.assertIn(15, fails(out))
        self.assertEqual(kv(out)["type"], ["process"])

    def test_10_allowed_tools_fails_d4(self):
        for key in ("allowed-tools: Read", "version: 1.0", "type: process"):
            text = GOOD.replace('---\n\n# Role', key + '\n---\n\n# Role', 1)
            rc, out, _ = self.m(text)
            self.assertEqual(rc, 1, key)
            self.assertIn(15, fails(out), key)

    def test_11_description_length(self):
        def with_desc(n):
            return GOOD.replace(
                'description: "Ranks showtimes for one film. Use when asked for showtimes, or for which slot to book."',
                'description: "' + "x" * n + '"')
        out = self.m(with_desc(1024))[1]
        self.assertNotIn(12, fails(out))
        self.assertEqual(kv(out)["description_chars"], ["1024"])
        self.assertIn(12, fails(self.m(with_desc(1025))[1]))

    def test_11b_description_angle_brackets_fail(self):
        good = 'description: "Ranks showtimes for one film. Use when asked for showtimes, or for which slot to book."'
        for bad in ("Saves to <topic>/draft.md. Use when saving, or when finding.", "Needs x > 1. Use when a, or b."):
            out = self.m(GOOD.replace(good, 'description: "' + bad + '"'))[1]
            self.assertIn(12, fails(out), bad)
            self.assertIn("description_error:", out)
        self.assertNotIn(12, fails(self.m(GOOD.replace(good, 'description: "Saves to {topic}/draft.md. Use when saving, or when finding."'))[1]))

    def test_12_line_limit(self):
        base = len(GOOD.rstrip("\n").split("\n"))

        def padded(total):
            return GOOD.replace("# Role\n", "# Role\n" + "filler\n" * (total - base), 1)
        out = self.m(padded(500))[1]
        self.assertEqual(kv(out)["lines"], ["500"])
        self.assertNotIn(6, fails(out))
        self.assertIn(6, fails(self.m(padded(501))[1]))

    def test_13_legacy_format(self):
        text = GOOD.replace("# Role\n", "Start here:\n1. read\n\n# Workflows\n\n<demo scope=\"public\">\n\n# Role\n", 1)
        rc, out, _ = self.m(text)
        self.assertEqual(kv(out)["type"], ["legacy-process"])
        self.assertIn(2, fails(out))
        self.assertNotEqual(kv(out)["legacy"], ["none"])

    def test_14_labelled_bullet(self):
        bad = GOOD.replace("Search with", "- **Action:** read\n\nSearch with")
        self.assertIn(2, fails(self.m(bad)[1]))
        ok = GOOD.replace("* Rank by price alone.", "* Rank by price alone.\n- **Action:** read")
        self.assertNotIn(2, fails(self.m(ok)[1]))

    def test_15_leftover_fill_in(self):
        rc, out, _ = self.m(GOOD.replace("rank the screenings", "[[x]]"))
        self.assertIn(11, fails(out))
        self.assertEqual(kv(out)["unfilled"], ["1"])
        self.assertIn(11, fails(self.m(GOOD.replace("rank the screenings", "<!-- x -->"))[1]))

    def test_16_unresolved_links(self):
        text = GOOD.replace("Search with", "Read {{ SKILL_ROOT }}/references/missing.md and [x](references/missing.md). Search with")
        out = self.m(text)[1]
        self.assertIn(14, fails(out))
        self.assertIn("references/missing.md", kv(out)["unresolved_links"][0])
        os.makedirs(os.path.join(self.tmp, "references"))
        with open(os.path.join(self.tmp, "references", "missing.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("x\n")
        out = self.m(text)[1]
        self.assertNotIn(14, fails(out))
        self.assertEqual(kv(out)["unresolved_links"], ["none"])

    def test_17_skill_mention_warns(self):
        rc, out, _ = self.m(GOOD.replace("Search with", "Ask /other-skill, then search with"))
        self.assertEqual(rc, 0, out)
        self.assertEqual(kv(out)["skill_mentions"], ["/other-skill"])
        self.assertIn(14, warns(out))

    def test_18_host_path(self):
        self.assertIn(11, fails(self.m(GOOD.replace("Search with", "Open /home/dev/x, then search with"))[1]))
        ok = GOOD.replace("* Rank 21:40 above 22:30.", "* Rank 21:40 above 22:30 in /home/dev/x.")
        self.assertNotIn(11, fails(self.m(ok)[1]))

    def test_19_fenced_text_ignored(self):
        text = GOOD.replace("Search with", "```text\n# Workflows\n@Tool: /Read x\n### 9. Fake\n```\n\nSearch with")
        rc, out, _ = self.m(text)
        self.assertEqual(rc, 0, out)

    def test_20_untagged_fence(self):
        text = GOOD.replace("Search with", "```\nplain\n```\n\nSearch with")
        self.assertIn(3, fails(self.m(text)[1]))

    def test_21_steering(self):
        rc, out, _ = self.m(STEERING)
        self.assertEqual(rc, 0, out)
        self.assertEqual(kv(out)["type"], ["steering"])
        self.assertEqual(kv(out)["presend_items"], ["3"])

    def test_22_steering_failures(self):
        cases = [STEERING.replace("## 2. Branches", "## 3. Branches"),
                 STEERING.replace("(§2)", "(§9)"),
                 STEERING.replace("3. No name mixes cases (§1).\n", ""),
                 STEERING.replace("## 2. Branches", "## 2. Notes")]
        for c in cases:
            self.assertIn(2, fails(self.m(c)[1]))

    def test_23_knowledge(self):
        rc, out, _ = self.m(KNOWLEDGE)
        self.assertEqual(rc, 0, out)
        self.assertEqual(kv(out)["type"], ["knowledge"])
        out = self.m(KNOWLEDGE.replace("- A matinee costs 65,000đ.\n", ""))[1]
        self.assertIn(5, fails(out))

    def test_24_template_detection(self):
        text = GOOD.replace('name: "demo"', 'name: "[[skill-name]]"').replace(
            "Ranks showtimes", "x" * 1100).replace("rank the screenings", "[[x]]")
        rc, out, _ = self.m(text)
        self.assertEqual(rc, 0, out)
        self.assertEqual(kv(out)["template"], ["yes"])

    def test_25_shipped_templates(self):
        for t, kind in (("process", "process"), ("steering", "steering"), ("knowledge", "knowledge")):
            rc, out, err = run(MEASURE, os.path.join(TEMPLATES, t + ".md"))
            self.assertEqual(rc, 0, t + out + err)
            self.assertEqual(kv(out)["type"], [kind])
            self.assertEqual(kv(out)["template"], ["yes"])
            self.assertEqual(kv(out)["failures"], ["none"])

    def test_26_workflow_part(self):
        wf = os.path.join(self.tmp, "references", "workflows")
        os.makedirs(wf)
        part = ("Used by SKILL.md step 2.\n\n# Input\n\n* **x:** required - default: none - X.\n\n"
                "# Process\n\n### 1. Do it\n\nUse `x` with `Read`.\n\nDo:\n* a\n* b\n\n"
                "# Output\n\n```text\n" + SIX + "```\n\nDo:\n* a\n\nDon't:\n* b\n\n```text\n" + FAIL + "```\n")
        with open(os.path.join(wf, "x.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(part)
        rc, out, _ = self.m(GOOD)
        self.assertEqual(rc, 1)
        self.assertIn("part: references/workflows/x.md | steps=1 | failures=5", out.splitlines())
        with open(os.path.join(wf, "x.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(part.replace("* a\n* b\n\n# Output", "* a\n\nDon't:\n* b\n\n# Output"))
        rc, out, _ = self.m(GOOD)
        self.assertEqual(rc, 0, out)

    def test_27_usage_and_read_errors(self):
        for args in ((), (os.path.join(self.tmp, "nope.md"),)):
            rc, _, err = run(MEASURE, *args)
            self.assertEqual(rc, 2)
            self.assertTrue(err)
        for text in ("# Role\n", "---\nname: x\n"):
            rc, _, err = self.m(text)
            self.assertEqual(rc, 2)
            self.assertTrue(err)

    def test_28_crlf(self):
        self.assertEqual(self.m(GOOD)[1], self.m(GOOD, newline="\r\n")[1])

    def test_29_real_skill_md(self):
        if not os.path.isfile(REAL):
            self.skipTest("no SKILL.md")
        rc, out, err = run(MEASURE, REAL)
        self.assertEqual(rc, 0, out + err)
        d = kv(out)
        self.assertEqual(d["type"], ["process"])
        self.assertEqual(d["steps"], ["11"])
        self.assertEqual(len(d["input"]), 10)
        self.assertEqual(d["inputs_required"], ["request, scope"])
        self.assertEqual(d["output_templates"], ["2"])
        self.assertEqual(d["unresolved_links"], ["none"])
        self.assertEqual(d["failure_template"], ["yes"])

    def test_30_failure_template_required_d1(self):
        no_block = GOOD.split("```text\n" + FAIL_LINE)[0]
        self.assertIn(16, fails(self.m(no_block)[1]))
        partial = GOOD.replace("<open>missing: [NAMES_OR_NONE]</open>", "<open>[NAMES_OR_NONE]</open>")
        self.assertIn(16, fails(self.m(partial)[1]))
        wrong = GOOD.replace(FAIL_LINE, "<status>completed | blocked</status>")
        self.assertIn(16, fails(self.m(wrong)[1]))
        for line in ("needs-input | blocked | failed", "blocked | needs-input | failed | extra",
                     "partial | partial | blocked | needs-input | failed", "blocked | failed"):
            odd = GOOD.replace(FAIL_LINE, "<status>" + line + "</status>")
            self.assertIn(16, fails(self.m(odd)[1]), line)
        plain = GOOD.replace(FAIL_LINE, "<status>blocked | needs-input | failed</status>")
        self.assertNotIn(16, fails(self.m(plain)[1]))
        rej = GOOD.replace(FAIL_LINE, "<status>blocked | needs-input | rejected | failed</status>")
        self.assertNotIn(16, fails(self.m(rej)[1]))
        for line in ("partial | blocked | needs-input | failed | rejected", "blocked | needs-input | rejected"):
            odd = GOOD.replace(FAIL_LINE, "<status>" + line + "</status>")
            self.assertIn(16, fails(self.m(odd)[1]), line)

    def test_31_asking_needs_needs_input_d2(self):
        bad = GOOD.replace("; otherwise return `<status>needs-input</status>` with `<open>` beginning `missing: film`", "").replace(
            "ask or return needs-input", "ask")
        self.assertIn(17, fails(self.m(bad)[1]))
        blocked = bad.replace("ask with `AskUserQuestion`", "ask with `AskUserQuestion`; otherwise return `<status>blocked</status>`")
        self.assertIn(17, fails(self.m(blocked)[1]))

    def test_32_returned_fields(self):
        out = self.m(GOOD)[1]
        self.assertIn("returns: ranked-list | always", out.splitlines())
        self.assertIn("output_field: ranked-list", out.splitlines())
        bad = GOOD.replace("* **ranked-list:** always - In `<claims>`: the numbered screenings.\n* **note:** when a page failed - In `<open>`: which page failed.\n", "")
        self.assertIn(18, fails(self.m(bad)[1]))

    def test_33_dead_input_warns(self):
        rc, out, _ = self.m(GOOD.replace("Read `film` and `area` from", "Read `film` from").replace(
            ", area `Quận 7`", ""))
        self.assertEqual(rc, 0, out)
        self.assertIn(4, warns(out))

    def test_34_independence_clean_passes(self):
        rc, out, _ = self.m(GOOD)
        self.assertEqual(rc, 0, out)
        self.assertNotIn(20, fails(out))
        self.assertNotIn("independence_hit", out)

    def _indep(self, old, new, token):
        rc, out, _ = self.m(GOOD.replace(old, new))
        self.assertEqual(rc, 1, out)
        self.assertIn(20, fails(out))
        self.assertIn("independence_hit: SKILL.md:", out)
        self.assertIn("| " + token, out)

    def test_35_independence_caller(self):
        self._indep("Never guess a time", "Report to the caller; never guess a time", "caller")

    def test_36_independence_orchestrator(self):
        self._indep("Never guess a time", "Never wait for the Orchestrator; never guess a time", "Orchestrator")

    def test_37_independence_subagent(self):
        self._indep("Never guess a time", "Assume you run in a subagent; never guess a time", "in a subagent")

    def test_38_independence_description_names_skill(self):
        self._indep("Ranks showtimes for one film.", "Ranks showtimes for one film, called by `Skill(plan)`.",
                    "description: called by")

    def test_39_independence_other_file_and_allowlist(self):
        d = os.path.join(self.tmp, "s")
        os.makedirs(os.path.join(d, "references"))
        with open(os.path.join(d, "references", "x.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("line one\nThe main thread waits.\n")
        rc, out, _ = self.m(GOOD, folder=d)
        self.assertIn("independence_hit: references/x.md:2 | main thread", out)
        self.assertIn(20, fails(out))
        # allowlist applies only to skill-smith itself
        rc, out, _ = self.m(GOOD.replace('name: "demo"', 'name: "skill-smith"'), folder=d)
        self.assertIn("references/x.md:2", out)
        # validate-rules.md is allowlisted only under the skill-smith name
        with open(os.path.join(d, "references", "validate-rules.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("line one\nThe main thread waits.\n")
        rc, out, _ = self.m(GOOD.replace('name: "demo"', 'name: "skill-smith"'), folder=d)
        self.assertNotIn("references/validate-rules.md", out)
        rc, out, _ = self.m(GOOD, folder=d)
        self.assertIn("references/validate-rules.md:2", out)

    def test_40_real_skill_smith_independent(self):
        out = run(MEASURE, REAL)[1]
        self.assertNotIn(20, fails(out), out)

    # ---- relay section 4 output: rules 7, 16, 18 and 23
    def swap_first_fence(self, new_body):
        """GOOD with the success template replaced by new_body."""
        old = GOOD[GOOD.index("```text\n<status>completed"):GOOD.index("```\n\nDo:\n* `ranked-list")]
        return GOOD.replace(old, "```text\n" + new_body)

    def test_41_six_tags_pass(self):
        rc, out, err = self.m(GOOD)
        self.assertEqual(rc, 0, out + err)
        self.assertIn("output_tags: yes", out.splitlines())
        self.assertIn("failure_template: yes", out.splitlines())
        self.assertEqual(warns(out) & {18}, set())

    def test_42_old_key_value_template_fails(self):
        out = self.m(self.swap_first_fence("status: completed\nranked-list: [LIST]\n"))[1]
        self.assertIn(7, fails(out))
        self.assertIn(23, fails(out))
        self.assertIn("output_tags: no", out.splitlines())
        old = GOOD.replace(FAIL_LINE + "\n<outcome>[ONE_SENTENCE]</outcome>\n<claims>none</claims>\n<artefacts>none</artefacts>\n"
                           "<open>missing: [NAMES_OR_NONE]</open>\n<deviations>none</deviations>\n",
                           "status: partial | blocked | needs-input | rejected | failed\nreason: [ONE_SENTENCE]\nmissing: [NAMES_OR_NONE]\n")
        self.assertNotEqual(old, GOOD)
        out = self.m(old)[1]
        self.assertIn(16, fails(out))
        self.assertIn(23, fails(out))

    def test_43_tags_out_of_order_fail(self):
        swapped = ("<status>completed</status>\n<outcome>Done.</outcome>\n<artefacts>none</artefacts>\n"
                   "<claims>\n- x: 1. verified: Read x\n</claims>\n<open>none</open>\n<deviations>none</deviations>\n")
        self.assertIn(7, fails(self.m(self.swap_first_fence(swapped))[1]))

    def test_44_nested_tag_or_attribute_or_missing_tag_fails(self):
        nested = SIX.replace("</claims>\n", "<open>none</open>\n</claims>\n")
        self.assertIn(7, fails(self.m(self.swap_first_fence(nested))[1]))
        attr = SIX.replace("<status>", '<status kind="done">')
        self.assertIn(7, fails(self.m(self.swap_first_fence(attr))[1]))
        short = SIX.replace("<deviations>none</deviations>\n", "")
        self.assertIn(7, fails(self.m(self.swap_first_fence(short))[1]))
        twice = SIX + "<open>none</open>\n"
        self.assertIn(7, fails(self.m(self.swap_first_fence(twice))[1]))
        self.assertEqual(fails(self.m(self.swap_first_fence(SIX))[1]), set())

    def test_45_failure_template_shape(self):
        self.assertEqual(fails(self.m(GOOD)[1]), set())
        tail = GOOD[GOOD.rindex("```text\n" + FAIL_LINE):]
        no_missing = GOOD.replace(tail, tail.replace("<open>missing: [NAMES_OR_NONE]</open>", "<open>none</open>"))
        self.assertIn(16, fails(self.m(no_missing)[1]))
        no_status = GOOD.replace(tail, tail.replace(FAIL_LINE + "\n", ""))
        self.assertIn(16, fails(self.m(no_status)[1]))
        no_outcome = GOOD.replace(tail, tail.replace("<outcome>[ONE_SENTENCE]</outcome>\n", ""))
        self.assertIn(16, fails(self.m(no_outcome)[1]))
        trailing = GOOD + "\nOne more line.\n"
        self.assertIn(16, fails(self.m(trailing)[1]))
        success_last = GOOD.replace(tail, "```text\n" + SIX + "```\n")
        self.assertIn(16, fails(self.m(success_last)[1]))

    def test_46_user_message_field_fails(self):
        bad = GOOD.replace("* **note:**", "* **user-message:** always - In `<outcome>`: the text for the reader.\n* **note:**")
        self.assertIn(23, fails(self.m(bad)[1]))
        fenced = self.swap_first_fence(SIX + "```\n\n```text\nuser-message: Done.\n")
        self.assertIn(23, fails(self.m(fenced)[1]))

    def test_47_field_bullet_without_tag_warns(self):
        bad = GOOD.replace("always - In `<claims>`: the numbered screenings.", "always - The numbered screenings.")
        rc, out, _ = self.m(bad)
        self.assertEqual(rc, 0, out)
        self.assertIn(18, warns(out))

    def test_48_part_output_follows_the_same_shape(self):
        wf = os.path.join(self.tmp, "references", "workflows")
        os.makedirs(wf)
        head = ("Used by SKILL.md step 2.\n\n# Input\n\n* **x:** required - default: none - X.\n\n"
                "# Process\n\n### 1. Do it\n\nUse `x` with `Read`.\n\nDo:\n* a\n\nDon't:\n* b\n\n# Output\n\n")
        tail = "Do:\n* a\n\nDon't:\n* b\n\n"
        good = head + "```text\n" + SIX + "```\n\n" + tail + "```text\n" + FAIL + "```\n"
        old = head + "```text\nx: 1\n```\n\n" + tail + "```text\nstatus: blocked | needs-input | failed\nreason: r\nmissing: none\n```\n"
        for text, ok in ((good, True), (old, False)):
            with open(os.path.join(wf, "x.md"), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            rc, out, _ = self.m(GOOD)
            self.assertEqual(rc == 0, ok, out)
            if not ok:
                part = [l for l in out.splitlines() if l.startswith("part: ")][0]
                self.assertIn("7", part.split("failures=")[1])
                self.assertIn("16", part.split("failures=")[1])

    def test_22_slot_direct_call_fails(self):
        out = self.m(GOOD.replace("Search with", "Resolve with Skill(agentville:workspace), then search with"))[1]
        self.assertIn(22, fails(out))
        self.assertTrue(any(l.startswith("slot_direct_calls:") and "Skill(agentville:workspace)" in l for l in out.splitlines()))

    def test_22_plugin_default_mention_allowed(self):
        out = self.m(GOOD.replace("Search with", "Note the plugin default `Skill(agentville:workspace)`, then search with"))[1]
        self.assertNotIn(22, fails(out))

    def test_22_plugin_default_then_call_fails(self):
        out = self.m(GOOD.replace("Search with", "Fall back to the plugin default, then call Skill(agentville:toolbelt), then search with"))[1]
        self.assertIn(22, fails(out))
        self.assertTrue(any(l.startswith("slot_direct_calls:") and "Skill(agentville:toolbelt)" in l for l in out.splitlines()))

    def test_22_call_with_source_outside_record_fails(self):
        for text in ("Call `Skill(agentville:toolbelt) (project-x)`", "Call `Skill(agentville:toolbelt) (project-rules)`",
                     "Write `toolbelt: Skill(agentville:toolbelt) (project-rules)`"):
            out = self.m(GOOD.replace("Search with", text + ", then search with"))[1]
            self.assertIn(22, fails(out), text)

    def test_22_call_followed_by_plugin_default_record_allowed(self):
        out = self.m(GOOD.replace("Search with", "Name `Skill(agentville:toolbelt) (plugin-default)`, then search with"))[1]
        self.assertNotIn(22, fails(out))

    def test_22_imperative_verb_before_default_call_fails(self):
        for text in ("Call `Skill(agentville:toolbelt) (plugin-default)`", "Load the plugin default `Skill(agentville:workspace)`",
                     "then run Skill(agentville:draft) (plugin-default)", "Invoke the plugin default Skill(agentville:plan)",
                     "Use `Skill(agentville:report)` (plugin-default)"):
            out = self.m(GOOD.replace("Search with", text + ", then search with"))[1]
            self.assertIn(22, fails(out), text)
            self.assertTrue(any(l.startswith("slot_direct_calls:") and "Skill(agentville:" in l for l in out.splitlines()), text)

    def test_22_non_imperative_default_description_still_allowed(self):
        for text in ("The slot falls back to the plugin default `Skill(agentville:draft)`", "Name `Skill(agentville:plan) (plugin-default)`",
                     "Write `report: agentville:report (plugin-default)`"):
            out = self.m(GOOD.replace("Search with", text + ", then search with"))[1]
            self.assertNotIn(22, fails(out), text)

    def test_22_record_needs_known_source_and_own_slot(self):
        for text in ("toolbelt: agentville:toolbelt (project-x)", "workspace: agentville:toolbelt (project-rules)"):
            out = self.m(GOOD.replace("Search with", f"Write `{text}`, then search with"))[1]
            self.assertIn(22, fails(out), text)
        out = self.m(GOOD.replace("Search with", "Write `toolbelt: agentville:toolbelt (project-rules)`, then search with"))[1]
        self.assertNotIn(22, fails(out))

    def test_22_slot_without_context_injection_fails(self):
        out = self.m(GOOD.replace("Search with", "Use the `toolbelt` slot, then search with"))[1]
        self.assertIn(22, fails(out))
        self.assertIn("slot_without_context_injection: toolbelt", out)

    def test_22_slot_via_context_injection_passes(self):
        out = self.m(GOOD.replace("Search with", "Use the `toolbelt` slot through Skill(agentville:context-injection), then search with"))[1]
        self.assertNotIn(22, fails(out))

    def test_22_slot_default_skill_exempt(self):
        text = GOOD.replace('name: "demo"', 'name: "workspace"').replace("Search with", "Resolve with Skill(agentville:workspace), then search with")
        self.assertNotIn(22, fails(self.m(text)[1]))

    def test_22_plugin_default_elsewhere_on_line_does_not_exempt(self):
        line = "Fall back to the plugin default and say so in the report, then call Skill(agentville:workspace), then search with"
        out = self.m(GOOD.replace("Search with", line))[1]
        self.assertIn(22, fails(out))

    def test_22_other_call_forms_fail(self):
        for form in ("agentville:toolbelt", "/agentville:toolbelt", "Skill(toolbelt)"):
            out = self.m(GOOD.replace("Search with", f"Load {form} first, then search with"))[1]
            self.assertIn(22, fails(out), form)

    def test_22_slot_record_with_source_allowed(self):
        out = self.m(GOOD.replace("Search with", "Write `workspace: agentville:workspace (plugin-default)`, then search with"))[1]
        self.assertNotIn(22, fails(out))

    def test_22_reference_files_are_scanned(self):
        d = os.path.join(self.tmp, "withrefs")
        os.makedirs(os.path.join(d, "references"))
        with open(os.path.join(d, "references", "notes.md"), "w", encoding="utf-8") as f:
            f.write("Resolve with Skill(agentville:workspace) first.\nUse the `toolbelt` slot.\n")
        out = self.m(GOOD, folder=d)[1]
        self.assertIn(22, fails(out))
        self.assertTrue(any(l.startswith("slot_direct_calls:") and "references/notes.md:1:Skill(agentville:workspace)" in l
                            for l in out.splitlines()), out)
        self.assertIn("slot_without_context_injection: toolbelt", out)


class StageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def mk(self, root, files):
        for rel, data in files.items():
            p = os.path.join(root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(data)

    def create(self, *a):
        rc, out, err = run(STAGE, "create", *a, env={"TMPDIR": self.tmp})
        self.assertEqual(rc, 0, err)
        self.assertTrue(out.startswith("path: "))
        return out.strip()[6:]

    def test_create_named_and_default(self):
        p = self.create("acme-pr-review")
        self.assertRegex(os.path.basename(p), r"^acme-pr-review-[0-9a-f]{8}$")
        self.assertTrue(os.path.isfile(os.path.join(p, ".skill-smith-staging")))
        self.assertTrue(p.startswith(os.path.realpath(self.tmp) + "/skill-smith-staging/"))
        self.assertRegex(os.path.basename(self.create()), r"^draft-[0-9a-f]{8}$")
        self.assertNotEqual(self.create("a"), self.create("a"))

    def test_create_refuses_skills_folder(self):
        bad = os.path.join(self.tmp, ".claude", "skills")
        os.makedirs(bad)
        rc, _, err = run(STAGE, "create", env={"TMPDIR": bad})
        self.assertEqual(rc, 2)
        self.assertTrue(err)
        self.assertFalse(os.path.exists(os.path.join(bad, "skill-smith-staging")))

    def test_sync_copies_removes_reports(self):
        src, dst = os.path.join(self.tmp, "src"), os.path.join(self.tmp, "dst")
        blob = bytes(range(256))
        self.mk(src, {"SKILL.md": b"new\r\n", "references/a.md": blob, ".skill-smith-staging": b"m"})
        self.mk(dst, {"SKILL.md": b"old", "stale.txt": b"x", "old/deep.txt": b"y", ".skill-smith-staging": b"keep"})
        rc, out, err = run(STAGE, "sync", src, dst)
        self.assertEqual(rc, 0, err)
        lines = out.splitlines()
        a = os.path.join(dst, "references", "a.md")
        self.assertIn(f"written: {a}", lines)
        self.assertNotIn(f"written: {os.path.join(dst, 'SKILL.md')}", lines)
        self.assertIn(f"removed: {os.path.join(dst, 'stale.txt')}", lines)
        self.assertEqual(lines[-1], f"files: {a}")
        self.assertEqual(read_bytes(a), blob)
        self.assertEqual(read_bytes(os.path.join(dst, "SKILL.md")), b"new\r\n")
        self.assertFalse(os.path.exists(os.path.join(dst, "stale.txt")))
        self.assertFalse(os.path.exists(os.path.join(dst, "old")))
        self.assertEqual(read_bytes(os.path.join(dst, ".skill-smith-staging")), b"keep")

    def test_sync_creates_destination_and_none(self):
        src, dst = os.path.join(self.tmp, "src"), os.path.join(self.tmp, "new", "dst")
        self.mk(src, {"SKILL.md": b"x", ".skill-smith-staging": b"m"})
        rc, out, _ = run(STAGE, "sync", src, dst)
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "files: none")
        self.assertTrue(os.path.isfile(os.path.join(dst, "SKILL.md")))
        self.assertFalse(os.path.exists(os.path.join(dst, ".skill-smith-staging")))

    def test_sync_refusals(self):
        rc, _, err = run(STAGE, "sync", os.path.join(self.tmp, "missing"), os.path.join(self.tmp, "d"))
        self.assertEqual(rc, 2)
        self.assertTrue(err)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "d")))
        self.assertEqual(run(STAGE, "sync", self.tmp, self.tmp)[0], 2)
        self.assertEqual(run(STAGE, "sync", self.tmp)[0], 2)

    def install(self, src, dst, scope, project, user):
        return run(STAGE, "install", src, dst, "--scope", scope, "--project-root", project, "--user-root", user)

    def roots(self):
        project, user = os.path.join(self.tmp, "proj"), os.path.join(self.tmp, "home")
        os.makedirs(project)
        os.makedirs(user)
        return project, user

    def test_install_accepts_project_and_user_scope(self):
        project, user = self.roots()
        stg = os.path.join(self.tmp, "stg")
        self.mk(stg, {"SKILL.md": b"x", "references/a.md": b"a", ".skill-smith-staging": b"m"})
        for scope, root in (("project", project), ("user", user)):
            dst = os.path.join(root, ".claude", "skills", "acme-pr-review")
            rc, out, err = self.install(stg, dst, scope, project, user)
            self.assertEqual(rc, 0, err)
            self.assertIn("files: ", out)
            self.assertEqual(read_bytes(os.path.join(dst, "SKILL.md")), b"x")
            self.assertEqual(read_bytes(os.path.join(dst, "references", "a.md")), b"a")

    def test_install_refuses_plugin_target(self):
        project, user = self.roots()
        stg = os.path.join(self.tmp, "stg")
        self.mk(stg, {"SKILL.md": b"x", ".skill-smith-staging": b"m"})
        plugin = os.path.join(project, "plugins", "acme")
        self.mk(plugin, {".claude-plugin/plugin.json": b"{}"})
        for scope in ("project", "user"):
            for dst in (os.path.join(plugin, "skills", "acme-pr-review"),
                        os.path.join(plugin, ".claude", "skills", "acme-pr-review"),
                        os.path.join(project, "plugins", "other", "skills", "acme-pr-review"),
                        os.path.join(plugin, ".claude-plugin", "acme-pr-review")):
                rc, _, err = self.install(stg, dst, scope, project, user)
                self.assertEqual(rc, 2, dst)
                self.assertIn("refused", err)
                self.assertFalse(os.path.exists(os.path.join(dst, "SKILL.md")), dst)
        # a project root that is itself a plugin is refused even at its own .claude/skills
        rc, _, err = self.install(stg, os.path.join(plugin, ".claude", "skills", "acme-pr-review"), "project", plugin, user)
        self.assertEqual(rc, 2)
        self.assertIn("plugin", err)
        self.assertFalse(os.path.exists(os.path.join(plugin, ".claude", "skills")))

    def test_install_accepts_project_root_under_plugins_folder(self):
        stg = os.path.join(self.tmp, "stg")
        self.mk(stg, {"SKILL.md": b"x", ".skill-smith-staging": b"m"})
        project = os.path.join(self.tmp, "plugins", "myapp")
        user = os.path.join(self.tmp, "home")
        os.makedirs(project)
        os.makedirs(user)
        dst = os.path.join(project, ".claude", "skills", "acme-pr-review")
        rc, _, err = self.install(stg, dst, "project", project, user)
        self.assertEqual(rc, 0, err)
        self.assertTrue(os.path.isfile(os.path.join(dst, "SKILL.md")))

    def test_install_refuses_other_folders_and_missing_scope(self):
        project, user = self.roots()
        stg = os.path.join(self.tmp, "stg")
        self.mk(stg, {"SKILL.md": b"x", ".skill-smith-staging": b"m"})
        skills = os.path.join(project, ".claude", "skills")
        for dst, scope in ((os.path.join(self.tmp, "elsewhere", "acme-pr-review"), "project"),
                           (skills, "project"),
                           (os.path.join(skills, "acme-pr-review", "deep"), "project"),
                           (os.path.join(skills, "Bad Name"), "project"),
                           (os.path.join(skills, "acme-pr-review"), "user"),
                           (os.path.join(skills, "acme-pr-review"), "plugin")):
            self.assertEqual(self.install(stg, dst, scope, project, user)[0], 2, (dst, scope))
        self.assertEqual(run(STAGE, "install", stg, os.path.join(skills, "acme-pr-review"),
                             "--project-root", project)[0], 2)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "elsewhere")))
        self.assertFalse(os.path.exists(os.path.join(skills, "acme-pr-review")))

    def test_sync_refuses_plugin_on_either_side(self):
        src = os.path.join(self.tmp, "src")
        self.mk(src, {"SKILL.md": b"x"})
        plugin = os.path.join(self.tmp, "plugins", "acme", "skills", "acme-pr-review")
        self.mk(plugin, {"SKILL.md": b"old"})
        self.mk(os.path.join(self.tmp, "plugins", "acme"), {".claude-plugin/plugin.json": b"{}"})
        self.assertEqual(run(STAGE, "sync", src, plugin)[0], 2)
        self.assertEqual(read_bytes(os.path.join(plugin, "SKILL.md")), b"old")
        self.assertEqual(run(STAGE, "sync", plugin, os.path.join(self.tmp, "out"))[0], 2)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "out")))

    def test_clean(self):
        p = self.create("x")
        self.mk(p, {"SKILL.md": b"a", "r/b.md": b"b"})
        rc, out, _ = run(STAGE, "clean", p)
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), f"removed: {p}")
        self.assertFalse(os.path.exists(p))

    def test_clean_refuses_unmarked_and_missing(self):
        d = os.path.join(self.tmp, "live")
        self.mk(d, {"SKILL.md": b"a"})
        rc, _, err = run(STAGE, "clean", d)
        self.assertEqual(rc, 2)
        self.assertTrue(err)
        self.assertTrue(os.path.exists(os.path.join(d, "SKILL.md")))
        self.assertEqual(run(STAGE, "clean", os.path.join(self.tmp, "nope"))[0], 2)
        self.assertEqual(run(STAGE, "clean")[0], 2)

    def test_seed_keeps_marker(self):
        live = os.path.join(self.tmp, "live")
        self.mk(live, {"SKILL.md": b"skill", "references/a.md": b"a", "evals/evals.json": b"{}"})
        p = self.create("seed")
        rc, out, err = run(STAGE, "sync", live, p)
        self.assertEqual(rc, 0, err)
        self.assertTrue(os.path.isfile(os.path.join(p, ".skill-smith-staging")))
        self.assertEqual(read_bytes(os.path.join(p, "evals", "evals.json")), b"{}")
        dst = os.path.join(self.tmp, "installed")
        rc, out, err = run(STAGE, "sync", p, dst)
        self.assertEqual(rc, 0, err)
        self.assertTrue(os.path.isfile(os.path.join(dst, "references", "a.md")))
        self.assertFalse(os.path.exists(os.path.join(dst, ".skill-smith-staging")))
        self.assertEqual(run(STAGE, "clean", p)[0], 0)
        self.assertFalse(os.path.exists(p))

    def test_usage(self):
        self.assertEqual(run(STAGE)[0], 2)
        self.assertEqual(run(STAGE, "bogus")[0], 2)


if __name__ == "__main__":
    unittest.main()
