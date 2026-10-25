"""Idempotent edits of steering and settings files: UTF-8, the file's own line endings, nothing else touched."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FileEditError(Exception):
    """A file cannot be edited safely, such as settings that are not valid JSON."""


def _read_text(path: Path) -> str:
    """Read UTF-8 text exactly as stored: newline="" keeps CRLF and LF untranslated."""
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return handle.read()
    except UnicodeDecodeError as exc:
        raise FileEditError(f"{path} is not UTF-8 text; left unchanged") from exc


def _line_separator(text: str) -> str:
    """Return the separator the text already uses: CRLF when its first line ends so, else LF."""
    first = text.find("\n")
    if first > 0 and text[first - 1] == "\r":
        return "\r\n"
    return "\n"


def _write_text(path: Path, text: str) -> None:
    """Write the text as given; callers have already chosen the line separator."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def missing_lines(path: Path, lines: list[str] | tuple[str, ...]) -> list[str]:
    """Return the lines not yet in the file, compared without surrounding whitespace."""
    if not path.exists():
        return list(lines)
    present = {line.strip() for line in _read_text(path).splitlines()}
    return [line for line in lines if line.strip() not in present]


def append_lines(path: Path, lines: list[str] | tuple[str, ...], dry_run: bool = False) -> list[str]:
    """Append each line the file lacks, creating the file if needed; return the lines added.

    An existing file keeps its content and its line endings (CRLF or LF); the new
    lines follow a blank line so a Markdown list never runs into the paragraph
    before it. A new file gets LF.
    """
    to_add = missing_lines(path, lines)
    if not to_add or dry_run:
        return to_add
    existing = _read_text(path) if path.exists() else ""
    sep = _line_separator(existing)
    if existing and not existing.endswith("\n"):
        existing += sep
    if existing.strip() and not existing.endswith(sep + sep):
        existing += sep
    _write_text(path, existing + sep.join(to_add) + sep)
    return to_add


def read_json_object(path: Path) -> dict[str, Any]:
    """Read a JSON object; a missing or empty file is an empty object."""
    if not path.exists():
        return {}
    text = _read_text(path)
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FileEditError(f"{path} is not valid JSON ({exc.msg}, line {exc.lineno}); left unchanged") from exc
    if not isinstance(data, dict):
        raise FileEditError(f"{path} does not hold a JSON object; left unchanged")
    return data


def merge_json_object(path: Path, patch: dict[str, dict[str, Any]], dry_run: bool = False) -> list[str]:
    """Set `patch[section][key] = value` in the JSON object at `path`, keeping every other key.

    Return the changed entries as `section.key`. Refuse, writing nothing, when the
    file or a section is not a JSON object.
    """
    sep = _line_separator(_read_text(path)) if path.exists() else "\n"
    data = read_json_object(path)
    changed: list[str] = []
    for section, entries in patch.items():
        current = data.get(section)
        if current is None:
            current = {}
        elif not isinstance(current, dict):
            raise FileEditError(f"{path}: '{section}' is not a JSON object; left unchanged")
        for key, value in entries.items():
            if current.get(key) != value:
                current[key] = value
                changed.append(f"{section}.{key}")
        data[section] = current
    if changed and not dry_run:
        # json.dumps escapes newlines inside strings, so every "\n" here is a line break.
        _write_text(path, json.dumps(data, indent=2, ensure_ascii=False).replace("\n", sep) + sep)
    return changed
