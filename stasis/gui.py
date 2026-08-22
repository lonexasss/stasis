"""dark tkinter frontend: an app grid that launches things into stasis."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import __version__
from . import freeze as fz
from . import launch, power
from .desktop import list_apps
from .profile import (
    Profile,
    category_map,
    ensure_default_config,
    get_profile,
    load_profiles,
)
from .state import load_state

BG = "#0f1115"
PANEL = "#161a20"
FG = "#e6e6e6"
DIM = "#8b949e"
ACCENT = "#00ff9c"
BORDER = "#30363d"

FONT = ("Noto Sans Mono", 10)
FONT_SMALL = ("Noto Sans Mono", 9)
FONT_BIG = ("Noto Sans Mono", 11, "bold")

CONFIG_HELP = "~/.config/stasis/config.toml"


class StasisGui:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(f"stasis {__version__}")
        root.configure(bg=BG)
        self._style()

        created = ensure_default_config(CONFIG_HELP)
        self.apps = list_apps()
        self.running = False

        self._build_topbar()
        self._build_app_grid()
        self._build_freeze_panel()
        self._build_status_bar()
        self.refresh_all()
        if created:
            self.root.after(
                300,
                lambda: messagebox.showinfo(
                    "stasis",
                    "welcome!\n\nno config was found, so a default one was "
                    f"created at {CONFIG_HELP}\napps in the 'Game' category "
                    "launch with the game profile automatically.",
                ),
            )
        self._poll()

    # ---------- ui plumbing ----------

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG, font=FONT)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("Dim.TLabel", background=BG, foreground=DIM)
        style.configure("Header.TLabel", background=PANEL, foreground=DIM, font=FONT_BIG)
        style.configure(
            "Tile.TButton", background=PANEL, foreground=FG, bordercolor=BORDER,
            font=FONT, padding=(8, 10),
        )
        style.map(
            "Tile.TButton",
            background=[("active", ACCENT)],
            foreground=[("active", "#000000")],
        )
        style.configure(
            "TButton", background=PANEL, foreground=FG, bordercolor=BORDER
        )
        style.configure("TEntry", fieldbackground=PANEL, foreground=FG, insertcolor=FG)

    def _build_topbar(self):
        bar = ttk.Frame(self.root)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 0))
        ttk.Label(bar, text="search:", style="Dim.TLabel").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.search_var, width=24)
        entry.pack(side="left", padx=(6, 14))
        entry.bind("<KeyRelease>", lambda _e: self.render_grid())
        ttk.Label(bar, text="launch profile:", style="Dim.TLabel").pack(side="left")
        self.profile_var = tk.StringVar(value="default")
        self.profile_box = ttk.Combobox(
            bar, textvariable=self.profile_var, state="readonly", width=12
        )
        self.profile_box.pack(side="left", padx=(6, 0))

    def _build_app_grid(self):
        outer = ttk.Frame(self.root)
        outer.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        self.grid_canvas = tk.Canvas(
            outer, bg=BG, highlightthickness=1, highlightbackground=BORDER
        )
        scroll = ttk.Scrollbar(outer, orient="vertical", command=self.grid_canvas.yview)
        self.grid_inner = ttk.Frame(self.grid_canvas, style="Panel.TFrame")
        self.grid_inner.bind(
            "<Configure>",
            lambda e: self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all")),
        )
        self.grid_window = self.grid_canvas.create_window((0, 0), window=self.grid_inner, anchor="nw")
        self.grid_canvas.configure(yscrollcommand=scroll.set)
        self.grid_canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.grid_canvas.bind_all("<MouseWheel>", lambda e: self.grid_canvas.yview_scroll(-e.delta // 120, "units"))
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_rowconfigure(1, weight=1)

    def render_grid(self):
        for child in self.grid_inner.winfo_children():
            child.destroy()
        query = self.search_var.get().lower().strip()
        columns = max(1, self.grid_canvas.winfo_width() // 170 or 4)
        shown = 0
        for app in self.apps:
            if query and query not in app["name"].lower():
                continue
            tile = ttk.Button(
                self.grid_inner,
                text=app["name"],
                style="Tile.TButton",
                width=16,
                command=lambda a=app: self.on_launch(a),
            )
            tile.grid(row=shown // columns, column=shown % columns, padx=5, pady=5, sticky="nsew")
            shown += 1
        if shown == 0:
            ttk.Label(
                self.grid_inner,
                text="nothing found" if query else "no applications discovered",
                style="Dim.TLabel",
            ).grid(row=0, column=0, padx=12, pady=12)

    def _build_freeze_panel(self):
        panel = ttk.Frame(self.root, style="Panel.TFrame")
        panel.grid(row=1, column=1, sticky="ns", padx=(0, 8), pady=6)
        ttk.Label(panel, text="FROZEN", style="Header.TLabel").pack(anchor="w", padx=8, pady=(6, 2))
        self.frozen_list = tk.Listbox(
            panel, height=12, bg=PANEL, fg=FG, relief="flat",
            highlightthickness=1, highlightbackground=BORDER, font=FONT_SMALL, width=22,
        )
        self.frozen_list.pack(fill="both", expand=True, padx=8)

        self.pattern_entry = ttk.Entry(panel, font=FONT_SMALL)
        self.pattern_entry.pack(fill="x", padx=8, pady=(6, 2))
        row = ttk.Frame(panel, style="Panel.TFrame")
        row.pack(fill="x", padx=8, pady=(2, 8))
        ttk.Button(row, text="freeze", command=self.on_freeze).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ttk.Button(row, text="thaw all", command=self.on_thaw).pack(side="left", expand=True, fill="x", padx=(3, 0))

    def _build_status_bar(self):
        self.status = tk.StringVar(value="")
        tk.Label(
            self.root, textvariable=self.status, bg=BG, fg=DIM,
            anchor="w", font=FONT_SMALL,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 6))

    # ---------- actions ----------

    def profile_for(self, app: dict) -> str:
        bindings = category_map(CONFIG_HELP)
        for category in app["categories"]:
            if category in bindings:
                return bindings[category]
        return self.profile_var.get() or "default"

    def on_launch(self, app: dict):
        if self.running:
            return
        try:
            profile = get_profile(CONFIG_HELP, self.profile_for(app))
        except SystemExit as e:
            messagebox.showerror("stasis", str(e))
            return

        def worker(p: Profile = profile, cmd: list[str] = app["exec"]):
            self.running = True
            state: dict = {}
            try:
                fz.freeze(p.freeze, ignore=p.ignore)
                if p.governor:
                    power.set_governor(p.governor, state)
                code = launch.run_in_scope(p, cmd)
            except SystemExit as e:
                self.root.after(0, lambda: messagebox.showerror("stasis", str(e)))
            finally:
                if p.governor:
                    power.restore_governors(state)
                fz.thaw()
                self.running = False
                self.root.after(0, self.refresh_all)

        threading.Thread(target=worker, daemon=True).start()
        self.status.set(f"launched: {app['name']} (profile: {profile.name})")

    def on_freeze(self):
        raw = self.pattern_entry.get().strip()
        if not raw:
            return
        fz.freeze([p for p in raw.replace(",", " ").split() if p])
        self.pattern_entry.delete(0, "end")
        self.refresh_all()

    def on_thaw(self):
        fz.thaw()
        self.refresh_all()

    def refresh_all(self):
        try:
            names = sorted(load_profiles(CONFIG_HELP))
            self.profile_box["values"] = names
            if not self.profile_box.get():
                self.profile_box.set("default" if "default" in names else (names[0] if names else ""))
        except SystemExit:
            pass

        self.frozen_list.delete(0, "end")
        for pid in load_state().get("frozen_pids", []):
            try:
                comm = open(f"/proc/{pid}/comm").read().strip()
                self.frozen_list.insert("end", f"{pid:>7}  {comm}")
            except OSError:
                self.frozen_list.insert("end", f"{pid:>7}  (gone)")

        govs = sorted(set(power.current_governors().values()))
        extra = "   ·   running…" if self.running else ""
        self.status.set(f"governors: {', '.join(govs) or 'n/a'}{extra}")

    def _poll(self):
        if not self.running:
            self.refresh_all()
        self.root.after(2000, self._poll)


def main():
    root = tk.Tk()
    root.geometry("980x560")
    root.minsize(760, 420)
    StasisGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
