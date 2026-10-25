"""Claude Code target: the plugin through the `claude` CLI, else through settings files."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

from agentville.console import Console
from agentville.files import FileEditError, append_lines, merge_json_object, read_json_object
from agentville.targets.base import EXIT_FAILED, EXIT_OK, InstallOptions

MARKETPLACE_NAME = "minhphamdo"
MARKETPLACE_REPO = "minhphamdonhat/Agentville"
PLUGIN_IDS = {
    "stable": f"agentville@{MARKETPLACE_NAME}",
    "beta": f"agentville-beta@{MARKETPLACE_NAME}",
    "dev": f"agentville-dev@{MARKETPLACE_NAME}",
}
# The two steering lines README.md gives for running Agentville under any agent.
STEERING_LINES = (
    "- Load `Skill(agentville:root-agent)` and follow it in every reply.",
    "- Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it.",
)


def plugin_id(channel: str) -> str:
    return PLUGIN_IDS[channel]


def settings_path(options: InstallOptions) -> Path:
    if options.scope == "project":
        return options.project_dir / ".claude" / "settings.json"
    return options.home / ".claude" / "settings.json"


def claude_md_path(options: InstallOptions) -> Path:
    if options.scope == "project":
        return options.project_dir / "CLAUDE.md"
    return options.home / ".claude" / "CLAUDE.md"


def cli_commands(claude: str, options: InstallOptions) -> list[list[str]]:
    """The `claude` CLI calls that add the marketplace and install the plugin."""
    return [
        [claude, "plugin", "marketplace", "add", MARKETPLACE_REPO, "--scope", options.scope],
        [claude, "plugin", "install", plugin_id(options.channel), "--scope", options.scope],
    ]


def settings_patch(channel: str) -> dict[str, dict[str, object]]:
    """The settings entries the fallback writes, the same ones the `claude` CLI writes."""
    return {
        "extraKnownMarketplaces": {
            MARKETPLACE_NAME: {"source": {"source": "github", "repo": MARKETPLACE_REPO}},
        },
        "enabledPlugins": {plugin_id(channel): True},
    }


def _display(command: list[str]) -> str:
    return shlex.join([Path(command[0]).name, *command[1:]])


def _warn_other_channels(path: Path, current: dict[str, object], channel: str, console: Console) -> None:
    """Warn when settings already enable another Agentville channel."""
    enabled = current.get("enabledPlugins")
    if not isinstance(enabled, dict):
        return
    others = [pid for pid in PLUGIN_IDS.values() if pid != plugin_id(channel) and enabled.get(pid)]
    if others:
        console.warn(
            f"{', '.join(others)} is also enabled in {path}; install one channel at a time, "
            "because all channels load the same names."
        )


class ClaudeCodeTarget:
    name = "claude-code"
    description = "Claude Code (plugin through the claude CLI, else settings.json)"

    def install(self, options: InstallOptions, console: Console) -> int:
        cwd = options.project_dir if options.scope == "project" else None
        claude = shutil.which("claude")
        if claude:
            code = self._install_with_cli(claude, options, console, cwd)
        else:
            console.info("The claude command is not on PATH; writing Claude Code settings instead.")
            code = self._install_with_settings(options, console)
        if code != EXIT_OK:
            return code
        return self._add_steering(options, console)

    def _install_with_cli(self, claude: str, options: InstallOptions, console: Console, cwd: Path | None) -> int:
        where = f" (in {cwd})" if cwd else ""
        try:
            _warn_other_channels(settings_path(options), read_json_object(settings_path(options)), options.channel, console)
        except (FileEditError, OSError):
            pass  # The claude CLI reports a broken settings file itself; the warning is only a hint.
        for command in cli_commands(claude, options):
            console.action(f"run: {_display(command)}{where}")
            if options.dry_run:
                continue
            try:
                result = subprocess.run(
                    command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
                )
            except OSError as exc:
                console.error(f"could not run {_display(command)}: {exc}")
                return EXIT_FAILED
            output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part and part.strip())
            if output:
                console.info("  " + output.replace("\n", "\n  "))
            if result.returncode != 0:
                is_marketplace_add = command[1:4] == ["plugin", "marketplace", "add"]
                if is_marketplace_add and "already" in output.lower():
                    console.info("  The marketplace is already added; continuing.")
                    continue
                console.error(f"{_display(command)} exited with {result.returncode}")
                return EXIT_FAILED
        return EXIT_OK

    def _install_with_settings(self, options: InstallOptions, console: Console) -> int:
        path = settings_path(options)
        try:
            current = read_json_object(path)
            changed = merge_json_object(path, settings_patch(options.channel), dry_run=options.dry_run)
        except FileEditError as exc:
            console.error(str(exc))
            return EXIT_FAILED
        _warn_other_channels(path, current, options.channel, console)
        if changed:
            console.action(f"update {path}: set {', '.join(changed)}")
        else:
            console.info(f"{path} already enables {plugin_id(options.channel)}; unchanged.")
        return EXIT_OK

    def _add_steering(self, options: InstallOptions, console: Console) -> int:
        path = claude_md_path(options)
        try:
            added = append_lines(path, STEERING_LINES, dry_run=options.dry_run)
        except (FileEditError, OSError) as exc:
            console.error(str(exc))
            return EXIT_FAILED
        if added:
            console.action(f"append {len(added)} line(s) to {path}")
        else:
            console.info(f"{path} already holds the Agentville lines; unchanged.")
        return EXIT_OK


TARGET = ClaudeCodeTarget()
