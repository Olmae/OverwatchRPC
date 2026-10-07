"""Scrollable pages keep settings reachable on smaller/high-DPI displays."""
import tkinter as tk
from tkinter import ttk


class ScrollPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#f2f4f7")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.content = ttk.Frame(self.canvas, padding=18)
        self.window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self.resize)
        self.canvas.bind("<Configure>", self.resize)

    def resize(self, event=None):
        width = max(1, self.canvas.winfo_width())
        height = max(self.canvas.winfo_height(), self.content.winfo_reqheight())
        self.canvas.itemconfigure(self.window, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))

    def wheel(self, event):
        steps = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(steps * 3, "units")
