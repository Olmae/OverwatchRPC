# OWRPC Desktop 2.0

Windows-first companion for Discord Rich Presence, based on the GPLv3 Python
fork. Keep the existing CLI available as `legacy_cli.py`; `owrpc.py` launches the
desktop app. User requested autonomous implementation and GitHub publication.

## Product

- An English-language Tkinter window and a pystray notification-area menu.
- Manual menus/queue/match state, editable hero/map/mode catalogs and custom text.
- Persist settings in `%APPDATA%/OWRPC/settings.json`, atomically; preserve corrupt
  settings separately instead of silently overwriting them.
- Discord runs in a worker thread with reconnection and a minimum 15-second update
  interval. UI never calls Discord synchronously. Pausing clears presence.
- Optional Windows startup via an HKCU Run entry; closing hides to tray when the
  tray started successfully, otherwise quits. Single instance per Windows user.
- Optional game-process gating; no memory access, injection, game-file modifications
  or undocumented game API. A process name detects running game, not match state.
- Experimental local OCR: user explicitly selects a map and/or hero text rectangle
  on the primary monitor. Capture only while Overwatch is foreground. Tesseract is
  an external optional dependency. Accept catalog matches only after repeated
  confident samples. Never claim OCR determines match phase. Manual changes clear
  pending OCR observations. No screenshots are uploaded or saved.
- Text names always work. Existing Discord app assets may be obsolete; only the
  known `overwatch` key is used by default. Custom app ID and image keys are editable.
- Include a dated catalog, editable selections for later patches, packaging, a portable
  Windows ZIP, automatic GitHub Actions tests/build, and an honest Windows checklist.
  Final publication target is `Olmae/OverwatchRPC`; acknowledgements name Tominous
  and maxicc. All UI, documentation and commits use English.

## Boundaries

`owrpc_app/model.py`: settings, status, validation, payload and catalog matching.
`storage.py`: atomic persistence and corrupt-file recovery.
`platform.py`: process/foreground/startup/single-instance integration.
`ocr.py`: screen regions and local Tesseract recognition.
`runtime.py`: background polling, Discord connection, OCR debounce, event queue.
`ui.py`: Tkinter controls and thread-safe tray events. `widgets.py` provides
scrollable pages; `regions.py` handles explicit screenshot-region calibration.

## Validation

Unit tests cover invalid settings, corrupted files, presence transitions, reconnect,
pause/clear, stale OCR rejection and matching ambiguity. Windows CI builds a frozen
app and smoke-tests its dependency imports and `--self-test`. Local macOS tests do
not prove Windows tray, Discord IPC, fullscreen capture or OCR accuracy. The user
will validate those on the gaming PC; release is marked beta until then.
