from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile

from .model import Settings


def data_dir():
    return Path(os.environ.get("APPDATA", str(Path.home() / ".config"))) / "OWRPC"


def load_settings(path=None):
    path = Path(path) if path else data_dir() / "settings.json"
    if not path.exists():
        return Settings(), ""
    try:
        return Settings.from_dict(json.loads(path.read_text(encoding="utf-8"))), ""
    except (ValueError, TypeError):
        backup = path.with_name(f"settings.corrupt-{datetime.now():%Y%m%d-%H%M%S-%f}.json")
        path.rename(backup)
        return Settings(), f"Corrupt settings preserved at: {backup}"


def save_settings(settings, path=None):
    path = Path(path) if path else data_dir() / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix="settings-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(asdict(settings), stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
