# Artwork and data attribution

The transparent Overwatch logo was supplied by the maintainer from
[Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Overwatch_circle_logo.svg)
on October 7, 2026. `overwatch-logo.svg` preserves that original vector source.
The Discord PNG is rendered at 1280 x 1280 with alpha transparency; the window,
tray and executable icons use transparent raster versions of the same source.
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
