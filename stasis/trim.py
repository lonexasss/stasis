"""cgroup v2 memory reclaim: push cold pages of a process out to swap.

this is the honest alternative to "ram cleaners": the kernel decides
which pages are cold, we just ask it to work on this specific cgroup.
"""

import os
import subprocess
from pathlib import Path

CGROUP_ROOT = Path("/sys/fs/cgroup")


def cgroup_v2_path(pid: int, proc_dir: str | Path = "/proc") -> str | None:
    """return the relative cgroup v2 path of a pid ('' means root)."""
    try:
        lines = (Path(proc_dir) / str(pid) / "cgroup").read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        parts = line.split(":", 2)
        if len(parts) == 3 and parts[1] == "" and parts[0] == "0":
            return parts[2].lstrip("/")
    return None


def trim_pid(pid: int, amount: str = "512M") -> bool:
    """ask the kernel to reclaim `amount` from the pid's cgroup."""
    rel = cgroup_v2_path(pid)
    if rel is None:
        return False
    target = CGROUP_ROOT / rel / "memory.reclaim" if rel else CGROUP_ROOT / "memory.reclaim"
    try:
        with open(target, "w") as f:
            f.write(amount)
        return True
    except (OSError, ValueError):
        return False
