"""toml profiles: what stasis does around a launched application."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# things that must never be frozen or the desktop dies
DEFAULT_IGNORE = [
    "systemd",
    "dbus",
    "pipewire",
    "wireplumber",
    "pulseaudio",
    "xorg",
    "kwin",
    "gnome-shell",
    "plasmashell",
    "hyprland",
    "sway",
    "stasis",
]


@dataclass
class Profile:
    name: str = "default"
    cpu_affinity: str | None = None   # e.g. "0-7", "*" = all cores
    memory_high: str | None = None    # systemd MemoryHigh, e.g. "8G"
    memory_max: str | None = None     # hard ceiling, e.g. "12G"
    governor: str | None = None       # cpufreq governor while app runs
    freeze: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE))
    trim_frozen: bool = False         # push cold pages of frozen pids to swap


_FIELDS = {
    "cpu_affinity": str,
    "memory_high": str,
    "memory_max": str,
    "governor": str,
    "freeze": list,
    "ignore": list,
    "trim_frozen": bool,
}


def load_profiles(path: str | Path) -> dict[str, Profile]:
    """parse a config file into named profiles, validating keys and types."""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        raise SystemExit(f"error: config not found: {path}")
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"error: bad toml in {path}: {e}")

    profiles: dict[str, Profile] = {}
    for name, raw in data.items():
        if not isinstance(raw, dict):
            raise SystemExit(f"error: [{name}] must be a table")
        profile = Profile(name=name)
        for key, value in raw.items():
            if key not in _FIELDS:
                raise SystemExit(f"error: unknown key '{key}' in [{name}]")
            expected = _FIELDS[key]
            if expected is list:
                if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                    raise SystemExit(f"error: '{key}' in [{name}] must be a list of strings")
            elif type(value) is not expected:
                raise SystemExit(
                    f"error: '{key}' in [{name}] must be {expected.__name__}"
                )
            setattr(profile, key, value)
        profiles[name] = profile
    return profiles


def get_profile(path: str | Path, name: str) -> Profile:
    profiles = load_profiles(path)
    if name not in profiles:
        known = ", ".join(sorted(profiles)) or "none"
        raise SystemExit(f"error: profile '{name}' not found (have: {known})")
    return profiles[name]
