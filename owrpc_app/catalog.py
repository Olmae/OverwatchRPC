import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse


def resource_dir():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "assets"


def validate_catalog(catalog):
    if not isinstance(catalog, dict) or not isinstance(catalog.get("as_of"), str):
        raise ValueError("Invalid catalog")
    for kind, limit, artwork in (("heroes", 256, "portrait"), ("maps", 512, "screenshot")):
        rows = catalog.get(kind)
        if not isinstance(rows, list) or not 1 <= len(rows) <= limit:
            raise ValueError("Invalid catalog size")
        keys = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Invalid catalog entry")
            key, name = row.get("key"), row.get("name")
            if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", key) or key in keys:
                raise ValueError("Invalid or duplicate catalog key")
            keys.add(key)
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100 or any(ord(c) < 32 for c in name):
                raise ValueError("Invalid catalog name")
            url = row.get(artwork)
            if not isinstance(url, str) or len(url) > 512:
                raise ValueError("Invalid artwork URL")
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("Artwork must have a public HTTPS URL")
            localized = row.get("localized_names", {})
            if not isinstance(localized, dict) or any(not isinstance(v, str) or len(v) > 100 for v in localized.values()):
                raise ValueError("Invalid localized catalog names")
    return catalog


def load_catalog(cache_path=None):
    bundled = json.loads((resource_dir() / "catalog.json").read_text(encoding="utf-8"))
    if cache_path is None:
        return bundled
    try:
        cache = json.loads(Path(cache_path).read_text(encoding="utf-8"))
        if cache.get("schema") != 1:
            return bundled
        catalog = validate_catalog(cache["catalog"])
        # New bundled entries and reviewed translations take precedence over
        # an older cache after an application upgrade.
        for kind in ("heroes", "maps"):
            by_key = {row["key"]: row for row in catalog[kind]}
            for row in bundled[kind]:
                if row["key"] not in by_key:
                    by_key[row["key"]] = row
                elif row.get("localized_names"):
                    by_key[row["key"]]["localized_names"] = row["localized_names"]
            catalog[kind] = sorted(by_key.values(), key=lambda row: row["name"])
        return catalog
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return bundled
