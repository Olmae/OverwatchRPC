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
    def setUp(self):
        capture_patch = patch('owrpc_app.runtime.TabCapture', return_value=None)
        capture_patch.start()
        self.addCleanup(capture_patch.stop)

    def test_two_buffered_frames_confirm_after_tab_is_released(self):
        from owrpc_app.tab_capture import Sample
        from owrpc_app.detection import Detection
        capture = unittest.mock.Mock()
        capture.take.side_effect = [Sample(object(), 0, 1, 0, 0),
                                    Sample(object(), 0, 1, 0, 0), None]
        capture.current.return_value = True
        worker = Worker(Settings(), Status(), CATALOG, queue.Queue())
        worker.stop_event = Ticks(3)
        with patch('owrpc_app.runtime.TabCapture', return_value=capture), \
                patch('owrpc_app.runtime.game_running', return_value=True), \
                patch('owrpc_app.runtime.game_foreground', return_value=True), \
                patch('owrpc_app.runtime.tab_pressed', return_value=False), \
                patch('owrpc_app.runtime.analyze_frame', return_value={'__scene__': Detection(phase='match', hero='Ana')}), \
                patch('owrpc_app.runtime.recognize', return_value={}), \
                patch('owrpc_app.runtime.RpcSession', return_value=FakeRpc()):
            worker.run()
        self.assertEqual(worker.status.hero, 'Ana')
        capture.close.assert_called_once()

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

    def test_loading_map_is_kept_on_hero_selection_and_results_stop_timer(self):
        from owrpc_app.detection import Detection
        scenes = [Detection(phase='map_loading', map_name='Ilios', scene='map_loading')]*2
        scenes += [Detection(phase='match', hero='Ana', scene='hero_select')]*2
        scenes += [Detection(phase='results', scene='results')]*2
        events = queue.Queue()
        worker = Worker(Settings(kda_enabled=True), Status(phase='map_vote'), CATALOG, events)
        worker.stop_event = Ticks(6)
        with patch('owrpc_app.runtime.RpcSession', return_value=FakeRpc()), \
             patch('owrpc_app.runtime.game_running', return_value=True), \
             patch('owrpc_app.runtime.game_foreground', return_value=True), \
             patch('owrpc_app.runtime.recognize', side_effect=[{'__scene__': s} for s in scenes]), \
             patch('owrpc_app.runtime.time.monotonic', side_effect=lambda: worker.stop_event.tick * 10):
            worker.run()
        confirmed = [value[0] for event, value in events.queue if event == 'detected']
        hero_selection = next(s for s in confirmed if s.scene == 'hero_select')
        self.assertEqual(hero_selection.map_name, 'Ilios')
        self.assertEqual(worker.status.phase, 'results')
        self.assertEqual(worker.status.map_name, 'Ilios')
        self.assertIsNone(worker.status.started_at)

    def test_missed_menu_recovers_new_match_only_from_confirmed_boundary(self):
        from owrpc_app.detection import Detection
        cases = (
            (2, "Grimsvotn", None, 0, True),
            (1, "Grimsvotn", None, 0, False),
            (2, "Old map", (0, 0, 0), 0, True),
            (2, "Old map", (12, 3, 2), 0, False),  # Same-map next round retains cumulative stats.
            (2, None, None, None, False),
        )
        for frames, map_name, kda, elapsed, changed in cases:
            with self.subTest(frames=frames, map_name=map_name, kda=kda):
                status = Status(phase="match", hero="Ana", map_name="Old map", mode="Control",
                                started_at=100, kda=(12, 3, 2), kda_read_at=190,
                                party_size=5, party_read_at=90)
                worker = Worker(Settings(ocr_enabled=True, kda_enabled=True), status, CATALOG, queue.Queue())
                worker.stop_event = Ticks(frames)
                scene = Detection(phase="match", map_name=map_name, kda=kda,
                                  elapsed=elapsed, scene="scoreboard")
                with patch("owrpc_app.runtime.RpcSession", return_value=FakeRpc()), \
                     patch("owrpc_app.runtime.game_running", return_value=True), \
                     patch("owrpc_app.runtime.game_foreground", return_value=True), \
                     patch("owrpc_app.runtime.recognize", return_value={"__scene__": scene}), \
                     patch("owrpc_app.runtime.time.time", return_value=200), \
                     patch("owrpc_app.runtime.time.monotonic", side_effect=lambda: worker.stop_event.tick * 10):
                    worker.run()
                self.assertEqual(worker.status.started_at, 200 if changed else 100)
                self.assertEqual(worker.status.hero, "" if changed else "Ana")
                self.assertEqual(worker.status.party_size, 5)
                if changed:
                    self.assertEqual(worker.status.kda, kda)
                    self.assertEqual(worker.status.mode, "Quick Play")

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
