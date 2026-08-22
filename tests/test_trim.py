from stasis.trim import cgroup_v2_path


def test_parses_v2_unified_line(tmp_path):
    proc = tmp_path / "42"
    proc.mkdir()
    (proc / "cgroup").write_text(
        "0::/user.slice/user-1000.slice/user@1000.service/app.slice/app-firefox.scope\n"
    )
    assert cgroup_v2_path(42, proc_dir=tmp_path) == (
        "user.slice/user-1000.slice/user@1000.service/app.slice/app-firefox.scope"
    )


def test_root_cgroup_is_empty_string(tmp_path):
    proc = tmp_path / "7"
    proc.mkdir()
    (proc / "cgroup").write_text("0::/\n")
    assert cgroup_v2_path(7, proc_dir=tmp_path) == ""


def test_ignores_v1_hierarchies(tmp_path):
    proc = tmp_path / "9"
    proc.mkdir()
    (proc / "cgroup").write_text(
        "10:pids:/\n"
        "0::/system.slice/sshd.service\n"
    )
    assert cgroup_v2_path(9, proc_dir=tmp_path) == "system.slice/sshd.service"


def test_missing_proc_entry_returns_none(tmp_path):
    assert cgroup_v2_path(999999, proc_dir=tmp_path) is None
