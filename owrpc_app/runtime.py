from dataclasses import replace
import logging
import queue
import threading
import time
import sys

from .model import build_payload, match_catalog, StableMatch, parse_kda, ScoreboardClock
from .platform import game_running, game_started_at, game_foreground, lower_worker_priority, tab_pressed
from .ocr import recognize, close_recognition, analyze_frame
from .recognition_schedule import RecognitionSchedule
from .tab_capture import TabCapture

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
        stable = {key: StableMatch() for key in ("hero", "map", "kda", "phase", "mode", "nickname", "party", "scene")}
        scoreboard_clock = ScoreboardClock()
        next_rpc = next_process = 0
        schedule = RecognitionSchedule()
        running = False
        game_start = None
        previous_running = None
        current_revision = 0
        nickname = ""
        previous_detection = previous_confirmation = None
        tab_opened_at = None
        active_burst = None
        capture = TabCapture() if sys.platform == "win32" else None
        if capture is not None:
            capture.configure(self.settings, current_revision, self.status.paused)
            capture.start()
        try:
            while not self.stop_event.wait(0.25):
                while True:
                    try:
                        self.settings, self.status, current_revision, catalog = self.commands.get_nowait()
                        if catalog is not None:
                            self.catalog = catalog
                        schedule = RecognitionSchedule()
                        scoreboard_clock = ScoreboardClock()
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
                if capture is not None:
                    capture.configure(self.settings, current_revision, self.status.paused)
                if now >= next_process:
                    try:
                        running = game_running(self.settings.game_process)
                        game_start = game_started_at(self.settings.game_process) if running else None
                    except Exception as exc:
                        running = False
                        game_start = None
                        log.warning("Process detection failed: %s", exc)
                    next_process = now + 5
                    self.events.put(("game", running))
                    if previous_running and not running:
                        if capture is not None:
                            capture.configure(self.settings, current_revision, True)
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
                sample = capture.take(current_revision, time.monotonic()) if capture is not None and enabled and running else None
                if not foreground and sample is None:
                    scoreboard_clock = ScoreboardClock()
                    tab_opened_at = None
                    for match in stable.values():
                        match.reset()
                elif capture is None and pressed and not schedule.pressed:
                    tab_opened_at = time.monotonic()
                    log.info("Recognition timing: Tab opened")
                due = schedule.due(now, foreground, pressed if capture is None else False, self.settings.ocr_interval)
                if sample is not None or (due and not (capture is not None and pressed)):
                    try:
                        recognition_started = time.monotonic()
                        captured_at = time.time() - (max(0, recognition_started-sample.captured_at) if sample is not None else 0)
                        if sample is not None:
                            tab_opened_at = sample.opened_at
                            if sample.burst != active_burst:
                                active_burst = sample.burst
                                for match in stable.values():
                                    match.reset()
                            readings = dict(analyze_frame(self.settings, self.catalog, nickname, sample.image))
                            if not capture.current(sample):
                                continue
                        else:
                            readings = dict(recognize(self.settings, self.catalog, nickname))
                        schedule.completed(time.monotonic(), self.settings.ocr_interval)
                        # A manual edit queued during capture invalidates that capture.
                        if not self.commands.empty():
                            continue
                        scene = readings.pop("__scene__", None)
                        evidence = readings.pop("__ocr_evidence__", None)
                        if scene is not None:
                            if sample is not None and scene.scene == 'scoreboard' and evidence:
                                log.info("Scoreboard OCR: burst=%s hero_title=%r timer=%r text_ms=%s parse_ms=%s", sample.burst,
                                         evidence['hero_title'], evidence['timer'],
                                         evidence.get('text_ms'), evidence.get('parse_ms'))
                            if (scene.elapsed is not None and game_start is not None
                                    and captured_at-scene.elapsed < game_start-3):
                                log.info("Game timer rejected: elapsed=%s exceeds game process age=%.1f",
                                         scene.elapsed, captured_at-game_start)
                            confirmed_start = scoreboard_clock.observe(
                                scene.elapsed if scene.phase == "match" else None, captured_at, game_start)
                            detection = (scene.scene, scene.phase, scene.hero, scene.map_name,
                                         scene.mode, scene.kda, scene.party_size, scene.elapsed)
                            if detection != previous_detection:
                                log.info("Recognition candidate: scene=%s phase=%s hero=%s map=%s mode=%s kda=%s party=%s elapsed=%s duration_ms=%.1f",
                                         *detection, (time.monotonic() - recognition_started) * 1000)
                                previous_detection = detection
                            detected_nick = stable["nickname"].observe(scene.nickname)
                            if detected_nick:
                                nickname = detected_nick
                            # Collect match candidates before phase confirmation so two
                            # scoreboard frames confirm both the scene and its fields.
                            accepted_fields = {}
                            if scene.phase in ("match", "map_loading"):
                                for key, candidate in (("hero", scene.hero), ("map", scene.map_name), ("kda", scene.kda)):
                                    accepted_fields[key] = (None if sample is not None and candidate is None
                                                            else stable[key].observe(candidate))
                            elif sample is None or scene.phase is not None:
                                for key in ("hero", "map", "kda"):
                                    stable[key].reset()
                            accepted_phase = (None if sample is not None and scene.phase is None
                                              else stable["phase"].observe(scene.phase))
                            mode = (None if sample is not None and scene.mode is None
                                    else stable["mode"].observe(scene.mode))
                            if capture is None and pressed and not accepted_fields.get("hero"):
                                schedule.retry_followup(time.monotonic())
                            if self.settings.ocr_enabled and accepted_phase is not None:
                                old_phase = self.status.phase
                                map_changed = (accepted_fields.get("map") and self.status.map_name
                                               and accepted_fields["map"] != self.status.map_name)
                                counters_reset = (accepted_fields.get("kda") == (0, 0, 0)
                                                  and self.status.kda and any(self.status.kda)
                                                  and scene.elapsed is not None and 0 <= scene.elapsed <= 10
                                                  and self.status.started_at is not None
                                                  and time.time() - self.status.started_at >= 60)
                                practice_exit = (self.status.map_name == 'Practice Range'
                                                 and scene.scene == 'scoreboard'
                                                 and mode in ('Control','Escort','Hybrid','Push','Mystery Madness'))
                                if old_phase == accepted_phase == "match" and (map_changed or counters_reset or practice_exit):
                                    log.info("New match recovered: map_changed=%s counters_reset=%s practice_exit=%s", bool(map_changed), bool(counters_reset), practice_exit)
                                    self.status.hero = self.status.map_name = ""
                                    self.status.mode = self.settings.mode
                                    self.status.kda = self.status.kda_read_at = None
                                    self.status.started_at = confirmed_start or int(time.time())
                                self.status.transition(accepted_phase)
                                if old_phase != accepted_phase:
                                    if accepted_phase != "results":
                                        self.status.hero = ""
                                    if accepted_phase != "results" and not (old_phase == "map_loading" and accepted_phase == "match"):
                                        self.status.map_name = ""
                            if self.status.phase == scene.phase == "match" and confirmed_start is not None:
                                if self.status.started_at is None or abs(self.status.started_at-confirmed_start) > 2:
                                    log.info("Game timer synchronized: elapsed=%s start=%s", scene.elapsed, confirmed_start)
                                    self.status.started_at = confirmed_start
                            accepted_scene = stable["scene"].observe(scene.scene) if scene.phase else None
                            if accepted_scene and self.status.phase == scene.phase:
                                self.status.scene = accepted_scene
                            if scene.phase == self.status.phase == "map_loading":
                                loading_map = accepted_fields.get("map")
                                if loading_map:
                                    self.status.map_name = loading_map
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
                                if scene.party_size is not None and stable["party"].count == 1:
                                    # One prompt confirmation, then resume normal polling.
                                    schedule.next_poll = min(schedule.next_poll, time.monotonic() + .25)
                                if size is not None and self.status.phase == scene.phase:
                                    self.status.party_size = size
                                    self.status.party_read_at = time.time()
                            else:
                                stable["party"].reset()
                            confirmation = (self.status.phase, self.status.hero, self.status.map_name,
                                            self.status.mode, self.status.kda, self.status.party_size)
                            if confirmation != previous_confirmation:
                                log.info("Recognition confirmed: phase=%s hero=%s map=%s mode=%s kda=%s party=%s", *confirmation)
                                if (tab_opened_at is not None and self.status.hero
                                        and (previous_confirmation is None or self.status.hero != previous_confirmation[1])):
                                    log.info("Recognition timing: hero=%s tab_to_confirm_ms=%.1f",
                                             self.status.hero, (time.monotonic() - tab_opened_at) * 1000)
                                previous_confirmation = confirmation
                            if (sample is not None and accepted_phase and accepted_fields.get("hero")
                                    and accepted_fields.get("map") and mode
                                    and (not self.settings.kda_enabled or accepted_fields.get("kda") is not None)):
                                capture.discard(sample.burst)
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
            if capture is not None:
                capture.close()
            try:
                rpc.send(self.settings.client_id, None)
            finally:
                close_recognition()
                rpc.close()
