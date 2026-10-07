"""Bounded, read-only release checks. Installation stays under user control."""
from dataclasses import dataclass
import json
import re
from urllib.request import Request, urlopen

from . import __version__
from .model import PROJECT_URL

RELEASE_API = "https://api.github.com/repos/Olmae/OverwatchRPC/releases?per_page=30"


def request_bytes(url, limit=12 * 1024 * 1024):
    request = Request(url, headers={"User-Agent": f"OWRPC-Desktop/{__version__}", "Accept": "application/json,text/html"})
    with urlopen(request, timeout=7) as response:
        body = response.read(limit + 1)
    if len(body) > limit:
        raise ValueError("Response exceeds the metadata size limit")
    return body


def version_key(value):
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?(?:\+[A-Za-z0-9.-]+)?", value)
    if not match or len(value) > 80:
        return None
    major, minor, patch, channel, number = match.groups()
    return (int(major), int(minor), int(patch), {"alpha": 0, "beta": 1, "rc": 2, None: 3}[channel], int(number or 0))


@dataclass(frozen=True)
class Release:
    version: str
    url: str


def select_release(rows, current):
    current_key = version_key(current)
    if not isinstance(rows, list) or current_key is None:
        raise ValueError("Invalid release metadata or application version")
    candidates = []
    for row in rows[:100]:
        if not isinstance(row, dict) or row.get("draft"):
            continue
        tag = row.get("tag_name")
        key = version_key(tag)
        if key is None or key <= current_key:
            continue
        if current_key[3] == 3 and (key[3] < 3 or row.get("prerelease")):
            continue
        candidates.append((key, tag))
    if not candidates:
        return None
    _, tag = max(candidates)
    # Construct the official URL ourselves; ignore links embedded in API data.
    return Release(tag.removeprefix("v"), PROJECT_URL + "/releases/tag/" + tag)


def check_release(current, fetch=request_bytes):
    return select_release(json.loads(fetch(RELEASE_API)), current)
