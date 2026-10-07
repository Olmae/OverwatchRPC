# Desktop responsiveness check

Measured in the existing Windows 11 Parallels VM on an Apple Silicon Mac at
200% UI scale. The probe uses the real background Worker, tray and startup
release/catalog checks. Overwatch was not running.

The original 9-slice button image had a 3-pixel center, which ttk tiled across
wide buttons. Enlarging the center reduces repeated alpha-image draw operations
without increasing the native requested button size. Hover uses prebuilt native
state images; text wrapping follows the container and avoids repeated unchanged
configuration. Scroll-page size updates are coalesced at idle.

Before the button-image fix, the first transition to Additional took 2409.9 ms.
The final measured transitions were [0.2, 161.3, 32.2, 31.0, 38.1, 29.6] ms.
The event-loop probe recorded a maximum delay of 169.3 ms,
a 95th percentile delay of 53.8 ms, and no callback errors.
These are short desktop responsiveness measurements, not an FPS benchmark or
proof of in-game recognition performance on other machines.

Run `python scripts/probe_ui_runtime.py` from a Windows checkout. The script
uses temporary settings and records `build/ui-runtime.json`. The probe closes
its own window after approximately 12 seconds. Also run
`python scripts/smoke_ui.py` for localization, controls, persistence and layout.
