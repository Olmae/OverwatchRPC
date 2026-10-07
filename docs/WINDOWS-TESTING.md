# Windows acceptance checklist

## Recorded beta checks (October 7, 2026)

The beta.2 portable x64 build launched under Windows 11 ARM64 x64 emulation in
Parallels (Windows 10.0.26200.9168). Its frozen self-test loaded 54 heroes and 59
maps. The desktop window and Settings tab rendered in the interactive user
session. With game gating disabled in isolated test settings, the logged-in
desktop Discord client displayed In Menus, then a manually selected Quick Play
match with a map name, Doctrine portrait, and match timer. These are observed
client results, rather than only mocked IPC tests.

One five-second idle sample with OCR disabled measured approximately 67 MiB RAM
and 0.62% of one CPU core. This short VM measurement is not a gaming benchmark.
Real Overwatch capture/OCR, tray lifecycle, startup, and Discord restart recovery
still require the checklist below. Beta.3 changes the fallback logo source and
migrates the legacy `overwatch` image key; its rendering needs a separate check.

The unit tests and CI smoke checks do not validate these real-device flows.
Please run this checklist with the desktop Discord client and Overwatch on your PC.

- Extract the entire portable ZIP and launch `OverwatchRPC.exe` without Python.
- Launch while Discord is closed: window opens, stays responsive and shows retrying.
- Open Discord: presence connects after the next interval. Enable activity sharing.
- Start Overwatch; select In match, a map and hero, then Apply presence. Inspect
  the profile from another Discord account: text, external images and timer render.
- Check the optional link button from another account (own buttons may be hidden).
- Pause clears activity; Resume restores it on the next update interval.
- Close hides to tray, Open OWRPC restores it, Quit exits and clears activity.
- Relaunch twice: the second instance reports the already-running tray app.
- Enable Launch with Windows; log out/in; the app starts. Disable it and verify
  the OWRPC HKCU Run entry is removed. Move a portable folder only after disabling
  startup, then enable startup again from its new location.
- Close the game: hero/map clear, phase returns to menus; with game gating enabled,
  activity disappears within the polling/update interval.
- Restart Discord during a match: the companion reconnects without resetting time.
- Select New match: timer restarts and old hero/map fields clear.
- Test at 100%, 125% and 150% display scaling; every control is reachable.
- Optional OCR: install Tesseract and eng traineddata, run Overwatch borderless on
  the PRIMARY monitor, select only hero/map name text, enable OCR, select In match.
  Keep the text visible for two samples; check the OCR status and actual name.
- Alt-tab away: OCR stops capturing. Test unknown/noisy text: it must not invent
  a selection. Manual changes must override pending OCR results.
- Change resolution: recalibrate. Missing Tesseract, unsupported language, hidden
  hero text or black captures should show a diagnostic without preventing manual use.
- Check Task Manager with OCR off and on; record CPU, RAM and update latency.
  Performance is not yet measured on a gaming PC.

Logs and settings: `%APPDATA%\OWRPC`. No screenshot files are created by the app.
Report OS, app version, display scaling, Discord version, log excerpt and exact
steps. Do not upload personal screenshots or logs without reviewing them first.
