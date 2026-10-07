# Artwork and data attribution

The transparent fallback Overwatch logo is an unchanged PNG export of Blizzard's
[official favicon](https://static.playoverwatch.com/images/favicon.988844a2b97828442775a674abf32ada4f722334.ico),
retrieved on October 7, 2026. It replaces the legacy Discord asset's white square.
The original favicon is 31 x 31 pixels; Discord may soften it when scaling.

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
