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
