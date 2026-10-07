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

Windows PC probe, 2026-10-07: i9-9900K, RTX 5070 Ti, 32 GiB RAM,
Windows 11, 3440x1440 desktop, Tk scale approximately 1.0. With the real Worker,
tray and startup checks, but no running game, transitions measured
[0.0, 99.3, 10.6, 11.6, 11.7, 11.4] ms. Maximum heartbeat delay was 112.2 ms,
p95 16.4 ms, and process CPU time 1.344 seconds over 12.01 seconds.
No callback errors occurred. Game screenshots show instantaneous FPS only;
they are not comparable app-off/tray/window measurements. Real FPS impact,
frame times and recognition CPU load have not yet been established.

After independent bounded Tab capture and artwork controls, a repeat PC probe
without a running game or concurrent build measured transitions
[0.0, 130.1, 5.9, 8.9, 6.2, 5.9] ms, heartbeat maximum 122.5 ms,
p95 13.4 ms and 1.062 CPU seconds over 12.02 seconds, with no callback errors.
In the preceding live build, a 698 ms Tab opening supplied two frames; E/A/D
31/6/6 confirmed about three seconds after release. This proves processing can
continue after release, not that all heroes or arbitrarily brief taps succeed.

Expanded settings route mouse-wheel events through a page binding before
closed combobox class bindings. Wheel scrolling no longer changes a selection
or stops over an embedded control; open popup lists retain their own handling.
Changing document height preserves the top pixel instead of the scroll fraction.
The native smoke probe opens all sections, checks wheel scrolling over the
artwork selector without changing it, and verifies position after collapsing
a lower section. These are real Tk controls with a substitute Worker.

The page scrollbar uses a narrow native ttk thumb, a dark track and native
hover/pressed colors. There is no redraw loop or per-hover image generation.
After transition recognition and scrolling changes, a clean PC probe without
a running game measured transitions [0.0, 106.0, 6.0, 5.5, 5.4, 5.6] ms,
heartbeat maximum 79.2 ms, p95 14.0 ms and 1.078 CPU seconds over 12.05 seconds,
with no callback errors. These measurements do not establish game FPS impact.
