# Desktop refresh · beta 3

The seven-year-old console companion is now a Windows tray application with
English UI, settings and documentation. Thank you to Tominous and maxicc for
the original OWRPC code and inspiration.

- Tkinter window, tray controls, optional Windows startup and single-instance guard.
- Manual phase/map/hero controls, hero gallery, local preview and match timer.
- 54 official Blizzard hero portraits and a 59-entry map catalog, checked against
  available sources for October 6, 2026. Includes Doctrine and legacy/Arcade/Stadium
  maps; seasonal duplicates and ranked rotations are not a separate catalog.
- Current pypresence 4.6.2: HTTPS images, clickable hero artwork, optional profile
  button, status display selection, background reconnect and update throttling.
- Optional calibrated Tesseract OCR, foreground-only capture and conservative
  matching. This is experimental; it cannot infer match state or read hidden text.
- Local atomic settings, rotating logs, Windows portable ZIP and build checks.
- Window size adapts to screen height; settings remain reachable through scrolling.

The transparent official fallback logo replaces the old white-square Discord
asset; existing settings using the legacy image key migrate automatically.

Extract the entire ZIP. Launch `OverwatchRPC.exe`; Python is not needed. Tesseract
is needed only for optional OCR. The build is unsigned.

Beta.2 ran in Windows 11 ARM64 under x64 emulation and published real Discord menu
and match activity with Doctrine's portrait and a timer. Real Overwatch/OCR and
the full tray/startup lifecycle still require testing. See the included
WINDOWS-TESTING.md before treating the beta as stable.
