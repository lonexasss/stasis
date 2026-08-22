import pytest

from stasis.profile import get_profile, load_profiles


def write(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text)
    return p


def test_parses_full_profile(tmp_path):
    path = write(tmp_path, """
[game]
cpu_affinity = "0-7"
memory_high = "8G"
memory_max = "12G"
governor = "performance"
freeze = ["firefox", "telegram"]
ignore = ["pipewire"]
trim_frozen = true
""")
    profiles = load_profiles(path)
    game = profiles["game"]
    assert game.cpu_affinity == "0-7"
    assert game.memory_high == "8G"
    assert game.memory_max == "12G"
    assert game.governor == "performance"
    assert game.freeze == ["firefox", "telegram"]
    assert game.ignore == ["pipewire"]
    assert game.trim_frozen is True


def test_ignore_defaults_present(tmp_path):
    path = write(tmp_path, "[simple]\n")
    profile = load_profiles(path)["simple"]
    assert "pipewire" in profile.ignore
    assert "stasis" in profile.ignore


def test_unknown_key_rejected(tmp_path):
    path = write(tmp_path, '[x]\nram_boost = true\n')
    with pytest.raises(SystemExit, match="unknown key 'ram_boost'"):
        load_profiles(path)


def test_bad_type_rejected(tmp_path):
    path = write(tmp_path, '[x]\nfreeze = "not-a-list"\n')
    with pytest.raises(SystemExit, match="must be a list"):
        load_profiles(path)


def test_missing_profile_is_clean_error(tmp_path):
    path = write(tmp_path, "[a]\n")
    with pytest.raises(SystemExit, match="profile 'b' not found"):
        get_profile(path, "b")


def test_missing_config_is_clean_error(tmp_path):
    with pytest.raises(SystemExit, match="config not found"):
        load_profiles(tmp_path / "nope.toml")
