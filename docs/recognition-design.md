# Automatic recognition

Scoreboard hero recognition first compares the large illustration above the
own-hero name against 54 bundled local templates (50 exported game illustrations
and four reviewed maintainer crops). It runs only after scoreboard header
evidence, checks five known panel anchors and requires grayscale correlation
at least 0.86 with a 0.10 lead over the runner-up. Transparent template margins
are excluded. A strong match skips hero-name OCR; unknown or ambiguous art uses
the existing title fallback. The two-observation confirmation still applies.
There are no new runtimes, network requests or learned model dependencies.
All 54 catalog heroes now have local templates. The 15 previously missing 2D
illustrations came from https://github.com/drippinghere/overwatch-hero-icons at
commit `f4ddc06cf07d0741c40beda77eeeb1a81a99a279`. Source URLs and original
hashes are recorded in `assets/tab-portraits/sources.json`. The expanded set
passes 111 unit tests and the same 35 private native screenshot cases. A local
render of each template at the known panel anchor additionally checks resource
coverage and ambiguity; this is not independent live evidence for every hero.
Screenshot-derived templates are calibration examples; validation
on the same image is not independent live evidence.

Control, Escort, Hybrid and Push header glyphs provide a second local source
for map type. Binary overlap must exceed 0.80 with a 0.12 ambiguity margin;
unknown glyphs fall back to text. Named playlists such as Mystery Madness take
precedence over the underlying Control glyph. New Queen Street has a reviewed
Russian alias and bounded fuzzy matching only in confirmed scoreboard header
regions. Clock cleanup preserves trailing map words beside long playlist names.
Additional research candidates, not enabled as recognition templates:
https://commons.wikimedia.org/wiki/File:Flashpoint_map_icon.svg (a vector
recreation), and the menu UI collection at
https://www.spriters-resource.com/pc_computer/overwatch2/asset/597730/ . These need
comparison with native scoreboard glyphs. The alternate full hero art sheet is
https://www.spriters-resource.com/pc_computer/overwatch2/asset/597452/ . The found
individual exports were sufficient for the missing hero templates; full UI
screenshots with account names are not bundled.

Local 16:9 follow-up (2026-10-08): ordinary window captures strip verified
non-client borders before applying normalized OCR and party coordinates. Unknown
capture dimensions fall back to the visible foreground client rectangle.
Practice-range hero titles use the wide panel at 16:9, while ultrawide panels
retain their compact crops. The supplied 1584x891 viewport reads Junkrat and
the practice timer 1:33; both supplied solo menus read party size 1 using native
Windows OCR. Four additional 16:9 practice scoreboards now read Juno, D.Mon,
D.Va and Mei, with elapsed times 21:23, 21:55, 22:15 and 22:31 respectively.
Overlapping OCR passes deduplicate headers without regard to letter case;
otherwise duplicate DMG headers can prevent scoreboard detection altogether.
Unknown short titles use bounded native-size Cyrillic/Latin and enlarged Latin
fallbacks with a gentler italic correction. The timer crop includes both minute
digits, with a narrower fallback for unreadable one-digit-minute clocks. A fifth
supplied frame also reads Doctrine and 34:30. These screenshot checks do not
establish live recognition latency.

The displayed game timer is synchronized from two consistent scoreboard reads,
using frame capture time rather than OCR completion time. Subsequent confirmed
reads can correct an initial estimate or a round clock reset without clearing
cumulative E/A/D or treating the round as a new match. An isolated inconsistent
timer read is ignored. Discord continues counting between observations, so
pauses and unseen clock changes cannot be reflected until another valid read.
Confirmed OCR clocks must also start no earlier than the game process itself
(with three seconds of tolerance). This rejects repeated label/digit merges,
including the observed 756:16 misread, without imposing an arbitrary match-length
limit. New-match recovery never applies an unconfirmed raw clock directly.
Buffered scoreboard diagnostics log only the small title/timer text regions;
they do not save screenshots or the player table.

The last confirmed party count also remains visible in menus while the game is
not foreground. It is replaced by a confirmed new count and cleared at the
existing match-exit/game-close boundaries; it does not disappear after 30 seconds
spent looking at the application. A first valid menu count schedules one prompt
confirmation frame before normal polling resumes.

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
changes, and keeps the last confirmed fields on unknown frames. E/A/D retains
the last confirmed scoreboard values until another confirmed read or match exit,
and is never inferred from another player's row. A nickname can be learned from
the HUD; an explicit nickname in Advanced is recommended. Tab is not pressed by
the app. An unseen hero switch cannot be confirmed.

If menu/queue frames are missed between matches, two matching observations of
a different map recover the boundary while already in match phase. Clear the
previous hero, mode, E/A/D and timer before applying fields confirmed for the
new map; retain the last known party. A same-map restart additionally requires
confirmed zero E/A/D, a scoreboard timer at 0–10 seconds and a prior match at
least 60 seconds old with nonzero counters. A round timer resetting alone does
not create a new match. The supplied Grimsvotn scoreboard validates D.Mon,
Escort, the reviewed Russian map alias and elapsed 0:00 using real Windows OCR;
its own E/A/D row remains unconfirmed and must not be inferred as zero.

Transition screenshots also cover waiting for the group to choose roles,
map voting, its winning-map screen, hero selection/team assembly, the centered
final defeat banner and post-match player cards. Results form a separate phase
and stop the timer and E/A/D immediately after phase confirmation; recognized
map information remains contextual, without advertising active play. The winning
map remains available when entering hero selection. Two observations still
confirm phases and scene labels; a brief unseen transition cannot be inferred.
The centered final banner requires large text in its specific screen area;
round-complete notices and chat text do not establish a completed match.

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
for names shorter than four normalized characters. Maps use exact phrase matching outside confirmed scoreboard headers. Word ordering groups OCR bounds by line center
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
or continuous game-frame analysis. A foreground-only Tab rising edge starts a
separate capture thread's bounded burst: at most three in-memory frames, after
150 ms of opening animation and at least 250 ms apart. OCR processes them
sequentially even after Tab is released or the player opens the app. Only
foreground game pixels are captured; focus loss prevents new captures without
discarding verified pending frames. Pause, configuration changes and the first
valid capture of a new burst discard older work. A brief tap that captures
nothing cannot cancel the previous burst. Frames expire after 20 seconds to
allow bounded cold OCR startup without keeping old frames indefinitely.
Holding Tab does not repeat the burst; ordinary polling resumes after release.
No screenshots are written to disk. This reads key state
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
navigation and menu/queue scenes can produce a count. The count includes the user's
own portrait and confirms twice. The last confirmed count remains visible in menus, queue, map voting
and match until a confirmed replacement or a match-exit/game-close boundary. Leaving a match clears it until a new menu observation. Recognition disabled
or custom state text suppresses the automatic label. No Discord join/invite metadata
or invented maximum party capacity is advertised. Tested source strips cover solo,
duo and trio, plus inverted/grayscale/shifted-hue variants. A supplied 3440x1440
five-player strip covers the mixed layout with two wide and three compact
profile tiles; all five profiles and the absent sixth slot must be recognizable.
An artificial ultrawide
canvas verifies right-edge anchoring; this is not proof of a live ultrawide UI.
Ambiguous artwork and unsupported layouts can leave party size unknown.

Windows PC validation, 2026-10-07: Russian interface, 3440x1440 (21:9),
borderless game window. PrintWindow returned an entirely black image on this PC.
Capture now falls back to the visible game client rectangle, checking foreground
identity before and after capture. No capture is saved by the application.

Real Windows OCR on supplied screenshots identifies Reaper on two practice
scoreboards and hero selection, Ramattra on hero selection and a later scoreboard,
Ilios and Control on the match scoreboard, and own E/A/D 10/0/1. Smaller padded
title crops preserve condensed Cyrillic glyphs. Practice headers need a lower,
context-specific search area. HUD ammo templates supplement missed OCR digits.
The supplied menu portraits identify solo and duo; the user also observed the
live change from one to two players. These do not establish all-avatar support.

Map voting has its own phase, confirmed with the same two-observation rule.
Candidate map names are deliberately ignored. The supplied voting result now
identifies the winning map; assembled-team frames identify hero selection.
The initial zero-stat Ramattra scoreboard now identifies the hero through its
portrait; its own row remains unconfirmed. The 2026-10-08 build passes 35 private
16:9 and 21:9 screenshot cases with real Windows OCR, including New Queen Street
(Push), Nepal (Mystery Madness), and the supplied practice hero frames. Source
screenshots and detailed OCR output stay in the ignored private corpus. Live
rechecks and FPS comparisons remain required after rebuilding.

Ultrawide nickname crops extend to x=0.385 rather than 0.36. On the supplied
3440x1440 Mystery Madness Torbjörn scoreboard, the old crop clipped the last
letters of the configured nickname and rejected the own row. The expanded crop
reads own E/A/D 1/0/1 without lowering nickname confidence or guessing a row.
The timer remains unreadable in this particular frame.

English practice follow-up, 2026-10-09: zero-stat rows can be absent from the
initial numeric OCR pass. The row anchor now accepts both DMG and УРОН headers,
then requires the configured nickname before digit-template fallback. English
practice headers can be re-read in Latin with Russian OCR configured. The
supplied D.Mon and D.Va frames read E/A/D 0/0/0 with either engine language.
Pillarboxed practice headers move independently of the centered scoreboard;
the English clock crop anchors to RANGE. D.Va reads 2:03; the condensed 0:29
in the D.Mon frame remains unreadable and is not substituted with an estimate.

Geometry and numeric clock follow-up, 2026-10-09: a bounded grayscale scan locates
the neutral scoreboard header after the scoreboard tab has been recognized.
Numeric column offsets use the observed table edge and viewport height, with
separate practice and match layouts. This skips header-letter OCR when geometry
is unambiguous; other frames retain the text-based fallback. Nickname crops and
the first-row anchor follow that band, including initial all-zero scoreboards.
The configured nickname must still match before any own E/A/D is accepted.

The numeric clock reader checks a colon's two dots, one to three minute digits,
two second digits, glyph confidence, and spacing. It straightens the italic
glyphs and supports changed hues; a bright monochrome pass is conservative and
can abstain. Unreadable digits cannot be dropped from the beginning of minutes.
It is used only after scoreboard recognition. A confirmed numeric reading skips
extra clock OCR passes; otherwise the existing OCR clock fallback remains.
Capture-time consistency and the game-process-age bound still guard live timer
updates. The supplied 0:42 and 0:29 failures now read correctly, as does the
pillarboxed 2:03. The 0:42 frame is held out from clock template extraction;
the 0:29 case is partly calibration because its isolated 9 is a source template.
The private corpus distinguishes improved expected readings from former unknowns.
Recognition logs include text/visual extraction and parsing durations separately.
Independent field confirmations and match/menu resets already exist in runtime;
these changes retain that behavior. Screenshot timings are not live FPS results.

The English 2561x1440 Freja scoreboard supplied later on 2026-10-09 reads
`ESCORT | GRIMSVÖTN`: the game omits the catalog's Watchpoint prefix and OCR
can preserve only one of the two accents. The catalog now includes the observed
English display name Grímsvötn. Exact phrase matching folds Unicode diacritics
while preserving word boundaries and ambiguity rejection. This also works with
older catalog caches because bundled localized names take precedence.
A twice-confirmed scoreboard mode incompatible with Practice clears a retained
Practice Range state even when the next map is unreadable, preventing an
`Escort · Practice Range` combination after a missed transition. A single
observation is insufficient. Independent new hero/KDA values can then update.


## Local failure evidence

Use Additional → Recognition diagnostics to enable local failure captures and
optional minute snapshots, then save settings. Recording is disabled by default.
The same flags can be configured in `%APPDATA%\OWRPC\settings.json` while closed.

Incomplete scoreboard readings, hero-selection readings, missing menu party counts,
and unrecognized buffered Tab frames save a PNG and a JSON reason under
`%APPDATA%\OWRPC\recognition-failures`. Ordinary HUD frames without Tab do not
trigger recording. Screenshots can include visible game chat and player names;
there is no automatic upload. Metadata omits nickname and raw OCR text.

Each scene/missing-field combination is limited to one capture per minute.
The recorder keeps at most 40 frames and 100 MB including metadata, pruning the
pairs by diagnostic value: routine minute samples first, unrecognized Tab frames
next, missing fields in recognized scenes next, and manual snapshots last.
Within each priority, the oldest pairs are removed first. Disk errors are logged
and do not stop recognition.

Set `recognition_minute_snapshots` to `true` alongside diagnostics to also
record an ordinary game frame approximately once per minute, even when no
expected field is missing. This uses existing foreground game captures and
pauses while the game is not foreground; it does not capture other applications.
Periodic samples and failures share the same retention limits. JSON metadata
marks minute samples with `periodic: true`.


## Transition confirmation and live diagnostics

Strong phase or map changes request one extra foreground reading after 250 ms.
Two observations remain mandatory; extra polls are limited to one per five seconds.
Confirmed changes schedule Discord delivery with at least three seconds between sends,
instead of waiting for the normal presence interval. Summary / Rewards ends a match
without requiring a Competitive label. Centered Assemble Your Heroes is a match HUD
cue when health counters are present, not the left-hand Heroes menu navigation.

The Additional page shows the last captured frame time, last confirmation time,
processing duration, scene, missing expected fields and confirmed presence values.
A missing value in a new frame is distinguished from the retained confirmed value.
Background, paused, unavailable OCR and stopped-game states remain visible alongside
this snapshot. These times describe recognition, not a Discord delivery receipt.

Before Tab, English assembly screens provide map names and a verified-player portrait
fallback. The fallback currently supports the observed 16:9 assembly layout; it requires
an unambiguous nickname match in the five player-card positions. Existing Tab artwork
is supplemented with `assets/assembly-ramattra.png`, a portrait-only crop of the
maintainer-provided Midtown screenshot from 2026-10-09. It contains no nickname or chat.
The same reference recognizes the independently supplied Grímsvötn assembly frame.
Both use correlation >= .86 and a hero margin >= .15. Unknown illustrations abstain.
This is initial assembly coverage, not a claim that every hero, skin, aspect ratio or
loading-screen layout is supported. Loading map votes retain their existing handling.


## Explicit diagnostic snapshot

Right Alt+] captures the verified foreground Overwatch client immediately on
its rising edge, independently of OCR polling and Tab bursts. A held shortcut
captures once. The tray Save game frame item queues a capture until Overwatch
returns to the foreground. Requests never capture another application.
Two manual frames can wait in memory; accepted requests are spaced by two seconds.
The recognition worker saves PNG + JSON (`manual: true`), bypassing automatic
recording switches and minute throttles but retaining the same disk limits.
If OCR fails, the original game image is still saved with an unknown detection.
Manual samples do not confirm or change presence state. A tray notification
confirms disk saving. A quiet 140 ms sound also confirms a successful manual
save; automatic frames and failed saves remain silent. Playback is asynchronous
and does not change system volume. Nothing is uploaded automatically.


## Missing friendly rows and compact queue banners

Friendly nickname rows are also anchored to the neutral scoreboard header when
native OCR misses every single-digit counter. This covers a non-first player row
at 0/0/0 and comma-separated totals on expanded perk tables. Native-size padded
nickname OCR is a fallback only when the normal pass cannot identify the player;
ambiguous nicknames still abstain. The numeric crop starts at the first statistic
column, excluding perk artwork. Missing counters retain independent digit checks.

English assembly accepts Ready alongside the assembly heading and reads the
selected roster label separately from the large fading hero title. Compact blue
Role Queue banners require both a recognized playlist and a timer. A bottom-right
Stay as Team footer identifies post-match screens even when chat hides the highlight
title. Ordinary chat mentions outside that footer do not end a match.


## Ambiguous scoreboard digits

When a verified player row is missing a counter, the shape reader checks the
individual counter crop. If its confidence is insufficient, native OCR retries
that isolated, padded crop. Only one exact numeric token of one to three digits
is accepted; ambiguous, split or nonnumeric tokens abstain. This fallback does
not relax shape thresholds or the runtime requirement for repeated observations.

The neutral scoreboard band is located even when the Scoreboard tab caption
is absent or unreadable during a transition. Menu/search exclusions still run
first. Without a tab caption, a real DMG heading must also be read inside
the band to reject similar bars on hero selection screens. Player ownership
still requires an unambiguous nickname match.
The reviewed `digits/1-eichenwalde.png` is a binary 12x20 glyph from the
maintainer-provided 2026-10-12 frame; it contains no names or chat. Alternatives
are scored per digit, preserving the .28 error and .035 ambiguity thresholds.


## Centered Tab and expanded assembly cards

The neutral table locator includes the centered scoreboard shown before the
right hero panel appears. The nickname range follows a unique first statistic
header, remains to its left, and retains the existing confidence and ambiguity
gates. No hero is inferred from question-mark portraits on that loading frame.
English assembly map captions that already resolve are not re-read through a
crop that could clip their first word. Unresolved captions get a complete crop.
The observed 21:9 expanded player-card layout can read a verified nickname and
match that card's portrait using the existing references and .86/.15 gates.
This does not claim coverage of all 21:9 assembly variants or skins.


## Match stages during map and hero selection

English SELECTING MAP and VOTE FOR A MAP headings identify map voting before
Tab. The countdown variant can also use the complete central vote instruction;
clipped or unrelated chat words are insufficient. Candidate map cards and their
highlight are never treated as the winning map. Two observations still confirm
phase changes. Discord and the current-activity header present map voting, map
loading and hero selection as In match, with the specific stage underneath.
Canonical internal phases remain separate so voting clears the previous hero,
map, counters and timer. The selected loading map survives into hero selection.
The observed 21:9 Ready layout uses its own nickname and portrait bounds, with
the same ownership check, portrait references and .86/.15 confidence gates.
The supplied Junkertown frame and independent Eichenwalde / King's Row captures
are included in the private OCR corpus. No screenshots are uploaded.

The additional `assembly-ramattra-highlight.png` reference is a portrait-only
crop of the maintainer-provided 2026-10-12 Eichenwalde frame (205407). The adjacent
205421 frame is held out from extraction. Native nickname retries are limited
to an unreadable owner; multiple OCR spellings can merge within one player slot,
while matching names in different slots still abstain.

The 2026-10-15 practice-range selection captures add portrait-only assembly
references for Anran, Echo, Freja, Doctrine, Lúcio and Hazard. Each reference is
a 144px square at x=.300 of the 3440px viewport and y=.478 of its 1440px height;
names and chat are excluded. These are standard player-card portraits even
when the large model uses a different skin. The six source captures remain in
the private corpus, with additional resize and brightness checks; they are not
independent held-out captures. This expands verified assembly coverage to seven
heroes, including Ramattra, rather than claiming real-frame coverage of all 54.

Continue identifies the compact practice assembly layout, as Ready does in a
match. A confident nickname-owned portrait takes precedence over a stale title
only in hero selection. Existing ownership, correlation and ambiguity gates
remain unchanged. When ownership or the portrait cannot be verified, the large
title and the highlighted grid label are text fallbacks. The grid label can be
in any role column. Compact nameplate retries use tighter bounds only after
the normal ownership reads fail. Hero galleries never invoke this override.

Queue playlist extraction reads the left SEARCHING detail on collapsed English
menus before returning from the header-only OCR path. Expanded dropdowns use
the line containing QUEUE / РОЛЯМ, excluding navigation tabs on other lines.
Generic top-panel mode names are ignored when menu navigation is present;
timed side banners keep their existing priority. A maintainer-provided solo
Competitive Role Queue capture (2026-10-15, 21:37) is a private regression case.

English/Russian interface OCR now follows multiple fixed navigation labels,
paired scoreboard captions, or paired selection controls. It retains the
confirmed language between frames and can switch back; unconfirmed probes
are discarded. An isolated word or a player name cannot change the interface
language. A separate lazy Russian OCR bridge avoids restarting the configured
English bridge. Other configured OCR languages keep their existing behavior.
Detected changes and the language used are recorded in local diagnostics.

Own-name OCR selects its alphabet from the configured/detected nickname,
independently of the game UI: Cyrillic or mixed Cyrillic/Latin names use the
Russian bridge, Latin names use the English bridge. Confidence and duplicate
owner checks are unchanged. Private checks include the supplied Russian menu
with English OCR configured, a Russian-to-English-to-Russian menu sequence,
and an English scoreboard with a synthetic Cyrillic own-name overlay and KDA.

Russian practice/assembly screens now run the same nickname-owned portrait
checks as English screens, and highlighted grid names use the detected UI
language. Kiriko adds an eighth verified assembly reference, extracted from
the maintainer's 2026-10-15 22:56 screenshot (portrait only, same compact bounds
as above). The independently recorded 225603 frame is held out from extraction.
Initial language probing also covers selection controls without requiring a
previous menu observation, so starting directly on Russian selection works.

## HUD ability and weapon fallback

The 2026-10-16 matcher bundles 276 current ability/weapon images for 54 heroes.
Public Blizzard CDN URLs, ability names, hero mappings and SHA-256 hashes are
recorded in `assets/hud-icons/sources.json`; mappings were retrieved through
OverFast API. No network request is needed at recognition time. The older
Pukima ability collection was researched but is not bundled for HUD matching.

The matcher extracts dark glyphs enclosed in neutral ready-ability tiles in
the bottom-right HUD, preserving disconnected white interior details. Bounds
follow viewport height for 16:9 and 21:9. Colored cooldown tiles are excluded.
Normalized binary shapes allow a one-pixel alignment tolerance. Two distinct
abilities on different tiles must jointly identify one hero, each at least
.78, strongest at least .86, mean at least .82, with .12 mean margin over the
next hero. Multiple crops of one weapon count as one slot. If two abilities
are unavailable, a weapon may support a uniquely matching .86 ability; the
joint weapon path additionally requires .09 hero margin and .12 individual
ability margin. A lone weapon, lone ability, duplicate ability or conflicting
pair is insufficient.

Application integration requires a verified own-name plate, independently of
the game UI alphabet. It can fill a detected HUD's hero or confirm an otherwise
unknown screen from the matching icon pair when health/ammo OCR failed.
Recognized statistic headings exclude that recovery path. Replay/spectator
headings abstain. Menu, queue, results, selection and scoreboard paths do not
use this fallback. Existing two-observation confirmation remains required.
HUD icons can replace an existing hero after two positive observations, so an
ordinary Mei-to-Mauga swap updates without opening Tab. A first different hero
requests a prompt confirmation. Known Echo is protected from HUD replacements
when copied abilities are visible. This conservative fallback
does not claim universal spectator/replay detection when headings are hidden.

Real screenshots verify Reaper, Ramattra, Genji, Mei and Mauga; official templates cover
the other heroes without claiming equivalent real-frame validation. Tests
include separate Ramattra captures, resized/dimmed HUD crops, a simulated
cooldown with Reaper's remaining ability and weapon, wrong own-name, replay
headings, and negative menu/queue/scoreboard integration. Sanitized test crops
contain only the HUD region, with no names or chat. Full captures stay private.

Mei adds a ninth assembly reference from the maintainer's 2026-10-16 00:32:35
capture (portrait only). Fresh Mei selection, Tab, HUD and Mauga HUD captures
are private regression cases. Missing map/mode fields on HUD frames preserve
pending positive observations from selection. Automatic match entry clears an
unconfirmed saved manual mode; unknown mode uses neutral `In match` details.

## Saved-frame review, 2026-10-18

The local review includes all 41 retained captures (manual, failure and six
periodic captures), with 26 additional exact images beyond the previous
95-case corpus. Historical sidecars are audit inputs, not ground truth; scene,
hero, map and timer corrections were checked against the visible captures.

Runasapi's Russian caption `РУНАСАПИ` now resolves through its reviewed
localization. Challenge navigation (`DAILY`, `WEEKLY`, `LIFETIME`) is a menu;
`STADIUM COMPETITIVE` navigation cannot borrow the system clock from the other
corner as queue evidence. Playlist and timer must share the banner bounds.
Role selection before starting a search is also a menu.

Compact scoreboard captions have a tight fallback that excludes adjacent TIME
text, with the alphabet selected from fixed scoreboard captions, not nicknames.
This covers the dim Ilios and Russian Busan frames. Three sanitized glyph-only
clock references (6 from Nepal 000210, 3 from Ilios 002853, dim 8 from Ilios
003712, 2026-10-15 captures) retain existing shape/margin checks. The separate
Nepal 000211 and Ilios 003831 captures verify the same digits independently.
Evidence sidecars now include the detected interface OCR language and hero
source, when available, separately from the configured language.

Three further maintainer captures cover Russian map voting and two Doctrine
scoreboards on Rialto (zero counters and 0:00). A cold start on Russian voting
can select the interface alphabet from the complete fixed probability hint in
its bounded center region, even when the condensed voting title is unreadable.
Incomplete hints and player-name regions cannot trigger that language change.
Voting remains `map_vote`; highlighted map candidates and previous-hero icons
are not promoted to confirmed match fields.

## Confirmed field freshness

Match counters remain available until the next reading or match exit. After
120 seconds, the Discord state includes their age in whole minutes instead of
presenting an old scoreboard reading as current. A new confirmed reading removes
that age label. Local preview state refreshes with the timer without reloading
artwork; explicit custom status text still takes precedence.

Two consecutive unreadable hero-selection scenes clear the previous hero, while
keeping the map, timer and match-wide counters. One transient selection frame
does not clear it. A following HUD pair can then confirm a new hero, including
after leaving Echo; copied HUD abilities while Echo remains confirmed continue
to abstain from replacement. Unknown ordinary HUD frames alone do not erase a
hero, since cooldowns and occlusion are not evidence of a swap.

Menu party recognition also accepts a BACK/НАЗАД navigation header after the
scene has been identified as a menu/queue. The same conservative portrait-strip
matcher is used; the social counter is not interpreted as party membership.
The maintainer's 2026-10-18 00:36:40 Esc-menu capture verifies solo, addressing
a stale duo retained when the regular HEROES/SHOP navigation was absent. The
worker still requires two positive membership readings before replacing duo.

## Exact-input OCR cache

Each native OCR bridge caches results for identical RGB pixels at the exact
dimensions submitted to Windows OCR, keyed by language, dimensions and SHA-256.
The cache retains at most 64 regions and 4096 words per bridge; it stores no
source images. Hits return a separate list of immutable Word records. Any
changed pixel, dimensions or language requires a new read. Closing/restarting the
bridge and OCR errors clear it. Empty successful readings can be cached too.
Independent frame capture and two-observation confirmation remain unchanged.

In a four-read static Mauga HUD benchmark on 2026-10-18, warmed reads changed
from 1196–1260 ms to 516–523 ms with identical words. This measures a repeated
still frame, not all live-game frames: moving pixels reduce cache reuse. The
first read still includes bridge startup and is not the warm-cache benchmark.

## Escape-menu boundaries

A BACK/НАЗАД label alone is no longer sufficient to declare menus. The main
escape menu needs bounded profile/settings controls and an Exit Game command.
A Leave Game/Leave Match/Покинуть матч command is instead an unconfirmed
`pause_menu` scene: opening that menu does not prove that the match was left.
The worker retains the confirmed hero, counters and timer until a real boundary.

Three neutral button interiors trigger small menu-control OCR crops, but pixels
alone never classify the scene. Fixed MENU/PROFILE/OPTIONS or Russian equivalents
can identify the interface alphabet, independently of player names. The saved
2026-10-18 00:36:40 Russian menu is checked both as the first frame (configured
English OCR) and after the full corpus; its cold start formerly remained unknown.
