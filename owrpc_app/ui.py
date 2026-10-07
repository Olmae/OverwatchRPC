from dataclasses import asdict, replace
import logging
import queue
import sys
import time
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from . import __version__
from .i18n import LANGUAGES, resolve_language, tr
from .catalog import load_catalog, resource_dir
from .model import Settings, Status, PHASES, MODES, build_payload, valid_url, kda_is_fresh, party_is_fresh
from .platform import open_folder, set_autostart
from .regions import choose_region
from .runtime import Worker
from .storage import data_dir, load_settings, save_settings
from .widgets import ScrollPage, MotionButton, Disclosure, RoundedCard

log = logging.getLogger(__name__)


class App:
    def __init__(self, root, hidden=False):
        self.root = root
        self.settings, warning = load_settings()
        self.language = resolve_language(self.settings.language)
        self.catalog = load_catalog(data_dir() / "catalog-cache.json")
        self.status = Status(hero=self.settings.hero, map_name=self.settings.map_name, mode=self.settings.mode)
        self.events = queue.Queue()
        self.tray = None
        self.tray_ready = False
        self.quitting = False
        self.hidden_requested = hidden or self.settings.start_hidden
        self.photos = {}
        self.service_busy = set()
        self.pending_release = None
        self.service_label = tk.StringVar(value="")
        root.report_callback_exception = self.callback_error
        from PIL import Image, ImageTk
        with Image.open(resource_dir() / "app.png") as image:
            self.window_icon = ImageTk.PhotoImage(image)
        root.iconphoto(True, self.window_icon)
        self.vars = {}
        self.rpc_label = tk.StringVar(value=self.t('Waiting for Discord…'))
        self.rpc_status = "Waiting for Discord…"
        self.game_running = None
        self.ocr_status = "Waiting for recognition"
        self.game_label = tk.StringVar(value=self.t('Checking Overwatch…'))
        self.ocr_label = tk.StringVar(value=self.t('Waiting for recognition'))
        root.title(f"OWRPC Desktop · {__version__}")
        self.scale = max(1.0, float(root.tk.call("tk", "scaling")) / (96 / 72))
        width = int(min(1120 * self.scale, max(850 * self.scale, root.winfo_screenwidth() - 80 * self.scale)))
        height = int(min(710 * self.scale, max(500 * self.scale, root.winfo_screenheight() - 100 * self.scale)))
        root.geometry(f"{width}x{height}")
        root.minsize(min(int(740 * self.scale), width), min(int(650 * self.scale), height))
        root.configure(bg="#15191f")
        root.protocol("WM_DELETE_WINDOW", self.close_window)
        self.style()
        self.build()
        self.worker = Worker(replace(self.settings), replace(self.status), self.catalog, self.events)
        self.worker.start()
        self.start_tray()
        root.after(150, self.poll)
        root.after(5000, self.check_tray)
        if warning:
            root.after(200, lambda: messagebox.showwarning(self.t('Settings recovered'), warning))
        self.preview()
        root.after(1000, self.start_services)

    def t(self, key, **values):
        return tr(key, self.language, **values)

    def change_language(self, event=None):
        choices = {self.t("System language"): "auto", **{name: code for code, name in LANGUAGES.items()}}
        language = choices[self.language_var.get()]
        self.settings.language = language
        self.var("language").set(language)
        self.language = resolve_language(language)
        selected = self.book.index(self.book.select())
        for child in self.root.winfo_children():
            child.destroy()
        self.build()
        self.book.select(selected)
        self.rpc_label.set(self.t(self.rpc_status))
        self.game_label.set(self.t("Checking Overwatch…" if self.game_running is None else "Overwatch running" if self.game_running else "Overwatch not running"))
        self.ocr_label.set(self.t(self.ocr_status))
        self.worker.configure(self.settings, self.status)
        self.persist()
        self.preview()
        self.pause_button.configure(text=self.t("Resume" if self.status.paused else "Pause"))
        if self.tray:
            self.tray.update_menu()

    def style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background="#20252d", foreground="#f4f6f8")
        style.configure("Page.TFrame", background="#15191f")
        style.configure("Header.TFrame", background="#15191f")
        style.configure("Card.TFrame", borderwidth=0, relief="flat", background="#20252d")
        style.configure("Header.TLabel", background="#15191f", foreground="#98a2ae")
        style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"), background="#15191f", foreground="#f4f6f8")
        style.configure("Small.TLabel", font=("Segoe UI", 9), foreground="#98a2ae")
        style.configure("Caption.TLabel", font=("Segoe UI", 9, "bold"), foreground="#98a2ae")
        style.configure("Status.TLabel", background="#15191f", foreground="#71d898", font=("Segoe UI", 10))
        style.layout("TNotebook.Tab", [])
        style.configure("TNotebook", background="#15191f", borderwidth=0, bordercolor="#15191f", lightcolor="#15191f", darkcolor="#15191f")
        style.configure("TNotebook.Tab", padding=(18, 10), background="#15191f", foreground="#98a2ae", borderwidth=0, bordercolor="#15191f", lightcolor="#15191f", darkcolor="#15191f")
        style.map("TNotebook.Tab", background=[("selected", "#20252d"), ("active", "#2a323e")],
                  foreground=[("selected", "#f59c20"), ("active", "#ffffff")])
        style.configure("TEntry", fieldbackground="#151b23", foreground="#f4f6f8", insertcolor="#f59c20", bordercolor="#343b44", lightcolor="#343b44", darkcolor="#343b44", padding=7)
        style.configure("TCombobox", fieldbackground="#151b23", background="#2a323e", foreground="#f4f6f8", arrowcolor="#98a2ae", bordercolor="#343b44", lightcolor="#343b44", darkcolor="#343b44", padding=7)
        style.map("TCombobox", fieldbackground=[("readonly", "#151b23")], foreground=[("readonly", "#f4f6f8")])
        style.configure("TCheckbutton", background="#20252d", foreground="#f4f6f8", indicatorbackground="#151b23", indicatorforeground="#f59c20")
        style.map("TCheckbutton", background=[("active", "#20252d")], indicatorbackground=[("selected", "#f59c20")])
        style.configure("TRadiobutton", background="#20252d", foreground="#f4f6f8")
        style.map("TRadiobutton", background=[("active", "#20252d")])
        style.configure("TLabelframe", background="#20252d", bordercolor="#343b44", lightcolor="#343b44", darkcolor="#343b44", padding=12)
        style.configure("TLabelframe.Label", foreground="#f4f6f8", font=("Segoe UI", 11, "bold"))
        style.configure("Vertical.TScrollbar", background="#343b44", troughcolor="#15191f", arrowcolor="#98a2ae", bordercolor="#20252d")
        self.root.option_add("*TCombobox*Listbox.background", "#20252d")
        self.root.option_add("*TCombobox*Listbox.foreground", "#f4f6f8")
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#a66a17")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    def build(self):
        header = ttk.Frame(self.root, padding=(24, 16, 24, 16), style="Header.TFrame")
        header.pack(fill="x")
        from PIL import Image, ImageTk
        with Image.open(resource_dir() / "app.png") as image:
            self.header_icon = ImageTk.PhotoImage(image.resize((int(38 * self.scale), int(38 * self.scale)), Image.Resampling.LANCZOS))
        ttk.Label(header, image=self.header_icon, style="Header.TLabel").pack(side="left", padx=(0, 12))
        ttk.Label(header, text="OWRPC", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text=self.t("Overwatch companion"), style="Header.TLabel").pack(side="left", padx=16)
        self.pause_button = MotionButton(header, text=self.t("Resume" if self.status.paused else "Pause"), command=self.toggle_pause)
        self.pause_button.pack(side="right")
        navigation = ttk.Frame(self.root, padding=(18, 0, 18, 10), style="Header.TFrame")
        navigation.pack(fill="x")
        self.nav_buttons = []
        for index, key in enumerate(("Activity", "Additional")):
            button = MotionButton(navigation, text=self.t(key), command=lambda i=index: self.book.select(i))
            button.pack(side="left", padx=(0, 8))
            self.nav_buttons.append(button)
        self.book = book = ttk.Notebook(self.root)
        book.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        pages = [ScrollPage(book) for _ in range(2)]
        for page, title in zip(pages, ("Activity", "Additional")):
            book.add(page, text=self.t(title))
        self.root.bind("<MouseWheel>", lambda event: pages[book.index(book.select())].wheel(event))
        def navigation_changed(event=None):
            for index, button in enumerate(self.nav_buttons):
                selected = index == book.index(book.select())
                button.stop_animation()
                button.base = "#68451c" if selected else "#15191f"
                button.hover = "#865b26" if selected else "#2a323e"
                button.configure(background=button.base, foreground="#ffc46d" if selected else "#98a2ae")
        book.bind("<<NotebookTabChanged>>", navigation_changed)
        navigation_changed()
        self.build_presence(pages[0].content)
        essentials = RoundedCard(pages[1].content, padding=20)
        essentials.pack(fill="x", pady=(0, 16))
        ttk.Label(essentials, text=self.t("Recognition settings"), font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 8))
        self.build_recognition(essentials)
        MotionButton(essentials, text=self.t("Save settings"), style="Accent.TButton", command=self.save_preferences).pack(anchor="w", pady=(10, 0))
        self.build_preferences(pages[1].content)
        self.build_advanced(pages[1].content)
        about = Disclosure(pages[1].content, self.t("About"))
        about.pack(fill="x", pady=(18, 8))
        self.build_about(about.content)
        footer = ttk.Frame(self.root, padding=(24, 0, 24, 14), style="Header.TFrame")
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.game_label, style="Header.TLabel").pack(side="left")
        ttk.Label(footer, textvariable=self.rpc_label, style="Header.TLabel").pack(side="right")

    def hint(self, parent, key):
        label = ttk.Label(parent, text=self.t(key), wraplength=int(620 * self.scale), style="Small.TLabel")
        label.pack(anchor="w", fill="x", pady=(8, 12))
        def wrap_hint(event):
            width = max(int(200 * self.scale), event.width - int(40 * self.scale))
            if int(label.cget("wraplength")) != width:
                label.configure(wraplength=width)
        parent.bind("<Configure>", wrap_hint, add="+")

    def var(self, key):
        if key not in self.vars:
            value = getattr(self.settings, key)
            self.vars[key] = tk.BooleanVar(value=value) if isinstance(value, bool) else tk.StringVar(value=str(value))
        return self.vars[key]

    def entry(self, parent, row, label, key, values=None):
        ttk.Label(parent, text=self.t(label), wraplength=int(235 * self.scale), justify="left").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        widget = (ttk.Combobox(parent, textvariable=self.var(key), values=values)
                  if values is not None else ttk.Entry(parent, textvariable=self.var(key)))
        if key in ("ocr_interval", "rpc_interval"):
            widget.destroy()
            widget = ttk.Spinbox(parent, textvariable=self.var(key), from_=3 if key == "ocr_interval" else 15,
                                 to=120 if key == "ocr_interval" else 300)
        widget.grid(row=row, column=1, sticky="ew", pady=5)
        parent.columnconfigure(1, weight=1)
        return widget

    def check(self, parent, text, key):
        ttk.Checkbutton(parent, text=self.t(text), variable=self.var(key)).pack(anchor="w", pady=4)

    def build_presence(self, parent):
        layout = ttk.Frame(parent, style="Page.TFrame")
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=3)
        layout.columnconfigure(1, weight=2)
        self.dashboard_left = left = RoundedCard(layout, padding=(20, 18))
        self.dashboard_right = card = RoundedCard(layout, padding=(20, 18))
        self.dashboard_layout = layout
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        def reflow(event):
            narrow = event.width < int(850 * self.scale)
            if getattr(self, "dashboard_narrow", None) == narrow:
                return
            self.dashboard_narrow = narrow
            left.grid_configure(row=0, column=0, columnspan=2 if narrow else 1, padx=0 if narrow else (0, 10))
            card.grid_configure(row=1 if narrow else 0, column=0 if narrow else 1, columnspan=2 if narrow else 1, padx=0 if narrow else (10, 0), pady=(16, 0) if narrow else 0)
        layout.bind("<Configure>", reflow)
        ttk.Label(left, text=self.t("Current activity"), style="Caption.TLabel").pack(anchor="w")
        self.scene_label = ttk.Label(left, font=("Segoe UI", 22, "bold"))
        self.scene_label.pack(anchor="w", pady=(8, 4))
        self.mode_label = ttk.Label(left, style="Small.TLabel")
        self.mode_label.pack(anchor="w", pady=(0, 18))
        info = ttk.Frame(left)
        info.pack(fill="x")
        self.activity_values = {}
        for index, key in enumerate(("Hero", "Map", "Party", "Match timer")):
            cell = ttk.Frame(info, padding=(0, 8, 10, 12))
            cell.grid(row=index // 2, column=index % 2, sticky="nsew")
            info.columnconfigure(index % 2, weight=1)
            ttk.Label(cell, text=self.t(key), style="Caption.TLabel").pack(anchor="w")
            value = ttk.Label(cell, font=("Segoe UI", 12, "bold"), wraplength=int(220 * self.scale))
            value.pack(anchor="w", pady=(5, 0))
            self.activity_values[key] = value
        self.kda_label = ttk.Label(left, style="Small.TLabel", wraplength=int(460 * self.scale))
        self.kda_label.pack(anchor="w", pady=(8, 14))
        ttk.Separator(left).pack(fill="x", pady=(0, 16))
        recognition_row = ttk.Frame(left)
        recognition_row.pack(fill="x")
        ttk.Checkbutton(recognition_row, text=self.t("Automatic recognition"), variable=self.var("ocr_enabled"), command=self.toggle_recognition).pack(side="left")
        self.recognition_detail = ttk.Label(left, textvariable=self.ocr_label, style="Small.TLabel", wraplength=int(440 * self.scale))
        self.recognition_detail.pack(anchor="w", pady=(8, 6))
        self.hint(left, "Recognition reads the visible game. Open Tab to refresh the scoreboard.")
        self.manual_open = False
        self.manual_toggle = MotionButton(left, text=self.t("Manual correction") + "  ▸", command=self.toggle_manual)
        self.manual_toggle.pack(fill="x", pady=(10, 0))
        self.manual_panel = form = ttk.Frame(left, padding=(0, 14, 0, 0))
        self.phase_var = tk.StringVar(value=self.status.phase)
        phases = ttk.Frame(form)
        phases.pack(fill="x", pady=(0, 14))
        self.phase_buttons = {}
        for phase, name in PHASES.items():
            button = MotionButton(phases, text=self.t(name), command=lambda p=phase: self.set_phase(p))
            button.pack(side="left", padx=(0, 3))
            self.phase_buttons[phase] = button
        self.mode_var = tk.StringVar(value=self.t(self.var("mode").get()))
        ttk.Label(form, text=self.t("Mode")).pack(anchor="w", pady=(0, 5))
        mode = ttk.Combobox(form, textvariable=self.mode_var, values=[self.t(x) for x in MODES], state="readonly")
        mode.pack(fill="x", pady=(0, 14))
        mode.bind("<<ComboboxSelected>>", lambda _: self.var("mode").set(dict(zip([self.t(x) for x in MODES], MODES))[self.mode_var.get()]))
        for label, key, catalog in (("Map", "map_name", "maps"), ("Hero", "hero", "heroes")):
            ttk.Label(form, text=self.t(label)).pack(anchor="w", pady=(0, 5))
            row = ttk.Frame(form)
            row.pack(fill="x", pady=(0, 14))
            ttk.Entry(row, textvariable=self.var(key)).pack(side="left", fill="x", expand=True)
            MotionButton(row, text=self.t("Choose"), command=lambda kind=catalog, field=key: self.catalog_picker(kind, field)).pack(side="right", padx=(6, 0))
        MotionButton(form, text=self.t("Apply activity"), style="Accent.TButton", command=self.apply_presence).pack(fill="x", pady=(6, 8))
        MotionButton(form, text=self.t("New match"), command=self.new_match).pack(fill="x")
        self.hint(form, "New match clears hero and map and restarts timer.")
        ttk.Label(card, text=self.t("Discord preview"), style="Caption.TLabel").pack(anchor="w")
        self.preview_source = ttk.Label(card, style="Small.TLabel")
        self.preview_source.pack(anchor="w", pady=(6, 18))
        artwork = tk.Frame(card, background="#20252d", width=int(150 * self.scale), height=int(150 * self.scale))
        artwork.pack(anchor="w", pady=(0, 18))
        artwork.pack_propagate(False)
        self.map_preview = tk.Label(artwork, background="#20252d", borderwidth=0)
        self.map_preview.place(x=0, y=0)
        self.hero_preview = tk.Label(artwork, background="#20252d", borderwidth=0)
        self.hero_preview.place(relx=1, rely=1, anchor="se")
        ttk.Label(card, text="OVERWATCH", font=("Segoe UI", 11, "bold"), foreground="#f59c20").pack(anchor="w", pady=(0, 8))
        self.preview_details = ttk.Label(card, font=("Segoe UI", 14, "bold"), wraplength=int(340 * self.scale))
        self.preview_details.pack(anchor="w", pady=(0, 8))
        self.preview_state = ttk.Label(card, wraplength=int(340 * self.scale))
        self.preview_state.pack(anchor="w")
        self.preview_time = ttk.Label(card, style="Small.TLabel")
        self.preview_time.pack(anchor="w", pady=(10, 14))
        self.preview_link = MotionButton(card, text="GitHub", command=self.open_preview_link)
        self.preview_link.pack(fill="x", pady=(0, 16))
        self.preview_notice = ttk.Label(card, style="Small.TLabel", wraplength=int(340 * self.scale))
        self.preview_notice.pack(anchor="w", pady=(0, 16))
        ttk.Separator(card).pack(fill="x", pady=(0, 16))
        ttk.Label(card, text=self.t("Preview examples"), style="Caption.TLabel").pack(anchor="w", pady=(0, 10))
        examples = ttk.Frame(card)
        examples.pack(fill="x")
        self.example_phase = None
        self.example_buttons = {}
        for phase, key in ((None, "Live"), ("menus", PHASES["menus"]), ("queue", PHASES["queue"]), ("match", PHASES["match"])):
            button = MotionButton(examples, text=self.t(key), command=lambda p=phase: self.show_example(p))
            button.pack(side="left", padx=(0, 3))
            self.example_buttons[phase] = button
        self.hint(card, "Examples only change the preview. Your Discord activity stays live.")
        self.update_phase_buttons()

    def toggle_manual(self):
        self.manual_open = not self.manual_open
        if self.manual_open:
            self.manual_panel.pack(fill="x")
        else:
            self.manual_panel.pack_forget()
        self.manual_toggle.configure(text=self.t("Manual correction") + ("  ▾" if self.manual_open else "  ▸"))

    def toggle_recognition(self):
        self.settings.ocr_enabled = self.var("ocr_enabled").get()
        self.worker.configure(self.settings, self.status)
        self.persist()
        self.preview()

    def show_example(self, phase):
        self.example_phase = phase
        self.preview()

    def open_preview_link(self):
        buttons = self.preview_payload.get("buttons", [])
        if buttons and valid_url(buttons[0]["url"]):
            webbrowser.open(buttons[0]["url"])

    def update_phase_buttons(self):
        for phase, button in self.phase_buttons.items():
            selected = phase == self.status.phase
            button.stop_animation()
            button.base = "#68451c" if selected else "#2a323e"
            button.hover = "#865b26" if selected else "#3a4554"
            button.configure(background=button.base, foreground="#ffc46d" if selected else "#f4f6f8")

    def catalog_picker(self, kind, field):
        top = tk.Toplevel(self.root)
        top.title(self.t("Choose hero" if kind == "heroes" else "Map"))
        top.configure(background="#20252d")
        top.geometry(f"{int(420 * self.scale)}x{int(470 * self.scale)}")
        top.transient(self.root)
        query = tk.StringVar()
        search = ttk.Entry(top, textvariable=query)
        search.pack(fill="x", padx=14, pady=14)
        rows = tk.Listbox(top, background="#151b23", foreground="#f4f6f8", selectbackground="#68451c",
                          selectforeground="#ffc46d", borderwidth=0, highlightthickness=0,
                          font=("Segoe UI", 11), activestyle="none")
        rows.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        names = {x.get("localized_names", {}).get(self.language, x["name"]): x["name"] for x in self.catalog[kind]}
        def render(*_):
            rows.delete(0, "end")
            for name in names:
                if query.get().casefold() in name.casefold() or query.get().casefold() in names[name].casefold():
                    rows.insert("end", name)
            if rows.size():
                rows.selection_set(0)
        def choose(event=None):
            if rows.curselection():
                self.var(field).set(names[rows.get(rows.curselection()[0])])
                self.apply_presence()
                top.destroy()
        query.trace_add("write", render)
        rows.bind("<Double-Button-1>", choose)
        rows.bind("<Return>", choose)
        search.bind("<Return>", choose)
        top.bind("<Escape>", lambda _: top.destroy())
        MotionButton(top, text=self.t("Apply activity"), style="Accent.TButton", command=choose).pack(fill="x", padx=14, pady=(0, 14))
        render()
        search.focus_set()

    def build_preferences(self, parent):
        section = RoundedCard(parent, padding=20)
        section.pack(fill="x", pady=(0, 16))
        parent = section
        ttk.Label(parent, text=self.t("General settings"), font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(parent, text=self.t("Language")).pack(anchor="w", pady=(14, 4))
        self.language_var = tk.StringVar(value=LANGUAGES.get(self.settings.language, self.t("System language")))
        language = ttk.Combobox(parent, textvariable=self.language_var,
                                values=[self.t("System language"), *LANGUAGES.values()], state="readonly")
        language.pack(fill="x")
        language.bind("<<ComboboxSelected>>", self.change_language)
        self.hint(parent, "Language changes immediately. Match selections and timer are kept.")
        for label, key in (("Close window to tray", "minimize_to_tray"), ("Start hidden in tray", "start_hidden"),
                           ("Launch with Windows", "autostart"), ("Publish only while Overwatch runs", "only_when_game"),
                           ("Show match timer", "show_timer")):
            self.check(parent, self.t(label), key)
        MotionButton(parent, text=self.t("Save settings"), command=self.save_preferences).pack(anchor="w", pady=16)
        self.check(parent, "Check GitHub releases on startup", "check_updates")
        self.check(parent, "Refresh hero and map catalog daily", "auto_catalog")
        ttk.Label(parent, textvariable=self.service_label, wraplength=int(590 * self.scale)).pack(anchor="w", pady=8)
        MotionButton(parent, text=self.t("Check for updates"), command=lambda: self.run_service("release", True)).pack(anchor="w", pady=4)
        MotionButton(parent, text=self.t("Refresh catalog"), command=lambda: self.run_service("catalog", True)).pack(anchor="w", pady=4)
        MotionButton(parent, text=self.t("Open settings & logs"), command=lambda: open_folder(data_dir())).pack(anchor="w")

    def build_advanced(self, parent):
        self.hint(parent, "Defaults work for most players. Change these only when needed.")
        connection_section = Disclosure(parent, self.t("Discord connection"), opened=False)
        connection_section.pack(fill="x", pady=8)
        connection = connection_section.content
        self.entry(connection, 0, self.t("Discord application ID"), "client_id")
        self.entry(connection, 1, self.t("Update interval (15–300 seconds)"), "rpc_interval")
        self.entry(connection, 2, self.t("Game process"), "game_process")
        self.entry(connection, 4, "OCR interval (3–120 seconds)", "ocr_interval")
        ttk.Label(connection, text=self.t("Keep the default ID unless you own a Discord application. No account token is needed."),
                  wraplength=int(590 * self.scale), style="Small.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", pady=8)
        appearance_section = Disclosure(parent, self.t("Activity appearance"), opened=False)
        appearance_section.pack(fill="x", pady=8)
        appearance = appearance_section.content
        self.check(appearance, self.t("Use official hero portraits"), "use_hero_portrait")
        self.check(appearance, self.t("Use map artwork"), "use_map_art")
        form = ttk.Frame(appearance)
        form.pack(fill="x", pady=6)
        labels = ("Application name", "State", "Details")
        if not hasattr(self, "display_value"):
            self.display_value = self.settings.display_type
        self.display_var = tk.StringVar(value=self.t(labels[self.display_value]))
        ttk.Label(form, text=self.t("Discord status line")).grid(row=0, column=0, sticky="w")
        display = ttk.Combobox(form, textvariable=self.display_var, values=[self.t(x) for x in labels], state="readonly")
        display.grid(row=0, column=1, sticky="ew")
        display.bind("<<ComboboxSelected>>", lambda _: setattr(self, "display_value", [self.t(x) for x in labels].index(self.display_var.get())))
        for row, (label, key) in enumerate((("Fallback image key / HTTPS URL", "large_image"),
                                          ("Custom hero image key / HTTPS URL", "hero_image"),
                                          ("Custom details (optional)", "details_override"),
                                          ("Custom state (optional)", "state_override"),
                                          ("Button label (optional)", "button_label"),
                                          ("Button URL (http/https)", "button_url")), 1):
            self.entry(form, row, self.t(label), key)
        self.entry(form, 9, "Menu logo HTTPS URL", "menu_image")
        self.hint(appearance, "Leave custom text blank to show mode, map and hero automatically. HTTPS artwork is fetched by Discord.")
        MotionButton(parent, text=self.t("Save settings"), command=self.save_preferences).pack(anchor="w", pady=12)

    def build_recognition(self, parent):
        self.hint(parent, "Automatic recognition uses Windows OCR on the foreground game window. Team colors are ignored. Enter your nickname for E/A/D.")
        self.check(parent, "Enable automatic scene/hero/map recognition", "ocr_enabled")
        form = ttk.Frame(parent)
        form.pack(fill="x", pady=10)
        self.entry(form, 0, "Game nickname (for your E/A/D row)", "player_name")
        ttk.Label(form, text=self.t("Recognition language")).grid(row=1, column=0, sticky="w", pady=5)
        self.ocr_language_choice = tk.StringVar(value="Русский" if self.settings.ocr_language == "rus" else "English")
        ttk.Combobox(form, textvariable=self.ocr_language_choice,
                     values=("English", "Русский"), state="readonly").grid(row=1, column=1, sticky="ew", pady=5)
        self.region_labels = {}
        self.check(parent, "Show E/A/D from the scoreboard (experimental)", "kda_enabled")
        self.hint(parent, "E/A/D is read from your nickname row while Tab is visible. Old readings are omitted from Discord. No region calibration is needed.")
        ttk.Label(parent, textvariable=self.ocr_label, wraplength=int(590 * self.scale)).pack(anchor="w", pady=10)

    def build_about(self, parent):
        ttk.Label(parent, text=f"OWRPC Desktop {__version__}", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        self.hint(parent, 'Thank you Tominous and maxicc for the original OWRPC code.')
        self.hint(parent, "Unofficial fan companion. No game memory access, account login or screenshot uploads. Code: GPLv3.")
        ttk.Label(parent, text=self.t("{heroes} heroes · {maps} maps · catalog as of {date}",
                  heroes=len(self.catalog["heroes"]), maps=len(self.catalog["maps"]), date=self.catalog["as_of"]),
                  wraplength=int(620 * self.scale)).pack(anchor="w", pady=12)
        MotionButton(parent, text=self.t("GitHub & help"), command=lambda: webbrowser.open(
            "https://github.com/Olmae/OverwatchRPC")).pack(anchor="w", pady=8)
        MotionButton(parent, text=self.t("Quit OWRPC"), command=self.quit).pack(anchor="w", pady=18)

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
        self.phase_var.set(phase)
        self.update_phase_buttons()
        self.apply_presence()

    def new_match(self):
        self.status.transition("menus")
        self.status.hero = self.status.map_name = ""
        self.var("hero").set("")
        self.var("map_name").set("")
        self.set_phase("match")

    def toggle_pause(self):
        self.status.paused = not self.status.paused
        if self.tray:
            self.tray.update_menu()
        self.pause_button.configure(text=self.t("Resume" if self.status.paused else "Pause"))
        self.worker.configure(self.settings, self.status)
        self.preview()

    def persist(self):
        try:
            save_settings(self.settings)
        except OSError as exc:
            messagebox.showerror(self.t('Cannot save settings'), str(exc))

    def save_preferences(self):
        raw = asdict(self.settings)
        for key, var in self.vars.items():
            value = var.get()
            if key in ("rpc_interval", "ocr_interval"):
                try:
                    value = int(value)
                except ValueError:
                    messagebox.showerror(self.t('Invalid setting'), self.t("Enter a whole number for {field}.", field=self.t({"rpc_interval": "Update interval (15–300 seconds)", "ocr_interval": "OCR interval (3–120 seconds)"}[key])))
                    return
            raw[key] = value
        raw["ocr_language"] = "rus" if self.ocr_language_choice.get() == "Русский" else "eng"
        raw["display_type"] = self.display_value
        if not str(raw["client_id"]).isdecimal() or not 6 <= len(str(raw["client_id"])) <= 22:
            messagebox.showerror(self.t("Invalid setting"), self.t("Use a numeric Discord application ID (6–22 digits)."))
            return
        if raw["button_url"] and not valid_url(raw["button_url"]):
            messagebox.showerror(self.t("Invalid setting"), self.t("Button URL must be an http or https address."))
            return
        proposed = Settings.from_dict(raw)
        try:
            set_autostart(proposed.autostart)
            save_settings(proposed)
        except OSError as exc:
            messagebox.showerror(self.t('Cannot save settings'), str(exc))
            return
        self.settings = proposed
        for key, var in self.vars.items():
            var.set(getattr(self.settings, key))
        for key in ("hero", "map_name", "mode"):
            setattr(self.status, key, getattr(self.settings, key))
        self.worker.configure(self.settings, self.status)
        self.preview()
        self.service_label.set(self.t("Settings saved"))

    def calibrate(self, field):
        messagebox.showinfo(self.t("Select text region"), self.t("Open the game on the primary monitor. Drag around one visible name, then press Enter. Escape cancels. The screenshot stays local."))
        def selected(region):
            setattr(self.settings, field + "_region", region)
            self.region_labels[field].set(str(region))
            self.worker.configure(self.settings, self.status)
            self.persist()
        choose_region(self.root, selected, self.language)

    def clear_region(self, field):
        setattr(self.settings, field + "_region", None)
        self.region_labels[field].set(self.t("Not configured"))
        self.worker.configure(self.settings, self.status)
        self.persist()

    def photo(self, kind, key, size, crop=False):
        from PIL import Image, ImageTk, ImageOps
        cache_key = (kind, key, size, crop)
        if cache_key not in self.photos:
            path = resource_dir() / kind / (key + ".png")
            if not path.exists():
                return None
            with Image.open(path) as source:
                image = source.copy()
            image = ImageOps.fit(image, size, Image.Resampling.LANCZOS) if crop else ImageOps.contain(image, size, Image.Resampling.LANCZOS)
            self.photos[cache_key] = ImageTk.PhotoImage(image)
        return self.photos[cache_key]

    def preview(self):
        current = self.status
        phase = self.example_phase
        for example, button in self.example_buttons.items():
            selected = example == phase
            button.stop_animation()
            button.base = "#68451c" if selected else "#2a323e"
            button.hover = "#865b26" if selected else "#3a4554"
            button.configure(background=button.base, foreground="#ffc46d" if selected else "#f4f6f8")
        shown = replace(current, phase=phase, hero="Ana", map_name="King's Row", mode="Quick Play", started_at=time.time() - 127, kda=None, party_size=None) if phase else current
        hero = next((x for x in self.catalog["heroes"] if x["name"] == shown.hero), None)
        map_info = next((x for x in self.catalog["maps"] if x["name"] == shown.map_name), None)
        payload = self.preview_payload = build_payload(self.settings, shown, hero, map_info)
        self.preview_source.configure(text=self.t("Example — {scene}", scene=self.t(PHASES[phase])) if phase else self.t("Live activity"))
        self.preview_details.configure(text=payload["details"])
        self.preview_state.configure(text=self.t("Presence paused") if current.paused and not phase else payload["state"])
        large = self.photo("maps", map_info["key"], (int(150 * self.scale), int(150 * self.scale)), crop=True) if shown.phase == "match" and self.settings.use_map_art and map_info else self.photo("", "overwatch-logo", (int(150 * self.scale), int(150 * self.scale)))
        large = large or self.photo("", "overwatch-logo", (int(150 * self.scale), int(150 * self.scale)))
        self.map_preview.configure(image=large or "", text="")
        small = None
        if shown.phase == "menus":
            small = self.photo("", "owrpc-logo", (int(44 * self.scale), int(44 * self.scale)))
        elif shown.phase == "match" and self.settings.use_hero_portrait and hero:
            small = self.photo("heroes", hero["key"], (int(44 * self.scale), int(44 * self.scale)))
        self.hero_preview.configure(image=small or "", text="")
        if small:
            self.hero_preview.place(relx=1, rely=1, anchor="se")
        else:
            self.hero_preview.place_forget()
        buttons = payload.get("buttons", [])
        if buttons:
            self.preview_link.configure(text=buttons[0]["label"])
            self.preview_link.pack(fill="x", before=self.preview_notice, pady=(0, 16))
        else:
            self.preview_link.pack_forget()
        custom_art = self.settings.large_image != Settings().large_image or bool(self.settings.hero_image and shown.phase == "match") or bool(self.settings.menu_image and shown.phase == "menus")
        note = "Custom artwork is sent to Discord; the preview uses local artwork." if custom_art else "This is a local preview. Discord controls the final appearance."
        if shown.phase == "menus" and not self.settings.menu_image:
            note = "The menu logo is ready locally. Add its public HTTPS URL in Additional to show it in Discord."
        self.preview_notice.configure(text=self.t(note))
        self.scene_label.configure(text=self.t(PHASES[current.phase]))
        self.mode_label.configure(text=self.t(current.mode) if current.phase != "menus" else self.t("Your activity updates automatically") if self.settings.ocr_enabled else self.t("Manual activity"))
        current_hero = next((x for x in self.catalog["heroes"] if x["name"] == current.hero), {})
        current_map = next((x for x in self.catalog["maps"] if x["name"] == current.map_name), {})
        self.activity_values["Hero"].configure(text=current_hero.get("localized_names", {}).get(self.language, current.hero) if current.phase == "match" and current.hero else "—")
        self.activity_values["Map"].configure(text=current_map.get("localized_names", {}).get(self.language, current.map_name) if current.phase == "match" and current.map_name else "—")
        self.activity_values["Party"].configure(text=self.t("Solo") if party_is_fresh(self.settings, current) and current.party_size == 1 else str(current.party_size) if party_is_fresh(self.settings, current) else "—")
        self.timer_tick()

    @staticmethod
    def set_text(widget, text):
        if str(widget.cget("text")) != str(text):
            widget.configure(text=text)

    def timer_tick(self):
        tick = (int(time.time()), self.status.phase, self.status.started_at,
                self.status.kda, self.status.kda_read_at, self.status.party_size,
                self.status.party_read_at, self.settings.kda_enabled, self.settings.ocr_enabled,
                self.settings.show_timer, self.example_phase)
        if getattr(self, "last_timer_tick", None) == tick:
            return
        self.last_timer_tick = tick
        active = self.status.phase == "match" and self.status.started_at
        seconds = max(0, int(time.time() - self.status.started_at)) if active else 0
        clock = f"{seconds // 60:02d}:{seconds % 60:02d}" if active else "—"
        self.set_text(self.activity_values["Match timer"], clock)
        fresh_party = party_is_fresh(self.settings, self.status)
        party_text = self.t("Solo") if fresh_party and self.status.party_size == 1 else str(self.status.party_size) if fresh_party else "—"
        self.set_text(self.activity_values["Party"], party_text)
        if self.settings.kda_enabled:
            if kda_is_fresh(self.settings, self.status):
                values = "/".join(str(value) for value in self.status.kda)
                age = max(0, int(time.time() - self.status.kda_read_at))
                self.set_text(self.kda_label, self.t("E/A/D {values} · read {seconds}s ago", values=values, seconds=age))
            else:
                self.set_text(self.kda_label, self.t("E/A/D unavailable · open the scoreboard to refresh"))
        else:
            self.set_text(self.kda_label, "")
        if self.example_phase:
            self.set_text(self.preview_time, self.t("Match time: {time}", time="02:07") if self.example_phase == "match" and self.settings.show_timer else "")
        elif self.status.phase == "match" and self.status.started_at and self.settings.show_timer:
            seconds = max(0, int(time.time()) - self.status.started_at)
            self.set_text(self.preview_time, self.t("Match time · {time}", time=f"{seconds // 60:02d}:{seconds % 60:02d}"))
        else:
            self.set_text(self.preview_time, self.t('No match timer'))

    def hero_gallery(self):
        top = tk.Toplevel(self.root)
        top.title(self.t('Choose a hero'))
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
                button = MotionButton(grid, text=f"{hero['name']}\n{hero['role'].title()}",
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
                pystray.MenuItem(lambda item: self.t('Open OWRPC'), lambda *_: post("show"), default=True),
                pystray.MenuItem(lambda item: self.t('In menus'), lambda *_: post("phase", "menus")),
                pystray.MenuItem(lambda item: self.t('In queue'), lambda *_: post("phase", "queue")),
                pystray.MenuItem(lambda item: self.t('In match'), lambda *_: post("phase", "match")),
                pystray.MenuItem(lambda item: self.t("Resume" if self.status.paused else "Pause"), lambda *_: post("pause")),
                pystray.MenuItem(lambda item: self.t("Quit OWRPC"), lambda *_: post("quit")))
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
            self.rpc_label.set(self.t("Tray unavailable · window kept open"))

    def poll(self):
        if self.quitting:
            return
        while True:
            try:
                event, value = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "service":
                kind, result, error, manual = value
                self.service_busy.discard(kind)
                if error:
                    self.service_label.set(self.t("Network unavailable; saved data retained"))
                elif kind == "release":
                    if result:
                        self.pending_release = result
                        self.service_label.set(self.t("Update available") + ": " + result.version)
                    elif manual:
                        self.service_label.set(self.t("No newer release available"))
                elif result is not None:
                    self.catalog = result
                    self.worker.configure(self.settings, self.status, catalog=result)
                    self.service_label.set(self.t("Catalog updated") + f": {len(result['heroes'])} / {len(result['maps'])}")
                    self.preview()
            elif event == "rpc":
                self.rpc_status = value
                self.rpc_label.set(self.t(value))
            elif event == "game":
                self.game_running = value
                self.game_label.set(self.t("Overwatch running" if value else "Overwatch not running"))
            elif event == "ocr_status":
                self.ocr_status = value
                self.ocr_label.set(self.t(value))
            elif event == "game_closed":
                if value != self.worker.revision:
                    continue
                self.status.transition("menus")
                self.phase_var.set("menus")
                self.update_phase_buttons()
                self.status.hero = self.status.map_name = ""
                self.var("hero").set("")
                self.var("map_name").set("")
                self.apply_presence()
            elif event == "kda":
                values, read_at, revision = value
                if revision != self.worker.revision or self.status.phase != "match":
                    continue
                self.status.kda, self.status.kda_read_at = values, read_at
                self.preview()
            elif event == "detected":
                status, revision = value
                if revision != self.worker.revision:
                    continue
                self.status = status
                self.phase_var.set(status.phase)
                self.update_phase_buttons()
                for field in ("hero", "map_name", "mode"):
                    name = getattr(status, field)
                    self.var(field).set(name)
                    setattr(self.settings, field, name)
                self.preview()
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
        if self.pending_release and not self.game_running and self.root.state() != "withdrawn":
            release, self.pending_release = self.pending_release, None
            if messagebox.askyesno(self.t("Update available"),
                    self.t("Open the release page?") + "\n" + release.version):
                webbrowser.open(release.url)
        self.root.after(200, self.poll)

    def callback_error(self, exc_type, exc, traceback):
        log.error("UI callback failed", exc_info=(exc_type, exc, traceback))
        self.service_label.set(self.t("An error occurred; see logs"))

    def start_services(self):
        if self.quitting:
            return
        if self.settings.check_updates:
            self.run_service("release")
        if self.settings.auto_catalog:
            self.run_service("catalog")

    def run_service(self, kind, manual=False):
        if kind in self.service_busy or self.quitting:
            return
        self.service_busy.add(kind)
        previous = self.catalog
        self.service_label.set(self.t("Checking…"))
        def run():
            try:
                if kind == "release":
                    from .updates import check_release
                    result = check_release(__version__)
                else:
                    from .catalog_updates import refresh_catalog
                    result = refresh_catalog(previous, data_dir() / "catalog-cache.json", force=manual)
                self.events.put(("service", (kind, result, None, manual)))
            except Exception as exc:
                log.warning("Background %s check failed", kind, exc_info=True)
                self.events.put(("service", (kind, None, str(exc), manual)))
        threading.Thread(target=run, name="OWRPC " + kind, daemon=True).start()

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
