from dataclasses import replace
import logging
import queue
import threading
import time

from .model import build_payload, match_catalog, StableMatch
from .platform import game_running, game_foreground
from .ocr import recognize

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
        self.settings, self.status, self.catalog, self.events = settings, status, catalog, events
        self.commands = queue.Queue()
        self.stop_event = threading.Event()
        self.revision = 0

    def configure(self, settings, status):
        self.revision += 1
        self.commands.put((replace(settings), replace(status), self.revision))

    def run(self):
        rpc = RpcSession()
        stable = {key: StableMatch() for key in ("hero", "map")}
        next_rpc = next_ocr = next_process = 0
        running = False
        previous_running = None
        current_revision = 0
        try:
            while not self.stop_event.wait(0.25):
                while True:
                    try:
                        self.settings, self.status, current_revision = self.commands.get_nowait()
                        for match in stable.values():
                            match.reset()
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
                if self.settings.ocr_enabled and not self.status.paused and now >= next_ocr:
                    next_ocr = now + self.settings.ocr_interval
                    try:
                        foreground = running and game_foreground(self.settings.game_process)
                        if not foreground or self.status.phase != "match":
                            for match in stable.values():
                                match.reset()
                            self.events.put(("ocr_status", "OCR waiting for a match and Overwatch in foreground"))
                            continue
                        readings = recognize(self.settings)
                        # A manual edit queued during capture invalidates that capture.
                        if not self.commands.empty():
                            continue
                        for field, text in readings.items():
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
                        next_ocr = time.monotonic() + 30
        finally:
            try:
                rpc.send(self.settings.client_id, None)
            finally:
                rpc.close()
