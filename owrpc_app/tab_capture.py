"""Small in-memory Tab bursts, independent of slow OCR and Discord IPC."""
from collections import deque
from dataclasses import dataclass
import logging
import threading
import time

from .model import Settings
from .ocr import capture_frame
from .platform import game_foreground, lower_worker_priority, tab_pressed

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Sample:
    image: object
    revision: int
    burst: int
    opened_at: float
    captured_at: float


class TabCapture(threading.Thread):
    def __init__(self):
        super().__init__(name="OWRPC Tab capture", daemon=True)
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.config = (False, "Overwatch.exe", 0)
        self.samples = deque(maxlen=3)
        self.pressed = False
        self.burst = 0
        self.opened_at = 0
        self.count = 0
        self.cooldown = 0

    def configure(self, settings, revision, paused):
        config = (not paused and (settings.ocr_enabled or settings.kda_enabled),
                  settings.game_process, revision)
        with self.lock:
            if config != self.config:
                self.config = config
                self.samples.clear()
                self.pressed = False

    def step(self, now):
        with self.lock:
            enabled, process, revision = self.config
        foreground = enabled and game_foreground(process)
        pressed = foreground and tab_pressed()
        if not foreground:
            with self.lock:
                self.samples.clear()
        if pressed and not self.pressed:
            with self.lock:
                self.samples.clear()
                self.burst += 1
            self.opened_at, self.count = now, 0
            log.info("Recognition timing: Tab opened (capture thread)")
        if self.pressed and not pressed and foreground:
            log.info("Tab released: burst=%s samples=%s held_ms=%.1f", self.burst,
                     self.count, (now - self.opened_at) * 1000)
        self.pressed = pressed
        # Leave the opening animation time to settle. Capture at most three
        # independent frames; a held key never becomes continuous capture.
        if (not pressed or self.count >= 3 or now < self.cooldown
                or now < self.opened_at + .15 + self.count * .25):
            return
        image = capture_frame(Settings(game_process=process))
        captured_at = time.monotonic()
        if image is not None and game_foreground(process):
            with self.lock:
                if not self.stop_event.is_set() and self.config == (enabled, process, revision):
                    self.samples.append(Sample(image, revision, self.burst,
                                               self.opened_at, captured_at))
        self.count += 1
        log.info("Tab sample: burst=%s count=%s capture_ms=%.1f", self.burst,
                 self.count, (captured_at - self.opened_at) * 1000)

    def take(self, revision, now):
        with self.lock:
            while self.samples:
                sample = self.samples.popleft()
                if sample.revision == revision and 0 <= now - sample.captured_at <= 10:
                    return sample
        return None

    def current(self, sample):
        with self.lock:
            return sample.revision == self.config[2] and sample.burst == self.burst

    def discard(self, burst):
        with self.lock:
            self.samples = deque((s for s in self.samples if s.burst != burst), maxlen=3)

    def run(self):
        try:
            lower_worker_priority()
        except OSError:
            log.warning("Could not lower Tab capture priority", exc_info=True)
        while not self.stop_event.wait(.05):
            try:
                self.step(time.monotonic())
            except Exception as exc:
                self.cooldown = time.monotonic() + 30
                log.info("Tab capture unavailable: %s", exc)

    def close(self):
        self.stop_event.set()
        self.join(timeout=2)
        with self.lock:
            self.samples.clear()
