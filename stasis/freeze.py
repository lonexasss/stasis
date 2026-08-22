"""process scanning and background freezing via SIGSTOP/SIGCONT.

stasis never freezes blindly: only names explicitly listed in the
profile's `freeze`, minus everything in `ignore` and minus its own
process tree.
"""

import os
import signal
from pathlib import Path

from .state import load_state, save_state


def scan_processes(proc_dir: str | Path = "/proc") -> list[dict]:
    """return [{pid:int, comm:str, cmdline:str}] for readable processes."""
    out = []
    try:
        entries = sorted(Path(proc_dir).iterdir())
    except OSError:
        return out
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            comm = (entry / "comm").read_text().strip()
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
        except OSError:
            continue  # vanished or not ours
        out.append({"pid": int(entry.name), "comm": comm, "cmdline": cmdline})
    return out


def own_tree_root(pid: int, proc_dir: str | Path = "/proc") -> set[int]:
    """pids of our own ancestry, so we can't freeze ourselves."""
    tree = set()
    current = pid
    while current > 1:
        tree.add(current)
        try:
            stat = (Path(proc_dir) / str(current) / "stat").read_text()
            current = int(stat.rsplit(")", 1)[1].split()[1])
        except (OSError, IndexError, ValueError):
            break
    return tree


def select_pids(
    patterns: list[str],
    *,
    ignore: list[str],
    proc_dir: str | Path = "/proc",
    skip_pids: set[int] | None = None,
) -> list[int]:
    patterns_l = [p.lower() for p in patterns]
    ignore_l = [i.lower() for i in ignore]
    skip = set(skip_pids or ()) | own_tree_root(os.getpid(), proc_dir)

    picked = []
    for proc in scan_processes(proc_dir):
        if proc["pid"] in skip:
            continue
        haystack = f"{proc['comm']} {proc['cmdline']}".lower()
        if any(i in haystack for i in ignore_l):
            continue
        if any(p in haystack for p in patterns_l):
            picked.append(proc["pid"])
    return sorted(set(picked))


def freeze(
    patterns: list[str],
    *,
    ignore: list[str] | None = None,
    dry_run: bool = False,
    proc_dir: str | Path = "/proc",
) -> list[int]:
    """SIGSTOP every matching pid and remember it in state."""
    pids = select_pids(patterns, ignore=ignore or [], proc_dir=proc_dir)
    if dry_run:
        return pids
    for pid in pids:
        try:
            os.kill(pid, signal.SIGSTOP)
        except OSError:
            pass
    state = load_state()
    already = state.get("frozen_pids", [])
    state["frozen_pids"] = sorted(set(already) | set(pids))
    save_state(state)
    return pids


def thaw(*, dry_run: bool = False) -> list[int]:
    """SIGCONT everything stasis froze earlier."""
    state = load_state()
    pids = state.get("frozen_pids", [])
    if dry_run:
        return pids
    for pid in pids:
        try:
            os.kill(pid, signal.SIGCONT)
        except OSError:
            pass
    state["frozen_pids"] = []
    save_state(state)
    return pids
