"""Refresh official Blizzard hero names/portraits and OverFast map metadata.

Run explicitly; the desktop app never downloads assets or refreshes catalogs.
Blizzard artwork remains Blizzard's property, not GPL-licensed project code.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
HEROES = "https://overwatch.blizzard.com/en-us/heroes/"
MAPS = "https://overfast-api.tekrop.fr/maps"
PATCHES = "https://overwatch.blizzard.com/en-us/news/patch-notes/"


def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": "OWRPC-Catalog/2.0"}), timeout=30) as r:
        return r.read()


class HeroParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.heroes, self.current, self.heading = [], None, False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and "hero-card" in d.get("class", "").split():
            self.current = {"key": d["id"], "name": "", "role": d.get("data-role", ""),
                            "subrole": d.get("data-subrole", ""),
                            "stadium": d.get("data-stadium") == "true",
                            "source": "https://overwatch.blizzard.com" + d["href"]}
        if self.current:
            if tag in ("img", "blz-image") and "heroCardPortrait" in d.get("class", ""):
                self.current["portrait"] = d["src"]
            elif tag == "h2":
                self.heading = True

    def handle_data(self, data):
        if self.current and self.heading:
            self.current["name"] += data

    def handle_endtag(self, tag):
        if tag == "h2":
            self.heading = False
        if tag == "a" and self.current:
            if self.current["name"] and self.current.get("portrait"):
                self.heroes.append(self.current)
            self.current = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", required=True, help="Content cutoff in YYYY-MM-DD")
    parser.add_argument("--heroes-html", type=Path)
    parser.add_argument("--maps-json", type=Path)
    args = parser.parse_args()
    datetime.strptime(args.as_of, "%Y-%m-%d")
    hero_raw = args.heroes_html.read_bytes() if args.heroes_html else fetch(HEROES)
    maps_raw = args.maps_json.read_bytes() if args.maps_json else fetch(MAPS)
    parsed = HeroParser()
    parsed.feed(hero_raw.decode("utf-8"))
    maps = json.loads(maps_raw)
    if len(parsed.heroes) < 40 or len(maps) < 30:
        raise RuntimeError("Unexpected source format; refusing to overwrite catalog")
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    catalog = {"as_of": args.as_of, "retrieved_at": datetime.now(timezone.utc).isoformat(),
               "sources": [HEROES, MAPS, PATCHES],
               "source_hashes": {"heroes": sha256(hero_raw).hexdigest(), "maps": sha256(maps_raw).hexdigest()},
               "scope": "Official live hero roster; OverFast standard, Arcade, Stadium and Workshop maps. Not a ranked map rotation or a list of every seasonal variant.",
               "heroes": sorted(parsed.heroes, key=lambda x: x["name"]),
               "maps": sorted(maps, key=lambda x: x["name"])}
    # Prepare every image before replacing catalog, avoiding partially refreshed data.
    def thumbnail(item):
        from PIL import Image
        kind, row = item
        url = row["portrait" if kind == "heroes" else "screenshot"]
        folder = assets / kind
        folder.mkdir(exist_ok=True)
        target = folder / (row["key"] + ".png")
        try:
            image = Image.open(BytesIO(fetch(url))).convert("RGBA" if kind == "heroes" else "RGB")
            image.thumbnail((128, 128) if kind == "heroes" else (320, 180))
            image.save(target, optimize=True)
            row["image_available"] = True
        except Exception as exc:
            row["image_available"] = False
            row["image_error"] = str(exc)
            if target.exists():
                target.unlink()
            print(f"WARNING: {kind}/{row['key']}: {exc}")
        return row["key"]
    items = [(kind, row) for kind in ("heroes", "maps") for row in catalog[kind]]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for key in pool.map(thumbnail, items):
            print(key)
    (assets / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(parsed.heroes)} heroes and {len(maps)} maps")


if __name__ == "__main__":
    main()
