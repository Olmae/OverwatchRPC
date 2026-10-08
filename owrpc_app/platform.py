import ctypes
import os
import subprocess
import sys
from pathlib import Path


def game_running(process_name):
    import psutil
    return any((p.info.get("name") or "").casefold() == process_name.casefold()
               for p in psutil.process_iter(["name"]))


def game_started_at(process_name):
    """Conservative lower bound for a game clock, without reading game memory."""
    import psutil
    starts = []
    for process in psutil.process_iter(["name", "create_time"]):
        if (process.info.get("name") or "").casefold() == process_name.casefold():
            created = process.info.get("create_time")
            if created is not None:
                starts.append(created)
    return min(starts) if starts else None


def game_foreground(process_name):
    if sys.platform != "win32":
        return False
    import psutil
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(ctypes.windll.user32.GetForegroundWindow(), ctypes.byref(pid))
    try:
        return psutil.Process(pid.value).name().casefold() == process_name.casefold()
    except psutil.Error:
        return False


def set_autostart(enabled):
    if sys.platform != "win32":
        if enabled:
            raise OSError("Autostart is only supported on Windows")
        return
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        if enabled:
            if getattr(sys, "frozen", False):
                command = subprocess.list2cmdline([sys.executable, "--hidden"])
            else:
                executable = Path(sys.executable)
                windowless = executable.with_name("pythonw.exe")
                command = subprocess.list2cmdline([str(windowless if windowless.exists() else executable),
                                                   str(Path(__file__).resolve().parent.parent / "owrpc.py"), "--hidden"])
            winreg.SetValueEx(key, "OWRPC", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "OWRPC")
            except FileNotFoundError:
                pass


class SingleInstance:
    def __init__(self):
        self.handle = None
        self.already_running = False
        if sys.platform == "win32":
            kernel = ctypes.windll.kernel32
            kernel.CreateMutexW.restype = ctypes.c_void_p
            self.handle = kernel.CreateMutexW(None, False, "Local\\Olmae.OWRPC.Desktop")
            self.already_running = kernel.GetLastError() == 183
            if not self.handle:
                raise ctypes.WinError()

    def close(self):
        if self.handle:
            ctypes.windll.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None


def open_folder(path):
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def enable_dpi_awareness():
    """Use physical screen coordinates for Tk layout and OCR calibration."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def lower_worker_priority():
    """Give the foreground game precedence over local capture/preprocessing."""
    if sys.platform != "win32":
        return
    from ctypes import wintypes
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentThread.restype = wintypes.HANDLE
    kernel.SetThreadPriority.argtypes = [wintypes.HANDLE, ctypes.c_int]
    if not kernel.SetThreadPriority(kernel.GetCurrentThread(), -1):
        raise OSError("Could not lower recognition worker priority")


def tab_pressed():
    """Read current Tab state; caller must first verify game foreground."""
    if sys.platform != "win32":
        return False
    return bool(ctypes.windll.user32.GetAsyncKeyState(0x09) & 0x8000)
