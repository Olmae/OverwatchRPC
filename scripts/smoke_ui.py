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

    def configure(self, settings, status):
        self.revision += 1
        self.status = status

    def is_alive(self):
        return False


def main():
    import tkinter as tk
    from tkinter import ttk
    from PIL import ImageGrab
    from owrpc_app.ui import App
    from owrpc_app.catalog import resource_dir
    output = Path("build/ui-smoke")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"APPDATA": folder}), \
            patch("owrpc_app.ui.Worker", FakeWorker), patch.object(App, "start_tray"):
        root = tk.Tk()
        root.geometry("780x710+0+0")
        app = App(root)
        app.var("hero").set("Doctrine")
        app.var("map_name").set("King’s Row")
        app.set_phase("match")
        root.update()
        assert root.winfo_height() <= max(500, root.winfo_screenheight() - 100)
        assert app.status.hero == "Doctrine"
        assert app.status.started_at
        assert app.hero_preview.cget("image")
        assert "Doctrine" in app.preview_state.cget("text")
        for kind in ("heroes", "maps"):
            for row in app.catalog[kind]:
                if row.get("image_available"):
                    assert (resource_dir() / kind / (row["key"] + ".png")).is_file()
        book = next(w for w in root.winfo_children() if isinstance(w, ttk.Notebook))
        for tab in range(4):
            book.select(tab)
            root.update()
            time.sleep(0.2)
            if sys.platform == "win32":
                ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(),
                                    root.winfo_rootx() + root.winfo_width(),
                                    root.winfo_rooty() + root.winfo_height())).save(output / f"tab-{tab}.png")
        book.select(0)
        app.hero_gallery()
        root.update()
        app.toggle_pause()
        assert app.status.paused
        app.new_match()
        assert app.status.hero == "" and app.status.map_name == ""
        app.events.put(("recognized", ("hero", "Ana", app.worker.revision - 1)))
        app.poll()
        assert app.status.hero == "", "Stale OCR must not overwrite a manual change"
        root.destroy()
    print("Tk UI smoke passed: widgets, portraits, state transitions and stale OCR rejection")


if __name__ == "__main__":
    main()
