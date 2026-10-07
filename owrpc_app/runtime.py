from dataclasses import replace
import logging
import queue
import threading
import time

from .model import build_payload, match_catalog, StableMatch, parse_kda
from .platform import game_running, game_foreground, lower_worker_priority, tab_pressed
from .ocr import recognize, close_recognition
from .recognition_schedule import RecognitionSchedule

log = logging.getLogger(__name__)


class RpcSession:
    def __init__(self, factory=None):
        self.factory = factory or self._factory
        self.client, self.client_id, self.last = None, None, None
        self.error = ""
        self.last_sent = 0

    @staticmethod
    def _factory(client_id):
        from pypresence import Presence
        client = Presence(client_id, connection_timeout=3, response_timeout=3)
        # pypresence 4.6.2 connect() allocates a fresh loop. Release its unused
        # constructor loop so repeated connection attempts do not leak loops.
        client.loop.close()
        return client

    def send(self, client_id, payload):
        if self.client and self.client_id != client_id:
            try:
                self.client.clear()
            except Exception:
                log.debug("Could not clear previous application", exc_info=True)
            self.close()
        if payload is None and self.client is None:
            return True
        try:
            if self.client is None:
                self.client = self.factory(client_id)
                self.client_id = client_id
                self.client.connect()
            if payload != self.last or (payload is not None and time.monotonic() - self.last_sent >= 60):
                if payload is None:
                    self.client.clear()
                else:
                    self.client.update(**payload)
                self.last = payload
                self.last_sent = time.monotonic()
            self.error = ""
            return True
        except Exception as exc:
            self.error = str(exc)
            log.info("Discord unavailable: %s", exc)
            self.close()
            return False

    def close(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                log.debug("Discord close failed", exc_info=True)
            # Library close() can fail before closing the loop on a dead pipe.
            writer = getattr(self.client, "sock_writer", None)
            loop = getattr(self.client, "loop", None)
            try:
                if writer:
                    writer.close()
            except Exception:
                log.debug("Discord pipe cleanup failed", exc_info=True)
            if loop and not loop.is_closed():
                loop.close()
        self.client, self.client_id, self.last = None, None, None


class Worker(threading.Thread):
    def __init__(self, settings, status, catalog, events):
        super().__init__(name="OWRPC worker", daemon=True)
        self.settings, self.status, self.catalog, self.events = replace(settings), replace(status), catalog, events
        self.commands = queue.Queue()
        self.stop_event = threading.Event()
        self.revision = 0

    def configure(self, settings, status, catalog=None):
        self.revision += 1
        self.commands.put((replace(settings), replace(status), self.revision, catalog))

    def run(self):
        try:
            lower_worker_priority()
        except OSError:
            log.warning("Could not lower recognition worker priority", exc_info=True)
        rpc = RpcSession()
        stable = {key: StableMatch() for key in ("hero", "map", "kda", "phase", "mode", "nickname", "party")}
        next_rpc = next_process = 0
        schedule = RecognitionSchedule()
        running = False
        previous_running = None
        current_revision = 0
        nickname = ""
        try:
            while not self.stop_event.wait(0.25):
                while True:
                    try:
                        self.settings, self.status, current_revision, catalog = self.commands.get_nowait()
                        if catalog is not None:
                            self.catalog = catalog
                        schedule = RecognitionSchedule()
                        for match in stable.values():
                            match.reset()
                        if self.status.paused or not (self.settings.ocr_enabled or self.settings.kda_enabled):
                            close_recognition()
                        if self.status.paused:
                            rpc.send(self.settings.client_id, None)
                            self.events.put(("rpc", "Presence paused"))
                    except queue.Empty:
                        break
                now = time.monotonic()
                if now >= next_process:
                    try:
                        running = game_running(self.settings.game_process)
                    except Exception as exc:
                        running = False
                        log.warning("Process detection failed: %s", exc)
                    next_process = now + 5
                    self.events.put(("game", running))
                    if previous_running and not running:
                        self.status.transition("menus")
                        self.status.hero = self.status.map_name = ""
                        self.status.party_size = self.status.party_read_at = None
                        for match in stable.values():
                            match.reset()
                        self.events.put(("game_closed", current_revision))
                    previous_running = running
                if now >= next_rpc:
                    active = not self.status.paused and (running or not self.settings.only_when_game)
                    hero = next((h for h in self.catalog["heroes"] if h["name"] == self.status.hero), None)
                    map_info = next((m for m in self.catalog["maps"] if m["name"] == self.status.map_name), None)
                    payload = build_payload(self.settings, self.status, hero, map_info) if active else None
                    ok = rpc.send(self.settings.client_id, payload)
                    label = ("Connected to Discord" if active else "Presence hidden") if ok else "Discord unavailable · retrying"
                    self.events.put(("rpc", label))
                    next_rpc = time.monotonic() + self.settings.rpc_interval
                enabled = (self.settings.ocr_enabled or self.settings.kda_enabled) and not self.status.paused
                try:
                    foreground = enabled and running and game_foreground(self.settings.game_process)
                    pressed = foreground and tab_pressed()
                except Exception as exc:
                    foreground = pressed = False
                    log.info("Foreground/key check failed: %s", exc)
                if not foreground:
                    for match in stable.values():
                        match.reset()
                if schedule.due(now, foreground, pressed, self.settings.ocr_interval):
                    try:
                        readings = dict(recognize(self.settings, self.catalog, nickname))
                        schedule.completed(time.monotonic(), self.settings.ocr_interval)
                        # A manual edit queued during capture invalidates that capture.
                        if not self.commands.empty():
                            continue
                        scene = readings.pop("__scene__", None)
                        if scene is not None:
                            detected_nick = stable["nickname"].observe(scene.nickname)
                            if detected_nick:
                                nickname = detected_nick
                            # Collect match candidates before phase confirmation so two
                            # scoreboard frames confirm both the scene and its fields.
                            accepted_fields = {}
                            if scene.phase == "match":
                                for key, candidate in (("hero", scene.hero), ("map", scene.map_name), ("kda", scene.kda)):
                                    accepted_fields[key] = stable[key].observe(candidate)
                            else:
                                for key in ("hero", "map", "kda"):
                                    stable[key].reset()
                            accepted_phase = stable["phase"].observe(scene.phase)
                            if self.settings.ocr_enabled and accepted_phase is not None:
                                old_phase = self.status.phase
                                self.status.transition(accepted_phase)
                                if old_phase != accepted_phase:
                                    self.status.hero = self.status.map_name = ""
                                    if accepted_phase == "match" and scene.elapsed is not None:
                                        self.status.started_at = int(time.time()) - scene.elapsed
                            mode = stable["mode"].observe(scene.mode)
                            if mode:
                                self.status.mode = mode
                            if self.status.phase == "match" and scene.phase == "match":
                                if self.settings.ocr_enabled:
                                    for key, attr in (("hero", "hero"), ("map", "map_name")):
                                        name = accepted_fields.get(key)
                                        if name:
                                            setattr(self.status, attr, name)
                                if self.settings.kda_enabled:
                                    values = accepted_fields.get("kda")
                                    if values is not None:
                                        self.status.kda = values
                                        self.status.kda_read_at = time.time()
                            if scene.phase in ("menus", "queue") and self.settings.ocr_enabled:
                                size = stable["party"].observe(scene.party_size)
                                if size is not None and self.status.phase == scene.phase:
                                    self.status.party_size = size
                                    self.status.party_read_at = time.time()
                            else:
                                stable["party"].reset()
                            self.events.put(("detected", (replace(self.status), current_revision)))
                            self.events.put(("ocr_status", "Automatic recognition: " + scene.scene))
                            continue
                        for field, text in readings.items():
                            if field == "kda":
                                value = stable["kda"].observe(parse_kda(text))
                                if value is not None:
                                    self.status.kda = value
                                    self.status.kda_read_at = time.time()
                                    self.events.put(("kda", (value, self.status.kda_read_at, current_revision)))
                                continue
                            if field not in ("hero", "map"):
                                continue
                            names = [x["name"] for x in self.catalog["heroes" if field == "hero" else "maps"]]
                            name = stable[field].observe(match_catalog(text, names))
                            if name:
                                attr = "hero" if field == "hero" else "map_name"
                                if getattr(self.status, attr) != name:
                                    setattr(self.status, attr, name)
                                    self.events.put(("recognized", (attr, name, current_revision)))
                        self.events.put(("ocr_status", "OCR: " + (" · ".join(f"{k}: {v[:50] or '—'}" for k, v in readings.items()) or "select text regions first")))
                    except Exception as exc:
                        self.events.put(("ocr_status", "OCR unavailable: " + str(exc)[:180]))
                        log.info("OCR error: %s", exc)
                        schedule.failed(time.monotonic())
        finally:
            try:
                rpc.send(self.settings.client_id, None)
            finally:
                close_recognition()
                rpc.close()
