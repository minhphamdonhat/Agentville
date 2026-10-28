#!/usr/bin/env python3
"""Staging helper for agent-smith.

stage.py create [name]                         make a marked scratch folder, print path: <abs path>
stage.py fork <template> <base> <out> <name>   write <out> from the template, pasting the base
                                               agent's core blocks over each {{ CORE x }} line; a base
                                               with no core block (standalone) has its numbered rules
                                               pasted between base markers over {{ CORE constraints }};
                                               a base other than the worker is named as metadata.base
stage.py seed <agent-file> <folder>            copy an existing agent file into a staging folder
stage.py install <file> <dir> --scope plugin|project [--replace] [--project-root P]
                                               copy a compiled agent file into an agents folder;
                                               <dir> must be exactly
                                                 plugin:  <root>/plugins/agentville/agents
                                                          (needs <root>/plugins/agentville/.claude-plugin/plugin.json)
                                                 project: <root>/.claude/agents
                                               The user scope is refused.
stage.py clean <folder>                        remove a folder only if create marked it
This is the Agentville maintainer copy: it may write into the Agentville plugin, which the shipped copy never does.
The project root defaults to $CLAUDE_PROJECT_DIR, then the working folder.
Exit: 0 success, 2 usage or safety refusal.
"""
import os
import re
import secrets
import shutil
import sys
import tempfile

MARKER = ".agent-smith-staging"
CORE_LINE_RE = re.compile(r"^\{\{ CORE ([a-z-]+) \}\}\s*$")
CORE_BEGIN_RE = re.compile(r"^<!-- core:begin ([a-z-]+) -->\s*$")
CORE_END = "<!-- core:end {} -->"
BASE_BEGIN = "<!-- base:begin {} -->"
BASE_END = "<!-- base:end {} -->"
DEFAULT_BASE_NAME = "worker"
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
EXTEND_RE = re.compile(r"^\d+\. \*\*\[\[Extending rule title\]\]")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SCOPES = ("plugin", "project")
PLUGIN_NAME = "agentville"
PLUGIN_PARTS = (".claude-plugin",)


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def norm(path):
    return os.path.normcase(path).replace(os.sep, "/").rstrip("/") + "/"


def in_install_folder(path):
    p = norm(path)
    return "/.claude/agents/" in p or "/.claude/skills/" in p


def inside_plugin(path):
    """True when path sits under a .claude-plugin folder, or under a folder with .claude-plugin/plugin.json."""
    for p in {os.path.abspath(path), os.path.realpath(path)}:
        if any(part in PLUGIN_PARTS for part in norm(p).strip("/").split("/")):
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


def check_target(folder, scope, project_root):
    """Refuse unless folder is exactly the agents folder of the chosen scope.

    plugin: <root>/plugins/agentville/agents, and only when that plugin has .claude-plugin/plugin.json.
    project: <root>/.claude/agents, outside every plugin.
    """
    if scope not in SCOPES:
        die(f"refused: scope must be plugin or project, not {scope}")
    root = os.path.realpath(project_root)
    if scope == "plugin":
        plugin = os.path.join(root, "plugins", PLUGIN_NAME)
        if not os.path.isfile(os.path.join(plugin, ".claude-plugin", "plugin.json")):
            die(f"refused: no plugin at {plugin}: {os.path.join(plugin, '.claude-plugin', 'plugin.json')} is missing")
        expected = os.path.join(os.path.realpath(plugin), "agents")
    else:
        expected = os.path.join(root, ".claude", "agents")
        if inside_plugin(expected):
            die(f"refused: {expected} is inside a plugin; the project scope installs outside every plugin")
    if os.path.normcase(os.path.realpath(folder)) != os.path.normcase(expected):
        die(f"refused: {folder} is not {expected}; the {scope} scope installs there only")


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


def frontmatter_name(text, fallback):
    """The `name:` of an agent file's frontmatter, else the fallback."""
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            m = re.match(r"^name:\s*[\"']?([a-z0-9-]+)[\"']?\s*$", line)
            if m:
                return m.group(1)
    return fallback


def constraints_rules(text):
    """A standalone base's numbered rules: its `# Constraints` section up to the next H1, blank edges trimmed."""
    lines, fence, lo, hi = text.split("\n"), None, None, None
    for i, line in enumerate(lines):
        m = FENCE_RE.match(line)
        if m:
            fence = None if fence == m.group(1)[0] else (fence or m.group(1)[0])
            continue
        if fence is None and re.match(r"^#\s+\S", line):
            if lo is not None:
                hi = i
                break
            if line.strip() == "# Constraints":
                lo = i + 1
    if lo is None:
        return None
    body = lines[lo:hi if hi is not None else len(lines)]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return body


def add_metadata_base(lines, base_name):
    """Insert `  base: <name>` under the frontmatter's `metadata:` key."""
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            break
        if line.rstrip() == "metadata:":
            j = i + 1
            while j < len(lines) and lines[j].startswith((" ", "\t")) and lines[j].strip():
                j += 1
            lines.insert(j, f"  base: {base_name}")
            return lines
    die("refused: the template has no metadata: key to hold metadata.base")


def create(args):
    if len(args) > 1:
        die("usage: stage.py create [name]")
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", args[0]).strip(".-") if args else ""
    name = name or "draft"
    base = os.path.realpath(os.path.join(tempfile.gettempdir(), "agent-smith-staging"))
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
    with open(os.path.join(path, MARKER), "w", encoding="utf-8", newline="\n") as f:
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
    base_text = read_text(base)
    base_name = frontmatter_name(base_text, os.path.splitext(os.path.basename(base))[0])
    blocks = core_blocks(base_text)
    rules = None if blocks else constraints_rules(base_text)
    if not blocks and rules is None:
        die(f"refused: base has neither core blocks nor a # Constraints section: {base}")
    next_rule = 1 + max([int(m.group(1)) for m in (re.match(r"^(\d+)\. ", l) for l in rules or []) if m] or [0])
    lines, missing, skip_blank = [], [], False
    for line in read_text(template).split("\n"):
        if skip_blank and not line.strip():
            skip_blank = False
            continue
        skip_blank = False
        m = CORE_LINE_RE.match(line)
        if m and rules is not None:
            # A standalone base has no worker core: its numbered rules stand in for the constraints core.
            if m.group(1) == "constraints":
                lines += [BASE_BEGIN.format(base_name)] + rules + [BASE_END.format(base_name)]
            else:
                skip_blank = True
            continue
        if m:
            if m.group(1) not in blocks:
                missing.append(m.group(1))
                continue
            lines.append(blocks[m.group(1)])
        elif rules is not None and EXTEND_RE.match(line):
            lines.append(re.sub(r"^\d+", str(next_rule), line.replace("[[agent-name]]", name)))
        else:
            lines.append(line.replace("[[agent-name]]", name))
    if missing:
        die("refused: base has no core block for: " + ", ".join(missing))
    if base_name != DEFAULT_BASE_NAME:
        lines = add_metadata_base(lines, base_name)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))
    print(f"written: {os.path.abspath(out)}")
    print(f"base: {base_name}" + (" (standalone)" if rules is not None else ""))
    if rules is not None:
        print(f"core: base {base_name}")
        print(f"next-rule: {next_rule}")
    else:
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
    args = list(args)
    replace = "--replace" in args
    args = [a for a in args if a != "--replace"]
    scope = take_option(args, "--scope")
    project_root = take_option(args, "--project-root") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if len(args) != 2 or scope is None:
        die("usage: stage.py install <file> <dir> --scope plugin|project [--replace]")
    src, folder = args
    check_target(folder, scope, project_root)
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
            "seed <agent-file> <folder> | install <file> <dir> --scope plugin|project [--replace] | clean <folder>")
    return cmds[argv[1]](argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
