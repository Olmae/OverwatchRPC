# Localization and usability refresh (local draft)

Keep OWRPC focused on Discord Rich Presence and retain its small native Tk UI.
The first screen should explain connection status and let a player select phase,
mode, hero and map. General settings contain language, tray/startup behavior,
game gating and the timer. Advanced settings group Discord connection, activity
appearance and experimental OCR, with plain explanations and safe defaults.

Support English, Simplified Chinese, Russian, Brazilian Portuguese, Spanish,
Traditional Chinese and Korean. This selection uses Steam review counts for
Overwatch (app 2357570), retrieved October 7, 2026, as a public audience proxy.
It is not an official ranking of all Overwatch players, including Battle.net.
English 172138; Simplified Chinese 145490; Russian 21453; Brazilian Portuguese
20713; Spanish (Spain) 15645; Traditional Chinese 6106; Korean 6074.
Spanish Latin America is covered by the Spanish interface as well.
Sources: https://store.steampowered.com/app/2357570/ and its public appreviews API.

Store stable English catalog identifiers and modes so language switching cannot
break artwork lookup, existing settings or OCR matching. Translate visible
interface and Discord activity phrases; use official localized hero names when
available, with canonical names as a fallback. UI language does not imply support
for recognizing localized game text with OCR.

Language changes retain the current match, timer, pause state and unsaved fields.
No game memory access, overlay, account/token login or performance counters.
Do not commit or push this draft or implementation until the user requests it.

## Implementation and verification

1. Add an offline translation layer, locale validation, platform locale detection
   and tests for language completeness, formatting, fallback and payloads.
2. Split general and advanced settings, translate dialogs/tray/status messages,
   simplify activity controls and retain all existing configuration capabilities.
3. Fetch official hero-name translations without changing the cutoff catalog.
4. Test state preservation on language changes, setting round trips, stale OCR
   rejection, all seven layouts and frozen asset availability. Render actual Tk
   screens in the Windows ARM VM; report game/OCR checks separately.

The additional French and German interfaces bring the supported total to nine languages. All catalog identifiers remain canonical; proper hero and map names use the existing source names unless a localized name is available.

Approved visual direction: graphite surfaces, orange Overwatch accents, native
Tk controls, searchable selection dialogs, event-driven button transitions and
a two-column Discord preview. No WebView.

Optional scoreboard E/A/D is opt-in. Read only a calibrated rectangle while
Overwatch is foreground and the phase is match. Accept exactly three numeric
counters after two consecutive matching samples; track reading time, retain the
last confirmed values until the next update or match exit, and reset on a new match. Reject events from prior worker
revisions. This is an experimental OCR convenience, not a live game API.
