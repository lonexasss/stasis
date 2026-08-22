"""freedesktop.org application discovery: installed apps become launchables."""

import os
import re
import shlex
from pathlib import Path

APP_DIRS = [
    "~/.local/share/applications",
    "/usr/local/share/applications",
    "/usr/share/applications",
]

_FIELD_CODE = re.compile(r"%(?![%])[a-zA-Z]")


def strip_field_codes(exec_line: str) -> str:
    """remove %f/%u/%c style placeholders, keep literal %%."""
    return _FIELD_CODE.sub("", exec_line.replace("%%", "\0")).replace("\0", "%").strip()


def parse_desktop(path: Path) -> dict | None:
    """extract the fields we need, or None if this is not a launchable app."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    data: dict[str, str] = {}
    inside = False
    for line in lines:
        line = line.strip()
        if line.startswith("["):
            inside = line == "[Desktop Entry]"
            continue
        if not inside or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in data:
            data[key] = value.strip()

    if data.get("Type") != "Application":
        return None
    if data.get("Hidden") == "true" or data.get("NoDisplay") == "true":
        return None
    if data.get("Terminal") == "true":
        return None  # cli tools are not launcher material
    if not data.get("Name") or not data.get("Exec"):
        return None
    return data


def list_apps(dirs: list[str] | None = None) -> list[dict]:
    """return [{name, exec, categories}] sorted by name; user entries win."""
    out: dict[str, dict] = {}
    for raw_dir in dirs or APP_DIRS:
        directory = Path(os.path.expanduser(raw_dir))
        if not directory.is_dir():
            continue
        for f in sorted(directory.glob("*.desktop")):
            data = parse_desktop(f)
            if data is None or data["Name"] in out:
                continue
            try:
                command = shlex.split(strip_field_codes(data["Exec"]))
            except ValueError:
                continue
            if not command:
                continue
            out[data["Name"]] = {
                "name": data["Name"],
                "exec": command,
                "categories": [
                    c for c in data.get("Categories", "").split(";") if c.strip()
                ],
            }
    return sorted(out.values(), key=lambda a: a["name"].lower())
