import json
from pathlib import Path
import sys


def resource_dir():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "assets"


def load_catalog():
    return json.loads((resource_dir() / "catalog.json").read_text(encoding="utf-8"))
