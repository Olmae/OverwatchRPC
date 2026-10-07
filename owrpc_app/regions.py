"""Explicit primary-monitor OCR calibration; image remains in memory."""
import tkinter as tk
from tkinter import messagebox
from .i18n import tr


def choose_region(root, callback, language="auto"):
    from PIL import ImageGrab, ImageTk
    root.withdraw()

    def capture():
        try:
            screenshot = ImageGrab.grab()
        except Exception as exc:
            root.deiconify()
            messagebox.showerror("Screen capture failed", str(exc))
            return
        width, height = root.winfo_screenwidth(), root.winfo_screenheight()
        original_w, original_h = screenshot.size
        top = tk.Toplevel(root)
        top.overrideredirect(True)
        top.geometry(f"{width}x{height}+0+0")
        top.attributes("-topmost", True)
        canvas = tk.Canvas(top, highlightthickness=0, cursor="crosshair")
        canvas.pack(fill="both", expand=True)
        image = ImageTk.PhotoImage(screenshot.resize((width, height)))
        canvas.create_image(0, 0, anchor="nw", image=image)
        canvas.image = image
        canvas.create_rectangle(12, 12, 690, 60, fill="#17202c", outline="")
        canvas.create_text(28, 36, anchor="w", fill="white", font=("Segoe UI", 13),
                           text=tr("Open the game on the primary monitor. Drag around one visible name, then press Enter. Escape cancels. The screenshot stays local.", language), width=650)
        selection = {"start": None, "end": None, "rectangle": None}

        def begin(event):
            selection["start"] = (event.x, event.y)
            selection["end"] = None
            if selection["rectangle"]:
                canvas.delete(selection["rectangle"])
            selection["rectangle"] = canvas.create_rectangle(event.x, event.y, event.x, event.y,
                                                              outline="#ff9c42", width=3)

        def drag(event):
            if selection["start"]:
                selection["end"] = (event.x, event.y)
                canvas.coords(selection["rectangle"], *selection["start"], event.x, event.y)

        def finish(event=None, confirm=False):
            region = None
            if confirm and selection["start"] and selection["end"]:
                a, b = selection["start"], selection["end"]
                x, y = min(a[0], b[0]), min(a[1], b[1])
                w, h = abs(a[0] - b[0]), abs(a[1] - b[1])
                region = [round(x * original_w / width), round(y * original_h / height),
                          round(w * original_w / width), round(h * original_h / height)]
                if region[2] < 8 or region[3] < 8:
                    return
            top.destroy()
            root.deiconify()
            root.lift()
            if region:
                callback(region)

        canvas.bind("<ButtonPress-1>", begin)
        canvas.bind("<B1-Motion>", drag)
        canvas.bind("<ButtonRelease-1>", drag)
        top.bind("<Return>", lambda e: finish(e, True))
        top.bind("<Escape>", finish)
        top.focus_force()

    root.after(400, capture)
