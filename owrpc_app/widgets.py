"""Scrollable pages keep settings reachable on smaller/high-DPI displays."""
import tkinter as tk
from tkinter import ttk


class ScrollPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#15191f")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                  style="OWRPC.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.content = ttk.Frame(self.canvas, padding=18, style="Page.TFrame")
        self.window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self.resize)
        self.canvas.bind("<Configure>", self.resize)
        self.wheel_tag = "OWRPCScroll" + str(self)
        self.bind_class(self.wheel_tag, "<MouseWheel>", self.wheel)
        self.after_idle(self.install_wheel_bindings)
        self.bind("<Destroy>", self.clear_wheel_binding)

    def install_wheel_bindings(self):
        def visit(widget):
            tags = widget.bindtags()
            if self.wheel_tag not in tags:
                widget.bindtags((self.wheel_tag, *tags))
            for child in widget.winfo_children():
                visit(child)
        visit(self)

    def clear_wheel_binding(self, event):
        if event.widget == self:
            self.unbind_class(self.wheel_tag, "<MouseWheel>")

    def resize(self, event=None):
        if getattr(self, "resize_pending", False):
            return
        self.resize_pending = True
        self.after_idle(self.resize_content)

    def resize_content(self):
        self.resize_pending = False
        width = max(1, self.canvas.winfo_width())
        height = max(self.canvas.winfo_height(), self.content.winfo_reqheight())
        extent = (width, height)
        if getattr(self, "last_extent", None) == extent:
            return
        self.last_extent = extent
        top = max(0, self.canvas.canvasy(0))
        self.canvas.itemconfigure(self.window, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))
        self.canvas.yview_moveto(top / height)

    def wheel(self, event):
        if not event.delta:
            return "break"
        steps = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(steps * 3, "units")
        return "break"


class MotionButton(ttk.Button):
    """A native ttk button with a small, stretchable rounded image surface.

    The label, keyboard bindings, command and disabled state stay native. Only
    the background is drawn. Two tiny images are reused during hover feedback;
    no canvas, full-size bitmaps or repeating idle animation are required.
    """

    def __init__(self, parent, **kwargs):
        from PIL import ImageTk
        accent = kwargs.pop("style", "") == "Accent.TButton"
        self.base = "#f59c20" if accent else "#2a323e"
        self.hover = "#ffb744" if accent else "#3a4554"
        self.animation = None
        self.surface_color = self.base
        self.foreground_color = "#15191f" if accent else "#f4f6f8"
        self.surface_background = parent_background(parent)
        self.surface_scale = max(1.0, float(parent.tk.call("tk", "scaling")) / (96 / 72))
        self.radius = round(9 * self.surface_scale)
        # ttk tiles the center of an image surface. A 3-pixel center
        # caused thousands of alpha draws on wide buttons at high DPI.
        # A wider center keeps the rounded border with far fewer draw calls.
        self.tile_size = 2 * self.radius + 129
        super().__init__(parent, **kwargs)
        self.native_style = ttk.Style(self)
        root = self._root()
        root.rounded_button_serial = getattr(root, "rounded_button_serial", 0) + 1
        self.surface_style = "Rounded" + str(root.rounded_button_serial) + ".TButton"
        self.surface_image = ImageTk.PhotoImage(self.surface_bitmap(self.base))
        self.focus_image = ImageTk.PhotoImage(self.surface_bitmap(self.base, focused=True))
        self.hover_image = ImageTk.PhotoImage(self.surface_bitmap(self.hover))
        element = self.surface_style + ".surface"
        self.native_style.element_create(element, "image", self.surface_image,
                                         ("disabled", self.surface_image), ("focus", self.focus_image), ("active", self.hover_image),
                                         border=self.radius + 1, padding=0, sticky="nsew",
                                         width=2 * self.radius + 5, height=2 * self.radius + 5)
        self.native_style.layout(self.surface_style, [
            (element, {"sticky": "nsew", "children": [
                ("Button.padding", {"sticky": "nsew", "children": [
                    ("Button.label", {"sticky": "nsew"})]})]})])
        self.native_style.configure(self.surface_style,
                                    padding=(round(14 * self.surface_scale), round(8 * self.surface_scale)),
                                    font=("Segoe UI", 10), foreground=self.foreground_color,
                                    background=self.surface_background, anchor="center")
        self.native_style.map(self.surface_style, foreground=[("disabled", "#737d89")])
        super().configure(style=self.surface_style, takefocus=True)
        self.bind("<Destroy>", self.stop_animation)
        def keyboard_invoke(event):
            self.invoke()
            return "break"
        self.bind("<Return>", keyboard_invoke)

    def surface_bitmap(self, color, focused=False):
        return rounded_tile(self.tile_size, self.radius, color, self.surface_background,
                            "#ffc46d" if focused else None, round(self.surface_scale))

    def configure(self, cnf=None, **kwargs):
        # Existing selection controls use tk-style color options. Convert just
        # these appearance options into ttk styles; keep native options intact.
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        if "background" in kwargs:
            color = kwargs.pop("background")
            if color != self.surface_color:
                self.surface_color = color
                self.surface_image.paste(self.surface_bitmap(color))
                self.focus_image.paste(self.surface_bitmap(color, focused=True))
                self.hover_image.paste(self.surface_bitmap(self.hover))
        if "foreground" in kwargs:
            color = kwargs.pop("foreground")
            if color != self.foreground_color:
                self.foreground_color = color
                self.native_style.configure(self.surface_style, foreground=color)
        for key in ("anchor", "font", "padding"):
            if key in kwargs:
                self.native_style.configure(self.surface_style, **{key: kwargs.pop(key)})
        if cnf is None and not kwargs:
            return None
        return super().configure(cnf, **kwargs)

    config = configure

    def cget(self, key):
        if key == "background":
            return self.surface_color
        if key == "foreground":
            return self.foreground_color
        return super().cget(key)

    def stop_animation(self, event=None):
        if self.animation:
            self.after_cancel(self.animation)
            self.animation = None

    def animate(self, target):
        # ttk selects the prebuilt active image. No scheduled bitmap repaints.
        self.stop_animation()


def parent_background(parent):
    if isinstance(parent, ttk.Widget):
        style = parent.cget("style") or parent.winfo_class()
        return ttk.Style(parent).lookup(style, "background") or "#20252d"
    return parent.cget("background")


def rounded_tile(size, radius, color, background, outline=None, stroke=1):
    """Antialiased 9-slice tile; size depends on corner radius, not widget size."""
    from PIL import Image, ImageDraw
    ratio = 4
    image = Image.new("RGB", (size * ratio, size * ratio), background)
    draw = ImageDraw.Draw(image)
    inset = ratio if outline else 0
    draw.rounded_rectangle((inset, inset, size * ratio - 1 - inset, size * ratio - 1 - inset),
                           radius=radius * ratio, fill=color, outline=outline,
                           width=max(1, stroke) * ratio)
    return image.resize((size, size), Image.Resampling.LANCZOS)


class RoundedCard(ttk.Frame):
    """A native frame with four fixed-size corner images, no geometry tricks."""

    def __init__(self, parent, **kwargs):
        from PIL import ImageTk
        kwargs.setdefault("style", "Card.TFrame")
        super().__init__(parent, **kwargs)
        scale = max(1.0, float(self.tk.call("tk", "scaling")) / (96 / 72))
        radius = round(16 * scale)
        size = 2 * radius + 5
        background = parent_background(parent)
        tile = rounded_tile(size, radius, "#20252d", background)
        self.corner_images = []
        for box, x, y, anchor in (
            ((0, 0, radius, radius), 0, 0, "nw"),
            ((size - radius, 0, size, radius), 1, 0, "ne"),
            ((0, size - radius, radius, size), 0, 1, "sw"),
            ((size - radius, size - radius, size, size), 1, 1, "se"),
        ):
            image = ImageTk.PhotoImage(tile.crop(box))
            self.corner_images.append(image)
            corner = tk.Label(self, image=image, borderwidth=0, highlightthickness=0, background=background)
            corner.place(relx=x, rely=y, anchor=anchor, bordermode="outside")




class Disclosure(ttk.Frame):
    """Keyboard-accessible section with no animation or work while collapsed."""

    def __init__(self, parent, title, opened=False):
        super().__init__(parent, style="Page.TFrame")
        self.title = title
        self.opened = opened
        self.heading = MotionButton(self, command=self.toggle)
        self.heading.pack(fill="x")
        self.content = RoundedCard(self, padding=(16, 12, 16, 14))
        self.render()

    def toggle(self):
        self.opened = not self.opened
        self.render()

    def render(self):
        self.heading.configure(text=("▾  " if self.opened else "▸  ") + self.title, anchor="w")
        if self.opened:
            self.content.pack(fill="x", pady=(6, 0))
        else:
            self.content.pack_forget()
