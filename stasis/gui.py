"""dark tkinter frontend for stasis."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import __version__
from . import freeze as fz
from . import launch, power
from .profile import get_profile, load_profiles
from .state import load_state

BG = "#0f1115"
PANEL = "#161a20"
FG = "#e6e6e6"
DIM = "#8b949e"
ACCENT = "#00ff9c"
BORDER = "#30363d"

FONT = ("Noto Sans Mono", 10)
FONT_BIG = ("Noto Sans Mono", 11, "bold")


class StasisGui:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(f"stasis {__version__}")
        root.configure(bg=BG)
        self._style()

        self.running = False
        self._build_profile_panel()
        self._build_run_panel()
        self._build_freeze_panel()
        self._build_status_bar()
        self.refresh_all()
        self._poll_threads()

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG, font=FONT)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("Header.TLabel", background=BG, foreground=DIM, font=FONT_BIG)
        style.configure(
            "TButton",
            background=PANEL,
            foreground=FG,
            bordercolor=BORDER,
            focuscolor=ACCENT,
        )
        style.map(
            "Run.TButton",
            background=[("active", ACCENT), ("!disabled", PANEL)],
            foreground=[("active", "#000000")],
        )
        style.configure("TEntry", fieldbackground=PANEL, foreground=FG, insertcolor=FG)
        style.configure(
            "TListbox",
            background=PANEL,
            foreground=FG,
            highlightthickness=1,
            highlightbackground=BORDER,
        )

    def _panel(self, parent, **grid):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.grid(**grid, sticky="nsew", padx=8, pady=4)
        return frame

    def _build_profile_panel(self):
        panel = self._panel(self.root, row=0, column=0)
        ttk.Label(panel, text="PROFILES", style="Header.TLabel").pack(anchor="w", pady=(6, 2))
        self.profile_list = tk.Listbox(
            panel,
            height=6,
            bg=PANEL,
            fg=FG,
            selectbackground=ACCENT,
            selectforeground="#000000",
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            font=FONT,
        )
        self.profile_list.pack(fill="both", expand=True, pady=(0, 4))

    def _build_run_panel(self):
        panel = self._panel(self.root, row=0, column=1)
        ttk.Label(panel, text="COMMAND", style="Header.TLabel").pack(anchor="w", pady=(6, 2))
        self.command_entry = ttk.Entry(panel, font=FONT)
        self.command_entry.pack(fill="x", pady=(0, 6))
        self.command_entry.insert(0, "")
        self.dry_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(panel, text="dry run", variable=self.dry_var).pack(anchor="w")
        self.run_button = ttk.Button(
            panel, text="RUN", style="Run.TButton", command=self.on_run, width=12
        )
        self.run_button.pack(anchor="e", pady=6)

    def _build_freeze_panel(self):
        panel = self._panel(self.root, row=1, column=0, rowspan=1)
        ttk.Label(panel, text="FROZEN PROCESSES", style="Header.TLabel").pack(anchor="w", pady=(6, 2))
        self.frozen_list = tk.Listbox(
            panel,
            height=7,
            bg=PANEL,
            fg=FG,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            font=FONT,
        )
        self.frozen_list.pack(fill="both", expand=True)

        row = ttk.Frame(panel, style="Panel.TFrame")
        row.pack(fill="x", pady=6)
        self.pattern_entry = ttk.Entry(row, width=18, font=FONT)
        self.pattern_entry.pack(side="left", padx=(0, 6))
        ttk.Button(row, text="freeze", command=self.on_freeze).pack(side="left", padx=(0, 4))
        ttk.Button(row, text="thaw all", command=self.on_thaw).pack(side="left")

    def _build_status_bar(self):
        self.status = tk.StringVar(value="")
        bar = tk.Label(
            self.root,
            textvariable=self.status,
            bg=BG,
            fg=DIM,
            anchor="w",
            font=("Noto Sans Mono", 9),
        )
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 6))

    # ---------- actions ----------

    def refresh_all(self):
        try:
            profiles = load_profiles_default()
            self.profile_list.delete(0, "end")
            for name in sorted(profiles):
                self.profile_list.insert("end", name)
        except SystemExit as e:
            self.profile_list.delete(0, "end")
            self.profile_list.insert("end", "(no config)")

        self.frozen_list.delete(0, "end")
        for pid in load_state().get("frozen_pids", []):
            try:
                comm = open(f"/proc/{pid}/comm").read().strip()
                self.frozen_list.insert("end", f"{pid:>7}  {comm}")
            except OSError:
                self.frozen_list.insert("end", f"{pid:>7}  (gone)")

        govs = sorted(set(power.current_governors().values()))
        self.status.set(f"governors: {', '.join(govs) or 'n/a'}   ·   config: ~/.config/stasis/config.toml")

    def on_run(self):
        if self.running:
            return
        selection = self.profile_list.curselection()
        raw = self.command_entry.get().strip()
        if not selection:
            messagebox.showwarning("stasis", "pick a profile first")
            return
        if not raw:
            messagebox.showwarning("stasis", "enter a command to run")
            return
        name = self.profile_list.get(selection[0])
        try:
            profile = get_profile(config_path(), name)
        except SystemExit as e:
            messagebox.showerror("stasis", str(e))
            return

        command = raw.split()
        if self.dry_var.get():
            preview = " ".join(launch.build_command(profile, command))
            messagebox.showinfo("dry run", preview)
            return

        def worker():
            self.running = True
            state = {}
            try:
                fz.freeze(profile.freeze, ignore=profile.ignore)
                if profile.governor:
                    power.set_governor(profile.governor, state)
                code = launch.run_in_scope(profile, command)
            except SystemExit as e:
                self.root.after(0, lambda: messagebox.showerror("stasis", str(e)))
            except FileNotFoundError:
                self.root.after(0, lambda: messagebox.showerror("stasis", "systemd-run not found"))
            finally:
                if profile.governor:
                    power.restore_governors(state)
                fz.thaw()
                self.running = False
                self.root.after(0, self.refresh_all)
            if isinstance(locals().get("code"), int):
                self.root.after(0, lambda c=code: self.status.set(f"last exit code: {c}"))

        self.run_button.state(["disabled"])
        threading.Thread(target=worker, daemon=True).start()

    def on_freeze(self):
        raw = self.pattern_entry.get().strip()
        if not raw:
            return
        patterns = [p for p in raw.replace(",", " ").split() if p]
        pids = fz.freeze(patterns)
        self.refresh_all()
        self.pattern_entry.delete(0, "end")

    def on_thaw(self):
        fz.thaw()
        self.refresh_all()

    def _poll_threads(self):
        if not self.running:
            self.run_button.state(["!disabled"])
            self.refresh_all()
        self.root.after(1500, self._poll_threads)


def config_path():
    import os
    return os.path.expanduser("~/.config/stasis/config.toml")


def load_profiles_default():
    from .profile import load_profiles
    return load_profiles(config_path())


def main():
    root = tk.Tk()
    root.geometry("760x420")
    root.minsize(640, 380)
    StasisGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
