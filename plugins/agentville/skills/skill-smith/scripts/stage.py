#!/usr/bin/env python3
"""Staging helper for skill-smith.

stage.py create [name]        make a marked scratch folder, print path: <abs path>
stage.py sync <from> <to>     mirror <from> into <to> byte for byte; refuses a plugin on either side
stage.py install <staging> <skill-folder> --scope project|user [--project-root P] [--user-root U]
                              mirror a staging folder onto <skill-folder>, which must be exactly
                              <root>/.claude/skills/<skill-name> of the chosen scope, never in a plugin
stage.py clean <folder>       remove a folder only if create marked it
The project root defaults to $CLAUDE_PROJECT_DIR, then the working folder; the user root to the home folder.
Exit: 0 success, 2 usage or safety refusal.
"""
import os
import re
import secrets
import shutil
import sys

MARKER = ".skill-smith-staging"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SCOPES = ("project", "user")
PLUGIN_PARTS = (".claude-plugin",)


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def in_skills_folder(path):
    return "/.claude/skills/" in (path.replace(os.sep, "/").rstrip("/") + "/")


def inside_plugin(path):
    """True when path sits under a .claude-plugin folder, or under a folder with .claude-plugin/plugin.json."""
    for p in {os.path.abspath(path), os.path.realpath(path)}:
        if any(part in PLUGIN_PARTS for part in p.replace(os.sep, "/").strip("/").split("/")):
            return True
        d = p
        while True:
            if os.path.isfile(os.path.join(d, ".claude-plugin", "plugin.json")):
                return True
            up = os.path.dirname(d)
            if up == d:
                break
            d = up
    return False


def take_option(args, flag):
    """Remove `flag value` from args and return the value, or None."""
    if flag not in args:
        return None
    i = args.index(flag)
    if i + 1 >= len(args) or args[i + 1].startswith("--"):
        die(f"usage: {flag} needs a value")
    value = args[i + 1]
    del args[i:i + 2]
    return value


def check_target(folder, scope, project_root, user_root):
    """Refuse unless folder is <root>/.claude/skills/<name> for the chosen scope and outside every plugin."""
    if scope not in SCOPES:
        die("refused: scope must be project or user")
    root = project_root if scope == "project" else user_root
    skills = os.path.join(os.path.realpath(root), ".claude", "skills")
    if inside_plugin(folder) or inside_plugin(skills):
        die(f"refused: {folder} is inside a plugin; skills install to project or user scope only")
    real = os.path.realpath(folder)
    if os.path.dirname(real) != skills or not NAME_RE.match(os.path.basename(real)):
        die(f"refused: {folder} is not {skills}/<skill-name>; the {scope} scope installs there only")


def create(args):
    if len(args) > 1:
        die("usage: stage.py create [name]")
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", args[0]).strip(".-") if args else ""
    name = name or "draft"
    base = os.path.realpath(os.path.join(os.environ.get("TMPDIR") or "/tmp", "skill-smith-staging"))
    if in_skills_folder(base):
        die(f"refused: {base} is inside a .claude/skills/ folder")
    os.makedirs(base, exist_ok=True)
    for _ in range(10):
        path = os.path.join(base, f"{name}-{secrets.token_hex(4)}")
        try:
            os.mkdir(path)
            break
        except FileExistsError:
            continue
    else:
        die("could not create a unique folder")
    path = os.path.realpath(path)
    if in_skills_folder(path):
        os.rmdir(path)
        die(f"refused: {path} is inside a .claude/skills/ folder")
    with open(os.path.join(path, MARKER), "w") as f:
        f.write("created by skill-smith stage.py\n")
    print(f"path: {path}")
    return 0


def files_under(root):
    out = set()
    for d, dirs, fs in os.walk(root):
        for f in fs:
            rel = os.path.relpath(os.path.join(d, f), root)
            if rel != MARKER:
                out.add(rel)
    return out


def sync(args):
    if len(args) != 2:
        die("usage: stage.py sync <from> <to>")
    src, dst = os.path.abspath(args[0]), os.path.abspath(args[1])
    if inside_plugin(src) or inside_plugin(dst):
        die("refused: a plugin is on one side; skill-smith never changes a plugin")
    return mirror(src, dst)


def mirror(src, dst):
    if not os.path.isdir(src):
        die(f"refused: source folder does not exist: {src}")
    if os.path.exists(dst) and not os.path.isdir(dst):
        die(f"refused: destination is not a folder: {dst}")
    rs, rd = os.path.realpath(src), os.path.realpath(dst)
    if rs == rd or rd.startswith(rs + os.sep) or rs.startswith(rd + os.sep):
        die("refused: source and destination overlap")
    os.makedirs(dst, exist_ok=True)
    want = files_under(src)
    have = files_under(dst)
    lines, written = [], []
    for rel in sorted(want):
        target = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(os.path.join(src, rel), target)
        if rel != "SKILL.md":
            lines.append(f"written: {target}")
            written.append(target)
    for rel in sorted(have - want):
        os.remove(os.path.join(dst, rel))
        lines.append(f"removed: {os.path.join(dst, rel)}")
    for d, dirs, fs in os.walk(dst, topdown=False):
        if d != dst and not os.listdir(d):
            os.rmdir(d)
    lines.append("files: " + (", ".join(written) if written else "none"))
    print("\n".join(lines))
    return 0


def install(args):
    args = list(args)
    scope = take_option(args, "--scope")
    project_root = take_option(args, "--project-root") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    user_root = take_option(args, "--user-root") or os.path.expanduser("~")
    if len(args) != 2 or scope is None:
        die("usage: stage.py install <staging> <skill-folder> --scope project|user")
    src, dst = os.path.abspath(args[0]), os.path.abspath(args[1])
    check_target(dst, scope, project_root, user_root)
    return mirror(src, dst)


def clean(args):
    if len(args) != 1:
        die("usage: stage.py clean <folder>")
    folder = os.path.abspath(args[0])
    if os.path.islink(folder) or not os.path.isdir(folder):
        die(f"refused: not a staging folder: {folder}")
    if not os.path.isfile(os.path.join(folder, MARKER)):
        die(f"refused: {folder} has no {MARKER} marker")
    shutil.rmtree(folder)
    print(f"removed: {folder}")
    return 0


def main(argv):
    cmds = {"create": create, "sync": sync, "install": install, "clean": clean}
    if len(argv) < 2 or argv[1] not in cmds:
        die("usage: stage.py create [name] | sync <from> <to> | "
            "install <staging> <skill-folder> --scope project|user | clean <folder>")
    return cmds[argv[1]](argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
