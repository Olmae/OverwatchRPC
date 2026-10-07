from dataclasses import asdict, replace
import logging
import queue
import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from . import __version__
from .catalog import load_catalog, resource_dir
from .model import Settings, Status, PHASES, MODES, build_payload, valid_url
from .platform import open_folder, set_autostart
from .regions import choose_region
from .runtime import Worker
from .storage import data_dir, load_settings, save_settings
from .widgets import ScrollPage

log = logging.getLogger(__name__)


class App:
    def __init__(self, root, hidden=False):
        self.root = root
        self.settings, warning = load_settings()
        self.catalog = load_catalog()
        self.status = Status(hero=self.settings.hero, map_name=self.settings.map_name, mode=self.settings.mode)
        self.events = queue.Queue()
        self.tray = None
        self.tray_ready = False
        self.quitting = False
        self.hidden_requested = hidden or self.settings.start_hidden
        self.photos = {}
        self.vars = {}
        self.rpc_label = tk.StringVar(value="Waiting for Discord…")
        self.game_label = tk.StringVar(value="Checking Overwatch…")
        self.ocr_label = tk.StringVar(value="OCR is optional and disabled by default")
        root.title(f"OWRPC Desktop · {__version__}")
        root.geometry("780x710")
        root.minsize(690, 650)
        root.configure(bg="#f2f4f7")
        root.protocol("WM_DELETE_WINDOW", self.close_window)
        self.style()
        self.build()
        self.worker = Worker(replace(self.settings), replace(self.status), self.catalog, self.events)
        self.worker.start()
        self.start_tray()
        root.after(150, self.poll)
        root.after(5000, self.check_tray)
        if warning:
            root.after(200, lambda: messagebox.showwarning("Settings recovered", warning))
        self.preview()

    def style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background="#f2f4f7", foreground="#182331")
        style.configure("TNotebook.Tab", padding=(18, 10))
        style.configure("TButton", padding=(12, 7))
        style.configure("Accent.TButton", background="#f29b3d", foreground="#152332")
        style.map("Accent.TButton", background=[("active", "#ffb25b")])
        style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"))
        style.configure("Small.TLabel", foreground="#5c6b7b", font=("Segoe UI", 9))
        style.configure("TLabelframe", padding=12)
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))

    def build(self):
        header = ttk.Frame(self.root, padding=(22, 18, 22, 10))
        header.pack(fill="x")
        ttk.Label(header, text="OWRPC", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="DESKTOP / OVERWATCH COMPANION", style="Small.TLabel").pack(side="left", padx=16, pady=10)
        self.pause_button = ttk.Button(header, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side="right")
        book = ttk.Notebook(self.root)
        book.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        pages = [ScrollPage(book) for _ in range(4)]
        presence, preferences, recognition, about = [p.content for p in pages]
        for page, name in zip(pages, ("Presence", "Settings", "Recognition", "About")):
            book.add(page, text=name)
        self.root.bind("<MouseWheel>", lambda event: pages[book.index(book.select())].wheel(event))
        self.build_presence(presence)
        self.build_preferences(preferences)
        self.build_recognition(recognition)
        self.build_about(about)
        footer = ttk.Frame(self.root, padding=(22, 0, 22, 14))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.rpc_label, style="Small.TLabel").pack(side="left")
        ttk.Label(footer, textvariable=self.game_label, style="Small.TLabel").pack(side="right")

    def var(self, key):
        if key not in self.vars:
            value = getattr(self.settings, key)
            self.vars[key] = tk.BooleanVar(value=value) if isinstance(value, bool) else tk.StringVar(value=str(value))
        return self.vars[key]

    def entry(self, parent, row, label, key, values=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        widget = (ttk.Combobox(parent, textvariable=self.var(key), values=values)
                  if values is not None else ttk.Entry(parent, textvariable=self.var(key)))
        widget.grid(row=row, column=1, sticky="ew", pady=5)
        parent.columnconfigure(1, weight=1)
        return widget

    def check(self, parent, text, key):
        ttk.Checkbutton(parent, text=text, variable=self.var(key)).pack(anchor="w", pady=4)

    def build_presence(self, parent):
        controls = ttk.Frame(parent)
        controls.pack(fill="x")
        self.phase_var = tk.StringVar(value=PHASES[self.status.phase])
        for phase, name in PHASES.items():
            ttk.Radiobutton(controls, text=name, value=name, variable=self.phase_var,
                            command=lambda p=phase: self.set_phase(p)).pack(side="left", padx=(0, 22))
        form = ttk.Frame(parent)
        form.pack(fill="x", pady=14)
        self.entry(form, 0, "Mode", "mode", MODES)
        self.entry(form, 1, "Map", "map_name", [m["name"] for m in self.catalog["maps"]])
        self.entry(form, 2, "Hero", "hero", [h["name"] for h in self.catalog["heroes"]])
        actions = ttk.Frame(parent)
        actions.pack(fill="x")
        ttk.Button(actions, text="Apply presence", style="Accent.TButton", command=self.apply_presence).pack(side="left")
        ttk.Button(actions, text="New match", command=self.new_match).pack(side="left", padx=8)
        ttk.Button(actions, text="Browse heroes", command=self.hero_gallery).pack(side="right")
        ttk.Label(parent, text="Manual selection always works. Automatic recognition requires OCR setup.",
                  style="Small.TLabel").pack(anchor="w", pady=(12, 10))
        card = ttk.LabelFrame(parent, text="LOCAL PREVIEW · DISCORD MAY DISPLAY THIS DIFFERENTLY")
        card.pack(fill="both", expand=True)
        self.map_preview = ttk.Label(card, text="Select a map")
        self.map_preview.pack(side="left", padx=(0, 16))
        info = ttk.Frame(card)
        info.pack(side="left", fill="both", expand=True)
        self.hero_preview = ttk.Label(info)
        self.hero_preview.pack(anchor="w")
        self.preview_details = ttk.Label(info, font=("Segoe UI", 12, "bold"), wraplength=330)
        self.preview_details.pack(anchor="w", pady=(8, 4))
        self.preview_state = ttk.Label(info, wraplength=330)
        self.preview_state.pack(anchor="w")
        self.preview_time = ttk.Label(info, style="Small.TLabel")
        self.preview_time.pack(anchor="w", pady=4)

    def build_preferences(self, parent):
        left, right = ttk.Frame(parent), ttk.Frame(parent)
        left.pack(side="left", fill="both", expand=True, padx=(0, 18))
        right.pack(side="left", fill="both", expand=True)
        fields = [("Discord application ID", "client_id"), ("Update interval (15–300 s)", "rpc_interval"),
                  ("Game process", "game_process"), ("Fallback large image key / URL", "large_image"),
                  ("Custom hero image key / URL", "hero_image"), ("Custom details", "details_override"),
                  ("Custom state", "state_override"), ("Button label (optional)", "button_label"),
                  ("Button URL (http/https)", "button_url")]
        for label, key in fields:
            ttk.Label(left, text=label, style="Small.TLabel").pack(anchor="w", pady=(7, 0))
            ttk.Entry(left, textvariable=self.var(key)).pack(fill="x", pady=(2, 0))
        for text, key in [("Close window to tray", "minimize_to_tray"), ("Start hidden in tray", "start_hidden"),
                          ("Launch with Windows", "autostart"), ("Publish only while Overwatch runs", "only_when_game"),
                          ("Show match timer", "show_timer"), ("Use official hero portraits", "use_hero_portrait"),
                          ("Use map artwork", "use_map_art")]:
            self.check(right, text, key)
        ttk.Label(right, text="Discord status line", style="Small.TLabel").pack(anchor="w", pady=(18, 4))
        self.display_var = tk.StringVar(value=["Application name", "State", "Details"][self.settings.display_type])
        ttk.Combobox(right, textvariable=self.display_var, state="readonly",
                     values=["Application name", "State", "Details"]).pack(fill="x")
        ttk.Label(right, text="External portraits and map artwork need Discord to fetch their HTTPS URLs.\n\n"
                  "A custom application ID changes the activity name and uploaded asset library.\n\n"
                  "Settings are stored locally. No account or API token is required.",
                  wraplength=270, style="Small.TLabel").pack(anchor="w", pady=18)
        ttk.Button(right, text="Save settings", style="Accent.TButton", command=self.save_preferences).pack(fill="x")
        ttk.Button(right, text="Open settings & logs", command=lambda: open_folder(data_dir())).pack(fill="x", pady=8)

    def build_recognition(self, parent):
        ttk.Label(parent, text="EXPERIMENTAL / LOCAL OCR", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Reads visible hero/map text only. It does not inspect game memory or determine "
                  "match phase. Set In match first. Names must remain visible long enough for two samples. "
                  "English text is supported by the bundled catalog; other languages need matching names.",
                  wraplength=680).pack(anchor="w", pady=12)
        self.check(parent, "Enable automatic hero/map recognition", "ocr_enabled")
        form = ttk.Frame(parent)
        form.pack(fill="x", pady=10)
        self.entry(form, 0, "Tesseract executable (blank = auto)", "tesseract_path")
        self.entry(form, 1, "OCR language (e.g. eng)", "ocr_language")
        self.entry(form, 2, "OCR interval (3–120 seconds)", "ocr_interval")
        regions = ttk.Frame(parent)
        regions.pack(fill="x", pady=8)
        self.region_labels = {}
        for field, label in (("hero", "Hero name"), ("map", "Map name")):
            row = ttk.Frame(regions)
            row.pack(fill="x", pady=5)
            ttk.Button(row, text=f"Select {label.lower()} region", command=lambda f=field: self.calibrate(f)).pack(side="left")
            var = tk.StringVar(value=str(getattr(self.settings, field + "_region") or "Not configured"))
            self.region_labels[field] = var
            ttk.Label(row, textvariable=var, style="Small.TLabel").pack(side="left", padx=12)
            ttk.Button(row, text="Clear", command=lambda f=field: self.clear_region(f)).pack(side="right")
        ttk.Label(parent, text="Calibration captures the primary monitor once, in memory. Use borderless/windowed "
                  "mode; select only the text, not the portrait. Recalibrate after changing resolution or UI scale. "
                  "Black fullscreen captures and names hidden by the HUD cannot be recognized.",
                  wraplength=680, style="Small.TLabel").pack(anchor="w", pady=14)
        ttk.Button(parent, text="Tesseract Windows installation", command=lambda: webbrowser.open(
            "https://github.com/UB-Mannheim/tesseract/wiki")).pack(anchor="w")
        ttk.Label(parent, textvariable=self.ocr_label, wraplength=680).pack(anchor="w", pady=18)
        ttk.Button(parent, text="Save recognition settings", style="Accent.TButton", command=self.save_preferences).pack(anchor="w")

    def build_about(self, parent):
        ttk.Label(parent, text=f"OWRPC Desktop {__version__}", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(parent, text="A modern desktop refresh of the original 2019 console client.\n"
                  "Thanks to Tominous and maxicc. Updated by Olmae · GPLv3 source.", wraplength=680).pack(anchor="w", pady=14)
        ttk.Label(parent, text=f"Catalog snapshot: {self.catalog['as_of']}\n"
                  f"{len(self.catalog['heroes'])} heroes · {len(self.catalog['maps'])} maps\n\n"
                  "Heroes and portraits: official Blizzard roster. Map data/art: OverFast API.\n"
                  "Includes legacy, Arcade, Stadium and Workshop maps; not a ranked rotation.\n\n"
                  "This beta still needs real Windows/Discord/Overwatch validation. Process detection "
                  "only tells whether Overwatch.exe is running. Manual phase and selection are the "
                  "reliable default; OCR is a calibrated convenience.\n\n"
                  "Closing the window hides it only after the tray is ready. Use Quit from the tray "
                  "or the button below to stop the companion and clear its Discord activity.",
                  wraplength=680).pack(anchor="w", pady=14)
        for label, url in [("GitHub / README", "https://github.com/Olmae/OverwatchRPC"),
                           ("Blizzard hero roster", "https://overwatch.blizzard.com/en-us/heroes/"),
                           ("Discord Rich Presence docs", "https://docs.discord.com/developers/rich-presence/overview")]:
            ttk.Button(parent, text=label, command=lambda u=url: webbrowser.open(u)).pack(anchor="w", pady=4)
        ttk.Button(parent, text="Quit OWRPC", command=self.quit).pack(anchor="w", pady=18)

    def apply_presence(self):
        for key in ("hero", "map_name", "mode"):
            value = self.var(key).get().strip()[:128]
            setattr(self.status, key, value)
            setattr(self.settings, key, value)
        self.worker.configure(self.settings, self.status)
        self.preview()
        self.persist()

    def set_phase(self, phase):
        self.status.transition(phase)
        self.phase_var.set(PHASES[phase])
        self.apply_presence()

    def new_match(self):
        self.status.transition("menus")
        self.status.hero = self.status.map_name = ""
        self.var("hero").set("")
        self.var("map_name").set("")
        self.set_phase("match")

    def toggle_pause(self):
        self.status.paused = not self.status.paused
        self.pause_button.configure(text="Resume" if self.status.paused else "Pause")
        self.worker.configure(self.settings, self.status)
        self.preview()

    def persist(self):
        try:
            save_settings(self.settings)
        except OSError as exc:
            messagebox.showerror("Cannot save settings", str(exc))

    def save_preferences(self):
        raw = asdict(self.settings)
        for key, var in self.vars.items():
            value = var.get()
            if key in ("rpc_interval", "ocr_interval"):
                try:
                    value = int(value)
                except ValueError:
                    messagebox.showerror("Invalid setting", f"{key} must be an integer")
                    return
            raw[key] = value
        raw["display_type"] = ["Application name", "State", "Details"].index(self.display_var.get())
        if not str(raw["client_id"]).isdecimal() or not 6 <= len(str(raw["client_id"])) <= 22:
            messagebox.showerror("Invalid application ID", "Use a numeric Discord application ID (6–22 digits)")
            return
        if raw["button_url"] and not valid_url(raw["button_url"]):
            messagebox.showerror("Invalid button URL", "Use an http:// or https:// URL")
            return
        proposed = Settings.from_dict(raw)
        try:
            set_autostart(proposed.autostart)
            save_settings(proposed)
        except OSError as exc:
            messagebox.showerror("Cannot save settings", str(exc))
            return
        self.settings = proposed
        for key, var in self.vars.items():
            var.set(getattr(self.settings, key))
        for key in ("hero", "map_name", "mode"):
            setattr(self.status, key, getattr(self.settings, key))
        self.worker.configure(self.settings, self.status)
        self.preview()
        self.rpc_label.set("Settings saved · Discord updates on the next interval")

    def calibrate(self, field):
        messagebox.showinfo("Select text region", "The window will hide briefly. Open the game screen with the "
                            "name visible on the PRIMARY monitor first. Drag around its text and press Enter. "
                            "This captures a frozen screenshot locally; it is not saved or uploaded.")
        def selected(region):
            setattr(self.settings, field + "_region", region)
            self.region_labels[field].set(str(region))
            self.worker.configure(self.settings, self.status)
            self.persist()
        choose_region(self.root, selected)

    def clear_region(self, field):
        setattr(self.settings, field + "_region", None)
        self.region_labels[field].set("Not configured")
        self.worker.configure(self.settings, self.status)
        self.persist()

    def photo(self, kind, key, size):
        from PIL import Image, ImageTk
        cache_key = (kind, key, size)
        if cache_key not in self.photos:
            path = resource_dir() / kind / (key + ".png")
            if not path.exists():
                return None
            with Image.open(path) as source:
                image = source.copy()
            image.thumbnail(size)
            self.photos[cache_key] = ImageTk.PhotoImage(image)
        return self.photos[cache_key]

    def preview(self):
        hero = next((x for x in self.catalog["heroes"] if x["name"] == self.status.hero), None)
        map_info = next((x for x in self.catalog["maps"] if x["name"] == self.status.map_name), None)
        payload = build_payload(self.settings, self.status, hero, map_info)
        self.preview_details.configure(text=payload["details"])
        self.preview_state.configure(text="Paused · presence hidden" if self.status.paused else payload["state"])
        self.hero_preview.configure(image=self.photo("heroes", hero["key"], (80, 80)) if hero else "",
                                    text=self.status.hero if not hero else "")
        photo = self.photo("maps", map_info["key"], (250, 145)) if map_info else None
        self.map_preview.configure(image=photo or "", text="" if photo else "No map artwork")
        self.timer_tick()

    def timer_tick(self):
        if self.status.started_at and self.settings.show_timer:
            seconds = max(0, int(time.time()) - self.status.started_at)
            self.preview_time.configure(text=f"Match time · {seconds // 60:02d}:{seconds % 60:02d}")
        else:
            self.preview_time.configure(text="No match timer")

    def hero_gallery(self):
        top = tk.Toplevel(self.root)
        top.title("Hero catalog · click to select")
        top.geometry("680x560")
        search = tk.StringVar()
        ttk.Entry(top, textvariable=search).pack(fill="x", padx=12, pady=12)
        shell = ttk.Frame(top)
        shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(shell, highlightthickness=0, bg="#f2f4f7")
        scroll = ttk.Scrollbar(shell, command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        grid = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=grid, anchor="nw")
        grid.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))

        def choose(name):
            self.var("hero").set(name)
            self.apply_presence()
            top.destroy()

        def render(*_):
            for child in grid.winfo_children():
                child.destroy()
            filtered = [h for h in self.catalog["heroes"] if search.get().casefold() in h["name"].casefold()]
            for i, hero in enumerate(filtered):
                button = ttk.Button(grid, text=f"{hero['name']}\n{hero['role'].title()}",
                                    image=self.photo("heroes", hero["key"], (70, 70)) or "", compound="top",
                                    command=lambda name=hero["name"]: choose(name))
                button.grid(row=i // 4, column=i % 4, padx=5, pady=5, ipadx=10)
        search.trace_add("write", render)
        render()

    def start_tray(self):
        if sys.platform != "win32":
            return
        try:
            import pystray
            from PIL import Image
            def post(event, value=None):
                self.events.put((event, value))
            menu = pystray.Menu(
                pystray.MenuItem("Open OWRPC", lambda *_: post("show"), default=True),
                pystray.MenuItem("In menus", lambda *_: post("phase", "menus")),
                pystray.MenuItem("In queue", lambda *_: post("phase", "queue")),
                pystray.MenuItem("In match", lambda *_: post("phase", "match")),
                pystray.MenuItem("Pause / Resume", lambda *_: post("pause")),
                pystray.MenuItem("Quit", lambda *_: post("quit")))
            with Image.open(resource_dir() / "app.png") as image:
                self.tray = pystray.Icon("OWRPC", image.copy(), "OWRPC Desktop", menu)
            def setup(icon):
                try:
                    icon.visible = True
                    post("tray_ready")
                except Exception as exc:
                    post("tray_error", str(exc))
            self.tray.run_detached(setup)
        except Exception as exc:
            log.exception("Tray initialization failed")
            self.events.put(("tray_error", str(exc)))

    def check_tray(self):
        if not self.tray_ready and self.hidden_requested:
            self.show()
            self.rpc_label.set("Tray unavailable · window kept open")

    def poll(self):
        if self.quitting:
            return
        while True:
            try:
                event, value = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "rpc":
                self.rpc_label.set(value)
            elif event == "game":
                self.game_label.set("Overwatch running" if value else "Overwatch not running")
            elif event == "ocr_status":
                self.ocr_label.set(value)
            elif event == "game_closed":
                if value != self.worker.revision:
                    continue
                self.status.transition("menus")
                self.phase_var.set(PHASES["menus"])
                self.status.hero = self.status.map_name = ""
                self.var("hero").set("")
                self.var("map_name").set("")
                self.apply_presence()
            elif event == "recognized":
                field, name, revision = value
                if revision != self.worker.revision:
                    continue
                setattr(self.status, field, name)
                self.var(field).set(name)
                setattr(self.settings, field, name)
                self.preview()
            elif event == "show":
                self.show()
            elif event == "phase":
                self.set_phase(value)
            elif event == "pause":
                self.toggle_pause()
            elif event == "quit":
                self.quit()
                return
            elif event == "tray_ready":
                self.tray_ready = True
                if self.hidden_requested:
                    self.root.withdraw()
                    self.hidden_requested = False
            elif event == "tray_error":
                self.tray_ready = False
                self.show()
                self.rpc_label.set("Tray unavailable · " + value[:80])
        self.timer_tick()
        self.root.after(200, self.poll)

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def close_window(self):
        if self.settings.minimize_to_tray and self.tray_ready:
            self.root.withdraw()
        else:
            self.quit()

    def quit(self):
        if self.quitting:
            return
        self.quitting = True
        self.worker.stop_event.set()
        if self.tray:
            self.tray.stop()
        self.persist()
        deadline = time.monotonic() + 10
        def finish():
            if self.worker.is_alive() and time.monotonic() < deadline:
                self.root.after(100, finish)
            else:
                self.root.destroy()
        finish()
