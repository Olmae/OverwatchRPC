# OverwatchRPC 2.0.0-beta.5

A native Windows tray companion for Overwatch and Discord Rich Presence.
This beta improves English/Russian recognition, scoreboard geometry and match transitions.
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
- Tab portrait templates for all 54 catalog heroes, with ambiguous matches rejected.
- Scoreboard geometry and wider nickname crops improve E/A/D recognition,
  including initial 0/0/0 rows and English practice scoreboards.
- Separate numeric timer recognition reads previously missed 0:29 and 0:42
  clocks. Capture-time confirmation and process-age checks reject implausible
  readings. Window borders and pillarboxed headers receive separate handling.
- Mode icons supplement text for Control, Escort, Hybrid and Push, while
  Mystery Madness remains a distinct playlist.
- English Grímsvötn headers match Watchpoint: Grimsvotn, including partially
  omitted accents. A confirmed exit from Practice clears its retained map even
  when the next map name is unreadable.
- Captured Tab frames can finish after switching to the application, with
  bounded queues and stale-work rejection. Logs include recognition-stage timing.

Validation: 118 unit tests, lint, native UI smoke checks in nine languages and
the frozen Windows OCR/dependency self-test passed on the maintainer's PC.
Real Windows OCR on 41 supplied English/Russian 16:9 and 21:9 frames matched the declared
expectations, including documented unavailable fields. Live short-Tab checks and
an actual Discord activity capture were also performed. Documentation activity
values are illustrative, not recognition benchmarks. Some clock fixtures are
calibration data, rather than independent accuracy measurements.

Recognition remains experimental. Every hero/skin, every layout and controlled
app-off/tray/open-window FPS comparisons
are still pending. Desktop latency measurements do not prove zero FPS impact.

Download **OverwatchRPC.exe** for the standalone application, or
**OverwatchRPC-Windows.zip** for the recommended portable folder. The standalone
EXE extracts its runtime to a temporary directory at launch, so startup can take
longer. No screenshots are attached to this release.

For the ZIP download, extract the entire folder. Keep
`OverwatchRPC.exe` and `_internal` together; Python is not required. Open the
desktop Discord client, enable activity sharing, and select the game's OCR
language under Additional. This is an unsigned Windows beta.

Settings and rotating logs are stored in `%APPDATA%\OWRPC`. See the README and
Windows acceptance checklist for setup and bug-report details.
