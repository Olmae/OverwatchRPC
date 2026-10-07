"""Real Tk widget smoke test; Windows CI additionally captures preview images.

Uses a fake worker: this tests layout and controls, not Discord IPC or game OCR.
"""
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class FakeWorker:
    def __init__(self, *args):
        self.revision = 0
        self.status = None

    def start(self):
        pass

    def configure(self, settings, status, catalog=None):
        self.revision += 1
        self.status = status

    def is_alive(self):
        return False


def main():
    import tkinter as tk
    from PIL import ImageGrab
    from owrpc_app.ui import App
    from owrpc_app.catalog import resource_dir
    output = Path("build/ui-smoke")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"APPDATA": folder}), \
            patch("owrpc_app.ui.Worker", FakeWorker), patch.object(App, "start_tray"):
        from owrpc_app.platform import enable_dpi_awareness
        enable_dpi_awareness()
        root = tk.Tk()
        root.geometry("780x710+0+0")
        ui_started = time.perf_counter()
        print("Creating native UI", flush=True)
        App.start_services = lambda self: None
        app = App(root)
        callback_errors = []
        root.report_callback_exception = lambda *args: callback_errors.append(str(args[1]))
        print("Native UI created", flush=True)
        original_catalog = app.catalog
        original_rpc_status = app.rpc_status
        app.events.put(("service", ("catalog", None, None, False)))
        app.poll()
        assert app.catalog is original_catalog
        app.ocr_language_choice.set("Русский")
        with patch("owrpc_app.ui.set_autostart"):
            app.save_preferences()
        assert app.settings.ocr_language == "rus"
        assert app.rpc_status == original_rpc_status
        app.artwork_layout_choice.set(app.t("Large hero, small map"))
        app.artwork_layout_widget.event_generate("<<ComboboxSelected>>")
        with patch("owrpc_app.ui.set_autostart"):
            app.save_preferences()
        assert app.settings.artwork_layout == "hero_large"
        app.artwork_layout_choice.set(app.t("Large map, small hero"))
        app.artwork_layout_widget.event_generate("<<ComboboxSelected>>")
        with patch("owrpc_app.ui.set_autostart"):
            app.save_preferences()
        assert app.settings.artwork_layout == "map_large"
        app.events.put(("service", ("catalog", None, "offline", True)))
        app.poll()
        assert app.catalog is original_catalog

        app.var("hero").set("Doctrine")
        app.var("map_name").set("King’s Row")
        app.set_phase("match")
        print("Updating layout", flush=True)
        root.update()
        print("Layout ready in", round(time.perf_counter() - ui_started, 2), "seconds", flush=True)
        from owrpc_app.widgets import Disclosure
        app.book.select(1)
        root.update()
        page = root.nametowidget(app.book.tabs()[1])
        disclosures = []
        def collect(widget):
            if isinstance(widget, Disclosure):
                disclosures.append((widget, widget.opened))
            for child in widget.winfo_children():
                collect(child)
        collect(page)
        for section, _ in disclosures:
            section.opened = True
            section.render()
        root.update()
        page.canvas.yview_moveto(.15)
        root.update()
        previous = page.canvas.yview()[0]
        selected = app.artwork_layout_widget.get()
        app.artwork_layout_widget.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert page.canvas.yview()[0] > previous, "Wheel over an expanded section must scroll the page"
        assert app.artwork_layout_widget.get() == selected, "Wheel must not silently change a closed list"
        before_resize = page.canvas.canvasy(0)
        # Changing a lower section's height preserves the top pixel rather than
        # its fraction of the full document, which previously caused jumps.
        section = disclosures[-1][0]
        section.opened = False
        section.render()
        root.update()
        assert abs(page.canvas.canvasy(0)-before_resize) <= 2
        for section, opened in disclosures:
            section.opened = opened
            section.render()
        page.canvas.yview_moveto(0)
        app.book.select(0)
        root.update()
        assert root.winfo_height() <= max(500, root.winfo_screenheight() - 100)
        assert app.status.hero == "Doctrine"
        assert app.status.started_at
        assert app.hero_preview.cget("image")
        selected_hero = next(row for row in app.catalog["heroes"] if row["name"] == app.status.hero)
        displayed_hero = selected_hero.get("localized_names", {}).get(app.language, app.status.hero)
        assert app.preview_state.cget("text") == app.t("Playing {hero}", hero=displayed_hero)
        for kind in ("heroes", "maps"):
            for row in app.catalog[kind]:
                if row.get("image_available"):
                    assert (resource_dir() / kind / (row["key"] + ".png")).is_file()
        from owrpc_app.i18n import LANGUAGES
        from owrpc_app.storage import load_settings
        print("UI dimensions", root.winfo_width(), root.winfo_height(), "screen", root.winfo_screenwidth(), root.winfo_screenheight(), "scale", app.scale)
        timer = app.status.started_at
        app.var("details_override").set("My custom activity")
        app.display_value = 2
        app.toggle_pause()
        for code, name in LANGUAGES.items():
            language_started = time.perf_counter()
            print("UI language", code, flush=True)
            app.language_var.set(name)
            app.change_language()
            root.update()
            print("Language layout seconds", round(time.perf_counter() - language_started, 2), flush=True)
            assert app.language == code
            assert app.status.hero == "Doctrine" and app.status.map_name == "King’s Row"
            assert app.status.started_at == timer and app.status.paused
            assert app.phase_buttons["match"].cget("background") == "#68451c"
            assert app.var("details_override").get() == "My custom activity"
            assert app.display_value == 2
            assert app.phase_var.get() == "match"
            assert app.book.tab(0, "text") == app.t("Activity")
            assert app.preview_state.cget("text") == app.t("Presence paused")
            app.book.select(1)
            root.update()
        app.language_var.set(LANGUAGES["ru"])
        app.change_language()
        app.toggle_pause()
        app.var("only_when_game").set(False)
        with patch("owrpc_app.ui.set_autostart"):
            app.save_preferences()
        saved, warning = load_settings()
        assert not warning and saved.language == "ru" and saved.display_type == 2
        assert saved.details_override == "My custom activity"
        assert not saved.only_when_game
        assert app.status.started_at == timer
        app.var("details_override").set("")
        app.settings.details_override = ""
        app.settings.kda_enabled = True
        app.status.kda, app.status.kda_read_at = (12, 4, 3), time.time()
        app.preview()
        app.status.party_size, app.status.party_read_at = 3, time.time()
        app.timer_tick()
        assert app.activity_values["Party"].cget("text") == "3"
        app.status.party_read_at = time.time() - 1000
        app.timer_tick()
        assert app.activity_values["Party"].cget("text") == "3", "Last confirmed party stays visible during a match"
        app.set_phase("menus")
        app.timer_tick()
        assert app.activity_values["Party"].cget("text") == "—", "Leaving the match clears remembered party"
        app.status.party_size = app.status.party_read_at = None
        # Rounded surfaces keep native keyboard activation and disabled state.
        app.pause_button.focus_force()
        root.update()
        paused = app.status.paused
        app.pause_button.event_generate("<Return>")
        root.update()
        assert app.status.paused != paused, "Return must invoke once"
        app.pause_button.event_generate("<Return>")
        root.update()
        assert app.status.paused == paused
        app.pause_button.configure(state="disabled")
        app.pause_button.invoke()
        assert app.status.paused == paused, "Disabled buttons must not invoke"
        app.pause_button.configure(state="normal")
        app.pause_button.animate(app.pause_button.hover)
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            root.update()
            time.sleep(0.02)
        assert app.pause_button.animation is None, "Button animation must stop after transition"
        app.catalog_picker("heroes", "hero")
        root.update()
        for child in root.winfo_children():
            if isinstance(child, tk.Toplevel):
                child.destroy()
        for tab in range(2):
            app.book.select(tab)
            root.update()
            time.sleep(0.2)
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
                hwnd = ctypes.windll.user32.GetAncestor(root.winfo_id(), 2)
                ImageGrab.grab(window=hwnd).save(output / f"tab-{tab}.png")
        app.book.select(0)
        if sys.platform == "win32":
            def capture(name):
                root.update()
                time.sleep(0.15)
                ImageGrab.grab(window=hwnd).save(output / name)
            app.show_example("menus")
            capture("menu-preview.png")
            app.show_example(None)
            app.toggle_manual()
            capture("manual.png")
            app.toggle_manual()
            root.geometry(f"{int(760 * app.scale)}x{int(710 * app.scale)}")
            root.update()
            assert app.dashboard_right.grid_info()["row"] == 1
            capture("narrow.png")
        # Examples must never configure the worker or mutate real activity.
        revision = app.worker.revision
        actual = (app.status.phase, app.status.hero, app.status.map_name, app.status.started_at)
        for phase in ("menus", "queue", "match", None):
            app.show_example(phase)
            root.update()
            assert app.worker.revision == revision
            assert (app.status.phase, app.status.hero, app.status.map_name, app.status.started_at) == actual
        app.toggle_manual()
        root.update()
        assert app.manual_panel.winfo_ismapped()
        app.toggle_manual()
        assert not app.manual_open
        app.hero_gallery()
        root.update()
        app.toggle_pause()
        assert app.status.paused
        app.new_match()
        assert app.status.hero == "" and app.status.map_name == ""
        app.events.put(("kda", ((12, 4, 3), time.time(), app.worker.revision - 1)))
        app.events.put(("recognized", ("hero", "Ana", app.worker.revision - 1)))
        app.poll()
        assert app.status.hero == "", "Stale OCR must not overwrite a manual change"
        assert not callback_errors, callback_errors
        root.destroy()
    print("Tk UI smoke passed: widgets, portraits, state transitions and stale OCR rejection")


if __name__ == "__main__":
    main()
