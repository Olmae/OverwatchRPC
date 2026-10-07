# Automatic recognition

The existing optional recognition flow now runs on all foreground game scenes,
not only after a manual match selection. It uses the built-in Windows OCR engine
in a persistent hidden helper process. There are no browser runtimes, cloud OCR
calls, model downloads, screenshot files, game-memory reads, or injected hooks.
English and Russian OCR require the corresponding Windows language capability.

Scene parsing uses normalized positions and text. Search overrides gallery and
practice-range scenes; results override live data; history screens never supply
the current map or outcome. A scoreboard anchors E/A/D columns using header
geometry, supports five or six rows, and reads own hero/map from separate areas.
Italic names are straightened. Tiny digit templates supplement missing OCR
characters. Row matching is independent of team color and highlight color.

The worker confirms state changes with two observations, rejects captures that
cross a manual configuration revision, clears match-specific values on phase
changes, and keeps the last confirmed fields on unknown frames. E/A/D expires
and is never inferred from another player's row. A nickname can be learned from
the HUD; an explicit nickname in Advanced is recommended. Tab is not pressed by
the app. An unseen hero switch cannot be confirmed.

Private source screenshots remain under ignored `build/recognition-fixtures`.
`scripts/check_recognition.py` validates their external manifest using real
Windows OCR, including grayscale, inverted and shifted-hue variants. The digit
unit-test images contain only number cells, with no names or account data.

Russian recognition uses the official Blizzard names for all 54 catalog heroes,
plus an initial subset of map names in `localized_names`. Canonical identities
remain English; Russian Discord text and image tooltips use the localized names.
The explicit catalog refresh preserves reviewed translations by stable key.
Hero typo correction compares localized phrases as well as English names, keeps
the existing confidence and ambiguity thresholds, and requires exact matching
for names shorter than four normalized characters. Maps use exact phrase matching. Word ordering groups OCR bounds by line center
before sorting left to right, avoiding reversal from differing Cyrillic letter heights.
Russian native OCR is checked with synthetic scoreboard probes; these do not
replace real Russian scoreboard screenshots or establish recognition for every hero.

Limits: real-game capture, every hero/skin, ultrawide framing, and OCR languages
beyond the tested English/Russian cases still require validation. Native OCR
alone cannot reliably read every italic nickname. Ambiguous fields remain
unset, with manual controls available. The initial implementation targets the
Windows application; macOS/CrossOver does not provide these Windows OCR APIs.

Performance: the capture worker and OCR helper run below normal Windows priority.
Polling is configurable (default 5 seconds) and stops outside the foreground
Overwatch window or while paused. OCR is sequential, with no overlay rendering
or continuous game-frame analysis. A foreground-only Tab rising edge starts an immediate capture and one follow-up
350 ms after it finishes, provided Tab remains held. Release, focus loss, pause,
or configuration changes cancel the follow-up. Holding Tab does not repeat the
burst; ordinary polling resumes at the configured interval. This reads key state
without keyboard hooks or input injection. OCR failures impose a 30-second cooldown.
Two matching scoreboard observations confirm phase and match fields together.

The initial VM measurement showed about
157 MiB for the persistent OCR helper, zero helper CPU in a three-second idle
sample, and roughly 0.2–1.7 seconds for warmed screenshot probes. These are
not live-game FPS or frame-time measurements. RAM minimization is secondary to
avoiding interference with gameplay; FPS must be checked on the user's PC.

Additional supplied screenshots (2026-10-07): the Russian Havana scoreboard
confirms Kiriko, elapsed 6:47, and the configured FRITZ row at E/A/D 4/8/8.
Grayscale, inverted, and shifted-hue variants preserve these readings. Row
refinement uses numeric evidence from multiple columns, so a missed elimination
digit no longer prevents reading that player's nickname. Latin nicknames in a
Russian interface and a dedicated small timer crop can use a lazily started
English OCR helper. Both persistent helpers are released on pause/shutdown.
English recognition reuses its primary helper; there is no per-frame process launch.
The earlier memory measurement describes one helper, not this optional two-helper path.

German end-of-match screens and Spanish team reports are recognized as results,
not live scoreboard state. The Portuguese assembly screen confirms match phase
and Blizzard World but its large condensed Juno/mode titles remain unreadable in
this probe. The private corpus records these reference values separately from
expected conservative unknown fields; it does not claim full Portuguese support.
All six new source images stay in the ignored private fixture directory.

Menu party size: `party.py` reads a small portrait strip anchored to the right edge
and scaled by viewport height. Local corner samples estimate each tile's background;
contrast coverage and horizontal/vertical extent separate full profile artwork from
small social glyphs. Low-confidence strips return unknown. Only recognized menu
navigation and menu/queue scenes can produce a count, and only menu presence displays
it. The count includes the user's own portrait, confirms twice, is cleared on phase
changes, and expires after max(30 seconds, 3 polling intervals). Recognition disabled
or custom state text suppresses the automatic label. No Discord join/invite metadata
or invented maximum party capacity is advertised. Tested source strips cover solo,
duo and trio, plus inverted/grayscale/shifted-hue variants. An artificial ultrawide
canvas verifies right-edge anchoring; this is not proof of a live ultrawide UI.
Ambiguous artwork and unsupported layouts can leave party size unknown.
