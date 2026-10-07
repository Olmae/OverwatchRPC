"""Daily, validated catalog refresh with an atomic offline cache."""
from copy import deepcopy
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import tempfile
import time

from .catalog import validate_catalog
from .updates import request_bytes

HEROES_URL = "https://overwatch.blizzard.com/en-us/heroes/"
MAPS_URL = "https://overfast-api.tekrop.fr/maps"
CACHE_TTL = 24 * 60 * 60


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


def refresh_catalog(previous, cache_path, force=False, fetch=request_bytes, now=None):
    now = time.time() if now is None else now
    path = Path(cache_path)
    if not force:
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            checked = cached["checked_at"]
            validate_catalog(cached["catalog"])
            if cached.get("schema") == 1 and type(checked) in (int, float) and 0 <= now - checked < CACHE_TTL:
                return None
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass
    parser = HeroParser()
    parser.feed(fetch(HEROES_URL).decode("utf-8"))
    maps = json.loads(fetch(MAPS_URL))
    heroes = parser.heroes
    if len(heroes) < min(40, len(previous["heroes"])) or not isinstance(maps, list) or len(maps) < min(30, len(previous["maps"])):
        raise ValueError("Incomplete roster response; keeping the existing catalog")
    stamp = datetime.fromtimestamp(now, timezone.utc)
    incoming = {"heroes": heroes, "maps": maps, "as_of": stamp.date().isoformat()}
    validate_catalog(incoming)
    result = deepcopy(previous)
    for kind in ("heroes", "maps"):
        by_key = {row["key"]: row for row in result[kind]}
        for row in incoming[kind]:
            old = by_key.get(row["key"], {})
            merged = {**old, **row}
            # Reviewed local translations survive source metadata changes.
            if old.get("localized_names"):
                merged["localized_names"] = deepcopy(old["localized_names"])
            if kind == "heroes":
                merged["image_available"] = True
            elif row["key"] not in by_key or row.get("screenshot") != old.get("screenshot"):
                merged["image_available"] = True
            by_key[row["key"]] = merged
        result[kind] = sorted(by_key.values(), key=lambda row: row["name"])
    result.update(as_of=incoming["as_of"], retrieved_at=stamp.isoformat(), sources=[HEROES_URL, MAPS_URL])
    validate_catalog(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix="catalog-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"schema": 1, "checked_at": now, "catalog": result}, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return result
