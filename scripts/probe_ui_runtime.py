"""Bounded real-worker desktop responsiveness probe; does not require a game."""
from pathlib import Path
import json
import os
import sys
import tempfile
import time
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tkinter as tk
from owrpc_app.platform import enable_dpi_awareness
from owrpc_app.ui import App

enable_dpi_awareness()
with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'APPDATA': folder}):
    root = tk.Tk()
    app = App(root)
    errors = []
    root.report_callback_exception = lambda *args: errors.append(str(args[1]))
    delays = []
    transitions = []
    def switch_tab(index):
        began = time.perf_counter()
        app.nav_buttons[index].invoke()
        root.update_idletasks()
        transitions.append(round((time.perf_counter() - began) * 1000, 1))
    for index in range(6):
        root.after(2000 + index * 1000, lambda i=index: switch_tab(i % 2))
    start = time.perf_counter()
    cpu_start = time.process_time()
    expected = start + .05
    def heartbeat():
        global expected
        now = time.perf_counter()
        delays.append(max(0, now - expected))
        expected = now + .05
        if now - start >= 12:
            report = {'heartbeat_max_ms': round(max(delays) * 1000, 1),
                      'heartbeat_p95_ms': round(sorted(delays)[int(len(delays)*.95)] * 1000, 1),
                      'cpu_seconds': round(time.process_time() - cpu_start, 3),
                      'seconds': round(now - start, 2), 'samples': len(delays),
                      'callback_errors': errors, 'tab_switch_ms': transitions, 'scope': 'real Worker, tray and startup services; no running game'}
            Path('build').mkdir(exist_ok=True)
            Path('build/ui-runtime.json').write_text(json.dumps(report), encoding='utf-8')
            app.quit()
            return
        root.after(50, heartbeat)
    root.after(50, heartbeat)
    root.mainloop()
