#!/usr/bin/env python3
"""Staging helper for agent-smith.

stage.py create [name]                         make a marked scratch folder, print path: <abs path>
stage.py fork <template> <base> <out> <name>   write <out> from the template, pasting the base
                                               agent's core blocks over each {{ CORE x }} line
stage.py seed <agent-file> <folder>            copy an existing agent file into a staging folder
stage.py install <file> <dir> [--replace]      copy a compiled agent file into an agents folder
stage.py clean <folder>                        remove a folder only if create marked it
Exit: 0 success, 2 usage or safety refusal.
"""
import os
import re
import secrets
import shutil
import sys

MARKER = ".agent-smith-staging"
CORE_LINE_RE = re.compile(r"^\{\{ CORE ([a-z-]+) \}\}\s*$")
CORE_BEGIN_RE = re.compile(r"^<!-- core:begin ([a-z-]+) -->\s*$")
CORE_END = "<!-- core:end {} -->"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def norm(path):
    return path.replace(os.sep, "/").rstrip("/") + "/"


def in_install_folder(path):
    p = norm(path)
    return "/.claude/agents/" in p or "/.claude/skills/" in p


def read_text(path):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return f.read().replace("\r\n", "\n")
    except (OSError, UnicodeError) as e:
        die(f"cannot read {path}: {e}")


def core_blocks(text):
    """Return {name: block text including markers} from an agent file."""
    lines = text.split("\n")
    out, i = {}, 0
    while i < len(lines):
        m = CORE_BEGIN_RE.match(lines[i])
        if m:
            name = m.group(1)
            end = CORE_END.format(name)
            j = next((k for k in range(i + 1, len(lines)) if lines[k].strip() == end), None)
            if j is None:
                die(f"unterminated core block: {name}")
            out[name] = "\n".join(lines[i:j + 1])
            i = j
        i += 1
    return out


def create(args):
    if len(args) > 1:
        die("usage: stage.py create [name]")
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", args[0]).strip(".-") if args else ""
    name = name or "draft"
    base = os.path.realpath(os.path.join(os.environ.get("TMPDIR") or "/tmp", "agent-smith-staging"))
    if in_install_folder(base):
        die(f"refused: {base} is inside a .claude/agents/ or .claude/skills/ folder")
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
    with open(os.path.join(path, MARKER), "w") as f:
        f.write("created by agent-smith stage.py\n")
    print(f"path: {path}")
    return 0


def fork(args):
    if len(args) != 4:
        die("usage: stage.py fork <template> <base> <out> <name>")
    template, base, out, name = args
    if not NAME_RE.match(name) or len(name) > 64:
        die(f"refused: name must be kebab-case, at most 64 characters: {name}")
    if in_install_folder(os.path.abspath(out)):
        die("refused: write the fork under the staging folder, not an install folder")
    blocks = core_blocks(read_text(base))
    lines, missing = [], []
    for line in read_text(template).split("\n"):
        m = CORE_LINE_RE.match(line)
        if m:
            if m.group(1) not in blocks:
                missing.append(m.group(1))
                continue
            lines.append(blocks[m.group(1)])
        else:
            lines.append(line.replace("[[agent-name]]", name))
    if missing:
        die("refused: base has no core block for: " + ", ".join(missing))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))
    print(f"written: {os.path.abspath(out)}")
    print("core: " + ", ".join(sorted(blocks)))
    return 0


def seed(args):
    if len(args) != 2:
        die("usage: stage.py seed <agent-file> <folder>")
    src, folder = args
    if not os.path.isfile(src):
        die(f"refused: not a file: {src}")
    if not os.path.isfile(os.path.join(folder, MARKER)):
        die(f"refused: {folder} has no {MARKER} marker")
    dst = os.path.join(os.path.abspath(folder), os.path.basename(src))
    shutil.copyfile(src, dst)
    print(f"written: {dst}")
    return 0


def install(args):
    replace = "--replace" in args
    args = [a for a in args if a != "--replace"]
    if len(args) != 2:
        die("usage: stage.py install <file> <dir> [--replace]")
    src, folder = args
    if not os.path.isfile(src) or not src.endswith(".md"):
        die(f"refused: not an agent .md file: {src}")
    if os.path.exists(folder) and not os.path.isdir(folder):
        die(f"refused: destination is not a folder: {folder}")
    dst = os.path.join(os.path.abspath(folder), os.path.basename(src))
    if os.path.exists(dst) and not replace:
        die(f"refused: {dst} exists; pass --replace to overwrite")
    existed = os.path.exists(dst)
    os.makedirs(folder, exist_ok=True)
    shutil.copyfile(src, dst)
    print(f"written: {dst}")
    print(f"replaced: {'yes' if existed else 'no'}")
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
    cmds = {"create": create, "fork": fork, "seed": seed, "install": install, "clean": clean}
    if len(argv) < 2 or argv[1] not in cmds:
        die("usage: stage.py create [name] | fork <template> <base> <out> <name> | "
            "seed <agent-file> <folder> | install <file> <dir> [--replace] | clean <folder>")
    return cmds[argv[1]](argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
