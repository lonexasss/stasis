import os

from stasis.freeze import own_tree_root, select_pids


def make_proc(tmp_path, pid, comm, cmdline="", parent=1):
    d = tmp_path / str(pid)
    d.mkdir()
    (d / "comm").write_text(comm + "\n")
    (d / "cmdline").write_bytes(cmdline.encode().replace(b" ", b"\0") + b"\0")
    (d / "stat").write_text(f"{pid} ({comm}) S {parent} 0\n")
    return d


def test_selects_matching_names(tmp_path):
    make_proc(tmp_path, 101, "firefox")
    make_proc(tmp_path, 102, "Web Content", "firefox --contentproc")
    make_proc(tmp_path, 103, "kate", "kate main.py")
    pids = select_pids(["firefox"], ignore=[], proc_dir=tmp_path)
    assert sorted(pids) == [101, 102]


def test_ignore_wins_over_match(tmp_path):
    make_proc(tmp_path, 201, "pipewire")
    pids = select_pids(["pipe"], ignore=["pipewire"], proc_dir=tmp_path)
    assert pids == []


def test_never_matches_own_ancestry(tmp_path):
    me = os.getpid()
    # fake stat chain: our real pid claims parentage inside the fake tree
    make_proc(tmp_path, me, "python", f"pytest {me}", parent=1)
    make_proc(tmp_path, 300, "python", "evil target")
    pids = select_pids(["python"], ignore=[], proc_dir=tmp_path)
    assert me not in pids
    assert 300 in pids


def test_skip_pids_respected(tmp_path):
    make_proc(tmp_path, 401, "vlc")
    pids = select_pids(["vlc"], ignore=[], proc_dir=tmp_path, skip_pids={401})
    assert pids == []
