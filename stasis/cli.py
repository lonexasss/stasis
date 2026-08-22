"""stasis — a launcher that keeps the rest of the system out of the way."""

import argparse
import os
import sys

from . import __version__
from . import freeze as fz
from . import launch, power, trim
from .profile import get_profile, load_profiles
from .state import clear_state, load_state


def _print_pids(label: str, pids: list[int]) -> None:
    if pids:
        print(f"[stasis] {label}: {len(pids)} -> {pids}")
    else:
        print(f"[stasis] {label}: nothing matched")


def cmd_run(args: argparse.Namespace) -> int:
    profile = get_profile(args.config, args.profile)

    if not args.command:
        raise SystemExit("error: nothing to run. usage: stasis run <profile> -- <command>")

    print(f"[stasis] profile '{profile.name}'")
    frozen = fz.freeze(profile.freeze, ignore=profile.ignore, dry_run=args.dry_run)
    if profile.freeze:
        _print_pids("frozen" if not args.dry_run else "would freeze", frozen)

    state = load_state()
    if profile.governor and not args.dry_run:
        power.set_governor(profile.governor, state)
        print(f"[stasis] governor -> {profile.governor}")

    if profile.trim_frozen and frozen and not args.dry_run:
        trimmed = sum(trim.trim_pid(pid) for pid in frozen)
        print(f"[stasis] reclaimed memory in {trimmed}/{len(frozen)} cgroups")

    if args.dry_run:
        from .launch import build_command
        print("[stasis] would run:", " ".join(build_command(profile, args.command)))
        return 0

    try:
        code = launch.run_in_scope(profile, args.command)
    finally:
        if profile.governor:
            power.restore_governors(state)
        thawed = fz.thaw()
        _print_pids("thawed", thawed)
        clear_state()
    return code


def cmd_freeze(args: argparse.Namespace) -> None:
    pids = fz.freeze(args.patterns)
    _print_pids("frozen", pids)


def cmd_thaw(_args: argparse.Namespace) -> None:
    pids = fz.thaw()
    _print_pids("thawed", pids)


def cmd_trim(args: argparse.Namespace) -> None:
    ok = trim.trim_pid(args.pid, args.amount)
    if ok:
        print(f"[stasis] reclaimed {args.amount} from pid {args.pid}")
    else:
        raise SystemExit(
            f"error: cannot trim pid {args.pid} "
            "(no cgroup v2 or no permission; try sudo)"
        )


def cmd_status(_args: argparse.Namespace) -> None:
    state = load_state()
    frozen = state.get("frozen_pids", [])
    if frozen:
        names = []
        for pid in frozen:
            try:
                comm = open(f"/proc/{pid}/comm").read().strip()
                names.append(f"{pid} ({comm})")
            except OSError:
                names.append(str(pid))
        print("frozen:", ", ".join(names))
    else:
        print("frozen: nothing")

    govs = power.current_governors()
    if govs:
        values = sorted(set(govs.values()))
        print("governors:", ", ".join(values))
    else:
        print("governors: n/a")


def cmd_profiles(args: argparse.Namespace) -> None:
    profiles = load_profiles(args.config)
    for name, profile in profiles.items():
        bits = []
        if profile.cpu_affinity:
            bits.append(f"cpus={profile.cpu_affinity}")
        if profile.memory_high:
            bits.append(f"mem<={profile.memory_high}")
        if profile.governor:
            bits.append(f"governor={profile.governor}")
        if profile.freeze:
            bits.append(f"freeze={len(profile.freeze)}")
        print(f"{name:16s} {' '.join(bits)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stasis",
        description="a launcher that keeps the rest of the system out of the way",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", default=os.path.expanduser("~/.config/stasis/config.toml"))
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="run a command inside a resource-controlled scope")
    run.add_argument("profile")
    run.add_argument("--dry-run", action="store_true", help="show planned actions, change nothing")
    run.add_argument("command", nargs="*")

    frz = sub.add_parser("freeze", help="SIGSTOP processes by name pattern")
    frz.add_argument("patterns", nargs="+")

    sub.add_parser("thaw", help="SIGCONT everything stasis froze")

    trm = sub.add_parser("trim", help="ask the kernel to reclaim cold pages of a pid")
    trm.add_argument("pid", type=int)
    trm.add_argument("--amount", default="512M")

    sub.add_parser("status", help="show current state")
    sub.add_parser("profiles", help="list configured profiles")

    args = parser.parse_args(argv)
    handlers = {
        "run": cmd_run,
        "freeze": cmd_freeze,
        "thaw": cmd_thaw,
        "trim": cmd_trim,
        "status": cmd_status,
        "profiles": cmd_profiles,
    }
    rc = handlers[args.cmd](args)
    return 0 if rc is None else rc


if __name__ == "__main__":
    sys.exit(main())
