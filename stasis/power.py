"""cpu governor switching with automatic restore."""

import os
from pathlib import Path



def _governor_files() -> list[Path]:
    return sorted(Path("/sys/devices/system/cpu").glob("cpu*/cpufreq/scaling_governor"))


def available_governors() -> list[str]:
    paths = _governor_files()
    if not paths:
        return []
    scaling = paths[0].parent / "scaling_available_governors"
    try:
        return scaling.read_text().split()
    except OSError:
        return []


def current_governors() -> dict[str, str]:
    out = {}
    for path in _governor_files():
        try:
            out[path.parts[-3]] = path.read_text().strip()
        except OSError:
            continue
    return out


def set_governor(name: str, state: dict) -> None:
    """switch all cpus to `name`, remembering originals inside `state`."""
    files = _governor_files()
    if not files:
        raise SystemExit("error: no cpufreq support detected on this machine")
    if "governors" not in state:
        state["governors"] = current_governors()
    for path in files:
        try:
            path.write_text(name + "\n")
        except PermissionError:
            raise SystemExit(
                "error: cannot change governor without root.\n"
                "run: sudo stasis run <profile> -- <command>"
            )


def restore_governors(state: dict) -> None:
    saved: dict = state.pop("governors", {})
    for cpu, name in saved.items():
        path = Path(f"/sys/devices/system/cpu/{cpu}/cpufreq/scaling_governor")
        try:
            path.write_text(name + "\n")
        except OSError:
            pass
