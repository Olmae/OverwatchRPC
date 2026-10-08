# Artwork and data attribution

The transparent Overwatch logo was supplied by the maintainer from
[Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Overwatch_circle_logo.svg)
on October 7, 2026. `overwatch-logo.svg` preserves that original vector source.
The Discord PNG is rendered at 1280 x 1280 with alpha transparency and a white
and orange treatment for dark backgrounds.
The logo and associated trademarks belong to Blizzard Entertainment.

Hero portraits are resized from the official Blizzard Overwatch hero roster.
Map screenshots and metadata are provided by the MIT-licensed
[OverFast API](https://github.com/TeKrop/overfast-api).

Overwatch, its characters, map artwork and associated marks belong to Blizzard
Entertainment. These images are not covered by the GPLv3 license of this project's
source code. This is an unofficial, noncommercial fan companion, unaffiliated with
Blizzard or Discord. No ownership of game artwork is claimed.

`catalog.json` records original image URLs, source URLs and retrieval time.
The bundled small images allow the interface to work without network downloads.
Discord uses the original HTTPS hero portrait URL when the user enables it;
local files cannot be used as Discord Rich Presence assets.

`assets/tab-portraits` contains separate scoreboard illustrations used only for
local recognition. Thirty-five exported illustrations come from
https://github.com/Pukima-MacroDeck/Icons-Overwatch-HeroIllustrations at revision
`a58b07279cffe506f3a4fa1c36c71d6316afa0e2`; `sources.json` records individual
source URLs and SHA-256 hashes. Four additional portrait-only crops (Juno,
D.Mon, Doctrine and Ramattra) come from screenshots supplied by the maintainer.
These crops contain no account names or statistics. They remain Blizzard game
artwork and are not covered by this project's code license.
`assets/mode-icons` similarly contains only four scoreboard header glyphs from
maintainer-supplied screenshots: Control, Escort, Hybrid and Push.
`tests/fixtures/tab-portraits` and `tests/fixtures/mode-icons` contain isolated
portrait/header crops from separate supplied frames for regression checks.
They contain no player names; Blizzard retains ownership of the game artwork.

Catalog cutoff: 2026-10-06. Heroes were checked against Blizzard's live roster and
the official October 6 patch, including Doctrine, which was absent in the API
hero list at retrieval. Map catalog follows OverFast's 59 entries, including
Arcade, Stadium, practice and Workshop entries. Seasonal duplicates and current
ranked rotations are not represented as separate maps; an editable map field
supports unlisted variants. Sources can change; updating this snapshot requires
an explicit maintainer review of the requested cutoff.

The small `assets/digits` templates and `tests/fixtures/count-*.png` cells were
extracted from Overwatch scoreboard screenshots supplied by the user for local
recognition work. They contain only digits. The original game UI remains
Blizzard Entertainment's property; it is not covered by the project's code license.

Russian hero names were retrieved from Blizzard's official Russian hero roster
on 2026-10-07: https://overwatch.blizzard.com/ru-ru/heroes/. The catalog records
the source hash. Russian map names are an initial curated subset awaiting broader
in-game screenshot validation; they are not a complete localization of the roster.

`tests/fixtures/party-*.png` contain cropped menu headers from user-provided
Overwatch screenshots for portrait-strip regression checks. They contain no player
names. The game interface and profile artwork retain their original ownership;
they are not covered by the code's GPL license.

The original OWRPC orange and ivory relay mark (`owrpc-logo.png` and
`owrpc-logo-source.png`) is the application identity. Window, tray and
executable icons use resized versions of this approved mark.

The README cover combines the original OWRPC mark, an English native desktop
capture, and a Discord activity screenshot supplied by the maintainer on
October 8, 2026. Its heading uses stylized lettering inspired by Overwatch;
no official Overwatch font file is bundled. The cover translates the Discord
card header to English. Activity values in these documentation images are
illustrative and do not represent measured recognition accuracy or performance.
The original captures are stored separately under `docs/screenshots`.

Scoreboard illustration templates in `tab-portraits` retain Blizzard Entertainment's
ownership and are not covered by the code license. The initial 35 exports are from
https://github.com/Pukima-MacroDeck/Icons-Overwatch-HeroIllustrations ; 15 additional
2D exports are from https://github.com/drippinghere/overwatch-hero-icons . Four
portrait-only crops were supplied by the maintainer. `sources.json` records pinned
source URLs and original SHA-256 hashes. Mode templates and isolated regression
fixtures also contain only cropped game artwork from maintainer screenshots.

`clock-digits` contains isolated masked timer glyphs from maintainer-supplied
Overwatch scoreboard screenshots, with source and transformation records in
`sources.json`. `tests/fixtures/clock` contains cropped scoreboard headers without
player identities. These game UI extracts retain Blizzard Entertainment's
ownership and are not covered by the code license. Full source frames remain
outside distributable assets.
