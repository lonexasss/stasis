from pathlib import Path

from stasis.desktop import list_apps, parse_desktop, strip_field_codes


def write(tmp_path: Path, name: str, body: str) -> Path:
    f = tmp_path / name
    f.write_text(body)
    return f


GOOD = """\
[Desktop Entry]
Type=Application
Name=Steam
Exec=/usr/bin/steam %U
Categories=Game;
"""


def test_strip_field_codes():
    assert strip_field_codes("steam %U") == "steam"
    assert strip_field_codes("code %f %f") == "code"
    assert strip_field_codes("echo 100%%") == "echo 100%"


def test_parse_valid(tmp_path):
    data = parse_desktop(write(tmp_path, "steam.desktop", GOOD))
    assert data is not None
    assert data["Name"] == "Steam"


def test_parse_rejects_non_apps(tmp_path):
    cases = {
        "nodisp": GOOD + "NoDisplay=true\n",
        "hidden": GOOD + "Hidden=true\n",
        "terminal": GOOD + "Terminal=true\n",
        "wrongtype": GOOD.replace("Application", "Link"),
        "noexec": GOOD.replace("Exec=/usr/bin/steam %U\n", ""),
        "noname": GOOD.replace("Name=Steam\n", ""),
    }
    for fname, body in cases.items():
        assert parse_desktop(write(tmp_path, f"{fname}.desktop", body)) is None


def test_list_apps_user_overrides_system(tmp_path):
    user = tmp_path / "user"
    system = tmp_path / "system"
    user.mkdir()
    system.mkdir()
    (system / "steam.desktop").write_text(GOOD)
    (system / "files.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Files\nExec=nautilus\n"
    )
    # same Name as system steam -> must win
    (user / "steam.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Steam\nExec=flatpak run com.valvesoftware.Steam\n"
    )

    apps = {a["name"]: a for a in list_apps(dirs=[str(user), str(system)])}
    assert set(apps) == {"Files", "Steam"}
    assert apps["Steam"]["exec"] == ["flatpak", "run", "com.valvesoftware.Steam"]
    assert apps["Files"]["categories"] == []


def test_list_apps_sorted_case_insensitive(tmp_path):
    d = tmp_path
    (d / "b.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=zeta\nExec=z\n"
    )
    (d / "a.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Alpha\nExec=a\n"
    )
    apps = list_apps(dirs=[str(d)])
    assert [a["name"] for a in apps] == ["Alpha", "zeta"]
