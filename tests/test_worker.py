import queue
import unittest
from unittest.mock import patch

from owrpc_app.model import Settings, Status
from owrpc_app.runtime import Worker


class Ticks:
    def __init__(self, count, callback=None):
        self.count, self.tick, self.callback = count, 0, callback

    def wait(self, _):
        self.tick += 1
        if self.callback:
            self.callback(self.tick)
        return self.tick > self.count


class FakeRpc:
    def __init__(self):
        self.calls = []

    def send(self, client_id, payload):
        self.calls.append(payload)
        return True

    def close(self):
        pass


CATALOG = {"heroes": [{"name": "Ana", "portrait": "https://example.com/ana.png"}], "maps": []}


class WorkerTests(unittest.TestCase):
    def make_worker(self, foreground=True, callback=None, status=None):
        events = queue.Queue()
        worker = Worker(Settings(ocr_enabled=True, ocr_interval=3), status or Status(phase="match"), CATALOG, events)
        worker.stop_event = Ticks(3, callback)
        rpc = FakeRpc()
        with patch("owrpc_app.runtime.RpcSession", return_value=rpc), \
                patch("owrpc_app.runtime.game_running", return_value=True), \
                patch("owrpc_app.runtime.game_foreground", return_value=foreground), \
                patch("owrpc_app.runtime.recognize", return_value={"hero": "Ana"}) as capture, \
                patch("owrpc_app.runtime.time.monotonic", side_effect=lambda: worker.stop_event.tick * 10):
            worker.run()
        results = []
        while not events.empty():
            results.append(events.get())
        return worker, rpc, capture, results

    def test_ocr_never_captures_background_window(self):
        _, _, capture, results = self.make_worker(foreground=False)
        capture.assert_not_called()
        self.assertFalse(any(e == "recognized" for e, _ in results))

    def test_automatic_detection_captures_menus(self):
        _, _, capture, _ = self.make_worker(status=Status(phase="menus"))
        self.assertGreaterEqual(capture.call_count, 2)

    def test_two_samples_update_hero_and_shutdown_clears(self):
        worker, rpc, capture, results = self.make_worker()
        self.assertEqual(worker.status.hero, "Ana")
        self.assertGreaterEqual(capture.call_count, 2)
        self.assertTrue(any(e == "recognized" for e, _ in results))
        self.assertIsNone(rpc.calls[-1])

    def test_scene_detection_moves_from_menus_without_manual_phase(self):
        from owrpc_app.detection import Detection
        events = queue.Queue()
        worker = Worker(Settings(ocr_enabled=True), Status(), CATALOG, events)
        worker.stop_event = Ticks(4)
        with patch("owrpc_app.runtime.RpcSession", return_value=FakeRpc()), \
             patch("owrpc_app.runtime.game_running", return_value=True), \
             patch("owrpc_app.runtime.game_foreground", return_value=True), \
             patch("owrpc_app.runtime.recognize", return_value={"__scene__": Detection(phase="match", hero="Ana", scene="scoreboard")}), \
             patch("owrpc_app.runtime.time.monotonic", side_effect=lambda: worker.stop_event.tick * 10):
            worker.run()
        self.assertEqual(worker.status.phase, "match")
        self.assertEqual(worker.status.hero, "Ana")
        self.assertTrue(any(event == "detected" for event, _ in events.queue))

    def test_scoreboard_requires_two_samples_and_stops_in_background(self):
        for foreground in (True, False):
            events = queue.Queue()
            worker = Worker(Settings(kda_enabled=True, ocr_interval=3), Status(phase="match", started_at=50), CATALOG, events)
            worker.stop_event = Ticks(4)
            rpc = FakeRpc()
            with patch("owrpc_app.runtime.RpcSession", return_value=rpc), \
                 patch("owrpc_app.runtime.game_running", return_value=True), \
                 patch("owrpc_app.runtime.game_foreground", return_value=foreground), \
                 patch("owrpc_app.runtime.recognize", return_value={"kda": "12 4 3"}), \
                 patch("owrpc_app.runtime.time.time", return_value=100), \
                 patch("owrpc_app.runtime.time.monotonic", side_effect=lambda: worker.stop_event.tick * 10):
                worker.run()
            results = list(events.queue)
            if foreground:
                self.assertEqual(worker.status.kda, (12, 4, 3))
                self.assertTrue(any(event == "kda" for event, _ in results))
                self.assertTrue(any(payload and "12/4/3" in payload["state"] for payload in rpc.calls))
            else:
                self.assertIsNone(worker.status.kda)
                self.assertFalse(any(event == "kda" for event, _ in results))

    def test_two_scoreboard_captures_confirm_match_and_fields(self):
        from owrpc_app.detection import Detection
        worker = Worker(Settings(ocr_enabled=True, kda_enabled=True), Status(), CATALOG, queue.Queue())
        worker.stop_event = Ticks(2)
        scene = Detection(phase="match", hero="Ana", kda=(12, 4, 3), scene="scoreboard")
        with patch("owrpc_app.runtime.RpcSession", return_value=FakeRpc()), \
             patch("owrpc_app.runtime.game_running", return_value=True), \
             patch("owrpc_app.runtime.game_foreground", return_value=True), \
             patch("owrpc_app.runtime.recognize", return_value={"__scene__": scene}), \
             patch("owrpc_app.runtime.time.monotonic", side_effect=lambda: worker.stop_event.tick * 10):
            worker.run()
        self.assertEqual(worker.status.phase, "match")
        self.assertEqual(worker.status.hero, "Ana")
        self.assertEqual(worker.status.kda, (12, 4, 3))

    def test_tab_burst_captures_twice_with_long_poll_interval(self):
        worker = Worker(Settings(ocr_enabled=True, ocr_interval=60), Status(), CATALOG, queue.Queue())
        worker.stop_event = Ticks(8)
        with patch("owrpc_app.runtime.RpcSession", return_value=FakeRpc()), \
             patch("owrpc_app.runtime.game_running", return_value=True), \
             patch("owrpc_app.runtime.game_foreground", return_value=True), \
             patch("owrpc_app.runtime.tab_pressed", side_effect=lambda: worker.stop_event.tick >= 2, create=True), \
             patch("owrpc_app.runtime.recognize", return_value={}) as capture, \
             patch("owrpc_app.runtime.time.monotonic", side_effect=lambda: worker.stop_event.tick * 0.25):
            worker.run()
        # Initial background poll, rising edge, one follow-up, then idle.
        self.assertEqual(capture.call_count, 3)

    def test_background_or_pause_does_not_read_tab_state(self):
        for paused, foreground in ((False, False), (True, True)):
            worker = Worker(Settings(ocr_enabled=True), Status(paused=paused), CATALOG, queue.Queue())
            worker.stop_event = Ticks(3)
            with patch("owrpc_app.runtime.RpcSession", return_value=FakeRpc()), \
                 patch("owrpc_app.runtime.game_running", return_value=True), \
                 patch("owrpc_app.runtime.game_foreground", return_value=foreground), \
                 patch("owrpc_app.runtime.tab_pressed") as key, \
                 patch("owrpc_app.runtime.recognize") as capture:
                worker.run()
            key.assert_not_called()
            capture.assert_not_called()

    def test_disable_during_capture_discards_result_and_cancels_burst(self):
        from owrpc_app.detection import Detection
        worker = Worker(Settings(ocr_enabled=True, ocr_interval=60), Status(), CATALOG, queue.Queue())
        worker.stop_event = Ticks(8)

        def capture(*args):
            worker.configure(Settings(ocr_enabled=False), Status())
            return {"__scene__": Detection(phase="match", hero="Ana", scene="scoreboard")}

        with patch("owrpc_app.runtime.RpcSession", return_value=FakeRpc()), \
             patch("owrpc_app.runtime.game_running", return_value=True), \
             patch("owrpc_app.runtime.game_foreground", return_value=True), \
             patch("owrpc_app.runtime.tab_pressed", return_value=True), \
             patch("owrpc_app.runtime.recognize", side_effect=capture) as read, \
             patch("owrpc_app.runtime.time.monotonic", side_effect=lambda: worker.stop_event.tick * 0.25):
            worker.run()
        self.assertEqual(read.call_count, 1)
        self.assertEqual(worker.status.phase, "menus")
        self.assertEqual(worker.status.hero, "")

    def test_party_size_requires_two_samples_and_menu_scene(self):
        from owrpc_app.detection import Detection
        for count in (1, 2, 3):
            worker = Worker(Settings(ocr_enabled=True), Status(), CATALOG, queue.Queue())
            worker.stop_event = Ticks(2)
            with patch("owrpc_app.runtime.RpcSession", return_value=FakeRpc()), \
                 patch("owrpc_app.runtime.game_running", return_value=True), \
                 patch("owrpc_app.runtime.game_foreground", return_value=True), \
                 patch("owrpc_app.runtime.tab_pressed", return_value=False), \
                 patch("owrpc_app.runtime.recognize", return_value={"__scene__": Detection(phase="menus", scene="menus", party_size=count)}), \
                 patch("owrpc_app.runtime.time.time", return_value=100), \
                 patch("owrpc_app.runtime.time.monotonic", side_effect=lambda: worker.stop_event.tick * 10):
                worker.run()
            self.assertEqual(worker.status.party_size, count)
            self.assertEqual(worker.status.party_read_at, 100)

    def test_single_party_observation_is_not_published(self):
        from owrpc_app.detection import Detection
        worker = Worker(Settings(ocr_enabled=True), Status(), CATALOG, queue.Queue())
        worker.stop_event = Ticks(1)
        with patch("owrpc_app.runtime.RpcSession", return_value=FakeRpc()), \
             patch("owrpc_app.runtime.game_running", return_value=True), \
             patch("owrpc_app.runtime.game_foreground", return_value=True), \
             patch("owrpc_app.runtime.tab_pressed", return_value=False), \
             patch("owrpc_app.runtime.recognize", return_value={"__scene__": Detection(phase="menus", party_size=2)}):
            worker.run()
        self.assertIsNone(worker.status.party_size)


if __name__ == "__main__":
    unittest.main()
