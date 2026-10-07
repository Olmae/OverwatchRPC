from dataclasses import dataclass, fields
from difflib import SequenceMatcher
import time
import unicodedata
from urllib.parse import urlparse

DEFAULT_CLIENT = "583356928688783369"
DEFAULT_LARGE_IMAGE = "https://raw.githubusercontent.com/Olmae/OverwatchRPC/main/assets/overwatch-logo.png"
PHASES = {"menus": "In menus", "queue": "In queue", "match": "In match"}
MODES = ["Quick Play", "Competitive", "Stadium", "Arcade", "Custom Game",
         "Mystery Heroes", "Mystery Madness: Graveyard Games", "Practice",
         "Capture the Flag", "Deathmatch", "Team Deathmatch", "Elimination", "Payload Race", "Workshop"]


@dataclass
class Settings:
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
    use_hero_portrait: bool = True
    use_map_art: bool = True
    display_type: int = 0
    button_label: str = ""
    button_url: str = ""
    details_override: str = ""
    state_override: str = ""
    ocr_enabled: bool = False
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
        if result.large_image == "overwatch":
            result.large_image = DEFAULT_LARGE_IMAGE
        return result


@dataclass
class Status:
    phase: str = "menus"
    hero: str = ""
    map_name: str = ""
    mode: str = "Quick Play"
    paused: bool = False
    started_at: int | None = None

    def transition(self, phase, now=None):
        if phase not in PHASES:
            raise ValueError("Unknown phase")
        if phase != self.phase:
            self.started_at = int(time.time() if now is None else now) if phase == "match" else None
        self.phase = phase


def build_payload(settings, status, hero_info=None, map_info=None):
    if status.phase == "match":
        details = f"{status.mode} · {status.map_name or 'Map not selected'}"
        state = f"Playing {status.hero}" if status.hero else "In match"
    elif status.phase == "queue":
        details, state = f"{status.mode}: In Queue", "Waiting for a match"
    else:
        details, state = "In Menus", "Overwatch"
    payload = {"details": (settings.details_override or details)[:128],
               "state": (settings.state_override or state)[:128],
               "activity_type": 0, "status_display_type": settings.display_type}
    if settings.large_image:
        payload.update(large_image=settings.large_image[:256],
                       large_text=(status.map_name if status.phase == "match" else "Overwatch") or "Overwatch")
    if status.phase == "match" and settings.hero_image and status.hero:
        payload.update(small_image=settings.hero_image[:256], small_text=status.hero[:128])
    elif status.phase == "match" and settings.use_hero_portrait and hero_info:
        payload.update(small_image=hero_info["portrait"], small_text=status.hero[:128],
                       small_url=hero_info.get("source"))
    if status.phase == "match" and settings.use_map_art and map_info and map_info.get("image_available", True):
        payload.update(large_image=map_info["screenshot"], large_text=status.map_name[:128])
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
