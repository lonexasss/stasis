from stasis.launch import build_command, scope_properties
from stasis.profile import Profile


def test_empty_profile_yields_bare_scope():
    profile = Profile()
    cmd = build_command(profile, ["steam"])
    assert cmd == ["systemd-run", "--user", "--scope", "--", "steam"]


def test_all_properties_in_order():
    profile = Profile(
        cpu_affinity="0-7",
        memory_high="8G",
        memory_max="12G",
    )
    cmd = build_command(profile, ["wine", "game.exe"])
    assert cmd == [
        "systemd-run", "--user", "--scope",
        "-p", "AllowedCPUs=0-7",
        "-p", "MemoryHigh=8G",
        "-p", "MemoryMax=12G",
        "--", "wine", "game.exe",
    ]


def test_star_affinity_is_omitted():
    props = scope_properties(Profile(cpu_affinity="*"))
    assert props == []


def test_command_with_flags_passes_through():
    profile = Profile()
    cmd = build_command(profile, ["mpv", "--fs", "file.mkv"])
    assert cmd[-3:] == ["mpv", "--fs", "file.mkv"]
