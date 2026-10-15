#!/usr/bin/env python3
"""Staging helper for skill-smith.

stage.py create [name]        make a marked scratch folder, print path: <abs path>
stage.py sync <from> <to>     mirror <from> into <to> byte for byte
stage.py clean <folder>       remove a folder only if create marked it
Exit: 0 success, 2 usage or safety refusal.
"""
import os
import re
import secrets
import shutil
import sys

MARKER = ".skill-smith-staging"


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def in_skills_folder(path):
    return "/.claude/skills/" in (path.replace(os.sep, "/").rstrip("/") + "/")


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
    cmds = {"create": create, "sync": sync, "clean": clean}
    if len(argv) < 2 or argv[1] not in cmds:
        die("usage: stage.py create [name] | sync <from> <to> | clean <folder>")
    return cmds[argv[1]](argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
