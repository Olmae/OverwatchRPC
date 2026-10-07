from dataclasses import dataclass, fields
from difflib import SequenceMatcher
import time
import re
import unicodedata
from urllib.parse import urlparse
from .i18n import LANGUAGES, resolve_language, tr

PROJECT_URL = "https://github.com/Olmae/OverwatchRPC"

DEFAULT_CLIENT = "583356928688783369"
LEGACY_LARGE_IMAGE = "https://raw.githubusercontent.com/Olmae/OverwatchRPC/main/assets/overwatch-logo.png"
DEFAULT_LARGE_IMAGE = LEGACY_LARGE_IMAGE + "?v=20261007"
PHASES = {"menus": "In menus", "queue": "In queue", "match": "In match"}
MODES = ["Quick Play", "Competitive", "Stadium", "Arcade", "Custom Game",
         "Mystery Heroes", "Mystery Madness: Graveyard Games", "Practice",
         "Capture the Flag", "Deathmatch", "Team Deathmatch", "Elimination", "Payload Race", "Workshop"]


@dataclass
class Settings:
    language: str = "auto"
    client_id: str = DEFAULT_CLIENT
    hero: str = ""
    map_name: str = ""
    mode: str = "Quick Play"
    rpc_interval: int = 15
    minimize_to_tray: bool = True
    start_hidden: bool = False
    autostart: bool = False
    only_when_game: bool = True
    game_process: str = "Overwatch.exe"
    show_timer: bool = True
    large_image: str = DEFAULT_LARGE_IMAGE
    hero_image: str = ""
    menu_image: str = ""
    use_hero_portrait: bool = True
    use_map_art: bool = True
    display_type: int = 0
    button_label: str = ""
    button_url: str = ""
    details_override: str = ""
    state_override: str = ""
    kda_enabled: bool = False
    kda_region: list | None = None
    player_name: str = ""
    check_updates: bool = True
    auto_catalog: bool = True
    ocr_enabled: bool = True
    ocr_interval: int = 5
    ocr_language: str = "eng"
    tesseract_path: str = ""
    map_region: list | None = None
    hero_region: list | None = None

    @classmethod
    def from_dict(cls, data):
        result = cls()
        if not isinstance(data, dict):
            raise ValueError("Settings must be a JSON object")
        for f in fields(cls):
            if f.name not in data:
                continue
            v = data[f.name]
            default = getattr(result, f.name)
            if isinstance(default, bool):
                if isinstance(v, bool):
                    setattr(result, f.name, v)
            elif f.name.endswith("_region"):
                if (isinstance(v, list) and len(v) == 4
                        and all(type(n) is int for n in v)
                        and v[0] >= 0 and v[1] >= 0 and v[2] >= 8 and v[3] >= 8
                        and all(n <= 32768 for n in v)):
                    setattr(result, f.name, v)
            elif isinstance(default, int):
                if type(v) is int:
                    setattr(result, f.name, v)
            elif isinstance(v, str):
                setattr(result, f.name, v.strip()[:500])
        result.rpc_interval = max(15, min(300, result.rpc_interval))
        result.ocr_interval = max(3, min(120, result.ocr_interval))
        result.display_type = result.display_type if result.display_type in (0, 1, 2) else 0
        if not result.client_id.isdecimal() or not 6 <= len(result.client_id) <= 22:
            result.client_id = DEFAULT_CLIENT
        if result.large_image in ("overwatch", LEGACY_LARGE_IMAGE):
            result.large_image = DEFAULT_LARGE_IMAGE
        if result.language not in (*LANGUAGES, "auto"):
            result.language = "auto"
        result.ocr_language = "rus" if result.ocr_language.lower() in ("rus", "ru", "ru-ru", "rus+eng") else "eng"
        return result


@dataclass
class Status:
    phase: str = "menus"
    hero: str = ""
    map_name: str = ""
    mode: str = "Quick Play"
    paused: bool = False
    started_at: int | None = None

    kda: tuple | None = None
    kda_read_at: float | None = None
    party_size: int | None = None
    party_read_at: float | None = None

    def transition(self, phase, now=None):
        if phase not in PHASES:
            raise ValueError("Unknown phase")
        if phase != self.phase or (phase == "match" and self.started_at is None):
            self.kda = self.kda_read_at = None
            self.started_at = int(time.time() if now is None else now) if phase == "match" else None
        if phase != self.phase:
            self.party_size = self.party_read_at = None
        self.phase = phase


def parse_kda(text):
    """Accept only a tightly calibrated row of three E/A/D counters."""
    if not isinstance(text, str) or not re.fullmatch(r"\s*\d{1,3}(?:\s+|\s*/\s*)\d{1,3}(?:\s+|\s*/\s*)\d{1,3}\s*", text):
        return None
    return tuple(int(value) for value in re.findall(r"\d+", text))


def kda_is_fresh(settings, status, now=None):
    age = (time.time() if now is None else now) - (status.kda_read_at or 0)
    return bool(settings.kda_enabled and status.phase == "match" and status.kda is not None
                and status.kda_read_at is not None and 0 <= age <= max(15, settings.ocr_interval * 3))


def party_is_fresh(settings, status, now=None):
    return bool(settings.ocr_enabled and status.party_size in range(1, 7)
                and status.party_read_at is not None
                and 0 <= (time.time() if now is None else now) - status.party_read_at
                <= max(30, settings.ocr_interval * 3))


def build_payload(settings, status, hero_info=None, map_info=None, now=None):
    language = resolve_language(settings.language)
    hero_name = (hero_info or {}).get("localized_names", {}).get(language, status.hero)
    map_name = (map_info or {}).get("localized_names", {}).get(language, status.map_name)
    if status.phase == "match":
        details = f"{tr(status.mode, language)} · {map_name or tr('Map not selected', language)}"
        state = tr("Playing {hero}", language, hero=hero_name) if status.hero else tr("In match", language)
    elif status.phase == "queue":
        details, state = f"{tr(status.mode, language)}: {tr('In Queue', language)}", tr("Waiting for a match", language)
    else:
        details, state = tr("In Menus", language), "Overwatch"
    if status.phase == "menus" and party_is_fresh(settings, status, now):
        if status.party_size == 1:
            state = tr("Solo", language)
        else:
            key = "In a party: {count} players"
            if language == "ru" and status.party_size in (2, 3, 4):
                key = "In a party: {count} teammates"
            state = tr(key, language, count=status.party_size)
    if kda_is_fresh(settings, status, now):
        state += " · E/A/D " + "/".join(str(value) for value in status.kda)
    payload = {"details": (settings.details_override or details)[:128],
               "state": (settings.state_override or state)[:128],
               "activity_type": 0, "status_display_type": settings.display_type}
    if settings.large_image:
        payload.update(large_image=settings.large_image[:256],
                       large_text=(map_name if status.phase == "match" else "Overwatch") or "Overwatch")
    if status.phase == "match" and settings.hero_image and status.hero:
        payload.update(small_image=settings.hero_image[:256], small_text=hero_name[:128])
    elif status.phase == "match" and settings.use_hero_portrait and hero_info:
        payload.update(small_image=hero_info["portrait"], small_text=hero_name[:128],
                       small_url=hero_info.get("source"))
    if status.phase == "match" and settings.use_map_art and map_info and map_info.get("image_available", True):
        payload.update(large_image=map_info["screenshot"], large_text=map_name[:128])
    if status.phase == "menus" and valid_url(settings.menu_image):
        payload.update(small_image=settings.menu_image[:256], small_text="OWRPC", small_url=PROJECT_URL)
    if status.phase == "menus" and not settings.button_label:
        payload["buttons"] = [{"label": "GitHub", "url": PROJECT_URL}]
    if settings.button_label and valid_url(settings.button_url):
        payload["buttons"] = [{"label": settings.button_label[:32], "url": settings.button_url}]
    if settings.show_timer and status.phase == "match" and status.started_at:
        payload["start"] = status.started_at
    return payload


def valid_url(value):
    parsed = urlparse(value)
    return parsed.scheme in ("https", "http") and bool(parsed.hostname) and len(value) <= 512


def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text).casefold() if c.isalnum())


def match_catalog(text, catalog):
    normalized = normalize(text)
    if len(normalized) < 3:
        return None
    scores = sorted(((SequenceMatcher(None, normalized, normalize(name)).ratio(), name)
                     for name in catalog), reverse=True)
    if not scores:
        return None
    score, name = scores[0]
    # Short names are especially prone to false positives; require exact match.
    if len(normalize(name)) <= 4 and normalized != normalize(name):
        return None
    if score < 0.88 or (len(scores) > 1 and score - scores[1][0] < 0.08):
        return None
    return name


class StableMatch:
    def __init__(self):
        self.reset()

    def reset(self):
        self.last, self.count = None, 0

    def observe(self, value):
        if value is None:
            self.reset()
            return None
        self.count = self.count + 1 if value == self.last else 1
        self.last = value
        return value if self.count >= 2 else None
