"""Windows desktop entry point. Original console version: legacy_cli.py."""
import argparse
import logging
from logging.handlers import RotatingFileHandler
import sys


def main():
    parser = argparse.ArgumentParser(description="OWRPC Desktop · local Discord Rich Presence")
    parser.add_argument("--hidden", action="store_true", help="Start in the tray, if available")
    parser.add_argument("--self-test", action="store_true", help="Validate dependencies/catalog without Discord or game")
    parser.add_argument("--self-test-report", help="Write self-test result as JSON (for windowless build CI)")
    parser.add_argument("--self-test-ocr", action="store_true", help="Also validate local Windows OCR and digit assets")
    args = parser.parse_args()
    if args.self_test or args.self_test_ocr:
        import importlib
        from owrpc_app.catalog import load_catalog
        from owrpc_app.model import Settings, Status, build_payload
        from pypresence.payloads import Payload
        for dependency in ("PIL", "psutil", "pytesseract", "tkinter"):
            importlib.import_module(dependency)
        if sys.platform == "win32":
            importlib.import_module("pystray")
        catalog = load_catalog()
        hero, map_info = catalog["heroes"][0], catalog["maps"][0]
        payload = build_payload(Settings(), Status(phase="match", hero=hero["name"], map_name=map_info["name"]), hero, map_info)
        Payload.set_activity(**payload)
        for kind in ("heroes", "maps"):
            assert catalog[kind] and len({x["key"] for x in catalog[kind]}) == len(catalog[kind])
        if args.self_test_ocr:
            from PIL import Image, ImageDraw, ImageFont
            from owrpc_app.native_ocr import _engine
            from owrpc_app.digits import templates
            assert len(templates()) == 10
            image = Image.new("RGB", (600, 100), "white")
            font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 36)
            ImageDraw.Draw(image).text((20, 20), "WINDOWS OCR READY 12345", font=font, fill="black")
            try:
                text = " ".join(word.text for word in _engine.words(image))
                assert "12345" in text and "READY" in text, text
            finally:
                _engine.close()
        print(f"OWRPC self-test passed: {len(catalog['heroes'])} heroes / {len(catalog['maps'])} maps")
        if args.self_test_report:
            import json
            from pathlib import Path
            Path(args.self_test_report).write_text(json.dumps({"ok": True, "heroes": len(catalog["heroes"]),
                                                              "maps": len(catalog["maps"])}), encoding="utf-8")
        return 0
    from owrpc_app.storage import data_dir
    folder = data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[RotatingFileHandler(folder / "owrpc.log", maxBytes=1_000_000,
                                                      backupCount=2, encoding="utf-8")])
    import tkinter as tk
    from tkinter import messagebox
    from owrpc_app.platform import SingleInstance
    from owrpc_app.ui import App
    instance = SingleInstance()
    from owrpc_app.platform import enable_dpi_awareness
    enable_dpi_awareness()
    root = tk.Tk()
    if instance.already_running:
        root.withdraw()
        messagebox.showinfo("OWRPC is already running", "Open OWRPC from its system tray icon.")
        root.destroy()
        instance.close()
        return 0
    try:
        App(root, hidden=args.hidden)
        root.mainloop()
    except Exception as exc:
        logging.exception("Startup failed")
        root.deiconify()
        messagebox.showerror("OWRPC could not start", f"{exc}\n\nLog: {folder / 'owrpc.log'}")
        return 1
    finally:
        instance.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
