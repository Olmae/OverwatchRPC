# OverwatchRPC 2.0.0-beta.4

A native Windows tray companion for Overwatch and Discord Rich Presence.
This beta improves local recognition, desktop responsiveness and activity artwork.
Thank you to Tominous and maxicc for the original OWRPC code and inspiration.

- Activity dashboard with a Discord preview, compact rounded controls, nine
  interface languages and expandable settings under Additional.
- Local Windows OCR for English and Russian game interfaces. No Tesseract
  installation, WebView, cloud OCR, game-memory reads or in-game overlay.
- A foreground-only, bounded Tab capture burst lets OCR finish after releasing
  the scoreboard. Two matching readable observations still confirm changes.
- Menu, queue, map voting, winning-map loading, hero selection and match-result
  states. New-map confirmation recovers a match boundary when menu frames were missed.
- Optional E/A/D from your nickname row. The last confirmed values remain until
  the next successful read or match exit; unreadable values are never invented.
- Party count remembered from menus through search and gameplay, including the
  reviewed five-player compact header layout.
- Choose a large map with a small hero, or a large hero with a small map.
  White/orange Overwatch artwork and the original OWRPC application icon.
- Wheel scrolling over embedded controls, preserved position when collapsing
  sections and a narrow scrollbar with native hover feedback.
- Background release checks and validated daily hero/map reference updates, with
  a local cache. No automatic EXE replacement or live-statistics database.
- 54 bundled heroes and 59 map entries, with reviewed Russian aliases.
- English README with the new cover and one native application screenshot.

Validation: 101 unit tests, lint, native UI smoke checks in nine languages and
the frozen Windows OCR/dependency self-test passed on the maintainer's PC.
Real Windows OCR on 25 supplied 3440×1440 screenshots matched the declared
expectations, including documented unavailable fields. Live short-Tab checks and
an actual Discord activity capture were also performed. Documentation activity
values are illustrative, not recognition benchmarks.

Recognition remains experimental. Every hero/skin, 16:9, live rechecks of the
latest transition changes and controlled app-off/tray/open-window FPS comparisons
are still pending. Desktop latency measurements do not prove zero FPS impact.

Download `OverwatchRPC-Windows.zip` and extract the entire folder. Keep
`OverwatchRPC.exe` and `_internal` together; Python is not required. Open the
desktop Discord client, enable activity sharing, and select the game's OCR
language under Additional. This is an unsigned Windows beta.

Settings and rotating logs are stored in `%APPDATA%\OWRPC`. See the README and
Windows acceptance checklist for setup and bug-report details.
