# OverwatchRPC

A small Windows tray companion for **Overwatch + Discord Rich Presence**.
Choose your hero, map and game mode, preview your activity, and keep the app out
of the way while you play. No Chromium runtime, account login or Discord token.

![Windows build](https://github.com/Olmae/OverwatchRPC/actions/workflows/windows.yml/badge.svg)
![Version](https://img.shields.io/badge/version-2.0.0--beta.2-orange)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/code-GPLv3-blue)

## Why this refresh exists

The original OWRPC was a useful console script, but its 2019 dependencies, map
list and terminal-only workflow had become outdated. Seven years later, I
decided to update it into a practical desktop companion: a tray icon, a compact
window, persistent settings, current hero portraits and modern Discord activity
fields. This repository preserves the old history and credits while replacing
the primary entry point with the desktop application.

**Thank you to [Tominous](https://github.com/Tominous/owrpc) for the original code
shared in their repository, and to [maxicc](https://github.com/maxicc/owrpc), the
original author credited in the source.** Their work made this refresh possible.
The untouched console implementation is kept as `legacy_cli.py` for reference;
its old network checks and catalogs are not part of the supported desktop flow.

## Get started on Windows

1. Download **OverwatchRPC-Windows.zip** from
   [Releases](https://github.com/Olmae/OverwatchRPC/releases).
2. Extract the **entire folder** to a permanent location. Keep `OverwatchRPC.exe`
   and its `_internal` directory together; Python is not required.
3. Open the desktop Discord client and enable **Activity Privacy → Share your
   detected activities with others**. Browser-only Discord cannot accept local RPC.
4. Launch `OverwatchRPC.exe`, start Overwatch, choose **In match**, select a mode,
   map and hero, then click **Apply presence**.
5. Allow up to the configured update interval (15 seconds by default), and check
   your profile from another Discord account.

Closing the window hides it in the tray once the tray is ready. Right-click the
tray icon for phase controls, Pause/Resume and Quit. **New match** clears old
selections and resets the timer. Settings are saved to `%APPDATA%\OWRPC`.

This is an **unsigned beta**. A successful build does not prove Windows tray,
Discord rendering or in-game recognition on your PC. Please use the
[Windows acceptance checklist](docs/WINDOWS-TESTING.md).

## What is included

- Tkinter desktop UI, notification-area menu, Windows startup and single-instance guard.
- Manual menus/queue/match state, editable hero/map/mode fields and a searchable hero gallery.
- Hero portraits and map thumbnails in an offline local preview.
- Persistent settings, match timer, pause/clear and automatic Discord reconnection.
- Optional game-process gating, enabled by default: only publish while `Overwatch.exe` runs.
- Current `pypresence` 4.6.2 activity fields: external HTTPS artwork, clickable hero
  image, optional URL button and application-name/state/details status display.
- Configurable application ID, image keys/URLs, custom text and update interval.
- Experimental local OCR, disabled by default; no game-memory access or injection.
- Portable Windows build, frozen dependency checks, unit tests and UI smoke checks.

## Catalog: October 6, 2026

The snapshot includes **54 heroes**, checked directly against Blizzard's official
roster, and **59 map entries** from OverFast. It includes newer heroes such as
Anran, D.Mon, Doctrine, Domina, Emre, Freja, Hazard, Jetpack Cat, Mizuki, Shion,
Sierra, Vendetta and Wuyang. Doctrine was missing from the API hero list when
retrieved, so hero names and portrait URLs come from Blizzard directly.

Maps include standard, legacy Assault, Arcade, Stadium, practice and Workshop
entries, including Aatlis, Gogadoro, Hanaoka, Neon Junction, Runasapi, Throne of
Anubis, Watchpoint: Grimsvotn and Wuxing University. This is a reference catalog,
**not the current Competitive rotation**, and it does not enumerate every seasonal
variant as a separate map. Unlisted names can be entered manually.

All 54 hero thumbnails are bundled. Map screenshots were available for 57 of the
59 entries; Neon Junction and Watchpoint: Grimsvotn returned HTTP 404 from the
provider. Their names remain selectable and use the fallback Discord artwork.
Source URLs, original image URLs, hashes and retrieval time are stored in
[`assets/catalog.json`](assets/catalog.json). Game artwork belongs to Blizzard;
see [artwork attribution](assets/NOTICE.md).

Sources:

- [Official Blizzard hero roster](https://overwatch.blizzard.com/en-us/heroes/)
- [Official October 6 patch notes](https://overwatch.blizzard.com/en-us/news/patch-notes/#patch-2026-10-06)
- [OverFast map API](https://overfast-api.tekrop.fr/maps) and
  [MIT-licensed source](https://github.com/TeKrop/overfast-api)
- [Discord Rich Presence documentation](https://docs.discord.com/developers/rich-presence/overview)
- [pypresence documentation](https://qwertyquerty.github.io/pypresence/html/doc/presence.html)

## Discord settings

The historical application ID is retained for compatibility. It is public; no
account password or user token is used. If that old Discord application stops
working, create an application in the [Developer Portal](https://discord.com/developers/applications)
and paste its application ID into Settings. Its application name determines the
activity name; it is not freely renamed by this companion.

Official hero portraits use external HTTPS URLs, so they do not depend on uploading
every new hero to the historical application's asset library. Map images use the
provider's original screenshot URLs. If Discord cannot render an external image,
disable that artwork option and use asset keys uploaded to your own application.
For an app without the historical `overwatch` asset, clear or replace that key.

The optional button needs an HTTP(S) URL and a label. Your own Discord client may
hide your own buttons; inspect the activity from another account. This companion
does not implement lobby joining, party invitations or spectating: the game does
not provide those integrations here. No Discord Social SDK login is needed for
this local IPC companion.

Updates are limited to at least 15 seconds. Unchanged payloads are skipped on
routine polls and refreshed at least once per minute at the default interval,
so a restarted Discord connection can be detected even without a hero change.
Pause clears presence without waiting for the next scheduled update; resume and
manual changes publish on the next interval. If Discord restarts, connection is
retried in the background.

## Optional automatic recognition

**Process detection does not detect your hero, map or match phase.** The reliable
default is manual selection. OCR is a separate, experimental convenience that
reads a visible name from a rectangle you explicitly select on the primary monitor.

1. Install Tesseract OCR with English (`eng`) trained data. A Windows installation
   guide is available from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
2. Use English game text and borderless/windowed mode on the primary monitor.
3. In Recognition, select a hero-name and/or map-name rectangle around **text only**.
   Drag on the frozen screenshot and press Enter; Esc cancels.
4. Enable recognition, save settings and select **In match**.
5. Keep the name visible for two consecutive OCR samples. The app accepts only
   conservative catalog matches and retains manual selections on unknown text.

The app captures selected rectangles only while Overwatch is foreground. The
calibration screenshot remains in memory; gameplay screenshots are neither saved
nor uploaded. Manual edits invalidate pending OCR observations. Recalibrate after
changing resolution, display scaling or UI layout.

Hidden hero names, short transition screens, icon-only HUDs, black fullscreen
captures, other-language names and secondary monitors are not reliably supported.
OCR cannot infer menus/queue/match state, and it is not guaranteed to recognize
every hero switch. Changing the Tesseract language alone does not translate the
English catalog. Missing OCR dependencies do not prevent manual use.

## Run from source

Use Python 3.12+ with Tkinter (included in the python.org Windows installer).

```powershell
git clone https://github.com/Olmae/OverwatchRPC.git
cd OverwatchRPC
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python owrpc.py
```

`--hidden` requests tray startup; if the tray is unavailable, the window stays
accessible. `--self-test` validates imports, catalog structure and Discord payload
serialization without connecting to Discord or capturing the screen.

The target is Windows 10/11 x64. Other platforms can run the window when Tkinter
is available, but Windows startup, single-instance guard, tray and foreground OCR
are Windows integrations. Administrator privileges are not required.

## Build and maintain

```powershell
.venv\Scripts\python -m pip install -r requirements-build.txt
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m ruff check owrpc.py owrpc_app scripts tests
.venv\Scripts\python owrpc.py --self-test
.venv\Scripts\python scripts\smoke_ui.py
.venv\Scripts\python scripts\build_windows.py
```

PyInstaller builds `dist/OverwatchRPC/OverwatchRPC.exe` on Windows. A directory
build avoids extracting a bundled runtime on every launch. CI uploads the portable
ZIP and UI previews; version tags publish a prerelease with its SHA-256 checksum.

To refresh catalog and thumbnails explicitly:

```powershell
.venv\Scripts\python scripts\refresh_catalog.py --as-of YYYY-MM-DD
```

The script fetches **live** sources, not historical archives. The `--as-of` value
records a maintainer-reviewed cutoff; it does not automatically filter future
heroes. Review official patch notes and catalog changes before committing. The
desktop application never automatically downloads catalog updates.

## Troubleshooting

- **No activity:** desktop Discord must be running with activity sharing enabled;
  Overwatch must be running if game gating is enabled. Check application ID and
  `%APPDATA%\OWRPC\owrpc.log`. Browser Discord cannot provide local IPC.
- **No portrait:** try your own application ID; verify Discord can fetch the HTTPS
  source; optionally disable external artwork and use uploaded asset keys.
- **OCR unavailable:** verify Tesseract path and traineddata. Read the Recognition
  status, recalibrate, and use manual selection when names are hidden.
- **No tray:** the window remains usable and closing exits. Use Quit in About.
- **Startup after moving files:** disable Launch with Windows before moving the
  portable folder, then enable it from the new location.
- **Settings reset:** corrupt JSON is preserved as `settings.corrupt-*.json`;
  fix or restore it while the companion is closed.

There is no telemetry or automatic updater. Logs are local, rotated and exclude
screenshots and OCR readings. Idle CPU/RAM and in-game OCR accuracy still need
measurement on a real gaming PC; lightweight architecture is not a benchmark.

## License and thanks

Source code: [GNU GPLv3](LICENSE). Original history and attribution are preserved.
Thanks to Tominous, maxicc, the pypresence maintainers and TeKrop/OverFast.
Blizzard's artwork and trademarks are separately attributed and are not GPL code.
OverwatchRPC is unofficial and is not affiliated with Blizzard or Discord.
