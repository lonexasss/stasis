"""launching commands inside systemd user scopes with resource properties."""

import subprocess

from .profile import Profile


def scope_properties(profile: Profile) -> list[str]:
    props: list[str] = []
    if profile.cpu_affinity and profile.cpu_affinity != "*":
        props += ["-p", f"AllowedCPUs={profile.cpu_affinity}"]
    if profile.memory_high:
        props += ["-p", f"MemoryHigh={profile.memory_high}"]
    if profile.memory_max:
        props += ["-p", f"MemoryMax={profile.memory_max}"]
    return props


def build_command(profile: Profile, command: list[str]) -> list[str]:
    return ["systemd-run", "--user", "--scope", *scope_properties(profile), "--", *command]


def run_in_scope(profile: Profile, command: list[str]) -> int:
    """blocking launch; returns the exit code of the wrapped command."""
    cmd = build_command(profile, command)
    try:
        result = subprocess.run(cmd)
        return result.returncode
    except FileNotFoundError:
        raise SystemExit("error: systemd-run not found (is systemd installed?)")
