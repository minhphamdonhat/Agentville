#!/usr/bin/env python3
"""Tests for scan.py: PS-22c package-runner pins and bare-repository scans.

Run from the repository root:
  python3 .claude/skills/plugin-security/scripts/test_scan.py
On Windows run `py -3` for `python3`. Needs only Python 3.8+ and git.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCAN = HERE / "scan.py"
SHA = "0123456789abcdef0123456789abcdef01234567"
GIT = ["git", "-c", "user.name=Acme Dev", "-c", "user.email=dev@users.noreply.github.com",
       "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c", "init.defaultBranch=main"]

spec = importlib.util.spec_from_file_location("plugin_security_scan", SCAN)
scan_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan_mod)


def git(cwd, *args):
    r = subprocess.run(GIT + list(args), cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), r.stderr))
    return r.stdout


def mcp(command, args, name="acme"):
    return json.dumps({"mcpServers": {name: {"command": command, "args": args}}}, indent=2) + "\n"


def make_repo(root, files):
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "feat(acme): add fixtures")
    return root


def run_scan(repo, *extra):
    r = subprocess.run([sys.executable, str(SCAN), "--repo", str(repo), "--format", "json", "--external", "off",
                        *extra], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace")
    report = json.loads(r.stdout) if r.stdout.strip() else None
    return r.returncode, report, r.stderr


def hit_paths(report, rule):
    """Paths of every tip location that carries the rule."""
    return sorted(loc.split(":")[0] for f in report["findings"] if f["rule"] == rule for loc in f["locations"])


def hit_locations(report, rule):
    return [loc for f in report["findings"] if f["rule"] == rule for loc in f["locations"]]


class PackageRunnerPins(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        git_url = "git+https://github.com/acme/server.git"
        cases = {
            "git-sha": mcp("uvx", ["--from", "%s@%s" % (git_url, SHA), "acme-server"]),
            "git-sha-subdir": mcp("uvx", ["--from", "%s@%s#subdirectory=apps/api" % (git_url, SHA), "acme-server"]),
            "git-tag": mcp("uvx", ["--from", "%s@v1.0.0" % git_url, "acme-server"]),
            "git-short-sha": mcp("uvx", ["--from", "%s@0123abc" % git_url, "acme-server"]),
            "git-branch": mcp("uvx", ["--from", "%s@main" % git_url, "acme-server"]),
            "npx-scoped-exact": mcp("npx", ["-y", "@acme/server@1.2.3"]),
            "npx-exact": mcp("npx", ["-y", "acme-server@1.2.3"]),
            "npx-latest": mcp("npx", ["-y", "@acme/server@latest"]),
            "npx-caret": mcp("npx", ["-y", "@acme/server@^1.2.0"]),
            "npx-range": mcp("npx", ["-y", "acme-server@>=1"]),
            "npx-partial": mcp("npx", ["-y", "acme-server@1.2"]),
            "npx-bare": mcp("npx", ["-y", "acme-server"]),
            "npx-no-args": mcp("npx", []),
            "pipx-exact": mcp("pipx", ["run", "acme-server==1.2.3"]),
            "pipx-range": mcp("pipx", ["run", "acme-server>=1.2"]),
            "pipx-wildcard": mcp("pipx", ["run", "acme-server==1.*"]),
            "bunx-exact": mcp("bunx", ["acme-server@2.0.1"]),
            "local-command": mcp("node", ["server.js"]),
        }
        files = {"plugins/acme/%s/.mcp.json" % k: v for k, v in cases.items()}
        files["plugins/acme/invalid-json/.mcp.json"] = '{\n  // comment makes this invalid JSON\n  "mcpServers": ' \
                                                       '{"acme": {"command": "npx", "args": ["acme-server@1.2.3"]}}\n}\n'
        cls.repo = make_repo(Path(cls.tmp.name) / "fixture", files)
        cls.code, cls.report, cls.err = run_scan(cls.repo)
        cls.fired = set(p.split("/")[2] for p in hit_paths(cls.report, "PS-22c"))
        cls.fired_22 = set(p.split("/")[2] for p in hit_paths(cls.report, "PS-22"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_scan_runs(self):
        self.assertIn(self.code, (0, 1), self.err)

    def test_git_full_sha_clears(self):
        self.assertNotIn("git-sha", self.fired)
        self.assertNotIn("git-sha", self.fired_22)

    def test_git_full_sha_with_subdirectory_clears(self):
        self.assertNotIn("git-sha-subdir", self.fired)
        self.assertNotIn("git-sha-subdir", self.fired_22)

    def test_git_tag_fires_both_rules(self):
        self.assertIn("git-tag", self.fired)
        self.assertIn("git-tag", self.fired_22)

    def test_git_short_sha_and_branch_fire(self):
        for case in ("git-short-sha", "git-branch"):
            self.assertIn(case, self.fired)
            self.assertIn(case, self.fired_22)

    def test_npm_exact_version_clears(self):
        for case in ("npx-scoped-exact", "npx-exact", "bunx-exact"):
            self.assertNotIn(case, self.fired)

    def test_npm_latest_range_partial_and_bare_fire(self):
        for case in ("npx-latest", "npx-caret", "npx-range", "npx-partial", "npx-bare", "npx-no-args"):
            self.assertIn(case, self.fired)

    def test_latest_still_fires_ps22b(self):
        self.assertIn("npx-latest", set(p.split("/")[2] for p in hit_paths(self.report, "PS-22b")))

    def test_pip_exact_version_clears(self):
        self.assertNotIn("pipx-exact", self.fired)

    def test_pip_range_and_wildcard_fire(self):
        self.assertIn("pipx-range", self.fired)
        self.assertIn("pipx-wildcard", self.fired)

    def test_non_runner_command_never_fires(self):
        self.assertNotIn("local-command", self.fired)

    def test_invalid_json_falls_back_to_the_line_regex(self):
        self.assertIn("invalid-json", self.fired)

    def test_severity_stays_medium(self):
        severities = {f["severity"] for f in self.report["findings"] if f["rule"] == "PS-22c"}
        self.assertEqual(severities, {"medium"})

    def test_pinned_server_is_judged_by_its_own_entry(self):
        doc = {"mcpServers": {
            "pinned": {"command": "npx", "args": ["-y", "@acme/server@1.2.3"]},
            "loose": {"command": "npx", "args": ["-y", "@acme/other"]},
        }}
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp) / "two", {"plugins/acme/.mcp.json": json.dumps(doc, indent=2) + "\n"})
            code, report, err = run_scan(repo)
        self.assertIn(code, (0, 1), err)
        lines = [int(loc.split(":")[1].split(" ")[0]) for loc in hit_locations(report, "PS-22c")]
        text = json.dumps(doc, indent=2).splitlines()
        loose_command = [n for n, l in enumerate(text, 1) if '"command"' in l][1]
        self.assertEqual(lines, [loose_command])


class RunnerVerdicts(unittest.TestCase):
    def verdicts(self, command, args):
        return scan_mod.runner_verdicts(mcp(command, args))

    def test_pins(self):
        self.assertEqual(self.verdicts("uvx", ["acme==1.2.3"]), [False])
        self.assertEqual(self.verdicts("uvx", ["--from=git+https://github.com/acme/s.git@%s" % SHA, "s"]), [False])
        self.assertEqual(self.verdicts("npx", ["@acme/server@1.2.3-rc.1"]), [False])

    def test_unpinned(self):
        for args in (["acme"], ["acme@latest"], ["acme@^1.2.3"], ["acme@~1.2.3"], ["acme@1.2"], ["acme==1.*"],
                     ["git+https://github.com/acme/s.git@" + SHA[:7]], ["git+https://github.com/acme/s.git@v1.0.0"]):
            self.assertEqual(self.verdicts("npx", args), [True], args)

    def test_not_json(self):
        self.assertIsNone(scan_mod.runner_verdicts("{ not json"))


class BareRepository(unittest.TestCase):
    def test_bare_clone_scans_without_failing(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = make_repo(Path(tmp) / "fixture", {
                "plugins/acme/.mcp.json": mcp("uvx", ["--from", "git+https://github.com/acme/s.git@" + SHA, "s"]),
                "README.md": "# Acme\n",
            })
            bare = Path(tmp) / "fixture.git"
            git(Path(tmp), "clone", "-q", "--bare", str(src), str(bare))
            self.assertEqual(git(bare, "rev-parse", "--is-bare-repository").strip(), "true")
            code, report, err = run_scan(bare)
            self.assertIn(code, (0, 1), err)
            self.assertNotIn("error:", err)
            self.assertEqual(report["stats"]["stash"], 0)
            self.assertTrue(any("bare repository" in n and "stash" in n for n in report["notes"]), report["notes"])
            self.assertTrue(any("PS-45" in n for n in report["notes"]), report["notes"])
            self.assertEqual([f for f in report["findings"] if f["rule"] == "PS-45"], [])
            self.assertEqual([f for f in report["findings"] if f["rule"] == "PS-22c"], [])

    def test_bare_clone_text_report_names_the_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = make_repo(Path(tmp) / "fixture", {"README.md": "# Acme\n"})
            bare = Path(tmp) / "fixture.git"
            git(Path(tmp), "clone", "-q", "--bare", str(src), str(bare))
            r = subprocess.run([sys.executable, str(SCAN), "--repo", str(bare), "--external", "off"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace")
            self.assertIn(r.returncode, (0, 1), r.stderr)
            self.assertIn("note: bare repository", r.stdout)

    def test_work_tree_repo_still_lists_stash_and_probes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp) / "fixture", {"README.md": "# Acme\n"})
            (repo / "README.md").write_text("# Acme docs\n", encoding="utf-8", newline="\n")
            git(repo, "stash")
            code, report, err = run_scan(repo)
            self.assertIn(code, (0, 1), err)
            self.assertEqual(report["notes"], [])
            self.assertEqual(report["stats"]["stash"], 1)
            self.assertTrue(hit_paths(report, "PS-45"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
